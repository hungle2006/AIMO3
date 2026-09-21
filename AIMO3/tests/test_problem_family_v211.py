from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.problem_family import classify_problem_family
CASES=[
('Define a function f by f(n)=sum_{i=1}^{n} sum_{j=1}^{n} j^{1024} floor((1)/(j)+(n-i)/(n)). Let k be the largest non-negative integer such that 2^{k} divides N.','floor_sum_valuation'),
('On a blackboard choose a base-b representation m = sum_{k=0}^{∞} a_k b^k and replace m by its digit sum. Find the largest possible number of moves.','adaptive_digit_sum_dynamics'),
('A function alpha is called shifty. Define a shift operator S_n and alpha ⋆ beta = sum_{n∈Z} alpha(n) beta(n).','finite_sequence_correlation'),
('A positive integer is n-Norwegian. Let f(n) denote the smallest n-Norwegian and define g(c); write the sum as p/q where p and q are coprime positive integers.','divisor_minimization_asymptotic'),
]
for text,expected in CASES:
    got=classify_problem_family(text,{'domain':'number_theory'})
    assert got==expected,(got,expected,text)
print('test_problem_family_v211: PASS')
