from __future__ import annotations

import ast
import math
import operator
import re
import sympy as sp

SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
MAX_EXPR_CHARS = 5000
MAX_AST_NODES = 400
MAX_POWER_ABS = 1_000_000


def _symbols(names):
    env = {}
    for n in names or []:
        if not SAFE_NAME.fullmatch(str(n)):
            raise ValueError(f"Unsafe symbol name: {n}")
        env[str(n)] = sp.Symbol(str(n))
    return env


SAFE_FUNCS = {
    "sqrt": sp.sqrt,
    "Abs": sp.Abs,
    "abs": sp.Abs,
    "floor": sp.floor,
    "ceiling": sp.ceiling,
    "factorial": sp.factorial,
}
SAFE_CONSTS = {"pi": sp.pi, "E": sp.E}


class _SafeSympyBuilder(ast.NodeVisitor):
    def __init__(self, env: dict):
        self.env = dict(env)
        self.nodes = 0

    def visit(self, node):
        self.nodes += 1
        if self.nodes > MAX_AST_NODES:
            raise ValueError("Expression AST too large")
        return super().visit(node)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            raise ValueError("Boolean constants are not allowed")
        if isinstance(node.value, int):
            return sp.Integer(node.value)
        raise ValueError("Only integer literals are allowed")

    def visit_Name(self, node):
        if node.id in self.env:
            return self.env[node.id]
        if node.id in SAFE_CONSTS:
            return SAFE_CONSTS[node.id]
        raise ValueError(f"Unknown/unsafe name: {node.id}")

    def visit_UnaryOp(self, node):
        value = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value
        raise ValueError("Unsafe unary operator")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            # Permit mathematical powers, but reject obviously abusive literal exponents.
            if isinstance(right, sp.Integer) and abs(int(right)) > MAX_POWER_ABS:
                raise ValueError("Exponent too large")
            return left ** right
        if isinstance(node.op, ast.Mod):
            return sp.Mod(left, right)
        raise ValueError("Unsafe binary operator")

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCS:
            raise ValueError("Unsafe function call")
        if node.keywords:
            raise ValueError("Keyword arguments are not allowed")
        args = [self.visit(a) for a in node.args]
        return SAFE_FUNCS[node.func.id](*args)

    def generic_visit(self, node):
        raise ValueError(f"Unsafe expression node: {type(node).__name__}")


def _parse(expr: str, env: dict):
    expr = str(expr).strip()
    if len(expr) > MAX_EXPR_CHARS:
        raise ValueError("Expression too long")
    # Normalize common mathematical power spelling before Python parses precedence.
    expr = expr.replace("^", "**")
    tree = ast.parse(expr, mode="eval")
    return _SafeSympyBuilder(env).visit(tree)


def _valuation_int(n: int, p: int) -> int:
    n = abs(int(n)); p = int(p)
    if p <= 1:
        raise ValueError("p must be >= 2")
    if n == 0:
        raise ValueError("valuation of 0 is not finite")
    k = 0
    while n % p == 0:
        n //= p
        k += 1
    return k


def _valuation_factorial(n: int, p: int) -> int:
    n, p = int(n), int(p)
    if n < 0 or p <= 1:
        raise ValueError("Require n>=0 and p>=2")
    s = 0
    q = p
    while q <= n:
        s += n // q
        q *= p
    return s


def _numeric_env(assignments: dict) -> dict:
    env = {}
    for name, value in (assignments or {}).items():
        if not SAFE_NAME.fullmatch(str(name)):
            raise ValueError(f"Unsafe assignment name: {name}")
        env[str(name)] = sp.Integer(int(value))
    return env


def run_one(req: dict):
    op = req.get("op")
    variables = req.get("variables", [])
    env = _symbols(variables)

    try:
        if op == "identity":
            lhs = _parse(str(req["lhs"]), env)
            rhs = _parse(str(req["rhs"]), env)
            residual = sp.simplify(lhs - rhs)
            return {"ok": True, "op": op, "verified": bool(residual == 0), "residual": str(residual)}

        if op == "simplify":
            expr = _parse(str(req["expr"]), env)
            return {"ok": True, "op": op, "result": str(sp.simplify(expr))}

        if op == "expand":
            expr = _parse(str(req["expr"]), env)
            return {"ok": True, "op": op, "result": str(sp.expand(expr))}

        if op == "factor":
            expr = _parse(str(req["expr"]), env)
            return {"ok": True, "op": op, "result": str(sp.factor(expr))}

        if op == "mod_pow":
            base, exp, mod = int(req["base"]), int(req["exp"]), int(req["mod"])
            if exp < 0 or mod <= 0:
                raise ValueError("Require exp>=0 and mod>0")
            return {"ok": True, "op": op, "result": pow(base, exp, mod)}

        if op == "gcd":
            return {"ok": True, "op": op, "result": math.gcd(int(req["a"]), int(req["b"]))}

        if op == "factorint":
            n = int(req["n"])
            if abs(n) > 10**18:
                raise ValueError("factorint input too large")
            return {"ok": True, "op": op, "result": {str(k): int(v) for k, v in sp.factorint(n).items()}}

        if op == "valuation_int":
            return {"ok": True, "op": op, "result": _valuation_int(int(req["n"]), int(req["p"]))}

        if op == "valuation_factorial":
            return {"ok": True, "op": op, "result": _valuation_factorial(int(req["n"]), int(req["p"]))}

        if op == "binomial":
            n, k = int(req["n"]), int(req["k"])
            if n < 0 or k < 0 or k > n or n > 2_000_000:
                raise ValueError("Unsafe/invalid binomial arguments")
            return {"ok": True, "op": op, "result": int(sp.binomial(n, k))}

        if op == "totient":
            n = int(req["n"])
            if not (1 <= n <= 10**18):
                raise ValueError("Unsafe/invalid totient input")
            return {"ok": True, "op": op, "result": int(sp.totient(n))}

        if op == "check_expression_value":
            nenv = _numeric_env(req.get("assignments", {}))
            expr = _parse(str(req["expr"]), nenv)
            expected = sp.Integer(int(req["expected"]))
            value = sp.simplify(expr)
            verified = bool(value == expected)
            return {
                "ok": True, "op": op, "verified": verified,
                "value": str(value), "expected": int(expected),
                "answer_bound": False,
            }

        if op == "check_equalities":
            nenv = _numeric_env(req.get("assignments", {}))
            equalities = req.get("equalities", [])
            if not isinstance(equalities, list) or not equalities:
                raise ValueError("equalities must be a non-empty list")
            checks = []
            all_ok = True
            for item in equalities:
                if not isinstance(item, dict) or "lhs" not in item or "rhs" not in item:
                    raise ValueError("each equality must contain lhs and rhs")
                lhs = _parse(str(item["lhs"]), nenv)
                rhs = _parse(str(item["rhs"]), nenv)
                residual = sp.simplify(lhs - rhs)
                ok = bool(residual == 0)
                all_ok = all_ok and ok
                checks.append({
                    "lhs": str(item["lhs"]), "rhs": str(item["rhs"]),
                    "verified": ok, "residual": str(residual),
                })

            answer_check = None
            if req.get("answer_expr") is not None and req.get("expected_answer") is not None:
                value = sp.simplify(_parse(str(req["answer_expr"]), nenv))
                expected = sp.Integer(int(req["expected_answer"]))
                answer_ok = bool(value == expected)
                all_ok = all_ok and answer_ok
                answer_check = {
                    "expr": str(req["answer_expr"]), "value": str(value),
                    "expected_answer": int(expected), "verified": answer_ok,
                }

            return {
                "ok": True, "op": op, "verified": all_ok,
                "assignments": {k: int(v) for k, v in req.get("assignments", {}).items()},
                "checks": checks, "answer_check": answer_check,
                "answer_bound": bool(answer_check is not None and checks),
            }

        return {"ok": False, "op": op, "error": "Operation not allowed"}

    except Exception as e:
        return {"ok": False, "op": op, "error": str(e)[:500]}


def run_tool_requests(requests: list[dict], max_requests: int, allowed_ops: list[str]):
    reports = []
    for req in (requests or [])[:max_requests]:
        if req.get("op") not in allowed_ops:
            reports.append({"ok": False, "op": req.get("op"), "error": "Operation not allowed by config"})
            continue
        reports.append(run_one(req))
    return reports
