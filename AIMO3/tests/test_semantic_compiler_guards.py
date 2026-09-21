from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.semantic_constraints import compile_semantic_formalization, solve_compiled_system, semantic_certificate_ok

PROBLEM = """Alice and Bob are each holding some integer number of sweets. Alice says to Bob:
“If we each added the number of sweets we're holding to our positive integer age, my answer
would be double yours. If we took the product, then my answer would be four times yours.”
Bob replies: “Why don't you give me five of your sweets because then both our sum and product
would be equal.” What is the product of Alice and Bob's ages?"""

BASE = {
    "parse_ok": True,
    "entities": ["Alice", "Bob"],
    "variables": [
        {"name":"a","owner":"Alice","kind":"sweets","domain":"integer"},
        {"name":"b","owner":"Bob","kind":"sweets","domain":"integer"},
        {"name":"x","owner":"Alice","kind":"age","domain":"positive integer"},
        {"name":"y","owner":"Bob","kind":"age","domain":"positive integer"},
    ],
    "pre_relations": [
        {"type":"sum_ratio","left":"Alice","right":"Bob","factor":2,"operands":["age","sweets"]},
        {"type":"product_ratio","left":"Alice","right":"Bob","factor":4,"operands":["age","sweets"]},
    ],
    "post_equalities": [
        {"type":"sum_equal","left":"Alice","right":"Bob","operands":["age","sweets"]},
        {"type":"product_equal","left":"Alice","right":"Bob","operands":["age","sweets"]},
    ],
    "goal": {"type":"product","terms":["Alice.age","Bob.age"]},
    "ambiguity": "NONE",
}

okf = dict(BASE)
okf["events"] = [{"type":"transfer","asset":"sweets","amount":5,"from":"Alice","to":"Bob"}]
c = compile_semantic_formalization(PROBLEM, okf).to_dict()
assert c["ok"] is True, c
assert semantic_certificate_ok(c) is True, c
assert c["equations"] == [
    "(x+a)=2*(y+b)",
    "(x)*(a)=4*(y)*(b)",
    "(x+(a-5))=(y+(b+5))",
    "(x)*((a-5))=(y)*((b+5))",
], c["equations"]
s = solve_compiled_system(c)
assert s["unique_answer"] is True and s["answer"] == 50, s

wrong = dict(BASE)
wrong["events"] = [{"type":"transfer","asset":"sweets","amount":5,"from":"Bob","to":"Alice"}]
c2 = compile_semantic_formalization(PROBLEM, wrong).to_dict()
assert c2["ok"] is False, c2
assert "transfer event disagrees" in c2["reason"], c2

wrong_factor = dict(BASE)
wrong_factor["events"] = okf["events"]
wrong_factor["pre_relations"] = [
    {"type":"sum_ratio","left":"Alice","right":"Bob","factor":3,"operands":["age","sweets"]},
    {"type":"product_ratio","left":"Alice","right":"Bob","factor":4,"operands":["age","sweets"]},
]
c3 = compile_semantic_formalization(PROBLEM, wrong_factor).to_dict()
assert c3["ok"] is False, c3
assert "relation factors/types" in c3["reason"], c3
print("test_semantic_compiler_guards: PASS")
