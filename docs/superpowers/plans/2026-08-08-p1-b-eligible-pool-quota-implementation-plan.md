# P1-B Eligible-Pool SELECT Quota Amendment V1 — Implementation Plan

Execute only after the design amendment is reviewed.

## Goal

Replace the infeasible absolute family quota with an eligible-pool quota,
without changing the frozen salt, split-key payload, access rules, runtime,
evaluator, or seed schedule.

## Files

Modify:

```text
configs/evaluation/schemas/p1_b_split_contract_v1.json
src/pchsi/evaluation/p1b_split.py
tests/evaluation/test_p1b_split.py
```

Do not modify Runtime Core, task loader, policy condition, condition schedule
or episode evaluator.

## RED tests

Add:

```text
N=24, forced=18, E=6 -> target=2
N=17, forced=16, E=1 -> target=1
N>0, forced=N, E=0 -> P1_B_SPLIT_INFEASIBLE_NO_ELIGIBLE_SELECT
```

Run `python -m pytest -q tests/evaluation/test_p1b_split.py` and require RED.

## GREEN implementation

Freeze:

```python
def select_target_for_eligible(eligible_count: int) -> int:
    if eligible_count <= 0:
        raise P1BSplitInfeasibleError(
            "P1_B_SPLIT_INFEASIBLE_NO_ELIGIBLE_SELECT"
        )
    return max(1, eligible_count // 3)
```

For each family:

```text
forced = reviewed forced-DEV rows
nonforced = all remaining rows
E_f = len(nonforced)
target = select_target_for_eligible(E_f)
sort nonforced by (split_key_sha256, manifest_index)
first target -> SELECT
rest -> DEV
```

Update the schema `family_rule` string to:

```text
E_f=N_f-F_f; require E_f>0; SELECT_TARGET=max(1,floor(E_f/3))
```

Keep schema identity, salt, sort rule and forced-dev flags unchanged.

## Verification

Run:

```bash
python -m pytest -q tests/evaluation/test_p1b_split.py
python -m pytest -q
python -m compileall -q src tests scripts
git diff --check
```

Block if split logic references result/outcome fields, the salt changes, the
split-key payload changes, or Runtime Core/task loader changes.

Suggested focused commit:

```text
Use eligible pool for P1-B SELECT quota
```

Completion does not authorize historical materialization or model execution.
