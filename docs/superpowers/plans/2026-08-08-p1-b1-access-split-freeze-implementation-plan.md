# P1-B1 任务访问、固定拆分与运行身份 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不读取当前 π0 结果、不运行模型的前提下，实现 legacy/current task 身份对照、历史访问证据治理、forced DEV、固定 salt 的六类 task 拆分、当前数据血缘、P4-R0-PI0 条件和 seed-17 DEV schedule 的离线冻结工具。

**Architecture:** P1-B1 只做“任务是谁、过去接触过什么、当前属于开发还是选择、将来用哪个 π0 条件和 seed 运行”的离线治理。它复用 P1-A 已合并的 `HistoricalAccessAuditV1`、`TaskAccessManifestV1`、`PolicyConditionManifestV1`、`ConditionRunScheduleV1` 与 canonical SHA-256 工具；所有 legacy 证据必须先被显式输入，工具不得扫描历史仓库并自行推断“看过/没看过”。

**Tech Stack:** Python 3.12 standard library, frozen/slotted dataclasses, existing canonical JSON/schema validator, pytest.

## Global Constraints

- Parent design merge commit: `eef94f4b4f15b6d7be4420c346cbd7145605e677`.
- Parent spec: `docs/superpowers/specs/2026-08-08-p1-b-access-and-evidence-v1-design.md`.
- P1-A governance implementation is frozen on `main`.
- `strict-134` is a candidate task pool, not an automatic access class.
- Current strict-134 manifest SHA-256 is `6e480bb663a6f17207aa2c7a6e1b504adad8448f6e8a2615c5e62fea0b64c0f4`.
- Frozen split salt is exactly `P1_B_ACCESS_SPLIT_V1|effb7c0b25002321a7c123376c53890731ee19a9`.
- `TRAJECTORY_INSPECTED` or `USED_FOR_METHOD_DESIGN` forces `DEV_VISIBLE`.
- Legacy task-level access evidence may affect access flags / forced DEV / confirmatory eligibility only.
- Legacy success/failure, trajectory semantics, old taxonomy, old teacher outputs and old method performance must never influence hash split or current data.
- P1 DEV replicate seed schedule is exactly `(17,)`.
- P1 DEV seed 17 is non-adaptive.
- P4 SELECT evaluation seeds are outside this plan and will be frozen separately before SELECT.
- No ALFWorld, vLLM, teacher API, training, SELECT or trajectory collection is permitted in this plan.
- Do not modify Runtime Core semantics.
- Do not modify legacy `build_e1_run_schedule()` semantics.
- Do not scan `raw_results/`, reports, or historical repositories to infer labels during production execution.
- All automatic decisions must be reproducible from explicit input artifacts.
- Every task follows RED → GREEN → full regression → static audit → focused commit.

## Planned File Map

Create:

```text
configs/evaluation/schemas/
├── legacy_current_task_crosswalk_v1.json
├── p1_b_split_contract_v1.json
├── p1_b_split_proof_v1.json
└── current_pilot_data_lineage_v1.json

src/pchsi/evaluation/
├── p1b_access_crosswalk.py
├── p1b_split.py
├── p1b_access_materializer.py
└── p1b_lineage.py

scripts/evaluation/
└── materialize_p1b_access.py

tests/evaluation/
├── test_p1b_access_crosswalk.py
├── test_p1b_split.py
├── test_p1b_access_materializer.py
├── test_p1b_lineage.py
└── test_materialize_p1b_access.py
```

Modify:

```text
src/pchsi/evaluation/policy_condition.py
tests/evaluation/test_policy_condition.py
tests/evaluation/test_evaluation_schema_inventory.py
```

The `policy_condition.py` modification is a compatibility correction: the logical condition ID is `P4-R0-PI0`, while the already frozen and smoke-tested vLLM served model string remains `Qwen2.5-3B-Instruct-E1`. Do not create a new untested service alias merely to make the condition ID and transport model string identical.

---

### Task 1: Reconcile P4-R0-PI0 logical identity with the frozen vLLM service identity

**Files:**
- Modify: `src/pchsi/evaluation/policy_condition.py`
- Modify: `tests/evaluation/test_policy_condition.py`
- Modify: `tests/evaluation/test_condition_run_schedule.py`
- Modify: `tests/evaluation/test_distillation_governance.py`

**Interfaces:**
- Consumes: frozen E1 runtime identity `Qwen2.5-3B-Instruct-E1`.
- Produces: `PolicyConditionManifestV1` that binds logical condition `P4-R0-PI0` to the actual frozen transport service identity.

- [ ] **Step 1: Add RED test for the actual frozen service identity**

Append:

```python
def test_pi0_condition_accepts_frozen_e1_served_model_name() -> None:
    payload = pi0().to_dict()
    payload["served_model_name"] = "Qwen2.5-3B-Instruct-E1"

    observed = PolicyConditionManifestV1.from_dict(payload)

    assert observed.policy_condition_id == "P4-R0-PI0"
    assert observed.served_model_name == "Qwen2.5-3B-Instruct-E1"
```

- [ ] **Step 2: Prove RED**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_policy_condition.py::test_pi0_condition_accepts_frozen_e1_served_model_name
```

Expected: FAIL because the current P1-A hardening requires the synthetic `Qwen2.5-3B-Instruct-P4-R0-PI0` string.

- [ ] **Step 3: Minimal compatibility correction**

Change only the canonical π0 served model constant to:

```python
_PI0_SERVED_NAME = "Qwen2.5-3B-Instruct-E1"
```

Update every existing P1-A governance/schedule test fixture that constructs
`P4-R0-PI0` so the canonical π0 fixture uses the same frozen runtime
service string. This is a fixture compatibility update only; do not
weaken any schedule or governance assertion.

Keep all other P1-A hardening:

```text
P4-R0-PI0
→ BASE_MODEL
→ training_method NONE
→ policy_version pi0
→ MEMORY_M0_V1
→ frozen served_model_name
```

- [ ] **Step 4: Focused GREEN and regression**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_policy_condition.py \
  tests/evaluation/test_condition_run_schedule.py \
  tests/evaluation/test_distillation_governance.py

python -m pytest -q
python -m compileall -q src tests scripts
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add -- \
  src/pchsi/evaluation/policy_condition.py \
  tests/evaluation/test_policy_condition.py

git commit \
  -m "Align P1 pi0 condition with frozen service identity"
```

---

### Task 2: LegacyCurrentTaskCrosswalkV1

**Files:**
- Create: `configs/evaluation/schemas/legacy_current_task_crosswalk_v1.json`
- Create: `src/pchsi/evaluation/p1b_access_crosswalk.py`
- Create: `tests/evaluation/test_p1b_access_crosswalk.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Consumes: explicit legacy inventory records supplied by the caller and current `FrozenTaskRecord`.
- Produces: `LegacyCurrentTaskCrosswalkV1`.

Freeze enums:

```python
class LegacyMatchStatus(str, Enum):
    EXACT_GAMEFILE_SHA1_MATCH = "EXACT_GAMEFILE_SHA1_MATCH"
    EXACT_TASK_ID_AND_PATH_MATCH = "EXACT_TASK_ID_AND_PATH_MATCH"
    TASK_ID_ONLY_INSUFFICIENT = "TASK_ID_ONLY_INSUFFICIENT"
    NO_MATCH = "NO_MATCH"
    LEGACY_RECORD_INCOMPLETE = "LEGACY_RECORD_INCOMPLETE"
```

Records must contain:

```text
legacy_source
legacy_task_id
legacy_gamefile
legacy_gamefile_sha1
current_manifest_index
current_task_id
current_gamefile
current_gamefile_sha1
manual_same_gamefile_confirmed
match_status
evidence_source
confidence_class
```

`manual_same_gamefile_confirmed` is required only for the
`EXACT_TASK_ID_AND_PATH_MATCH` route. It is reviewed evidence, not an automatic
inference made by the matcher.

- [ ] **Step 1: RED exact-SHA matching test**

```python
def test_crosswalk_exact_sha1_match_is_high_confidence() -> None:
    record = match_legacy_to_current(
        legacy=LegacyTaskIdentityV1(
            legacy_source="alfworld-api-model-trajectory-analysis",
            legacy_task_id="alfworld_valid_unseen_all134_0000",
            legacy_gamefile="/legacy/task/game.tw-pddl",
            legacy_gamefile_sha1="a" * 40,
            evidence_source="legacy-inventory:0",
        ),
        current=_current_record(
            index=0,
            gamefile_sha1="a" * 40,
        ),
    )

    assert record.match_status is LegacyMatchStatus.EXACT_GAMEFILE_SHA1_MATCH
    assert record.confidence_class == "HIGH"
```

- [ ] **Step 2: RED no-guess test**

```python
def test_task_id_only_is_insufficient() -> None:
    record = match_legacy_to_current(
        legacy=_legacy(
            task_id="alfworld_valid_unseen_all134_0000",
            gamefile=None,
            sha1=None,
        ),
        current=_current_record(index=0),
    )

    assert record.match_status is LegacyMatchStatus.TASK_ID_ONLY_INSUFFICIENT
    assert record.confidence_class != "HIGH"
```

- [ ] **Step 3: Implement strict schema/model**

Rules:

```text
exact SHA-1 equality
→ EXACT_GAMEFILE_SHA1_MATCH

exact task ID + exact canonical gamefile path
+ manual_same_gamefile_confirmed = true
→ EXACT_TASK_ID_AND_PATH_MATCH

exact task ID + exact path without reviewed confirmation
→ TASK_ID_ONLY_INSUFFICIENT

task ID only
→ TASK_ID_ONLY_INSUFFICIENT

incomplete legacy identity
→ LEGACY_RECORD_INCOMPLETE

otherwise
→ NO_MATCH
```

No fuzzy path matching, basename-only matching, suffix matching, casefold or
automatic repair. The matcher must never create the manual confirmation flag.

- [ ] **Step 4: Update exact schema inventory**

Add only:

```text
legacy_current_task_crosswalk_v1.json
→ LEGACY_CURRENT_TASK_CROSSWALK_V1
```

Keep exact equality.

- [ ] **Step 5: GREEN, full regression, commit**

```bash
python -m pytest -q tests/evaluation/test_p1b_access_crosswalk.py
python -m pytest -q
python -m compileall -q src tests
git diff --check

git add -- \
  configs/evaluation/schemas/legacy_current_task_crosswalk_v1.json \
  src/pchsi/evaluation/p1b_access_crosswalk.py \
  tests/evaluation/test_p1b_access_crosswalk.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git commit -m "Add P1-B legacy task identity crosswalk"
```

---

### Task 3: Forced DEV and deterministic family-stratified split proof

**Files:**
- Create: `configs/evaluation/schemas/p1_b_split_contract_v1.json`
- Create: `configs/evaluation/schemas/p1_b_split_proof_v1.json`
- Create: `src/pchsi/evaluation/p1b_split.py`
- Create: `tests/evaluation/test_p1b_split.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Consumes: `HistoricalAccessAuditV1`, current ordered `FrozenTaskRecord` tuple.
- Produces: `P1BSplitContractV1`, `P1BSplitProofV1`, deterministic access assignment.

Freeze:

```python
P1_B_SPLIT_SALT = (
    "P1_B_ACCESS_SPLIT_V1|"
    "effb7c0b25002321a7c123376c53890731ee19a9"
)
```

`split_key_sha256` payload:

```python
{
    "schema_id": "P1_B_TASK_SPLIT_KEY_V1",
    "salt": P1_B_SPLIT_SALT,
    "task_type": record.task_type,
    "task_id": record.task_id,
    "gamefile_sha1": record.gamefile_sha1,
}
```

- [ ] **Step 1: RED forced-DEV tests**

```python
@pytest.mark.parametrize(
    "flag",
    [
        HistoricalAccessFlag.TRAJECTORY_INSPECTED,
        HistoricalAccessFlag.USED_FOR_METHOD_DESIGN,
    ],
)
def test_explicitly_inspected_or_method_design_task_is_forced_dev(
    flag,
) -> None:
    result = assign_p1b_access(
        records=_records_one_family(6),
        audit=_audit_with_flag(task_index=2, flag=flag),
    )

    assert result.assignment_for(2).forced_dev is True
    assert (
        result.assignment_for(2).access_class
        is DistillationAccessClass.DEV_VISIBLE
    )
```

- [ ] **Step 2: RED deterministic salt test**

```python
def test_split_key_matches_frozen_canonical_formula() -> None:
    record = _record(index=3)

    expected = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_id": "P1_B_TASK_SPLIT_KEY_V1",
                "salt": P1_B_SPLIT_SALT,
                "task_type": record.task_type,
                "task_id": record.task_id,
                "gamefile_sha1": record.gamefile_sha1,
            }
        )
    )

    assert split_key_sha256(record) == expected
```

- [ ] **Step 3: RED family quota and infeasible split tests**

```python
def test_select_target_is_floor_one_third_per_family() -> None:
    assert select_target(2) == 1
    assert select_target(3) == 1
    assert select_target(8) == 2
    assert select_target(12) == 4


def test_split_fails_closed_when_forced_dev_exhausts_select_quota() -> None:
    with pytest.raises(P1BSplitInfeasibleError):
        assign_p1b_access(
            records=_records_one_family(3),
            audit=_audit_all_forced_dev(3),
        )
```

- [ ] **Step 4: Implement exact rules**

For each family:

```text
N_f = total current candidate tasks in family
SELECT_TARGET_f = max(1, floor(N_f / 3))
remove forced DEV
sort remaining by (split_key_sha256, manifest_index)
first SELECT_TARGET_f → SELECT_SUMMARY_ONLY
rest → DEV_VISIBLE
```

Do not read any result field.

Proof rows must include:

```text
manifest_index
task_id
task_type
gamefile_sha1
historical_access_flags
historical_evidence_sources
forced_dev
forced_dev_reason or null
forced_dev_evidence_sources
split_key_sha256 or null for forced DEV
family_select_target
family_rank among non-forced tasks or null
final_access_class
```

When `forced_dev=true`:

- `forced_dev_reason` is exactly `TRAJECTORY_INSPECTED`,
  `USED_FOR_METHOD_DESIGN`, or both in frozen order;
- `forced_dev_evidence_sources` is non-empty;
- the sources are copied from the reviewed task-level audit input;
- the split tool must not invent or discover evidence sources.

- [ ] **Step 5: Update schema inventory, GREEN and commit**

```bash
python -m pytest -q tests/evaluation/test_p1b_split.py
python -m pytest -q
python -m compileall -q src tests
git diff --check

git add -- \
  configs/evaluation/schemas/p1_b_split_contract_v1.json \
  configs/evaluation/schemas/p1_b_split_proof_v1.json \
  src/pchsi/evaluation/p1b_split.py \
  tests/evaluation/test_p1b_split.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git commit -m "Add frozen P1-B task split proof"
```

---

### Task 4: Build TaskAccessManifestV1 from the audited split

**Files:**
- Create: `src/pchsi/evaluation/p1b_access_materializer.py`
- Create: `tests/evaluation/test_p1b_access_materializer.py`

**Interfaces:**
- Consumes: exact current task records, `HistoricalAccessAuditV1`, `P1BSplitProofV1`.
- Produces: `TaskAccessManifestV1`.

- [ ] **Step 1: RED exact permission tests**

```python
def test_materialized_dev_permissions_are_exact() -> None:
    manifest = materialize_task_access_manifest(
        records=_records(),
        audit=_audit(),
        split_proof=_proof(),
    )

    dev = next(
        item for item in manifest.records
        if item.access_class is DistillationAccessClass.DEV_VISIBLE
    )

    assert (
        dev.teacher_call_permitted,
        dev.training_permitted,
        dev.select_evaluation_permitted,
        dev.confirmatory_permitted,
    ) == (True, True, False, False)
```

```python
def test_materialized_select_permissions_are_exact() -> None:
    ...
    assert permissions == (False, False, True, False)
```

- [ ] **Step 2: Reject proof/audit identity mismatch**

Test:

```text
task ID mismatch
gamefile mismatch
historical flags mismatch
missing audit row
extra audit row
split proof hash mismatch
```

All must fail closed.

- [ ] **Step 3: Implement**

Every current strict-134 task must have exactly one audit row and exactly one split-proof row.

This plan does not materialize `CONFIRMATORY_SEALED`.

- [ ] **Step 4: GREEN and commit**

```bash
python -m pytest -q tests/evaluation/test_p1b_access_materializer.py
python -m pytest -q
git diff --check

git add -- \
  src/pchsi/evaluation/p1b_access_materializer.py \
  tests/evaluation/test_p1b_access_materializer.py

git commit -m "Materialize P1-B task access manifest"
```

---

### Task 5: Current pilot data lineage, P4-R0-PI0 manifest and seed-17 DEV schedule

**Files:**
- Create: `configs/evaluation/schemas/current_pilot_data_lineage_v1.json`
- Create: `src/pchsi/evaluation/p1b_lineage.py`
- Create: `tests/evaluation/test_p1b_lineage.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Produces: `CurrentPilotDataLineageV1`, `build_p1_dev_policy_condition()`, `build_p1_dev_schedule()`.

Freeze lineage sub-IDs:

```text
CURRENT_PILOT_DATA_LINEAGE_V1
P1_DEV_DATA_LINEAGE_V1
P4_SELECT_EVALUATION_LINEAGE_V1
```

- [ ] **Step 1: RED P1 seed-only test**

```python
def test_p1_dev_schedule_is_seed17_only() -> None:
    schedule = build_p1_dev_schedule(
        task_access_manifest=_access_manifest(),
        policy_condition=_pi0_condition(),
    )

    assert schedule.replicate_seeds == (17,)
    assert schedule.run_purpose is ConditionRunPurpose.P1_PI0_DEV_ROLLOUT
    assert (
        schedule.target_access_class
        is DistillationAccessClass.DEV_VISIBLE
    )
```

- [ ] **Step 2: RED legacy-data exclusion test**

`CurrentPilotDataLineageV1` must contain explicit prohibited legacy classes and no field accepting legacy result payloads.

- [ ] **Step 3: Build the actual π0 policy condition**

Use frozen:

```text
policy_condition_id = P4-R0-PI0
repository = Qwen/Qwen2.5-3B-Instruct
revision = aa8e72537993ba99e69dfaafa59ed015b17504d1
checkpoint_kind = BASE_MODEL
training_method = NONE
policy_version = pi0
memory_version = MEMORY_M0_V1
served_model_name = Qwen2.5-3B-Instruct-E1
```

All remaining content identities are function arguments and must be explicit lowercase SHA-256/commit values; never read “latest”.

- [ ] **Step 4: Update inventory, full regression, commit**

```bash
python -m pytest -q tests/evaluation/test_p1b_lineage.py
python -m pytest -q
python -m compileall -q src tests
git diff --check

git add -- \
  configs/evaluation/schemas/current_pilot_data_lineage_v1.json \
  src/pchsi/evaluation/p1b_lineage.py \
  tests/evaluation/test_p1b_lineage.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git commit -m "Bind P1-B current data lineage"
```

---

### Task 6: Offline P1-B access artifact materialization CLI

**Files:**
- Create: `scripts/evaluation/materialize_p1b_access.py`
- Create: `tests/evaluation/test_materialize_p1b_access.py`

**Interfaces:**
- Consumes: explicit legacy identity inventory, reviewed historical audit, frozen strict-134 manifest identity, explicit runtime identity inputs.
- Produces an immutable directory containing crosswalk, split contract/proof, TaskAccessManifest, lineage, π0 condition, seed-17 schedule and governance freeze bundle.

Frozen output names:

```text
legacy_current_task_crosswalk.json
historical_access_audit.json
forced_dev_tasks.json
split_contract.json
split_proof.json
task_access_manifest.json
current_pilot_data_lineage.json
policy_condition_manifest.json
condition_run_schedule.json
governance/
P1B_SHA256SUMS
```

- [ ] **Step 1: RED no-clobber and explicit-input tests**

```python
def test_materializer_refuses_existing_output(tmp_path) -> None:
    ...
    with pytest.raises(FileExistsError):
        materialize_p1b_access(...)
```

Also prove it does not walk historical repo directories.

- [ ] **Step 2: RED legacy result ban**

If the provided legacy identity input contains fields like:

```text
success
reward
failure_type
model_output
teacher_reason
```

the strict input schema must reject them rather than silently ignore them.

- [ ] **Step 3: Implement**

The CLI must:

```text
validate exact current manifest identity
load explicit reviewed audit
load explicit reviewed forced-DEV evidence ledger
build crosswalk
derive forced DEV only from reviewed inputs
build deterministic split
materialize TaskAccessManifest
build current lineage
build π0 condition
build seed-17 DEV schedule
validate full P1-A governance bundle
freeze all outputs no-clobber
```

The authoritative materialization CLI must refuse to run if either the reviewed
historical audit or the reviewed forced-DEV evidence ledger is absent. A
candidate evidence-extraction report may be generated by a separate human
workflow, but candidate output is not authoritative input until reviewed and
frozen.

It must not run an environment or policy.

- [ ] **Step 4: Full cumulative audit**

```bash
python -m pytest -q
python -m compileall -q src tests scripts
git diff --check

grep -RInE \
  'success|failure_type|teacher_reason' \
  src/pchsi/evaluation/p1b_split.py \
  src/pchsi/evaluation/p1b_access_materializer.py
```

Any split logic reference to result semantics is a blocker.

- [ ] **Step 5: Commit**

```bash
git add -- \
  scripts/evaluation/materialize_p1b_access.py \
  tests/evaluation/test_materialize_p1b_access.py

git commit -m "Add offline P1-B access materializer"
```

## P1-B1 Completion Gate

A code candidate can receive:

```text
CODE_CANDIDATE_READY_P1_B1_ACCESS_SPLIT_FREEZE_V1
```

only if:

- all tests are green;
- schema inventory remains exact;
- no environment/model/network execution exists;
- salt is literal and unique;
- forced DEV is evidence-driven;
- no legacy outcome field can enter split;
- P1 schedule is exactly seed 17;
- old E1 runtime/schedule semantics remain intact.

Code approval does not authorize artifact materialization or π0 execution.
