# Experiment Ledger

Every experiment must be recorded by research question, not only by an
internal phase or engineering task name.

| Field | Required entry |
|---|---|
| Experiment ID | E0–E20 or explicitly marked exploratory |
| Research question | One falsifiable question |
| Hypothesis | Expected directional result |
| Unique change | The only intended experimental difference |
| Fixed controls | Model, prompt, tasks, menu, budget, seeds and evaluator |
| Sample | Tasks, episodes, states and repetitions |
| Baseline | Exact baseline condition |
| Intervention | Exact changed condition |
| Primary endpoint | Prespecified success, risk or cost metric |
| Result | Numerator, denominator and task/state unit |
| Cases | At least one supporting and one adverse or failed case |
| Conclusion strength | Supported, partial, unsupported or uncertain |
| Alternative explanation | Main unresolved confound |
| Source | Code, config, raw output, command and hashes |

## Completed Round-1 scientific event

The repository contains a completed historical first single-round
policy-improvement validation that is distinct from the active E0-E20
roadmap.

| Field | Registered state |
|---|---|
| Round identity | `ROUND1_SINGLE_ROUND_POLICY_IMPROVEMENT_VALIDATION` |
| Round execution | `COMPLETE` |
| Harness-OFF policy-improvement result | `COMPLETE_NO_GO` |
| Hierarchical Levels 1-4 | `COMPLETE` |
| Level 5 global synthesis | `REJECTED` |
| Level 6 independent challenge | `INCOMPLETE` |
| Canonical evidence/provenance closure | `IN_PROGRESS` |
| Failure Memory | `HOLD` |

The historical round completed pi0-to-pi1 training and independent
Harness-OFF evaluation, but it did not establish successful policy
internalisation.

This historical scientific event is not silently remapped to E0-E20.

Authoritative navigation:

- [Round-1 Overview](../rounds/round1/README.md)
- [Round-1 Asset Registry](../rounds/round1/ASSET_REGISTRY.md)
- [Hierarchical Analysis Ledger](../rounds/round1/HIERARCHICAL_ANALYSIS.md)
- [Current Provenance Audit](../audits/ROUND1_CANONICAL_GAP_AUDIT.md)

## Engineering and governance status

Engineering evidence is not an experiment result.

| Item | Current state |
|---|---|
| Runtime Core implementation | Merged into `main` |
| Task-level code review | Passed for Tasks 1–6; Runtime Core and ActionTrace post-review corrections verified |
| Latest verified Runtime Core suite | 271 collected / 271 passed |
| Fake-environment integration | Passed; test-only; ActionTrace counter lineage synchronized |
| Runtime termination-gate correction | Verified at `b4fa1647af29e495d58f83e039c97f83e5a9f750`; file-level review passed |
| ActionTrace consistency correction | Verified at `086231b2919ac0afa0aa043cc6aa87ef981e2a1c`; file-level review passed |
| File-level cumulative review | Complete |
| Cumulative code approval | Complete |
| Merge approval | Complete |
| Approved review base | `b079f2b3696fb6525353a6694be2bb78ee8d027a` |
| Approved review head | `85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7` |
| Runtime Core merge commit | `1ce3622b3b247c44e962a6b98eb78192f724580b` |
| Machine governance status | `runtime_core_code_approved_execution_not_approved` |
| Merge into `main` | Completed |
| `SPLIT_AND_ACCESS_V1` | Not frozen |
| ALFWorld evaluator | Not implemented |
| E1-Dev execution | Not approved |
| E1-Confirmatory execution | Not approved |
| E1 rollout results | None |

The following implication is false:

```text
CODE_APPROVED
⇒ EXECUTION_APPROVED
```

The completed cumulative code-approval decision is externally bound to
review base `b079f2b3696fb6525353a6694be2bb78ee8d027a` and review head `85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7`. The completed
merge approval is bound to merge commit `1ce3622b3b247c44e962a6b98eb78192f724580b`. These evidence
labels do not authorize evaluator or experiment execution.

## Active experiment ledger

The E0-E20 table below tracks the active/current protocol roadmap.
It is not the identifier namespace of the completed historical Round-1
scientific event.


| ID | Experiment status | Infrastructure readiness | Research conclusion |
|---|---|---|---|
| E0 | Pending minimal reset audit | Historical assets exist | Historical facts still require code–log–raw-output agreement |
| E1 | Not executed | Runtime Core merged into `main`; code and merge approval complete; termination-gate and ActionTrace consistency corrections verified; 271 tests passed; `SPLIT_AND_ACCESS_V1` not frozen; evaluator not implemented; execution not approved | No E1 rollout has occurred. No success-rate, model-performance, badcase-taxonomy or failure-mechanism conclusion is available |
| E2 | Not implemented | No approved no-menu evaluator | Old no-menu analyses remain auxiliary until protocol audit |
| E3 | Not started on fresh raw-policy trajectories | Verifier not implemented | Historical verifiers are not automatically approved |
| E4–E8 | Historical evidence only | Fresh Runtime Core execution not available | Historical results must be repeated on fresh raw-policy states |
| E9–E11 | Historical Phase 1G NO-GO | No approved new selector | Old states may generate hypotheses but cannot validate a new selector |
| E12–E16 | Not started | No approved training/evaluation pipeline for the active E0-E20 roadmap | No successful policy-internalisation result is established for the active roadmap. Separately, the completed historical Round-1 Harness-OFF evaluation exists and ended `COMPLETE_NO_GO` |
| E17–E20 | Not started | No approved transfer or Research Planner execution | No transfer or autonomous-discovery claim exists |

## Current non-events

The merged Runtime Core package contains no:

- E1 or all134 execution;
- new valid-unseen detailed badcase inspection;
- closed-source model call;
- model training;
- Phase-Critical Harness execution;
- Research Planner execution;
- automatic candidate-policy promotion;
- rollout result or model artifact.

## Interpretation boundary

Passing unit and fake-environment tests establishes an engineering
property of the merged Runtime Core package. It does not establish:

- E1 success;
- model capability;
- an ALFWorld result;
- a failure taxonomy;
- a training improvement;
- an execution approval.

## S1 backend-probe engineering and governance status

Engineering evidence is not an experiment result.

| Field | Current state |
|---|---|
| Design ID | `S1_COLLECTOR_BACKEND_PROBE_V1` |
| Candidate implementation | Merged into `main` |
| Approved review base | `0c5249bf6bf8c6335e77a791256654bff0f0e01d` |
| Approved review head | `465503d14ee968d2acf23a314c66c65c52260583` |
| GitHub merge commit | `71ff322ecba105521baf2cb4c2d84024529824b9` |
| Candidate commits | `22` |
| Cumulative changed paths | `143` |
| Latest verified suite | `477 passed` |
| Code approval | `CODE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1_CANDIDATE_ONLY` |
| Merge approval | `MERGE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1_CANDIDATE_ONLY` |
| Candidate tree SHA-256 | `d61493ccbb433babf2fed2a7e749dc483fe2e63bc6d43422048440d84ad96885` |
| Candidate binary SHA-256 | `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713` |
| Source manifest SHA-256 | `41f7461ac7ac7213ca13024a7c755a551f9ad0ab363ac46bc414040af3904eb7` |
| Runtime manifest SHA-256 | `4a524d95339afedbdc282a027cc99d388f4e99005f6ad109ff2bc61158effcfc` |
| Backend-probe execution | Not approved |
| P1–P20 execution | Not executed and not approved |
| Read-only inventory execution | Not executed and not approved |
| Final collector-backend approval | Pending |
| `SPLIT_AND_ACCESS_V1` | Not frozen |
| ALFWorld evaluator | Not implemented |
| E1-Dev execution | Not approved |
| E1-Confirmatory execution | Not approved |

The candidate-only code approval does not grant backend-probe
execution. The merge approval does not grant read-only inventory execution.

### S1 non-events

The reviewed and merged S1 candidate has not produced a P1–P20 runtime
result, a sandbox-effectiveness conclusion on the target server, a read-only
inventory, a frozen split/access record, an ALFWorld rollout, a model or GPU
job, an E1-Dev or E1-Confirmatory result, or a Phase-Critical Harness
scientific result.

## E1 trusted-manifest split/access freeze

`SPLIT_AND_ACCESS_V1` is frozen in `TRUSTED_MANIFEST_DIRECT_V1` mode.

The E1 critical path uses the committed strict-134 `valid_unseen` manifest
directly. Automated hostile-collector inventory and S1 P1–P20 execution are
deferred optional hardening and are not prerequisites for E1.

This freeze does not authorize ALFWorld, model, smoke, E1-Dev, or
E1-Confirmatory execution. The evaluator remains unimplemented.

---

## FAILURE_MEMORY_TASK_ACCESS_FOUNDATION_SEAL_V1

Status: **SCIENTIFICALLY_CLOSED**

The one-time correction-aware read-only task-access materialization passed
at reviewed repository head `1f715ac9cb1104497bc8ba6e12bcd04daf3748b3`.

Frozen result:

- total records: 3827
- TRAIN_MEMORY_SOURCE: 2367
- TRAIN_RETRIEVAL_DEV: 1186
- valid_seen clean ID confirmation: 140
- valid_unseen standard OOD, historically exposed: 134
- protected SHA-256:
  `260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea`
- sanitized SHA-256:
  `e7dc8ddd1795b4ed51fdf62735a49620c8bc03470b86de220180d45a336c5228`
- PRE/POST source fingerprint:
  `d657703df1033a9797e7e9a18b3eb989e49dd3391a468d1a65f6edff3e609e24`

Detailed evidence:
`docs/audits/FAILURE_MEMORY_TASK_ACCESS_FOUNDATION_SEAL_V1.md`

Next scientific module:
Sequence Failure Experience → Procedural Failure Memory → Stage 0.

---

## FAILURE_MEMORY_PRIMARY_POLICY_IDENTITY_FOUNDATION_SEAL_V1

Status: **SCIENTIFICALLY_CLOSED**

The Failure Memory primary/secondary frozen Policy identity has been
materialized and independently verified.

Frozen identity:

- primary worker: Train17
- secondary policy-realization audits: Train31 / Train47
- source-record effect policy: ORIGINAL_SOURCE_CHECKPOINT
- no best-of-checkpoint selection
- primary policy contract SHA-256:
  `048b131d57c8080592e8855d483ced33c30b0362eec644a545a5f3ec29e86f82`
- source PRE/POST root identity:
  `6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8`
- execution manifest SHA-256:
  `e88b66e512e47d3ee15f955238d0b9cc225e7e54a7c910b936c84c6f9c8de8e7`

Detailed evidence:

`docs/audits/FAILURE_MEMORY_PRIMARY_POLICY_IDENTITY_FOUNDATION_SEAL_V1.md`

Together with the task-access seal, Failure Memory Unit 1 is now closed.

Next implementation unit:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

## Memory Scientific Validation V1 — protocol freeze before first Memory-ON outcome

Status: `DESIGN_APPROVED_TARGETED_HARDENING`.

The three downstream scientific packages are representation (A), retrieval/applicability safety (B), and Analyzer+history→verified repair (C). The policy-internalization experiment is a later independent package whose protocol must be pre-frozen before large C unblinding.

Current B-DIRECT engineering readiness does not authorize Memory-ON scientific execution. No scientific outcome is created by this protocol freeze.

## Memory Scientific Validation V1 — fixed-head Code Approval

A0 scientific-contract code at `2d0c38cbbae511d2f05b3375ff2e2f48e16427b0` is Code Approved.

No Memory-ON outcome has been produced. Formal A/B/C execution remains separately gated.

## Memory Scientific Validation V1 — pre-ABC authority seal

Shared A/B/C scientific contracts and fixed-head Code Approval are sealed before any Memory-ON outcome.

A may proceed to a separate formal scientific execution package. B/C remain dependency holds.

## Formal Memory Package A — hardened Code Approval

Formal A A0 execution code at `9d4e4b853fb62757ed8c709d76d14b80bc3fd357` is Code Approved for the
three-source × M0/M1/M2/M3 local paired probe.

No scientific outcome is produced by this approval. Runtime freeze and explicit
scientific execution approval remain required.

## Formal Memory Package A — runtime freeze

The Formal A0 Train17 runtime/service identity is frozen after hardened Code Approval.
Scientific execution remains NOT_AUTHORIZED and no Memory scientific outcome has been
produced.

## Formal Memory Package A0 — scientific result seal

Formal A0 execution and independent byte-identical recomputation audit are complete.
The result authority freezes all 12 cell outcomes, 9 local paired effects, aggregate
hashes and the local-only claim boundary.

Next package: Formal Package B retrieval and applicability safety.

## Formal Memory Package B — implementation activation

Package B is activated from the sealed A0 result authority. The implementation plan
freezes a safety-first selective lexical retriever and exact applicability gate flow.
No Package-B scientific result has been produced.

## Formal Memory Package B — code preparation

Formal-B retrieval/safety evaluation code and its offline runner are implemented.
Scientific execution remains separately gated; no Q3 result has been produced.

## Formal Memory Package B — pre-outcome hardening

A registered PROTOCOL_DEFECT amendment hardened threshold selection and independent
gold binding before any Package-B scientific execution. No Q3 outcome existed at the
time of amendment.

## Formal Memory Package B — hardened Code Approval

Formal-B retrieval/applicability-safety code at `f17b29d518c916e83f26ba453d545f1120ee4b9d` is Code Approved.
No Q3 result exists. Next stage is read-only source census followed by independent
gold/pool freezing.

## Formal Memory Package B — pool and query-candidate freeze

Calibration DEV / Selection Validation / Safety Stress group membership is frozen
before gold annotation. Query candidates use the final up to three policy-visible
model-call states per failure. No retrieval result or Q3 outcome exists.

## Formal Memory Package B — blinded gold annotation packet

The independent-gold annotation packet is frozen before annotation and before any
retrieval score. It contains 79 policy-visible query states and anonymous Memory
boundary cards only.

## Formal Memory Package B — corrected gold authority

Formal-B gold preparation is versioned to V2 before any scoring. The correction
adds mechanically bound factual sidecars for the reference annotator and audits
query timing against PolicyCallEvidenceV1. Group pools and retriever remain frozen.

## Formal Memory Package B — minimal Q3 protocol

B now proceeds as a pure offline deterministic retrieval/applicability-safety
evaluation using mechanically registered reference labels, followed by
Calibration, Validation and Safety Stress.

## Formal Memory Package B — minimal Q3 result

Formal B is complete. The sealed result answers Q3 retrieval/applicability safety
only; subsequent system-level Memory value is tested in Package C.

## Failure Memory V1 corrected scientific program

Frozen Stage 0 / 1A / 1B / 2 / 3 identities and honest Q1-Q5 authority boundaries.
The local `708638a...` over-scope incident is preserved externally and is not pushed.

## Failure Memory V1 scientific harness contracts

Registered the Memory-owned Stage 0, 1A, 1B, 2 and 3 experiment program and exact
Q1-Q5 evidence dependencies without self-authorizing scientific execution.
