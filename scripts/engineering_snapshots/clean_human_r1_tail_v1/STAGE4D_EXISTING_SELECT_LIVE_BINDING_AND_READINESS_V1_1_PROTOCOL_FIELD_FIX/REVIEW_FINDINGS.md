# Exact Stage4C Review Findings

The uploaded read-only handoff was independently re-hashed as:

`d5ef890b5da18f218600502ee5b41bcbcfbb21af4aa63d1e05900cea4c2ec9bd`

ZIP integrity passed.

The fixed source and upstream bindings support the following Stage4D reuse plan:

- preserve fixed head/tree/protocol and exact 355 x 5 x 2 grid;
- use existing typed SELECT server/policy/condition/schedule classes;
- use existing I1 SELECT execution profile;
- use existing ALFWorld runtime manifest contract;
- use existing episode evaluator and result audit;
- statically serve clean base plus the exact T2 LoRA;
- keep dynamic LoRA updates disabled;
- keep scientific execution unauthorized during readiness.

The export contained 10 omissions. They are Failure-Memory/support artifacts marked for possible embedded secrets plus one historical reuse-census JSON; none is a core Stage4C SELECT protocol/runtime/evaluator/candidate/schedule source required by this readiness package.

Important identity correction applied by this package:

- Research Planner training-plan SHA remains `ac04690c...` as planning authority.
- `PolicyConditionManifestV1.training_config_sha256` is bound to the actual frozen training contract SHA `fa0c49b9...`, not to the Research Planner plan SHA.


## V1.1 bounded correction

V1 failed before any Slurm submission because it looked up `grid["paired_task_seed_cells"]`. The frozen Stage4C protocol canonically stores the grid count as `grid["paired_cells"]`; `paired_task_seed_cells` exists only in the earlier preflight receipt. V1.1 reads only the canonical Stage4C field and additionally verifies the exact `pairs` product/order. No scientific count, seed, task, candidate, protocol hash, path root, or execution authority is changed.
