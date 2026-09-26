# Failure Memory Token-Budget Feasibility Range Extension V1

Date: 2026-08-19

```text
STATUS = PRE-OUTCOME FEASIBILITY AMENDMENT
MEMORY_ON_EXECUTED = false
PERFORMANCE_ESTIMAND = NO_PERFORMANCE_ESTIMAND
```

## Trigger

The originally frozen single-record candidate grid:

```text
256, 384, 512, 640, 768
```

failed the frozen 90% feasibility criterion on the already frozen first
30 train-side failures.

Complete-window FM1 token counts:

```text
360,382,403,412,414,414,415,421,421,434,
451,490,505,616,682,718,749,805,818,836,
840,846,850,867,3073,3626,4061,4437,5017,5789
```

Required coverage:

```text
27 / 30 = 90%
```

Empirical threshold:

```text
4061
```

Original maximum 768 covers:

```text
17 / 30
```

Library three-record FM2 pack counts:

```text
360,371,386,389,390,395,396,402,409,420
```

## Range extension

Single-record candidates become:

```text
256,384,512,640,768,1024,2048,4096
```

Library-total candidates remain:

```text
384,512,640,768
```

Coverage target remains:

```text
0.90
```

Maximum library record count remains:

```text
3
```

The generic Package-B single-record projection envelope is extended to 4096.

## Expected mechanical result

From the already frozen calibration statistics:

```text
<=2048 = 24/30
<=4096 = 27/30
```

Therefore the existing selection rule is expected to choose:

```text
single-record = 4096
```

For library packs:

```text
<=512 = 10/10
```

so the expected library-total choice is:

```text
512
```

These are expectations only. The normal token-budget contract builder must
still independently recompute and publish the final contract and SHA.

## Non-changes

```text
coverage target = 0.90

FM1 complete-window fidelity = required
FM1 event truncation = forbidden
FM1 LLM compression = forbidden
FM1 post-hoc excerpt selection = forbidden

whole-record packing = required
mid-record truncation = forbidden

NO_PERFORMANCE_ESTIMAND = unchanged
Memory-ON outcome use = forbidden
valid_seen use = forbidden
valid_unseen use = forbidden
Benefit/Harm use = forbidden
```

The three FM1 views above 4096 remain unavailable:

```text
4437
5017
5789
```

This amendment therefore does not convert the protocol into a 100%-coverage
rule.

## Total rendered prompt

4096 is a Memory-slot ceiling, not a total prompt guarantee.

Before any Package-B Memory-ON scientific execution, the final selected
representation cells must pass a separate rendered-prompt token census against
the frozen policy/runtime context boundary.
