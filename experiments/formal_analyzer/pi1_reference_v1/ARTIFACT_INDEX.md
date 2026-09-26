# Formal Analyzer π1 Reference — Artifact and Path Index V1

This file records the server-side scientific assets that produced the π1 Formal Analyzer reference result. Paths are provenance, not portable configuration. Future migrations should preserve semantic/file SHA identities and update path mappings explicitly.

## 1. Repository/worktree

Actual Formal Main execution worktree:

`/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-formal-act3-canonical-pack-hardening-v1`

Execution HEAD:

`0529efa4b4c896f3855a4634c7daa3a3559e3a89`

Canonical post-experiment code head:

`17201a462d24985e195a5bb225e388bd9cb9089e`

## 2. Fresh π1 collection

Primary build root:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_fresh_pi1_collection_build_v1`

Run01 mirror/related root when present:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_analyzer_fresh_pi1_collection_build_v1`

Scientific census:
- 48 executed failure trajectories;
- frozen first 42 selected;
- 12 pilot + 30 Main.

## 3. Formal A0/A1 preparation and runtime registry

Preparation root:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_selected42_evidence_a0a1_preparation_v1`

Formal Main local runtime registry:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_selected42_evidence_a0a1_preparation_v1/_run_state/formal_selected42_prepared/main/runtime_registry_formal_main_a0a1.json`

Registry SHA:

`8a91904f9f264dac9d13ffde2dbe4303120c0a795ffbd463351a902d4a227a40`

## 4. Formal Main batch import

Transport root:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_batch_transport_v2_round_continuation_v1`

Main handoff:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_batch_transport_v2_round_continuation_v1/_run_state/FORMAL_MAIN_LOCAL_RESULTS_HANDOFF_V1.json`

Normalized Main import manifest:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_batch_transport_v2_round_continuation_v1/_run_state/main_batch_import/normalized_execution_manifest.json`

Per-result directories under:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_batch_transport_v2_round_continuation_v1/_run_state/main_batch_import/`

Each accepted local unit contains at least:
- `batch_output_row.json`;
- `raw_response.json`;
- `validated_artifact.json`.

Final local census: 60 accepted = 30 A0 + 30 A1.

## 5. Main A1 local-results materialization

Root:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_main_a1_group_materialization_v1`

Current source-closure input:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_main_a1_group_materialization_v1/_run_state/group_binding_discovery/local_results.json`

This exact 30-object A1 identity set is the authority used by source closure.

## 6. Corrected Formal source closure

Root:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_act3_registration_hardening_and_source_materialization_v1/_run_state/corrected_source_closure`

Key files:
- `FORMAL_ACT3_REGISTRATION_CLOSURE_V2.json`
- `FORMAL_ACT3_SOURCE_CLOSURE_ROWS_V2.json`
- `FORMAL_EXACT_SOURCE_BINDINGS_V1.json`
- `FORMAL_SOURCE_CONTEXTS_V1.json`
- `ANALYZER_SOURCE_CLOSED_GROUPS_V1.json`
- `ANALYZER_SOURCE_CLOSED_GROUP_SYNTHESIS_INPUTS_V1.json`

Final census:
- 71 error instances;
- 58 deterministic groups;
- 30 source-closed groups;
- 37 memberships;
- 30 unique source states.

## 7. Post-Main exact A1 path freeze

Freeze manifest:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_postlocal_group_x_human_researcher_bridge_v1/_run_state/FORMAL_MAIN_POSTLOCAL_INPUT_FREEZE_V1.json`

This manifest binds the 30 current Main `local_result_sha256` identities to exact existing `validated_artifact.json` paths and file SHA256 values. It does not duplicate the artifacts.

Final audit:
- A1 result count = 30;
- unique count = 30;
- missing = [];
- extra = [].

## 8. Frozen Failure Memory snapshot used by A3

Memory calibration root:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/failure_memory_token_budget_calibration_v1`

Frozen active snapshot:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/failure_memory_token_budget_calibration_v1/active_snapshots/8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189`

Snapshot SHA:

`8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189`

Historical sealed ACT3 materializer source:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_act3_exact_old_materializer_seal_and_current_compat_v6/evidence/SEALED_OLD_ACT3_MEMORY_MATERIALIZER_SOURCE.py`

Sealed source SHA:

`80a0f2512bde26914ba97b1687e433220b016fc13fec3f012e2179c9b7689658`

## 9. Formal Main A3 Memory restore

Result root:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_main_a3_group_memory_semantics_restore_v1_results/fixed_0944e3c5a172f3b30431d142a4b53a9c113bd0a1f9a473c35a38bcfbad16e057`

Restore identity:

`0944e3c5a172f3b30431d142a4b53a9c113bd0a1f9a473c35a38bcfbad16e057`

Key contents:
- `RESTORE_SUMMARY_V1.json`;
- `ANALYZER_MEMORY_RETRIEVAL_MANIFEST_V1.json`;
- `ANALYZER_MEMBER_MEMORY_VIEWS_V1.jsonl`;
- `group_bundles/`;
- `memory_packs/`.

Final audit:
- 30 packs;
- 37 member queries;
- 25 singleton groups;
- 5 multi-member groups;
- no retrieval fusion/hand selection/singleton flattening.

## 10. Formal A2/A3 offline materialization

Root:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_main_a2a3_offline_materialization_v1`

Key contents:
- `a2_projections/`;
- `a3_projections/`;
- `group_manifests/`;
- `group_synthesis_inputs/`;
- `rendered_requests/`;
- `A2_A3_PAIR_AUDIT.json`;
- `REQUEST_PREFLIGHT.json`.

Final audit:
- 30 pairs;
- 60 requests;
- 30/30 common-input equality;
- A2 Memory exposure 0;
- A3 Memory count 30;
- max rendered request 115,513 bytes.

## 11. Formal G/X execution and final Analyzer boundary

State root:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_analyzer_to_human_researcher_pre_boundary_v1_1_state`

### Stage 1 — group registry + Formal DAG

Directory:

`01_offline_registry_dag/`

Formal DAG SHA:

`71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`

### Stage 2 — Formal G A2/A3

Directory:

`02_formal_g_batch/`

Batch ID:

`batch_6a9118638eac8190a431ddfbab4f7f0a`

Result: 60/60 validated.

### Stage 3 — Formal X

Directory:

`03_formal_x_batch/`

Batch ID:

`batch_6a91192f92508190a60f88d8780fb7ea`

Result: 60/60 validated.

### Stage 4 — deterministic candidate projector

Directory:

`04_candidate_projector/`

Key artifact:

`FORMAL_ANALYZER_CANDIDATE_POOL_V1.json`

Result:
- 30 source states;
- 60 state-condition rows;
- K1 collisions 0;
- selected A2 candidates 30;
- selected A3 candidates 30;
- no environment verification/Benefit-Harm labels.

### Stage 5 — Round Evidence seal

Directory:

`05_round_evidence_seal/`

Final package:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_analyzer_to_human_researcher_pre_boundary_v1_1_state/05_round_evidence_seal/ROUND_EVIDENCE_PACKAGE_V1.json`

Semantic SHA:

`d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

Boundary:

`NEXT_GATE=HUMAN_TRAINING_RESEARCHER_PRE`

## 12. Runtime logs

Boundary package logs:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_to_human_researcher_pre_boundary_v1_logs/`

These logs are useful for forensic transport reconstruction but are not the scientific result authority when a validated semantic artifact/manifest exists.

## 13. Archive classification

### Commit to Git
Keep in Git:
- code;
- prompts;
- schemas;
- design docs;
- compact experiment manifests;
- semantic hashes;
- artifact indexes;
- maintenance invariants.

### Keep out of normal Git history
Do not blindly commit:
- raw provider response bodies;
- full Batch output/error JSONL files;
- duplicate rendered request trees;
- large repeated projections;
- logs;
- temporary ZIP delivery packages;
- transient `_run_state` directories.

These may be packaged into a separate immutable release asset with a SHA256 inventory if long-term off-cluster preservation is required.

## 14. Migration rule

If these absolute paths change, a migration manifest must map each old logical artifact to its new path and preserve/check its file SHA or semantic SHA. Do not edit this historical index to pretend the original execution happened somewhere else.