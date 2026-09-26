# Formal Analyzer V2 — Architecture and Code Map V1

Status: **FROZEN REFERENCE MAP**  
Reference round: `FORMAL_ANALYZER_PI1_REFERENCE_V1`  
Formal Main execution head: `0529efa4b4c896f3855a4634c7daa3a3559e3a89`  
Canonical post-experiment Analyzer head: `17201a462d24985e195a5bb225e388bd9cb9089e`

This document maps each scientific design element of Formal Analyzer V2 to the concrete repository implementation, schema, prompt, tests, and server-side reference artifacts used by the first complete π1 Formal Analyzer run.

The authoritative high-level description remains `FORMAL_ANALYZER_V2_CANONICAL_ARCHIVE_V1.md`; this file is the maintenance/code-navigation companion.

## 1. End-to-end chain

Reference scientific chain:

`π1 failures -> L-A0/L-A1 -> deterministic grouping/source closure -> G-A2/G-A3 -> X -> deterministic candidate projection -> source-state x condition K<=1 -> ROUND_EVIDENCE_PACKAGE_V1 -> Human Training Researcher PRE`

Later causal chain, outside the Formal Analyzer boundary:

`Human PRE -> same-state F0/F1 -> Benefit/Harm/Neutral/Uncertain -> Human POST -> verified training evidence -> π2`

The Analyzer is an evidence-grounded diagnosis and repair-candidate discovery subsystem. It does not own causal effect labels, environment execution, training-method selection, promotion, or rollback.

## 2. Role/authority map

| Concern | Authority | Primary implementation | Canonical notes |
|---|---|---|---|
| Analyzer scientific role | Analyzer | `src/pchsi/analyzer/authorities.py` | Analyzer diagnoses/proposes/abstains; no Benefit/Harm authority |
| Local Analyzer result construction/validation | Analyzer | `src/pchsi/analyzer/local_results.py`, `src/pchsi/analyzer/schema_contract.py` | Produces `ANALYZER_LOCAL_RESULT_V2` |
| Analysis budget/sampling | Deterministic control | `src/pchsi/analyzer/analysis_budget.py`, `analysis_sampling.py` | Budget is not evidence and cannot change treatment semantics |
| Deterministic grouping | Deterministic | `src/pchsi/analyzer/grouping.py` | No model/human hand grouping |
| Exact source registration / Formal group I/O | Deterministic | `src/pchsi/analyzer/act3_registration.py` | Exact state/menu/call identity; ambiguity fails closed |
| Formal failure collection | Collection/runtime glue | `src/pchsi/analyzer/formal_failure_collection.py` | Used for fresh π1 failure collection |
| Group hypothesis/proposal stage | Analyzer | runtime projection/renderer + G prompt | A2 Memory OFF; A3 same current evidence + Memory |
| X cross-check | Analyzer challenge role | `src/pchsi/analyzer/crosscheck.py`, `src/pchsi/cognitive_runtime/projections.py` | X challenges target; cannot silently rewrite it |
| Proposal -> candidate | Deterministic | `src/pchsi/analyzer/candidate_projector.py` | Candidate projection is not causal validation |
| State-level K<=1 | Deterministic | `src/pchsi/analyzer/state_candidate_budget.py` | Distinct execution-semantic collisions produce no winner |
| Metrics/statistics | Deterministic analysis | `src/pchsi/analyzer/metrics.py`, `metric_registry.py` | Pre-verification metrics must not imply Benefit/Harm |
| Runtime identity/access | Runtime governance | `src/pchsi/cognitive_runtime/identity.py`, `access.py` | Exact scientific-unit and task-access binding |
| Formal DAG V2 | Runtime governance | `src/pchsi/cognitive_runtime/formal_registry_v2.py` | Enforces A0/A1 and A2/A3 paired contracts |
| Projection materialization | Runtime | `src/pchsi/cognitive_runtime/projections.py` | Current-evidence and Memory identities separated |
| Request rendering | Runtime | `src/pchsi/cognitive_runtime/request_renderer.py` | One scientific unit/request, structured output, no tools |
| Provider response parsing | Runtime | `src/pchsi/cognitive_runtime/response.py` | Provider/transport result parsing only |
| Stage output validation | Runtime | `src/pchsi/cognitive_runtime/output_validation.py` | Schema/evidence authority enforcement |
| Runtime orchestration | Runtime | `src/pchsi/cognitive_runtime/orchestrator.py` | No hidden scientific retry |
| Round evidence freeze | Runtime/evidence boundary | `src/pchsi/cognitive_runtime/round_evidence.py` | Final Analyzer-to-Researcher evidence boundary |
| Human/API Researcher records | Researcher boundary | `src/pchsi/cognitive_runtime/researcher.py` | Human PRE starts only after Round Evidence freeze |

## 3. Local stages L-A0 and L-A1

### Design

Both stages use the same registered Formal Main episode/task-gamefile evidence universe.

- `L-A0 / A0`: one-shot local analysis baseline; Memory OFF.
- `L-A1 / A1`: multi-hypothesis local analysis; Memory OFF.
- Pairing must preserve the same underlying task/gamefile scientific unit.
- A1 produces the exact validated local result consumed later by grouping and G.

### Code

- `src/pchsi/analyzer/local_results.py`
- `src/pchsi/analyzer/schema_contract.py`
- `src/pchsi/cognitive_runtime/projections.py`
- `src/pchsi/cognitive_runtime/request_renderer.py`
- `src/pchsi/cognitive_runtime/output_validation.py`
- `src/pchsi/cognitive_runtime/response.py`

### Schemas

- `configs/analyzer/schemas/analyzer_local_result_v2.json`
- `configs/cognitive_runtime/schemas/scientific_unit_identity_v1.json`
- `configs/cognitive_runtime/schemas/runtime_input_registry_v1.json`
- `configs/cognitive_runtime/schemas/runtime_stage_result_v1.json`

### Final prompts used by the frozen runtime manifest

- A0: `prompts/cognitive_runtime/ANALYZER_L_A0_PROMPT_V3.txt`
- A1: `prompts/cognitive_runtime/ANALYZER_L_A1_PROMPT_V3.txt`

Authoritative bindings, including prompt/schema hashes, are in `configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`.

### Main reference artifacts

- preparation root: `/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_selected42_evidence_a0a1_preparation_v1`
- Main local registry: `_run_state/formal_selected42_prepared/main/runtime_registry_formal_main_a0a1.json`
- Main Batch import: `/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_batch_transport_v2_round_continuation_v1/_run_state/main_batch_import`
- result: 30 A0 + 30 A1 accepted/validated local units.

## 4. Error instances, deterministic grouping, and source closure

### Design

A1 failures are decomposed into registered error instances. Grouping is deterministic from frozen signatures; task/gamefile is preserved in each membership rather than used as an ad-hoc post-hoc grouping knob.

Formal Main produced:
- 71 error instances;
- 58 deterministic groups;
- 30 source-closed Formal groups;
- 37 source-closed memberships;
- 30 unique source states;
- group-size census: 25x1, 3x2, 2x3;
- five multi-member groups, all cross-source/task/gamefile.

### Code

- `src/pchsi/analyzer/grouping.py`
- `src/pchsi/analyzer/act3_registration.py`
- CLI/reference scripts:
  - `scripts/analyzer/build_analyzer_groups_v1.py`
  - `scripts/analyzer/run_formal_failure_collection_v1.py`
  - `scripts/analyzer/build_formal_failure_collection_panel_v1.py`

### Schemas

- `configs/analyzer/schemas/analyzer_error_instance_membership_v1.json`
- `configs/analyzer/schemas/analyzer_group_manifest_v1.json`
- `configs/analyzer/schemas/analyzer_group_synthesis_input_v1.json`

### Exact source-binding contract

Each source-conditioned member is bound by the registered identity tuple including:
- `local_result_sha256`;
- `error_instance_id`;
- `source_state_sha256`;
- `menu_sha256`;
- exact source call index / registered source context.

No fuzzy action matching, inferred source call, menu sorting/deduplication, or post-hoc regrouping is allowed.

### Server authority

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/formal_act3_registration_hardening_and_source_materialization_v1/_run_state/corrected_source_closure`

Key files are indexed in `experiments/formal_analyzer/pi1_reference_v1/ARTIFACT_INDEX.md`.

## 5. Group stages G-A2 and G-A3

### Design

A2/A3 are a paired causal-design control over Analyzer historical Memory exposure.

A2:
- same registered group;
- same member bindings;
- same plural A1 validated results;
- same source contexts/current evidence;
- Memory OFF.

A3:
- exactly the same current evidence as A2;
- plus exactly one frozen Analyzer Memory role pack for the group.

Removing `memory_pack` / `memory_pack_sha256` from A3 must yield the A2 common projection.

### Code

- `src/pchsi/cognitive_runtime/projections.py` (`group_projection_v2/v3` lineage)
- `src/pchsi/cognitive_runtime/request_renderer.py`
- `src/pchsi/cognitive_runtime/output_validation.py`
- `src/pchsi/cognitive_runtime/formal_registry_v2.py`
- `src/pchsi/analyzer/act3_registration.py`

### Schemas

- `configs/analyzer/schemas/analyzer_group_result_v2.json`
- `configs/analyzer/schemas/analyzer_source_conditioned_proposal_v1.json`
- `configs/cognitive_runtime/schemas/formal_analyzer_dag_registry_v2.json`

### Final prompts

- A2: `prompts/cognitive_runtime/ANALYZER_G_A2_PROMPT_V4.txt`
- A3: `prompts/cognitive_runtime/ANALYZER_G_A3_PROMPT_V4.txt`

### Formal result field

Current group-result proposal field is `source_conditioned_proposals`. The stale name `source_conditioned_repairs` is not the current contract.

### Main reference result

- 30 A2 projections + 30 A3 projections;
- 30/30 common-input equality;
- A2 Memory exposure count = 0;
- A3 Memory pack count = 30;
- 60/60 G provider results validated.

## 6. A3 Failure Memory interface

Formal Analyzer does not redefine the Failure Memory subsystem; it consumes the already-validated Memory interface.

### Relevant implementation

- `src/pchsi/memory/consumer_views.py`
- `src/pchsi/memory/dev_snapshot_loader.py` when using the frozen descriptive snapshot path
- `src/pchsi/cognitive_runtime/projections.py` for role-pack attachment

### Frozen A3 materialization semantics

`exact member source context -> independent AnalyzerMemoryViewV1 -> group bundle -> one Analyzer role pack`

Frozen rules:
- no hand selection;
- `cross_member_retrieval_fusion=false`;
- singleton groups are not flattened;
- A2 receives no Memory;
- A3 receives the corresponding frozen group pack only;
- Memory does not certify Benefit/Harm.

### Reference snapshot/materialization

- snapshot SHA: `8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189`
- restore identity: `0944e3c5a172f3b30431d142a4b53a9c113bd0a1f9a473c35a38bcfbad16e057`
- 30 group packs / 37 member queries.

## 7. X independent cross-check

### Design

X independently challenges the target G artifact under explicit evidence allowlists.

- X may accept, downgrade, or reject target content according to its schema/contract.
- X may not silently replace the target with a different repair.
- A2 X receives no historical Memory allowlist.
- A3 X historical evidence is limited to the corresponding frozen Memory identity.

### Code

- `src/pchsi/analyzer/crosscheck.py`
- `src/pchsi/cognitive_runtime/projections.py` (`crosscheck_projection_v2` lineage)
- `src/pchsi/cognitive_runtime/request_renderer.py`
- `src/pchsi/cognitive_runtime/output_validation.py`

### Schema/prompt

- schema: `configs/analyzer/schemas/analyzer_crosscheck_result_v1.json`
- prompt: `prompts/cognitive_runtime/ANALYZER_X_PROMPT_V2.txt`

### Main reference result

60 X requests completed, 0 failed, 60/60 validated.

## 8. Deterministic candidate projection and state-level K<=1

### Design

Validated source-conditioned proposals are projected into bounded executable candidate representations. This is deterministic post-processing, not causal verification.

Budget authority is `source_state x condition`:
- zero executable candidates: abstain/no candidate is valid;
- one execution semantics: candidate may advance;
- more than one distinct execution semantics: method-invalid collision/no winner.

### Code

- `src/pchsi/analyzer/candidate_projector.py`
- `src/pchsi/analyzer/state_candidate_budget.py`
- `scripts/analyzer/project_analyzer_candidates_v1.py`

### Schema

- `configs/analyzer/schemas/analyzer_repair_candidate_v1.json`
- `configs/analyzer/schemas/analyzer_source_conditioned_proposal_v1.json`

### Main reference result

- 30 registered source states;
- 60 state-condition outcomes;
- K1 collision count = 0;
- selected executable candidate count: A2=30, A3=30.

This is candidate coverage, not evidence that A3 is causally better than A2. Benefit/Harm remains an F0/F1 environment question.

## 9. Runtime architecture

Authoritative runtime manifest:

`configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`

Frozen runtime properties include:
- provider endpoint `/v1/responses`;
- requested model `gpt-5.6-sol` for the reference runtime;
- one scientific unit per request;
- `store=false`;
- no tools;
- no shared conversation state;
- no `previous_response_id` reuse;
- `truncation=disabled`;
- SDK automatic retries = 0;
- ambiguous post-send automatic retry forbidden.

### Runtime module map

- access governance: `src/pchsi/cognitive_runtime/access.py`
- scientific identity: `identity.py`
- registry/DAG: `formal_registry.py`, `formal_registry_v2.py`
- projection construction: `projections.py`
- request rendering: `request_renderer.py`
- response parsing: `response.py`
- output validation: `output_validation.py`
- orchestration: `orchestrator.py`
- ledgers/manifests: `ledger.py`, `manifest.py`
- schema lookup: `schema_registry.py`
- cross-stage validation: `validation.py`
- round evidence: `round_evidence.py`
- Researcher boundary records: `researcher.py`

## 10. Frozen stage binding table

| Stage | Condition | Final prompt | Output schema | Memory |
|---|---|---|---|---|
| `L-A0` | A0 | `ANALYZER_L_A0_PROMPT_V3.txt` | `analyzer_local_result_v2.json` | OFF |
| `L-A1` | A1 | `ANALYZER_L_A1_PROMPT_V3.txt` | `analyzer_local_result_v2.json` | OFF |
| `G-A2` | A2 | `ANALYZER_G_A2_PROMPT_V4.txt` | `analyzer_group_result_v2.json` | OFF |
| `G-A3` | A3 | `ANALYZER_G_A3_PROMPT_V4.txt` | `analyzer_group_result_v2.json` | ON, exact group pack |
| `C` | n/a | `ANALYZER_C_PROMPT_V1.txt` | `analyzer_component_attribution_v1.json` | OFF |
| `P` | n/a | deterministic | none | OFF |
| `X` | target-linked | `ANALYZER_X_PROMPT_V2.txt` | `analyzer_crosscheck_result_v1.json` | A3 historical allowlist only |
| `R-PRE-SHADOW` | n/a | `RESEARCHER_PRE_SHADOW_PROMPT_V1.txt` | `api_researcher_pre_shadow_v1.json` | Researcher role |
| `R-POST-SHADOW` | n/a | `RESEARCHER_POST_SHADOW_PROMPT_V1.txt` | `api_researcher_post_shadow_v1.json` | Researcher role |

The manifest file, not this table, is authoritative for exact prompt/schema SHA values.

## 11. Formal DAG and multi-source group runtime representation

Formal Main contains five multi-source groups. Runtime representation must not fabricate a single task/gamefile for such a group.

Reference representation:

`GROUP scientific identity + memberwise teacher-access witness + exact member bindings`

Analyzer live-call authorization uses `teacher_call_permitted=true` plus exact task/gamefile provenance checks. `confirmatory_permitted` is recorded data-use metadata and is not the Analyzer live-call authorization bit.

Formal DAG V2 SHA for the reference run:

`71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`

## 12. Round Evidence and Human Researcher boundary

### Code/schemas

- `src/pchsi/cognitive_runtime/round_evidence.py`
- `src/pchsi/cognitive_runtime/researcher.py`
- `configs/cognitive_runtime/schemas/round_evidence_package_v1.json`
- `configs/cognitive_runtime/schemas/human_researcher_pre_v1.json`
- `configs/cognitive_runtime/schemas/api_researcher_pre_shadow_v1.json`

Round Evidence is frozen only after the Formal Analyzer result boundary is complete and must exclude future F0/F1 outcomes, Human PRE, future π2 evaluation, or other sealed future evidence.

Reference Round Evidence SHA:

`d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

Reference next gate:

`HUMAN_TRAINING_RESEARCHER_PRE`

## 13. Tests and hardening map

Key tests include:
- `tests/analyzer/test_local_results.py`
- `tests/analyzer/test_analyzer_grouping_v2.py`
- `tests/analyzer/test_act3_registration_group_io_v1.py`
- `tests/analyzer/test_act3_registration_canonical_pack_formal_v1.py`
- `tests/analyzer/test_analyzer_candidate_projector_v2.py`
- `tests/analyzer/test_state_candidate_budget_v1.py`
- `tests/cognitive_runtime/test_a0_a1_semantic_contract.py`
- `tests/cognitive_runtime/test_act1_evidence_reference_contract.py`
- `tests/cognitive_runtime/test_act3_group_identity_evidence_universe.py`
- `tests/cognitive_runtime/test_act3_group_projection_identity.py`
- `tests/cognitive_runtime/test_act3_x_evidence_contract.py`
- `tests/cognitive_runtime/test_formal_analyzer_dag_v2.py`
- `tests/cognitive_runtime/test_request_renderer.py`
- `tests/cognitive_runtime/test_run_registry_hard_stop.py`
- `tests/cognitive_runtime/test_researcher_and_round.py`

Historical hardening/audit documents remain under `docs/audits/` and are preserved as lineage evidence.

## 14. Formal reference server roots

Detailed paths and scientific/file identities are maintained in:

`experiments/formal_analyzer/pi1_reference_v1/ARTIFACT_INDEX.md`

Primary roots:
- fresh π1 collection: `formal_analyzer_fresh_pi1_collection_build_v1`
- Main A0/A1 preparation: `formal_analyzer_selected42_evidence_a0a1_preparation_v1`
- Main Batch transport/import: `formal_batch_transport_v2_round_continuation_v1`
- Main A1 materialization: `formal_main_a1_group_materialization_v1`
- corrected source closure: `formal_act3_registration_hardening_and_source_materialization_v1/_run_state/corrected_source_closure`
- A3 Memory restore: `formal_main_a3_group_memory_semantics_restore_v1_results/fixed_0944...`
- A2/A3 offline materialization: `formal_main_a2a3_offline_materialization_v1`
- G/X/candidate/Round Evidence state: `formal_analyzer_to_human_researcher_pre_boundary_v1_1_state`

## 15. Versioning rule

Any future change to grouping semantics, source/menu matching, A2/A3 evidence balance, Memory retrieval fusion, X authority, proposal representation, K budget, or Analyzer causal authority requires an explicit new version/condition and new experiment. It must not be silently interpreted as the same V2 reference method.
