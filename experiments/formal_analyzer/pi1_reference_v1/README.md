# Formal Analyzer π1 Reference Experiment V1

This directory is the machine-readable and maintenance-facing archive for the first complete Formal Analyzer V2 reference run.

## Canonical identities

- Reference round: `FORMAL_ANALYZER_PI1_REFERENCE_V1`
- Policy version: `P4-R1-Q2-BAD-TRAIN17`
- Actual Formal Main execution code head: `0529efa4b4c896f3855a4634c7daa3a3559e3a89`
- Canonical post-experiment Analyzer head: `17201a462d24985e195a5bb225e388bd9cb9089e`
- Formal DAG V2: `71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`
- Round Evidence: `d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

## Final execution summary

### Local stage
- 30 Formal Main A0 results accepted.
- 30 Formal Main A1 results accepted.
- 60/60 local normalized rows accepted.

### Failure/group materialization
- 30 Main A1 trajectories.
- 71 error instances.
- 58 deterministic groups.
- 30 source-closed groups.
- 37 memberships.
- 30 unique Formal source states.
- group sizes: 25 x 1, 3 x 2, 2 x 3.
- 5 multi-member groups; all 5 span multiple source/task/gamefile units.

### A3 Memory
- 30 group Memory packs.
- 37 member Memory queries.
- 25 singleton groups.
- 5 multi-member groups.
- no cross-member retrieval fusion.
- no hand selection.
- no singleton flattening.

### A2/A3 offline causal fairness
- 30 A2/A3 pairs.
- 60 rendered G requests.
- A2 Memory exposure count: 0.
- A3 Memory pack count: 30.
- A2/A3 common-input equality: 30/30.
- maximum rendered request size: 115,513 bytes.

### Formal G
Batch: `batch_6a9118638eac8190a431ddfbab4f7f0a`
- completed 60;
- failed 0;
- validated 60/60.

### Formal X
Batch: `batch_6a91192f92508190a60f88d8780fb7ea`
- completed 60;
- failed 0;
- validated 60/60.

### Candidate projection
- source states: 30;
- K1 collision count: 0;
- selected executable candidate states: A2=30, A3=30;
- Benefit/Harm labels: not assigned;
- environment verification: not performed.

## Correct interpretation

The result `A2=30 selected` and `A3=30 selected` does **not** establish that Memory improves repair quality. It establishes complete, collision-free candidate coverage after G+X under both conditions. The causal comparison requires later same-state F0/F1 outcomes.

No Formal Analyzer result in this archive should be labeled Benefit/Harm/Neutral/Uncertain.

## Boundary

The run ended at:

`NEXT_GATE=HUMAN_TRAINING_RESEARCHER_PRE`

with:
- Human PRE absent;
- API Researcher PRE shadow absent;
- environment call count 0;
- F0/F1 count 0;
- automatic scientific retry count 0.

This is intentional. Human Researcher PRE must consume a frozen Round Evidence package, not partially evolving Analyzer state.

## Files in this directory

### Scientific/run identity
- `EXPERIMENT_MANIFEST.json`: machine-readable scientific identity and complete reference-run summary.
- `RESULT_MANIFEST.json`: machine-readable final result and explicit claim-boundary summary.

### Code and method inventory
- `CODE_ASSET_MANIFEST.json`: complete reference map of Analyzer/runtime/Memory-interface code, schemas, prompts, design docs, scripts and key tests.
- `ORCHESTRATION_PACKAGE_V1_1.md`: exact identity and successful behavior of the final V1.1 execution harness.

### Data/artifact provenance
- `DATA_ASSET_MANIFEST.json`: machine-readable server asset roots, canonical status and release-archive requirements.
- `ARTIFACT_INDEX.md`: human-readable detailed absolute paths and provenance.
- `REMOTE_ARCHIVE_COMPLETENESS_V1.md`: release gate defining exactly what still must be copied off the HPC filesystem before server-independent archival can be declared complete.

### Release
- `RELEASE_NOTES.md`: release-facing summary for `formal-analyzer-pi1-reference-v1.0`.

### Exact orchestration source
Required final location after server-side import:

`orchestration_v1_1/`

It must contain the exact source files from the successful server package and pass that package's original `SHA256SUMS.txt`. The original ZIP is additionally retained as a release asset.

## Canonical design documentation

Start with:
- `docs/analyzer/FORMAL_ANALYZER_V2_CANONICAL_ARCHIVE_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_ARCHITECTURE_CODE_MAP_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_FIELD_SCHEMA_REFERENCE_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_EXPERIMENT_PROTOCOL_RESULTS_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_MAINTENANCE_INVARIANTS_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_BRANCH_CONSOLIDATION_V1.md`

## Reproduction rule

For scientific reproduction, bind the actual execution head `0529efa...` and the exact experiment manifests/artifacts listed here. The archive branch is based on the later post-experiment head `17201a...` so future maintenance includes explicit state-K1 infrastructure; that later code must not be represented as the code used for the original G/X run.

## Remote archival rule

Git must contain the complete readable method definition: design, final code, runtime, schemas, prompts, tests, protocol and exact orchestration source.

A separate release asset must contain the byte-level generated scientific snapshot needed to independently re-audit the run after the current server paths disappear. Until that release archive is verified, the archive is scientifically indexed but not yet fully server-independent.
