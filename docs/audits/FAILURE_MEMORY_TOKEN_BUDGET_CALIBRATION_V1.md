# Failure Memory Token-Budget Calibration V1

## Authority

This is a pre-outcome train-side representation-feasibility calibration.

```text
NO_PERFORMANCE_ESTIMAND
MEMORY_ON_EXECUTION_USED=false
VALID_SEEN_USED=false
VALID_UNSEEN_USED=false
```

## Frozen sample

Calibration failures:

`30`

Valid safety-clean Analyzer-localized representation records:

`30`

Selection rule:

`FIRST_30_FAILURES_IN_PRE_FROZEN_TRAIN_MEMORY_SOURCE_PANEL_ORDER_V1`

Source-panel SHA-256:

`1d84ac1dc76a01495fab2aa344e077cf35fe54d32d7164e85a240996608730ea`

Calibration failure-panel SHA-256:

`bdcf1030b9a991fedbcf240e96e48173ef15e5f6f4d486e7e8b8df324b831b76`

Analyzer prompt SHA-256:

`67383b0ea054394bbe7dade69599f843ee1619f035ec7cce30efb488cc1f7f82`

Analyzer model:

`gpt-5.6-sol`

Analyzer outputs are `CALIBRATION_ONLY_ANALYZER_PROPOSAL` and do not become
active Memory authority.

## Candidate budgets

Single-record:

`256, 384, 512, 640, 768`

Library total:

`384, 512, 640, 768`

Coverage target:

`0.90`

Max library records:

`3`

FM1 truncation:

`FORBIDDEN`

FM1 LLM compression:

`FORBIDDEN`

FM1 post-hoc excerpt selection:

`FORBIDDEN`

## Frozen observed lengths

FM1 complete-window token counts:

`[616, 451, 415, 414, 682, 421, 4437, 3073, 749, 840, 490, 360, 850, 3626, 382, 836, 5017, 805, 4061, 403, 867, 818, 421, 434, 846, 5789, 718, 414, 505, 412]`

FM2 descriptive token counts:

`[149, 129, 125, 128, 139, 130, 120, 124, 117, 139, 134, 114, 132, 146, 132, 132, 127, 132, 143, 115, 114, 127, 139, 130, 140, 152, 129, 118, 145, 127]`

Consecutive three-record FM2 pack counts:

`[402, 396, 360, 386, 409, 390, 371, 395, 420, 389]`

## Selected budgets

Single-record hard ceiling:

`4096`

Library-total hard ceiling:

`512`

Contract SHA-256:

`613166c9f092795cb03c892ee0046f0af5bf7fc13ba44f7fccb950027c329262`

These values were frozen before any π1 Memory-ON scientific execution.

No task-success, Benefit/Harm, benchmark, valid_seen or valid_unseen result was
used to select these token ceilings.
