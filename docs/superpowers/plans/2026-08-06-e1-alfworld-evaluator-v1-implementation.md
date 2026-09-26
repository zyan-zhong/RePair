
# E1 ALFWorld Evaluator V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:using-git-worktrees before starting implementation, then use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a manifest-bound, controller-free, fully auditable E1 ALFWorld evaluator that preserves the frozen Runtime Core, exact model-visible input, exact environment semantics, retry resolution, and crash-consistent scientific evidence.

**Architecture:** The implementation is divided into fourteen focused tasks and fourteen focused commits. Pure canonical/schema contracts and identity builders come first; strict environment and policy adapters follow; schedule, transitions, sequence validation, artifacts, orchestration, result audit, execution gating, and cumulative audit build on those contracts. Real ALFWorld, real vLLM, GPU use, formal gamefile hashing, and target-host readiness artifact generation remain outside this implementation phase.

**Tech Stack:** Python 3.12, frozen dataclasses, JSON Schema, hashlib, pathlib, multiprocessing with the explicit `spawn` context, standard-library `http.client`, pytest, Git, ALFWorld/TextWorld interfaces behind injected fakes, and existing `pchsi.evaluation` Runtime Core contracts.

## Approval binding

```text
PLAN_APPROVAL=
PLAN_APPROVED_E1_ALFWORLD_EVALUATOR_V1

DESIGN_ID=
E1_ALFWORLD_EVALUATOR_V1

DESIGN_REVISION=
1.2

DESIGN_MERGE_COMMIT=
5cddface67c220c8c799d1b0699cf611d7ffc78a

DESIGN_BLOB_SHA=
ad0eea1638716917d36391b098e9770b8a0c06fe

SPLIT_AND_ACCESS_MERGE_COMMIT=
97ce6358bb2b0db345f67b3bc6278f7d81a028bb

IMPLEMENTATION_STATUS=
AUTHORIZED_AFTER_PLAN_PR_MERGE

REAL_ENVIRONMENT_EXECUTION=
NOT_APPROVED

MODEL_EXECUTION=
NOT_APPROVED

ENGINEERING_SMOKE_EXECUTION=
NOT_APPROVED

E1_DEV_EXECUTION=
NOT_APPROVED

E1_CONFIRMATORY_EXECUTION=
NOT_APPROVED
```

## Global Constraints

- The plan-only PR must merge before implementation begins.
- At implementation start, bind `PLAN_MERGE_COMMIT` to the merge commit produced by the plan-only PR and verify the implementation worktree starts exactly there.
- Create the implementation branch `implementation/e1-alfworld-evaluator-v1` in an isolated Git worktree.
- One task equals one focused implementation commit. Tasks 1 through 14 therefore produce exactly fourteen ordered implementation commits.
- Every task must demonstrate a valid RED before GREEN. Collection errors, syntax errors, missing-module errors, skipped tests, or deleted assertions do not count as valid RED.
- A task may create an importable stub that raises `NotImplementedError` so its focused tests fail after collection.
- Do not write production code for a later task before the current task is committed and post-commit verification passes.
- Ordinary tests must not import or instantiate real ALFWorld, TextWorld, Gym environments, vLLM, CUDA, or a GPU.
- Ordinary tests must not read the formal 134 gamefiles or connect to any network service.
- Builder scripts are implemented and tested only against explicit temporary fixtures during Tasks 2, 3, and 6.
- The following target-host artifacts are reserved outputs and must not be generated during implementation:
  - `configs/evaluation/e1_gamefile_sha256_preflight_v1.json`
  - `configs/evaluation/alfworld_environment_runtime_manifest_v1.json`
  - `configs/evaluation/e1_policy_runtime_manifest_v1.json`
- Running those builders on the target server requires the later approval `EXECUTION_APPROVED_E1_EVALUATOR_READINESS_PREFLIGHT`.
- Existing Runtime Core scientific semantics are immutable. Do not modify:
  - `src/pchsi/evaluation/runtime_core.py`
  - `src/pchsi/evaluation/raw_policy_parser.py`
  - `src/pchsi/evaluation/raw_policy_prompt.py`
  - `src/pchsi/evaluation/budget.py`
  - `src/pchsi/evaluation/action_trace.py`
- Do not modify the frozen task selection:
  - `data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl`
  - `configs/protocols/split_and_access_v1.json`
- Preserve the task-manifest SHA-256:
  `6e480bb663a6f17207aa2c7a6e1b504adad8448f6e8a2615c5e62fea0b64c0f4`.
- The frozen seeds are `17, 31, 47, 73, 101`; the schedule is seed-major and contains exactly 670 cells.
- The primary statistical unit is the unique task. The five seed replicates are not independent tasks.
- Hidden retry, automatic retry, best-of-run selection, action repair, menu sorting, menu filtering, menu deduplication, menu truncation, case normalization, fuzzy matching, controller logic, and phase inference are forbidden.
- `--execute` remains unconditionally closed in the implementation candidate.
- No repository-local string, environment variable, debug flag, configuration boolean, or command-line force flag may self-authorize execution.
- Every task ends with exact changed-path verification, one commit, focused post-commit verification, and a clean worktree.
- Do not squash, rebase, amend published commits, force-push, or directly push to `main`.

## Implementation worktree prelude

After the plan PR is merged, execute the worktree setup before Task 1:

```bash
cd ~/run/sdar_repro/badcase/github_exports/phase-critical-harness-guided-self-improvement

git fetch origin main

export PLAN_MERGE_COMMIT="$(git rev-parse origin/main)"
export IMPLEMENTATION_BRANCH="implementation/e1-alfworld-evaluator-v1"
export IMPLEMENTATION_WORKTREE="$HOME/run/sdar_repro/badcase/github_exports/worktrees/e1-alfworld-evaluator-v1"

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git worktree add -b "$IMPLEMENTATION_BRANCH" "$IMPLEMENTATION_WORKTREE" "$PLAN_MERGE_COMMIT"

cd "$IMPLEMENTATION_WORKTREE"
test "$(git rev-parse HEAD)" = "$PLAN_MERGE_COMMIT"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
```

Before Task 1, record the immutable baseline:

```bash
mkdir -p "$HOME/.cache/pchsi/e1-evaluator-implementation"

git rev-parse \
  HEAD:docs/superpowers/specs/2026-08-06-e1-alfworld-evaluator-v1-design.md \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/design.blob"

git hash-object \
  src/pchsi/evaluation/runtime_core.py \
  src/pchsi/evaluation/raw_policy_parser.py \
  src/pchsi/evaluation/raw_policy_prompt.py \
  src/pchsi/evaluation/budget.py \
  src/pchsi/evaluation/action_trace.py \
  data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl \
  configs/protocols/split_and_access_v1.json \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/frozen-paths.blobs"
```

## File responsibility map

| File or directory | Responsibility |
|---|---|
| `canonical_evidence.py` | Exact canonical JSON bytes, strict JSON parsing, finite-number and digest helpers |
| `schema_contract.py` | Closed-schema loading, validation, and Python-model/schema parity checks |
| `schema_models.py` | Frozen wire/artifact dataclasses shared by later tasks |
| `task_manifest.py` | Strict trusted-manifest parsing and order/identity validation |
| `gamefile_identity.py` | Fixture-safe gamefile SHA-1/SHA-256 identity models and builder logic |
| `environment_runtime_manifest.py` | Fixture-safe environment software/source identity |
| `alfworld_contracts.py` | Pure validation of reset/step batches, menu snapshots, gamefile latch, done/won/score |
| `alfworld_worker_protocol.py` | Closed parent/worker IPC messages |
| `alfworld_worker.py` | Lazily imported real-environment child entrypoint; never invoked in ordinary tests |
| `alfworld_adapter.py` | Spawned-process lifecycle, timeout, close, terminate, kill, join, and public result boundary |
| `policy_request.py` | Exact `E1_POLICY_REQUEST_V1` object and canonical bytes |
| `policy_response.py` | Strict non-streaming response-envelope parser |
| `rendered_prompt.py` | Frozen local rendered-token contract behind an injected tokenizer renderer |
| `policy_client.py` | Direct standard-library HTTP transport with exact bytes, no redirect, no retry |
| `policy_runtime_manifest.py` | Fixture-safe model/tokenizer/vLLM runtime identity |
| `run_schedule.py` | Exact 670-cell schedule and stable IDs |
| `run_resolution.py` | Attempt ordinal, retry eligibility, first-result lock, run invalidation, no best-of-run |
| `public_transition.py` | Non-leaking post-action public transition model |
| `trace_assembler.py` | Correct construction of existing `ActionTrace` values |
| `episode_sequence.py` | Cross-trace, budget, menu, feedback, M0, count, and termination validation |
| `attempt_state.py` | Scientific outcome and operational finalization state machines |
| `episode_artifact.py` | Semantic projection, attempt file bytes, and exact bundle identity |
| `artifact_publisher.py` | Crash-consistent staging, fsync, cell lock, directory rename, receipt publication |
| `cell_lock.py` | No-clobber scientific lock and lock/bundle matching |
| `episode_evaluator.py` | Single-episode orchestration using frozen Runtime Core and injected adapters |
| `result_audit.py` | 670-cell formal result completeness gate |
| `run_e1_evaluator.py` | Closed candidate CLI: describe, validate-config, reject execute |
| `audit_e1_evaluator_candidate.py` | Cumulative immutable-path, scope, no-real-execution, and requirement-matrix audit |
| `E1_EVALUATOR_REQUIREMENT_MATRIX.md` | Exact design requirement → source → test → command → task commit mapping |

## Shared focused-task protocol

Each Task uses this sequence:

```text
write focused tests and importable RED stubs
→ run focused RED and inspect the named failure
→ implement only the task's declared production scope
→ run focused GREEN
→ run task static audit
→ verify exact changed paths
→ commit with the frozen subject
→ rerun focused tests post-commit
→ record task commit SHA outside the repository
→ require a clean worktree
```

The task-specific sections below define the exact files, interfaces, RED tests,
commands, commit subjects, and forbidden behavior.

---

### Task 1: Canonical evidence and closed schema models

**Dependency:** Implementation worktree prelude completed; no earlier task commit.

**Files:**
- Create: `src/pchsi/evaluation/canonical_evidence.py`
- Create: `src/pchsi/evaluation/schema_contract.py`
- Create: `src/pchsi/evaluation/schema_models.py`
- Create: `configs/evaluation/schemas/e1_public_transition_v1.json`
- Create: `configs/evaluation/schemas/e1_attempt_receipt_v1.json`
- Create: `configs/evaluation/schemas/e1_scientific_cell_lock_v1.json`
- Create: `configs/evaluation/schemas/e1_episode_artifact_v1.json`
- Create: `configs/evaluation/schemas/e1_run_schedule_v1.json`
- Create: `tests/evaluation/test_canonical_evidence.py`
- Create: `tests/evaluation/test_schema_contract.py`
- Create: `tests/evaluation/test_schema_models.py`
- Create: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Produces:
  ```python
  def canonical_json_bytes(value: object) -> bytes: ...
  def canonical_json_text(value: object) -> str: ...
  def strict_json_loads(data: str | bytes) -> object: ...
  def sha256_bytes(data: bytes) -> str: ...
  def sha256_text(text: str) -> str: ...
  def sha256_file(path: Path) -> str: ...
  def require_lower_sha256(name: str, value: object) -> str: ...
  def require_nonnegative_int(name: str, value: object) -> int: ...
  def require_finite_number(name: str, value: object) -> int | float: ...
  ```
- Produces:
  ```python
  class StrictSchemaModel(Protocol):
      SCHEMA_ID: ClassVar[str]
      SCHEMA_VERSION: ClassVar[int]
      def to_dict(self) -> dict[str, object]: ...
      def to_json(self) -> str: ...

  def validate_model_against_schema(model: StrictSchemaModel) -> None: ...
  def validate_payload_against_schema(
      *, schema_id: str, payload: object
  ) -> None: ...
  ```
- Produces frozen dataclasses:
  `PublicTransitionRecordV1`, `AttemptReceiptV1`,
  `ScientificCellLockV1`, `EpisodeArtifactV1`, and `RunScheduleV1`.
- Later tasks must import these models instead of defining parallel artifact
  dictionaries.

**Wire-model field contracts:**

```text
PublicTransitionRecordV1:
schema_id, schema_version, scheduled_cell_id, execution_attempt_id,
model_call_index, environment_step_index, submitted_action,
pre_action_observation, pre_action_observation_sha256,
pre_action_admissible_commands, pre_action_admissible_commands_sha256,
resulting_observation, resulting_observation_sha256,
resulting_admissible_commands, resulting_admissible_commands_sha256,
done, won, score, pre_action_visibility, resulting_visibility

AttemptReceiptV1:
schema_id, schema_version, receipt_kind, run_id, scheduled_cell_id,
execution_attempt_id, attempt_ordinal, evaluator_commit,
design_merge_commit, runtime_core_commit, run_schedule_sha256,
scientific_outcome_status, operational_finalization_status,
episode_semantic_sha256, attempt_bundle_sha256, terminal_class,
error_code, created_at_utc

ScientificCellLockV1:
schema_id, schema_version, run_id, scheduled_cell_id,
execution_attempt_id, run_schedule_sha256, episode_semantic_sha256,
attempt_bundle_sha256, scientific_outcome_status, evaluator_commit

EpisodeArtifactV1:
schema_id, schema_version, run_id, scheduled_cell_id,
execution_attempt_id, attempt_ordinal, task_index, task_id, task_type,
gamefile_sha1, gamefile_sha256, seed, evaluator_commit,
design_merge_commit, runtime_core_commit, raw_protocol_sha256,
split_access_sha256, gamefile_identity_manifest_sha256,
environment_runtime_manifest_sha256, policy_runtime_manifest_sha256,
policy_request_schema_sha256, scientific_outcome_status,
operational_finalization_status, success, termination_reason,
final_score, final_done, final_won, final_budget, trace_count,
public_transition_count, environment_call_trace_count,
initial_observation_sha256, final_observation_sha256,
episode_semantic_sha256, started_at_utc, completed_at_utc

RunScheduleV1:
schema_id, schema_version, schedule_id, task_manifest_sha256,
replicate_seeds, order, cell_count, primary_statistical_unit,
replicates_are_not_independent_tasks,
pooled_670_iid_headline_result, cells
```

Every schema uses `additionalProperties: false`, exact `required` lists,
lowercase SHA-256 patterns, and explicit unions for nullable values.

**RED tests:**
- `test_canonical_json_bytes_are_sorted_compact_utf8_and_lf_terminated`
- `test_canonical_json_rejects_nan_infinity_and_duplicate_keys`
- `test_strict_integer_rejects_bool`
- `test_schema_inventory_is_exact_and_closed`
- `test_schema_validator_rejects_unsupported_keywords`
- `test_python_model_keys_equal_schema_properties`
- `test_all_schema_required_fields_are_produced`
- `test_unknown_and_missing_fields_are_rejected`
- `test_all_models_round_trip_without_changing_canonical_bytes`

- [ ] **Step 1: Create importable RED stubs and focused tests**

Create the production modules with the exact public names above. Each public
function raises `NotImplementedError("TASK1_RED")`; dataclass constructors may
exist but `to_dict`, `from_dict`, and schema validation raise the same error.

Create the five JSON schemas with their final IDs, versions, fields,
`required`, and `additionalProperties: false`.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_canonical_evidence.py \
  tests/evaluation/test_schema_contract.py \
  tests/evaluation/test_schema_models.py \
  tests/evaluation/test_evaluation_schema_inventory.py
```

Expected:

```text
tests collect successfully
at least the eight named tests fail
failure includes TASK1_RED or an exact unimplemented assertion
no ModuleNotFoundError
no SyntaxError
no skipped test
```

- [ ] **Step 3: Implement canonical and schema behavior**

Canonical JSON is:

```python
json.dumps(
    value,
    ensure_ascii=False,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8") + b"\n"
```

`strict_json_loads` must use an `object_pairs_hook` that rejects duplicate
keys before schema validation.

`schema_contract.py` is standard-library-only and implements exactly the
frozen schema subset used by this plan:

```text
$schema
$id
title
type
properties
required
additionalProperties
const
enum
oneOf
items
minItems
maxItems
uniqueItems
minLength
maxLength
pattern
minimum
```

Any schema containing an unsupported keyword is rejected. Do not import or
depend on undeclared third-party validators such as `jsonschema` or
`fastjsonschema`.

`require_nonnegative_int` must use `type(value) is int`.
`require_finite_number` accepts `int` or `float`, rejects `bool`, NaN, and
infinity. Do not add NumPy as a dependency in this task.

Each model implements exact `from_dict`, `to_dict`, `from_json`, and `to_json`
round trips and validates itself against its JSON schema.

- [ ] **Step 4: Run focused GREEN**

Run the same focused command. Expected: exit code `0`, all selected tests
pass, no skips.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/canonical_evidence.py \
  src/pchsi/evaluation/schema_contract.py \
  src/pchsi/evaluation/schema_models.py \
  tests/evaluation/test_canonical_evidence.py \
  tests/evaluation/test_schema_contract.py \
  tests/evaluation/test_schema_models.py \
  tests/evaluation/test_evaluation_schema_inventory.py
```

**Static audit:**

```bash
grep -RInE \
  'datetime\.now|time\.time|uuid\.uuid4|allow_nan=True|default=str|import jsonschema|import fastjsonschema|from jsonschema|from fastjsonschema' \
  src/pchsi/evaluation/canonical_evidence.py \
  src/pchsi/evaluation/schema_contract.py \
  src/pchsi/evaluation/schema_models.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
configs/evaluation/schemas/e1_attempt_receipt_v1.json
configs/evaluation/schemas/e1_episode_artifact_v1.json
configs/evaluation/schemas/e1_public_transition_v1.json
configs/evaluation/schemas/e1_run_schedule_v1.json
configs/evaluation/schemas/e1_scientific_cell_lock_v1.json
src/pchsi/evaluation/canonical_evidence.py
src/pchsi/evaluation/schema_contract.py
src/pchsi/evaluation/schema_models.py
tests/evaluation/test_canonical_evidence.py
tests/evaluation/test_evaluation_schema_inventory.py
tests/evaluation/test_schema_contract.py
tests/evaluation/test_schema_models.py
```

**Commit:**

```bash
git add -- \
  configs/evaluation/schemas \
  src/pchsi/evaluation/canonical_evidence.py \
  src/pchsi/evaluation/schema_contract.py \
  src/pchsi/evaluation/schema_models.py \
  tests/evaluation/test_canonical_evidence.py \
  tests/evaluation/test_schema_contract.py \
  tests/evaluation/test_schema_models.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git diff --cached --check
git commit -m "Implement canonical evaluator evidence contracts"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_canonical_evidence.py \
  tests/evaluation/test_schema_contract.py \
  tests/evaluation/test_schema_models.py \
  tests/evaluation/test_evaluation_schema_inventory.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task01.commit"
```

**Forbidden:**
- Environment, model, network, filesystem publication, wall-clock-generated
  scientific values, permissive schema fields, unknown-field preservation,
  duplicate-key acceptance, or parallel artifact dictionary implementations.

---

### Task 2: Frozen task manifest and fixture-safe gamefile identity builder

**Dependency:** Task 1 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/task_manifest.py`
- Create: `src/pchsi/evaluation/gamefile_identity.py`
- Create: `scripts/evaluation/build_e1_gamefile_sha256_manifest.py`
- Create: `configs/evaluation/schemas/e1_gamefile_sha256_preflight_v1.json`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`
- Create: `tests/evaluation/test_task_manifest.py`
- Create: `tests/evaluation/test_gamefile_identity.py`
- Create: `tests/evaluation/test_gamefile_identity_builder.py`

**Interfaces:**
- Consumes Task 1 canonical/schema helpers.
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class FrozenTaskRecord:
      index: int
      task_id: str
      split: str
      task_type: str
      gamefile: str
      gamefile_sha1: str
      root: str
      traj_file: str

  def load_frozen_task_manifest(
      *,
      manifest_path: Path,
      expected_sha256: str,
      expected_record_count: int = 134,
  ) -> tuple[FrozenTaskRecord, ...]: ...

  @dataclass(frozen=True, slots=True)
  class GamefileIdentityRecordV1:
      index: int
      task_id: str
      gamefile_sha1: str
      gamefile_sha256: str

  @dataclass(frozen=True, slots=True)
  class GamefileIdentityManifestV1(StrictSchemaModel):
      ...

  def build_gamefile_identity_manifest(
      *,
      records: Sequence[FrozenTaskRecord],
      output_path: Path,
  ) -> GamefileIdentityManifestV1: ...
  ```
- Builder CLI requires explicit `--task-manifest`, `--expected-manifest-sha256`,
  and `--output`; it has no default path to the formal manifest.

**RED tests:**
- `test_manifest_loader_preserves_exact_order_and_134_identity`
- `test_manifest_loader_rejects_hash_count_index_id_split_and_duplicate_errors`
- `test_manifest_loader_rejects_symlinked_manifest`
- `test_gamefile_identity_rejects_missing_symlink_and_sha1_mismatch`
- `test_fixture_builder_writes_exact_closed_manifest_no_clobber`
- `test_builder_has_no_formal_manifest_default`

- [ ] **Step 1: Write RED tests and stubs**

Stubs expose the exact interfaces and raise `NotImplementedError("TASK2_RED")`.
Tests create small temporary JSONL manifests and temporary gamefiles; they do
not read the repository's formal 134 gamefiles.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_task_manifest.py \
  tests/evaluation/test_gamefile_identity.py \
  tests/evaluation/test_gamefile_identity_builder.py \
  tests/evaluation/test_evaluation_schema_inventory.py
```

Expected: named tests fail through `TASK2_RED`, with successful collection and
no skipped tests.

- [ ] **Step 3: Implement strict manifest and identity behavior**

The loader must reject:

```text
manifest symlink
wrong manifest SHA-256
blank lines
non-object records
unknown or missing required fields
non-contiguous index
wrong ID format/order
split other than valid_unseen
duplicate task ID
duplicate gamefile
non-absolute gamefile path
```

The builder validates regular, non-symlink gamefiles, compares manifest SHA-1
to actual bytes, computes SHA-256, preserves task order, writes canonical
bytes with mode `0600`, and refuses an existing output.

- [ ] **Step 4: Run focused GREEN**

Use the same focused command. Expected: exit `0`, all selected tests pass.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/task_manifest.py \
  src/pchsi/evaluation/gamefile_identity.py \
  scripts/evaluation/build_e1_gamefile_sha256_manifest.py \
  tests/evaluation/test_task_manifest.py \
  tests/evaluation/test_gamefile_identity.py \
  tests/evaluation/test_gamefile_identity_builder.py
```

**Static audit:**

```bash
grep -RIn \
  'alfworld_strict_valid_unseen_all134_v1.jsonl' \
  scripts/evaluation/build_e1_gamefile_sha256_manifest.py \
  && exit 1 || true

grep -RInE \
  'import alfworld|import textworld|env\.reset|env\.step|requests\.|httpx\.|urllib\.request' \
  src/pchsi/evaluation/task_manifest.py \
  src/pchsi/evaluation/gamefile_identity.py \
  scripts/evaluation/build_e1_gamefile_sha256_manifest.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
configs/evaluation/schemas/e1_gamefile_sha256_preflight_v1.json
scripts/evaluation/build_e1_gamefile_sha256_manifest.py
src/pchsi/evaluation/gamefile_identity.py
src/pchsi/evaluation/task_manifest.py
tests/evaluation/test_evaluation_schema_inventory.py
tests/evaluation/test_gamefile_identity.py
tests/evaluation/test_gamefile_identity_builder.py
tests/evaluation/test_task_manifest.py
```

**Commit:**

```bash
git add -- \
  configs/evaluation/schemas/e1_gamefile_sha256_preflight_v1.json \
  scripts/evaluation/build_e1_gamefile_sha256_manifest.py \
  src/pchsi/evaluation/task_manifest.py \
  src/pchsi/evaluation/gamefile_identity.py \
  tests/evaluation/test_evaluation_schema_inventory.py \
  tests/evaluation/test_task_manifest.py \
  tests/evaluation/test_gamefile_identity.py \
  tests/evaluation/test_gamefile_identity_builder.py

git diff --cached --check
git commit -m "Implement frozen E1 task and gamefile identity"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_task_manifest.py \
  tests/evaluation/test_gamefile_identity.py \
  tests/evaluation/test_gamefile_identity_builder.py \
  tests/evaluation/test_evaluation_schema_inventory.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task02.commit"
```

**Forbidden:**
- Reading the formal 134 gamefiles during implementation tests, creating an
  environment, importing ALFWorld, path relocation, directory task discovery,
  output overwrite, or committing a target-host readiness artifact.

---

### Task 3: Fixture-safe environment runtime identity builder

**Dependency:** Task 2 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/environment_runtime_manifest.py`
- Create: `scripts/evaluation/build_environment_runtime_manifest.py`
- Create: `configs/evaluation/schemas/alfworld_environment_runtime_manifest_v1.json`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`
- Create: `tests/evaluation/test_environment_runtime_manifest.py`
- Create: `tests/evaluation/test_environment_runtime_manifest_builder.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class SourceIdentity:
      logical_name: str
      source_path: str
      sha256: str

  @dataclass(frozen=True, slots=True)
  class EnvironmentRuntimeInputs:
      python_version: str
      python_executable_sha256: str
      alfworld_version: str
      textworld_version: str
      gym_version: str
      source_identities: tuple[SourceIdentity, ...]
      wrapper_order: tuple[str, ...]
      env_infos: tuple[str, ...]
      batch_size: int
      asynchronous: bool
      auto_reset: bool
      max_episode_steps: int
      process_start_method: str

  @dataclass(frozen=True, slots=True)
  class EnvironmentRuntimeManifestV1(StrictSchemaModel):
      ...

  def build_environment_runtime_manifest(
      *,
      inputs: EnvironmentRuntimeInputs,
      output_path: Path,
  ) -> EnvironmentRuntimeManifestV1: ...
  ```
- Required logical source names:
  `AlfredTWEnv`, `AlfredDemangler`, `AlfredInfos`,
  `textworld.gym.register_games`.

**RED tests:**
- `test_environment_manifest_binds_exact_runtime_and_source_hashes`
- `test_environment_manifest_requires_frozen_wrapper_and_envinfo_contract`
- `test_environment_manifest_requires_spawn_and_31_steps`
- `test_environment_builder_uses_only_explicit_fixture_inputs`
- `test_environment_builder_is_no_clobber_and_deterministic`

- [ ] **Step 1: Write RED tests and stubs**

Tests create fake package/source files and pass all metadata explicitly. The
builder must not inspect the installed target-host ALFWorld during tests.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest_builder.py \
  tests/evaluation/test_evaluation_schema_inventory.py
```

Expected: failures through `NotImplementedError("TASK3_RED")`, not package
import failures.

- [ ] **Step 3: Implement runtime identity validation**

Freeze:

```text
wrapper_order = ("AlfredDemangler(shuffle=false)", "AlfredInfos")
env_infos = ("won", "admissible_commands", "extra.gamefile")
batch_size = 1
asynchronous = false
auto_reset = false
max_episode_steps = 31
process_start_method = "spawn"
```

Reject missing logical source identities, duplicate names, non-lowercase
digests, mutable list order, `fork`, and any existing output.

- [ ] **Step 4: Run focused GREEN**

Same command; expected exit `0` and no skips.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/environment_runtime_manifest.py \
  scripts/evaluation/build_environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest_builder.py
```

**Static audit:**

```bash
grep -RInE \
  'import alfworld|import textworld|import gym|pkg_resources|importlib\.metadata\.version' \
  src/pchsi/evaluation/environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest_builder.py \
  && exit 1 || true
```

The readiness builder may later gather installed metadata, but its unit tests
must inject a fake inspector and prove no import occurs at module import time.

**Expected changed paths:**

```text
configs/evaluation/schemas/alfworld_environment_runtime_manifest_v1.json
scripts/evaluation/build_environment_runtime_manifest.py
src/pchsi/evaluation/environment_runtime_manifest.py
tests/evaluation/test_environment_runtime_manifest.py
tests/evaluation/test_environment_runtime_manifest_builder.py
tests/evaluation/test_evaluation_schema_inventory.py
```

**Commit:**

```bash
git add -- \
  configs/evaluation/schemas/alfworld_environment_runtime_manifest_v1.json \
  scripts/evaluation/build_environment_runtime_manifest.py \
  src/pchsi/evaluation/environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest_builder.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git diff --cached --check
git commit -m "Implement evaluator environment runtime identity"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_environment_runtime_manifest.py \
  tests/evaluation/test_environment_runtime_manifest_builder.py \
  tests/evaluation/test_evaluation_schema_inventory.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task03.commit"
```

**Forbidden:**
- Importing or initializing a real environment, inspecting the target-host
  installation in pytest, generating the authoritative runtime manifest,
  accepting fork/forkserver, or deriving wrapper order from runtime defaults.

---

### Task 4: Strict ALFWorld reset, step, menu, and public-state contracts

**Dependency:** Task 3 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/alfworld_contracts.py`
- Create: `tests/evaluation/test_alfworld_contracts.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class MenuSnapshot:
      commands: tuple[str, ...]
      sequence_sha256: str

  @dataclass(frozen=True, slots=True)
  class GamefileIdentityLatch:
      resolved_gamefile: str

  @dataclass(frozen=True, slots=True)
  class ResetPublicState:
      observation: str
      menu: MenuSnapshot
      gamefile_latch: GamefileIdentityLatch

  @dataclass(frozen=True, slots=True)
  class StepPublicState:
      observation: str
      menu: MenuSnapshot
      score: int | float
      done: bool
      won: bool

  def snapshot_menu(
      *,
      infos: Mapping[str, object],
      done: bool,
  ) -> MenuSnapshot: ...

  def parse_reset_batch(
      *,
      observations: object,
      infos: object,
      expected_gamefile: Path,
  ) -> ResetPublicState: ...

  def parse_step_batch(
      *,
      result: object,
      gamefile_latch: GamefileIdentityLatch,
  ) -> StepPublicState: ...
  ```
- `parse_step_batch` validates the four-item return before Runtime Core
  finalization.
- The step gamefile field is optional-if-present.

**RED tests:**
- `test_menu_outer_and_inner_string_like_values_are_rejected`
- `test_menu_mapping_and_iterator_values_are_rejected`
- `test_menu_duplicate_commands_and_order_are_preserved`
- `test_nonterminal_empty_menu_is_rejected_and_terminal_empty_menu_allowed`
- `test_reset_requires_exact_single_gamefile_and_latches_identity`
- `test_step_gamefile_missing_none_and_single_none_are_accepted`
- `test_step_nonnull_gamefile_must_match_reset_latch`
- `test_step_requires_exact_four_item_singleton_batches`
- `test_done_and_won_require_type_bool`
- `test_score_is_finite_numeric_and_not_bool`
- `test_won_true_done_false_is_rejected`

- [ ] **Step 1: Write RED tests and stubs**

Create the dataclasses and functions with final signatures. Functions raise
`NotImplementedError("TASK4_RED")`.

The tests use plain Python lists, tuples, dicts, generators, strings, and
temporary gamefile paths. They do not import ALFWorld or TextWorld.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_alfworld_contracts.py
```

Expected: all named behavior tests collect and fail through `TASK4_RED`;
no missing-module, syntax, or skip outcome.

- [ ] **Step 3: Implement strict public-contract parsing**

A stable sequence is accepted only when it implements `collections.abc.Sequence`
and is not `str`, `bytes`, `bytearray`, or `Mapping`.

The menu snapshot is constructed exactly once after structural validation.
Command shape validation is delegated to the existing Runtime Core menu
validator; this task does not sort, deduplicate, strip, lowercase, or repair.

Reset `extra.gamefile` contract:

```text
key required
outer stable sequence
length exactly one
element non-empty str
resolved element equals expected frozen gamefile
latch resolved identity
```

Step `extra.gamefile` contract:

```text
key absent: accepted
value None: accepted
singleton batch containing None: accepted
singleton batch containing str: resolve and compare to latch
all other forms: reject
```

`parse_step_batch` requires a four-item result and singleton outer sequences
for observations, scores, dones, and every requested info field. It uses
`type(value) is bool` for done/won and `math.isfinite` for numeric scores.

- [ ] **Step 4: Run focused GREEN**

```bash
python -m pytest -q \
  tests/evaluation/test_alfworld_contracts.py
```

Expected: exit `0`, all selected tests pass, no skips.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/alfworld_contracts.py \
  tests/evaluation/test_alfworld_contracts.py
```

**Static audit:**

```bash
grep -RInE \
  'tuple\(.*admissible_commands.*\[0\]\)|bool\(.*done|bool\(.*won|sorted\(|set\(|casefold\(|lower\(' \
  src/pchsi/evaluation/alfworld_contracts.py \
  && exit 1 || true

grep -RInE \
  'import alfworld|import textworld|import gym' \
  src/pchsi/evaluation/alfworld_contracts.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
src/pchsi/evaluation/alfworld_contracts.py
tests/evaluation/test_alfworld_contracts.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/alfworld_contracts.py \
  tests/evaluation/test_alfworld_contracts.py

git diff --cached --check
git commit -m "Implement strict ALFWorld data contracts"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_alfworld_contracts.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task04.commit"
```

**Forbidden:**
- Real environment imports, `bool()` coercion of done/won, unstable iterators,
  string-to-character conversion, menu repair, storing raw infos, requiring
  step `extra.gamefile` when absent or `None`, or finalizing Runtime Core here.

---

### Task 5: Spawned worker IPC and exact environment adapter lifecycle

**Dependency:** Task 4 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/alfworld_worker_protocol.py`
- Create: `src/pchsi/evaluation/alfworld_worker.py`
- Create: `src/pchsi/evaluation/alfworld_adapter.py`
- Create: `tests/evaluation/test_alfworld_worker_protocol.py`
- Create: `tests/evaluation/test_alfworld_worker_lifecycle.py`
- Create: `tests/evaluation/test_alfworld_adapter.py`

**Interfaces:**
- Produces closed IPC dataclasses:
  ```python
  CreateEnvironmentRequest
  ResetRequest
  StepRequest
  CloseRequest

  EnvironmentCreated
  ResetResult
  StepResult
  WorkerFailure
  WorkerTerminalStatus
  ```
- Every message implements Task 1 canonical serialization and rejects unknown
  fields.
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class WorkerTimeouts:
      constructor_seconds: float = 120.0
      reset_seconds: float = 60.0
      step_seconds: float = 60.0
      close_seconds: float = 30.0
      exit_seconds: float = 15.0
      terminate_grace_seconds: float = 5.0
      kill_grace_seconds: float = 5.0

  class SpawnedAlfworldAdapter:
      @classmethod
      def start(
          cls,
          *,
          exact_gamefile: Path,
          registration_id: str,
          runtime_manifest_sha256: str,
          timeouts: WorkerTimeouts = WorkerTimeouts(),
          worker_target: Callable[..., None] | None = None,
      ) -> SpawnedAlfworldAdapter: ...

      def reset(self) -> ResetPublicState: ...
      def step(self, action: str) -> StepPublicState: ...
      def close(self) -> WorkerTerminalStatus: ...
  ```
- `worker_target=None` selects the real worker only inside the spawned child.
  Tests always inject a fake top-level picklable worker target.

**Frozen worker boundary:**

```text
multiprocessing context = get_context("spawn")
fork fallback = forbidden
one worker = one execution attempt
one worker = one exact gamefile
no environment object crosses IPC
worker cannot call policy
worker cannot choose another task
worker cannot publish final artifacts
complete raw infos cannot cross IPC
```

The real child entrypoint lazily imports ALFWorld/TextWorld/Gym only after it
has validated `CreateEnvironmentRequest`.

**RED tests:**
- `test_worker_messages_are_closed_canonical_and_round_trip`
- `test_adapter_uses_spawn_context_and_rejects_fork_fallback`
- `test_one_worker_handles_one_exact_gamefile`
- `test_reset_and_step_return_only_public_fields`
- `test_constructor_reset_step_close_timeouts_are_classified`
- `test_unexpected_worker_death_is_classified`
- `test_close_is_sent_at_most_once`
- `test_terminate_then_kill_then_join_reaps_worker`
- `test_no_environment_object_or_raw_infos_crosses_ipc`
- `test_real_environment_import_is_lazy_and_not_reached_by_tests`

- [ ] **Step 1: Write RED tests and importable worker/adapter stubs**

Stubs expose final messages, timeout constants, and adapter methods. Adapter
methods raise `NotImplementedError("TASK5_RED")`.

Use fake worker targets defined at module top level so they are picklable
under `spawn`.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_alfworld_worker_protocol.py \
  tests/evaluation/test_alfworld_worker_lifecycle.py \
  tests/evaluation/test_alfworld_adapter.py
```

Expected: named tests fail through `TASK5_RED` after successful collection.
The test process must not import `alfworld`, `textworld`, or `gym`.

- [ ] **Step 3: Implement IPC and lifecycle**

Use `multiprocessing.get_context("spawn")`, a duplex `Pipe`, and canonical
message bytes. Parent and child both validate message schema before acting.

Real worker creation parameters are frozen:

```text
gamefiles=[exact_gamefile]
batch_size=1
asynchronous=false
auto_reset=false
max_episode_steps=31
EnvInfos: won, admissible_commands, extra.gamefile
wrappers: AlfredDemangler(shuffle=false), AlfredInfos
```

The real worker must bypass directory collection and must never include
`AlfredExpert`, `expert_plan`, `policy_commands`, or `facts`.

Lifecycle on timeout:

```text
send CloseRequest when protocol state permits
wait close timeout
terminate
wait terminate grace
kill if still alive
join/reap
emit one terminal classification
```

`close()` is idempotent at the parent API but sends at most one close request.

- [ ] **Step 4: Run focused GREEN**

Use the same focused command. Expected: exit `0`; all selected tests pass
without real environment imports.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/alfworld_worker_protocol.py \
  src/pchsi/evaluation/alfworld_worker.py \
  src/pchsi/evaluation/alfworld_adapter.py \
  tests/evaluation/test_alfworld_worker_protocol.py \
  tests/evaluation/test_alfworld_worker_lifecycle.py \
  tests/evaluation/test_alfworld_adapter.py
```

**Static audit:**

```bash
grep -RInE \
  'get_context\(["'\'']fork|set_start_method\(["'\'']fork|os\.fork|ProcessPoolExecutor' \
  src/pchsi/evaluation/alfworld_worker.py \
  src/pchsi/evaluation/alfworld_adapter.py \
  && exit 1 || true

python - <<'PY'
import sys
import pchsi.evaluation.alfworld_adapter
import pchsi.evaluation.alfworld_worker_protocol
assert "alfworld" not in sys.modules
assert "textworld" not in sys.modules
assert "gym" not in sys.modules
print("TASK5_LAZY_IMPORT_AUDIT_OK")
PY
```

**Expected changed paths:**

```text
src/pchsi/evaluation/alfworld_adapter.py
src/pchsi/evaluation/alfworld_worker.py
src/pchsi/evaluation/alfworld_worker_protocol.py
tests/evaluation/test_alfworld_adapter.py
tests/evaluation/test_alfworld_worker_lifecycle.py
tests/evaluation/test_alfworld_worker_protocol.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/alfworld_worker_protocol.py \
  src/pchsi/evaluation/alfworld_worker.py \
  src/pchsi/evaluation/alfworld_adapter.py \
  tests/evaluation/test_alfworld_worker_protocol.py \
  tests/evaluation/test_alfworld_worker_lifecycle.py \
  tests/evaluation/test_alfworld_adapter.py

git diff --cached --check
git commit -m "Implement spawned ALFWorld worker adapter"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_alfworld_worker_protocol.py \
  tests/evaluation/test_alfworld_worker_lifecycle.py \
  tests/evaluation/test_alfworld_adapter.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task05.commit"
```

**Forbidden:**
- Fork/forkserver fallback, pooling workers across attempts, real environment
  construction in pytest, raw infos IPC, policy calls in child, artifact
  publication in child, task selection in child, unbounded waits, unjoined
  children, or environment object serialization.

---

### Task 6: Exact policy request, response, rendered prompt, transport, and runtime identity

**Dependency:** Task 5 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/policy_request.py`
- Create: `src/pchsi/evaluation/policy_response.py`
- Create: `src/pchsi/evaluation/rendered_prompt.py`
- Create: `src/pchsi/evaluation/policy_client.py`
- Create: `src/pchsi/evaluation/policy_runtime_manifest.py`
- Create: `scripts/evaluation/build_policy_runtime_manifest.py`
- Create: `scripts/evaluation/validate_e1_vllm_readiness.py`
- Create: `configs/evaluation/schemas/e1_policy_runtime_manifest_v1.json`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`
- Create: `tests/evaluation/test_policy_request.py`
- Create: `tests/evaluation/test_policy_response.py`
- Create: `tests/evaluation/test_rendered_prompt.py`
- Create: `tests/evaluation/test_policy_client.py`
- Create: `tests/evaluation/test_policy_runtime_manifest.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class E1PolicyRequestV1:
      prompt_text: str
      seed: int
      request_id: str
      def to_wire_dict(self) -> dict[str, object]: ...
      def to_wire_bytes(self) -> bytes: ...

  @dataclass(frozen=True, slots=True)
  class RenderedPromptEvidence:
      raw_policy_prompt_sha256: str
      chat_template_sha256: str
      rendered_prompt_text_sha256: str
      rendered_token_ids: tuple[int, ...]
      rendered_token_ids_sha256: str
      prompt_token_count: int

  @dataclass(frozen=True, slots=True)
  class PolicyGeneration:
      raw_response_text: str
      raw_response_body: bytes
      provider_request_id: str
      client_request_id: str
      finish_reason: str
      prompt_tokens: int
      completion_tokens: int
      prompt_token_ids: tuple[int, ...]
      token_ids: tuple[int, ...] | None
      latency_ms: int

  class PromptRenderer(Protocol):
      def render(
          self, *, prompt_text: str
      ) -> RenderedPromptEvidence: ...

  class PolicyTransport(Protocol):
      def post_exact(
          self, *, path: str, body: bytes, headers: Mapping[str, str]
      ) -> tuple[int, Mapping[str, str], bytes]: ...

  class PolicyClient:
      def generate(
          self,
          *,
          request: E1PolicyRequestV1,
          expected_prompt: RenderedPromptEvidence,
      ) -> PolicyGeneration: ...
  ```
- Standard transport uses `http.client`; redirects are rejected, retries are
  zero, and response bytes are retained before JSON parsing.
- Local tokenizer loading is isolated behind an injected factory and must set:
  `local_files_only=True`, `trust_remote_code=False`.
- Produces `PolicyRuntimeManifestV1` and the fixture-safe builder/validator.

**Exact request constraints:**
- Endpoint: `/v1/chat/completions`
- Exactly one user message containing the exact `RAW_POLICY_PROMPT_V1`.
- Every key/value from the approved design's `E1_POLICY_REQUEST_V1`.
- Forbidden keys absent.
- `return_token_ids=true`, `stream=false`, `n=1`, hidden retry zero.
- Prompt truncation forbidden.

**RED tests:**
- `test_policy_request_has_exact_key_set_and_canonical_bytes`
- `test_policy_request_forbidden_keys_are_absent`
- `test_policy_request_seed_and_request_id_are_exact`
- `test_policy_response_requires_http_200_single_choice_usage_and_ids`
- `test_length_finish_is_completed_generation`
- `test_prompt_token_ids_must_match_local_rendering`
- `test_policy_transport_sends_exact_bytes_no_redirect_no_retry`
- `test_renderer_uses_local_files_only_and_no_remote_code`
- `test_policy_runtime_manifest_binds_server_and_tokenizer_identity`
- `test_policy_readiness_builder_uses_explicit_fixture_inputs_only`

- [ ] **Step 1: Write RED tests and stubs**

All network behavior uses an injected fake `PolicyTransport`. All tokenizer
behavior uses an injected fake renderer/factory. Stubs raise
`NotImplementedError("TASK6_RED")`.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_policy_request.py \
  tests/evaluation/test_policy_response.py \
  tests/evaluation/test_rendered_prompt.py \
  tests/evaluation/test_policy_client.py \
  tests/evaluation/test_policy_runtime_manifest.py \
  tests/evaluation/test_evaluation_schema_inventory.py
```

Expected: named tests fail through `TASK6_RED`; no socket connection, package
download, tokenizer download, CUDA initialization, or missing-module error.

- [ ] **Step 3: Implement exact request and response contracts**

`E1PolicyRequestV1.to_wire_dict()` must return exactly the approved key set
and exact values. `to_wire_bytes()` uses Task 1 canonical bytes.

`PolicyClient.generate()`:

```text
renders expected prompt locally
posts exact bytes once
rejects redirect and non-200 status
stores exact response bytes
strictly parses one JSON object
requires one choice/content/finish_reason
requires nonnegative token counts and provider ID
requires prompt_token_ids
compares prompt token IDs exactly
returns PolicyGeneration
```

Transport, HTTP, envelope, and token mismatch errors remain pre-result
infrastructure/protocol classifications for Task 11; this task only exposes
typed exceptions.

`PolicyRuntimeManifestV1` binds vLLM `0.11.0`, model/tokenizer revision,
served model name, dtype, tensor parallel size, generation-config mode,
template identity, request-ID mode, and token-ID response support.

- [ ] **Step 4: Run focused GREEN**

Use the same command. Expected: exit `0`, all selected tests pass, no skips.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/policy_request.py \
  src/pchsi/evaluation/policy_response.py \
  src/pchsi/evaluation/rendered_prompt.py \
  src/pchsi/evaluation/policy_client.py \
  src/pchsi/evaluation/policy_runtime_manifest.py \
  scripts/evaluation/build_policy_runtime_manifest.py \
  scripts/evaluation/validate_e1_vllm_readiness.py
```

**Static audit:**

```bash
grep -RInE \
  'import openai|from openai|requests\.|httpx\.|retry|follow_redirects=True|trust_remote_code=True|local_files_only=False' \
  src/pchsi/evaluation/policy_*.py \
  src/pchsi/evaluation/rendered_prompt.py \
  scripts/evaluation/build_policy_runtime_manifest.py \
  scripts/evaluation/validate_e1_vllm_readiness.py \
  && exit 1 || true

grep -RInE \
  'huggingface_hub|snapshot_download|from_pretrained\(.*local_files_only=False' \
  src/pchsi/evaluation/rendered_prompt.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
configs/evaluation/schemas/e1_policy_runtime_manifest_v1.json
scripts/evaluation/build_policy_runtime_manifest.py
scripts/evaluation/validate_e1_vllm_readiness.py
src/pchsi/evaluation/policy_client.py
src/pchsi/evaluation/policy_request.py
src/pchsi/evaluation/policy_response.py
src/pchsi/evaluation/policy_runtime_manifest.py
src/pchsi/evaluation/rendered_prompt.py
tests/evaluation/test_evaluation_schema_inventory.py
tests/evaluation/test_policy_client.py
tests/evaluation/test_policy_request.py
tests/evaluation/test_policy_response.py
tests/evaluation/test_policy_runtime_manifest.py
tests/evaluation/test_rendered_prompt.py
```

**Commit:**

```bash
git add -- \
  configs/evaluation/schemas/e1_policy_runtime_manifest_v1.json \
  scripts/evaluation/build_policy_runtime_manifest.py \
  scripts/evaluation/validate_e1_vllm_readiness.py \
  src/pchsi/evaluation/policy_request.py \
  src/pchsi/evaluation/policy_response.py \
  src/pchsi/evaluation/rendered_prompt.py \
  src/pchsi/evaluation/policy_client.py \
  src/pchsi/evaluation/policy_runtime_manifest.py \
  tests/evaluation/test_policy_request.py \
  tests/evaluation/test_policy_response.py \
  tests/evaluation/test_rendered_prompt.py \
  tests/evaluation/test_policy_client.py \
  tests/evaluation/test_policy_runtime_manifest.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git diff --cached --check
git commit -m "Implement frozen E1 policy transport"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_policy_request.py \
  tests/evaluation/test_policy_response.py \
  tests/evaluation/test_rendered_prompt.py \
  tests/evaluation/test_policy_client.py \
  tests/evaluation/test_policy_runtime_manifest.py \
  tests/evaluation/test_evaluation_schema_inventory.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task06.commit"
```

**Forbidden:**
- OpenAI SDK serialization, real HTTP in tests, redirects, retries, streaming,
  omitted null-field drift, prompt truncation, tokenizer network access,
  remote code, real vLLM startup, GPU initialization, or committing the
  target-host policy runtime manifest.

---

### Task 7: Frozen 670-cell run schedule and attempt resolution

**Dependency:** Task 6 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/run_schedule.py`
- Create: `src/pchsi/evaluation/run_resolution.py`
- Create: `tests/evaluation/test_run_schedule.py`
- Create: `tests/evaluation/test_run_resolution.py`

**Interfaces:**
- Consumes `RunScheduleV1`, `FrozenTaskRecord`, and Task 1 canonical helpers.
- Produces:
  ```python
  REPLICATE_SEEDS: tuple[int, ...] = (17, 31, 47, 73, 101)

  @dataclass(frozen=True, slots=True)
  class ScheduledCell:
      scheduled_cell_id: str
      task_index: int
      task_id: str
      seed: int

  def build_e1_run_schedule(
      *,
      records: Sequence[FrozenTaskRecord],
      task_manifest_sha256: str,
  ) -> RunScheduleV1: ...

  def scheduled_cell_id(*, task_index: int, seed: int) -> str: ...
  def execution_attempt_id(
      *, scheduled_cell_id: str, attempt_ordinal: int
  ) -> str: ...

  class RunResolutionState:
      def begin_attempt(
          self, *, scheduled_cell_id: str
      ) -> AttemptAuthorization: ...
      def record_terminal_attempt(
          self, *, receipt: AttemptReceiptV1
      ) -> RunResolutionState: ...
      def can_retry(
          self, *, scheduled_cell_id: str
      ) -> bool: ...
  ```
- Cell ID is exactly:
  `e1-t<task_index_4_digits>-s<seed_10_digits>`.
- Attempt ID is exactly:
  `<scheduled_cell_id>-a<attempt_ordinal_3_digits>`.

**RED tests:**
- `test_schedule_contains_exact_seed_major_670_cells`
- `test_schedule_ids_are_stable_and_unique`
- `test_schedule_primary_statistical_unit_is_unique_task`
- `test_attempt_ordinals_are_monotonic_and_no_clobber`
- `test_first_scientific_result_locks_cell`
- `test_pre_result_infrastructure_failure_allows_explicit_retry`
- `test_protocol_error_invalidates_entire_run`
- `test_post_result_operational_failure_does_not_authorize_model_retry`
- `test_best_of_run_selection_is_impossible`

- [ ] **Step 1: Write RED tests and stubs**

Stubs expose final signatures and raise `NotImplementedError("TASK7_RED")`.
Use synthetic 134-record fixtures with stable task IDs; do not read gamefiles.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_run_schedule.py \
  tests/evaluation/test_run_resolution.py
```

Expected: named tests fail through `TASK7_RED`, with no skip or collection
failure.

- [ ] **Step 3: Implement schedule and resolution**

Schedule ordering is:

```text
seed 17: tasks 0000..0133
seed 31: tasks 0000..0133
seed 47: tasks 0000..0133
seed 73: tasks 0000..0133
seed 101: tasks 0000..0133
```

`RunResolutionState` retains every attempt receipt. A cell is retryable only
when every terminal attempt has
`SCIENTIFIC_OUTCOME_NOT_PRODUCED` and an allowed pre-result infrastructure
classification. The first success/task-failure receipt locks the cell.

A protocol configuration error sets a run-invalid flag and forbids any
further attempt authorization.

- [ ] **Step 4: Run focused GREEN**

Same focused command; expected exit `0`, all selected tests pass.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/run_schedule.py \
  src/pchsi/evaluation/run_resolution.py \
  tests/evaluation/test_run_schedule.py \
  tests/evaluation/test_run_resolution.py
```

**Static audit:**

```bash
grep -RInE \
  'random|shuffle|choice|sample|best|sorted\(.*seed|set\(.*cells' \
  src/pchsi/evaluation/run_schedule.py \
  src/pchsi/evaluation/run_resolution.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
src/pchsi/evaluation/run_resolution.py
src/pchsi/evaluation/run_schedule.py
tests/evaluation/test_run_resolution.py
tests/evaluation/test_run_schedule.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/run_schedule.py \
  src/pchsi/evaluation/run_resolution.py \
  tests/evaluation/test_run_schedule.py \
  tests/evaluation/test_run_resolution.py

git diff --cached --check
git commit -m "Implement E1 run schedule and resolution"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_run_schedule.py \
  tests/evaluation/test_run_resolution.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task07.commit"
```

**Forbidden:**
- Randomized schedule ordering, pooled-670 iid claims, automatic retry,
  retry after scientific result, cell-level retry after protocol invalidation,
  deleted failed attempts, or selecting a preferred success.

---

### Task 8: Public transition evidence and existing ActionTrace assembly

**Dependency:** Task 7 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/public_transition.py`
- Create: `src/pchsi/evaluation/trace_assembler.py`
- Create: `tests/evaluation/test_public_transition.py`
- Create: `tests/evaluation/test_trace_assembler.py`

**Interfaces:**
- Consumes `PublicTransitionRecordV1`, existing `ActionTrace`,
  `TraceProvenance`, Runtime Core decisions, `MenuSnapshot`,
  `StepPublicState`, and policy evidence.
- Produces:
  ```python
  def build_public_transition(
      *,
      scheduled_cell_id: str,
      execution_attempt_id: str,
      model_call_index: int,
      environment_step_index: int,
      submitted_action: str,
      pre_observation: str,
      pre_menu: MenuSnapshot,
      result: StepPublicState,
  ) -> PublicTransitionRecordV1: ...

  @dataclass(frozen=True, slots=True)
  class TraceAssemblyInput:
      ...

  def assemble_action_trace(
      value: TraceAssemblyInput,
  ) -> ActionTrace: ...
  ```
- `TraceAssemblyInput` carries exact prompt/response hashes, Runtime Core
  before/after state, provider evidence, task/split/model/seed provenance,
  pre-action state, and optional accepted result.
- This task must not modify `action_trace.py`.

**RED tests:**
- `test_public_transition_contains_only_pre_and_post_public_fields`
- `test_public_transition_hashes_match_exact_sequences_and_text`
- `test_transition_visibility_labels_are_frozen`
- `test_environment_exception_produces_no_public_transition`
- `test_trace_assembler_builds_nonexecuted_executed_and_environment_error_traces`
- `test_trace_assembler_preserves_duplicate_menu_and_exact_action`
- `test_trace_assembler_does_not_change_action_trace_semantics`
- `test_raw_infos_expert_plan_and_facts_cannot_enter_artifact`

- [ ] **Step 1: Write RED tests and stubs**

Stubs raise `NotImplementedError("TASK8_RED")`. Tests build existing Runtime
Core results and synthetic public step states; they never store a raw infos
mapping.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_public_transition.py \
  tests/evaluation/test_trace_assembler.py
```

Expected: focused failures through `TASK8_RED`, no skip or import failure.

- [ ] **Step 3: Implement transition and trace assembly**

Public transition visibility constants are exact:

```text
pre_action_visibility=POLICY_VISIBLE_BEFORE_ACTION
resulting_visibility=POST_ACTION_PUBLIC_AUDIT_ONLY
```

`build_public_transition` accepts only a fully validated `StepPublicState`.

`assemble_action_trace` must call `ActionTrace.build` and map frozen Runtime
Core fields without modifying or duplicating parser, admissibility, budget, or
termination logic.

Environment-call infrastructure errors produce an
`ExecutionStatus.ENVIRONMENT_ERROR` trace with reserved
`environment_step_index` and no resulting public state.

- [ ] **Step 4: Run focused GREEN**

Same focused command; expected exit `0`.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/public_transition.py \
  src/pchsi/evaluation/trace_assembler.py \
  tests/evaluation/test_public_transition.py \
  tests/evaluation/test_trace_assembler.py
```

**Static audit:**

```bash
git diff --quiet "$PLAN_MERGE_COMMIT" -- \
  src/pchsi/evaluation/action_trace.py

grep -RInE \
  'expert_plan|policy_commands|facts|raw_infos|infos=' \
  src/pchsi/evaluation/public_transition.py \
  src/pchsi/evaluation/trace_assembler.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
src/pchsi/evaluation/public_transition.py
src/pchsi/evaluation/trace_assembler.py
tests/evaluation/test_public_transition.py
tests/evaluation/test_trace_assembler.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/public_transition.py \
  src/pchsi/evaluation/trace_assembler.py \
  tests/evaluation/test_public_transition.py \
  tests/evaluation/test_trace_assembler.py

git diff --cached --check
git commit -m "Implement public transitions and trace assembly"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_public_transition.py \
  tests/evaluation/test_trace_assembler.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task08.commit"
```

**Forbidden:**
- Editing `ActionTrace`, storing raw infos or hidden fields, deriving success
  from score/text, fabricating a transition on environment error, action
  repair, or recomputing Runtime Core decisions.

---

### Task 9: Episode-level trace sequence validator

**Dependency:** Task 8 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/episode_sequence.py`
- Create: `tests/evaluation/test_episode_sequence.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class EpisodeSequenceInput:
      traces: tuple[ActionTrace, ...]
      public_transitions: tuple[PublicTransitionRecordV1, ...]
      final_budget: BudgetState
      final_success: bool | None
      final_done: bool | None
      final_won: bool | None
      termination_reason: str

  @dataclass(frozen=True, slots=True)
  class EpisodeSequenceReport:
      model_call_count: int
      environment_call_trace_count: int
      public_transition_count: int
      final_environment_step_count: int
      valid: bool

  def validate_episode_sequence(
      value: EpisodeSequenceInput,
  ) -> EpisodeSequenceReport: ...
  ```

**Required invariants:**

```text
model_call_index = 0..N-1
environment_step_index contiguous across actual env calls
trace budget_after equals next budget_before
task/seed/model/config provenance constant
nonexecuted attempt preserves observation/menu/M0
accepted result observation/menu equals next pre-action state
feedback propagates after failure and clears after execution
M0 recomputes from accepted executed transitions
final budget equals last trace budget_after
each accepted ACTION_EXECUTED trace has one transition
each transition maps to one accepted ACTION_EXECUTED trace
INFRASTRUCTURE_ERROR trace has no transition
final environment step count equals actual environment-call trace count
termination and success agree with final done/won
```

**RED tests:**
- `test_valid_multi_attempt_sequence_passes`
- `test_missing_reordered_or_duplicate_trace_fails`
- `test_budget_observation_menu_feedback_and_m0_discontinuity_fail`
- `test_environment_step_indices_cover_executed_and_error_calls`
- `test_public_transition_count_excludes_infrastructure_error`
- `test_infrastructure_trace_with_transition_fails`
- `test_final_budget_and_termination_must_match`
- `test_success_requires_done_true_won_true`

- [ ] **Step 1: Write RED tests and stub**

Stub raises `NotImplementedError("TASK9_RED")`. Reuse existing fake Runtime
Core traces where possible; add explicit environment-error and terminal-menu
fixtures.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_sequence.py
```

Expected: named tests fail through `TASK9_RED`, not through malformed fixtures.

- [ ] **Step 3: Implement deterministic sequence validation**

Validation reports all invariant failures in deterministic check order but
raises one typed `EpisodeSequenceError` containing the first failure code.

No input sequence is sorted or repaired. The validator rejects rather than
normalizes.

- [ ] **Step 4: Run focused GREEN**

Same command; expected exit `0`.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/episode_sequence.py \
  tests/evaluation/test_episode_sequence.py
```

**Static audit:**

```bash
grep -RInE \
  'sorted\(|set\(|repair|dedup|casefold\(|lower\(' \
  src/pchsi/evaluation/episode_sequence.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
src/pchsi/evaluation/episode_sequence.py
tests/evaluation/test_episode_sequence.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/episode_sequence.py \
  tests/evaluation/test_episode_sequence.py

git diff --cached --check
git commit -m "Implement episode trace sequence validation"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_sequence.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task09.commit"
```

**Forbidden:**
- Reordering traces, filling missing transitions, ignoring infrastructure
  calls, accepting counter gaps, mutating inputs, or treating 670 episodes as
  independent statistical units.

---

### Task 10: Scientific state and crash-consistent artifact publication

**Dependency:** Task 9 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/attempt_state.py`
- Create: `src/pchsi/evaluation/episode_artifact.py`
- Create: `src/pchsi/evaluation/artifact_publisher.py`
- Create: `src/pchsi/evaluation/cell_lock.py`
- Create: `tests/evaluation/test_attempt_state.py`
- Create: `tests/evaluation/test_episode_artifact.py`
- Create: `tests/evaluation/test_artifact_publisher.py`
- Create: `tests/evaluation/test_cell_lock.py`
- Create: `tests/evaluation/test_artifact_crash_recovery.py`

**Interfaces:**
- Produces enums:
  ```python
  class ScientificOutcomeStatus(str, Enum):
      NOT_PRODUCED = "SCIENTIFIC_OUTCOME_NOT_PRODUCED"
      SUCCESS = "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS"
      TASK_FAILURE = "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"

  class OperationalFinalizationStatus(str, Enum):
      STAGING = "STAGING"
      PUBLISHED = "PUBLISHED"
      PUBLICATION_PENDING = "PUBLICATION_PENDING"
      CLOSE_FAILED_RECORDED = "CLOSE_FAILED_RECORDED"
      ARTIFACT_IO_FAILED = "ARTIFACT_IO_FAILED"
  ```
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class AttemptBundleBytes:
      attempt_json: bytes
      action_traces_jsonl: bytes
      public_transitions_jsonl: bytes
      checksums_text: bytes
      episode_semantic_sha256: str
      attempt_bundle_sha256: str

  def build_attempt_bundle_bytes(...) -> AttemptBundleBytes: ...

  class ArtifactPublisher:
      def write_started_receipt(...): ...
      def stage_bundle(...): ...
      def write_scientific_cell_lock(...): ...
      def publish_staged_directory(...): ...
      def write_terminal_receipt(...): ...
      def recover_publication(...): ...
  ```
- File layout is exactly the approved design.
- `PublicationFaultPoint` enum provides deterministic injected crash points.

**Frozen publication order:**

```text
1. write started receipt
2. finish scientific trajectory
3. construct complete staging bundle
4. validate episode trace sequence
5. compute episode_semantic_sha256
6. compute each file SHA-256
7. compute attempt_bundle_sha256
8. fsync every staging file and staging directory
9. write no-clobber scientific cell lock
10. no-clobber rename complete attempt directory
11. fsync attempts parent
12. write terminal receipt
13. fsync attempt-ledger parent
```

If step 9 succeeds and step 10 fails, the cell lock and identical staging
bytes remain; recovery may retry only the same publication bytes.

**Semantic projection excludes:**

```text
timestamps
latency
hostname
provider request ID
temporary paths
local exception messages
attempt ordinal
```

**RED tests:**
- `test_scientific_and_operational_states_are_independent`
- `test_bundle_bytes_are_deterministic_and_jsonl_ordered`
- `test_semantic_hash_ignores_operational_metadata`
- `test_exact_bundle_hash_changes_with_exact_artifact_bytes`
- `test_publication_is_directory_level_atomic_and_no_clobber`
- `test_cell_lock_and_bundle_match_bidirectionally`
- `test_publication_retry_uses_identical_staging_bytes`
- `test_lost_staging_remains_unresolved_and_never_authorizes_model_retry`
- `test_every_started_attempt_gets_one_terminal_receipt`
- `test_crash_after_each_frozen_boundary_has_defined_recovery`

Fault points:

```text
AFTER_STARTED_RECEIPT
AFTER_PARTIAL_STAGING
AFTER_COMPLETE_STAGING_BEFORE_FSYNC
AFTER_CELL_LOCK
AFTER_DIRECTORY_RENAME_BEFORE_PARENT_FSYNC
AFTER_PARENT_FSYNC_BEFORE_TERMINAL_RECEIPT
```

- [ ] **Step 1: Write RED tests and stubs**

Stubs expose final interfaces and raise `NotImplementedError("TASK10_RED")`.
Tests use only temporary directories and monkeypatched fsync/rename fault
injectors.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_attempt_state.py \
  tests/evaluation/test_episode_artifact.py \
  tests/evaluation/test_artifact_publisher.py \
  tests/evaluation/test_cell_lock.py \
  tests/evaluation/test_artifact_crash_recovery.py
```

Expected: focused failures through `TASK10_RED`, no flaky timing dependency.

- [ ] **Step 3: Implement deterministic bytes and crash recovery**

`action_traces.jsonl` is ordered by model call index and contains
`ActionTrace.to_json() + "\n"` per line.
`public_transitions.jsonl` is ordered by environment step index.
`SHA256SUMS` uses fixed file order and excludes itself.

The exact bundle hash is the SHA-256 of canonical ordered `(filename, file
sha256)` records including the checksum file hash; the bundle hash is written
only to cell lock and terminal receipt, not into a self-hashed bundle file.

All file creation is no-clobber with owner-only modes. Use explicit file and
directory `fsync`.

- [ ] **Step 4: Run focused GREEN**

Same focused command; expected exit `0`.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/attempt_state.py \
  src/pchsi/evaluation/episode_artifact.py \
  src/pchsi/evaluation/artifact_publisher.py \
  src/pchsi/evaluation/cell_lock.py \
  tests/evaluation/test_attempt_state.py \
  tests/evaluation/test_episode_artifact.py \
  tests/evaluation/test_artifact_publisher.py \
  tests/evaluation/test_cell_lock.py \
  tests/evaluation/test_artifact_crash_recovery.py
```

**Static audit:**

```bash
grep -RInE \
  'shutil\.move|os\.replace\(.*attempt\.json|open\(.*["'\'']a|exist_ok=True|unlink\(.*cell_lock' \
  src/pchsi/evaluation/artifact_publisher.py \
  src/pchsi/evaluation/cell_lock.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
src/pchsi/evaluation/artifact_publisher.py
src/pchsi/evaluation/attempt_state.py
src/pchsi/evaluation/cell_lock.py
src/pchsi/evaluation/episode_artifact.py
tests/evaluation/test_artifact_crash_recovery.py
tests/evaluation/test_artifact_publisher.py
tests/evaluation/test_attempt_state.py
tests/evaluation/test_cell_lock.py
tests/evaluation/test_episode_artifact.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/attempt_state.py \
  src/pchsi/evaluation/episode_artifact.py \
  src/pchsi/evaluation/artifact_publisher.py \
  src/pchsi/evaluation/cell_lock.py \
  tests/evaluation/test_attempt_state.py \
  tests/evaluation/test_episode_artifact.py \
  tests/evaluation/test_artifact_publisher.py \
  tests/evaluation/test_cell_lock.py \
  tests/evaluation/test_artifact_crash_recovery.py

git diff --cached --check
git commit -m "Implement crash-consistent evaluator artifacts"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_attempt_state.py \
  tests/evaluation/test_episode_artifact.py \
  tests/evaluation/test_artifact_publisher.py \
  tests/evaluation/test_cell_lock.py \
  tests/evaluation/test_artifact_crash_recovery.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task10.commit"
```

**Forbidden:**
- Per-file final publication, append-only shared result truth, overwrite,
  deletion of failed attempt evidence, model rerun after scientific outcome,
  best-of-run replacement, lost-staging replacement, missing terminal
  receipts, self-referential bundle hashes, or un-fsynced final publication.

---

### Task 11: Single-episode evaluator orchestration

**Dependency:** Task 10 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/episode_evaluator.py`
- Create: `tests/evaluation/test_episode_evaluator.py`

**Interfaces:**
- Consumes every earlier task plus the frozen Runtime Core functions:
  `validate_runtime_preconditions`, `build_raw_policy_prompt`,
  `process_completed_generation`, and `finalize_environment_result`.
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class EpisodeExecutionConfig:
      run_id: str
      cell: ScheduledCell
      execution_attempt_id: str
      attempt_ordinal: int
      task: FrozenTaskRecord
      seed: int
      evaluator_commit: str
      design_merge_commit: str
      runtime_core_commit: str
      raw_protocol_sha256: str
      split_access_sha256: str
      gamefile_identity_manifest_sha256: str
      environment_runtime_manifest_sha256: str
      policy_runtime_manifest_sha256: str
      policy_request_schema_sha256: str

  @dataclass(frozen=True, slots=True)
  class EpisodeDependencies:
      environment: SpawnedAlfworldAdapter
      policy_client: PolicyClient
      prompt_renderer: PromptRenderer
      artifact_publisher: ArtifactPublisher

  @dataclass(frozen=True, slots=True)
  class EpisodeAttemptResult:
      traces: tuple[ActionTrace, ...]
      transitions: tuple[PublicTransitionRecordV1, ...]
      final_budget: BudgetState
      scientific_outcome_status: ScientificOutcomeStatus
      operational_finalization_status: OperationalFinalizationStatus
      termination_reason: str
      success: bool | None
      attempt_bundle: AttemptBundleBytes | None

  def run_single_episode(
      *,
      config: EpisodeExecutionConfig,
      dependencies: EpisodeDependencies,
  ) -> EpisodeAttemptResult: ...
  ```

**Frozen orchestration order:**

```text
validate config and frozen identities
write started receipt
spawn exact-game adapter
reset
validate reset and latch gamefile
parse public goal
initialize budget/history/feedback/state
loop:
  use one immutable current menu snapshot
  validate Runtime Core preconditions
  build frozen prompt
  render expected prompt tokens
  make one policy request
  validate response
  process completed generation
  if no env call:
      assemble trace
      update feedback only
      resolve termination
  if env call:
      invoke env.step exactly once
      validate complete result before finalization
      finalize Runtime Core
      assemble trace
      build transition only for accepted result
      update history/state/menu only for accepted result
      resolve termination
establish immutable scientific outcome
validate episode sequence
build immutable attempt bundle
publish or preserve publication-pending state
close/reap worker and record operational status
```

**RED tests:**
- `test_first_action_success`
- `test_format_failure_then_off_list_then_success`
- `test_three_consecutive_nonexecuted_attempts_terminate`
- `test_policy_attempt_sixty_terminates_without_sixty_first_call`
- `test_environment_step_thirty_executes_then_budget_terminates`
- `test_invalid_menu_stops_before_policy_and_budget_change`
- `test_policy_transport_failure_consumes_no_policy_attempt`
- `test_env_step_exception_keeps_reserved_step_and_no_transition`
- `test_malformed_step_is_infrastructure_error_before_finalization`
- `test_failed_generations_do_not_enter_m0`
- `test_only_accepted_transitions_enter_m0`
- `test_step_result_is_validated_before_finalize_environment_result`
- `test_scientific_outcome_does_not_rerun_after_publication_failure`
- `test_environment_close_failure_is_operational_not_new_trajectory`

- [ ] **Step 1: Write RED tests and orchestration stub**

Tests inject fake environment, fake policy, fake renderer, and temporary
publisher. Use spies around the existing Runtime Core functions to assert
call order without mocking away their real logic.

The stub raises `NotImplementedError("TASK11_RED")`.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_evaluator.py
```

Expected: named scenario tests fail through `TASK11_RED`; existing Runtime Core
tests remain collected and unchanged.

- [ ] **Step 3: Implement orchestration only**

The evaluator must not parse actions, inspect exact membership, update
budgets, or invent termination logic. It passes frozen values into existing
Runtime Core APIs.

Policy transport failure occurs before a completed generation and therefore
does not call `process_completed_generation`.

For a reserved environment call, any exception or malformed result calls
`finalize_environment_result` with infrastructure error and keeps the
reserved environment step.

Only a fully accepted result creates a public transition and an
`ExecutedTransition` for M0.

- [ ] **Step 4: Run focused GREEN**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_evaluator.py \
  tests/evaluation/test_runtime_core_fake_environment.py
```

Expected: exit `0`; all selected evaluator and existing Runtime Core fake
environment tests pass.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/episode_evaluator.py \
  tests/evaluation/test_episode_evaluator.py
```

**Static audit:**

```bash
grep -RInE \
  'json\.loads\(.*raw_model|action in .*commands|apply_completed_attempt|resolve_after_environment|sorted\(|set\(|casefold\(|lower\(|difflib|fuzzy' \
  src/pchsi/evaluation/episode_evaluator.py \
  && exit 1 || true

git diff --quiet "$PLAN_MERGE_COMMIT" -- \
  src/pchsi/evaluation/runtime_core.py \
  src/pchsi/evaluation/raw_policy_parser.py \
  src/pchsi/evaluation/raw_policy_prompt.py \
  src/pchsi/evaluation/budget.py \
  src/pchsi/evaluation/action_trace.py
```

**Expected changed paths:**

```text
src/pchsi/evaluation/episode_evaluator.py
tests/evaluation/test_episode_evaluator.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/episode_evaluator.py \
  tests/evaluation/test_episode_evaluator.py

git diff --cached --check
git commit -m "Implement single-episode E1 evaluator"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_evaluator.py \
  tests/evaluation/test_runtime_core_fake_environment.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task11.commit"
```

**Forbidden:**
- Copying Runtime Core logic, hidden retry, real environment/model, policy
  calls after scientific lock, transition fabrication, M0 updates after
  failed actions, finalization before result validation, or swallowing
  protocol/infrastructure errors.

---

### Task 12: Run resolver and formal result-audit gate

**Dependency:** Task 11 commit exists and worktree is clean.

**Files:**
- Create: `src/pchsi/evaluation/result_audit.py`
- Create: `tests/evaluation/test_result_audit.py`

**Interfaces:**
- Consumes run schedule, attempt receipts, cell locks, and published attempt
  bundles.
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class ResultAuditReport:
      scheduled_cells: int
      scientifically_resolved_cells: int
      scientific_cell_locks: int
      published_scientific_attempt_bundles: int
      cell_locks_without_matching_published_bundle: int
      published_bundles_without_matching_cell_lock: int
      publication_pending: int
      artifact_io_failed_unresolved: int
      missing_terminal_receipts: int
      checksum_failures: int
      duplicate_cell_resolutions: int
      missing_task_seed_cells: int
      unresolved_protocol_errors: int
      unresolved_pre_result_infrastructure_cells: int
      best_of_run_selection: int
      approved: bool

  def audit_e1_run(
      *,
      run_root: Path,
      expected_schedule: RunScheduleV1,
  ) -> ResultAuditReport: ...
  ```
- Approval is true only when every approved-design count equals its exact
  required value.

**RED tests:**
- `test_complete_670_cell_run_is_approved`
- `test_each_single_missing_or_orphan_condition_rejects`
- `test_lock_and_bundle_semantic_and_exact_hashes_must_match`
- `test_missing_started_or_terminal_receipt_rejects`
- `test_publication_pending_and_unresolved_artifact_failure_reject`
- `test_duplicate_resolution_and_best_of_run_reject`
- `test_unresolved_protocol_or_infrastructure_cell_rejects`
- `test_close_failed_recorded_is_allowed_only_with_published_bundle_and_reaped_worker`
- `test_total_attempts_may_exceed_670_without_changing_scientific_cells`
- `test_pooled_670_iid_headline_is_forbidden`

- [ ] **Step 1: Write RED tests and stub**

Build compact temporary run fixtures programmatically. One passing fixture has
670 cells but uses small canonical files generated in a loop; no model or
environment executes.

Stub raises `NotImplementedError("TASK12_RED")`.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_result_audit.py
```

Expected: named tests fail through `TASK12_RED`.

- [ ] **Step 3: Implement exact gate**

The report requires:

```text
scheduled_cells = 670
scientifically_resolved_cells = 670
scientific_cell_locks = 670
published_scientific_attempt_bundles = 670
all listed error/pending/orphan/duplicate/missing counts = 0
```

Every lock/bundle pair must match scheduled cell, attempt ID, semantic hash,
and exact bundle hash. The audit validates checksums and receipts rather than
trusting counts from `attempt.json`.

`CLOSE_FAILED_RECORDED` is acceptable only with complete published evidence,
successful worker reap evidence, no contamination flag, and no later model
attempt.

- [ ] **Step 4: Run focused GREEN**

Same command; expected exit `0`.

**Focused verification:**

```bash
python -m compileall -q \
  src/pchsi/evaluation/result_audit.py \
  tests/evaluation/test_result_audit.py
```

**Static audit:**

```bash
grep -RInE \
  'best.*min|max\(.*success|drop.*error|ignore.*missing|670.*independent' \
  src/pchsi/evaluation/result_audit.py \
  && exit 1 || true
```

**Expected changed paths:**

```text
src/pchsi/evaluation/result_audit.py
tests/evaluation/test_result_audit.py
```

**Commit:**

```bash
git add -- \
  src/pchsi/evaluation/result_audit.py \
  tests/evaluation/test_result_audit.py

git diff --cached --check
git commit -m "Implement E1 result audit"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_result_audit.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task12.commit"
```

**Forbidden:**
- Count-only approval without hash/receipt checks, best-of-run, dropping
  infrastructure attempts, accepting orphan locks/bundles, approving missing
  artifacts, or treating five seeds as five independent tasks.

---

### Task 13: Closed candidate CLI and non-bypassable execution gate

**Dependency:** Task 12 commit exists and worktree is clean.

**Files:**
- Create: `scripts/evaluation/run_e1_evaluator.py`
- Create: `tests/evaluation/test_evaluator_execution_gate.py`
- Create: `tests/evaluation/test_evaluator_no_real_execution.py`

**Interfaces:**
- CLI modes:
  ```text
  --describe
  --validate-config <path>
  --execute
  ```
- Candidate behavior:
  ```text
  --describe: exit 0, deterministic non-executing JSON
  --validate-config: exit 0 or 2 after pure file/schema validation
  --execute: always exit 77 with E1_EVALUATOR_EXECUTION_NOT_APPROVED
  ```
- `--validate-config` may read repository configuration and readiness-artifact
  placeholders but may not import runtime libraries, connect, spawn, or write
  run artifacts.

**RED tests:**
- `test_describe_is_deterministic_and_nonexecuting`
- `test_validate_config_is_pure_and_rejects_missing_readiness_artifacts`
- `test_execute_always_returns_77`
- `test_no_force_unsafe_debug_or_environment_bypass_exists`
- `test_repository_approval_string_cannot_self_authorize`
- `test_module_import_describe_and_validate_do_not_import_runtime_packages`
- `test_module_import_describe_and_validate_do_not_open_socket_or_initialize_cuda`
- `test_cli_has_no_hidden_execute_true_configuration_path`

- [ ] **Step 1: Write RED tests and CLI stub**

Stub parser exposes only the three exact modes. `--execute` may initially
raise `NotImplementedError("TASK13_RED")` so the closure test fails validly.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_evaluator_execution_gate.py \
  tests/evaluation/test_evaluator_no_real_execution.py
```

Expected: named tests fail through `TASK13_RED`, not from importing ALFWorld or
network libraries.

- [ ] **Step 3: Implement closed candidate CLI**

`--execute` is unconditional rejection in this candidate. Do not implement a
future authorization parser in this task.

All runtime imports are inside the future gated execution function, which is
not reachable in the candidate.

No `--force`, `--unsafe`, `--debug-execute`, environment variable, config
field, or repository approval string bypass exists.

- [ ] **Step 4: Run focused GREEN**

Same command; expected exit `0`.

**Focused verification:**

```bash
python -m compileall -q \
  scripts/evaluation/run_e1_evaluator.py \
  tests/evaluation/test_evaluator_execution_gate.py \
  tests/evaluation/test_evaluator_no_real_execution.py

python scripts/evaluation/run_e1_evaluator.py --describe

set +e
python scripts/evaluation/run_e1_evaluator.py --execute
EXECUTE_RC=$?
set -e
test "$EXECUTE_RC" -eq 77
```

**Static audit:**

```bash
grep -RInE \
  -- '--force|--unsafe|debug.*execute|E1_.*APPROVED.*os\.environ|execute.*=.*true' \
  scripts/evaluation/run_e1_evaluator.py \
  && exit 1 || true

python - <<'PY'
import sys
import runpy
runpy.run_path(
    "scripts/evaluation/run_e1_evaluator.py",
    run_name="e1_evaluator_import_audit",
)
for forbidden in ("alfworld", "textworld", "gym", "vllm", "torch"):
    assert forbidden not in sys.modules
print("TASK13_IMPORT_AUDIT_OK")
PY
```

**Expected changed paths:**

```text
scripts/evaluation/run_e1_evaluator.py
tests/evaluation/test_evaluator_execution_gate.py
tests/evaluation/test_evaluator_no_real_execution.py
```

**Commit:**

```bash
git add -- \
  scripts/evaluation/run_e1_evaluator.py \
  tests/evaluation/test_evaluator_execution_gate.py \
  tests/evaluation/test_evaluator_no_real_execution.py

git diff --cached --check
git commit -m "Add evaluator candidate execution gate"
```

**Post-commit verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_evaluator_execution_gate.py \
  tests/evaluation/test_evaluator_no_real_execution.py

test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task13.commit"
```

**Forbidden:**
- Any execution bypass, real runtime import during safe modes, network,
  process spawn, GPU initialization, environment registration, run artifact
  creation, or authorization based solely on a repository/config string.

---

### Task 14: Cumulative candidate audit and design requirement matrix

**Dependency:** Task 13 commit exists and worktree is clean.

**Files:**
- Create: `scripts/evaluation/audit_e1_evaluator_candidate.py`
- Create: `tests/evaluation/test_evaluator_candidate_audit.py`
- Create: `docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md`

**Interfaces:**
- Produces a pure repository audit CLI:
  ```python
  class CandidateAuditPhase(str, Enum):
      PRECOMMIT_TASK14 = "PRECOMMIT_TASK14"
      POSTCOMMIT_TASK14 = "POSTCOMMIT_TASK14"

  def audit_candidate(
      *,
      repository_root: Path,
      implementation_base: str,
      expected_design_blob: str,
      expected_design_merge_commit: str,
      phase: CandidateAuditPhase,
  ) -> CandidateAuditReport: ...
  ```
- `CandidateAuditReport` includes audit phase, exact changed or staged paths,
  task commit subjects, frozen-path identities, no-real-execution scan,
  schema inventory, requirement-matrix completeness, full test command,
  candidate tree hash, and the resolved Task 14 head SHA in post-commit mode.
- `PRECOMMIT_TASK14` expects thirteen completed task commits plus the exact
  staged Task 14 paths.
- `POSTCOMMIT_TASK14` expects fourteen completed task commits, a clean
  worktree, and Task 14 as `HEAD`.

**Requirement matrix columns:**

```text
requirement_id
design_section
source_path
symbol
test_path
test_name
verification_command
task_number
task_commit_sha
```

The matrix maps evaluator design implementation requirements to Tasks 1–13.
Every `task_commit_sha` is an already existing, exact forty-character SHA
from Tasks 1–13. Task 14 is the audit mechanism itself and must not attempt to
embed its own Git SHA in bytes that determine that SHA. The post-commit audit
report resolves and records the Task 14 SHA from `HEAD`.

No row may use a generic `covered=true`, a symbolic `HEAD`, or a pending SHA.

**RED tests:**
- `test_candidate_audit_binds_design_blob_and_merge_commit`
- `test_precommit_audit_requires_thirteen_prior_commits_and_exact_task14_staged_paths`
- `test_postcommit_audit_requires_fourteen_ordered_task_commits`
- `test_postcommit_report_records_task14_head_sha`
- `test_candidate_audit_rejects_changed_frozen_runtime_or_manifest_paths`
- `test_candidate_audit_rejects_real_execution_in_tests`
- `test_candidate_audit_requires_every_design_requirement_mapping`
- `test_requirement_matrix_uses_only_resolved_task1_to_task13_shas`
- `test_requirement_matrix_references_existing_symbols_and_tests`
- `test_candidate_audit_reports_exact_changed_paths_and_tree_hash`
- `test_candidate_audit_rejects_skips_xfails_and_relaxed_assertions_in_security_critical_tests`

- [ ] **Step 1: Write RED tests, audit stub, and full requirement-matrix rows**

The matrix must map every design section 1–24 and each narrow correction to
specific source/test symbols implemented in Tasks 1–13. Populate each matrix
row with the exact corresponding Task 1–13 commit SHA recorded under
`$HOME/.cache/pchsi/e1-evaluator-implementation/`.

At RED, the audit stub raises `NotImplementedError("TASK14_RED")`.

- [ ] **Step 2: Run focused RED**

```bash
python -m pytest -q \
  tests/evaluation/test_evaluator_candidate_audit.py
```

Expected: named tests fail through `TASK14_RED`.

- [ ] **Step 3: Implement two-phase cumulative audit**

Bind exactly:

```text
design blob SHA =
ad0eea1638716917d36391b098e9770b8a0c06fe

design merge commit =
5cddface67c220c8c799d1b0699cf611d7ffc78a
```

Verify the following paths are byte-identical to `PLAN_MERGE_COMMIT`:

```text
src/pchsi/evaluation/runtime_core.py
src/pchsi/evaluation/raw_policy_parser.py
src/pchsi/evaluation/raw_policy_prompt.py
src/pchsi/evaluation/budget.py
src/pchsi/evaluation/action_trace.py
data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl
configs/protocols/split_and_access_v1.json
```

Frozen ordered subjects:

```text
01 Implement canonical evaluator evidence contracts
02 Implement frozen E1 task and gamefile identity
03 Implement evaluator environment runtime identity
04 Implement strict ALFWorld data contracts
05 Implement spawned ALFWorld worker adapter
06 Implement frozen E1 policy transport
07 Implement E1 run schedule and resolution
08 Implement public transitions and trace assembly
09 Implement episode trace sequence validation
10 Implement crash-consistent evaluator artifacts
11 Implement single-episode E1 evaluator
12 Implement E1 result audit
13 Add evaluator candidate execution gate
14 Add cumulative E1 evaluator candidate audit
```

`PRECOMMIT_TASK14` must verify:

```text
exactly 13 commits after PLAN_MERGE_COMMIT
subjects 01–13 match exactly
HEAD is Task 13
staged paths are exactly the three Task 14 paths
no unstaged or untracked path exists
requirement matrix contains only resolved Task 1–13 SHAs
```

`POSTCOMMIT_TASK14` must verify:

```text
exactly 14 commits after PLAN_MERGE_COMMIT
subjects 01–14 match exactly
HEAD subject is Task 14
worktree and index are clean
Task 14 head SHA is emitted in CandidateAuditReport
```

Both phases scan tests for skip/xfail markers and production/tests for real
network, GPU, or formal environment execution surfaces outside the lazily
gated worker implementation.

- [ ] **Step 4: Run focused GREEN**

```bash
python -m pytest -q \
  tests/evaluation/test_evaluator_candidate_audit.py
```

Expected: exit `0`. Unit fixtures exercise both pre-commit and post-commit
repository states.

**Focused verification:**

```bash
python -m pytest -q \
  tests/evaluation/test_evaluator_candidate_audit.py
```

**Static audit:**

```bash
python -m pytest -q

python -m compileall -q \
  src \
  tests \
  scripts

grep -RInE \
  'pytest\.mark\.skip|pytest\.mark\.xfail|unittest\.skip|import vllm|import torch|torch\.cuda|requests\.post|httpx\.post' \
  tests/evaluation \
  && exit 1 || true

grep -RInE \
  'alfworld_valid_unseen_all134_v1\.jsonl.*open|\.cache/alfworld|env\.step\(' \
  tests/evaluation \
  && exit 1 || true
```

`env.step(` may appear only inside named fake classes; the audit script must
parse AST/symbol context rather than relying solely on grep for its final
decision.

**Expected changed paths:**

```text
docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md
scripts/evaluation/audit_e1_evaluator_candidate.py
tests/evaluation/test_evaluator_candidate_audit.py
```

**Commit:**

```bash
git add -- \
  docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md \
  scripts/evaluation/audit_e1_evaluator_candidate.py \
  tests/evaluation/test_evaluator_candidate_audit.py

test "$(
  git diff --cached --name-only |
  LC_ALL=C sort
)" = "$(
cat <<'EOF_PATHS'
docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md
scripts/evaluation/audit_e1_evaluator_candidate.py
tests/evaluation/test_evaluator_candidate_audit.py
EOF_PATHS
)"

git diff --cached --check

python scripts/evaluation/audit_e1_evaluator_candidate.py \
  --repository-root . \
  --implementation-base "$PLAN_MERGE_COMMIT" \
  --expected-design-blob \
    ad0eea1638716917d36391b098e9770b8a0c06fe \
  --expected-design-merge-commit \
    5cddface67c220c8c799d1b0699cf611d7ffc78a \
  --phase PRECOMMIT_TASK14

git commit -m "Add cumulative E1 evaluator candidate audit"
```

**Post-commit verification:**

```bash
python -m pytest -q
python -m compileall -q src tests scripts

python scripts/evaluation/audit_e1_evaluator_candidate.py \
  --repository-root . \
  --implementation-base "$PLAN_MERGE_COMMIT" \
  --expected-design-blob \
    ad0eea1638716917d36391b098e9770b8a0c06fe \
  --expected-design-merge-commit \
    5cddface67c220c8c799d1b0699cf611d7ffc78a \
  --phase POSTCOMMIT_TASK14

test "$(git rev-list --count "$PLAN_MERGE_COMMIT..HEAD")" = "14"
test -z "$(git status --porcelain=v1 --untracked-files=all)"

git rev-parse HEAD \
  > "$HOME/.cache/pchsi/e1-evaluator-implementation/task14.commit"
```

**Forbidden:**
- Requiring fourteen commits before Task 14 is committed, embedding Task 14's
  own SHA in its committed file bytes, symbolic or pending matrix SHAs,
  generic coverage claims, changed frozen semantics, skipped critical tests,
  real smoke execution, target-host readiness generation, automatic approval,
  force-push, or claiming code approval from test success alone.
---

## Readiness artifacts are a later, separately authorized stage

The fourteen implementation tasks produce only candidate code and fixture
evidence. They do not produce authoritative host-bound readiness artifacts.

After cumulative code review and:

```text
CODE_APPROVED_E1_ALFWORLD_EVALUATOR_V1
```

a separate readiness plan must be approved:

```text
READINESS_PREFLIGHT_PLAN_APPROVED_E1_ALFWORLD_EVALUATOR_V1
```

Only after:

```text
EXECUTION_APPROVED_E1_EVALUATOR_READINESS_PREFLIGHT
```

may the target server run the builders to generate:

```text
configs/evaluation/e1_gamefile_sha256_preflight_v1.json
configs/evaluation/alfworld_environment_runtime_manifest_v1.json
configs/evaluation/e1_policy_runtime_manifest_v1.json
```

That readiness run may read the formal 134 gamefiles, inspect installed
ALFWorld/TextWorld/Gym/Python sources, inspect frozen local tokenizer files,
and perform read-only vLLM readiness checks. It may not create an ALFWorld
environment, call the model for generation, execute a game action, or run E1.

Generated artifacts then require:

```text
artifact review
hash freeze
READINESS_ARTIFACTS_APPROVED_E1_ALFWORLD_EVALUATOR_V1
```

before environment-only smoke approval.

## Review gates after implementation

```text
Task 1–14 focused reviews
→ cumulative evaluator code review
→ CODE_APPROVED_E1_ALFWORLD_EVALUATOR_V1
→ readiness plan and execution approval
→ readiness artifact review and approval
→ environment-only smoke approval
→ exact-game/reset/menu/fixed-action smoke
→ environment smoke audit
→ model-integrated smoke approval
→ 1–3 task vLLM smoke
→ integrated smoke audit
→ E1_DEV_EXECUTION_APPROVED
→ formal 670-cell run
```

Implementation tests, code approval, and readiness approval never imply smoke
or E1 execution approval.

## Plan self-review checklist

Before freezing this plan, verify:

- [ ] Exactly fourteen `### Task` sections exist.
- [ ] Each Task has dependency, exact files, interfaces, named RED tests,
      RED command and expected failure, GREEN scope, focused verification,
      static audit, exact paths, commit subject, post-commit verification,
      and forbidden behavior.
- [ ] Task 1–14 commit subjects are unique and ordered.
- [ ] Builder implementation is separated from target-host builder execution.
- [ ] Worker protocol fixes spawn, IPC messages, timeouts, close,
      terminate/kill, join/reap, and lazy imports.
- [ ] Policy task includes exact bytes, no SDK, no redirect, no retry,
      local-only tokenizer, response token-ID contract, and runtime manifest.
- [ ] Schema and Python model parity is tested.
- [ ] Crash-consistent publication order and every fault boundary are explicit.
- [ ] Candidate CLI has no force/debug/environment/config bypass.
- [ ] Cumulative audit binds design blob, design merge, frozen Runtime Core,
      manifest, split/access, and requirement matrix.
- [ ] Task 14 has separate PRECOMMIT and POSTCOMMIT audit phases, so it does
      not require its own commit before that commit exists.
- [ ] Requirement-matrix rows use only exact resolved Task 1–13 SHAs; the
      Task 14 SHA is emitted by the post-commit audit report.
- [ ] No real environment, model, network, GPU, or readiness artifact
      generation is authorized by this plan-only PR.
- [ ] No unfinished implementation marker exists in the plan.

## Execution handoff

After the plan-only PR is merged, implementation begins with Task 1 in an
isolated worktree. Use subagent-driven development if available: one fresh
worker per Task, specification review before code-quality review, and a
human checkpoint after every focused commit.

The plan approval does not authorize environment or model execution. It
authorizes only the fourteen RED→GREEN candidate implementation tasks after
the plan file is merged.

## Primary implementation references

- Frozen evaluator design:
  `docs/superpowers/specs/2026-08-06-e1-alfworld-evaluator-v1-design.md`
- vLLM 0.11.0 OpenAI protocol:
  `https://docs.vllm.ai/en/v0.11.0/api/vllm/entrypoints/openai/protocol.html`
- vLLM 0.11.0 OpenAI-compatible server:
  `https://docs.vllm.ai/en/v0.11.0/serving/openai_compatible_server.html`
- Python multiprocessing and explicit spawn context:
  `https://docs.python.org/3/library/multiprocessing.html`
- TextWorld Gym batch, auto-reset, and step-limit contract:
  `https://textworld.readthedocs.io/en/stable/textworld.gym.html`
- ALFWorld repository:
  `https://github.com/alfworld/alfworld`
