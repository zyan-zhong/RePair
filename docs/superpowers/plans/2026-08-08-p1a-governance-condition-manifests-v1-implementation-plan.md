# P1-A Governance & Condition Manifests V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the non-executing governance and condition-identity layer required before any P1 π0 DEV rollout: historical-access audit contracts, `TaskAccessManifestV1`, `PolicyConditionManifestV1`, and `ConditionRunScheduleV1`, with strict schemas, deterministic canonical identities, cross-manifest validation, and an offline canonicalization CLI.

**Architecture:** Add a new distillation-governance subsystem beside the frozen E1 strict-134 evaluator. The new subsystem reuses the repository's standard-library-only schema validator and canonical evidence utilities, but does not modify `task_manifest.py`, `run_schedule.py`, Runtime Core, `run_single_episode()`, policy transport, ALFWorld adapter, or artifact publication. Task/access decisions are explicit reviewed data: implementation validates and freezes them but never infers historical exposure from absence of evidence.

**Tech Stack:** Python 3.12 standard library, frozen `dataclasses`, `enum`, existing `pchsi.evaluation.canonical_evidence`, existing `pchsi.evaluation.schema_contract`, repository JSON Schema subset, pytest.

## Global Constraints

- Parent design merge commit: `e777ed20fd91f508680326fcf7c32761978afe77`.
- Reviewed design head before merge: `a84eab5e79559cfcaee2c3a212fbdec73e8b38b8`.
- Parent specification: `docs/superpowers/specs/2026-08-07-p1-p4-reduced-single-round-distillation-pilot-v1-design.md`.
- Plan approval required before any production-code write: `PLAN_APPROVED_P1_A_GOVERNANCE_CONDITION_MANIFESTS_V1`.
- Do not modify `src/pchsi/evaluation/task_manifest.py`.
- Do not modify `src/pchsi/evaluation/run_schedule.py`.
- Do not modify `src/pchsi/evaluation/runtime_core.py`.
- Do not modify `src/pchsi/evaluation/episode_evaluator.py`.
- Do not modify any ALFWorld adapter, policy client, prompt, parser, budget, trace, artifact-publication, or result-audit semantics.
- Do not call ALFWorld, vLLM, CUDA, a teacher provider, an external API, or a dataset-scanning subprocess in this plan.
- Do not create authoritative DEV/SELECT/TEST assignments during code implementation. Implementation provides contracts and deterministic validation/freezing tools; authoritative task classification is a later reviewed governance-materialization action.
- Do not infer `NO_KNOWN_PRIOR_ACCESS` from a missing log. It must be explicitly present in reviewed audit input.
- `ACCESS_HISTORY_INCOMPLETE` makes a task/gamefile ineligible for `CONFIRMATORY_SEALED`.
- `TRAJECTORY_INSPECTED`, `USED_FOR_METHOD_DESIGN`, or `SENT_TO_EXTERNAL_MODEL` makes a task/gamefile ineligible for `CONFIRMATORY_SEALED`.
- The current strict valid-unseen 134-task manifest is not automatically `CONFIRMATORY_SEALED`.
- Same task/gamefile must have exactly one access record and one access class.
- State-level splitting is forbidden.
- New wire models use `@dataclass(frozen=True, slots=True)` and tuples for nested collections.
- New wire schemas use the repository's existing JSON Schema subset only; do not add `jsonschema`, Pydantic, Marshmallow, or another validation dependency.
- Every schema is top-level `type: object`, uses `additionalProperties: false`, and freezes `$id`/schema version.
- Canonical JSON and content identity must use existing repository canonicalization functions; do not duplicate JSON serialization rules.
- No timestamps, current working-directory absolute paths, process IDs, hostnames, or wall-clock time enter scientific manifest hashes.
- Host-bound `gamefile` paths are permitted because the current ALFWorld dataset manifests are host-bound; relocation requires regeneration/refreeze rather than silent rewriting.
- Every task below uses RED → verify RED → minimal GREEN → focused GREEN → full regression → `compileall` → static audit → one focused commit.
- No task may weaken or delete an existing safety/scientific assertion to become GREEN.
- No mocks may replace the core contract being tested. Temporary filesystem fixtures are allowed.
- No implementation task is permission to perform π0 DEV rollout, teacher calls, training, or SELECT evaluation.

---

## Existing Code That Must Be Reused, Not Rewritten

### `src/pchsi/evaluation/canonical_evidence.py`

Use existing strict JSON/canonical JSON/SHA-256 helpers. New modules must import the repository helpers rather than define a second canonical serializer.

### `src/pchsi/evaluation/schema_contract.py`

Use:

```python
validate_payload_against_schema(
    schema_id=...,
    payload=...,
)
```

and the existing schema inventory under:

```text
configs/evaluation/schemas/
```

The validator intentionally supports a closed standard-library-only schema subset.

### `src/pchsi/evaluation/task_manifest.py`

This is the frozen E1 strict-134 loader. It intentionally hard-codes:

```text
134 records
alfworld_valid_unseen_all134_XXXX IDs
split = valid_unseen
```

Do not generalize it. P1-A creates separate distillation-governance task records.

### `src/pchsi/evaluation/run_schedule.py`

This is the frozen E1 134 × 5 schedule. It intentionally requires 134 valid-unseen records. Do not generalize it. P1-A creates a separate condition-bound schedule.

## Planned File Map

Create:

```text
configs/evaluation/schemas/
├── distillation_historical_access_audit_v1.json
├── distillation_task_access_manifest_v1.json
├── policy_condition_manifest_v1.json
└── condition_run_schedule_v1.json

src/pchsi/evaluation/
├── distillation_access.py
├── policy_condition.py
├── condition_run_schedule.py
└── distillation_governance.py

scripts/evaluation/
└── freeze_distillation_governance.py

tests/evaluation/
├── test_distillation_access.py
├── test_policy_condition.py
├── test_condition_run_schedule.py
├── test_distillation_governance.py
├── test_freeze_distillation_governance.py
└── test_evaluation_schema_inventory.py  # modify exact closed inventory
```

No other production path is planned.

## Frozen Public Interfaces

### Historical access

```python
class HistoricalAccessFlag(str, Enum):
    NO_KNOWN_PRIOR_ACCESS = "NO_KNOWN_PRIOR_ACCESS"
    ACCESS_HISTORY_INCOMPLETE = "ACCESS_HISTORY_INCOMPLETE"
    AGGREGATE_ONLY = "AGGREGATE_ONLY"
    EXECUTED_NOT_INSPECTED = "EXECUTED_NOT_INSPECTED"
    TRAJECTORY_INSPECTED = "TRAJECTORY_INSPECTED"
    USED_FOR_METHOD_DESIGN = "USED_FOR_METHOD_DESIGN"
    SENT_TO_EXTERNAL_MODEL = "SENT_TO_EXTERNAL_MODEL"
```

```python
@dataclass(frozen=True, slots=True)
class HistoricalAccessAuditRecordV1:
    task_id: str
    gamefile: str
    dataset_split: str
    first_known_access_date: str | None
    access_flags: tuple[HistoricalAccessFlag, ...]
    evidence_sources: tuple[str, ...]
```

```python
@dataclass(frozen=True, slots=True)
class HistoricalAccessAuditV1:
    schema_id: str
    schema_version: int
    audit_id: str
    dataset_version: str
    record_count: int
    records: tuple[HistoricalAccessAuditRecordV1, ...]

    def to_dict(self) -> dict[str, object]: ...
    def to_json(self) -> str: ...
    @classmethod
    def from_dict(cls, value: object) -> "HistoricalAccessAuditV1": ...
    @classmethod
    def from_json(cls, value: str | bytes) -> "HistoricalAccessAuditV1": ...
```

### Task-access data

```python
class DistillationAccessClass(str, Enum):
    DEV_VISIBLE = "DEV_VISIBLE"
    SELECT_SUMMARY_ONLY = "SELECT_SUMMARY_ONLY"
    CONFIRMATORY_SEALED = "CONFIRMATORY_SEALED"
    HISTORICALLY_EXPOSED = "HISTORICALLY_EXPOSED"
```

```python
@dataclass(frozen=True, slots=True)
class TaskAccessRecordV1:
    manifest_index: int
    task_id: str
    dataset_split: str
    task_type: str
    gamefile: str
    gamefile_sha1: str
    gamefile_sha256: str
    historical_access_flags: tuple[HistoricalAccessFlag, ...]
    access_class: DistillationAccessClass
    teacher_call_permitted: bool
    training_permitted: bool
    select_evaluation_permitted: bool
    confirmatory_permitted: bool
    provenance_sources: tuple[str, ...]
```

```python
@dataclass(frozen=True, slots=True)
class TaskAccessManifestV1:
    schema_id: str
    schema_version: int
    manifest_id: str
    dataset_version: str
    historical_access_audit_sha256: str
    record_count: int
    records: tuple[TaskAccessRecordV1, ...]

    def to_dict(self) -> dict[str, object]: ...
    def to_json(self) -> str: ...
    @classmethod
    def from_dict(cls, value: object) -> "TaskAccessManifestV1": ...
    @classmethod
    def from_json(cls, value: str | bytes) -> "TaskAccessManifestV1": ...
```

### Policy condition

```python
class CheckpointKind(str, Enum):
    BASE_MODEL = "BASE_MODEL"
    LORA_ADAPTER = "LORA_ADAPTER"
    FULL_CHECKPOINT = "FULL_CHECKPOINT"
```

```python
class TrainingMethod(str, Enum):
    NONE = "NONE"
    SFT = "SFT"
```

```python
@dataclass(frozen=True, slots=True)
class PolicyConditionManifestV1:
    schema_id: str
    schema_version: int
    policy_condition_id: str
    base_model_repository: str
    base_model_revision: str
    checkpoint_kind: CheckpointKind
    checkpoint_path: str | None
    checkpoint_sha256: str | None
    training_method: TrainingMethod
    training_run_id: str | None
    training_config_sha256: str | None
    policy_runtime_manifest_sha256: str
    tokenizer_identity_manifest_sha256: str
    chat_template_sha256: str
    served_model_name: str
    policy_version: str
    memory_version: str
    raw_protocol_sha256: str
    runtime_core_commit: str
    evaluator_commit: str

    def to_dict(self) -> dict[str, object]: ...
    def to_json(self) -> str: ...
    @classmethod
    def from_dict(cls, value: object) -> "PolicyConditionManifestV1": ...
    @classmethod
    def from_json(cls, value: str | bytes) -> "PolicyConditionManifestV1": ...
```

### Condition schedule

```python
class ConditionRunPurpose(str, Enum):
    P1_PI0_DEV_ROLLOUT = "P1_PI0_DEV_ROLLOUT"
    P4_HARNESS_OFF_SELECT = "P4_HARNESS_OFF_SELECT"
```

```python
@dataclass(frozen=True, slots=True)
class ConditionRunScheduleCellV1:
    condition_cell_id: str
    manifest_index: int
    task_id: str
    seed: int
```

```python
@dataclass(frozen=True, slots=True)
class ConditionRunScheduleV1:
    schema_id: str
    schema_version: int
    schedule_id: str
    task_access_manifest_sha256: str
    policy_condition_manifest_sha256: str
    run_purpose: ConditionRunPurpose
    target_access_class: DistillationAccessClass
    replicate_seeds: tuple[int, ...]
    order: str
    cell_count: int
    output_namespace: str
    primary_statistical_unit: str
    cells: tuple[ConditionRunScheduleCellV1, ...]

    def to_dict(self) -> dict[str, object]: ...
    def to_json(self) -> str: ...
    @classmethod
    def from_dict(cls, value: object) -> "ConditionRunScheduleV1": ...
    @classmethod
    def from_json(cls, value: str | bytes) -> "ConditionRunScheduleV1": ...
```

```python
def condition_cell_id(
    *,
    policy_condition_id: str,
    manifest_index: int,
    seed: int,
) -> str: ...
```

```python
def build_condition_run_schedule(
    *,
    task_access_manifest: TaskAccessManifestV1,
    task_access_manifest_sha256: str,
    policy_condition: PolicyConditionManifestV1,
    policy_condition_manifest_sha256: str,
    run_purpose: ConditionRunPurpose,
    target_access_class: DistillationAccessClass,
    replicate_seeds: Sequence[int],
    output_namespace: str,
) -> ConditionRunScheduleV1: ...
```

### Cross-manifest validation

```python
@dataclass(frozen=True, slots=True)
class DistillationGovernanceBundleV1:
    historical_access_audit: HistoricalAccessAuditV1
    task_access_manifest: TaskAccessManifestV1
    policy_condition: PolicyConditionManifestV1
    schedule: ConditionRunScheduleV1
```

```python
def validate_distillation_governance_bundle(
    bundle: DistillationGovernanceBundleV1,
) -> None: ...
```

```python
def canonical_model_sha256(
    model: object,
) -> str: ...
```

`canonical_model_sha256()` accepts only an object that exposes `to_dict()` and hashes the existing canonical JSON bytes; it must not silently hash `repr()` or arbitrary Python objects.

---


### Exact schema inventory integration correction

The repository deliberately keeps `configs/evaluation/schemas/` under an
exact closed inventory test. Adding a reviewed schema therefore requires a
same-commit update to
`tests/evaluation/test_evaluation_schema_inventory.py`. This is a plan-scope
correction discovered by the first full-regression RED/GREEN integration
attempt; the exact-inventory safety property is preserved and is not relaxed.


### Task 1: Historical Access Audit and TaskAccessManifestV1

**Files:**
- Create: `configs/evaluation/schemas/distillation_historical_access_audit_v1.json`
- Create: `configs/evaluation/schemas/distillation_task_access_manifest_v1.json`
- Create: `src/pchsi/evaluation/distillation_access.py`
- Create: `tests/evaluation/test_distillation_access.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Produces: `HistoricalAccessFlag`, `HistoricalAccessAuditRecordV1`, `HistoricalAccessAuditV1`, `DistillationAccessClass`, `TaskAccessRecordV1`, `TaskAccessManifestV1`.
- Consumes: existing `canonical_json_text`, `strict_json_loads`, `require_lower_sha256`, `validate_payload_against_schema`.
- Later tasks rely on exact enum values and field names above.

- [ ] **Step 1: Write RED schema-inventory and immutable-round-trip tests**

Create `tests/evaluation/test_distillation_access.py` with the following first tests:

```python
from dataclasses import FrozenInstanceError
import json

import pytest

from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
    HistoricalAccessAuditRecordV1,
    HistoricalAccessAuditV1,
    HistoricalAccessFlag,
    TaskAccessManifestV1,
    TaskAccessRecordV1,
)
from pchsi.evaluation.schema_contract import load_schema


def _audit_record(
    *,
    task_id: str = "dev-task-0000",
    gamefile: str = "/dataset/train/dev-task-0000/game.tw-pddl",
    flags: tuple[HistoricalAccessFlag, ...] = (
        HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,
    ),
) -> HistoricalAccessAuditRecordV1:
    return HistoricalAccessAuditRecordV1(
        task_id=task_id,
        gamefile=gamefile,
        dataset_split="train",
        first_known_access_date=None,
        access_flags=flags,
        evidence_sources=("reviewed-ledger:row-1",),
    )


def test_distillation_access_schemas_are_registered() -> None:
    assert (
        load_schema("DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1")["$id"]
        == "DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1"
    )
    assert (
        load_schema("DISTILLATION_TASK_ACCESS_MANIFEST_V1")["$id"]
        == "DISTILLATION_TASK_ACCESS_MANIFEST_V1"
    )


def test_historical_access_audit_round_trip_is_canonical() -> None:
    audit = HistoricalAccessAuditV1(
        schema_id="DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1",
        schema_version=1,
        audit_id="P1_A_HISTORICAL_ACCESS_AUDIT_V1",
        dataset_version="json_2.1.1",
        record_count=1,
        records=(_audit_record(),),
    )

    observed = HistoricalAccessAuditV1.from_json(audit.to_json())

    assert observed == audit
    assert json.loads(audit.to_json())["record_count"] == 1


def test_access_records_are_frozen() -> None:
    record = _audit_record()

    with pytest.raises(FrozenInstanceError):
        record.task_id = "mutated"  # type: ignore[misc]
```

- [ ] **Step 2: Run RED and verify the failure is contract absence**

Run:

```bash
python -m pytest \
  -q \
  tests/evaluation/test_distillation_access.py
```

Expected RED: import failure for `pchsi.evaluation.distillation_access` and/or unknown schema IDs. A syntax error, wrong test import, or fixture error is not a valid RED.

- [ ] **Step 3: Add RED historical-access consistency tests**

Append:

```python
@pytest.mark.parametrize(
    "flags",
    [
        (
            HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,
            HistoricalAccessFlag.AGGREGATE_ONLY,
        ),
        (
            HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,
            HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
        ),
    ],
)
def test_no_known_prior_access_cannot_coexist_with_other_flags(
    flags,
) -> None:
    with pytest.raises(ValueError, match="NO_KNOWN_PRIOR_ACCESS"):
        _audit_record(flags=flags)


def test_access_history_incomplete_is_allowed_with_observed_evidence() -> None:
    record = _audit_record(
        flags=(
            HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
            HistoricalAccessFlag.EXECUTED_NOT_INSPECTED,
        )
    )

    assert HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE in (
        record.access_flags
    )
```

Run the focused test again and verify these fail because validation is not implemented.

- [ ] **Step 4: Add RED TaskAccess permission and sealing tests**

Append helpers/tests:

```python
def _task_access_record(
    *,
    access_class: DistillationAccessClass,
    flags: tuple[HistoricalAccessFlag, ...],
    teacher: bool,
    training: bool,
    select: bool,
    confirmatory: bool,
) -> TaskAccessRecordV1:
    return TaskAccessRecordV1(
        manifest_index=0,
        task_id="dev-task-0000",
        dataset_split="train",
        task_type="pick_and_place_simple",
        gamefile="/dataset/train/dev-task-0000/game.tw-pddl",
        gamefile_sha1="a" * 40,
        gamefile_sha256="b" * 64,
        historical_access_flags=flags,
        access_class=access_class,
        teacher_call_permitted=teacher,
        training_permitted=training,
        select_evaluation_permitted=select,
        confirmatory_permitted=confirmatory,
        provenance_sources=("audit:row-1",),
    )


def test_dev_visible_requires_teacher_and_training_permission() -> None:
    with pytest.raises(ValueError, match="DEV_VISIBLE"):
        _task_access_record(
            access_class=DistillationAccessClass.DEV_VISIBLE,
            flags=(HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,),
            teacher=False,
            training=True,
            select=False,
            confirmatory=False,
        )


def test_select_summary_only_forbids_teacher_and_training() -> None:
    with pytest.raises(ValueError, match="SELECT_SUMMARY_ONLY"):
        _task_access_record(
            access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY,
            flags=(HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,),
            teacher=True,
            training=False,
            select=True,
            confirmatory=False,
        )


@pytest.mark.parametrize(
    "forbidden_flag",
    [
        HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
        HistoricalAccessFlag.TRAJECTORY_INSPECTED,
        HistoricalAccessFlag.USED_FOR_METHOD_DESIGN,
        HistoricalAccessFlag.SENT_TO_EXTERNAL_MODEL,
    ],
)
def test_confirmatory_sealed_rejects_disqualifying_history(
    forbidden_flag,
) -> None:
    with pytest.raises(ValueError, match="CONFIRMATORY_SEALED"):
        _task_access_record(
            access_class=DistillationAccessClass.CONFIRMATORY_SEALED,
            flags=(forbidden_flag,),
            teacher=False,
            training=False,
            select=False,
            confirmatory=True,
        )


def test_historically_exposed_can_never_be_confirmatory() -> None:
    with pytest.raises(ValueError, match="HISTORICALLY_EXPOSED"):
        _task_access_record(
            access_class=DistillationAccessClass.HISTORICALLY_EXPOSED,
            flags=(HistoricalAccessFlag.TRAJECTORY_INSPECTED,),
            teacher=True,
            training=True,
            select=False,
            confirmatory=True,
        )
```

- [ ] **Step 5: Implement the two schemas**

Both schema files must:

- use `$schema` only if it already appears in repository schemas;
- set exact `$id`;
- use top-level `type: "object"`;
- set `additionalProperties: false`;
- inline nested record objects because the current schema subset does not rely on external `$ref`;
- represent nullable dates with `type: ["string", "null"]`;
- constrain access flags and access classes with exact `enum` values;
- constrain hashes with lowercase-hex patterns;
- require all fields.

`distillation_historical_access_audit_v1.json` top-level required fields:

```text
schema_id
schema_version
audit_id
dataset_version
record_count
records
```

`distillation_task_access_manifest_v1.json` top-level required fields:

```text
schema_id
schema_version
manifest_id
dataset_version
historical_access_audit_sha256
record_count
records
```

- [ ] **Step 6: Implement `distillation_access.py` minimally**

Implementation requirements:

1. use frozen/slotted dataclasses;
2. tuples only for `access_flags`, `evidence_sources`, `records`, `provenance_sources`;
3. reject empty IDs/paths/splits/types/sources;
4. reject duplicate flags;
5. `NO_KNOWN_PRIOR_ACCESS` must be the sole flag when present;
6. validate lowercase SHA-1/SHA-256 exactly;
7. `HistoricalAccessAuditV1.record_count == len(records)`;
8. audit records must have unique `task_id` and unique `gamefile`;
9. `TaskAccessManifestV1.record_count == len(records)`;
10. task access `manifest_index` is exactly contiguous `0..record_count-1`;
11. task access records have unique `task_id` and unique `gamefile`;
12. enforce access-class permission rules:

```text
DEV_VISIBLE:
  teacher_call_permitted = true
  training_permitted = true
  select_evaluation_permitted = false
  confirmatory_permitted = false

SELECT_SUMMARY_ONLY:
  teacher_call_permitted = false
  training_permitted = false
  select_evaluation_permitted = true
  confirmatory_permitted = false

CONFIRMATORY_SEALED:
  teacher_call_permitted = false
  training_permitted = false
  select_evaluation_permitted = false
  confirmatory_permitted = true
  reject ACCESS_HISTORY_INCOMPLETE
  reject TRAJECTORY_INSPECTED
  reject USED_FOR_METHOD_DESIGN
  reject SENT_TO_EXTERNAL_MODEL

HISTORICALLY_EXPOSED:
  confirmatory_permitted = false
  teacher/training/select permissions remain explicit,
  because the reviewed design permits historically exposed tasks to be
  used for development according to recorded permissions.
```

13. call `validate_payload_against_schema()` from top-level models;
14. round-trip enum values as strings in JSON;
15. do not scan the filesystem or verify gamefile bytes in constructors.

- [ ] **Step 7: Run focused GREEN**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_distillation_access.py
```

Expected: all Task 1 focused tests pass.

- [ ] **Step 8: Run schema-contract regression**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_schema_contract.py \
  tests/evaluation/test_schema_models.py \
  tests/evaluation/test_distillation_access.py
```

If an existing filename differs, locate the existing schema contract test by repository path and run that existing file plus the new test. Do not create duplicate legacy tests to hide a path mistake.

- [ ] **Step 9: Static audit Task 1**

```bash
grep -RInE \
  'NEVER_ACCESSED|jsonschema|pydantic|marshmallow' \
  src/pchsi/evaluation/distillation_access.py \
  tests/evaluation/test_distillation_access.py \
  configs/evaluation/schemas/distillation_historical_access_audit_v1.json \
  configs/evaluation/schemas/distillation_task_access_manifest_v1.json \
  && exit 1 || true

git diff --check
```

Also confirm frozen E1 files are untouched:

```bash
git status --short

git diff -- \
  src/pchsi/evaluation/task_manifest.py \
  src/pchsi/evaluation/run_schedule.py \
  src/pchsi/evaluation/runtime_core.py \
  src/pchsi/evaluation/episode_evaluator.py
```

The second command must have no output.

- [ ] **Step 10: Full regression and compile**

```bash
python -m pytest -q

python -m compileall \
  -q \
  src \
  tests \
  scripts
```

- [ ] **Step 11: Commit Task 1**

```bash
git add -- \
  configs/evaluation/schemas/distillation_historical_access_audit_v1.json \
  configs/evaluation/schemas/distillation_task_access_manifest_v1.json \
  src/pchsi/evaluation/distillation_access.py \
  tests/evaluation/test_distillation_access.py

git diff --cached --check

git commit \
  -m "Add distillation task access contracts"
```

**Task 1 forbidden behavior:**

- no automatic classification of tasks from missing evidence;
- no dataset scan;
- no mutation of strict-134 task loader;
- no state-level split;
- no teacher/model/environment execution.

---

### Task 2: PolicyConditionManifestV1

**Files:**
- Create: `configs/evaluation/schemas/policy_condition_manifest_v1.json`
- Create: `src/pchsi/evaluation/policy_condition.py`
- Create: `tests/evaluation/test_policy_condition.py`

**Interfaces:**
- Produces: `CheckpointKind`, `TrainingMethod`, `PolicyConditionManifestV1`.
- Consumes: existing canonical/schema helpers.
- `ConditionRunScheduleV1` and later evaluator condition binding consume this exact model.

- [ ] **Step 1: Write RED π0 and trained-condition round-trip tests**

Create `tests/evaluation/test_policy_condition.py`:

```python
from dataclasses import FrozenInstanceError

import pytest

from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)
from pchsi.evaluation.schema_contract import load_schema


def _pi0() -> PolicyConditionManifestV1:
    return PolicyConditionManifestV1(
        schema_id="POLICY_CONDITION_MANIFEST_V1",
        schema_version=1,
        policy_condition_id="P4-R0-PI0",
        base_model_repository="Qwen/Qwen2.5-3B-Instruct",
        base_model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        checkpoint_kind=CheckpointKind.BASE_MODEL,
        checkpoint_path=None,
        checkpoint_sha256=None,
        training_method=TrainingMethod.NONE,
        training_run_id=None,
        training_config_sha256=None,
        policy_runtime_manifest_sha256="a" * 64,
        tokenizer_identity_manifest_sha256="b" * 64,
        chat_template_sha256="c" * 64,
        served_model_name="Qwen2.5-3B-Instruct-P4-R0-PI0",
        policy_version="pi0",
        memory_version="MEMORY_M0_V1",
        raw_protocol_sha256="d" * 64,
        runtime_core_commit="1ce3622b3b247c44e962a6b98eb78192f724580b",
        evaluator_commit="39ee3d78246239aac3844075c2ece7c3e94ec97d",
    )


def test_policy_condition_schema_is_registered() -> None:
    assert (
        load_schema("POLICY_CONDITION_MANIFEST_V1")["$id"]
        == "POLICY_CONDITION_MANIFEST_V1"
    )


def test_pi0_policy_condition_round_trip() -> None:
    condition = _pi0()

    assert PolicyConditionManifestV1.from_json(
        condition.to_json()
    ) == condition


def test_policy_condition_is_frozen() -> None:
    condition = _pi0()
    with pytest.raises(FrozenInstanceError):
        condition.policy_version = "mutated"  # type: ignore[misc]
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_policy_condition.py
```

Expected RED: missing module/schema.

- [ ] **Step 3: Add RED cross-field identity tests**

Append:

```python
def test_base_model_condition_forbids_training_artifacts() -> None:
    payload = _pi0().to_dict()
    payload["training_run_id"] = "unexpected"

    with pytest.raises(ValueError, match="BASE_MODEL"):
        PolicyConditionManifestV1.from_dict(payload)


def test_sft_condition_requires_checkpoint_and_training_identity() -> None:
    payload = _pi0().to_dict()
    payload.update(
        {
            "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
            "checkpoint_kind": "LORA_ADAPTER",
            "training_method": "SFT",
            "policy_version": "pi1-bad",
            "served_model_name": "P4-R1-Q2-BAD-TRAIN17",
        }
    )

    with pytest.raises(ValueError, match="SFT"):
        PolicyConditionManifestV1.from_dict(payload)


def test_trained_condition_cannot_reuse_pi0_served_name() -> None:
    payload = _pi0().to_dict()
    payload.update(
        {
            "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
            "checkpoint_kind": "LORA_ADAPTER",
            "checkpoint_path": "/models/pi1-bad/adapter",
            "checkpoint_sha256": "e" * 64,
            "training_method": "SFT",
            "training_run_id": "p4-r1-train17",
            "training_config_sha256": "f" * 64,
            "policy_version": "pi1-bad",
            "served_model_name": "Qwen2.5-3B-Instruct-P4-R0-PI0",
        }
    )

    with pytest.raises(ValueError, match="served_model_name"):
        PolicyConditionManifestV1.from_dict(payload)
```

The exact rule implemented is:

```text
BASE_MODEL + NONE:
  checkpoint_path = null
  checkpoint_sha256 = null
  training_run_id = null
  training_config_sha256 = null

LORA_ADAPTER or FULL_CHECKPOINT + SFT:
  checkpoint_path != null
  checkpoint_sha256 != null
  training_run_id != null
  training_config_sha256 != null
  policy_version != "pi0"
```

Additionally, a trained condition whose `served_model_name` equals the canonical π0 served name `Qwen2.5-3B-Instruct-P4-R0-PI0` is rejected.

- [ ] **Step 4: Implement schema and model**

`policy_condition_manifest_v1.json` must require every field and permit null only for:

```text
checkpoint_path
checkpoint_sha256
training_run_id
training_config_sha256
```

`policy_condition_id`, `served_model_name`, `policy_version`, and `memory_version` must be non-empty. SHA-256 fields use lowercase 64-hex patterns. Git commit fields use lowercase 40-hex patterns.

Implement `policy_condition.py` with:

- frozen/slotted dataclass;
- strict enum parsing;
- schema validation;
- cross-field rules above;
- canonical round-trip.

Do not inspect checkpoint files or start a model service here.

- [ ] **Step 5: Focused GREEN**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_policy_condition.py
```

- [ ] **Step 6: Static audit and regression**

```bash
grep -RInE \
  'vllm|requests|urllib|transformers|torch|subprocess' \
  src/pchsi/evaluation/policy_condition.py \
  tests/evaluation/test_policy_condition.py \
  && exit 1 || true

git diff --check

python -m pytest -q

python -m compileall \
  -q \
  src \
  tests
```

- [ ] **Step 7: Commit Task 2**

```bash
git add -- \
  configs/evaluation/schemas/policy_condition_manifest_v1.json \
  src/pchsi/evaluation/policy_condition.py \
  tests/evaluation/test_policy_condition.py

git diff --cached --check

git commit \
  -m "Add policy condition manifest"
```

**Task 2 forbidden behavior:**

- no vLLM request;
- no checkpoint load;
- no filesystem-derived checkpoint hash during model construction;
- no reuse of π0 condition identity for trained policy conditions.

---

### Task 3: ConditionRunScheduleV1

**Files:**
- Create: `configs/evaluation/schemas/condition_run_schedule_v1.json`
- Create: `src/pchsi/evaluation/condition_run_schedule.py`
- Create: `tests/evaluation/test_condition_run_schedule.py`

**Interfaces:**
- Produces: `ConditionRunPurpose`, `ConditionRunScheduleCellV1`, `ConditionRunScheduleV1`, `condition_cell_id()`, `build_condition_run_schedule()`.
- Consumes: `TaskAccessManifestV1`, `PolicyConditionManifestV1`.
- Later P1 rollout runner consumes schedule cells but must not call the legacy E1 `build_e1_run_schedule()` for distillation conditions.

- [ ] **Step 1: Write RED schedule-ID and non-134 schedule tests**

Create tests:

```python
import pytest

from pchsi.evaluation.condition_run_schedule import (
    ConditionRunPurpose,
    build_condition_run_schedule,
    condition_cell_id,
)
from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
    HistoricalAccessFlag,
    TaskAccessManifestV1,
    TaskAccessRecordV1,
)
from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)


def test_condition_cell_id_is_condition_bound() -> None:
    assert condition_cell_id(
        policy_condition_id="P4-R0-PI0",
        manifest_index=7,
        seed=17,
    ) == "p4-P4-R0-PI0-t00007-s0000000017"


def test_condition_schedule_does_not_require_134_tasks() -> None:
    manifest = _dev_manifest(task_count=2)
    policy = _pi0_condition()

    schedule = build_condition_run_schedule(
        task_access_manifest=manifest,
        task_access_manifest_sha256="a" * 64,
        policy_condition=policy,
        policy_condition_manifest_sha256="b" * 64,
        run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
        target_access_class=DistillationAccessClass.DEV_VISIBLE,
        replicate_seeds=(17, 31),
        output_namespace="p1-pi0-dev-v1",
    )

    assert schedule.cell_count == 4
    assert [cell.seed for cell in schedule.cells] == [17, 17, 31, 31]
```

In this test file, implement `_dev_manifest()` and `_pi0_condition()` using the exact public constructors from Tasks 1 and 2; do not monkeypatch those types.

- [ ] **Step 2: Verify RED**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_condition_run_schedule.py
```

Expected RED: missing schedule module/schema.

- [ ] **Step 3: Add RED access-purpose and seed tests**

Append:

```python
def test_p1_dev_schedule_rejects_non_dev_target() -> None:
    with pytest.raises(ValueError, match="P1_PI0_DEV_ROLLOUT"):
        build_condition_run_schedule(
            task_access_manifest=_dev_manifest(task_count=2),
            task_access_manifest_sha256="a" * 64,
            policy_condition=_pi0_condition(),
            policy_condition_manifest_sha256="b" * 64,
            run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
            target_access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY,
            replicate_seeds=(17,),
            output_namespace="invalid",
        )


@pytest.mark.parametrize(
    "seeds",
    [
        (),
        (17, 17),
        (-1,),
    ],
)
def test_schedule_rejects_invalid_seed_schedule(seeds) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_condition_run_schedule(
            task_access_manifest=_dev_manifest(task_count=2),
            task_access_manifest_sha256="a" * 64,
            policy_condition=_pi0_condition(),
            policy_condition_manifest_sha256="b" * 64,
            run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
            target_access_class=DistillationAccessClass.DEV_VISIBLE,
            replicate_seeds=seeds,
            output_namespace="p1-dev",
        )
```

Also add a test proving the builder selects only records whose `access_class` exactly equals the target class and preserves their manifest order inside each seed.

- [ ] **Step 4: Implement schedule schema and model**

Frozen V1 rules:

```text
schema_id = CONDITION_RUN_SCHEDULE_V1
schema_version = 1
order = seed-major
primary_statistical_unit = unique_task
```

`condition_cell_id()` rules:

- `policy_condition_id` must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`;
- `manifest_index` is non-negative and <= 99999;
- `seed` is non-negative and <= 9999999999;
- format exactly:
  `p4-{policy_condition_id}-t{manifest_index:05d}-s{seed:010d}`.

`output_namespace` must match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` and must not contain `/`, `..`, or whitespace.

`build_condition_run_schedule()` rules:

1. validate both supplied SHA-256 identities;
2. reject empty/duplicate/negative seeds;
3. `P1_PI0_DEV_ROLLOUT` requires `DEV_VISIBLE`;
4. `P4_HARNESS_OFF_SELECT` requires `SELECT_SUMMARY_ONLY`;
5. P1 purpose requires `policy_condition.policy_condition_id == "P4-R0-PI0"` in this V1;
6. select only exact target-class task records;
7. reject zero selected tasks;
8. seed-major ordering;
9. `cell_count == len(selected_tasks) * len(replicate_seeds)`;
10. schedule cells reference original `manifest_index` and `task_id`, not renumbered task IDs.

- [ ] **Step 5: Focused GREEN**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_condition_run_schedule.py
```

- [ ] **Step 6: Prove legacy E1 schedule behavior is untouched**

Run:

```bash
python -m pytest \
  -q \
  tests/evaluation/test_condition_run_schedule.py \
  tests/evaluation/test_run_schedule.py
```

If the existing legacy schedule test has a different filename, locate and run the repository's existing test that imports `build_e1_run_schedule`. Do not alter the legacy schedule to make the new test pass.

Static diff:

```bash
git diff -- \
  src/pchsi/evaluation/run_schedule.py \
  src/pchsi/evaluation/task_manifest.py
```

Must be empty.

- [ ] **Step 7: Full regression, compile, commit**

```bash
python -m pytest -q

python -m compileall \
  -q \
  src \
  tests

git diff --check

git add -- \
  configs/evaluation/schemas/condition_run_schedule_v1.json \
  src/pchsi/evaluation/condition_run_schedule.py \
  tests/evaluation/test_condition_run_schedule.py

git diff --cached --check

git commit \
  -m "Add condition-bound run schedule"
```

**Task 3 forbidden behavior:**

- no strict-134 hard coding;
- no hidden task reindexing;
- no adaptive seed creation;
- no task randomization;
- no environment or model execution.

---

### Task 4: Cross-Manifest Governance Validation

**Files:**
- Create: `src/pchsi/evaluation/distillation_governance.py`
- Create: `tests/evaluation/test_distillation_governance.py`

**Interfaces:**
- Produces: `DistillationGovernanceBundleV1`, `canonical_model_sha256()`, `validate_distillation_governance_bundle()`.
- Consumes: models from Tasks 1–3.
- Freeze CLI in Task 5 must call this validator before writing anything.

- [ ] **Step 1: Write RED hash-binding tests**

Create:

```python
import pytest

from pchsi.evaluation.distillation_governance import (
    DistillationGovernanceBundleV1,
    canonical_model_sha256,
    validate_distillation_governance_bundle,
)


def test_canonical_model_sha256_is_stable() -> None:
    audit, access, policy, schedule = _valid_bundle_parts()

    assert canonical_model_sha256(audit) == canonical_model_sha256(
        audit
    )
    assert len(canonical_model_sha256(access)) == 64


def test_task_access_manifest_must_bind_exact_audit_hash() -> None:
    audit, access, policy, schedule = _valid_bundle_parts()
    access = _replace_access_audit_hash(access, "0" * 64)

    with pytest.raises(ValueError, match="historical_access_audit_sha256"):
        validate_distillation_governance_bundle(
            DistillationGovernanceBundleV1(
                historical_access_audit=audit,
                task_access_manifest=access,
                policy_condition=policy,
                schedule=schedule,
            )
        )
```

The test helpers must construct real immutable objects rather than dict mocks.

- [ ] **Step 2: Verify RED**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_distillation_governance.py
```

- [ ] **Step 3: Add RED task/audit identity and schedule-binding tests**

Required tests:

```text
task access task_id/gamefile/flags must exactly match historical audit
every task access record has a corresponding audit record
no extra audit record silently disappears from the reviewed manifest
schedule.task_access_manifest_sha256 equals canonical access manifest hash
schedule.policy_condition_manifest_sha256 equals canonical policy hash
schedule cell manifest_index/task_id pair exists in task access manifest
schedule cell access class equals schedule target class
P1 schedule cells all refer to DEV_VISIBLE records
SELECT schedule cells all refer to SELECT_SUMMARY_ONLY records
```

Representative test:

```python
def test_access_flags_must_equal_audited_flags() -> None:
    audit, access, policy, schedule = _valid_bundle_parts()
    access = _with_first_access_flags(
        access,
        (HistoricalAccessFlag.AGGREGATE_ONLY,),
    )

    with pytest.raises(ValueError, match="historical access flags"):
        validate_distillation_governance_bundle(
            DistillationGovernanceBundleV1(
                historical_access_audit=audit,
                task_access_manifest=access,
                policy_condition=policy,
                schedule=schedule,
            )
        )
```

- [ ] **Step 4: Implement minimal governance validator**

`canonical_model_sha256()`:

```python
def canonical_model_sha256(model: object) -> str:
    to_dict = getattr(model, "to_dict", None)
    if not callable(to_dict):
        raise TypeError("model must expose to_dict()")
    payload = to_dict()
    if not isinstance(payload, dict):
        raise TypeError("to_dict() must return dict")
    return sha256_bytes(canonical_json_bytes(payload))
```

Use the existing imported `canonical_json_bytes` and `sha256_bytes`.

`validate_distillation_governance_bundle()` must:

1. type-check each component;
2. compute exact canonical hashes;
3. compare access manifest's audit hash to audit canonical hash;
4. create task maps keyed separately by task ID and gamefile and reject mismatch;
5. require exact audited flags in task access;
6. require one task access record per historical audit record in this V1;
7. compare schedule access/policy hashes to actual canonical hashes;
8. verify every schedule cell pair `(manifest_index, task_id)`;
9. verify cell access class and run-purpose permission;
10. never use task result/outcome fields because this layer is pre-rollout governance only.

- [ ] **Step 5: Focused GREEN**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_distillation_governance.py
```

- [ ] **Step 6: Run combined P1-A model suite**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_distillation_access.py \
  tests/evaluation/test_policy_condition.py \
  tests/evaluation/test_condition_run_schedule.py \
  tests/evaluation/test_distillation_governance.py
```

- [ ] **Step 7: Static audit, full regression, commit**

```bash
grep -RInE \
  'alfworld|vllm|torch|transformers|requests|urllib|subprocess' \
  src/pchsi/evaluation/distillation_governance.py \
  tests/evaluation/test_distillation_governance.py \
  && exit 1 || true

git diff --check

python -m pytest -q

python -m compileall \
  -q \
  src \
  tests

git add -- \
  src/pchsi/evaluation/distillation_governance.py \
  tests/evaluation/test_distillation_governance.py

git diff --cached --check

git commit \
  -m "Validate distillation governance bindings"
```

**Task 4 forbidden behavior:**

- no inference from episode outcomes;
- no future/teacher fields;
- no hashing `repr(model)`;
- no cross-task data matching by observation text.

---

### Task 5: Offline Governance Freeze CLI and Cumulative Audit

**Files:**
- Create: `scripts/evaluation/freeze_distillation_governance.py`
- Create: `tests/evaluation/test_freeze_distillation_governance.py`

**Interfaces:**
- Produces: an offline CLI that canonicalizes already-reviewed governance inputs.
- Consumes: `HistoricalAccessAuditV1`, `TaskAccessManifestV1`, `PolicyConditionManifestV1`, `ConditionRunScheduleV1`, `validate_distillation_governance_bundle()`.
- It does not discover tasks, classify exposure, or execute an experiment.

- [ ] **Step 1: Write RED CLI success test with fully reviewed fixtures**

Use `tmp_path` and call the CLI module's pure function, not a subprocess, for the core test:

```python
from pathlib import Path

from pchsi.evaluation.distillation_governance import (
    canonical_model_sha256,
)
from scripts.evaluation.freeze_distillation_governance import (
    freeze_governance_inputs,
)


def test_freeze_governance_inputs_writes_canonical_no_clobber_bundle(
    tmp_path: Path,
) -> None:
    audit, access, policy, schedule = _valid_bundle_parts()
    output = tmp_path / "frozen"

    result = freeze_governance_inputs(
        historical_access_audit=audit,
        task_access_manifest=access,
        policy_condition=policy,
        schedule=schedule,
        output_dir=output,
    )

    assert result.output_dir == output
    assert (
        output / "historical_access_audit.json"
    ).read_text(encoding="utf-8") == audit.to_json() + "\n"
    assert (
        output / "task_access_manifest.sha256"
    ).read_text(encoding="ascii").strip() == (
        canonical_model_sha256(access)
    )
```

If direct import under `scripts` is not supported by repository packaging, define the pure freeze function in `src/pchsi/evaluation/distillation_governance.py` and keep the script as a thin `main()` wrapper. The test must exercise the pure production function, not duplicate it.

- [ ] **Step 2: Verify RED**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_freeze_distillation_governance.py
```

Expected RED: missing script/function.

- [ ] **Step 3: Add RED no-clobber and no-inference tests**

Required tests:

```python
def test_freeze_refuses_existing_output_directory(tmp_path) -> None:
    audit, access, policy, schedule = _valid_bundle_parts()
    output = tmp_path / "frozen"
    output.mkdir()

    with pytest.raises(FileExistsError):
        freeze_governance_inputs(
            historical_access_audit=audit,
            task_access_manifest=access,
            policy_condition=policy,
            schedule=schedule,
            output_dir=output,
        )
```

Also test:

- invalid cross-manifest hash fails before output directory creation;
- symlink output path is rejected;
- output contains only the frozen canonical files and SHA-256 sidecars;
- no timestamp field appears in output;
- source files are not mutated;
- execution does not inspect referenced gamefile bytes.

- [ ] **Step 4: Implement pure freezer and thin CLI**

Frozen output names:

```text
historical_access_audit.json
historical_access_audit.sha256
task_access_manifest.json
task_access_manifest.sha256
policy_condition_manifest.json
policy_condition_manifest.sha256
condition_run_schedule.json
condition_run_schedule.sha256
governance_freeze_index.json
governance_freeze_index.sha256
```

`governance_freeze_index.json` contains only deterministic identities:

```json
{
  "schema_id": "DISTILLATION_GOVERNANCE_FREEZE_INDEX_V1",
  "schema_version": 1,
  "historical_access_audit_sha256": "...",
  "task_access_manifest_sha256": "...",
  "policy_condition_manifest_sha256": "...",
  "condition_run_schedule_sha256": "...",
  "design_merge_commit": "e777ed20fd91f508680326fcf7c32761978afe77"
}
```

Do not add a wall-clock timestamp.

Write each file using `O_CREAT | O_EXCL`, `0600`, complete write, file `fsync`, then directory `fsync`. Do not overwrite an existing output directory or file.

CLI arguments:

```text
--historical-access-audit PATH
--task-access-manifest PATH
--policy-condition-manifest PATH
--condition-run-schedule PATH
--output-dir PATH
```

CLI loads strict JSON through the corresponding model `from_json()`, validates the full bundle, then calls the pure freezer.

The CLI must not contain:

```text
ALFWorld import
vLLM import
network library
dataset glob/scan
teacher provider client
training library
```

- [ ] **Step 5: Focused GREEN**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_freeze_distillation_governance.py
```

- [ ] **Step 6: Cumulative P1-A static scope audit**

At the implementation branch base, record:

```bash
IMPLEMENTATION_BASE="$(
  git merge-base HEAD origin/main
)"

echo "IMPLEMENTATION_BASE=$IMPLEMENTATION_BASE"
```

Then verify changed production paths are a subset of exactly:

```text
configs/evaluation/schemas/distillation_historical_access_audit_v1.json
configs/evaluation/schemas/distillation_task_access_manifest_v1.json
configs/evaluation/schemas/policy_condition_manifest_v1.json
configs/evaluation/schemas/condition_run_schedule_v1.json
src/pchsi/evaluation/distillation_access.py
src/pchsi/evaluation/policy_condition.py
src/pchsi/evaluation/condition_run_schedule.py
src/pchsi/evaluation/distillation_governance.py
scripts/evaluation/freeze_distillation_governance.py
tests/evaluation/test_distillation_access.py
tests/evaluation/test_policy_condition.py
tests/evaluation/test_condition_run_schedule.py
tests/evaluation/test_distillation_governance.py
tests/evaluation/test_freeze_distillation_governance.py
tests/evaluation/test_evaluation_schema_inventory.py
```

The existing exact schema inventory remains closed. Task 1 adds the two
distillation access schemas, Task 2 adds the policy-condition schema, and
Task 3 adds the condition-run-schedule schema. The inventory test must be
updated in the same focused commit as each schema addition; it must never be
weakened from exact equality to subset membership.

Use:

```bash
git diff \
  --name-only \
  "$IMPLEMENTATION_BASE"...HEAD \
  | sort
```

Confirm frozen core files have no diff from implementation base:

```bash
git diff \
  "$IMPLEMENTATION_BASE"...HEAD \
  -- \
  src/pchsi/evaluation/task_manifest.py \
  src/pchsi/evaluation/run_schedule.py \
  src/pchsi/evaluation/runtime_core.py \
  src/pchsi/evaluation/episode_evaluator.py \
  src/pchsi/evaluation/artifact_publisher.py
```

Expected: no output.

- [ ] **Step 7: Cumulative forbidden-dependency audit**

```bash
grep -RInE \
  '(^|[[:space:]])(import|from)[[:space:]]+(alfworld|vllm|torch|transformers|requests|httpx|anthropic|openai|google)' \
  src/pchsi/evaluation/distillation_access.py \
  src/pchsi/evaluation/policy_condition.py \
  src/pchsi/evaluation/condition_run_schedule.py \
  src/pchsi/evaluation/distillation_governance.py \
  scripts/evaluation/freeze_distillation_governance.py \
  tests/evaluation/test_distillation_access.py \
  tests/evaluation/test_policy_condition.py \
  tests/evaluation/test_condition_run_schedule.py \
  tests/evaluation/test_distillation_governance.py \
  tests/evaluation/test_freeze_distillation_governance.py \
  && exit 1 || true
```

Also reject historical overclaim residue:

```bash
grep -RIn \
  'NEVER_ACCESSED' \
  src/pchsi/evaluation/distillation_access.py \
  tests/evaluation/test_distillation_access.py \
  && exit 1 || true
```

- [ ] **Step 8: Full verification**

```bash
python -m pytest -q

python -m compileall \
  -q \
  src \
  tests \
  scripts

git diff --check
```

Record the exact full-suite pass count as evidence; do not weaken assertions if the count increases.

- [ ] **Step 9: Commit Task 5**

```bash
git add -- \
  scripts/evaluation/freeze_distillation_governance.py \
  tests/evaluation/test_freeze_distillation_governance.py

git diff --cached --check

git commit \
  -m "Freeze validated distillation governance inputs"
```

- [ ] **Step 10: Post-commit cumulative audit**

```bash
git status --short

python -m pytest -q

python -m compileall \
  -q \
  src \
  tests \
  scripts
```

Worktree must be clean.

**Task 5 forbidden behavior:**

- no real task-assignment generation;
- no historical-access inference;
- no dataset enumeration;
- no ALFWorld/model/teacher/training execution;
- no overwriting a prior governance freeze;
- no timestamp or host-dependent transient value in manifest identity.

---

## Plan-Level Review Checklist

Before `CODE_APPROVED_P1_A_GOVERNANCE_CONDITION_MANIFESTS_V1`, review the implementation candidate against every item below.

### Contract coverage

- [ ] `NO_KNOWN_PRIOR_ACCESS` exists and is never inferred from absence.
- [ ] `ACCESS_HISTORY_INCOMPLETE` exists.
- [ ] `ACCESS_HISTORY_INCOMPLETE` cannot be sealed.
- [ ] inspected/method-design/external-model tasks cannot be sealed.
- [ ] task/gamefile uniqueness is strict.
- [ ] state-level splitting has no representation in the APIs.
- [ ] `DEV_VISIBLE`, `SELECT_SUMMARY_ONLY`, `CONFIRMATORY_SEALED`, `HISTORICALLY_EXPOSED` are exact values.
- [ ] access permissions are explicit.
- [ ] π0 and trained policy conditions have distinct identities.
- [ ] trained conditions cannot silently reuse π0 served-model identity.
- [ ] condition schedule is not hard-coded to 134 or `valid_unseen`.
- [ ] P1 purpose schedules only DEV.
- [ ] SELECT purpose schedules only SELECT.
- [ ] seeds are frozen inputs, unique, and deterministic.
- [ ] no best-of-run or adaptive seed logic exists.
- [ ] schedule cells bind original task manifest indices.
- [ ] every schedule hash matches the actual canonical manifest bytes.
- [ ] audit flags in task access exactly match the reviewed audit.
- [ ] freezer is no-clobber and deterministic.
- [ ] freezer contains no task discovery or teacher execution.

### Frozen E1 regression boundary

- [ ] strict-134 `task_manifest.py` unchanged.
- [ ] E1 `run_schedule.py` unchanged.
- [ ] Runtime Core unchanged.
- [ ] single-episode evaluator unchanged.
- [ ] artifact publisher unchanged.
- [ ] existing E1 tests remain GREEN.
- [ ] existing integrated-smoke evidence is not rewritten or reused as DEV automatically.

### Schema and serialization

- [ ] all new schemas load through existing `schema_contract.py`.
- [ ] unsupported schema keywords are not introduced.
- [ ] `additionalProperties` is false.
- [ ] model↔wire round-trip tests pass.
- [ ] dataclasses are frozen/slotted.
- [ ] nested arrays become tuples in Python.
- [ ] SHA fields are lowercase fixed-length hex.
- [ ] canonical JSON identity uses existing helpers.
- [ ] no `NaN`/Infinity/non-standard JSON enters artifacts.

### Execution boundary

- [ ] no π0 DEV rollout occurred during implementation.
- [ ] no teacher call occurred.
- [ ] no ALFWorld environment was started.
- [ ] no vLLM server was started.
- [ ] no SFT was started.
- [ ] no SELECT task was inspected.

## Implementation Completion State

Successful implementation of this plan may support:

```text
CODE_CANDIDATE_READY_P1_A_GOVERNANCE_CONDITION_MANIFESTS_V1
```

After independent source review and full regression, a separate decision may grant:

```text
CODE_APPROVED_P1_A_GOVERNANCE_CONDITION_MANIFESTS_V1
```

Code approval still does not authorize authoritative task assignment or π0 rollout.

The next separate activity after code approval is:

```text
P1-A authoritative historical-access audit
→ reviewed TaskAccessManifestV1 materialization
→ P4-R0-PI0 PolicyConditionManifestV1 freeze
→ P1 DEV ConditionRunScheduleV1 freeze
→ EXECUTION_APPROVED_P1_PI0_DEV_ROLLOUT
```

Teacher, Q2 replay, SFT, and SELECT remain outside this implementation plan.
