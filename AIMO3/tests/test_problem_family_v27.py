from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.problem_family import classify_problem_family

cases = [
    ("Let f be a function such that for all positive integers m,n, f(m)+f(n)=f(m+n+mn).", {"domain":"number_theory"}, "functional_equation"),
    ("A square is divided into rectangles with distinct perimeters. Find the largest possible number.", {"domain":"geometry"}, "extremal_partition"),
    ("A tournament has many runners paired each round by equal score; count possible final orderings.", {"domain":"number_theory"}, "combinatorial_process"),
    ("Triangle ABC has two circles intersecting again at Y; prove a geometric condition.", {"domain":"geometry"}, "euclidean_geometry"),
]
for problem, analysis, expected in cases:
    got = classify_problem_family(problem, analysis)
    assert got == expected, (problem, got, expected)
print("test_problem_family_v27: PASS")
