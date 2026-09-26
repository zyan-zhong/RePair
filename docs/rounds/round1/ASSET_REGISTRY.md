# Round-1 Asset Registry

## Purpose

This document is the canonical major-asset registry for the completed first single-round policy-improvement validation.

It binds the major scientific workflow stages to verified server paths, repository records, producers, consumers, populations, historical identities, statuses and retention rules.

This registry does not replace the underlying evidence.

## Authority and Source-of-Truth Boundary

When records disagree, the Round-1 consolidation uses the following authority order:

```text
original server-side raw evidence
→ original manifest / ledger / cryptographic seal
→ deterministic audit output
→ this Asset Registry
→ Component / Hierarchical Analysis ledgers
→ Experiment Ledger
→ root README
```

A higher-level document may not strengthen, repair or override a lower-level scientific result.

Semantic-model output is authoritative evidence of what the semantic model returned, but its scientific authority remains semantic hypothesis generation rather than environment truth.

## Path and Mirror Policy

The representative server inspection root used for most current entries is:

```text
/data/run01/scwb204/pchsi
```

Historical paths are preserved exactly when they are themselves part of a frozen historical seal.

In particular, the full 340-bundle provenance archive retains its original `/data/home/...` path in the archive-root seal. This registry does not rewrite that historical identity to a different alias.

Repository paths are navigation or repository evidence. They do not substitute for server-side raw evidence.

## Registry Field Definitions

| Field | Meaning |
|---|---|
| Logical asset | Human-readable canonical name for the registered asset. |
| Workflow stage | Round-1 scientific or governance stage that owns the asset. |
| Scientific role | What the asset establishes or records. |
| Server path | Verified historical server path when applicable. |
| Repository path | Repository mirror, audit or navigation entry when available. |
| Producer | Historical component that created the asset. |
| Downstream consumer | Registered later stage that consumes the asset. |
| Population / file count | Relevant denominator, row count, request count or archive size. |
| Historical identity | Original file SHA, package freeze root, tree seal or commit identity. |
| Current verification SHA-256 | Current byte check when the registered object is a single file. |
| Status | Scientific or archival status without strengthening the original result. |
| Retention | How the historical bytes or navigation record must be retained. |
| Authority class | Raw/sealed, deterministic audit, derived analysis, navigation or historical reference. |

## Round-1 Workflow Asset Map

| Workflow stage | Registered assets | Statuses present |
|---|---:|---|
| Governance and Runtime Foundation | 1 | `COMPLETE` |
| pi0 Development Evidence | 1 | `COMPLETE` |
| Strong-Model Proposal and R132 | 2 | `COMPLETE` |
| Q2 Environment Validation | 2 | `COMPLETE` |
| Training-Data Construction | 1 | `COMPLETE` |
| pi1 Training | 4 | `COMPLETE` |
| Harness-OFF Evaluation | 2 | `COMPLETE`, `COMPLETE_NO_GO` |
| Mechanical Post-hoc Analysis | 4 | `COMPLETE` |
| Hierarchical Semantic Analysis | 7 | `COMPLETE`, `INCOMPLETE`, `REJECTED` |
| Canonical Evidence and Provenance Closure | 5 | `COMPLETE`, `IN_PROGRESS` |
| Failure Memory Handoff Boundary | 2 | `HOLD` |

Round-1 scientific state represented by this registry:

```text
Round execution                         = COMPLETE
Harness-OFF policy-improvement result  = COMPLETE_NO_GO
Hierarchical Levels 1-4                = COMPLETE
Level 5 global synthesis               = REJECTED
Level 6 independent challenge          = INCOMPLETE
Canonical evidence/provenance closure  = IN_PROGRESS
Failure Memory                         = HOLD
```

## Governance and Runtime Foundation

### Asset 01 — Round-1 runtime and raw-policy implementation

- **Workflow stage:** `governance_and_runtime_foundation`
- **Scientific role:** Repository implementation basis used by the Round-1 raw-policy runtime and evaluator lineage.
- **Server path:** `NOT_APPLICABLE_REPOSITORY_ONLY`
- **Repository path:** [`src/pchsi/evaluation`](../../../src/pchsi/evaluation)
- **Producer:** Runtime Core implementation and review process
- **Downstream consumer:** Round-1 policy evaluation pipeline
- **Population / file count:** repository implementation
- **Historical identity:** `COMMIT_SHA:1ce3622b3b247c44e962a6b98eb78192f724580b`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_AS_REPOSITORY_EVIDENCE`
- **Authority class:** `HISTORICAL_REFERENCE`
- **Source evidence:**
  - `docs/code_map.md`
  - `docs/experiments/EXPERIMENT_LEDGER.md`
- **Verification note:** Repository-only basis. Commit identity is not a server evidence-file SHA.

## pi0 Development Evidence

### Asset 02 — Frozen pi0 development root manifest

- **Workflow stage:** `pi0_development_evidence`
- **Scientific role:** Frozen entry point for initial pi0 development evidence.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p2_pre_model_call_package_v1/freeze/root_manifests/r0_pi0_dev.jsonl`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** pre-model-call evidence freeze
- **Downstream consumer:** strong-model proposal and later Round-1 analysis
- **Population / file count:** 1055 JSONL rows
- **Historical identity:** `FILE_SHA256:dd6470d6a760e2cd5c22ce749d2aa46c7a8ad789f1f0ee7322e6be5366f5c8a2`
- **Current verification SHA-256:** `dd6470d6a760e2cd5c22ce749d2aa46c7a8ad789f1f0ee7322e6be5366f5c8a2`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p2_pre_model_call_package_v1/freeze/root_manifests/r0_pi0_dev.jsonl`
- **Verification note:** Current bytes match the verified Module-3 file SHA.

## Strong-Model Proposal and R132

### Asset 03 — R132 strong-model proposal package

- **Workflow stage:** `strong_model_proposal_r132`
- **Scientific role:** Frozen 117-case strong-model proposal package feeding the Round-1 Q2 path.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_r1_3_2`
- **Repository path:** [`docs/audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/R132_PRIMARY117_IDENTITY_AUDIT_V1.json`](../../audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/R132_PRIMARY117_IDENTITY_AUDIT_V1.json)
- **Producer:** P2 strong offline proposer package builder
- **Downstream consumer:** Q2 validation and training-data construction
- **Population / file count:** 117 primary cases; 91 teacher outputs; 26 rejections; 351 Q2 bindings
- **Historical identity:** `PACKAGE_FREEZE_ROOT:794727df6157715d3c8e04156f97e53300ef9107ca793d215caec447cab964b5`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_r1_3_2/P2_OPENAI_PACKAGE_FREEZE_INDEX.json`
  - `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_r1_3_2/audit/static_self_audit.json`
  - `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_run_r1_3_2/run_summary.json`
  - `docs/audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/R132_PRIMARY117_IDENTITY_AUDIT_V1.json`
- **Verification note:** Dedicated identity-chain audit reports PASS with 117 cases, 91 teacher outputs, 26 rejections, 351 bindings, 99 raw responses and 135 transport attempt metadata records.

### Asset 04 — R132 PRIMARY117 execution log

- **Workflow stage:** `strong_model_proposal_r132`
- **Scientific role:** Primary transport/execution log for the 117-case run.
- **Server path:** `/data/run01/scwb204/pchsi/p2/logs/p2_r132_primary117/primary117.log`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** P2 R132 execution
- **Downstream consumer:** R132 identity audit
- **Population / file count:** 117 primary requests
- **Historical identity:** `FILE_SHA256:315236e71249dc9f8fd37617b9f426356dfc2c810ad5d3dafb2769aed92652e9`
- **Current verification SHA-256:** `315236e71249dc9f8fd37617b9f426356dfc2c810ad5d3dafb2769aed92652e9`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/logs/p2_r132_primary117/primary117.log`
- **Verification note:** Log SHA matches the registered R132 identity audit.

## Q2 Environment Validation

### Asset 05 — Frozen Q2 validated dataset manifest

- **Workflow stage:** `q2_environment_validation`
- **Scientific role:** Final Q2 dataset definition and scientific acceptance accounting.
- **Server path:** `/data/run01/scwb204/pchsi/p2/d_q2_bad_v1_frozen/final_dataset_manifest.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Q2 validation and dataset freeze
- **Downstream consumer:** training-data materialization
- **Population / file count:** 91 scientific Q2 accepted; 84 training examples
- **Historical identity:** `FILE_SHA256:445c99c5219c1a537ab9b8820d97ebbcbbc329dd305f40db6a296aa6d30393c8`
- **Current verification SHA-256:** `445c99c5219c1a537ab9b8820d97ebbcbbc329dd305f40db6a296aa6d30393c8`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/d_q2_bad_v1_frozen/final_dataset_manifest.json`
- **Verification note:** Manifest status D_Q2_BAD_V1_FROZEN; scientific_q2_accepted_count=91.

### Asset 06 — Q2 manual audit summary

- **Workflow stage:** `q2_environment_validation`
- **Scientific role:** Human-reviewed Q2 inclusion/exclusion audit.
- **Server path:** `/data/run01/scwb204/pchsi/p2/d_q2_bad_v1_frozen/manual_audit/manual_audit_review_summary.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Q2 manual audit
- **Downstream consumer:** frozen Q2 dataset
- **Population / file count:** 27 reviewed; 27 pass; 0 fail; 0 pending
- **Historical identity:** `FILE_SHA256:f690b10123e2947d84d7dd99f6de8b395a0ec153f20fc3433572aa915451ab07`
- **Current verification SHA-256:** `f690b10123e2947d84d7dd99f6de8b395a0ec153f20fc3433572aa915451ab07`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/d_q2_bad_v1_frozen/manual_audit/manual_audit_review_summary.json`
  - `/data/run01/scwb204/pchsi/p2/d_q2_bad_v1_frozen/manual_audit/manual_audit_results_reviewed_final.jsonl`
- **Verification note:** The historical summary text records review complete pending researcher approval; final frozen dataset subsequently records manual_audit_status=PASS.

## Training-Data Construction

### Asset 07 — Frozen Round-1 training-data materialization

- **Workflow stage:** `training_data_construction`
- **Scientific role:** Rendered training examples and tokenizer/model binding used for formal training.
- **Server path:** `/data/run01/scwb204/pchsi/p2/d_q2_bad_training_materialization_v1_frozen/final_materialization_manifest.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** D_Q2_BAD training materializer
- **Downstream consumer:** three formal pi1 training runs
- **Population / file count:** 84 training samples
- **Historical identity:** `FILE_SHA256:868c434bc519b14fb2f870fefd500526807581f4fb5b22b73eaa69e4e46db1e4`
- **Current verification SHA-256:** `868c434bc519b14fb2f870fefd500526807581f4fb5b22b73eaa69e4e46db1e4`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/d_q2_bad_training_materialization_v1_frozen/final_materialization_manifest.json`
- **Verification note:** Manifest status D_Q2_BAD_TRAINING_MATERIALIZATION_V1_FROZEN.

## pi1 Training

### Asset 08 — Formal pi1 training result seed 17

- **Workflow stage:** `pi1_training`
- **Scientific role:** Primary completion manifest for one formal Round-1 training seed.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_17/formal_run_manifest.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** formal Round-1 training runner
- **Downstream consumer:** checkpoint-set freeze and Harness-OFF evaluation
- **Population / file count:** 210 optimizer steps; 9670 target loss tokens
- **Historical identity:** `FILE_SHA256:ce44dd66ccf675da5d73fe9ac6b6273799df51e90b72bd92398ef521f1d103e6`
- **Current verification SHA-256:** `ce44dd66ccf675da5d73fe9ac6b6273799df51e90b72bd92398ef521f1d103e6`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_17/formal_run_manifest.json`
  - `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_17/adapter_artifact_manifest.json`
- **Verification note:** run_status=FORMAL_TRAINING_COMPLETED; adapter_manifest_sha256=cfcff4c187429f5f9a82b55a47bb3ce4a9123e224a541fdfefa45ed09e9073a7; frozen checkpoint alias bytes match.

### Asset 09 — Formal pi1 training result seed 31

- **Workflow stage:** `pi1_training`
- **Scientific role:** Primary completion manifest for one formal Round-1 training seed.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_31/formal_run_manifest.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** formal Round-1 training runner
- **Downstream consumer:** checkpoint-set freeze and Harness-OFF evaluation
- **Population / file count:** 210 optimizer steps; 9670 target loss tokens
- **Historical identity:** `FILE_SHA256:8b14bab7bf9d0396600c0d9bb5fc60340d0bd9336323dd9a3ad4047e76e8bd83`
- **Current verification SHA-256:** `8b14bab7bf9d0396600c0d9bb5fc60340d0bd9336323dd9a3ad4047e76e8bd83`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_31/formal_run_manifest.json`
  - `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_31/adapter_artifact_manifest.json`
- **Verification note:** run_status=FORMAL_TRAINING_COMPLETED; adapter_manifest_sha256=ca06e6807803d82ed803e0ecdbc5b018bb1fdd85a8347f3b05a821cbb117170d; frozen checkpoint alias bytes match.

### Asset 10 — Formal pi1 training result seed 47

- **Workflow stage:** `pi1_training`
- **Scientific role:** Primary completion manifest for one formal Round-1 training seed.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_47/formal_run_manifest.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** formal Round-1 training runner
- **Downstream consumer:** checkpoint-set freeze and Harness-OFF evaluation
- **Population / file count:** 210 optimizer steps; 9670 target loss tokens
- **Historical identity:** `FILE_SHA256:57db3c1dd720d758a21150389df840343cfec53a473b1b59b984303dd43eeb78`
- **Current verification SHA-256:** `57db3c1dd720d758a21150389df840343cfec53a473b1b59b984303dd43eeb78`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_47/formal_run_manifest.json`
  - `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_formal_runs_v1/seed_47/adapter_artifact_manifest.json`
- **Verification note:** run_status=FORMAL_TRAINING_COMPLETED; adapter_manifest_sha256=b491aec5dc1f65a3b8f2083e605241473b171aa351c07ccf8d252bfaed206159; frozen checkpoint alias bytes match.

### Asset 11 — Frozen three-checkpoint Round-1 set

- **Workflow stage:** `pi1_training`
- **Scientific role:** Frozen archive containing all three final training-seed checkpoints and manifests.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_checkpoint_set_v1_frozen`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** checkpoint-set freezer
- **Downstream consumer:** Harness-OFF evaluation
- **Population / file count:** 23 files; 359767109 bytes
- **Historical identity:** `ROOT_SEAL:6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** 23-file tree seal; checkpoint_set_manifest binds all three formal run manifests and adapters.

## Harness-OFF Evaluation

### Asset 12 — Harness-OFF raw episode evidence

- **Workflow stage:** `harness_off_evaluation`
- **Scientific role:** Complete raw Harness-OFF evaluation evidence for pi0 and three trained conditions.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Harness-OFF SELECT evaluator
- **Downstream consumer:** final analysis and post-hoc analysis
- **Population / file count:** 2724 files; 104897859 bytes
- **Historical identity:** `ROOT_SEAL:447137a57290e61b59db5dc48c932ad57edc926f343b5db6d41f469d021ffabe`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** 2724-file tree seal. Historical formal root has no standalone compact root result; this sealed raw root and downstream final-analysis bundle jointly bind the evaluation.

### Asset 13 — Harness-OFF final unblinded analysis

- **Workflow stage:** `harness_off_evaluation`
- **Scientific role:** Primary Round-1 policy-improvement decision under Harness-OFF evaluation.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_analysis/P4_SELECT_V2_FINAL_ANALYSIS_RESULT_V1.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** final SELECT analysis and unblind pipeline
- **Downstream consumer:** Round-1 scientific conclusion and post-hoc analysis
- **Population / file count:** pi0 plus three trained conditions
- **Historical identity:** `FILE_SHA256:865b2f33b36226a52031b2e764ec0de5728d217c8da2247701ecc34c5cc48246`
- **Current verification SHA-256:** `865b2f33b36226a52031b2e764ec0de5728d217c8da2247701ecc34c5cc48246`
- **Status:** `COMPLETE_NO_GO`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_analysis/P4_SELECT_V2_FINAL_ANALYSIS_RESULT_V1.json`
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_analysis/P4_SELECT_V2_FINAL_ANALYSIS_SEAL_V1.json`
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_analysis/P4_SELECT_V2_SINGLE_ROUND_FINAL_EVIDENCE.sha256`
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_analysis/P4_SELECT_V2_TASK_LEVEL_RESULTS_V1.json`
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_analysis/P4_select_v2_final_unblind.py`
- **Verification note:** Primary result plus final seal, task-level results, evidence checksum and unblind implementation all match their registered SHA-256 identities.

## Mechanical Post-hoc Analysis

### Asset 14 — Harness-OFF mechanical manifest r0_pi0

- **Workflow stage:** `mechanical_posthoc_analysis`
- **Scientific role:** Condition-level deterministic binding of published evaluation cells, runtime and schedule.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r0_pi0.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Harness-OFF mechanical publisher
- **Downstream consumer:** post-hoc deterministic and semantic analysis
- **Population / file count:** 85 cells
- **Historical identity:** `FILE_SHA256:5480917add60eab23fda300305fe283c35d03b0b0f124191300be8d708be150d`
- **Current verification SHA-256:** `5480917add60eab23fda300305fe283c35d03b0b0f124191300be8d708be150d`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r0_pi0.json`
- **Verification note:** Current bytes match registered condition manifest SHA.

### Asset 15 — Harness-OFF mechanical manifest r1_train17

- **Workflow stage:** `mechanical_posthoc_analysis`
- **Scientific role:** Condition-level deterministic binding of published evaluation cells, runtime and schedule.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r1_train17.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Harness-OFF mechanical publisher
- **Downstream consumer:** post-hoc deterministic and semantic analysis
- **Population / file count:** 85 cells
- **Historical identity:** `FILE_SHA256:fa2effb344970e980103c242371c3e57591fa1d9f1bb153c901609e9fa4b347f`
- **Current verification SHA-256:** `fa2effb344970e980103c242371c3e57591fa1d9f1bb153c901609e9fa4b347f`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r1_train17.json`
- **Verification note:** Current bytes match registered condition manifest SHA.

### Asset 16 — Harness-OFF mechanical manifest r1_train31

- **Workflow stage:** `mechanical_posthoc_analysis`
- **Scientific role:** Condition-level deterministic binding of published evaluation cells, runtime and schedule.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r1_train31.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Harness-OFF mechanical publisher
- **Downstream consumer:** post-hoc deterministic and semantic analysis
- **Population / file count:** 85 cells
- **Historical identity:** `FILE_SHA256:2e431a140ef607acdec0995a3f2c0a6f76807200e51dd317d354b7d8b6599dea`
- **Current verification SHA-256:** `2e431a140ef607acdec0995a3f2c0a6f76807200e51dd317d354b7d8b6599dea`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r1_train31.json`
- **Verification note:** Current bytes match registered condition manifest SHA.

### Asset 17 — Harness-OFF mechanical manifest r1_train47

- **Workflow stage:** `mechanical_posthoc_analysis`
- **Scientific role:** Condition-level deterministic binding of published evaluation cells, runtime and schedule.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r1_train47.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Harness-OFF mechanical publisher
- **Downstream consumer:** post-hoc deterministic and semantic analysis
- **Population / file count:** 85 cells
- **Historical identity:** `FILE_SHA256:10da0c7b41eb59d37472b336156545c9a86ec4526d69db465e5083e7cfaf1851`
- **Current verification SHA-256:** `10da0c7b41eb59d37472b336156545c9a86ec4526d69db465e5083e7cfaf1851`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_harness_off_select_v2_formal/_mechanical/r1_train47.json`
- **Verification note:** Current bytes match registered condition manifest SHA.

## Hierarchical Semantic Analysis

### Asset 18 — Matched-group evidence-pack archive

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Frozen matched-group semantic-analysis input packs.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_single_round_hierarchical_posthoc_v2/matched_group_packs_v3`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** matched-group pack builder
- **Downstream consumer:** Level-1 analysis
- **Population / file count:** 88 files; 1860187 bytes
- **Historical identity:** `ROOT_SEAL:acd7943f714305d9a9f993cb0360a1e1199320d1fd93d76c22973f7b426a4e90`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Provider bytes are authoritative records of the semantic-analysis execution; semantic claims remain hypotheses rather than environment truth.

### Asset 19 — Level-1 provider evidence archive

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Raw provider evidence for matched-group analysis.
- **Server path:** `/data/run01/scwb204/pchsi/evidence/p4_hierarchical_posthoc_v2/matched_group_analysis_background_v2`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Level-1 external analyzer runtime
- **Downstream consumer:** Level-1 audit and Level-2 input freeze
- **Population / file count:** 1729 files; 6075212 bytes
- **Historical identity:** `ROOT_SEAL:5db960bbe50d1b1762b2fe947e3c82774de0b793cd4b8eff21e9f81b465686c2`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Provider bytes are authoritative records of the semantic-analysis execution; semantic claims remain hypotheses rather than environment truth.

### Asset 20 — Level-2 provider evidence archive

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Raw provider evidence for mechanism discovery.
- **Server path:** `/data/run01/scwb204/pchsi/evidence/p4_hierarchical_posthoc_v2/level2_mechanism_synthesis_v1_1_formal`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Level-2 external analyzer runtime
- **Downstream consumer:** Level-2 audit and Level-3 projection
- **Population / file count:** 309 files; 2110263 bytes
- **Historical identity:** `ROOT_SEAL:31404e0edd3c7736e51fd160880d6a9463b3274bf9d4af8ed0c802844a3c94c2`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Provider bytes are authoritative records of the semantic-analysis execution; semantic claims remain hypotheses rather than environment truth.

### Asset 21 — Level-3 provider evidence archive

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Raw provider evidence for task-family projection.
- **Server path:** `/data/run01/scwb204/pchsi/evidence/p4_hierarchical_posthoc_v2/level3_task_family_projection_v1_formal`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Level-3 external analyzer runtime
- **Downstream consumer:** Level-3 audit and Level-4 interaction analysis
- **Population / file count:** 135 files; 1192736 bytes
- **Historical identity:** `ROOT_SEAL:dc481a216fb791100bb42d26a118c4002f71a32431f10aa1cc0c29e10d715182`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Provider bytes are authoritative records of the semantic-analysis execution; semantic claims remain hypotheses rather than environment truth.

### Asset 22 — Level-4 provider evidence archive

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Raw provider evidence for cross-capability analysis.
- **Server path:** `/data/run01/scwb204/pchsi/evidence/p4_hierarchical_posthoc_v2/level4_cross_capability_interaction_v1_formal`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Level-4 external analyzer runtime
- **Downstream consumer:** Level-4 audit and Level-5 synthesis
- **Population / file count:** 156 files; 780837 bytes
- **Historical identity:** `ROOT_SEAL:4a3284c53f0c5eaa3b9e45608ec5a2eb7456eea8c4c2ab176e5079b2f6e9b0ea`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Provider bytes are authoritative records of the semantic-analysis execution; semantic claims remain hypotheses rather than environment truth.

### Asset 23 — Level-5 provider evidence archive

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Raw provider evidence for the rejected global synthesis attempt.
- **Server path:** `/data/run01/scwb204/pchsi/evidence/p4_hierarchical_posthoc_v2/level5_global_mechanism_synthesis_v1_formal`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Level-5 external analyzer runtime
- **Downstream consumer:** Level-5 semantic validator
- **Population / file count:** 23 files; 1398158 bytes
- **Historical identity:** `ROOT_SEAL:32f5ad3b53860ff253b4422244d2753661eb22d60c2fb818e2d0db4d68b60fc1`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `REJECTED`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Provider bytes are authoritative records of the semantic-analysis execution; semantic claims remain hypotheses rather than environment truth.

### Asset 24 — Level-6 independent-challenger synthetic runtime seal

- **Workflow stage:** `hierarchical_semantic_analysis`
- **Scientific role:** Synthetic runtime validation for the intended independent challenger path.
- **Server path:** `/data/run01/scwb204/pchsi/p2/p4_single_round_hierarchical_posthoc_v2/ANALYZER_RUNTIME_SMOKE_SEAL_V1.json`
- **Repository path:** [`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`](HIERARCHICAL_ANALYSIS.md)
- **Producer:** analyzer runtime smoke test
- **Downstream consumer:** future real-data independent challenge
- **Population / file count:** synthetic challenger smoke
- **Historical identity:** `FILE_SHA256:0846f026f5b8f3dd31e1a365aeb603bebc1274d10a4bf045c7339e8ae964e7f0`
- **Current verification SHA-256:** `0846f026f5b8f3dd31e1a365aeb603bebc1274d10a4bf045c7339e8ae964e7f0`
- **Status:** `INCOMPLETE`
- **Retention:** `PRESERVE_AS_HISTORICAL_REFERENCE`
- **Authority class:** `HISTORICAL_REFERENCE`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/p2/p4_single_round_hierarchical_posthoc_v2/ANALYZER_RUNTIME_SMOKE_SEAL_V1.json`
  - `docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`
- **Verification note:** Runtime smoke used synthetic evidence; no final completed real-scientific-data Level-6 result is registered.

## Canonical Evidence and Provenance Closure

### Asset 25 — Round-1 canonical artifact-contract audit

- **Workflow stage:** `canonical_evidence_and_provenance_closure`
- **Scientific role:** Historical audit of exact server slots, archive roots and repository lineage.
- **Server path:** `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_CANONICAL_ARTIFACT_CONTRACT_AUDIT_V1.json`
- **Repository path:** [`docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md)
- **Producer:** canonical artifact-contract auditor
- **Downstream consumer:** current provenance-closure work
- **Population / file count:** 48 exact slots; 9 archive roots; 6 discovery slots
- **Historical identity:** `FILE_SHA256:ef41178218f8079b29dec4f413e93f486aa49866f5d3f2e7000fd89cb2c8f571`
- **Current verification SHA-256:** `ef41178218f8079b29dec4f413e93f486aa49866f5d3f2e7000fd89cb2c8f571`
- **Status:** `IN_PROGRESS`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_CANONICAL_ARTIFACT_CONTRACT_AUDIT_V1.json`
  - `docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`
- **Verification note:** Historical file remains canonical_contract_complete=false. Module-3 human review resolves the six discovery slots for the new registry without rewriting this historical audit.

### Asset 26 — Round-1 raw-bundle provenance validation summary

- **Workflow stage:** `canonical_evidence_and_provenance_closure`
- **Scientific role:** Deterministic provenance and semantic-identity validation for the 340 raw bundles.
- **Server path:** `/data/run01/scwb204/pchsi/scripts/p4_round1_raw_bundle_provenance_validation_v1_1/ROUND1_RAW_BUNDLE_PROVENANCE_VALIDATION_SUMMARY_V1.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** raw-bundle provenance validator v1.1
- **Downstream consumer:** Failure Memory design review and future evidence use
- **Population / file count:** 340 verified / 340; 0 rejected
- **Historical identity:** `FILE_SHA256:d2dc3fddba7425c356a269edae3be74c6afd57705c510fac65b113cf41206f0c`
- **Current verification SHA-256:** `d2dc3fddba7425c356a269edae3be74c6afd57705c510fac65b113cf41206f0c`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_raw_bundle_provenance_validation_v1_1/ROUND1_RAW_BUNDLE_PROVENANCE_VALIDATION_SUMMARY_V1.json`
- **Verification note:** provenance_validated=true and semantic_identity_validated=true; Memory generation remains unapproved.

### Asset 27 — Verified 340-bundle provenance manifest

- **Workflow stage:** `canonical_evidence_and_provenance_closure`
- **Scientific role:** Per-bundle byte, episode, seed and semantic identity resolution.
- **Server path:** `/data/run01/scwb204/pchsi/scripts/p4_round1_raw_bundle_provenance_validation_v1_1/ROUND1_VERIFIED_RAW_BUNDLE_MANIFEST_V1.jsonl`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** raw-bundle provenance validator v1.1
- **Downstream consumer:** future Failure Memory builder after design approval
- **Population / file count:** 340 JSONL rows
- **Historical identity:** `FILE_SHA256:65ff8ad426a6f817374743df543fe65304f8f8b81a5fce37c1f5f43ea762ae04`
- **Current verification SHA-256:** `65ff8ad426a6f817374743df543fe65304f8f8b81a5fce37c1f5f43ea762ae04`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_raw_bundle_provenance_validation_v1_1/ROUND1_VERIFIED_RAW_BUNDLE_MANIFEST_V1.jsonl`
- **Verification note:** Manifest resolves exact source-file bytes with registered aliases.

### Asset 28 — Full 340-bundle provenance validation archive

- **Workflow stage:** `canonical_evidence_and_provenance_closure`
- **Scientific role:** Sealed archive containing the full provenance manifest.
- **Server path:** `/data/home/scwb204/run/pchsi/scripts/p4_round1_raw_bundle_provenance_validation_v1_1`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** raw-bundle provenance validator v1.1
- **Downstream consumer:** future evidence consumers
- **Population / file count:** 4 files; 9837322 bytes
- **Historical identity:** `ROOT_SEAL:9a159ae0de742d9dc28e70ecf4754ffed1c659be9a1a9b8b9f5d967e59c28f71`
- **Current verification SHA-256:** `NOT_APPLICABLE_FOR_PACKAGE_TREE_OR_COMMIT_IDENTITY`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_WITH_ORIGINAL_SEAL`
- **Authority class:** `AUTHORITATIVE_RAW_OR_SEALED`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_canonical_artifact_contract_v1/ROUND1_ARCHIVE_ROOT_SEALS_V1.json`
- **Verification note:** Historical archive seal records the /data/home path. Do not normalize this historical path to /data/run01; the verified manifest separately records byte aliases.

### Asset 29 — Round-1 executed-history semantics audit

- **Workflow stage:** `canonical_evidence_and_provenance_closure`
- **Scientific role:** Clarifies full evidence history versus prompt-visible M0 history for all recorded calls.
- **Server path:** `/data/run01/scwb204/pchsi/scripts/p4_round1_executed_history_semantics_audit_v1/ROUND1_EXECUTED_HISTORY_SEMANTICS_AUDIT_V1.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** executed-history semantics auditor
- **Downstream consumer:** raw-bundle validator correction and Memory design
- **Population / file count:** 340 bundles; 3395 calls; 0 mismatches
- **Historical identity:** `FILE_SHA256:2ecfbf484a66829e0d9f63248200d6c8b4c75804f3453513970dcfc77d7c764f`
- **Current verification SHA-256:** `2ecfbf484a66829e0d9f63248200d6c8b4c75804f3453513970dcfc77d7c764f`
- **Status:** `COMPLETE`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_executed_history_semantics_audit_v1/ROUND1_EXECUTED_HISTORY_SEMANTICS_AUDIT_V1.json`
- **Verification note:** Historical audit preserves the older validator issue; later v1.1 raw-bundle validation verifies 340/340.

## Failure Memory Handoff Boundary

### Asset 30 — Failure Memory source-file inventory

- **Workflow stage:** `failure_memory_handoff_boundary`
- **Scientific role:** Source inventory prepared for future Memory design; not a Memory library.
- **Server path:** `/data/run01/scwb204/pchsi/scripts/p4_round1_failure_memory_source_inventory_v1/ROUND1_FAILURE_MEMORY_SOURCE_FILE_INDEX_V1.jsonl`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Failure Memory source inventory audit
- **Downstream consumer:** human-reviewed Failure Memory design
- **Population / file count:** 2555 source-file index rows
- **Historical identity:** `FILE_SHA256:078855abc0a12299a66052771165e607e0736673c0d49fd21488e84faebf63fa`
- **Current verification SHA-256:** `078855abc0a12299a66052771165e607e0736673c0d49fd21488e84faebf63fa`
- **Status:** `HOLD`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_failure_memory_source_inventory_v1/ROUND1_FAILURE_MEMORY_SOURCE_FILE_INDEX_V1.jsonl`
- **Verification note:** This is evidence preparation only. No Memory record has been generated.

### Asset 31 — Failure Memory sequence-truth audit

- **Workflow stage:** `failure_memory_handoff_boundary`
- **Scientific role:** Establishes which timeline structures can support future multi-step failure-memory records.
- **Server path:** `/data/run01/scwb204/pchsi/scripts/p4_round1_failure_memory_sequence_truth_audit_v1/ROUND1_FAILURE_MEMORY_SEQUENCE_TRUTH_AUDIT_V1.json`
- **Repository path:** `NOT_MIRRORED_IN_REPOSITORY`
- **Producer:** Failure Memory sequence-truth auditor
- **Downstream consumer:** human-reviewed Memory schema design
- **Population / file count:** 85 matched packs across four conditions
- **Historical identity:** `FILE_SHA256:a2ae1a410edf2e5772173f88fcf9303901bdfcff173a11f10357d91fe19e3804`
- **Current verification SHA-256:** `a2ae1a410edf2e5772173f88fcf9303901bdfcff173a11f10357d91fe19e3804`
- **Status:** `HOLD`
- **Retention:** `PRESERVE_EXACT_BYTES`
- **Authority class:** `AUTHORITATIVE_DETERMINISTIC_AUDIT`
- **Source evidence:**
  - `/data/run01/scwb204/pchsi/scripts/p4_round1_failure_memory_sequence_truth_audit_v1/ROUND1_FAILURE_MEMORY_SEQUENCE_TRUTH_AUDIT_V1.json`
- **Verification note:** All packs have complete timeline call ranges; detailed anchors are not complete-sequence authority. Memory generation remains unapproved pending human design review.

## Repository-Mirrored Evidence

| Logical asset | Repository entry | Role |
|---|---|---|
| Round-1 runtime and raw-policy implementation | [`src/pchsi/evaluation`](../../../src/pchsi/evaluation) | Repository implementation basis used by the Round-1 raw-policy runtime and evaluator lineage. |
| R132 strong-model proposal package | [`docs/audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/R132_PRIMARY117_IDENTITY_AUDIT_V1.json`](../../audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/R132_PRIMARY117_IDENTITY_AUDIT_V1.json) | Frozen 117-case strong-model proposal package feeding the Round-1 Q2 path. |
| Level-6 independent-challenger synthetic runtime seal | [`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`](HIERARCHICAL_ANALYSIS.md) | Synthetic runtime validation for the intended independent challenger path. |
| Round-1 canonical artifact-contract audit | [`docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md) | Historical audit of exact server slots, archive roots and repository lineage. |

## Retention Rules

- `PRESERVE_EXACT_BYTES`: retain the exact registered file bytes.
- `PRESERVE_WITH_ORIGINAL_SEAL`: preserve the complete historical archive under its original package or tree identity.
- `PRESERVE_AS_REPOSITORY_EVIDENCE`: retain the repository record and its Git lineage.
- `PRESERVE_AS_HISTORICAL_REFERENCE`: retain the artifact as historical evidence without promoting it to current scientific authority.
- `NAVIGATION_ONLY`: the record exists only to route readers to lower-level authoritative evidence.

## Known Historical Gaps

The historical canonical-artifact contract audit remains preserved with `canonical_contract_complete=false`.

Its six discovery slots were later reviewed during this repository consolidation. The new registry resolves the relevant major-asset entries without rewriting or replacing that historical audit file.

The Harness-OFF formal raw-evidence root has no standalone compact root result. Its identity is instead bound by the sealed 2724-file raw-evidence tree, four condition-level mechanical manifests and the downstream final-analysis bundle.

No final completed real-scientific-data Level-6 independent challenge result is registered.

Canonical evidence and provenance closure remains `IN_PROGRESS` at the project level even though the 340 raw bundles now have validated provenance and semantic identity.

Failure Memory remains `HOLD`. The source inventory and sequence-truth audit are evidence-preparation artifacts, not generated Memory records.

## Documentation Consumers

This registry is consumed by:

- [Round-1 Overview](./README.md)
- [Component Registry](./COMPONENT_REGISTRY.md)
- [Hierarchical Analysis Ledger](./HIERARCHICAL_ANALYSIS.md)
- [Asset Consolidation Ledger](./ASSET_CONSOLIDATION_LEDGER.md)
- [Project Experiment Ledger](../../experiments/EXPERIMENT_LEDGER.md)
- [Project Code Map](../../code_map.md)
- [Current Round-1 Provenance Audit](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md)

The root README is a navigation and high-level-status document; it should link here rather than duplicate this complete registry.
