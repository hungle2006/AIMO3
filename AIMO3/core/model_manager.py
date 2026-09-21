from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import copy
import gc
import json
import os
import time

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from .config import model_paths
from .budget import BudgetExhausted, cap_generation_budget


@dataclass
class GenerationResult:
    text: str
    raw_text: str
    input_tokens: int
    output_tokens: int
    max_new_tokens: int
    latency_sec: float
    gpu: int
    peak_allocated_gb: float
    free_before_gb: float
    free_after_gb: float
    do_sample: bool
    ended_with_eos: bool
    truncated: bool
    finish_reason: str
    timed_out: bool = False



class ModelManager:
    """
    T4x2 layout
      GPU0: DeepSeek-R1-Distill-Qwen-1.5B proposer + Qwen3-4B-Instruct solver
      GPU1: Qwen3-4B-Thinking critic
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.paths = model_paths(cfg)
        self.models: dict[str, object] = {}
        self.tokenizers: dict[str, object] = {}
        self.num_gpus = torch.cuda.device_count()

        if self.num_gpus < 1:
            raise RuntimeError("CUDA GPU is required.")
        if cfg.get("runtime", {}).get("require_two_gpus", False) and self.num_gpus < 2:
            raise RuntimeError(f"T4x2 runtime requires 2 GPUs; detected {self.num_gpus}.")

        self.resident = bool(
            cfg.get("runtime", {}).get("resident_on_two_gpus", True)
            and self.num_gpus >= 2
        )

    def gpu_report(self) -> list[dict]:
        rows = []
        for i in range(self.num_gpus):
            props = torch.cuda.get_device_properties(i)
            free_b, total_b = torch.cuda.mem_get_info(i)
            rows.append({
                "gpu": i,
                "name": props.name,
                "total_gb": round(total_b / 1024**3, 2),
                "free_gb": round(free_b / 1024**3, 2),
                "allocated_gb": round(torch.cuda.memory_allocated(i) / 1024**3, 2),
                "reserved_gb": round(torch.cuda.memory_reserved(i) / 1024**3, 2),
            })
        return rows

    def validate_t4x2(self) -> None:
        if self.num_gpus < 2:
            raise RuntimeError("Two CUDA GPUs are required by this profile.")
        for i in (0, 1):
            props = torch.cuda.get_device_properties(i)
            total_gb = props.total_memory / 1024**3
            if total_gb < 14.0:
                raise RuntimeError(
                    f"GPU{i} has {total_gb:.1f}GB; expected a 16GB-class T4."
                )

    def role_gpu(self, role: str) -> int:
        requested = int(self.cfg["models"][role].get("gpu", 0))
        return requested if requested < self.num_gpus else 0

    def _free_gb(self, gpu: int) -> float:
        free_b, _ = torch.cuda.mem_get_info(gpu)
        return free_b / 1024**3

    def _quant_config(self):
        mode = self.cfg.get("runtime", {}).get("quantization", "4bit_nf4")
        if mode == "4bit_nf4":
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
            )
        if mode == "8bit":
            return BitsAndBytesConfig(load_in_8bit=True)
        return None

    def _load_with_attention_fallback(self, kwargs: dict):
        runtime = self.cfg.get("runtime", {})
        requested = runtime.get("attn_implementation", "sdpa")
        fallback = runtime.get("attn_fallback", "eager")
        if requested:
            kwargs["attn_implementation"] = requested
        try:
            return AutoModelForCausalLM.from_pretrained(**kwargs)
        except (ValueError, ImportError, RuntimeError) as e:
            msg = str(e).lower()
            backend_error = any(k in msg for k in [
                "attn", "attention", "sdpa", "flash", "scaled_dot_product"
            ])
            if not backend_error or fallback == requested:
                raise
            print(f"[WARN] attention backend {requested!r} failed; retrying {fallback!r}.")
            kwargs["attn_implementation"] = fallback
            return AutoModelForCausalLM.from_pretrained(**kwargs)

    def load(self, role: str):
        if role in self.models:
            return self.models[role], self.tokenizers[role]

        if not self.resident:
            for old in list(self.models):
                if old != role:
                    self.unload(old)

        path = self.paths[role]
        if not path.exists():
            raise FileNotFoundError(f"Missing local model directory: {path}")

        gpu = self.role_gpu(role)
        print(f"[LOAD] {role} -> GPU{gpu}: {path}")
        print(f"[MEM] free before load: {self._free_gb(gpu):.2f} GB")

        tok = AutoTokenizer.from_pretrained(
            str(path), local_files_only=True, trust_remote_code=True, use_fast=True
        )
        if tok.pad_token_id is None and tok.eos_token_id is not None:
            tok.pad_token = tok.eos_token

        kwargs = dict(
            pretrained_model_name_or_path=str(path),
            local_files_only=True,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            device_map={"": gpu},
            torch_dtype=torch.float16,
        )
        qcfg = self._quant_config()
        if qcfg is not None:
            kwargs["quantization_config"] = qcfg

        try:
            model = self._load_with_attention_fallback(kwargs)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            raise RuntimeError(
                f"OOM while loading {role} on GPU{gpu}. Restart the notebook and "
                "remove other GPU workloads."
            )

        model.eval()
        if hasattr(model.config, "use_cache"):
            model.config.use_cache = True

        self.models[role] = model
        self.tokenizers[role] = tok
        print(f"[MEM] free after load:  {self._free_gb(gpu):.2f} GB")
        return model, tok

    def unload(self, role: str) -> None:
        self.models.pop(role, None)
        self.tokenizers.pop(role, None)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def preload(self) -> None:
        self.validate_t4x2()
        roles = self.cfg.get("runtime", {}).get("preload_roles", ["solver", "critic"])
        roles = [r for r in roles if r in {"proposer", "solver", "critic"}]
        for role in roles:
            self.load(role)
        print(f"[READY] Resident roles: {roles}")
        print(json.dumps(self.gpu_report(), indent=2))

    @staticmethod
    def _clean_decoded(text: str, tok) -> str:
        # Keep </think> intact for critic parsing, but strip obvious terminal special tokens.
        for token in [getattr(tok, "eos_token", None), getattr(tok, "pad_token", None)]:
            if token and token != "</think>":
                text = text.replace(token, "")
        return text.strip()

    def generate(
        self,
        role: str,
        user_prompt: str,
        system_prompt: str | None = None,
        overrides: dict | None = None,
    ) -> GenerationResult:
        model, tok = self.load(role)
        p = dict(self.cfg["models"][role])
        if overrides:
            p.update(overrides)
        budget_remaining_tokens = p.pop("_budget_remaining_tokens", None)
        budget_remaining_seconds = p.pop("_budget_remaining_seconds", None)
        gpu = self.role_gpu(role)

        # DeepSeek-R1 distilled proposer: put all instructions in user content.
        messages = []
        if role != "proposer" and system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if role == "proposer" and system_prompt:
            user_prompt = system_prompt + "\n\n" + user_prompt
        messages.append({"role": "user", "content": user_prompt})

        try:
            rendered = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            rendered = "\n\n".join(m["content"] for m in messages)

        max_input = int(p.get("max_input_tokens", 10000))
        encoded = tok(
            rendered,
            return_tensors="pt",
            truncation=True,
            max_length=max_input,
        )
        encoded = {k: v.to(f"cuda:{gpu}", non_blocking=True) for k, v in encoded.items()}
        input_tokens = int(encoded["input_ids"].shape[-1])

        configured_max_new = int(p.get("max_new_tokens", 2048))
        max_new, max_time = cap_generation_budget(
            input_tokens=input_tokens,
            configured_max_new=configured_max_new,
            remaining_total_tokens=budget_remaining_tokens,
            remaining_seconds=budget_remaining_seconds,
            safety_seconds=float(self.cfg.get("runtime", {}).get("generation_time_safety_sec", 1.0)),
        )
        do_sample = bool(p.get("do_sample", False))
        generation_cfg = getattr(model, "generation_config", None)
        effective_eos = getattr(generation_cfg, "eos_token_id", None) if generation_cfg is not None else None
        effective_pad = getattr(generation_cfg, "pad_token_id", None) if generation_cfg is not None else None
        if effective_eos is None:
            effective_eos = tok.eos_token_id
        if effective_pad is None:
            effective_pad = tok.pad_token_id

        # Work on a private GenerationConfig copy. This prevents a checkpoint's
        # saved sampling values from producing warnings when a call is deterministic,
        # and avoids mutating the resident model globally across roles/calls.
        call_generation_config = copy.deepcopy(model.generation_config)
        call_generation_config.do_sample = do_sample
        call_generation_config.pad_token_id = effective_pad
        call_generation_config.eos_token_id = effective_eos
        call_generation_config.repetition_penalty = float(p.get("repetition_penalty", 1.0))

        if do_sample:
            call_generation_config.temperature = float(p.get("temperature", 0.7))
            call_generation_config.top_p = float(p.get("top_p", 0.8))
            call_generation_config.top_k = int(p.get("top_k", 20))
        else:
            # Neutralize checkpoint sampling-only parameters so GenerationConfig
            # validation does not warn that they are ignored under greedy decoding.
            call_generation_config.temperature = None
            call_generation_config.top_p = None
            call_generation_config.top_k = None

        gen_kwargs = {
            "generation_config": call_generation_config,
            "max_new_tokens": max_new,
            "use_cache": True,
            "return_dict_in_generate": True,
            "output_scores": False,
        }

        # Hugging Face generate() supports max_time. It checks during generation and
        # finishes the current forward pass after the time limit is crossed.
        if max_time is not None:
            gen_kwargs["max_time"] = float(max_time)

        free_before = self._free_gb(gpu)
        torch.cuda.reset_peak_memory_stats(gpu)
        started = time.perf_counter()

        try:
            with torch.inference_mode():
                generated = model.generate(**encoded, **gen_kwargs)
        except torch.OutOfMemoryError:
            del encoded
            gc.collect()
            torch.cuda.empty_cache()
            raise RuntimeError(
                f"Generation OOM for {role} on GPU{gpu}. Reduce input/output token caps."
            )

        latency = time.perf_counter() - started
        seq = generated.sequences[0]
        gen_ids = seq[input_tokens:]
        output_tokens = int(gen_ids.shape[-1])
        last_id = int(gen_ids[-1].item()) if output_tokens else None
        eos_ids = effective_eos
        if isinstance(eos_ids, int):
            eos_set = {eos_ids}
        elif eos_ids is None:
            eos_set = set()
        else:
            eos_set = set(eos_ids)
        ended_with_eos = last_id in eos_set if last_id is not None else False
        timed_out = bool(max_time is not None and latency >= float(max_time) and not ended_with_eos)
        truncated = bool((output_tokens >= max_new or timed_out) and not ended_with_eos)
        if timed_out:
            finish_reason = "time"
        elif output_tokens >= max_new and not ended_with_eos:
            finish_reason = "length"
        else:
            finish_reason = "eos_or_stop"

        # Preserve Qwen Thinking delimiter in raw_text by not skipping special tokens.
        raw_text = tok.decode(gen_ids, skip_special_tokens=False)
        clean_text = tok.decode(gen_ids, skip_special_tokens=True)
        if role == "critic":
            text = self._clean_decoded(raw_text, tok)
        else:
            text = clean_text.strip()

        peak = torch.cuda.max_memory_allocated(gpu) / 1024**3
        free_after = self._free_gb(gpu)

        del encoded, generated, seq, gen_ids
        gc.collect()
        if self.cfg.get("runtime", {}).get("clear_cache_between_calls", False):
            torch.cuda.empty_cache()

        return GenerationResult(
            text=text,
            raw_text=raw_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            max_new_tokens=max_new,
            latency_sec=latency,
            gpu=gpu,
            peak_allocated_gb=peak,
            free_before_gb=free_before,
            free_after_gb=free_after,
            do_sample=do_sample,
            ended_with_eos=ended_with_eos,
            truncated=truncated,
            finish_reason=finish_reason,
            timed_out=timed_out,
        )
