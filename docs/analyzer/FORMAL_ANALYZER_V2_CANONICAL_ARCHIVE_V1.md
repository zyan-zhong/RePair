# Formal Analyzer V2 — Canonical Archive V1

Status: **FROZEN REFERENCE ARCHIVE**  
Reference round: `FORMAL_ANALYZER_PI1_REFERENCE_V1`  
Policy: `P4-R1-Q2-BAD-TRAIN17`  
Canonical post-experiment code head: `17201a462d24985e195a5bb225e388bd9cb9089e`  
Formal Main execution code head: `0529efa4b4c896f3855a4634c7daa3a3559e3a89`

This document is the maintenance entry point for the first complete Formal Analyzer V2 reference experiment. It consolidates the final design, authority boundaries, runtime, schemas, experimental conditions, execution semantics, and the exact boundary handed to the Human Training Researcher.

## 1. Research role

Formal Analyzer V2 is a **diagnosis and repair-candidate discovery system**. Its job is to transform grounded failure evidence into bounded, source-conditioned repair proposals while preserving exact evidence provenance.

It is **not** the policy, the environment verifier, the training researcher, or the promotion authority.

Canonical system chain:

`π1 failure evidence -> Local Analyzer -> deterministic grouping -> Group Analyzer -> independent X cross-check -> deterministic candidate projection/K<=1 -> ROUND_EVIDENCE_PACKAGE_V1 -> Human Training Researcher PRE -> same-state F0/F1 -> Benefit/Harm/Neutral/Uncertain -> verified training evidence -> π2`

### Analyzer authority

Analyzer may:
- identify error instances and mechanism hypotheses;
- group repeated mechanisms using frozen deterministic signatures;
- propose source-conditioned exact actions or short options;
- cite registered current/historical evidence;
- abstain;
- expose uncertainty.

Analyzer may **not**:
- assign Benefit/Harm/Neutral/Uncertain;
- execute F0/F1;
- declare a repair causally effective;
- choose training method or promotion/rollback;
- act as Human Training Researcher;
- silently rewrite the source state, menu, task, or group membership.

### Neighboring roles

- **Task Policy**: executes environment actions only.
- **Failure Memory**: governed historical substrate; it is not an effect oracle or reasoning authority.
- **Human Training Researcher**: selects one bottleneck/hypothesis/principal change after Round Evidence is frozen.
- **Harness**: executes the Researcher-approved verification plan.
- **Environment/Verifier**: sole authority for Benefit/Harm/Neutral/Uncertain.

## 2. Hierarchy

The conceptual hierarchy is:

`Mechanical Facts -> L -> G -> C -> P -> X -> deterministic projector`

Where:
- `L`: local trajectory-level analysis;
- `G`: group-level synthesis over deterministic repeated mechanisms;
- `C`: component attribution layer;
- `P`: deterministic policy/capability profile layer;
- `X`: independent challenge/cross-check;
- deterministic projector: converts only validated source-conditioned proposals into executable candidate bytes under source/menu and K<=1 constraints.

The **π1 Formal reference run** executed the registered treatment path `A0/A1 -> A2/A3 -> X -> deterministic candidate projection`. C/P modules remain part of the canonical Analyzer architecture and codebase, but no additional unregistered live C/P treatment was inserted into this Formal reference round.

## 3. Experimental conditions

### A0 — Local baseline
- unit: one episode/trajectory;
- Memory: OFF;
- purpose: local one-shot baseline under the registered local contract.

### A1 — Local multi-hypothesis Analyzer
- unit: same local episode universe as A0;
- Memory: OFF;
- purpose: structured local diagnosis, multiple mechanism hypotheses, local repair proposals;
- A0/A1 must reuse the same current evidence pack.

### A2 — Group Analyzer, Memory OFF
- unit: deterministic group;
- inputs: exact group synthesis input, exact Formal A1 bytes for every member, exact source contexts;
- Memory: OFF.

### A3 — Group Analyzer, Memory ON
- unit: exactly the same deterministic group and current evidence as A2;
- Memory: exactly one frozen Analyzer role pack;
- required causal fairness: after removing Memory fields, A2 and A3 common input bytes are identical.

### X — Independent cross-check
- target: validated G-A2 or G-A3 artifact;
- dispositions: `ACCEPT`, `DOWNGRADE_SCOPE`, `REQUIRE_ABSTENTION`, `REJECT`;
- X may challenge scope/evidence/proposal validity but may not rewrite the target repair into a different repair;
- A2 X remains Memory-blind; A3 X receives only the same registered historical Memory identity used by A3.

## 4. Deterministic grouping

Grouping is based on frozen mechanical/progress/lifecycle signatures, not post-hoc semantic selection.

The final Main universe produced true cross-trajectory recurrence:
- 30 source-closed Formal groups;
- 37 memberships;
- group-size census: 25 x size-1, 3 x size-2, 2 x size-3;
- 5 multi-member groups;
- all 5 multi-member groups span multiple A1 sources/tasks/gamefiles.

This is important: Formal grouping is allowed to represent repeated mechanisms across different tasks/gamefiles. Runtime authorization is therefore represented **memberwise**, not by inventing a fake single task/gamefile for a group.

## 5. Exact source closure

Every Formal member binds an exact source context by `(local_result_sha256, error_instance_id)` and preserves:
- `source_state_sha256`;
- `menu_sha256`;
- `source_call_index`;
- exact admissible command strings;
- source observation/history/public task goal as registered.

Ambiguity blocks execution. No guessing, fuzzy matching, lowercasing, menu repair, sorting, deduplication, or nearest-action substitution is allowed.

## 6. A3 Memory semantics

The historical ACT3 A3 algorithm was recovered and reused unchanged:

For every exact group member:
1. reconstruct `MemoryConsumerQueryV1` from its exact registered source context;
2. call the existing `build_analyzer_memory_view_v1`;
3. keep the member view independently.

For every group:
1. bundle all independent member views into `ACT3_GROUP_ANALYZER_MEMORY_BUNDLE_V1`;
2. wrap exactly once as `FAILURE_MEMORY_ROLE_PACK_V1`, `role=ANALYZER`;
3. use `cell_id = group_manifest_sha256`.

Frozen semantics:
- `cross_member_retrieval_fusion = false`;
- `hand_selection = false`;
- `singleton_special_flattening = false`;
- singleton groups remain one-member group bundles rather than naked member views.

Formal Main restore result:
- 30 group Memory packs;
- 37 member queries;
- 25 singleton groups;
- 5 multi-member groups.

## 7. Runtime and provider contract

Canonical runtime manifest:
`configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`

Reference settings include:
- provider: OpenAI;
- endpoint: `/v1/responses`;
- requested model: `gpt-5.6-sol`;
- `store=false`;
- `tools=[]`;
- `truncation=disabled`;
- SDK automatic retries: 0;
- ambiguous post-send automatic retry: forbidden;
- one scientific unit per request;
- no shared conversation state;
- no `previous_response_id` reuse.

Formal G and X were executed through OpenAI Batch with exact `custom_id` rebinding. Output order is never treated as scientific order.

## 8. Group result contract

Current Formal G output schema:
`configs/analyzer/schemas/analyzer_group_result_v2.json`

Canonical proposal field:
`source_conditioned_proposals`

Every proposal binds:
- `group_manifest_sha256`;
- `local_result_sha256`;
- `error_instance_id`;
- `source_state_sha256`;
- `menu_sha256`;
- exact action OR short option;
- supporting evidence SHA list;
- deterministic `source_proposal_sha256`.

Exact-action proposal:
- `exact_action` is one exact current-menu string;
- `option_actions=[]`;
- `termination_condition=null`.

Short-option proposal:
- `exact_action=null`;
- `option_actions` length 1-4;
- first action must be exact current-menu member;
- non-empty termination condition required;
- later option actions must be revalidated against the live menu if F1 is later authorized.

## 9. X evidence contract

X has two evidence universes:
- current evidence allowlist;
- historical evidence allowlist.

A2:
- historical allowlist empty;
- no Memory bytes or identity.

A3:
- historical allowlist contains exactly the frozen Memory pack identity;
- Memory bytes must resolve to that exact identity.

X citations outside registered allowlists fail closed.

## 10. Deterministic candidate projection and K<=1

`src/pchsi/analyzer/candidate_projector.py` validates source-conditioned proposal bytes and projects only source/menu-valid candidates.

State-level candidate budget is represented in:
`src/pchsi/analyzer/state_candidate_budget.py`

Canonical rule:
- at most one executable candidate per `source_state x condition`;
- zero candidates is valid abstention/no-candidate;
- distinct execution-semantic collisions do not receive an arbitrary winner;
- collision is method-invalid / no-winner, not post-hoc ranking.

Reference run result:
- 30 Formal source states;
- K1 collisions: 0;
- A2 selected executable candidate states: 30/30;
- A3 selected executable candidate states: 30/30.

This does **not** imply A3 is better than A2. Benefit/Harm evidence does not exist until independent same-state environment verification.

## 11. Formal Main data flow and final census

Fresh π1 collection:
- one formal fresh rollout stream;
- complete-batch stop rule;
- 48 failure trajectories collected;
- frozen first 42 selected by pre-registered order;
- 12 pilot + 30 confirmatory/Main trajectories.

Formal Main Analyzer:
- 30 Main A1 trajectories;
- 71 error instances;
- 58 deterministic groups;
- source closure -> 30 groups / 37 memberships / 30 unique source states.

Independent statistical universe remains the 30 registered Main task/gamefile states. Error instances, memberships, and groups are not silently reinterpreted as 71/58/37 independent experimental samples.

## 12. Formal reference execution results

### Offline A2/A3 materialization
- group count: 30;
- pair count: 30;
- rendered G requests: 60;
- A2 Memory exposure count: 0;
- A3 Memory pack count: 30;
- common-input equality: 30/30;
- max rendered request size: 115,513 bytes;
- provider/environment calls during offline materialization: 0.

### Formal DAG V2
`formal_dag_sha256 = 71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`

### G Batch
`batch_6a9118638eac8190a431ddfbab4f7f0a`
- completed: 60;
- failed: 0;
- validated: 60/60.

### X Batch
`batch_6a91192f92508190a60f88d8780fb7ea`
- completed: 60;
- failed: 0;
- validated: 60/60.

### Candidate pool
- Formal source states: 30;
- K1 collisions: 0;
- selected candidate counts: A2=30, A3=30;
- environment verification: not performed;
- Benefit/Harm labels: not assigned.

### Round Evidence boundary
`ROUND_EVIDENCE_PACKAGE_V1` SHA:
`d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

Boundary status:
- Human Researcher PRE created: false;
- API Researcher PRE shadow created: false;
- environment call performed: false;
- F0/F1 performed: false;
- automatic scientific retry performed: false;
- next gate: `HUMAN_TRAINING_RESEARCHER_PRE`.

## 13. Code identity

### Actual Formal Main execution head
`0529efa4b4c896f3855a4634c7daa3a3559e3a89`

This is the code identity bound to the successful Formal G/X reference execution.

### Canonical post-experiment Analyzer head
`17201a462d24985e195a5bb225e388bd9cb9089e`

This is one fast-forward commit after the execution head and adds explicit state-level K1 materialization infrastructure:
- `src/pchsi/analyzer/state_candidate_budget.py`;
- `tests/analyzer/test_state_candidate_budget_v1.py`;
- `docs/audits/FORMAL_ACT3_STATE_K1_HARDENING_V1.md`.

The archive branch uses this post-experiment head so future maintenance starts from the final correct Analyzer implementation, while this document preserves the exact execution head separately.

## 14. Canonical source map

### Analyzer core
- `src/pchsi/analyzer/authorities.py`
- `src/pchsi/analyzer/local_results.py`
- `src/pchsi/analyzer/grouping.py`
- `src/pchsi/analyzer/act3_registration.py`
- `src/pchsi/analyzer/crosscheck.py`
- `src/pchsi/analyzer/candidate_projector.py`
- `src/pchsi/analyzer/state_candidate_budget.py`
- `src/pchsi/analyzer/component_attribution.py`
- `src/pchsi/analyzer/metrics.py`
- `src/pchsi/analyzer/schema_contract.py`
- `src/pchsi/analyzer/formal_failure_collection.py`

### Cognitive runtime
- `src/pchsi/cognitive_runtime/manifest.py`
- `src/pchsi/cognitive_runtime/identity.py`
- `src/pchsi/cognitive_runtime/access.py`
- `src/pchsi/cognitive_runtime/projections.py`
- `src/pchsi/cognitive_runtime/request_renderer.py`
- `src/pchsi/cognitive_runtime/response.py`
- `src/pchsi/cognitive_runtime/output_validation.py`
- `src/pchsi/cognitive_runtime/formal_registry_v2.py`
- `src/pchsi/cognitive_runtime/orchestrator.py`
- `src/pchsi/cognitive_runtime/round_evidence.py`
- `src/pchsi/cognitive_runtime/researcher.py`

### Runtime config and schemas
- `configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`
- `configs/cognitive_runtime/schemas/formal_analyzer_dag_registry_v2.json`
- `configs/cognitive_runtime/schemas/runtime_input_registry_v1.json`
- `configs/cognitive_runtime/schemas/scientific_unit_identity_v1.json`
- `configs/cognitive_runtime/schemas/round_evidence_package_v1.json`
- `configs/cognitive_runtime/schemas/human_researcher_pre_v1.json`
- `configs/analyzer/schemas/analyzer_local_result_v2.json`
- `configs/analyzer/schemas/analyzer_group_manifest_v1.json`
- `configs/analyzer/schemas/analyzer_group_synthesis_input_v1.json`
- `configs/analyzer/schemas/analyzer_group_result_v2.json`
- `configs/analyzer/schemas/analyzer_source_conditioned_proposal_v1.json`
- `configs/analyzer/schemas/analyzer_crosscheck_result_v1.json`

### Prompts used by the final runtime
- `prompts/cognitive_runtime/ANALYZER_L_A0_PROMPT_V3.txt`
- `prompts/cognitive_runtime/ANALYZER_L_A1_PROMPT_V3.txt`
- `prompts/cognitive_runtime/ANALYZER_G_A2_PROMPT_V4.txt`
- `prompts/cognitive_runtime/ANALYZER_G_A3_PROMPT_V4.txt`
- `prompts/cognitive_runtime/ANALYZER_X_PROMPT_V2.txt`

## 15. Existing detailed design documents

This archive supersedes scattered branch names as the entry point, but the following detailed documents remain part of the canonical record:
- `docs/analyzer/HIERARCHICAL_ANALYZER_V2_DESIGN.md`
- `docs/analyzer/HIERARCHICAL_ANALYZER_V2_OUTPUT_CONTRACT_V1.md`
- `docs/analyzer/ANALYZER_A0_A3_PILOT_PROTOCOL_V1.md`
- `docs/analyzer/ANALYZER_METRIC_REGISTRY_V1.md`
- `docs/analyzer/OUTCOME_ADAPTIVE_ANALYSIS_BUDGET_V2.md`
- `docs/analyzer/COGNITIVE_ROLE_TRACE_AND_LOCAL_SUPERVISION_V1.md`
- `docs/paper/ANALYZER_V2_PAPER_EVIDENCE_CONTRACT_V1.md`
- `docs/protocol/REPAIR_DISCOVERY_AND_SAME_STATE_VERIFICATION_PROTOCOL_V1.md`
- `docs/runtime_researcher/MEMORY_ANALYZER_RESEARCHER_MODULE_HANDBOOK_V1.md`
- `docs/runtime_researcher/EXACT_STAGE_RUNTIME_FREEZE_V1.md`
- `docs/runtime_researcher/ROUND_EVIDENCE_PACKAGE_V1.md`
- `docs/research/HUMAN_TRAINING_RESEARCHER_TEMPLATE_V2.md`

## 16. Maintenance rule

Any future Analyzer V3 or experimental change that modifies authority, grouping, Memory exposure, evidence universe, source binding, K<=1 semantics, X semantics, or treatment definitions must:
1. use an explicit new version/schema/contract;
2. document the scientific reason;
3. preserve this V2 reference archive unchanged;
4. run a new experiment rather than silently reinterpret this reference run.

See `FORMAL_ANALYZER_V2_MAINTENANCE_INVARIANTS_V1.md` and `FORMAL_ANALYZER_V2_BRANCH_CONSOLIDATION_V1.md` for non-negotiable invariants and branch policy.