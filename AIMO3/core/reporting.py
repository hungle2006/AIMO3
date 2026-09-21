from __future__ import annotations

from pathlib import Path
import json


def save_result(result: dict, out_dir: str | Path):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = str(result.get("problem_id", "problem")).replace("/", "_")
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    final = result.get("final_solution", {})
    crit = result.get("critic", {})
    m = result.get("metrics", {})
    ver = result.get("verification", {})
    rag = result.get("rag", {})
    rag_final = rag.get("final") or {}
    rag_gate = (rag_final.get("gate") or {}).get("status", "NOT_USED")

    lines = [
        f"# {stem}", "",
        "## Problem", "", result.get("problem", ""), "",
        "## Run summary", "",
        f"- Status: `{result.get('status')}`",
        f"- Candidate answer: `{result.get('candidate_answer')}`",
        f"- Verified answer: `{result.get('verified_answer')}`",
        f"- Verification: `{ver.get('level')}` passed=`{ver.get('passed')}`",
        f"- Difficulty: `{result.get('difficulty')}` ({result.get('budget',{}).get('name')})",
        f"- RAG: used=`{rag.get('used')}` gate=`{rag_gate}`",
        f"- Model calls: `{m.get('model_calls')}`",
        f"- Total tokens: `{m.get('total_tokens')}`",
        f"- Latency: `{m.get('latency_sec',0):.2f}s`",
        f"- Critic: `{crit.get('verdict')}` confidence=`{crit.get('confidence')}`", "",
        "## Interpretation", "", final.get("interpretation", ""), "",
        "## Best proof", "", final.get("proof", ""), "",
        "## Candidate answer", "", str(final.get("candidate_answer", "")), "",
        "## Verified answer", "", str(final.get("verified_answer", "")), "",
        "## Verification reason", "", ver.get("reason", ""), "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
