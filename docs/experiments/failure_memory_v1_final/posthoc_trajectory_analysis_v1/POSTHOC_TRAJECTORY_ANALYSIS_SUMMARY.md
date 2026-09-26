# Failure Memory Post-hoc Trajectory Analysis

**Status:** post-hoc descriptive analysis only.

This analysis does not alter preregistered Q1-Q3 decisions, does not create Benefit/Harm authority, and does not authorize Analyzer, Researcher, training, promotion, or rollback.

## Input integrity

- Scientific execution head: `f3fdfd224bfc51db7b8c7580d60c7dce5253ebc8`
- Live cell results analyzed: **1348**
- Stages observed: STAGE_1B_FROZEN_POLICY_FM0_FM3, STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY, STAGE_3_FROZEN_FORMAL_EVALUATION
- Cells with discoverable step-level traces: **0 / 1348**

## Primary question: did Memory reduce repeated attempts?

The primary always-available proxies are paired changes in `model_calls` and `environment_steps`. Negative deltas mean the treatment used fewer attempts/steps than its matched reference.

| Stage | Split | Reference | Treatment | Subset | Pairs | Δ model calls mean/median | Δ env steps mean/median | Shorter | Same | Longer | Mixed |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM0_NO_MEMORY | FM1_MATCHED_RAW_EPISODIC | ALL_PAIRS | 3 | -5.000 / 0.000 | -6.667 / 0.000 | 1 | 1 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM0_NO_MEMORY | FM1_MATCHED_RAW_EPISODIC | DIRECT_EXPOSURE_TREATMENT | 3 | -5.000 / 0.000 | -6.667 / 0.000 | 1 | 1 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM0_NO_MEMORY | FM2_STRUCTURED_DESCRIPTIVE | ALL_PAIRS | 3 | -7.333 / 0.000 | -8.333 / 0.000 | 1 | 1 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM0_NO_MEMORY | FM2_STRUCTURED_DESCRIPTIVE | DIRECT_EXPOSURE_TREATMENT | 3 | -7.333 / 0.000 | -8.333 / 0.000 | 1 | 1 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM0_NO_MEMORY | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 3 | -6.667 / 0.000 | -8.333 / 0.000 | 1 | 1 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM0_NO_MEMORY | FM3_GATED_PRESCRIPTIVE | DIRECT_EXPOSURE_TREATMENT | 3 | -6.667 / 0.000 | -8.333 / 0.000 | 1 | 1 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM1_MATCHED_RAW_EPISODIC | FM2_STRUCTURED_DESCRIPTIVE | ALL_PAIRS | 3 | -2.333 / -1.000 | -1.667 / -1.000 | 2 | 0 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM1_MATCHED_RAW_EPISODIC | FM2_STRUCTURED_DESCRIPTIVE | DIRECT_EXPOSURE_TREATMENT | 3 | -2.333 / -1.000 | -1.667 / -1.000 | 2 | 0 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM1_MATCHED_RAW_EPISODIC | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 3 | -1.667 / -1.000 | -1.667 / -1.000 | 2 | 0 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM1_MATCHED_RAW_EPISODIC | FM3_GATED_PRESCRIPTIVE | DIRECT_EXPOSURE_TREATMENT | 3 | -1.667 / -1.000 | -1.667 / -1.000 | 2 | 0 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM2_STRUCTURED_DESCRIPTIVE | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 3 | 0.667 / 0.000 | 0.000 / 0.000 | 0 | 2 | 1 | 0 |
| STAGE_1B_FROZEN_POLICY_FM0_FM3 | TRAIN_RETRIEVAL_DEV | FM2_STRUCTURED_DESCRIPTIVE | FM3_GATED_PRESCRIPTIVE | DIRECT_EXPOSURE_TREATMENT | 3 | 0.667 / 0.000 | 0.000 / 0.000 | 0 | 2 | 1 | 0 |
| STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY | TRAIN_MEMORY_SOURCE | ROUND_0 | ROUND_1 | ALL_PAIRS | 60 | 1.050 / 0.000 | 0.883 / 0.000 | 1 | 55 | 4 | 0 |
| STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY | TRAIN_MEMORY_SOURCE | ROUND_0 | ROUND_2 | ALL_PAIRS | 60 | 0.017 / 0.000 | 0.000 / 0.000 | 2 | 54 | 4 | 0 |
| STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY | TRAIN_MEMORY_SOURCE | ROUND_0 | ROUND_3 | ALL_PAIRS | 60 | 0.700 / 0.000 | 0.450 / 0.000 | 1 | 56 | 3 | 0 |
| STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY | TRAIN_MEMORY_SOURCE | ROUND_1 | ROUND_2 | ALL_PAIRS | 60 | -1.033 / 0.000 | -0.883 / 0.000 | 4 | 54 | 2 | 0 |
| STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY | TRAIN_MEMORY_SOURCE | ROUND_1 | ROUND_3 | ALL_PAIRS | 60 | -0.350 / 0.000 | -0.433 / 0.000 | 2 | 56 | 2 | 0 |
| STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY | TRAIN_MEMORY_SOURCE | ROUND_2 | ROUND_3 | ALL_PAIRS | 60 | 0.683 / 0.000 | 0.450 / 0.000 | 2 | 54 | 4 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_SEEN | FM0_NO_MEMORY | FM1_MATCHED_RAW_EPISODIC | ALL_PAIRS | 140 | 0.007 / 0.000 | -0.086 / 0.000 | 5 | 131 | 4 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_SEEN | FM0_NO_MEMORY | FM2_STRUCTURED_DESCRIPTIVE | ALL_PAIRS | 140 | 0.036 / 0.000 | 0.000 / 0.000 | 8 | 127 | 5 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_SEEN | FM0_NO_MEMORY | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 140 | 0.093 / 0.000 | -0.029 / 0.000 | 4 | 133 | 3 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_SEEN | FM1_MATCHED_RAW_EPISODIC | FM2_STRUCTURED_DESCRIPTIVE | ALL_PAIRS | 140 | 0.029 / 0.000 | 0.086 / 0.000 | 7 | 131 | 2 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_SEEN | FM1_MATCHED_RAW_EPISODIC | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 140 | 0.086 / 0.000 | 0.057 / 0.000 | 3 | 133 | 4 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_SEEN | FM2_STRUCTURED_DESCRIPTIVE | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 140 | 0.057 / 0.000 | -0.029 / 0.000 | 2 | 132 | 6 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_UNSEEN | FM0_NO_MEMORY | FM1_MATCHED_RAW_EPISODIC | ALL_PAIRS | 134 | -0.172 / 0.000 | -0.201 / 0.000 | 1 | 130 | 3 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_UNSEEN | FM0_NO_MEMORY | FM2_STRUCTURED_DESCRIPTIVE | ALL_PAIRS | 134 | 0.112 / 0.000 | 0.157 / 0.000 | 4 | 125 | 5 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_UNSEEN | FM0_NO_MEMORY | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 134 | 0.067 / 0.000 | 0.052 / 0.000 | 1 | 127 | 6 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_UNSEEN | FM1_MATCHED_RAW_EPISODIC | FM2_STRUCTURED_DESCRIPTIVE | ALL_PAIRS | 134 | 0.284 / 0.000 | 0.358 / 0.000 | 4 | 126 | 4 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_UNSEEN | FM1_MATCHED_RAW_EPISODIC | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 134 | 0.239 / 0.000 | 0.254 / 0.000 | 1 | 129 | 4 | 0 |
| STAGE_3_FROZEN_FORMAL_EVALUATION | VALID_UNSEEN | FM2_STRUCTURED_DESCRIPTIVE | FM3_GATED_PRESCRIPTIVE | ALL_PAIRS | 134 | -0.045 / 0.000 | -0.104 / 0.000 | 1 | 128 | 5 | 0 |

## Attribution boundary

- `DIRECT_EXPOSURE_TREATMENT` is the only subset where a treatment cell actually reports `memory_exposed=1`.
- When coverage/exposure is zero (notably the registered Stage 2/3 result), trajectory differences must **not** be causally attributed to Memory.
- A shorter rollout without task rescue is reported as process efficiency only; it is not a successful repair.

## Step-level trace diagnostics

- Trace-linked cells: 0
- JSON files scanned: 6806
- Candidate trace files found: 0
- No trustworthy step-level action trace was discoverable from the sealed artifacts. Repetition/loop/edit-distance metrics are therefore left unavailable rather than inferred.

## Interpretation

Use this report to answer whether representation/exposure changed rollout dynamics even when binary success did not change. Treat any patterns as descriptive hypotheses for the next Analyzer + same-state verifier stage, not as retroactive support for Q1-Q3.
