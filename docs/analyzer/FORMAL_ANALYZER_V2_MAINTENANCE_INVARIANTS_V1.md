# Formal Analyzer V2 — Maintenance Invariants V1

Status: **NON-SILENT-CHANGE CONTRACT**

This file lists invariants that future maintenance must not silently change. If a future implementation needs to violate one of these rules, it must introduce a new explicit version and a new experiment rather than reinterpret the π1 reference run.

## 1. Role and authority invariants

1. Analyzer is not the Task Policy.
2. Analyzer is not the Human Training Researcher.
3. Failure Memory is not a reasoning agent and is not an effect oracle.
4. Analyzer cannot assign Benefit/Harm/Neutral/Uncertain.
5. Analyzer cannot execute F0/F1 or environment verification.
6. Analyzer cannot choose training method, π2 promotion, rollback, or round research priority.
7. X can challenge or constrain the target artifact but cannot silently rewrite it into a different repair.
8. Environment/Verifier remains the independent causal-effect authority.

## 2. Treatment invariants

### A0/A1
- same registered local U_reg;
- same current evidence per paired local unit;
- Memory OFF;
- A0 does not bind an A1 result;
- A1 binds its exact validated Formal local-result SHA.

### A2/A3
- same group identity;
- same group manifest;
- same member bindings;
- same plural A1 result SHA identities;
- same current evidence SHA universe;
- A2 Memory OFF;
- A3 exactly one frozen Analyzer Memory identity;
- removing Memory from A3 must yield the A2 common projection.

Do not add other treatment differences post hoc.

## 3. Grouping invariants

- Grouping is deterministic from frozen registered signatures.
- No human or model hand selection of group membership.
- No post-hoc regrouping after seeing A2/A3/X results.
- Cross-task/gamefile groups are legal when the deterministic grouping contract produces them.
- A multi-source group must preserve memberwise task/gamefile/source provenance; do not fabricate a single aggregate task/gamefile identity.
- The independent statistical universe is not silently changed from registered task/gamefile units to error memberships/groups.

## 4. Source-binding invariants

Every source-conditioned proposal must bind exact registered source evidence:
- `local_result_sha256`;
- `error_instance_id`;
- `source_state_sha256`;
- `menu_sha256`;
- exact registered menu strings.

Forbidden normalization/repair behavior:
- fuzzy matching;
- lower/casefold normalization for membership;
- nearest-action substitution;
- menu sorting, deduplication, or repair;
- inferred source calls when registration is ambiguous.

Ambiguity fails closed.

## 5. Memory invariants

Formal A3 Analyzer Memory semantics:

`exact member source -> independent AnalyzerMemoryViewV1 -> group bundle -> one Analyzer role pack`

Frozen rules:
- `cross_member_retrieval_fusion=false`;
- `hand_selection=false`;
- `singleton_special_flattening=false`;
- singleton groups remain group bundles;
- A2 receives no Memory;
- A3 receives exactly the frozen group pack;
- Memory cannot certify Benefit/Harm.

Any future group-fused retrieval is a new method and requires a new condition/version.

## 6. Evidence-universe invariants

- G hypotheses and proposals may cite only the registered current-evidence universe plus the A3 Memory identity when applicable.
- X current evidence and historical evidence are separate allowlists.
- A2 X historical allowlist is empty.
- A3 X historical allowlist contains exactly the corresponding Memory identity.
- Unregistered evidence citations fail closed.
- Current F0/F1 outcomes must never enter the pre-F0/F1 Analyzer evidence package.

## 7. Proposal serialization invariants

Current field: `source_conditioned_proposals`.

Exact action:
- one exact current-menu action string;
- `option_actions=[]`;
- `termination_condition=null`.

Short option:
- `exact_action=null`;
- 1-4 option actions;
- first action exact current-menu member;
- non-empty termination condition;
- later actions require live-menu revalidation during later F1 execution.

One group result cannot emit more than one proposal for the same `(local_result_sha256, error_instance_id)`.

## 8. K<=1 invariants

Candidate budget is enforced at `source_state x condition`.

- 0 executable candidates: abstain/no candidate is valid.
- 1 executable candidate: may advance to later verification.
- >1 distinct execution semantics: no winner may be selected by hidden rank/confidence/tie-break; record method-invalid collision/no-winner.
- Candidate projection does not imply causal benefit.

## 9. Runtime invariants

Canonical reference runtime:
- one scientific unit per request;
- `store=false`;
- no tools;
- no shared conversation state;
- no `previous_response_id` reuse;
- `truncation=disabled`;
- SDK automatic retries = 0;
- ambiguous post-send automatic retry forbidden.

Batch output order is not scientific order; exact `custom_id` rebinding is required.

A transport failure, provider refusal, schema-invalid output, or incomplete output must not be silently converted into a valid scientific result.

## 10. Task-access invariants

For Analyzer teacher calls, the authoritative live-call gate is `teacher_call_permitted=true` plus exact task/gamefile provenance checks.

`confirmatory_permitted` is a data-use field and must not be silently promoted into an Analyzer live-call authorization bit.

Select/sealed evaluation access and teacher-visible Analyzer access remain distinct.

## 11. Round-evidence invariants

`ROUND_EVIDENCE_PACKAGE_V1` is frozen only after the Formal Analyzer result boundary is complete.

It must exclude future/sealed fields including current F0/F1 outcomes, Human PRE, API shadow output, sealed test trajectories, and future π2 evaluation.

Human Training Researcher PRE occurs only after the round-evidence package is frozen.

## 12. Human Researcher interface invariant

Human PRE must make a real research decision:
- exactly one selected bottleneck;
- one falsifiable hypothesis;
- one principal change;
- fixed baseline/intervention variables;
- explicit sample definition and budgets;
- support/refutation/stop criteria.

Analyzer output is evidence for the Human Researcher, not a substitute for the Researcher decision.

## 13. Versioning rule

The following require an explicit new version/condition and new experiment:
- different grouping semantics;
- fused group Memory retrieval;
- different source/menu matching behavior;
- changed A2/A3 evidence balance;
- changed X authority;
- changed candidate K budget;
- changed proposal representation;
- Analyzer gaining causal-effect authority;
- new live C/P treatment inserted into the Formal reference path;
- any change that makes the original reference outcome no longer reproducible from its frozen manifests.

## 14. Reference identities

- Formal Main execution code head: `0529efa4b4c896f3855a4634c7daa3a3559e3a89`
- Canonical post-experiment Analyzer code head: `17201a462d24985e195a5bb225e388bd9cb9089e`
- Formal DAG V2 SHA: `71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`
- Round Evidence SHA: `d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`

These identities must remain visible in any future migration or reproduction report.