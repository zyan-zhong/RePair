# Formal Analyzer π1 Reference V1.0 — Release Notes

## Scope

This release freezes the first complete Formal Analyzer V2 π1 reference system and experiment, ending immediately before `HUMAN_TRAINING_RESEARCHER_PRE`.

## Code identities

- Actual Formal Main G/X execution head: `0529efa4b4c896f3855a4634c7daa3a3559e3a89`
- Canonical post-experiment Analyzer head: `17201a462d24985e195a5bb225e388bd9cb9089e`
- Consolidated archive/main release commit: use the commit containing this file.

## Scientific result identities

- Formal DAG V2: `71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`
- G Batch: `batch_6a9118638eac8190a431ddfbab4f7f0a` — 60/60 validated
- X Batch: `batch_6a91192f92508190a60f88d8780fb7ea` — 60/60 validated
- Formal source states: 30
- K1 collisions: 0
- selected candidate states: A2=30, A3=30
- Round Evidence SHA: `d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`
- environment/F0F1 execution in this release: none

## Final dataset/group census

- 48 fresh π1 failure trajectories collected
- first 42 frozen by pre-registered order
- 12 pilot + 30 Main
- 30 Main A1 trajectories
- 71 error instances
- 58 deterministic groups
- 30 source-closed groups
- 37 memberships
- group sizes: 25 x 1, 3 x 2, 2 x 3
- 5 multi-member groups, all cross-source/task/gamefile

## A3 Memory

- frozen snapshot: `8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189`
- 30 group Memory packs
- 37 member queries
- no cross-member retrieval fusion
- no hand selection
- no singleton flattening

## A2/A3 causal fairness

- 30 paired A2/A3 group inputs
- 30/30 common-input equality after removing Memory
- A2 Memory exposure: 0
- A3 Memory packs: 30
- 60 rendered G requests

## Orchestration asset

Recommended release asset:

`formal_analyzer_to_human_researcher_pre_boundary_v1_1.zip`

SHA-256:

`18a165518d498138853dc04b20f1d03ebddd9552797d3301eba2d6aee1750f52`

The package is a historical execution harness and should be attached as a release asset rather than treated as a production runtime module.

## Documentation entry points

- `docs/analyzer/README.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_CANONICAL_ARCHIVE_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_MAINTENANCE_INVARIANTS_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_BRANCH_CONSOLIDATION_V1.md`
- `experiments/formal_analyzer/pi1_reference_v1/EXPERIMENT_MANIFEST.json`
- `experiments/formal_analyzer/pi1_reference_v1/ARTIFACT_INDEX.md`
- `experiments/formal_analyzer/pi1_reference_v1/ORCHESTRATION_PACKAGE_V1_1.md`

## Scientific interpretation boundary

This release proves that the Formal Analyzer pipeline executes with full G/X validation coverage and collision-free source-state candidate projection under both A2 and A3. It does **not** prove A3/Memory is beneficial. Benefit/Harm/Neutral/Uncertain requires the next independent same-state F0/F1 verification stage.

## Next gate

`HUMAN_TRAINING_RESEARCHER_PRE`
