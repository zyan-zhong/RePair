# Formal Analyzer V2 — Field and Schema Reference V1

Status: **FROZEN MAINTENANCE REFERENCE**  
Reference round: `FORMAL_ANALYZER_PI1_REFERENCE_V1`

This document is a field-level map for the schemas used by the Formal Analyzer V2 reference system. The JSON schema files are authoritative for exhaustive required keys, types, enums, and length limits. This document explains the scientific meaning, producer/consumer relationship, and identity fields that must not be silently reinterpreted.

## 1. Global identity rules

Formal Analyzer artifacts use content-addressed scientific identities. A semantic SHA field is not interchangeable with a filesystem path, Git blob SHA, provider response ID, Batch request ID, or file SHA.

Common identity categories:
- scientific unit identity: what experimental unit the artifact belongs to;
- semantic artifact identity: hash of the canonical artifact payload;
- file identity: SHA256 of exact serialized bytes where recorded;
- transport identity: provider/Batch IDs used only for transport provenance;
- evidence identity: exact registered evidence SHA(s) that authorize citations or projections.

Paths are provenance and may change during migration; semantic/file identities must be preserved or explicitly remapped.

## 2. `ANALYZER_LOCAL_RESULT_V2`

Schema:

`configs/analyzer/schemas/analyzer_local_result_v2.json`

Produced by:
- `L-A0` and `L-A1` Analyzer stages;
- implementation centered in `src/pchsi/analyzer/local_results.py` plus runtime rendering/validation.

Consumed by:
- deterministic grouping;
- source registration/source closure;
- G-A2/G-A3 projections;
- later evidence/metric materialization.

Critical identity:
- `local_result_sha256` is the registered local-result semantic identity used by later membership/source binding.

Scientific contents include structured local hypotheses/error evidence and registered error-instance information under the full schema contract.

Rules:
- A0 and A1 share the same underlying task/gamefile evidence per paired local unit;
- A0/A1 Memory is OFF;
- A1 validated bytes/identity must be reused exactly by later Formal group projections;
- a later stage must not reconstruct a merely equivalent A1 object and substitute it for the registered result.

## 3. `ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1`

Schema:

`configs/analyzer/schemas/analyzer_error_instance_membership_v1.json`

Produced by:
- deterministic Analyzer grouping/registration pipeline.

Consumed by:
- group manifest;
- source closure;
- group synthesis input;
- Formal DAG member bindings.

Critical provenance fields include:
- `local_result_sha256`;
- `error_instance_id`;
- task/gamefile provenance;
- deterministic group membership identity.

Meaning:
A membership is one registered error instance assigned to one deterministic mechanism group. The independent statistical universe must not be silently redefined from task/gamefile states to membership count.

## 4. `ANALYZER_GROUP_MANIFEST_V1`

Schema:

`configs/analyzer/schemas/analyzer_group_manifest_v1.json`

Produced by:
- `src/pchsi/analyzer/grouping.py` and registration materialization.

Consumed by:
- group projection;
- G-A2/G-A3 runtime;
- X;
- Formal DAG V2;
- group scientific identity.

Critical identity:
- `group_manifest_sha256`.

Scientific meaning:
The manifest freezes deterministic membership and group-level mechanism signature/provenance. Cross-task/gamefile groups are legal if produced by the deterministic grouping contract. A multi-source group must retain memberwise provenance rather than inventing one aggregate task/gamefile.

## 5. `ANALYZER_GROUP_SYNTHESIS_INPUT_V1`

Schema:

`configs/analyzer/schemas/analyzer_group_synthesis_input_v1.json`

Produced by:
- source-closure materialization after exact source binding.

Consumed by:
- `group_projection_v3` / Formal G runtime.

Key semantics:
- binds one group to exact member rows;
- each member row retains exact local result/error/source identity;
- `proposal_slot_limit`/candidate-related budget fields remain frozen according to the registered protocol;
- base/current evidence excludes A3 Memory; A3 Memory is attached as a separate treatment input.

## 6. Exact source context / source binding

The source-closure artifact family is materialized under the Formal ACT3 registration pipeline rather than represented by one public JSON schema file in this directory.

Reference files:
- `FORMAL_EXACT_SOURCE_BINDINGS_V1.json`
- `FORMAL_SOURCE_CONTEXTS_V1.json`
- `FORMAL_ACT3_SOURCE_CLOSURE_ROWS_V2.json`

Critical binding tuple includes:
- `local_result_sha256`;
- `error_instance_id`;
- `source_state_sha256`;
- `menu_sha256`;
- registered source call index/context.

Rules:
- exact matching only;
- no fuzzy/nearest action substitution;
- no lowercase/casefold normalization for scientific membership;
- no menu sorting/deduplication/repair;
- ambiguous source registration fails closed.

## 7. `ANALYZER_GROUP_RESULT_V2`

Schema:

`configs/analyzer/schemas/analyzer_group_result_v2.json`

Produced by:
- `G-A2` and `G-A3`.

Consumed by:
- X;
- deterministic candidate projector;
- metrics and Round Evidence support manifests.

Current proposal field:

`source_conditioned_proposals`

Do not use the stale historical name `source_conditioned_repairs`.

Critical group/evidence binding:
- result must correspond to registered group/current evidence;
- source-conditioned proposals must cite registered member/source evidence only;
- proposal source states/menus must remain exact.

A2/A3 difference:
- A2 has no Memory;
- A3 sees the corresponding frozen Analyzer Memory pack;
- other registered current evidence must be identical.

## 8. `ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1`

Schema:

`configs/analyzer/schemas/analyzer_source_conditioned_proposal_v1.json`

Produced inside:
- `ANALYZER_GROUP_RESULT_V2`.

Consumed by:
- deterministic candidate projector;
- X/evidence checks where applicable.

Proposal identity/provenance must bind the exact registered source state/error evidence.

Two bounded execution representations are supported by the current candidate path:

### Exact action
- exact action string from the current registered menu;
- no option continuation;
- no hidden nearest/fuzzy repair.

### Short option
- bounded short action list according to the current schema/protocol;
- first action must be valid under the registered current source menu;
- later steps require live-menu revalidation during later F1 execution;
- non-empty termination condition.

A proposal is a hypothesis/repair candidate, not a Benefit claim.

## 9. `ANALYZER_CROSSCHECK_RESULT_V1`

Schema:

`configs/analyzer/schemas/analyzer_crosscheck_result_v1.json`

Produced by:
- X stage.

Implementation:
- `src/pchsi/analyzer/crosscheck.py`;
- X projection and evidence allowlists in `src/pchsi/cognitive_runtime/projections.py`;
- validation in `output_validation.py`.

Consumed by:
- deterministic candidate projection;
- pre-verification metrics;
- Round Evidence support manifests.

Scientific rule:
X is an independent challenge to the target artifact. It may constrain/reject/downgrade according to the frozen disposition contract but may not silently rewrite the target into a different repair.

Evidence rule:
- current evidence and historical evidence are separate allowlists;
- A2 X has no historical Memory allowlist;
- A3 X historical evidence is limited to the corresponding frozen Memory identity.

## 10. `ANALYZER_REPAIR_CANDIDATE_V1`

Schema:

`configs/analyzer/schemas/analyzer_repair_candidate_v1.json`

Produced by:
- `src/pchsi/analyzer/candidate_projector.py`.

Consumed by:
- state-level K<=1 materialization;
- later Human Researcher/F0F1 planning after the Analyzer boundary.

Scientific rule:
Candidate projection is deterministic representation/eligibility logic. It does not establish causal benefit.

Execution-semantic states used by the current reference path include exact-action and bounded short-option forms, plus non-executable/rejected states defined by the schema/projector.

## 11. State-level K<=1 artifact semantics

Implementation:

`src/pchsi/analyzer/state_candidate_budget.py`

Reference budget key:

`source_state x condition`

Rules:
- 0 distinct executable semantics -> no candidate/abstain is valid;
- 1 -> candidate may advance;
- >1 -> method-invalid collision/no hidden winner.

Reference run:
- 30 source states;
- 60 condition-state outcomes;
- K1 collision count = 0.

## 12. `RUNTIME_INPUT_REGISTRY_V1`

Schema:

`configs/cognitive_runtime/schemas/runtime_input_registry_v1.json`

Implementation:
- materialization/validation under `src/pchsi/cognitive_runtime/*` and associated scripts.

Meaning:
Registers exact scientific units and stage inputs for runtime execution. A runtime registry is an authority object, not a convenience list.

Key bindings include:
- source/scientific unit ID;
- stage/condition;
- scientific identity path/object;
- input projection;
- task-access authority;
- expected evidence/A1/Memory identities as applicable;
- registry semantic SHA.

## 13. `SCIENTIFIC_UNIT_IDENTITY_V1`

Schema:

`configs/cognitive_runtime/schemas/scientific_unit_identity_v1.json`

Implementation:

`src/pchsi/cognitive_runtime/identity.py`

Meaning:
Defines the scientific unit that a request/artifact belongs to (episode/group/cross-check target/round, etc.).

For cross-task Formal groups, the reference runtime uses a GROUP scientific identity plus memberwise provenance; it does not fabricate one task/gamefile identity for the aggregate group.

## 14. Task-access records

Implementation:

`src/pchsi/cognitive_runtime/access.py`

Reference live Analyzer gate:
- `teacher_call_permitted=true`;
- exact task/gamefile provenance must match.

`confirmatory_permitted` is a data-use field and must not be silently promoted into the Analyzer live-call authorization condition.

Select/sealed-evaluation access and teacher-visible Analyzer access remain distinct scientific concepts.

## 15. `FORMAL_ANALYZER_DAG_REGISTRY_V2`

Schema:

`configs/cognitive_runtime/schemas/formal_analyzer_dag_registry_v2.json`

Implementation:

`src/pchsi/cognitive_runtime/formal_registry_v2.py`

Reference Formal DAG SHA:

`71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`

Key scientific checks:

### Local A0/A1 pair
- same registered paired local unit;
- same common evidence identity;
- A0 has no A1 local result;
- A1 binds the exact validated A1 local-result SHA;
- Memory OFF.

### Group A2/A3 pair
Must match on:
- group ID;
- `group_manifest_sha256`;
- member bindings;
- plural `a1_local_result_sha256s`;
- `current_evidence_sha256s`.

Treatment difference:
- A2 `memory_pack_sha256 = null`;
- A3 binds the exact frozen Memory identity.

## 16. `UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1`

Path:

`configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`

This is the authoritative stage-to-prompt/schema/runtime binding table.

Reference global fields include:
- endpoint `/v1/responses`;
- requested model `gpt-5.6-sol` for this frozen runtime;
- `store=false`;
- one scientific unit per request;
- no shared conversation state;
- no `previous_response_id` reuse;
- no tools;
- `truncation=disabled`;
- SDK automatic retries = 0;
- ambiguous post-send automatic retry = false.

Final Analyzer stage bindings:
- `L-A0` -> `ANALYZER_L_A0_PROMPT_V3` -> `ANALYZER_LOCAL_RESULT_V2`;
- `L-A1` -> `ANALYZER_L_A1_PROMPT_V3` -> `ANALYZER_LOCAL_RESULT_V2`;
- `G-A2` -> `ANALYZER_G_A2_PROMPT_V4` -> `ANALYZER_GROUP_RESULT_V2`;
- `G-A3` -> `ANALYZER_G_A3_PROMPT_V4` -> `ANALYZER_GROUP_RESULT_V2`;
- `C` -> `ANALYZER_C_PROMPT_V1` -> `ANALYZER_COMPONENT_ATTRIBUTION_V1`;
- `P` -> deterministic/no model call;
- `X` -> `ANALYZER_X_PROMPT_V2` -> `ANALYZER_CROSSCHECK_RESULT_V1`.

The manifest's SHA fields are authoritative for exact prompt/schema bytes.

## 17. Memory role-pack interface

Analyzer A3 consumes the validated Failure Memory consumer interface; it does not redefine Memory scientific authority.

Relevant implementation:
- `src/pchsi/memory/consumer_views.py`;
- `src/pchsi/memory/dev_snapshot_loader.py` for the frozen snapshot loader path;
- Memory role-pack contracts under `configs/memory/`;
- attachment/identity checks in `src/pchsi/cognitive_runtime/projections.py`.

Formal A3 frozen semantics:
- independent member retrieval views;
- group bundle;
- one Analyzer role pack;
- no cross-member retrieval fusion;
- no hand selection;
- no singleton special flattening.

## 18. `ROUND_EVIDENCE_PACKAGE_V1`

Schema:

`configs/cognitive_runtime/schemas/round_evidence_package_v1.json`

Implementation:

`src/pchsi/cognitive_runtime/round_evidence.py`

Reference package semantic SHA:

`d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

Meaning:
Frozen pre-Human-Researcher evidence boundary after Formal Analyzer completion.

Must exclude future/sealed evidence including:
- current F0/F1 outcomes;
- Human PRE itself;
- API Researcher PRE shadow;
- future π2 evaluation;
- future promotion/rollback outcomes.

## 19. `HUMAN_RESEARCHER_PRE_V1`

Schema:

`configs/cognitive_runtime/schemas/human_researcher_pre_v1.json`

Finalizer:

`src/pchsi/cognitive_runtime/researcher.py`

Key Human PRE contract:
- exactly one selected bottleneck;
- one falsifiable hypothesis;
- one principal change;
- explicit baseline/intervention/fixed variables;
- sample/budget definitions;
- primary/secondary diagnostics;
- support/refutation/stop criteria.

Human PRE is downstream of Analyzer and is not part of the frozen Analyzer result itself.

## 20. Full-schema authority rule

This document intentionally does not copy every JSON-schema property. The complete field-level authority is the checked-in JSON schema at the referenced path. If this narrative and a schema disagree, the frozen schema/manifest used by the reference execution controls the reproduction; the discrepancy must then be fixed by an explicit documentation correction, not by silently changing the schema.
