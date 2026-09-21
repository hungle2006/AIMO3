from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("run_pdf_pipeline_v281_test", ROOT / "run_pdf_pipeline.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

class FakeManager:
    def __init__(self, cfg):
        self.cfg = cfg
    def preload(self):
        return None

class FakePipe:
    def __init__(self, cfg, manager):
        self.cfg = cfg
        self.manager = manager
    def run(self, problem, problem_id="problem", retrieval_problem=None):
        return {
            "problem_id": problem_id,
            "problem": problem,
            "status": "UNRESOLVED",
            "candidate_answer": None,
            "verified_answer": None,
            "verification": {"level": "NONE", "passed": False, "reason": "smoke"},
            "metrics": {"model_calls": 0, "total_tokens": 0, "latency_sec": 0.0},
        }

fake_mm = types.ModuleType("core.model_manager")
fake_mm.ModelManager = FakeManager
sys.modules["core.model_manager"] = fake_mm

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    inp = td / "problem.txt"
    inp.write_text("Find an integer.", encoding="utf-8")
    out = td / "out"

    mod.load_config = lambda _: {"project": {"output_dir": str(out)}}
    mod.prepare_environment = lambda cfg: None
    mod.save_result = lambda result, output_dir: None
    mod.FullOlympiadPipeline = FakePipe

    old_argv = sys.argv[:]
    try:
        sys.argv = ["run_pdf_pipeline.py", "--input", str(inp), "--config", "ignored.yaml"]
        mod.main()
    finally:
        sys.argv = old_argv

    summary = out / "pdf_batch_summary.json"
    assert summary.exists(), "normal path did not reach summary writing"

print("test_run_pdf_normal_path_v281: PASS")
