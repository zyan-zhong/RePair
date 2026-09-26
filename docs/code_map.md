# Code Map

## Current Round-1 research map

The repository-level scientific map for the completed historical first
single-round validation is:

```text
pi0 development evidence
→ strong-model proposal
→ Q2 environment validation
→ training-data construction
→ three pi1 training seeds
→ Harness-OFF evaluation
→ COMPLETE_NO_GO
→ mechanical post-hoc analysis
→ hierarchical semantic analysis
→ canonical evidence/provenance closure
```

Current disposition:

```text
Round-1 execution                       = COMPLETE
Harness-OFF policy improvement          = COMPLETE_NO_GO
Hierarchical Levels 1-4                 = COMPLETE
Level 5                                 = REJECTED
Level 6                                 = INCOMPLETE
Canonical evidence/provenance closure   = IN_PROGRESS
Failure Memory                          = HOLD
```

Current navigation:

- [Round-1 Overview](rounds/round1/README.md)
- [Component Registry](rounds/round1/COMPONENT_REGISTRY.md)
- [Asset Registry](rounds/round1/ASSET_REGISTRY.md)
- [Hierarchical Analysis Ledger](rounds/round1/HIERARCHICAL_ANALYSIS.md)
- [Current Provenance Audit](audits/ROUND1_CANONICAL_GAP_AUDIT.md)
- [Experiment Ledger](experiments/EXPERIMENT_LEDGER.md)

The Runtime Core and S1 sections below remain historical engineering
maps. They do not override the completed Round-1 scientific result.

## E1 Runtime Core merged implementation

| Field | Value |
|---|---|
| Historical implementation branch | `implementation/e1-runtime-core-v1-code` |
| Approved review base | `b079f2b3696fb6525353a6694be2bb78ee8d027a` |
| Approved review head | `85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7` |
| Runtime Core merge commit | `1ce3622b3b247c44e962a6b98eb78192f724580b` |
| Task 6 integration commit | `c95ee14c58709fc48ac23bd61ae071341380ff31` |
| Task 7 metadata seal commit | `397c6f3fa5ca3b3112f0b43431c931ea7cb94197` |
| Runtime termination-gate correction commit | `b4fa1647af29e495d58f83e039c97f83e5a9f750` |
| ActionTrace consistency correction commit | `086231b2919ac0afa0aa043cc6aa87ef981e2a1c` |
| Implementation status | Implemented on `main` |
| Task-level review | Tasks 1–6 passed; Runtime Core and ActionTrace post-review corrections verified |
| File-level review | Parser, prompt, budget, Runtime Core, and ActionTrace passed |
| Cumulative code approval | Complete |
| Merge approval | Complete |
| Latest verified test suite | 271 passed |
| `SPLIT_AND_ACCESS_V1` | Not frozen |
| ALFWorld evaluator | Not implemented |
| Execution status | Not approved |

The modules below are the reviewed Runtime Core modules merged into
`main`. They are not an active production deployment, an ALFWorld
evaluator, or an execution approval.

## Runtime Core merged modules

| Component | Path | Task and focused commit | Merged status | Runtime boundary |
|---|---|---|---|---|
| Strict raw-policy parser | `src/pchsi/evaluation/raw_policy_parser.py` | Task 1 — `28f4d3861d1cf33683a217a6155e3a5cc5d12a5c` | Merged into `main`; task-level review passed | Validates exactly one JSON action envelope and the literal action string; does not read the menu and does not repair actions |
| Deterministic prompt and M0 | `src/pchsi/evaluation/raw_policy_prompt.py` | Task 2 — `532be5e8b9916104274a25655ff19562faccb057` | Merged into `main`; task-level review passed | Builds `RAW_POLICY_PROMPT_V1`, fixed feedback, final-eight executed-transition memory, and `MEMORY_M0_V1` hashes |
| Immutable dual-budget accounting | `src/pchsi/evaluation/budget.py` | Task 3 — `d85e2e784a35242e53695d7ed44f253f19f7597f` | Merged into `main`; task-level review passed | Implements immutable policy-attempt, environment-step, and consecutive-nonexecuted accounting |
| Pure Runtime Core | `src/pchsi/evaluation/runtime_core.py` | Task 4 — `1c7f55975e31631a48e2cd88fa7adf71247287e3`; termination-gate correction — `b4fa1647af29e495d58f83e039c97f83e5a9f750` | Merged into `main`; file-level review passed after correction | Validates three-party menus and preconditions, closes the policy gate when environment, consecutive-nonexecuted, or policy-attempt limits are exhausted, performs strict parsing and exact membership, reserves environment steps, and finalizes environment results; never calls an environment |
| Immutable action trace | `src/pchsi/evaluation/action_trace.py` | Retained base plus Task 5 extension — `f5bac95abf6faa0fd4d7d48169756c73edad75ee`; consistency correction — `086231b2919ac0afa0aa043cc6aa87ef981e2a1c` | Merged into `main`; file-level review passed after correction | Records complete E1 provenance, parser/outcome coherence, exact budget lineage, environment results, and deterministic JSON while preserving historical non-Runtime constructors |

## Runtime Core tests

| Test scope | Path | Task and focused commit | Status |
|---|---|---|---|
| ActionTrace compatibility and Runtime Core fields | `tests/evaluation/test_action_trace.py` | Task 5 — `f5bac95abf6faa0fd4d7d48169756c73edad75ee`; consistency correction — `086231b2919ac0afa0aa043cc6aa87ef981e2a1c` | 106 tests; correction verified locally |
| Strict parser | `tests/evaluation/test_raw_policy_parser.py` | Task 1 — `28f4d3861d1cf33683a217a6155e3a5cc5d12a5c` | Merged tests |
| Prompt and M0 | `tests/evaluation/test_raw_policy_prompt.py` | Task 2 — `532be5e8b9916104274a25655ff19562faccb057` | Merged tests |
| Budget state machine | `tests/evaluation/test_budget.py` | Task 3 — `d85e2e784a35242e53695d7ed44f253f19f7597f` | Merged tests |
| Runtime Core decisions | `tests/evaluation/test_runtime_core.py` | Task 4 — `1c7f55975e31631a48e2cd88fa7adf71247287e3`; termination-gate correction — `b4fa1647af29e495d58f83e039c97f83e5a9f750` | 57 tests; correction verified locally |
| Fake-environment end-to-end integration | `tests/evaluation/test_runtime_core_fake_environment.py` | Task 6 — `c95ee14c58709fc48ac23bd61ae071341380ff31`; trace-schema correction — `086231b2919ac0afa0aa043cc6aa87ef981e2a1c` | 2 tests passed; test-only integration, not a production evaluator or ALFWorld adapter |

## Machine protocol and governance

| Component | Path | Status |
|---|---|---|
| Machine protocol | `configs/protocols/raw_with_menu_v1.json` | Runtime Core code-approved and merged; execution not approved |
| Experiment and governance ledger | `docs/experiments/EXPERIMENT_LEDGER.md` | Engineering and experiment states recorded separately |
| Approved implementation plan | `docs/superpowers/plans/2026-07-31-e1-runtime-core-v1-implementation.md` | Frozen implementation plan |

## Explicitly out of scope

The merged Runtime Core package does not implement or authorize:

- an ALFWorld evaluator or adapter;
- vLLM, SGLang, or other model clients;
- real Qwen or closed-source model calls;
- GPU, Slurm, or all134 execution;
- rollout outputs or experimental results;
- Phase-Critical Harness detection or intervention;
- closed-source distillation;
- SFT, preference learning, or reinforcement learning;
- Memory beyond `MEMORY_M0_V1`;
- a Research Planner;
- an automatic policy-promotion gate;
- E1-Dev results;
- E1-Confirmatory results.

## Approved handoff boundary

Completion and merge of this Runtime Core package permits only:

1. freeze `SPLIT_AND_ACCESS_V1`;
2. separately design the ALFWorld evaluator;
3. obtain evaluator code approval;
4. complete a separate execution-readiness audit;
5. obtain `EXECUTION_APPROVED_E1_DEV`.

Runtime Core completion does not authorize E1, all134, model, GPU, or
rollout execution.

## Historical source reference

The removed pre-v3.1 parser remains available only from:

- tag: `pre-v3.1-protocol-reset-20260731`
- path: `src/pchsi/evaluation/transport_parser.py`

Historical V7B.3c components remain audit subjects and are not active
dependencies of `RAW_WITH_MENU_V1`.

## S1 Collector Backend Probe merged candidate

| Field | Value |
|---|---|
| Design ID | `S1_COLLECTOR_BACKEND_PROBE_V1` |
| Historical implementation branch | `implementation/s1-read-only-inventory-collector-v1` |
| Approved review base | `0c5249bf6bf8c6335e77a791256654bff0f0e01d` |
| Approved review head | `465503d14ee968d2acf23a314c66c65c52260583` |
| GitHub merge commit | `71ff322ecba105521baf2cb4c2d84024529824b9` |
| Candidate commits | `22` |
| Cumulative changed paths | `143` |
| Latest verified full suite | `477 passed` |
| Native-test fail-closed correction | `6e9bc7eee04ce48bcecf103ae5138b547e7df03f` |
| Non-execution coverage correction | `465503d14ee968d2acf23a314c66c65c52260583` |
| Candidate tree SHA-256 | `d61493ccbb433babf2fed2a7e749dc483fe2e63bc6d43422048440d84ad96885` |
| Candidate binary SHA-256 | `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713` |
| Source manifest SHA-256 | `41f7461ac7ac7213ca13024a7c755a551f9ad0ab363ac46bc414040af3904eb7` |
| Runtime manifest SHA-256 | `4a524d95339afedbdc282a027cc99d388f4e99005f6ad109ff2bc61158effcfc` |
| Code approval | `CODE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1_CANDIDATE_ONLY` |
| Merge approval | `MERGE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1_CANDIDATE_ONLY` |
| Implementation status | Implemented and merged into `main` |
| Backend-probe execution | Not approved |
| Read-only inventory execution | Not approved |
| Final collector-backend approval | Pending |

### Merged candidate components

| Component | Path | Boundary |
|---|---|---|
| Frozen design | `docs/superpowers/specs/2026-08-05-s1-collector-backend-probe-design.md` | Defines the hostile-or-buggy collector threat model and the non-executing candidate boundary |
| Frozen implementation plan | `docs/superpowers/plans/2026-08-05-s1-collector-backend-probe-implementation.md` | Defines the reviewed Task 1–15 implementation sequence |
| Non-executing protocol | `docs/protocol/S1_COLLECTOR_BACKEND_PROBE_V1.md` | Records candidate-only status and future approval sequence |
| Native candidate | `native/s1_backend_probe/` | Default binary remains fail-closed; P1–P20 payloads remain compile-only |
| Python security contracts | `src/pchsi/security/` | Repository-local approval cannot open the execution gate |
| Candidate generation tools | `scripts/security/` | Generate deterministic descriptions and artifacts without running the probe |
| Regression suite | `tests/security/` | Covers native completeness, non-execution, evidence, manifests, and reproducibility |
| Probe manifests | `configs/security/probes/` | All 22 entries remain `execution_status=NOT_APPROVED` |
| Strict schemas | `configs/security/schemas/` | Close candidate contract and evidence structures |

### Current boundary

The merge establishes an engineering property only. It does not authorize or
establish the result of backend-probe execution, P1–P20 execution, real
namespace/mount/seccomp/Landlock operations, read-only inventory collection,
ALFWorld or model execution, final collector-backend approval, or any
Phase-Critical Harness scientific claim.
