from __future__ import annotations

import json
import re
from typing import Any


SECTION_NAMES = [
    "COMMIT", "INTERPRETATION", "KEY_REDUCTION", "OBLIGATIONS", "SOLUTION",
    "CHECK", "TOOL_REQUESTS", "CONFIDENCE", "FINAL"
]


def clamp01(value, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return default


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort balanced JSON object extraction for short control outputs."""
    if not text:
        return None
    starts = [i for i, c in enumerate(text) if c == "{"]
    candidates = []
    for start in starts:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
    for cand in sorted(candidates, key=len, reverse=True):
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return None


def extract_json_array(text: str) -> list[Any] | None:
    if not text:
        return None
    starts = [i for i, c in enumerate(text) if c == "["]
    candidates = []
    for start in starts:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
    for cand in sorted(candidates, key=len, reverse=True):
        try:
            obj = json.loads(cand)
            if isinstance(obj, list):
                return obj
        except Exception:
            pass
    return None


def _section_pattern(name: str) -> re.Pattern:
    return re.compile(rf"(?im)^\s*\[{re.escape(name)}\]\s*$")


def extract_sections(text: str) -> dict[str, str]:
    matches = []
    for name in SECTION_NAMES:
        for m in _section_pattern(name).finditer(text or ""):
            matches.append((m.start(), m.end(), name))
    matches.sort()
    sections = {}
    for i, (_, end, name) in enumerate(matches):
        next_start = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        sections[name] = text[end:next_start].strip()
    return sections


def _last_nonempty_line(text: str) -> str:
    for line in reversed((text or "").splitlines()):
        if line.strip():
            return line.strip()
    return ""


def extract_candidate_integer(text: str) -> tuple[int | None, str]:
    """Extract an explicitly committed candidate answer from anywhere in the output.

    This is deliberately weaker than FINAL_ANSWER. It preserves useful progress when
    generation truncates, but it never makes protocol_complete=True by itself.
    """
    if not text:
        return None, "NONE"
    vals = re.findall(
        r"(?im)^\s*CANDIDATE_ANSWER\s*:\s*(?:\\boxed\s*\{\s*)?(-?\d+)(?:\s*\})?\s*$",
        text,
    )
    if vals:
        return int(vals[-1]), "EARLY_COMMIT"
    return None, "NONE"


def extract_final_integer(text: str, require_last_line: bool = True) -> tuple[int | None, str]:
    """
    Conservative answer extraction.

    Strong protocol:
      FINAL_ANSWER: <int> as the final non-empty line.

    Candidate-only fallbacks are allowed so reasoning is not erased merely because
    formatting failed. These fallback modes NEVER make protocol_complete=True.
    """
    if not text:
        return None, "NONE"

    last = _last_nonempty_line(text)

    # Preferred protocol, including boxed variant.
    m = re.fullmatch(r"FINAL_ANSWER\s*:\s*(-?\d+)", last, flags=re.I)
    if m:
        return int(m.group(1)), "FINAL_SENTINEL"

    m = re.fullmatch(
        r"FINAL_ANSWER\s*:\s*\\boxed\s*\{\s*(-?\d+)\s*\}",
        last,
        flags=re.I,
    )
    if m:
        return int(m.group(1)), "FINAL_SENTINEL_BOXED"

    # Candidate-only recovery from a sentinel that was not the final line.
    if not require_last_line:
        vals = re.findall(
            r"(?im)^\s*FINAL_ANSWER\s*:\s*(?:\\boxed\s*\{\s*)?(-?\d+)(?:\s*\})?\s*$",
            text,
        )
        if vals:
            return int(vals[-1]), "FINAL_SENTINEL_NOT_LAST"

    tail = text[-3500:]

    # Standard olympiad answer notation.
    boxed = re.findall(r"\\boxed\s*\{\s*(-?\d+)\s*\}", tail)
    if boxed:
        return int(boxed[-1]), "BOXED_FALLBACK"

    # Explicit declarations on their own line.
    explicit = re.findall(
        r"(?im)^\s*(?:final\s+answer|answer)\s*(?::|=|is)\s*(-?\d+)\s*[.!]?\s*$",
        tail,
    )
    if explicit:
        return int(explicit[-1]), "ANSWER_DECLARATION_FALLBACK"

    # Last-resort candidate-only prose pattern near the tail. This is deliberately
    # narrow and does not verify the answer.
    prose = re.findall(
        r"(?i)(?:therefore|hence|thus)[^\\n]{0,100}?"
        r"(?:final\s+answer|answer)\s+(?:is|=)\s*(-?\d+)",
        tail,
    )
    if prose:
        return int(prose[-1]), "PROSE_ANSWER_FALLBACK"

    return None, "NONE"

def _parse_confidence(section: str) -> float:
    vals = re.findall(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", section or "")
    return clamp01(vals[-1] if vals else 0.5)


def _parse_ambiguity(interpretation: str) -> tuple[bool, str]:
    if not interpretation:
        return False, ""
    m = re.search(r"(?im)^\s*AMBIGUITY\s*:\s*(.+)$", interpretation)
    if m:
        value = m.group(1).strip()
        none_like = value.upper() in {"NONE", "NO", "FALSE", "N/A"}
        return (not none_like), value

    # If the model never emitted the marker but repeatedly self-corrected its reading,
    # treat the interpretation as semantically unsettled. This catches the real Kaggle
    # failure where the solver spent the whole generation debating "product".
    low = interpretation.lower()
    signals = [
        "wait", "key ambiguity", "re-read", "reinterpret", "doesn't make sense",
        "does not make sense", "perhaps", "alternative interpretation",
    ]
    hits = sum(low.count(x) for x in signals)
    if hits >= 2:
        return True, "implicit semantic uncertainty/self-correction detected"
    return False, ""


def parse_solver_output(text: str, truncated: bool = False) -> dict:
    sections = extract_sections(text)
    commit_answer, commit_mode = extract_candidate_integer(text)
    final_answer, final_mode = extract_final_integer(text, require_last_line=True)

    protocol_complete = (
        final_mode in {"FINAL_SENTINEL", "FINAL_SENTINEL_BOXED"}
        and not truncated
    )

    # Final answer dominates when a complete final sentinel exists. Otherwise keep
    # the early committed candidate so a truncated proof does not erase progress.
    answer = final_answer
    answer_mode = final_mode
    if answer is None:
        fallback_final, fallback_mode = extract_final_integer(text, require_last_line=False)
        if fallback_final is not None:
            answer = fallback_final
            answer_mode = fallback_mode
        elif commit_answer is not None:
            answer = commit_answer
            answer_mode = commit_mode

    commit_conflict = (
        commit_answer is not None
        and final_answer is not None
        and int(commit_answer) != int(final_answer)
    )

    tool_requests = []
    traw = sections.get("TOOL_REQUESTS", "")
    arr = extract_json_array(traw)
    if isinstance(arr, list):
        tool_requests = [x for x in arr if isinstance(x, dict)]

    ambiguous, ambiguity_text = _parse_ambiguity(sections.get("INTERPRETATION", ""))
    if commit_conflict:
        ambiguous = True
        ambiguity_text = (
            f"committed answer {commit_answer} conflicts with final answer {final_answer}"
        )
    confidence = _parse_confidence(sections.get("CONFIDENCE", ""))

    proof = sections.get("SOLUTION", "")
    if not proof:
        # Keep useful raw output for diagnostics when protocol formatting failed.
        proof = text.strip()

    obligations = extract_json_object(sections.get("OBLIGATIONS", "")) or {}

    return {
        "interpretation": sections.get("INTERPRETATION", ""),
        "key_reduction": sections.get("KEY_REDUCTION", ""),
        "proof": proof,
        "check": sections.get("CHECK", ""),
        "declared_obligations": obligations if isinstance(obligations, dict) else {},
        "tool_requests": tool_requests,
        "self_confidence": confidence,
        "commit_answer": commit_answer,
        "commit_parse_mode": commit_mode,
        "commit_conflict": commit_conflict,
        "candidate_answer": answer,
        "final_answer": "" if answer is None else str(answer),
        "answer_parse_mode": answer_mode,
        "protocol_complete": protocol_complete,
        "truncated": bool(truncated),
        "ambiguity_detected": ambiguous,
        "ambiguity_text": ambiguity_text,
        "raw_output": text,
        "parse_status": "OK" if protocol_complete else (
            "TRUNCATED_WITH_COMMIT" if truncated and commit_answer is not None else
            "TRUNCATED" if truncated else "PARTIAL"
        ),
    }


def parse_obligation_output(text: str, truncated: bool = False) -> dict:
    """Parse one focused proof-obligation call.

    The call may suggest a corrected candidate, but this is only routing evidence;
    it is never self-verifying.
    """
    def grab(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text or "", flags=re.I | re.M)
        return m.group(1).strip() if m else default

    name = grab(r"^\s*OBLIGATION\s*:\s*([A-Za-z0-9_\-]+)\s*$", "")
    status = grab(r"^\s*STATUS\s*:\s*(PROVED|REFUTED|UNRESOLVED)\s*$", "UNRESOLVED").upper()
    validity = grab(r"^\s*CANDIDATE_VALID\s*:\s*(YES|NO|UNKNOWN)\s*$", "UNKNOWN").upper()
    corr = grab(r"^\s*CORRECTED_CANDIDATE\s*:\s*(-?\d+|UNKNOWN)\s*$", "UNKNOWN")
    evidence_match = re.search(
        r"(?ims)^\s*EVIDENCE\s*:\s*(.*?)(?=^\s*(?:CANDIDATE_VALID|CORRECTED_CANDIDATE)\s*:|\Z)",
        text or "",
    )
    evidence = evidence_match.group(1).strip() if evidence_match else ""
    corrected = int(corr) if re.fullmatch(r"-?\d+", corr or "") else None
    parse_ok = bool(name) and status in {"PROVED", "REFUTED", "UNRESOLVED"}
    return {
        "obligation": name,
        "status": status,
        "candidate_valid": validity,
        "corrected_candidate": corrected,
        "evidence": evidence,
        "parse_ok": parse_ok,
        "truncated": bool(truncated),
        "raw_output": text or "",
    }

def parse_strategy_output(text: str, target_n: int = 3) -> list[dict]:
    arr = extract_json_array(text)
    if not arr:
        obj = extract_json_object(text)
        if obj and isinstance(obj.get("strategies"), list):
            arr = obj["strategies"]
    out = []
    for i, x in enumerate(arr or []):
        if not isinstance(x, dict):
            continue
        out.append({
            "id": str(x.get("id") or f"S{i+1}"),
            "name": str(x.get("name") or f"Strategy {i+1}"),
            "core_idea": str(x.get("core_idea") or x.get("idea") or ""),
            "why_it_fits": str(x.get("why_it_fits") or ""),
            "risks": str(x.get("risks") or ""),
            "confidence": clamp01(x.get("confidence", 0.5)),
        })
        if len(out) >= target_n:
            break
    return out


def split_qwen_thinking(raw_text: str, truncated: bool = False) -> dict:
    """
    Strict parser for Qwen3-4B-Thinking-2507.

    The official Qwen template can include the opening <think> in the prompt, so the
    generated continuation may contain only the closing </think>. Therefore we split
    on the LAST closing marker. Critically, if no closing marker is present we NEVER
    accept VERDICT-like text as final content: it may simply be unfinished private
    reasoning that happens to mention PASS/REVISE.
    """
    raw_text = raw_text or ""
    if "</think>" in raw_text:
        thinking, final = raw_text.rsplit("</think>", 1)
        return {
            "thinking_content": thinking.strip(),
            "final_content": final.strip(),
            "thinking_closed": True,
            "status": "OK" if final.strip() else "EMPTY_FINAL",
        }

    return {
        "thinking_content": raw_text.strip(),
        "final_content": "",
        "thinking_closed": False,
        "status": "TRUNCATED_THINKING" if truncated else "MISSING_THINK_CLOSE",
    }


def parse_critic_output(raw_text: str, truncated: bool = False) -> dict:
    split = split_qwen_thinking(raw_text, truncated=truncated)
    final = split["final_content"]

    def grab(pattern: str, default=None):
        m = re.search(pattern, final, flags=re.I | re.M)
        return m.group(1).strip() if m else default

    verdict = grab(r"^\s*VERDICT\s*:\s*(PASS|REVISE|REJECT)\s*$", None)
    conf = grab(r"^\s*CONFIDENCE\s*:\s*([01](?:\.\d+)?)\s*$", None)
    best = grab(r"^\s*BEST_CANDIDATE\s*:\s*([A-Za-z0-9_.\-]+)\s*$", None)
    revision = grab(r"^\s*REVISION\s*:\s*(.+)$", "")
    error = grab(r"^\s*ERROR\s*:\s*(.+)$", "")

    parse_ok = verdict is not None and conf is not None
    if not parse_ok:
        verdict = "REVISE"
        confidence = 0.0 if split["status"] == "TRUNCATED_THINKING" else 0.5
    else:
        confidence = clamp01(conf)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "best_candidate_id": best,
        "revision_instruction": revision,
        "error": error,
        "summary": final[:1500] if final else split["status"],
        "parse_ok": parse_ok,
        "thinking_status": split["status"],
        "thinking_closed": split["thinking_closed"],
        "thinking_content": split["thinking_content"],
        "final_content": final,
        "truncated": bool(truncated),
    }



def parse_constraint_formalization(text: str) -> dict:
    """Parse the structured semantic JSON used by v2.6.4.

    This stage checks syntax/schema only. Semantic correctness is validated separately
    by the deterministic compiler.
    """
    obj = extract_json_object(text)
    if not isinstance(obj, dict):
        return {
            "parse_ok": False,
            "entities": [],
            "variables": [],
            "pre_relations": [],
            "events": [],
            "post_equalities": [],
            "goal": {},
            "ambiguity": "UNPARSEABLE",
            "raw_output": text or "",
        }

    entities = obj.get("entities")
    variables = obj.get("variables")
    pre_relations = obj.get("pre_relations")
    events = obj.get("events")
    post_equalities = obj.get("post_equalities")
    goal = obj.get("goal")
    ambiguity = str(obj.get("ambiguity", "NONE")).strip()

    ok = (
        isinstance(entities, list) and len(entities) >= 2
        and isinstance(variables, list) and len(variables) >= 4
        and isinstance(pre_relations, list) and len(pre_relations) >= 1
        and isinstance(events, list)
        and isinstance(post_equalities, list)
        and isinstance(goal, dict) and bool(goal)
    )
    return {
        "parse_ok": bool(ok),
        "entities": [str(x) for x in entities] if isinstance(entities, list) else [],
        "variables": variables if isinstance(variables, list) else [],
        "pre_relations": pre_relations if isinstance(pre_relations, list) else [],
        "events": events if isinstance(events, list) else [],
        "post_equalities": post_equalities if isinstance(post_equalities, list) else [],
        "goal": goal if isinstance(goal, dict) else {},
        "ambiguity": ambiguity,
        "raw_output": text or "",
    }


def formalization_is_usable(formalization: dict) -> bool:
    if not formalization or not formalization.get("parse_ok"):
        return False
    ambiguity = str(formalization.get("ambiguity", "")).strip().upper()
    if ambiguity not in {"NONE", "NO", "FALSE", "N/A"}:
        return False
    return (
        len(formalization.get("variables", [])) >= 4
        and len(formalization.get("pre_relations", [])) >= 1
        and isinstance(formalization.get("goal"), dict)
    )


def parse_thinking_solver_output(raw_text: str, truncated: bool = False) -> dict:
    """Parse a Qwen3-Thinking solve call.

    Only the text AFTER the closing </think> is eligible as the public solution.
    Unclosed thinking is never mined for a final answer because it may contain
    tentative numbers or rejected branches.
    """
    split = split_qwen_thinking(raw_text, truncated=truncated)
    final = split.get("final_content", "")
    if not split.get("thinking_closed") or not final.strip():
        c = parse_solver_output("", truncated=True)
        c.update({
            "raw_output": raw_text or "",
            "thinking_content": split.get("thinking_content", ""),
            "thinking_status": split.get("status"),
            "thinking_closed": bool(split.get("thinking_closed")),
            "parse_status": split.get("status", "TRUNCATED_THINKING"),
        })
        return c

    c = parse_solver_output(final, truncated=False)
    c.update({
        "raw_output": raw_text or "",
        "thinking_content": split.get("thinking_content", ""),
        "thinking_status": split.get("status"),
        "thinking_closed": True,
        "deep_final_content": final,
        "source_model_mode": "thinking",
    })
    return c
