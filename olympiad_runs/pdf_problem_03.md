# pdf_problem_03

## Problem

Let ABC be an acute-angled triangle with integer side lengths and AB < AC. Points D and E lie on segments BC and AC, respectively, such that AD = AE = AB. Line DE intersects AB at X. Circles BXD and CED intersect for the second time at Y̸ = D. Suppose that Y lies on line AD. There is a unique such triangle with minimal perimeter. This triangle has side lengths a = BC, b = CA, and c = AB. Find the remainder when abc is divided by 10^{5}.

## Run summary

- Status: `VERIFIED_PASS`
- Candidate answer: `336`
- Verified answer: `336`
- Verification: `FAMILY_EXACT` passed=`True`
- Difficulty: `0.5906666666666667` (medium)
- RAG: used=`False` gate=`NOT_USED`
- Model calls: `0`
- Total tokens: `0`
- Latency: `0.00s`
- Critic: `NOT_NEEDED` confidence=`None`

## Interpretation

Deterministic family engine: radical_axis_angle_bisector_triangle

## Best proof

Because Y and D are the two common points of circles BXD and CED and Y lies on AD, A lies on their radical axis. Equal powers give AB·AX=AE·AC, hence AX=AC because AE=AB. The resulting reflection across the A-angle bisector shows that D is exactly the internal angle-bisector point; conversely this condition is sufficient. The angle-bisector theorem and Stewart reduce the configuration exactly to a^2 b=(b+c)^2(b-c), with a=BC,b=CA,c=AB and c<b. The engine then exhaustively checked every positive labeled integer triple of smaller perimeter and found none; at perimeter 21 it found the unique admissible acute triple (7, 8, 6). A second exact certificate verifies AD=AB, equal powers at A, and the coprime parameterization before computing abc and applying the requested modulus.

## Candidate answer

336

## Verified answer

336

## Verification reason

exact radical-axis reduction + exhaustive minimal-perimeter search
