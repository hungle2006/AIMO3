from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_norwegian_divisor_asymptotic
from core.target_spec import extract_target_spec
P='''Let n ≥6 be a positive integer. We call a positive integer n-Norwegian if it has three distinct positive divisors whose sum is equal to n. Let f(n) denote the smallest n-Norwegian positive integer. Let M = 3^{2025!} and for a non-negative integer c define g(c) = (1)/(2025!) * floor((2025! * f(M + c))/(M)). We can write g(0) + g(4M) + g(1848374) + g(10162574) + g(265710644) + g(44636594) = (p)/(q) where p and q are coprime positive integers. What is the remainder when p + q is divided by 99991?'''
r=solve_norwegian_divisor_asymptotic(P,extract_target_spec(P))
assert r.supported and r.ok,r
assert str(r.certificate['sum'])=='125561848/19033825',r.certificate
assert r.answer==8687,r
print('test_family_engine_norwegian_v211: PASS')
