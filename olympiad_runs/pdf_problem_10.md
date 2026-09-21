# pdf_problem_10

## Problem

Let n ≥6 be a positive integer. We call a positive integer n-Norwegian if it has three distinct positive divisors whose sum is equal to n. Let f(n) denote the smallest n-Norwegian positive
integer. Let M = 3^{2025!}and for a non-negative integer c define
) floor(2025!f(M + c).
g(c) = (1)/(2025!) * floor((2025! * f(M + c))/(M)).
We can write g(0) + g(4M) + g(1848374) + g(10162574) + g(265710644) + g(44636594) = (p)/(q) where p and q are coprime positive integers. What is the remainder when p + q is divided by 99991?

## Run summary

- Status: `VERIFIED_PASS`
- Candidate answer: `8687`
- Verified answer: `8687`
- Verification: `FAMILY_EXACT` passed=`True`
- Difficulty: `0.84` (hard)
- RAG: used=`False` gate=`NOT_USED`
- Model calls: `0`
- Total tokens: `0`
- Latency: `0.00s`
- Critic: `NOT_NEEDED` confidence=`None`

## Interpretation

Deterministic family engine: norwegian_divisor_asymptotic

## Best proof

Classify the smallest n-Norwegian integer for odd n by maximizing the reciprocal sum of three divisor quotients. The only optimal cases reduce to explicit ratios determined by divisibility by 9 or 25 and the smallest prime divisors congruent to 1 or 5 modulo 6. For M=3^(r!), Euler's theorem gives M=1 modulo every small modulus coprime to 3, so each required small divisor of M+c is determined exactly from 1+c without constructing M. The engine selects the certified ratio f(M+c)/(M+c), proves the residual term inside the floor is below 1, extracts each rational g(c), sums them with Fraction, reduces p/q, and computes the requested remainder of p+q exactly.

## Candidate answer

8687

## Verified answer

8687

## Verification reason

exact divisor classification + modular small-factor transfer + exact floor extraction
