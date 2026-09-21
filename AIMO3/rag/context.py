from __future__ import annotations

def build_context(decision, max_chars: int = 7000) -> str:
    if decision.status == "NO_CONTEXT":
        return "RAG_STATUS: NO_CONTEXT\nUse internal mathematical knowledge and reasoning."
    if decision.status == "CONFLICT":
        prefix = (
            "RAG_STATUS: CONFLICT\n"
            "Retrieved material may conflict. Treat it only as candidate hints and independently verify every theorem condition.\n"
        )
    elif decision.status == "WEAK":
        prefix = (
            "RAG_STATUS: WEAK\n"
            "Retrieved material has limited relevance. Use only as hints; do not force these methods.\n"
        )
    else:
        prefix = "RAG_STATUS: ACCEPT\nRelevant knowledge follows. Verify applicability before use.\n"

    parts = [prefix]
    used = len(prefix)
    for h in decision.selected:
        block = (
            f"\n[{h['rank']}] {h['title']} | domain={h['domain']} | score={h['score']:.3f}\n"
            f"{h['text']}\n"
        )
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "".join(parts)
