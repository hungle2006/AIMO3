from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any

import sympy as sp


_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def _norm(s: str) -> str:
    return (
        (s or "")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
    )


def _number_value(token: str) -> int | None:
    token = (token or "").strip().lower().replace("-", " ")
    if token.isdigit():
        return int(token)
    if token in _NUMBER_WORDS:
        return _NUMBER_WORDS[token]
    parts = token.split()
    if 1 <= len(parts) <= 2 and all(p in _NUMBER_WORDS for p in parts):
        return sum(_NUMBER_WORDS[p] for p in parts)
    return None


def _clean_kind(kind: str) -> str:
    k = re.sub(r"[^a-z0-9_ ]+", "", (kind or "").lower()).strip()
    aliases = {
        "sweet": "sweets", "candy": "sweets", "candies": "sweets",
        "year": "age", "years": "age", "ages": "age",
        "coin": "coins",
    }
    return aliases.get(k, k)


def _owner_key(owner: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (owner or "").lower())


def detect_transfer_from_text(problem: str, entities: list[str]) -> dict[str, Any] | None:
    """Best-effort cross-check for an explicit two-party transfer in English prose.

    For dialogue, bind pronouns to the nearest preceding speech attribution rather
    than allowing a regex to span from an earlier speaker into a later quotation.
    """
    text = _norm(problem)
    names = [e for e in entities if isinstance(e, str) and e.strip()]

    give = re.search(
        r"\bgive\s+me\s+(?P<num>[A-Za-z-]+|\d+)\s+(?:of\s+)?your\s+(?P<asset>[A-Za-z]+)",
        text,
        re.I,
    )
    if give:
        prefix = text[:give.start()]
        attrs = list(re.finditer(
            r"\b(?P<speaker>[A-Z][A-Za-z'-]*)\s+(?:replies|replied|responds|responded|says|said)\b",
            prefix,
            re.I,
        ))
        if attrs:
            speaker_token = attrs[-1].group("speaker")
            speaker = next(
                (n for n in names if _owner_key(n) == _owner_key(speaker_token)),
                speaker_token,
            )
            others = [n for n in names if _owner_key(n) != _owner_key(speaker)]
            amount = _number_value(give.group("num"))
            if len(others) == 1 and amount is not None:
                return {
                    "type": "transfer",
                    "asset": _clean_kind(give.group("asset")),
                    "amount": amount,
                    "from": others[0],
                    "to": speaker,
                    "source": "dialogue_give_me_your",
                }

    # Direct form: "Alice gives Bob five sweets" / "Alice gave Bob 5 coins".
    pat2 = re.compile(
        r"\b(?P<giver>[A-Z][A-Za-z'-]*)\s+(?:gives|gave|give)\s+"
        r"(?P<recv>[A-Z][A-Za-z'-]*)\s+(?P<num>[A-Za-z-]+|\d+)\s+(?P<asset>[A-Za-z]+)",
        re.I,
    )
    m = pat2.search(text)
    if m:
        amount = _number_value(m.group("num"))
        if amount is not None:
            def canon(x: str) -> str:
                return next((n for n in names if _owner_key(n) == _owner_key(x)), x)
            return {
                "type": "transfer",
                "asset": _clean_kind(m.group("asset")),
                "amount": amount,
                "from": canon(m.group("giver")),
                "to": canon(m.group("recv")),
                "source": "direct_transfer",
            }
    return None


@dataclass
class SemanticCompileResult:
    ok: bool
    equations: list[str]
    goal_expr: str
    checks: list[dict]
    variable_domains: dict[str, str]
    event: dict | None
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def compile_semantic_formalization(problem: str, f: dict) -> SemanticCompileResult:
    checks: list[dict] = []
    if not f or not f.get("parse_ok"):
        return SemanticCompileResult(False, [], "", checks, {}, None, "formalization not parseable")

    ambiguity = str(f.get("ambiguity", "NONE")).strip().upper()
    if ambiguity not in {"NONE", "NO", "FALSE", "N/A"}:
        return SemanticCompileResult(False, [], "", checks, {}, None, "formalization reports ambiguity")

    entities = [str(x) for x in f.get("entities", []) if str(x).strip()]
    variables = f.get("variables", [])
    if len(entities) < 2 or not isinstance(variables, list):
        return SemanticCompileResult(False, [], "", checks, {}, None, "missing entities/variables")

    var_map: dict[tuple[str, str], str] = {}
    domains: dict[str, str] = {}
    names_seen: set[str] = set()
    for v in variables:
        if not isinstance(v, dict):
            continue
        name = str(v.get("name", "")).strip()
        owner = str(v.get("owner", "")).strip()
        kind = _clean_kind(str(v.get("kind", "")))
        domain = str(v.get("domain", "integer")).strip().lower()
        if not name or not owner or not kind or not re.fullmatch(r"[A-Za-z]\w*", name):
            continue
        var_map[(_owner_key(owner), kind)] = name
        domains[name] = domain
        names_seen.add(name)

    checks.append({
        "type": "variable_role_map",
        "passed": len(var_map) >= 4,
        "mapped": {f"{a}.{k}": n for (a, k), n in var_map.items()},
    })
    if len(var_map) < 4:
        return SemanticCompileResult(False, [], "", checks, domains, None, "insufficient owner/kind variable mapping")

    events = f.get("events", [])
    event = None
    if isinstance(events, list) and events:
        e = events[0]
        if isinstance(e, dict) and str(e.get("type", "")).lower() == "transfer":
            try:
                event = {
                    "type": "transfer",
                    "asset": _clean_kind(str(e.get("asset", ""))),
                    "amount": int(e.get("amount")),
                    "from": str(e.get("from", "")).strip(),
                    "to": str(e.get("to", "")).strip(),
                }
            except Exception:
                event = None

    text_event = detect_transfer_from_text(problem, entities)
    if text_event is not None:
        event_match = bool(
            event
            and event.get("type") == "transfer"
            and _clean_kind(event.get("asset", "")) == _clean_kind(text_event.get("asset", ""))
            and int(event.get("amount", -1)) == int(text_event.get("amount", -2))
            and _owner_key(event.get("from", "")) == _owner_key(text_event.get("from", ""))
            and _owner_key(event.get("to", "")) == _owner_key(text_event.get("to", ""))
        )
        checks.append({
            "type": "text_transfer_crosscheck",
            "passed": event_match,
            "text_event": text_event,
            "model_event": event,
        })
        if not event_match:
            return SemanticCompileResult(False, [], "", checks, domains, event, "transfer event disagrees with problem text")
    else:
        checks.append({"type": "text_transfer_crosscheck", "passed": True, "reason": "no high-confidence text event detected"})

    def base(owner: str, kind: str) -> str:
        key = (_owner_key(owner), _clean_kind(kind))
        if key not in var_map:
            raise KeyError(f"missing variable for {owner}.{kind}")
        return var_map[key]

    def state(owner: str, kind: str, after: bool) -> str:
        expr = base(owner, kind)
        if not after or not event or _clean_kind(kind) != _clean_kind(event["asset"]):
            return expr
        amt = int(event["amount"])
        if _owner_key(owner) == _owner_key(event["from"]):
            return f"({expr}-{amt})"
        if _owner_key(owner) == _owner_key(event["to"]):
            return f"({expr}+{amt})"
        return expr

    # Cross-check simple relation words against the structured relation types/factors.
    low = _norm(problem).lower()
    pre_rels = [r for r in (f.get("pre_relations", []) or []) if isinstance(r, dict)]
    post_rels = [r for r in (f.get("post_equalities", []) or []) if isinstance(r, dict)]
    lexical_ok = True
    lexical_detail = []
    if "double" in low or "twice" in low:
        ok = any(str(r.get("type", "")).lower() == "sum_ratio" and int(r.get("factor", -1)) == 2 for r in pre_rels)
        lexical_ok = lexical_ok and ok
        lexical_detail.append({"signal": "double/twice", "passed": ok})
    m_times = re.search(r"\b(four|4)\s+times\b", low)
    if m_times:
        ok = any(str(r.get("type", "")).lower() == "product_ratio" and int(r.get("factor", -1)) == 4 for r in pre_rels)
        lexical_ok = lexical_ok and ok
        lexical_detail.append({"signal": "four times", "passed": ok})
    if "sum and product" in low and "equal" in low:
        types = {str(r.get("type", "")).lower() for r in post_rels}
        ok = {"sum_equal", "product_equal"}.issubset(types)
        lexical_ok = lexical_ok and ok
        lexical_detail.append({"signal": "sum and product equal", "passed": ok})
    checks.append({"type": "lexical_relation_crosscheck", "passed": lexical_ok, "details": lexical_detail})
    if not lexical_ok:
        return SemanticCompileResult(False, [], "", checks, domains, event, "relation factors/types disagree with problem text")

    equations: list[str] = []
    try:
        for rel in f.get("pre_relations", []) or []:
            if not isinstance(rel, dict):
                continue
            typ = str(rel.get("type", "")).lower()
            left = str(rel.get("left", ""))
            right = str(rel.get("right", ""))
            factor = int(rel.get("factor", 1))
            operands = [_clean_kind(str(x)) for x in rel.get("operands", [])]
            if len(operands) != 2 or factor <= 0:
                raise ValueError(f"bad pre relation: {rel}")
            l1, l2 = state(left, operands[0], False), state(left, operands[1], False)
            r1, r2 = state(right, operands[0], False), state(right, operands[1], False)
            if typ == "sum_ratio":
                equations.append(f"({l1}+{l2})={factor}*({r1}+{r2})")
            elif typ == "product_ratio":
                equations.append(f"({l1})*({l2})={factor}*({r1})*({r2})")
            else:
                raise ValueError(f"unsupported pre relation type: {typ}")

        for rel in f.get("post_equalities", []) or []:
            if not isinstance(rel, dict):
                continue
            typ = str(rel.get("type", "")).lower()
            left = str(rel.get("left", ""))
            right = str(rel.get("right", ""))
            operands = [_clean_kind(str(x)) for x in rel.get("operands", [])]
            if len(operands) != 2:
                raise ValueError(f"bad post relation: {rel}")
            l1, l2 = state(left, operands[0], True), state(left, operands[1], True)
            r1, r2 = state(right, operands[0], True), state(right, operands[1], True)
            if typ == "sum_equal":
                equations.append(f"({l1}+{l2})=({r1}+{r2})")
            elif typ == "product_equal":
                equations.append(f"({l1})*({l2})=({r1})*({r2})")
            else:
                raise ValueError(f"unsupported post relation type: {typ}")

        goal = f.get("goal", {})
        if not isinstance(goal, dict) or str(goal.get("type", "")).lower() != "product":
            raise ValueError("only structured product goal supported by deterministic compiler")
        terms = goal.get("terms", [])
        if not isinstance(terms, list) or len(terms) < 2:
            raise ValueError("goal terms missing")
        goal_parts = []
        for t in terms:
            owner, kind = str(t).split(".", 1)
            goal_parts.append(base(owner, kind))
        goal_expr = "*".join(f"({x})" for x in goal_parts)
    except Exception as e:
        checks.append({"type": "semantic_compile", "passed": False, "error": str(e)})
        return SemanticCompileResult(False, [], "", checks, domains, event, f"semantic compile failed: {e}")

    # Transfer conservation certificate is structural: source loses exactly what receiver gains.
    if event:
        asset = event["asset"]
        try:
            src0 = base(event["from"], asset)
            dst0 = base(event["to"], asset)
            src1 = state(event["from"], asset, True)
            dst1 = state(event["to"], asset, True)
            sym = {n: sp.Symbol(n) for n in names_seen}
            conservation = sp.simplify(
                sp.sympify(f"({src0})+({dst0})", locals=sym)
                - sp.sympify(f"({src1})+({dst1})", locals=sym)
            ) == 0
        except Exception:
            conservation = False
        checks.append({
            "type": "transfer_conservation",
            "passed": bool(conservation),
            "before": f"{src0}+{dst0}" if event else "",
            "after": f"{src1}+{dst1}" if event else "",
        })
        if not conservation:
            return SemanticCompileResult(False, equations, goal_expr, checks, domains, event, "transfer conservation failed")

    enough = len(equations) >= 2 and bool(goal_expr)
    checks.append({"type": "compiled_relations", "passed": enough, "equations": equations, "goal_expr": goal_expr})
    return SemanticCompileResult(enough, equations, goal_expr, checks, domains, event, "ok" if enough else "not enough compiled relations")


def semantic_certificate_ok(compiled: dict) -> bool:
    """True only for a fully validated supported semantic template."""
    if not compiled or not compiled.get("ok"):
        return False
    checks = compiled.get("checks", [])
    by_type = {c.get("type"): c for c in checks if isinstance(c, dict)}
    required = [
        "variable_role_map",
        "text_transfer_crosscheck",
        "lexical_relation_crosscheck",
        "transfer_conservation",
        "compiled_relations",
    ]
    if not all(t in by_type and by_type[t].get("passed") is True for t in required):
        return False
    # Auto-certification requires a high-confidence text-derived transfer event,
    # not merely the absence of a detectable event.
    if not by_type["text_transfer_crosscheck"].get("text_event"):
        return False
    return True


def solve_compiled_system(compiled: dict) -> dict:
    """Solve a small structured algebra system exactly with SymPy.

    This function only consumes equations produced by compile_semantic_formalization,
    not arbitrary raw model expressions.
    """
    if not compiled or not compiled.get("ok"):
        return {"ok": False, "unique_answer": False, "reason": "compiled semantic system unavailable"}

    eq_strings = list(compiled.get("equations", []))
    domains = dict(compiled.get("variable_domains", {}))
    names = sorted(domains)
    symbols = {n: sp.Symbol(n, real=True) for n in names}
    try:
        equations = []
        for eq in eq_strings:
            lhs, rhs = eq.split("=", 1)
            equations.append(sp.expand(sp.sympify(lhs, locals=symbols) - sp.sympify(rhs, locals=symbols)))
        raw = sp.solve(equations, [symbols[n] for n in names], dict=True)
    except Exception as e:
        return {"ok": False, "unique_answer": False, "reason": f"sympy solve failed: {e}"}

    valid = []
    for sol in raw:
        vals: dict[str, int] = {}
        acceptable = True
        for name in names:
            v = sp.simplify(sol.get(symbols[name], symbols[name]))
            if v.free_symbols or v.is_real is False or v.is_integer is not True:
                acceptable = False
                break
            iv = int(v)
            domain = domains.get(name, "integer")
            if "positive" in domain and iv <= 0:
                acceptable = False
                break
            if "nonnegative" in domain and iv < 0:
                acceptable = False
                break
            vals[name] = iv
        if not acceptable:
            continue

        event = compiled.get("event")
        if event:
            # Ensure the giver actually has enough of the transferred asset when a
            # corresponding variable can be inferred from compiled checks/equations.
            amount = int(event.get("amount", 0))
            # Find source variable by looking for the state-change pattern (v-amount).
            source_var = None
            pat = re.compile(rf"\(([A-Za-z]\w*)-{amount}\)")
            for eq in eq_strings:
                m = pat.search(eq)
                if m:
                    source_var = m.group(1)
                    break
            if source_var and vals.get(source_var, amount) < amount:
                continue

        try:
            goal_value = sp.simplify(sp.sympify(compiled["goal_expr"], locals={**symbols, **{k: sp.Integer(v) for k, v in vals.items()}}))
            if goal_value.free_symbols or goal_value.is_integer is not True:
                continue
            answer = int(goal_value)
        except Exception:
            continue

        residuals = []
        for eq in eq_strings:
            lhs, rhs = eq.split("=", 1)
            lv = sp.sympify(lhs, locals={**symbols, **{k: sp.Integer(v) for k, v in vals.items()}})
            rv = sp.sympify(rhs, locals={**symbols, **{k: sp.Integer(v) for k, v in vals.items()}})
            residuals.append(sp.simplify(lv-rv))
        if all(r == 0 for r in residuals):
            valid.append({"assignments": vals, "answer": answer})

    answers = sorted(set(v["answer"] for v in valid))
    if len(answers) != 1:
        return {
            "ok": bool(valid),
            "unique_answer": False,
            "answers": answers,
            "solutions": valid,
            "reason": "no unique integer goal value",
        }

    chosen = next(v for v in valid if v["answer"] == answers[0])
    return {
        "ok": True,
        "unique_answer": True,
        "answer": answers[0],
        "assignments": chosen["assignments"],
        "solutions": valid,
        "reason": "unique exact integer goal value",
    }


def deterministic_candidate(compiled: dict, solved: dict, cid: str = "DET1") -> dict:
    if not solved.get("ok") or not solved.get("unique_answer"):
        raise ValueError("deterministic candidate requires a unique exact solution")
    ans = int(solved["answer"])
    assignments = {k: int(v) for k, v in solved["assignments"].items()}
    equalities = []
    for eq in compiled.get("equations", []):
        lhs, rhs = eq.split("=", 1)
        equalities.append({"lhs": lhs, "rhs": rhs})
    tool_request = {
        "op": "check_equalities",
        "assignments": assignments,
        "equalities": equalities,
        "answer_expr": compiled.get("goal_expr", ""),
        "expected_answer": ans,
    }
    proof = (
        "A deterministic semantic compiler converted the validated relational structure "
        "into equations, and SymPy solved the resulting integer system exactly. "
        f"Assignments: {assignments}."
    )
    return {
        "id": cid,
        "stage": "deterministic_semantic_solve",
        "interpretation": "Validated structured semantics; transfer conservation passed.",
        "proof": proof,
        "check": "All compiled equations and the goal value are checked exactly.",
        "tool_requests": [tool_request],
        "self_confidence": 0.99,
        "candidate_answer": ans,
        "final_answer": str(ans),
        "answer_parse_mode": "DETERMINISTIC_EXACT",
        "protocol_complete": True,
        "truncated": False,
        "ambiguity_detected": False,
        "ambiguity_text": "",
        "raw_output": f"FINAL_ANSWER: {ans}",
        "parse_status": "OK",
        "deterministic_solution": solved,
        "semantic_compilation": compiled,
    }
