# P1-B Eligible-Pool SELECT Quota Amendment V1

**Status:** design amendment candidate; no experiment execution authorization.

**Parent design:** `docs/superpowers/specs/2026-08-08-p1-b-access-and-evidence-v1-design.md`

## Trigger

The historical-access cohort audit established a conservative forced-development
union of 77 tasks:

- historical diagnostic Top50 = 50
- frozen V7C dev35 = 35
- overlap = 8
- forced union = 77

The original rule `SELECT_TARGET_f = max(1, floor(N_f / 3))` is already
infeasible in three families after removing those forced-development tasks:

- pick_and_place_simple: N=24, forced=18, remaining=6, old target=8
- pick_clean_then_place_in_recep: N=31, forced=22, remaining=9, old target=10
- pick_two_obj_and_place: N=17, forced=16, remaining=1, old target=5

Therefore the old split must fail closed. Salt changes, result-dependent task
movement, quota borrowing, or removing historical-access evidence are forbidden.

## Amended denominator

After the final reviewed historical-access audit is frozen, define for each
task family `f`:

```text
N_f = all current candidate tasks in family f
F_f = forced DEV tasks in family f
E_f = N_f - F_f = tasks still eligible for deterministic DEV/SELECT allocation
```

If `E_f == 0`, fail closed with:

```text
P1_B_SPLIT_INFEASIBLE_NO_ELIGIBLE_SELECT
```

If `E_f > 0`, freeze:

```text
SELECT_TARGET_f = max(1, floor(E_f / 3))
```

Then:

1. remove forced DEV;
2. sort eligible tasks by `(split_key_sha256, manifest_index)`;
3. first `SELECT_TARGET_f` -> `SELECT_SUMMARY_ONLY`;
4. all remaining eligible tasks -> `DEV_VISIBLE`.

The frozen split salt remains exactly:

```text
P1_B_ACCESS_SPLIT_V1|effb7c0b25002321a7c123376c53890731ee19a9
```

The split-key payload, canonical JSON, family stratification and tie-breaking
remain unchanged. No historical or current outcome may enter the split key.

## One-time timing rule

Quota computation happens only after the authoritative forced-DEV audit is
frozen. The current 77-task cohort union is a feasibility trigger, not the
final split input. Additional forced tasks may still be discovered before
the historical audit is frozen.

After TaskAccessManifest, split contract and split proof are frozen:

- no task movement;
- no quota recomputation;
- no salt replacement;
- no adaptive expansion.

## Provisional lower-bound counts

| Family | N_f | forced lower bound | E_f | amended target |
|---|---:|---:|---:|---:|
| look_at_obj_in_light | 18 | 0 | 18 | 6 |
| pick_and_place_simple | 24 | 18 | 6 | 2 |
| pick_clean_then_place_in_recep | 31 | 22 | 9 | 3 |
| pick_cool_then_place_in_recep | 21 | 11 | 10 | 3 |
| pick_heat_then_place_in_recep | 23 | 10 | 13 | 4 |
| pick_two_obj_and_place | 17 | 16 | 1 | 1 |

Provisional totals under this lower-bound forced set:

```text
forced DEV = 77
eligible pool = 57
SELECT = 19
hash-assigned DEV = 38
total DEV = 115
```

These totals are not authoritative until the final forced-DEV audit is frozen.

## Claim boundary

All 134 tasks have historical external-model exposure after the reviewed
legacy/current identity crosswalk. This strict-134 pool is therefore not a
confirmatory-sealed benchmark. The reduced pilot remains developmental.
SELECT is a frozen internal selection/acceptance set, not a contamination-free
confirmatory benchmark.

## Implementation impact

Update only the deterministic split contract:

- `configs/evaluation/schemas/p1_b_split_contract_v1.json`
- `src/pchsi/evaluation/p1b_split.py`
- `tests/evaluation/test_p1b_split.py`
- directly dependent split tests if necessary

Required invariants:

- target uses `E_f`, not `N_f`;
- `E_f == 0` fails closed;
- forced tasks never receive split rank;
- same frozen salt and split-key payload;
- no result/outcome fields in split logic.

No task materialization or experiment execution is authorized by this amendment.
