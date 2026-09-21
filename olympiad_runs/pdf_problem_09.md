# pdf_problem_09

## Problem

Let F be the set of functions α: Z →Z for which there are only finitely many n ∈Z
such that α(n)̸ = 0.
For two functions α and β in F, define their product α ⋆ β to be sum_{n∈Z} α(n)·β(n). Also, for n ∈ Z, define a shift operator S_{n}: F → F by S_{n}(α)(t) = α(t + n) for all t ∈ Z.
A function α ∈F is called shifty if
• α(m) = 0 for all integers m < 0 and m > 8 and
• There exists β ∈F and integers k̸ = l such that for all n ∈Z
(
S_{n}(α) ⋆β =
1
n ∈{k, l}
0
n̸ ∈{k, l} ^{.}
How many shifty functions are there in F?

## Run summary

- Status: `VERIFIED_PASS`
- Candidate answer: `160`
- Verified answer: `160`
- Verification: `FAMILY_EXACT` passed=`True`
- Difficulty: `0.82` (hard)
- RAG: used=`False` gate=`NOT_USED`
- Model calls: `0`
- Total tokens: `0`
- Latency: `0.06s`
- Critic: `NOT_NEEDED` confidence=`None`

## Interpretation

Deterministic family engine: finite_correlation_polynomial

## Best proof

Encode alpha and beta by a polynomial P_alpha and a finite Laurent polynomial Q_beta. The shifted inner products are exactly the coefficients of P_alpha Q_beta, so the shifty condition is equivalent to P_alpha dividing x^k+x^l, hence x^a(x^b+1). Cyclotomic factorization makes every non-monomial divisor a signed monomial times a subset of cyclotomic factors whose indices have one common positive 2-adic valuation. Since deg P<=D, only Phi_d with phi(d)<=D can occur. The engine enumerates all such indices using a certified totient bound, constructs every signed divisor of degree at most D, deduplicates coefficient vectors, and returns the exact count.

## Candidate answer

160

## Verified answer

160

## Verification reason

exact correlation-to-polynomial reduction + cyclotomic enumeration
