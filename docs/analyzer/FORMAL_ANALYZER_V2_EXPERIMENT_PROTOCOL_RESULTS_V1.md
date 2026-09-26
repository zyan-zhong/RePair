# Formal Analyzer V2 — Experiment Protocol and Results V1

Status: **FROZEN REFERENCE EXPERIMENT DOCUMENT**  
Reference round: `FORMAL_ANALYZER_PI1_REFERENCE_V1`  
Policy version: `P4-R1-Q2-BAD-TRAIN17`

This document records the final experimental protocol, treatment definitions, execution order, reference cohort, runtime controls, observed results, and claim boundaries for the first complete Formal Analyzer V2 π1 reference experiment.

Machine-readable authority:

`experiments/formal_analyzer/pi1_reference_v1/EXPERIMENT_MANIFEST.json`

Server provenance/index:

`experiments/formal_analyzer/pi1_reference_v1/ARTIFACT_INDEX.md`

## 1. Research question at the Analyzer layer

The Formal Analyzer experiment asks whether a hierarchical, evidence-grounded failure-analysis system can produce better bounded repair candidates from real π1 failures, and specifically whether adding frozen historical Failure Memory to the same group-level current evidence changes repair discovery in a scientifically controlled way.

The experiment does **not** itself establish that a proposal is causally beneficial. Benefit/Harm/Neutral/Uncertain remains the later same-state F0/F1 Environment/Verifier authority.

## 2. Frozen role boundary

Analyzer may:
- diagnose error instances/mechanisms;
- aggregate repeated mechanism evidence under deterministic grouping;
- propose source-conditioned exact actions or bounded short options;
- cite registered current evidence and, only in A3, registered historical Memory;
- expose uncertainty or abstain.

Analyzer may not:
- assign Benefit/Harm/Neutral/Uncertain;
- execute environment verification;
- choose π2 training/promotion/rollback;
- replace Human Researcher prioritization;
- silently alter the registered treatment after seeing results.

## 3. Fresh π1 collection

Reference fresh collection:
- 48 executed failure trajectories;
- first 42 selected according to the pre-frozen ordering rule after complete-batch stopping;
- 12 Pilot + 30 Main;
- no best-seed/post-hoc task selection.

The Main scientific universe is 30 registered task/gamefile states. Error-instance/group membership counts are diagnostic/structural quantities and do not replace this independent statistical universe.

## 4. Formal local conditions A0/A1

### A0
One-shot local Analyzer baseline.

Controls:
- same registered episode evidence as A1;
- Memory OFF;
- one scientific unit per request;
- frozen prompt/schema/runtime.

### A1
Multi-hypothesis local Analyzer condition.

Controls:
- same underlying task/gamefile unit as paired A0;
- Memory OFF;
- exact validated A1 local result becomes the registered downstream local evidence.

Main execution result:
- A0 accepted/validated: 30;
- A1 accepted/validated: 30;
- normalized Main local results: 60 accepted total.

## 5. Error extraction and deterministic grouping

From the 30 Main A1 results:
- error instances: 71;
- deterministic groups before source closure: 58;
- source-closed Formal groups: 30;
- source-closed memberships: 37;
- unique registered source states: 30.

Group size census:
- size 1: 25 groups;
- size 2: 3 groups;
- size 3: 2 groups.

Five groups are multi-member and all five span multiple source A1 results, task IDs, and gamefiles. This establishes that the Formal Main grouping machinery actually instantiated cross-trajectory repeated-mechanism groups, unlike the earlier DEV cohort where no cross-episode multi-member group was available.

Grouping remains deterministic. Cross-task grouping is not manually selected and must preserve memberwise task/gamefile/source provenance.

## 6. Source closure

Each Formal group member must resolve to exact registered source evidence.

Core binding includes:
- `local_result_sha256`;
- `error_instance_id`;
- `source_state_sha256`;
- `menu_sha256`;
- exact registered source context/call index.

Ambiguous or missing binding fails closed. No fuzzy action/menu/source repair is allowed.

## 7. A3 Failure Memory treatment materialization

A3 uses the already-validated Failure Memory consumer path. No new Memory retrieval algorithm was introduced for the Formal Main experiment.

Frozen snapshot SHA:

`8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189`

Restore identity:

`0944e3c5a172f3b30431d142a4b53a9c113bd0a1f9a473c35a38bcfbad16e057`

Materialization semantics:

`exact member source -> independent AnalyzerMemoryViewV1 -> group bundle -> one Analyzer role pack`

Formal Main result:
- Memory packs: 30;
- member queries/views: 37;
- singleton groups: 25;
- multi-member groups: 5;
- cross-member retrieval fusion: false;
- hand selection: false;
- singleton special flattening: false.

## 8. Group conditions A2/A3

### A2 — Memory OFF group analysis

Input contains:
- exact group identity/manifest;
- exact member bindings;
- exact validated plural A1 results;
- exact source contexts/current evidence;
- no historical Memory.

### A3 — same current evidence + historical Memory

Input contains the identical A2 current evidence plus exactly one frozen Analyzer Memory pack for that group.

Frozen fairness requirement:

Removing `memory_pack` and `memory_pack_sha256` from A3 must yield the A2 common projection byte-for-byte under canonical serialization.

Offline materialization audit:
- group count: 30;
- A2/A3 pair count: 30;
- rendered requests: 60;
- A2 Memory exposure count: 0;
- A3 Memory pack count: 30;
- common-input equality: 30/30;
- max rendered request size: 115,513 bytes;
- provider/environment calls during this offline gate: 0.

## 9. Formal DAG V2 gate

Reference Formal DAG SHA:

`71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`

Registered units:
- paired local units: 30;
- local condition rows: 60;
- registered groups: 30;
- group condition rows: 60.

Multi-source runtime representation:

`MEMBERWISE_TEACHER_ACCESS_WITNESS_PLUS_GROUP_IDENTITY`

No fake single-task aggregate identity is introduced for cross-task groups.

## 10. Runtime/provider controls

Authoritative runtime manifest:

`configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`

Reference runtime controls:
- endpoint `/v1/responses`;
- requested model `gpt-5.6-sol`;
- `store=false`;
- tools disabled;
- one scientific unit per request;
- no shared conversation state;
- no `previous_response_id` reuse;
- `truncation=disabled`;
- SDK automatic retries = 0;
- ambiguous post-send automatic retry forbidden.

Batch output order is not scientific order; `custom_id` rebinding is mandatory.

## 11. Formal G execution

Batch ID:

`batch_6a9118638eac8190a431ddfbab4f7f0a`

Execution:
- requests: 60;
- completed: 60;
- provider failed: 0;
- validated scientific outputs: 60/60.

Conditions:
- 30 G-A2;
- 30 G-A3.

The current group output schema is `ANALYZER_GROUP_RESULT_V2`, and the current source-level proposal field is `source_conditioned_proposals`.

## 12. Formal X execution

X is an independent evidence-constrained challenge stage over each validated G target.

Batch ID:

`batch_6a91192f92508190a60f88d8780fb7ea`

Execution:
- requests: 60;
- completed: 60;
- provider failed: 0;
- validated X outputs: 60/60.

A2 X has no historical Memory allowlist. A3 X historical evidence is limited to the corresponding frozen Memory identity. X cannot silently rewrite the target repair.

## 13. Deterministic candidate projection and K<=1

Validated source-conditioned proposals passing the frozen post-X path are projected deterministically into bounded candidates.

Budget unit:

`source_state x condition`

Reference result:
- unique source states: 30;
- conditions: 2;
- state-condition outcomes: 60;
- K1 collision count: 0;
- selected executable candidates: A2=30, A3=30.

No hidden rank/confidence winner selection was needed.

## 14. What the candidate result does and does not mean

Observed:
- both A2 and A3 achieved executable candidate coverage on all 30 registered source states after the complete G/X/projector pipeline;
- no state-condition K1 collision occurred.

Not established:
- A3 candidate quality > A2 candidate quality;
- Memory causes more Benefit;
- Memory reduces Harm;
- selected candidates are causally correct;
- any repair should yet be used for training.

Those require independent same-state F0/F1 verification.

## 15. Round Evidence seal

The Formal Analyzer boundary ended by freezing:

`ROUND_EVIDENCE_PACKAGE_V1`

Semantic SHA:

`d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

Boundary assertions:
- Human Researcher PRE created: false;
- API Researcher PRE shadow created: false;
- environment call performed: false;
- F0/F1 performed: false;
- automatic scientific retry performed: false.

Next gate:

`HUMAN_TRAINING_RESEARCHER_PRE`

## 16. Reference execution harness

Reference package:

`formal_analyzer_to_human_researcher_pre_boundary_v1_1.zip`

SHA256:

`18a165518d498138853dc04b20f1d03ebddd9552797d3301eba2d6aee1750f52`

Its role was orchestration/content-addressed glue around the already-built Analyzer/runtime components. It did not redefine the scientific algorithms.

Package details and the V1 -> V1.1 correction are recorded in:

`experiments/formal_analyzer/pi1_reference_v1/ORCHESTRATION_PACKAGE_V1_1.md`

The exact source files used on the server should also be retained under the experiment archive in Git and the original ZIP should be attached to the release asset set.

## 17. Formal code identities

Actual Formal Main execution code head:

`0529efa4b4c896f3855a4634c7daa3a3559e3a89`

This identity is the authority for what code existed when the reference G/X execution was prepared and run.

Canonical post-experiment Analyzer head:

`17201a462d24985e195a5bb225e388bd9cb9089e`

This adds the state-level K1 materialization hardening as the canonical maintenance head after the run.

Archive/main documentation commits after `17201a...` describe and index the frozen system; they must not be confused with the Formal execution code identity.

## 18. Server artifact roots

Detailed file-by-file path/provenance index:

`experiments/formal_analyzer/pi1_reference_v1/ARTIFACT_INDEX.md`

Key roots:
- fresh π1 collection: `formal_analyzer_fresh_pi1_collection_build_v1`;
- Main A0/A1 prep: `formal_analyzer_selected42_evidence_a0a1_preparation_v1`;
- Main Batch import: `formal_batch_transport_v2_round_continuation_v1/_run_state/main_batch_import`;
- A1 group materialization: `formal_main_a1_group_materialization_v1`;
- source closure: `formal_act3_registration_hardening_and_source_materialization_v1/_run_state/corrected_source_closure`;
- A3 Memory restore: `formal_main_a3_group_memory_semantics_restore_v1_results/fixed_0944...`;
- A2/A3 materialization: `formal_main_a2a3_offline_materialization_v1`;
- G/X/candidate/Round Evidence: `formal_analyzer_to_human_researcher_pre_boundary_v1_1_state`.

## 19. Reproduction order

A faithful reproduction must preserve this order:

1. bind/freeze π1 policy identity and task-access authorities;
2. collect/freeze fresh π1 failures;
3. materialize and execute A0/A1 under frozen runtime;
4. freeze exact A1 results;
5. deterministic grouping and exact source closure;
6. materialize A3 Memory using frozen snapshot/semantics;
7. materialize paired A2/A3 and prove common-input equality;
8. materialize/validate Formal DAG V2;
9. execute/import/validate 60 G requests;
10. build/execute/import/validate 60 X requests;
11. deterministic proposal->candidate projection;
12. enforce K<=1 per source_state x condition;
13. freeze support manifests and Round Evidence;
14. only then begin Human Training Researcher PRE.

No later result may be back-propagated into an earlier frozen gate.

## 20. Publication/claim boundary

This Formal Analyzer reference supports methodology, coverage, exact evidence binding, treatment integrity, multi-source hierarchical grouping existence, and the successful construction of bounded candidates.

It does not by itself support a causal claim that Memory improves repair quality. The paper-level causal effect must be supported by the later independent F0/F1 Benefit/Harm evidence and, ultimately, scaffold-free π2 improvement under Memory OFF + Harness OFF.
