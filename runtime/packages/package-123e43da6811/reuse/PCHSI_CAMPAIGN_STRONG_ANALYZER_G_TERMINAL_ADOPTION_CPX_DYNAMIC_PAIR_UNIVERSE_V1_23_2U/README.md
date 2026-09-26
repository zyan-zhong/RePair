# V1.23.2U — Strong Analyzer G Terminal Adoption + C/P/X + Dynamic Pair Universe

Recovery for the V1232T post-G aggregation wrapper failure.

## What is reused
- V1232R1 complete-pair/group-prep authority.
- The exact V1232T activation root and its already-terminal G-A2/G-A3 call directories.
- Existing Analyzer Memory, `group_projection_v3`, C/P/X runtime, candidate projection, K<=1, and source-context equivalence assets.

## What is forbidden
- No G-A2/G-A3 resend.
- No retry of `AMBIGUOUS_POST_SEND`.
- No replacement/top-up groups.
- No environment execution, F0/F1, training, or Slurm.
- No fixed live cardinalities.

## Root cause repaired
V1232T stores group-stage results in the per-group record as `A2` / `A3`, while its C-stage loop incorrectly indexed those records using `G-A2` / `G-A3`. V1232U introduces one explicit stage-ID → record-key bridge and regression-tests it.

## Recovery semantics
V1232U recomputes the exact V1232T activation path, requires that root to already exist, verifies and adopts each terminal G logical call by exact request/unit identities, and only then continues C/P/X. Missing G calls fail closed rather than triggering provider execution.
