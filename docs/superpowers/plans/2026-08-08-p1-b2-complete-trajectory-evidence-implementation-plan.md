# P1-B2 完整轨迹证据与防泄漏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 evaluator 从“足够证明 episode 运行正确”的证据层扩展为“足够支持强模型离线分析、Q2 exact-state replay、student 防未来泄漏”的完整轨迹证据层，并在正式 π0 DEV collection 前提供机器可验证的完整性 gate。

**Architecture:** 保留 Runtime Core 的决策语义不变，在 policy transport/trace/evidence bundle 外围新增 `PolicyCallEvidenceV1`、可见性分类、完整性验证和 condition-bound execution binding。当前源码已经在内存中拥有 raw response body、token IDs、usage、finish reason、latency 和 exact request bytes，但 `ActionTrace`/attempt bundle 目前没有完整发布这些字段，因此本计划优先扩展 evidence，而不是改模型行为。

**Tech Stack:** Python 3.12 standard library, existing evaluator contracts, canonical JSON/SHA-256, pytest.

## Global Constraints

- Parent design merge commit: `eef94f4b4f15b6d7be4420c346cbd7145605e677`.
- Parent spec: `docs/superpowers/specs/2026-08-08-p1-b-access-and-evidence-v1-design.md`.
- Runtime Core parsing/admissibility/budget/environment-step semantics are frozen and must not change.
- No hidden simulator state enters teacher or student views.
- Every model call, including parser/off-list failures, must have evidence.
- Every successful environment step has exactly one public transition.
- Student projection may contain only information available before that action.
- DEV teacher projection may use full completed public trajectory.
- SELECT teacher export must fail closed.
- API keys / Authorization headers / secrets must never enter artifacts.
- No real teacher call is implemented here.
- No formal P1 DEV collection is authorized by code completion.
- Exact schema inventory remains closed.
- Existing E1 integrated-smoke semantics must remain reproducible.
- Each task uses RED → GREEN → full regression → static audit → focused commit.

## Current Known Evidence Gaps from Fixed Source Review

Current `PolicyGeneration` already contains:

```text
raw_response_body
provider_request_id
client_request_id
finish_reason
prompt_tokens
completion_tokens
prompt_token_ids
token_ids
latency_ms
```

Current `E1PolicyRequestV1` can emit exact canonical request bytes.

Current `ActionTrace` publishes:

```text
prompt_text/hash
observation/hash
menu/hash
raw_model_response/hash
parser/runtime fields
budget counters
submitted action
resulting observation
```

But `trace_assembler.py` currently copies only `raw_response_text` and selected runtime fields from `PolicyGeneration`, and `episode_artifact.py` currently bundles only:

```text
attempt.json
action_traces.jsonl
public_transitions.jsonl
SHA256SUMS
```

Therefore the plan must not mark request bytes, raw response body, token IDs, finish reason or latency as `PRESENT_AND_VALIDATED` until they are explicitly published and tested.

## Frozen evidence identity layers

P1-B2 must keep three identities separate.

### Exact audit identity

The exact attempt bundle and file SHA-256 values include:

- exact request wire bytes;
- exact raw response body bytes;
- allowlisted response headers;
- client/provider request IDs;
- latency;
- timestamps and attempt identity where present.

This identity answers: “What exact bytes were observed in this attempt?”

### Scientific semantic identity

The scientific semantic hash must be reproducible across clean attempts with
the same scientific behavior. It includes:

- request semantics after removing operational request IDs;
- prompt/rendered prompt content and token IDs;
- generation parameters;
- assistant content;
- finish reason;
- prompt/completion token counts and token IDs;
- observations, menus, decisions, budgets and public transitions.

It excludes only explicitly operational nondeterminism:

- client request ID;
- provider response/request ID;
- HTTP Date and other operational headers;
- latency;
- timestamps;
- attempt ordinal;
- raw response envelope fields whose only meaning is operational identity.

Exact request/response bytes remain in the audit bundle and exact bundle hash,
but they are not blindly inserted into the scientific semantic hash.

### Operational provenance identity

Operational receipts continue to bind run/attempt/publication/worker
information. They are not training labels and do not enter student input.

## Planned File Map

Create:

```text
configs/evaluation/schemas/
├── policy_call_evidence_v1.json
├── evidence_visibility_matrix_v1.json
└── p1_b_evidence_completeness_report_v1.json

src/pchsi/evaluation/
├── policy_call_evidence.py
├── evidence_visibility.py
├── evidence_completeness.py
└── condition_execution_binding.py

scripts/evaluation/
└── audit_p1b_evidence_completeness.py

tests/evaluation/
├── test_policy_call_evidence.py
├── test_evidence_visibility.py
├── test_evidence_completeness.py
├── test_condition_execution_binding.py
└── test_audit_p1b_evidence_completeness.py
```

Modify narrowly:

```text
configs/evaluation/schemas/e1_episode_artifact_v1.json
src/pchsi/evaluation/action_trace.py
src/pchsi/evaluation/rendered_prompt.py
src/pchsi/evaluation/policy_client.py
src/pchsi/evaluation/trace_assembler.py
src/pchsi/evaluation/episode_artifact.py
src/pchsi/evaluation/episode_evaluator.py
src/pchsi/evaluation/schema_models.py
tests/evaluation/test_action_trace.py
tests/evaluation/test_p1b_rendered_prompt_evidence.py
tests/evaluation/test_episode_evaluator.py
tests/evaluation/test_episode_artifact.py
tests/evaluation/test_evaluation_schema_inventory.py
```

Do not modify `runtime_core.py`.

---

### Task 1: Machine-readable evidence requirements and baseline gap audit

**Files:**
- Create: `configs/evaluation/schemas/p1_b_evidence_completeness_report_v1.json`
- Create: `src/pchsi/evaluation/evidence_completeness.py`
- Create: `scripts/evaluation/audit_p1b_evidence_completeness.py`
- Create: `tests/evaluation/test_evidence_completeness.py`
- Create: `tests/evaluation/test_audit_p1b_evidence_completeness.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Produces: `EvidenceRequirementStatus`, `EvidenceRequirementV1`, `EvidenceCompletenessReportV1`, `audit_current_evidence_contract()`.

Freeze statuses:

```text
PRESENT_AND_VALIDATED
PRESENT_BUT_UNVALIDATED
PARTIAL
MISSING
NOT_APPLICABLE_WITH_JUSTIFICATION
```

- [ ] **Step 1: RED baseline-report test**

```python
def test_current_baseline_marks_raw_response_body_missing_from_bundle() -> None:
    report = audit_current_evidence_contract()

    assert report.status_for(
        "policy_call.raw_response_body"
    ) is EvidenceRequirementStatus.MISSING
```

Likewise mark request wire bytes, token IDs, finish reason and latency as missing from the published bundle even though they exist transiently in memory.

- [ ] **Step 2: Implement explicit requirement inventory**

The inventory must include every item from spec sections 16–21 and cite source path/field when present.

Do not use AST heuristics to claim scientific validation; status is an explicit reviewed mapping.

- [ ] **Step 3: Update schema inventory, GREEN and commit**

```bash
python -m pytest -q tests/evaluation/test_evidence_completeness.py
python -m pytest -q
git diff --check

git add -- \
  configs/evaluation/schemas/p1_b_evidence_completeness_report_v1.json \
  src/pchsi/evaluation/evidence_completeness.py \
  scripts/evaluation/audit_p1b_evidence_completeness.py \
  tests/evaluation/test_evidence_completeness.py \
  tests/evaluation/test_audit_p1b_evidence_completeness.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git commit -m "Add P1-B trajectory evidence gap audit"
```

---

### Task 2: PolicyCallEvidenceV1 publishes exact request/response evidence

**Files:**
- Create: `configs/evaluation/schemas/policy_call_evidence_v1.json`
- Create: `src/pchsi/evaluation/policy_call_evidence.py`
- Create: `tests/evaluation/test_policy_call_evidence.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Produces immutable `PolicyCallEvidenceV1`.

Required fields:

```text
model_call_index
environment_step_count_before
client_request_id
provider_request_id

prompt_text
prompt_sha256
rendered_prompt_text
rendered_prompt_sha256
rendered_prompt_token_ids
rendered_prompt_token_count

request_wire_bytes_base64
request_wire_sha256

http_status
response_headers_allowlisted
raw_response_body_base64
raw_response_body_sha256

raw_response_text
raw_response_text_sha256
finish_reason
prompt_tokens
completion_tokens
prompt_token_ids
completion_token_ids
latency_ms

public_task_goal
public_task_goal_sha256
observation
observation_sha256
admissible_commands
admissible_commands_sequence_sha256

executed_history
executed_history_sha256
interface_feedback_before
budget_before
```

No secret headers.

- [ ] **Step 1: RED exact-byte round trip**

Construct an evidence object with binary request/response bytes and prove base64 decode restores exact bytes and hashes.

- [ ] **Step 2: RED secret-header rejection**

```python
@pytest.mark.parametrize(
    "key",
    ["authorization", "proxy-authorization", "cookie", "set-cookie"],
)
def test_secret_header_is_rejected(key) -> None:
    with pytest.raises(ValueError):
        PolicyCallEvidenceV1(... response_headers_allowlisted={key: "secret"})
```

- [ ] **Step 3: Implement**

Allowlist only frozen non-secret response metadata required for provenance. Provider request ID is a dedicated field.

- [ ] **Step 4: Inventory, full regression, commit**

```bash
python -m pytest -q tests/evaluation/test_policy_call_evidence.py
python -m pytest -q
python -m compileall -q src tests
git diff --check

git add -- \
  configs/evaluation/schemas/policy_call_evidence_v1.json \
  src/pchsi/evaluation/policy_call_evidence.py \
  tests/evaluation/test_policy_call_evidence.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git commit -m "Add exact policy call evidence"
```

---

### Task 3: Capture policy-call evidence without changing generation semantics

**Files:**
- Modify: `src/pchsi/evaluation/policy_client.py`
- Modify: `src/pchsi/evaluation/episode_evaluator.py`
- Modify: `src/pchsi/evaluation/trace_assembler.py`
- Test: `tests/evaluation/test_episode_evaluator.py`
- Test: `tests/evaluation/test_policy_call_evidence.py`

**Interfaces:**
- Existing `PolicyClient.generate()` remains source-compatible and continues
  returning `PolicyGeneration`.
- Add exactly:

```python
@dataclass(frozen=True, slots=True)
class PolicyCallResultV1:
    generation: PolicyGeneration
    transport_evidence: PolicyCallTransportEvidenceV1
```

```python
def generate_with_evidence(
    self,
    *,
    request: E1PolicyRequestV1,
    expected_prompt: RenderedPromptEvidence,
) -> PolicyCallResultV1: ...
```

- `generate()` delegates to `generate_with_evidence(...).generation`.
- The P1 condition-bound episode path uses `generate_with_evidence()`.
- Legacy E1 callers and tests using `generate()` remain unchanged.
- Runtime Core must not depend on transport evidence.

- [ ] **Step 1: RED exact request evidence test**

Prove `request.to_wire_bytes()` published in evidence exactly matches bytes given to `transport.post_exact()`.

- [ ] **Step 2: RED raw response evidence test**

Prove exact HTTP body returned by transport is preserved byte-for-byte.

- [ ] **Step 3: Implement minimal evidence capture**

Capture:

```text
status
allowlisted headers
exact body
request bytes
latency
generation metadata
expected rendered prompt
```

Continue validating server prompt token IDs against local rendering.

- [ ] **Step 4: Episode evaluator constructs one PolicyCallEvidence per completed generation**

Non-executed parser/off-list attempts must still produce a policy-call record.

Transport failure before a valid generation remains infrastructure evidence, not a fabricated completed policy-call record; document it separately in terminal receipt/error path.

- [ ] **Step 5: Full regression and commit**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_evaluator.py \
  tests/evaluation/test_policy_call_evidence.py

python -m pytest -q
git diff --check

git add -- \
  src/pchsi/evaluation/policy_client.py \
  src/pchsi/evaluation/episode_evaluator.py \
  src/pchsi/evaluation/trace_assembler.py \
  tests/evaluation/test_episode_evaluator.py \
  tests/evaluation/test_policy_call_evidence.py

git commit -m "Capture complete policy call evidence"
```

---

### Task 4: Add policy_calls.jsonl to the immutable attempt bundle

**Files:**
- Modify: `src/pchsi/evaluation/episode_artifact.py`
- Modify: `src/pchsi/evaluation/schema_models.py`
- Modify: `src/pchsi/evaluation/episode_evaluator.py`
- Modify: `tests/evaluation/test_episode_artifact.py`
- Modify: `tests/evaluation/test_episode_evaluator.py`

**Interfaces:**
- `AttemptBundleBytes` gains `policy_calls_jsonl`.
- Frozen bundle file order becomes:

```text
attempt.json
action_traces.jsonl
policy_calls.jsonl
public_transitions.jsonl
SHA256SUMS
```

- [ ] **Step 1: RED bundle test**

```python
def test_bundle_contains_one_policy_call_record_per_action_trace() -> None:
    bundle = build_attempt_bundle_bytes(
        episode_artifact=episode,
        traces=traces,
        policy_calls=policy_calls,
        public_transitions=transitions,
    )

    assert b'"model_call_index":0' in bundle.policy_calls_jsonl
```

- [ ] **Step 2: Count invariant**

Require:

```text
episode.trace_count
= len(action_traces)
= len(policy_calls)
```

and contiguous model call indices across both files.

- [ ] **Step 3: Exact bundle hash versus scientific semantic hash**

Freeze two tested projections:

```python
def exact_policy_call_payload(
    evidence: PolicyCallEvidenceV1,
) -> dict[str, object]: ...
```

This contains every published exact audit field and is covered by
`policy_calls.jsonl`, per-file SHA-256 and `attempt_bundle_sha256`.

```python
def semantic_policy_call_payload(
    evidence: PolicyCallEvidenceV1,
) -> dict[str, object]: ...
```

This contains scientific request/generation/state semantics but excludes the
operational nondeterminism listed in “Frozen evidence identity layers”.

Required tests:

```text
changing latency/request IDs/operational headers
→ exact bundle hash changes
→ episode semantic hash does not change

changing prompt/content/token IDs/menu/budget
→ exact bundle hash changes
→ episode semantic hash changes
```

Do not put exact raw response-envelope bytes directly into the semantic
projection merely because they are content-bearing at the transport layer.

- [ ] **Step 4: Full regression and commit**

```bash
python -m pytest -q \
  tests/evaluation/test_episode_artifact.py \
  tests/evaluation/test_episode_evaluator.py

python -m pytest -q
git diff --check

git add -- \
  src/pchsi/evaluation/episode_artifact.py \
  src/pchsi/evaluation/schema_models.py \
  src/pchsi/evaluation/episode_evaluator.py \
  tests/evaluation/test_episode_artifact.py \
  tests/evaluation/test_episode_evaluator.py

git commit -m "Publish complete policy call evidence"
```

---

### Task 5: Visibility matrix and no-future-leak projections

**Files:**
- Create: `configs/evaluation/schemas/evidence_visibility_matrix_v1.json`
- Create: `src/pchsi/evaluation/evidence_visibility.py`
- Create: `tests/evaluation/test_evidence_visibility.py`
- Modify: `tests/evaluation/test_evaluation_schema_inventory.py`

**Interfaces:**
- Produces:
  - `EvidenceVisibilityClass`
  - `build_dev_teacher_projection()`
  - `build_student_decision_projection()`
  - `validate_visibility_matrix()`

Visibility classes:

```text
POLICY_VISIBLE_AT_DECISION
POST_ACTION_PUBLIC_AUDIT
EPISODE_TERMINAL_OUTCOME
OFFLINE_TEACHER_VISIBLE_DEV_ONLY
OPERATIONAL_PROVENANCE_ONLY
SEALED_ORACLE_AUDIT_ONLY
```

- [ ] **Step 1: RED student projection future-leak tests**

Student projection at call `t` must reject/omit:

```text
next observation
future menu
episode success
termination outcome
teacher rationale
Q2 result
```

- [ ] **Step 2: RED teacher access test**

```python
def test_teacher_projection_rejects_select_task() -> None:
    with pytest.raises(PermissionError):
        build_dev_teacher_projection(
            access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY,
            ...
        )
```

- [ ] **Step 3: DEV teacher view**

DEV teacher may receive the completed public trajectory and terminal outcome, but never hidden simulator state or secrets.

- [ ] **Step 4: Inventory, full regression, commit**

```bash
python -m pytest -q tests/evaluation/test_evidence_visibility.py
python -m pytest -q
git diff --check

git add -- \
  configs/evaluation/schemas/evidence_visibility_matrix_v1.json \
  src/pchsi/evaluation/evidence_visibility.py \
  tests/evaluation/test_evidence_visibility.py \
  tests/evaluation/test_evaluation_schema_inventory.py

git commit -m "Add P1-B evidence visibility projections"
```

---

### Task 6: Condition-bound execution binding for P1 DEV

**Files:**
- Create: `src/pchsi/evaluation/condition_execution_binding.py`
- Create: `tests/evaluation/test_condition_execution_binding.py`
- Modify: `configs/evaluation/schemas/e1_episode_artifact_v1.json`
- Modify: `src/pchsi/evaluation/action_trace.py`
- Modify narrowly: `src/pchsi/evaluation/episode_evaluator.py`
- Modify: `src/pchsi/evaluation/schema_models.py`
- Modify: `tests/evaluation/test_action_trace.py`
- Modify: `tests/evaluation/test_episode_evaluator.py`
- Modify: `tests/evaluation/test_schema_models.py`

**Interfaces:**
- Consumes: `ConditionRunScheduleCellV1`, `TaskAccessRecordV1`, `PolicyConditionManifestV1`.
- Produces a condition-bound cell adapter that preserves the P4 condition cell ID in all artifact identities.

Suggested type:

```python
@dataclass(frozen=True, slots=True)
class ConditionBoundEpisodeCellV1:
    scheduled_cell_id: str
    task_index: int
    task_id: str
    seed: int
    policy_condition_id: str
    access_class: DistillationAccessClass
```

`scheduled_cell_id` equals the condition schedule's `condition_cell_id`, not a regenerated legacy `e1-t...` ID.

- [ ] **Step 1: RED identity preservation**

```python
def test_condition_cell_id_is_preserved_into_execution_attempt_id() -> None:
    cell = bind_condition_cell(...)
    assert cell.scheduled_cell_id.startswith("p4-P4-R0-PI0-")
    assert execution_attempt_id(
        scheduled_cell_id=cell.scheduled_cell_id,
        attempt_ordinal=0,
    ).startswith(cell.scheduled_cell_id)
```

- [ ] **Step 2: Reject SELECT for P1 execution**

P1 DEV binding requires `DEV_VISIBLE` and `P4-R0-PI0`.

- [ ] **Step 3: Episode config accepts legacy E1 or condition-bound cells without changing legacy behavior**

Use a narrow structural helper rather than weakening identity checks.

- [ ] **Step 4: Trace/episode provenance**

Add optional P1-only fields to the existing trace/episode models while
preserving legacy E1 wire compatibility:

```text
task_access_manifest_sha256
policy_condition_manifest_sha256
condition_run_schedule_sha256
access_class
policy_condition_id
condition_cell_id
```

Rules:

- legacy E1 artifacts may omit the complete P1 field bundle;
- if any P1 field is present, all P1 fields are required;
- a P1 DEV episode requires all fields;
- `condition_cell_id` equals the scheduled cell ID;
- the three manifest hashes must equal the exact frozen artifacts;
- `access_class` must be `DEV_VISIBLE`;
- `policy_condition_id` must be `P4-R0-PI0`;
- do not overload `split_name=valid_unseen` as access class;
- update `e1_episode_artifact_v1.json` without weakening
  `additionalProperties=false`.

- [ ] **Step 4.1: Preserve legacy E1 wire compatibility while testing P1 optional fields**

`E1_EPISODE_ARTIFACT_V1` now has exactly six P1-only optional properties:

```text
task_access_manifest_sha256
policy_condition_manifest_sha256
condition_run_schedule_sha256
access_class
policy_condition_id
condition_cell_id
```

The schema/model synchronization test must therefore verify both modes:

```text
legacy E1 EpisodeArtifact
→ emits exactly schema properties minus those six P1-only properties

P1 condition-bound EpisodeArtifact
→ emits exactly all schema properties
→ round-trips exactly
```

Do not make legacy E1 emit six new `null` fields merely to satisfy a
historical all-properties-equal assertion. That would change the frozen
legacy wire artifact.

- [ ] **Step 5: Full regression, legacy E1 tests, commit**

```bash
python -m pytest -q \
  tests/evaluation/test_condition_execution_binding.py \
  tests/evaluation/test_episode_evaluator.py \
  tests/evaluation/test_run_schedule.py

python -m pytest -q
git diff --check

git add -- \
  src/pchsi/evaluation/condition_execution_binding.py \
  src/pchsi/evaluation/episode_evaluator.py \
  tests/evaluation/test_condition_execution_binding.py \
  tests/evaluation/test_episode_evaluator.py

git commit -m "Bind P1 DEV episodes to condition schedule"
```

---

### Task 7: Machine-verifiable evidence completeness gate

**Files:**
- Modify: `src/pchsi/evaluation/evidence_completeness.py`
- Create/modify: `tests/evaluation/test_evidence_completeness.py`
- Modify: `scripts/evaluation/audit_p1b_evidence_completeness.py`

**Interfaces:**
- Produces:
  - `validate_distillation_evidence_complete(...)`
  - eligibility status `INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE`.

- [ ] **Step 1: RED missing-record and cross-file mismatch tests**

Reject:

```text
missing policy call
missing trace
missing transition for executed action
broken model_call_index continuity
broken BudgetState continuity
broken observation/menu chain
missing executed history
missing visibility labels
access_class != DEV_VISIBLE

policy call prompt/observation/menu differs from ActionTrace
policy call raw response differs from ActionTrace
policy call provider request ID differs from TraceProvenance
policy call budget_before differs from ActionTrace counters
executed ActionTrace action differs from PublicTransition submitted action
ActionTrace resulting observation differs from PublicTransition result
condition cell/manifest hashes differ across episode and trace
```

- [ ] **Step 2: GREEN complete synthetic episode**

A complete synthetic episode with parser failures and executed actions must pass.

- [ ] **Step 3: Re-run gap audit**

After Tasks 2–6, all critical requirements required before teacher distillation must be:

```text
PRESENT_AND_VALIDATED
```

Any remaining critical `MISSING` blocks smoke execution.

- [ ] **Step 4: Full regression and commit**

```bash
python -m pytest -q
python -m compileall -q src tests scripts
git diff --check

git add -- \
  src/pchsi/evaluation/evidence_completeness.py \
  scripts/evaluation/audit_p1b_evidence_completeness.py \
  tests/evaluation/test_evidence_completeness.py

git commit -m "Enforce P1-B complete trajectory evidence"
```

## P1-B2 Completion Gate

A code candidate can receive:

```text
CODE_CANDIDATE_READY_P1_B2_COMPLETE_TRAJECTORY_EVIDENCE_V1
```

only if:

- full suite passes;
- Runtime Core diff is empty;
- exact request/response bytes are published;
- token IDs/usage/finish reason/latency are published;
- every model call has one evidence record;
- non-executed attempts remain present;
- P1 DEV access/condition identity is bound to episode artifacts;
- teacher projection rejects SELECT;
- student projection contains no future outcome;
- completeness gate passes on complete synthetic fixtures;
- baseline gap audit has no unresolved critical `MISSING`.

After code approval and P1-B1 authoritative artifact materialization, run a separate 1–3 task completeness smoke. Smoke execution is not authorized by this implementation plan.
