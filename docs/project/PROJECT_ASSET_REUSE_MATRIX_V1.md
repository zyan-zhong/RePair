# PROJECT_ASSET_REUSE_MATRIX_V1

## Status

```text
STATUS = CANONICAL_REFERENCE_LOOP_REUSE_CONTRACT
BASE_MAIN_HEAD = 0d30be2cad516ab1b651a2735d28402c0a454fd3
FAILURE_MEMORY_FINAL_SEAL_TAG = failure-memory-v1-memory-owned-final-seal-v1
FAILURE_MEMORY_FINAL_SEAL_HEAD = 68b79fa94f25b9244298333be398c1f47b4a8b70
CHANGE_POLICY = EXPLICIT_DESIGN_REVIEW_REQUIRED
```

## Purpose

This matrix freezes what the π1→π2 human reference loop reuses, what receives a
narrow extension, and what must not be rebuilt. It is a scope and scientific
attribution contract, not an execution approval.

## Reuse matrix

| Asset | Existing authoritative capability | Reference-loop action | Forbidden |
|---|---|---|---|
| Runtime Core | strict parser, exact full-menu membership, 60/30/3 budgets, fixed feedback, immutable ActionTrace semantics | Reuse without changing decision semantics | A second Analyzer runtime; action repair; fuzzy matching; menu sorting/filtering/truncation |
| PolicyCallEvidenceV1 | exact prompt/rendered prompt, token IDs, request/response bytes, goal, observation, menu, executed history, budget and latency | Read and bind by content SHA | Re-serializing it as a new truth source; dropping failed/nonexecuted calls |
| ActionTrace | parser/admissibility/execution status, before/after budget counters, submitted and executed action, environment result | Read and bind by exact model-call identity | Editing old traces to add Analyzer fields; treating Analyzer hypotheses as trace facts |
| PublicTransitionRecordV1 | public pre/post observation and menu, executed action, done/won/score | Reuse as the environment-transition authority | Reconstructing transitions from model prose or Memory text |
| EpisodeArtifact + attempt bundle | attempt.json, action_traces.jsonl, policy_calls.jsonl, public_transitions.jsonl, SHA256SUMS | Revalidate and create a sidecar rebinding manifest | Building a second collector; silently accepting legacy bundles without policy_calls for formal Analyzer evidence |
| Mechanical fact bases | parser/admissibility, termination, budget, public transitions | Compile deterministic derived facts | Asking an LLM to count repeats, budget, no-effect or public state changes |
| Analyzer V0 / P2 proposer | one-case critical-step localization, one correction, short recovery, abstention, provider/schema/authority | Reuse provider and authority boundaries; upgrade evidence input and analysis hierarchy | A new unrelated proposer with incompatible evidence/authority |
| Hierarchical post-hoc analysis | matched group → mechanism → task family → capability → challenge | Convert only approved structures into grouped/global Analyzer passes | Treating post-hoc prose as online fact or causal authority |
| Failure Memory V1 | governed role packs, provenance, applicability, counterexamples, effect history, immutable final seal | Reuse ANALYZER_MEMORY_PACK_V1 and RESEARCHER_MEMORY_PACK_V1 | Reopening direct-to-policy Memory tuning; rewriting the registered negative result |
| Exact/same-state replay and F0/F1 | policy-conditioned state replay, paired branches, budget accounting, Benefit/Harm/Neutral/Uncertain authority | Add repair-registration and sidecar identity binding only | A second branch runner; Analyzer self-signing Benefit/Harm |
| First-round trainer | SFT/LoRA training pipeline and manifests | Reuse after verified-training evidence is frozen | Training before the F0/F1 evidence manifest is sealed |
| Harness-OFF evaluator | independent policy evaluation and task-family reporting | Rebind π1/π2 concrete identities; extend promotion evidence | Letting the Researcher decide promotion from prose |
| Artifact publisher | checksummed, no-clobber attempt and scientific artifacts | Reuse unchanged | New ad-hoc output trees without receipts/checksums |
| Failure Memory scientific results | Q1–Q3 NOT_SUPPORTED; Q4/Q5 handoff; post-hoc archive | Preserve as historical research evidence | Reinterpreting zero exposure as safe/beneficial Memory use |

## Required first outputs

The next implementation stage must consume this matrix and produce:

```text
TRAJECTORY_REBINDING_MANIFEST_V1
MECHANICAL_EPISODE_EVIDENCE_V1
MECHANICAL_PAIRED_EVIDENCE_V1
PI1_REFERENCE_IDENTITY_V1
TASK_ACCESS_REVALIDATION_V1
```

No Analyzer model call, environment branch execution, training, or policy
promotion is authorized by this document.
