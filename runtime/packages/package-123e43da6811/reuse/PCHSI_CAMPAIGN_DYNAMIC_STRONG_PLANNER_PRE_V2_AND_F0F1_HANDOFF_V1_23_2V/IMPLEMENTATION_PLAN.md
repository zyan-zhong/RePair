# V1232V Implementation Plan

## Goal

Continue from the live V1232U Analyzer-tail terminal into the existing Dynamic Strong Planner PRE V2 contract, then freeze a planner-bound current-round F0/F1 launch handoff. This package intentionally does not run ALFWorld branches or training: the selected state universe does not exist until PRE is accepted.

## Pipeline

`V1232U dynamic pair universe -> representation-only PRE V2 view -> current round-start Researcher Memory authority -> Dynamic PRE V2 contract -> one Strong PRE logical call -> deterministic normalization only if redundant derived fields are wrong -> selected state/candidate portfolio -> planner-bound F0/F1 state x seed x arm handoff`.

## No-retry semantics

- Exact accepted PRE terminal already present: reuse, zero provider resend.
- Existing non-accepted PRE terminal: fail closed, zero resend.
- Existing partial/nonterminal call directory: fail closed as unsafe ambiguity.
- New call: at most one `execute_one()` logical call.
- No automatic provider retry is introduced by this package.

## Dynamic authority

No current-round pair count, selected state count, or branch-run budget is hard-coded. The PRE contract derives its review count and selection ceiling from the V1232U pair table. F0/F1 branch budget is derived only after PRE from selected states and the frozen role-neutral replication protocol.

## Next live edge

On accepted PRE with at least one selected state, the next valid action is current-TRAIN exact-state replay rebind followed by native matched F0/F1 execution and the independent verifier. If PRE selects zero states, route directly to POST/NO_TRAIN governance without inventing verification work.
