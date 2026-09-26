# Outcome-Aware Hierarchical Analyzer V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the deterministic scientific infrastructure for an outcome-aware, failure-priority Hierarchical Analyzer V2 that analyzes failed and successful trajectories through separate semantic lanes, preserves external-model traces for later localization, produces bounded executable candidates, and evaluates downstream repair value with a literature-grounded, coverage-aware metric system.

**Architecture:** Reuse the sealed `ANALYZER_EVIDENCE_PACK_V1`, Memory role packs, same-state F0/F1 runner, canonical JSON helpers, and task-access authorities. Add a new `pchsi.analyzer` package whose deterministic components gate scientific outcome availability, schedule offline sampling, validate typed Analyzer artifacts, group error-instance memberships, aggregate explicit semantic attributions, project already source-conditioned candidates, materialize cognitive-role supervision, and aggregate metrics. Strong-model adapters and environment runners remain separately approval-gated; no Task Policy prompt receives Analyzer prose.

**Tech Stack:** Python 3.12, dataclasses, `enum`, `json`, `hashlib`, existing canonical JSON helpers, JSON Schema Draft 2020-12, pytest, shell fixed-head audits, existing ALFWorld/evaluation/Memory infrastructure.

**Spec:** `docs/superpowers/specs/2026-08-23-outcome-aware-hierarchical-analyzer-v2-design.md`

## Global Constraints

- `main` is not modified by implementation work until fixed-head source review and explicit merge approval.
- `ANALYZER_EVIDENCE_PACK_V1` is immutable and identical across A0–A3.
- A0–A3 remain the failure-repair main experiment; success-quality analysis is a separate pilot.
- A1 local results are generated once and reused byte-for-byte by A2/A3.
- Local analysis is Memory-blind; A3 attaches one frozen `ANALYZER_MEMORY_PACK_V1` only at higher levels.
- Scientific outcome availability and outcome routing use mechanical facts only; infrastructure/protocol/incomplete episodes never become policy failures.
- Analysis regimes remain exactly `85/15`, `70/30`, and `55/45`, always failure-majority, but only in `MECHANICAL_OUTCOME_ANALYSIS_SAMPLING_SCHEDULER_V1`. The scheduler does not define formal `U_reg`, select the Researcher bottleneck, or constitute an Analyzer method claim.
- Formal A0–A3 repair generation uses one common preregistered exact-state universe `U_reg`; eligibility freezes before Analyzer output and F0/F1 outcomes.
- Formal candidate budget is exactly K=1 candidate or ABSTAIN per condition per `U_reg` unit.
- Strong terminal-Harm/safety claims require a separately preregistered protected baseline cohort; failure-to-failure cost degradation remains a secondary paired diagnostic.
- The main verification-cost unit is formal verifier environment steps per repaired unique `U_reg` unit; branch episodes, policy calls, tokens, dollars, and wall time remain separate diagnostics.
- Weighted composite scores that mix success, Harm, verification cost, tokens, dollars, or wall time are forbidden; report these quantities separately.
- `terminal consequence` is mechanical evidence, not a scored Analyzer semantic prediction.
- Analyzer outputs never create Benefit/Harm/Neutral/Uncertain, training labels, or promotion decisions. Every artifact is `PRIVILEGED_OFFLINE_ANALYSIS` with `POST_EPISODE_DEV_ONLY` information boundary.
- Semantic G-stage output may propose source-conditioned executable bytes under K=1/ABSTAIN; C/P/X cannot rewrite them. Only deterministic projectors may validate and materialize executable candidate artifacts.
- Only exact actions or one-to-four-action options enter F1; Analyzer prose never enters the Task Policy prompt.
- All intervention actions count against the common environment budget.
- Success optimization uses a distinct effect-label namespace from failure repair.
- Raw external-model request/response evidence is immutable; adjudicated outputs and environment outcomes are separate layers.
- Existing task/gamefile access classes and historical-exposure records are reused, not replaced.
- Unique task/gamefile is the primary independent unit; branches and repeated continuations are not independent samples.
- Abstentions, invalid candidates, Harm, Neutral, Uncertain, and infrastructure incidents remain in denominators according to the metric registry.
- `Eligible-State Verified Repair Yield (EVRY)` is the primary C1 endpoint on one common preregistered `U_reg`, and is always reported with failure/protected-cohort Harm, ProposalCoverage, VBP, verifier environment steps per repaired unit, and EVRY@B.
- Internal `CSVRY` is a secondary specificity-confirmed subset on the preregistered D0–D4 cohort; it is not a headline endpoint and never gates a formal Benefit from verified-training consideration.
- Metric language remains `project-proposed` until the final related-work audit is complete.
- Tasks 1–16 end at `ANALYZER_DETERMINISTIC_SCIENTIFIC_INFRASTRUCTURE_CODE_APPROVED`. No formal model, environment, or policy-training execution is authorized; model activation requires the separate runtime handoff.

---

## File map

### New production package

```text
src/pchsi/analyzer/
├── __init__.py
├── authority.py
├── contracts.py
├── outcome_router.py
├── analysis_sampling.py
├── local_validation.py
├── grouping.py
├── component_attribution.py
├── capability_profile.py
├── crosscheck.py
├── candidate_projector.py
├── role_trace.py
├── supervision_materializer.py
├── metric_registry.py
├── metrics.py
├── success_optimization.py
├── repair_decomposition.py
├── gold_panel.py
└── experiment_registry.py
```

### New schemas and frozen contracts

```text
configs/analyzer/schemas/
├── analyzer_run_manifest_v1.json
├── analyzer_local_result_v1.json
├── analyzer_group_manifest_v1.json
├── analyzer_group_result_v1.json
├── analyzer_capability_profile_v1.json
├── analyzer_policy_behavior_profile_v1.json
├── analyzer_crosscheck_result_v1.json
├── analyzer_repair_candidate_v1.json
├── analyzer_success_optimization_candidate_v1.json
├── analyzer_success_workflow_reference_v1.json
├── analyzer_regression_guard_v1.json
├── cognitive_role_trace_v1.json
├── repair_effect_decomposition_trace_v1.json
└── repair_effect_decomposition_result_v1.json

configs/analyzer/
├── mechanical_analysis_sampling_thresholds_v1.json.example
├── analyzer_metric_registry_v1.json
├── analyzer_capability_taxonomy_v1.json
└── analyzer_common_repair_budget_v1.json
```

### New scripts

```text
scripts/analyzer/
├── build_outcome_analysis_census_v1.py
├── allocate_outcome_analysis_sampling_v1.py
├── materialize_analyzer_gold_panels_v1.py
├── validate_analyzer_result_v1.py
├── project_analyzer_candidates_v1.py
├── materialize_local_analyzer_supervision_v1.py
├── aggregate_analyzer_metrics_v1.py
├── run_success_optimization_pilot_v1.py
└── run_repair_effect_decomposition_v1.py
```

### Tests

```text
tests/analyzer/
├── test_authority.py
├── test_contracts.py
├── test_outcome_router.py
├── test_analysis_sampling.py
├── test_local_validation.py
├── test_grouping.py
├── test_capability_profile.py
├── test_crosscheck.py
├── test_candidate_projector.py
├── test_role_trace.py
├── test_supervision_materializer.py
├── test_metric_registry.py
├── test_metrics.py
├── test_success_optimization.py
├── test_repair_decomposition.py
├── test_gold_panel_materialization.py
├── test_experiment_registry.py
└── test_static_scientific_audit.py
```

---

## Scientific Review Disposition and Scope

The plan incorporates `ANALYZER_PLAN_REVIEW_DISPOSITION_HARDENING_V1`. H1, H3,
H4, H6, and H7 are adopted. H2 retains the approved ratios only as a mechanical
offline sampling scheduler. H5 is resolved by G-stage source-conditioned repair
bytes without an unequal extra A2/A3 call. Task 13 is secondary/non-blocking;
Task 14 is post-Benefit secondary. Tasks 1–16 build deterministic scientific
infrastructure; strong-model activation remains a separate approval gate.

---

### Task 1: Freeze Analyzer authorities, information boundaries, and canonical identities

**Files:**
- Create: `src/pchsi/analyzer/__init__.py`
- Create: `src/pchsi/analyzer/authority.py`
- Test: `tests/analyzer/test_authority.py`

**Interfaces:**
- Consumes: existing canonical JSON/hash utilities.
- Produces: `TrajectoryOutcome`, `OutcomeRouteStatus`, `AnalysisObjective`,
  `AnalyzerCondition`, `AnalyzerAuthority`, `ScientificUse`,
  `AnalysisTimeInformationBoundary`, `CandidateStatus`,
  `CrosscheckDisposition`, `FailureLifecycleStatus`, and
  `canonical_artifact_sha256(...)`.

- [ ] **Step 1: Write failing authority tests**

```python
from pchsi.analyzer.authority import (
    AnalysisTimeInformationBoundary,
    AnalyzerAuthority,
    AnalyzerCondition,
    OutcomeRouteStatus,
    ScientificUse,
)


def test_condition_ids_are_exact() -> None:
    assert [item.value for item in AnalyzerCondition] == [
        "A0_ONE_SHOT_LOCAL",
        "A1_MULTI_HYPOTHESIS_LOCAL",
        "A2_HIERARCHICAL_NO_HISTORY",
        "A3_HIERARCHICAL_WITH_HISTORY",
    ]


def test_non_scientific_routes_are_explicit() -> None:
    assert [item.value for item in OutcomeRouteStatus] == [
        "SCIENTIFIC_OUTCOME_AVAILABLE",
        "INFRASTRUCTURE_UNAVAILABLE",
        "PROTOCOL_INVALID",
        "EVIDENCE_INCOMPLETE",
    ]


def test_analyzer_is_privileged_offline_only() -> None:
    assert ScientificUse.PRIVILEGED_OFFLINE_ANALYSIS.value == "PRIVILEGED_OFFLINE_ANALYSIS"
    assert AnalysisTimeInformationBoundary.POST_EPISODE_DEV_ONLY.value == "POST_EPISODE_DEV_ONLY"
    assert "EFFECT" not in {item.name for item in AnalyzerAuthority}
```

- [ ] **Step 2: Run RED**

```bash
python -m pytest -q tests/analyzer/test_authority.py
```

Expected: import failure.

- [ ] **Step 3: Implement exact frozen enums and canonical hashing**

No aliases, permissive fallback, online-policy use, effect authority, training
authority, or promotion authority are representable.

- [ ] **Step 4: Run focused tests and compile**

```bash
python -m pytest -q tests/analyzer/test_authority.py
python -m compileall -q src/pchsi/analyzer
```

- [ ] **Step 5: Commit**

```bash
git add src/pchsi/analyzer/__init__.py src/pchsi/analyzer/authority.py tests/analyzer/test_authority.py
git commit -m "Define Analyzer scientific authority boundaries"
```

---

### Task 2: Add strict JSON Schemas and typed artifact loaders

**Files:**
- Create: all files under `configs/analyzer/schemas/` listed in the file map.
- Create: `src/pchsi/analyzer/contracts.py`
- Test: `tests/analyzer/test_contracts.py`
- Modify: existing closed schema-inventory test if the repository enforces an exact allowlist.

**Interfaces:**
- Consumes: `AnalyzerCondition`, `TrajectoryOutcome`, canonical JSON helpers, existing evidence reference format.
- Produces: frozen dataclasses `AnalyzerRunManifestV1`, `OutcomeRouteV1`, `AnalyzerLocalResultV1`, `ErrorInstanceMembershipV1`, `AnalyzerGroupManifestV1`, `AnalyzerGroupResultV1`, `AnalyzerComponentAttributionV1`, `AnalyzerCapabilityProfileV1`, `AnalyzerPolicyBehaviorProfileV1`, `AnalyzerCrosscheckResultV1`, `AnalyzerRepairCandidateV1`, `AnalyzerSuccessOptimizationCandidateV1`, `AnalyzerSuccessWorkflowReferenceV1`, `AnalyzerRegressionGuardV1`, `CognitiveRoleTraceV1`, `RepairEffectDecompositionTraceV1`, and `RepairEffectDecompositionResultV1`; plus `load_and_validate(schema_id: str, payload: Mapping[str, object])`.

- [ ] **Step 1: Write strict-schema tests**

```python
import json
from pathlib import Path

import pytest

from pchsi.analyzer.contracts import load_and_validate


def _valid_local_failure() -> dict[str, object]:
    return json.loads(Path("tests/fixtures/analyzer/local_failure_valid.json").read_text())


def test_local_result_rejects_benefit_field() -> None:
    payload = _valid_local_failure()
    payload["Benefit"] = True
    with pytest.raises(ValueError, match="additional properties"):
        load_and_validate("ANALYZER_LOCAL_RESULT_V1", payload)


def test_exactly_one_local_lane_is_present() -> None:
    payload = _valid_local_failure()
    payload["success_analysis"] = {}
    with pytest.raises(ValueError, match="exactly one lane"):
        load_and_validate("ANALYZER_LOCAL_RESULT_V1", payload)


def test_a3_group_requires_memory_packet() -> None:
    payload = json.loads(Path("tests/fixtures/analyzer/group_a3_valid.json").read_text())
    payload["memory_packet_sha256"] = None
    with pytest.raises(ValueError, match="A3 requires exactly one"):
        load_and_validate("ANALYZER_GROUP_RESULT_V1", payload)
```

Create minimal valid fixtures under `tests/fixtures/analyzer/` as part of this task; every fixture uses fake hashes and no real task data.

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest -q tests/analyzer/test_contracts.py
```

Expected: import or missing-schema failure.

- [ ] **Step 3: Write schemas with fail-closed structure**

Each object schema must contain:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "additionalProperties": false,
  "required": ["schema_id", "schema_version"],
  "properties": {
    "schema_id": {"const": "..."},
    "schema_version": {"const": 1}
  }
}
```

For the local result, encode a `oneOf` requiring exactly one of `failure_analysis` and `success_analysis`. Keep Analyzer effect/promotion fields absent from every schema.

- [ ] **Step 4: Implement typed loaders and semantic validation**

`load_and_validate()` performs JSON Schema validation first, then semantic checks that are awkward in JSON Schema:

```python
def _validate_local_semantics(payload: Mapping[str, object]) -> None:
    failure = payload.get("failure_analysis")
    success = payload.get("success_analysis")
    if (failure is None) == (success is None):
        raise ValueError("exactly one lane payload is required")
    if payload["trajectory_outcome"] == "FAILURE" and failure is None:
        raise ValueError("FAILURE requires failure_analysis")
    if payload["trajectory_outcome"] == "SUCCESS" and success is None:
        raise ValueError("SUCCESS requires success_analysis")
```

Also validate route availability before trajectory outcome, privileged-offline information boundaries, rank contiguity, multi-error membership identities, evidence-reference existence through an injected resolver, call-index bounds, A3 Memory requirements, source-conditioned repair binding, and forbidden authority values.

- [ ] **Step 5: Run focused and schema-inventory tests**

```bash
python -m pytest -q tests/analyzer/test_contracts.py
python -m pytest -q tests -k "schema and inventory"
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add configs/analyzer/schemas src/pchsi/analyzer/contracts.py tests/analyzer tests/fixtures/analyzer
git commit -m "Add strict outcome-aware Analyzer schemas"
```

---

### Task 3: Implement the deterministic scientific-outcome gate, outcome router, and mechanical census

**Files:**
- Create: `src/pchsi/analyzer/outcome_router.py`
- Create: `scripts/analyzer/build_outcome_analysis_census_v1.py`
- Test: `tests/analyzer/test_outcome_router.py`

**Interfaces:**
- Consumes: validated `ANALYZER_EVIDENCE_PACK_V1`, terminal/environment fields,
  execution status, protocol-integrity evidence, and completeness evidence.
- Produces: `OutcomeRouteV1`, `OutcomeAnalysisCensusV1`, and
  `route_episode(evidence_pack) -> OutcomeRouteV1`.

- [ ] **Step 1: Write scientific-availability RED tests**

```python
from pchsi.analyzer.outcome_router import route_episode


def test_environment_success_routes_to_success_quality(fake_success_pack) -> None:
    route = route_episode(fake_success_pack)
    assert route.route_status == "SCIENTIFIC_OUTCOME_AVAILABLE"
    assert route.trajectory_outcome == "SUCCESS"
    assert route.analysis_objective == "SUCCESS_QUALITY"


def test_infrastructure_error_never_routes_to_failure(infrastructure_pack) -> None:
    route = route_episode(infrastructure_pack)
    assert route.route_status == "INFRASTRUCTURE_UNAVAILABLE"
    assert route.trajectory_outcome is None
    assert route.analysis_objective is None


def test_protocol_invalid_never_enters_semantic_lane(protocol_invalid_pack) -> None:
    route = route_episode(protocol_invalid_pack)
    assert route.route_status == "PROTOCOL_INVALID"
    assert route.semantic_lane_eligible is False


def test_model_text_cannot_override_environment_outcome(fake_failure_pack) -> None:
    fake_failure_pack.raw_model_responses = ['{"analysis":"task succeeded"}']
    route = route_episode(fake_failure_pack)
    assert route.trajectory_outcome == "FAILURE"
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_outcome_router.py
```

- [ ] **Step 3: Implement fail-closed route precedence**

Order is exact:

```text
protocol invalid
→ evidence incomplete
→ infrastructure unavailable
→ scientific terminal outcome available
→ SUCCESS or FAILURE
```

A false/missing success Boolean alone is never sufficient to produce FAILURE.
Every route binds `PRIVILEGED_OFFLINE_ANALYSIS` and `POST_EPISODE_DEV_ONLY`.

- [ ] **Step 4: Implement the full census**

The census reports population success/failure only from scientifically available
episodes and separately reports infrastructure/protocol/incomplete counts and
reasons. It never derives prevalence from an Analyzer-allocated sample.

- [ ] **Step 5: Run tests and CLI smoke**

```bash
python -m pytest -q tests/analyzer/test_outcome_router.py
python scripts/analyzer/build_outcome_analysis_census_v1.py --help
```

- [ ] **Step 6: Commit**

```bash
git add src/pchsi/analyzer/outcome_router.py scripts/analyzer/build_outcome_analysis_census_v1.py tests/analyzer/test_outcome_router.py
git commit -m "Gate Analyzer routing on scientific outcome availability"
```

---

### Task 4: Implement the mechanical outcome-analysis sampling scheduler

**Scientific role:** `SECONDARY_COST_AND_COVERAGE_INFRASTRUCTURE`; this is not an
Analyzer semantic method component and is not used to define formal A0–A3
`U_reg` or to choose the Training Researcher bottleneck.

**Files:**
- Create: `src/pchsi/analyzer/analysis_sampling.py`
- Create: `configs/analyzer/mechanical_analysis_sampling_thresholds_v1.json.example`
- Create: `scripts/analyzer/allocate_outcome_analysis_sampling_v1.py`
- Test: `tests/analyzer/test_analysis_sampling.py`

**Interfaces:**
- Consumes: `OutcomeAnalysisCensusV1` and a human-approved mechanical threshold
  manifest.
- Produces: `OutcomeAnalysisSamplingAllocationV1` for broad offline API sampling;
  formal A0–A3 panel identity remains external and unchanged.

- [ ] **Step 1: Write ratio, floor, and role-boundary RED tests**

```python
from pchsi.analyzer.analysis_sampling import allocate_analysis_sampling


def test_failure_critical_is_85_15(census, thresholds) -> None:
    result = allocate_analysis_sampling(census, thresholds, total_slots=100)
    assert (result.failure_slots, result.success_slots) == (85, 15)


def test_scheduler_cannot_define_formal_u_reg(census, thresholds) -> None:
    result = allocate_analysis_sampling(census, thresholds, total_slots=20)
    assert not hasattr(result, "registered_universe_sha256")
    assert result.scientific_role == "SECONDARY_COST_AND_COVERAGE_INFRASTRUCTURE"


def test_every_failing_family_gets_floor_before_success(census, thresholds) -> None:
    result = allocate_analysis_sampling(census, thresholds, total_slots=12)
    assert set(result.failure_family_counts) == set(census.failing_families)
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_analysis_sampling.py
```

- [ ] **Step 3: Implement exact approved regimes**

Retain `85/15`, `70/30`, and `55/45`, severe-regression overrides, failing-family
floors, largest-remainder integer allocation, frozen family order, and
outcome-independent selection. Never inspect Analyzer text or F0/F1 outcomes.

- [ ] **Step 4: Add anti-authority tests**

Reject model-generated threshold fields, missing human approval hash, a census
hash mismatch, altered ratios, any attempt to mutate formal `U_reg`, or any
field selecting the principal Researcher bottleneck/training method.

- [ ] **Step 5: Run tests**

```bash
python -m pytest -q tests/analyzer/test_analysis_sampling.py
```

- [ ] **Step 6: Commit**

```bash
git add src/pchsi/analyzer/analysis_sampling.py configs/analyzer/mechanical_analysis_sampling_thresholds_v1.json.example scripts/analyzer/allocate_outcome_analysis_sampling_v1.py tests/analyzer/test_analysis_sampling.py
git commit -m "Add failure-priority offline analysis scheduler"
```

---

### Task 5: Validate local failure and success lane outputs

**Files:**
- Create: `src/pchsi/analyzer/local_validation.py`
- Create: `scripts/analyzer/validate_analyzer_result_v1.py`
- Test: `tests/analyzer/test_local_validation.py`

**Interfaces:**
- Consumes: raw strong-model output, condition contract, evidence pack, and expected lane.
- Produces: a validated `AnalyzerLocalResultV1` or a typed rejection receipt; never repairs malformed model content.

- [ ] **Step 1: Write lifecycle and success-quality validation tests**

```python
import pytest

from pchsi.analyzer.local_validation import validate_local_result


def test_failure_lane_accepts_multiple_error_instances(valid_failure_payload, evidence_index) -> None:
    result = validate_local_result(valid_failure_payload, evidence_index)
    assert len(result.failure_analysis.error_instances) == 2


def test_success_redundancy_is_candidate_not_fact(valid_success_payload, evidence_index) -> None:
    valid_success_payload["success_analysis"]["redundancy_candidates"][0]["status"] = "PROVEN_REDUNDANT"
    with pytest.raises(ValueError, match="candidate-only"):
        validate_local_result(valid_success_payload, evidence_index)


def test_local_pass_rejects_memory_reference(valid_failure_payload, evidence_index) -> None:
    valid_failure_payload["memory_packet_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="Memory-blind"):
        validate_local_result(valid_failure_payload, evidence_index)
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_local_validation.py
```

- [ ] **Step 3: Implement strict evidence/call-index/rank/lane validation**

The validator must reject unknown references, hidden-state claims, unsupported action text, Benefit/Harm language in authority fields, more than three hypotheses/repairs, noncontiguous ranks, or a success optimization presented as verified.

- [ ] **Step 4: Preserve every raw response and rejection**

The CLI writes:

```text
raw_response.json
validation_receipt.json
validated_result.json  # only on success
```

using no-clobber publication and canonical hashes.

- [ ] **Step 5: Run tests**

```bash
python -m pytest -q tests/analyzer/test_local_validation.py tests/analyzer/test_contracts.py
```

- [ ] **Step 6: Commit**

```bash
git add src/pchsi/analyzer/local_validation.py scripts/analyzer/validate_analyzer_result_v1.py tests/analyzer/test_local_validation.py
git commit -m "Validate failure and success Analyzer lanes"
```

---

### Task 6: Build deterministic error-instance grouping and grouped-synthesis bindings

**Files:**
- Create: `src/pchsi/analyzer/grouping.py`
- Create: `scripts/analyzer/build_analyzer_groups_v1.py`
- Test: `tests/analyzer/test_grouping.py`

**Interfaces:**
- Consumes: validated local results containing `error_instances[]` or success
  process instances plus deterministic mechanical signatures.
- Produces: content-addressed `ErrorInstanceMembershipV1`,
  `AnalyzerGroupManifestV1`, and immutable grouped-synthesis input bundles.

- [ ] **Step 1: Write multi-error membership RED tests**

```python
from pchsi.analyzer.grouping import build_group_manifests


def test_one_episode_may_join_multiple_error_groups(local_result, mechanics) -> None:
    local_result.failure_analysis.error_instances = [
        fake_error("e1", lifecycle="RESOLVED_COSTLY"),
        fake_error("e2", lifecycle="ACTIVE_TERMINAL"),
    ]
    groups = build_group_manifests([local_result], mechanics)
    memberships = [m for g in groups for m in g.memberships]
    assert {(m.local_result_sha256, m.error_instance_id) for m in memberships} == {
        (local_result.validated_result_sha256, "e1"),
        (local_result.validated_result_sha256, "e2"),
    }


def test_model_mechanism_prose_is_not_primary_group_key(local_result, mechanics) -> None:
    groups_a = build_group_manifests([local_result], mechanics)
    local_result.failure_analysis.error_instances[0].mechanism_statement = "changed prose"
    groups_b = build_group_manifests([local_result], mechanics)
    assert groups_a[0].group_id == groups_b[0].group_id


def test_multiple_memberships_do_not_change_independent_unit(groups) -> None:
    assert {g.inference_cluster_unit for g in groups} == {"TASK_GAMEFILE"}
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_grouping.py
```

- [ ] **Step 3: Implement mechanical primary keys**

Primary failure keys are:

```text
task_family
error_instance_mechanical_signature
progress/precondition_signature
lifecycle/resolution_signature
terminal_footprint_class
```

One error instance has exactly one primary group membership. An episode may have
many memberships. Cross-outcome matched views and cross-group relations are
sidecars, not additional independent observations. Missing/zero claims remain
explicit.

- [ ] **Step 4: Bind grouped semantic inputs and source-conditioned slots**

Each group bundle includes immutable member evidence/local hashes and exact
source-state/menu projections for registered members. It reserves at most one
`source_conditioned_repair` or ABSTAIN per member for the G-stage output. Group
formation cannot use gold labels, F0/F1 labels, Memory text, or Analyzer prose.

- [ ] **Step 5: Run deterministic permutation tests**

```bash
python -m pytest -q tests/analyzer/test_grouping.py
```

- [ ] **Step 6: Commit**

```bash
git add src/pchsi/analyzer/grouping.py scripts/analyzer/build_analyzer_groups_v1.py tests/analyzer/test_grouping.py
git commit -m "Group Analyzer error instances deterministically"
```

---

### Task 7: Implement explicit C-stage component attribution and deterministic policy profiles

**Files:**
- Create: `src/pchsi/analyzer/component_attribution.py`
- Create: `src/pchsi/analyzer/capability_profile.py`
- Create: `configs/analyzer/analyzer_capability_taxonomy_v1.json`
- Test: `tests/analyzer/test_capability_profile.py`

**Interfaces:**
- Consumes: validated group results and the frozen capability taxonomy.
- Produces: semantic `AnalyzerComponentAttributionV1`, deterministic
  `AnalyzerCapabilityProfileV1`, and `AnalyzerPolicyBehaviorProfileV1`.

- [ ] **Step 1: Write semantic-producer and no-inference RED tests**

```python
from pchsi.analyzer.capability_profile import build_capability_profile


def test_component_assignment_requires_c_stage_artifact(group_result) -> None:
    group_result.component_attribution_sha256 = None
    with pytest.raises(ValueError, match="component attribution"):
        build_capability_profile([group_result])


def test_profile_does_not_infer_component_from_statement(group_result) -> None:
    profile_a = build_capability_profile([group_result])
    group_result.recurring_mechanisms[0].statement = "planning-like prose"
    profile_b = build_capability_profile([group_result])
    assert profile_a.profile_sha256 == profile_b.profile_sha256


def test_zero_claim_groups_remain_in_denominator(attributions, all_groups) -> None:
    profile = build_capability_profile(attributions, group_universe=all_groups)
    assert profile.complete_group_count == len(all_groups)
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_capability_profile.py
```

- [ ] **Step 3: Implement `AnalyzerComponentAttributionV1` validation**

The C-stage artifact binds group hash, principal/secondary components, evidence
refs, uncertainty, raw response hash, and validated result hash. It may assign
`UNKNOWN_OR_CROSS_COMPONENT`; it never selects a training method or Researcher
bottleneck.

- [ ] **Step 4: Implement deterministic C/P aggregation**

Aggregate only validated attribution bytes. Preserve complete/partial/zero-claim
denominators, strengths/deficits, family scope, recurrence, counterexamples,
repairability, and uncertainty. P may produce a candidate bottleneck list but
not select the principal bottleneck, experiment budget, or training method.

- [ ] **Step 5: Run tests**

```bash
python -m pytest -q tests/analyzer/test_capability_profile.py
```

- [ ] **Step 6: Commit**

```bash
git add src/pchsi/analyzer/component_attribution.py src/pchsi/analyzer/capability_profile.py configs/analyzer/analyzer_capability_taxonomy_v1.json tests/analyzer/test_capability_profile.py
git commit -m "Separate Analyzer component attribution from aggregation"
```

---

### Task 8: Add immutable cross-check sidecars

**Files:**
- Create: `src/pchsi/analyzer/crosscheck.py`
- Test: `tests/analyzer/test_crosscheck.py`

**Interfaces:**
- Consumes: original local/group/capability/profile artifacts and challenger output.
- Produces: `AnalyzerCrosscheckResultV1`; originals remain byte-identical.

- [ ] **Step 1: Write immutability and disposition tests**

```python
from copy import deepcopy

from pchsi.analyzer.crosscheck import apply_crosscheck_disposition


def test_crosscheck_never_mutates_original(group_result, crosscheck) -> None:
    before = deepcopy(group_result)
    apply_crosscheck_disposition(group_result, crosscheck)
    assert group_result == before


def test_memory_only_claim_requires_downgrade_or_rejection(group_result, memory_only_crosscheck) -> None:
    result = apply_crosscheck_disposition(group_result, memory_only_crosscheck)
    assert result.disposition in {"DOWNGRADE_SCOPE", "REQUIRE_ABSTENTION", "REJECT"}
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_crosscheck.py
```

- [ ] **Step 3: Implement sidecar validation**

Allowed dispositions:

```text
ACCEPT
DOWNGRADE_SCOPE
REQUIRE_ABSTENTION
REJECT
```

The sidecar must cite support, contradictions, residual cases, and current-vs-historical evidence source separately.

- [ ] **Step 4: Commit**

```bash
git add src/pchsi/analyzer/crosscheck.py tests/analyzer/test_crosscheck.py
git commit -m "Preserve Analyzer cross-checks as sidecars"
```

---

### Task 9: Project deterministic failure/success candidates from source-conditioned proposals

**Files:**
- Create: `src/pchsi/analyzer/candidate_projector.py`
- Create: `scripts/analyzer/project_analyzer_candidates_v1.py`
- Test: `tests/analyzer/test_candidate_projector.py`

**Interfaces:**
- Consumes: local source-specific proposals or G-stage
  `source_conditioned_repairs[]`, C/P rankings, immutable X sidecars, and exact
  source-state/menu identities.
- Produces: failure repair, success optimization, workflow reference, and
  regression-guard artifacts under K=1/ABSTAIN.

- [ ] **Step 1: Write no-invention and source-binding RED tests**

```python
from pchsi.analyzer.candidate_projector import project_failure_candidate


def test_abstract_group_template_without_source_proposal_abstains(group_result, source_state) -> None:
    group_result.source_conditioned_repairs = []
    result = project_failure_candidate(group_result, source_state)
    assert result.candidate_status == "ABSTAIN"


def test_projector_never_rewrites_executable_bytes(source_proposal, source_state) -> None:
    result = project_failure_candidate(source_proposal, source_state)
    assert result.repair.exact_action == source_proposal.exact_action


def test_wrong_menu_or_source_hash_rejects(source_proposal, source_state) -> None:
    source_state.menu_sha256 = "0" * 64
    result = project_failure_candidate(source_proposal, source_state)
    assert result.candidate_status == "REJECTED_SOURCE_BINDING"
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_candidate_projector.py
```

- [ ] **Step 3: Implement deterministic projection only**

Validate source/error-instance identity, exact menu membership, option length,
per-step live-menu checking contract, termination, environment-budget rule,
Memory identity, evidence refs, rank, and X disposition. C/P/X may rank,
downgrade, or reject but cannot change executable bytes. No fuzzy matching,
normalization, action substitution, or template-to-action synthesis is allowed.

- [ ] **Step 4: Preserve A0–A3 fairness**

The primary A2/A3 hierarchy uses the G-stage source-conditioned output generated
within its already registered higher-level call. It does not add an unequal
extra proposal call. A future equalized proposal-generation extension requires
its own preregistration.

- [ ] **Step 5: Run tests and CLI smoke**

```bash
python -m pytest -q tests/analyzer/test_candidate_projector.py
python scripts/analyzer/project_analyzer_candidates_v1.py --help
```

- [ ] **Step 6: Commit**

```bash
git add src/pchsi/analyzer/candidate_projector.py scripts/analyzer/project_analyzer_candidates_v1.py tests/analyzer/test_candidate_projector.py
git commit -m "Project source-conditioned Analyzer candidates"
```

---

### Task 10: Preserve external Analyzer/Researcher calls and materialize local supervision

**Files:**
- Create: `src/pchsi/analyzer/role_trace.py`
- Create: `src/pchsi/analyzer/supervision_materializer.py`
- Create: `scripts/analyzer/materialize_local_analyzer_supervision_v1.py`
- Test: `tests/analyzer/test_role_trace.py`
- Test: `tests/analyzer/test_supervision_materializer.py`

**Interfaces:**
- Consumes: existing task-access manifests, raw provider request/response evidence, validated/adjudicated artifacts, F0/F1 result manifests, and Researcher pre/post records.
- Produces: immutable `CognitiveRoleTraceV1`, `LOCAL_ANALYZER_SUPERVISION_DATASET_V1`, and `LOCAL_RESEARCHER_SUPERVISION_DATASET_V1`.

- [ ] **Step 1: Write access and three-layer preservation tests**

```python
import pytest

from pchsi.analyzer.role_trace import build_cognitive_role_trace


def test_non_dev_task_cannot_be_sent_to_external_model(select_task_manifest, request_evidence) -> None:
    with pytest.raises(ValueError, match="teacher_call_permitted=false"):
        build_cognitive_role_trace(select_task_manifest, request_evidence)


def test_raw_adjudicated_and_environment_layers_are_distinct(valid_trace) -> None:
    assert valid_trace.raw_response_sha256 != valid_trace.adjudicated_output_sha256
    assert valid_trace.environment_outcome_sha256 != valid_trace.adjudicated_output_sha256
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_role_trace.py tests/analyzer/test_supervision_materializer.py
```

- [ ] **Step 3: Implement trace construction**

Bind role, objective, round, policy, evidence cutoff, task/gamefile, access class, evidence/Memory hashes, provider/model/version, prompt/schema/request IDs, token/latency/cost, raw pointers/hashes, adjudication, cross-check, and downstream environment outcome.

- [ ] **Step 4: Implement deterministic materialization**

Local Analyzer targets use adjudicated structured analysis, not raw prose. Preserve negative/rejected/Harm/abstention examples with typed training eligibility rather than deleting them. Enforce disjoint task/gamefile partitions for local training and gold evaluation.

- [ ] **Step 5: Run tests and commit**

```bash
python -m pytest -q tests/analyzer/test_role_trace.py tests/analyzer/test_supervision_materializer.py

git add src/pchsi/analyzer/role_trace.py src/pchsi/analyzer/supervision_materializer.py scripts/analyzer/materialize_local_analyzer_supervision_v1.py tests/analyzer/test_role_trace.py tests/analyzer/test_supervision_materializer.py
git commit -m "Materialize governed local Analyzer supervision"
```

---


Researcher supervision materialization requires frozen Human/API pre/post records under `HUMAN_TRAINING_RESEARCHER_TEMPLATE_V1`; Analyzer artifacts alone are ineligible.

---

### Task 11: Freeze the audited metric registry and statistical aggregator

This task implements the literature-grounded, independently reviewed metric
contract. **EVRY** is the C1 primary endpoint on one common `U_reg`; final paper
authority remains π2-vs-π1 Memory-OFF/Harness-OFF task success.

**Files:**
- Create: `configs/analyzer/analyzer_metric_registry_v1.json`
- Create: `src/pchsi/analyzer/metric_registry.py`
- Create: `src/pchsi/analyzer/metrics.py`
- Create: `scripts/analyzer/aggregate_analyzer_metrics_v1.py`
- Test: `tests/analyzer/test_metric_registry.py`
- Test: `tests/analyzer/test_metrics.py`

**Interfaces:**
- Consumes: common `U_reg` manifest, protected-baseline manifest, validated Analyzer artifacts, candidate/result bindings, D0–D4 bindings, cost ledgers, and infrastructure receipts.
- Produces: exact numerator/denominator ledgers, `EVRY_reg`, `EVRY_avail`, failure/protected-cohort Harm, ProposalCoverage, VBP, verification-cost reports, EVRY@B curves, specificity reports, clustered paired intervals, and paper-ready CSV/JSON.

- [ ] **Step 1: Write common-universe and anti-gaming RED tests**

```python
from pchsi.analyzer.metrics import aggregate_repair_discovery


def test_evry_uses_common_registered_universe(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.evry_reg.denominator == len(u_reg)
    assert report.evry_reg.numerator == len(report.unique_benefit_unit_ids)


def test_abstain_invalid_and_nonexecuted_method_failures_remain_in_evry(u_reg, result_rows) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.evry_reg.denominator == len(u_reg)
    assert report.method_failure_count > 0


def test_k1_prevents_candidate_spam(result_rows) -> None:
    by_unit_condition = {}
    for row in result_rows:
        if row.formal_candidate_proposed:
            key = (row.unit_id, row.condition_id)
            by_unit_condition[key] = by_unit_condition.get(key, 0) + 1
    assert max(by_unit_condition.values(), default=1) <= 1
```

- [ ] **Step 2: Write coverage, precision, protected-Harm, and cost RED tests**

```python
def test_vbp_retains_formally_proposed_invalid_candidates(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.vbp.denominator == report.formally_proposed_candidate_count


def test_k1_complete_execution_decomposes_evry(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    if report.execution_complete and report.k_equals_one:
        assert abs(report.evry_reg.value - report.proposal_coverage.value * report.vbp.value) < 1e-12


def test_verification_cost_uses_environment_steps_per_repaired_unique_unit(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.verification_cost.environment_steps == sum(r.formal_verifier_env_steps for r in result_rows)
    assert report.verification_cost.repaired_unit_count == len(report.unique_benefit_unit_ids)


def test_harm_is_separate_for_failure_and_protected_cohorts(failure_rows, protected_rows) -> None:
    report = aggregate_repair_discovery(failure_rows, protected_rows=protected_rows)
    assert report.failure_cohort_harm.denominator == len({r.unit_id for r in failure_rows})
    assert report.protected_cohort_harm.denominator == len({r.unit_id for r in protected_rows})
```

- [ ] **Step 3: Write infrastructure-estimand and EVRY@B RED tests**

```python
def test_operational_and_available_evry_are_both_reported(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.evry_reg.denominator == len(u_reg)
    assert report.evry_avail.denominator == report.protocol_complete_unit_count
    assert sum(report.infrastructure_reason_census.values()) == report.infrastructure_unavailable_count


def test_method_failures_are_not_reclassified_as_infrastructure(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.method_failure_unit_ids.isdisjoint(report.infrastructure_unavailable_unit_ids)


def test_evry_budget_curve_uses_frozen_priority_and_environment_steps(result_rows, u_reg) -> None:
    report = aggregate_repair_discovery(result_rows, registered_universe=u_reg)
    assert report.evry_curve.primary_budget_unit == "FORMAL_VERIFIER_ENVIRONMENT_STEPS"
    assert report.evry_curve.priority_order_frozen_before_outcomes is True
```

Run:

```bash
python -m pytest -q tests/analyzer/test_metric_registry.py tests/analyzer/test_metrics.py
```

Expected: import/missing-interface failure.

- [ ] **Step 4: Encode the audited registry**

Each entry freezes numerator, denominator, unit, missingness, uncertainty, and
claim status. Required entries include `EVRY_reg`, `EVRY_avail`, failure-cohort
Harm, protected-cohort Harm, ProposalCoverage, VBP, verifier environment steps
per repaired unique unit, EVRY@B, all localization/grounding diagnostics, and
secondary specificity-confirmed repair yield. The registry forbids weighted
composite scores and `FIRST_EVER` novelty language.

- [ ] **Step 5: Implement statistics and explicit failure accounting**

Implement task/gamefile-clustered paired bootstrap intervals, Wilson/exact
proportion intervals where applicable, paired binary/McNemar summaries, risk
differences/relative risks, and Holm adjustment for registered secondary
contrasts. Write explicit reason censuses for pre-scientific infrastructure
failures and keep method-side schema/context/evidence/executability failures in
the operational denominator.

Write:

```text
METRIC_DENOMINATOR_AUDIT_V2.json
PROTECTED_BASELINE_HARM_AUDIT_V1.json
EVRY_OPERATIONAL_AND_AVAILABLE_AUDIT_V1.json
EVRY_BUDGET_CURVE_AUDIT_V2.json
SPECIFICITY_COHORT_COVERAGE_AUDIT_V1.json
```

- [ ] **Step 6: Run tests and commit**

```bash
python -m pytest -q tests/analyzer/test_metric_registry.py tests/analyzer/test_metrics.py

git add configs/analyzer/analyzer_metric_registry_v1.json src/pchsi/analyzer/metric_registry.py src/pchsi/analyzer/metrics.py scripts/analyzer/aggregate_analyzer_metrics_v1.py tests/analyzer/test_metric_registry.py tests/analyzer/test_metrics.py
git commit -m "Aggregate audited coverage-aware Analyzer metrics"
```

---

### Task 12: Add deterministic gold-panel tooling

**Files:**
- Create: `scripts/analyzer/materialize_analyzer_gold_panels_v1.py`
- Test: `tests/analyzer/test_gold_panel_materialization.py`

**Interfaces:**
- Consumes: frozen eligible order, outcome census, task-access manifest, evidence completeness receipts.
- Produces: failure gold manifest, success reference manifest, complete eligibility/exclusion census, annotation templates, and double-annotation assignment manifest.

- [ ] **Step 1: Write selection tests**

```python
from pchsi.analyzer.gold_panel import select_gold_panels


def test_selection_is_first_unique_gamefiles_by_frozen_order(eligible_rows) -> None:
    panels = select_gold_panels(eligible_rows)
    assert panels.failure.task_ids == expected_failure_ids
    assert panels.success.task_ids == expected_success_ids


def test_no_gamefile_crosses_panels(eligible_rows) -> None:
    panels = select_gold_panels(eligible_rows)
    assert set(panels.failure.gamefiles).isdisjoint(panels.success.gamefiles)
```

Create `src/pchsi/analyzer/gold_panel.py` if logic cannot remain a thin CLI.

- [ ] **Step 2: Verify RED and implement deterministic selection**

```bash
python -m pytest -q tests/analyzer/test_gold_panel_materialization.py
```

Select 30–36 failures and 12 successes, with family quotas where available; never duplicate to fill a quota. Double-annotation assignment uses a frozen hash rule and targets 20%–25% with at least eight failures when panel size is 36.

- [ ] **Step 3: Commit**

```bash
git add src/pchsi/analyzer/gold_panel.py scripts/analyzer/materialize_analyzer_gold_panels_v1.py tests/analyzer/test_gold_panel_materialization.py
git commit -m "Materialize deterministic Analyzer gold panels"
```

---

### Task 13: Implement the success-quality pilot protocol (secondary, non-blocking)

**Files:**
- Create: `src/pchsi/analyzer/success_optimization.py`
- Create: `scripts/analyzer/run_success_optimization_pilot_v1.py`
- Test: `tests/analyzer/test_success_optimization.py`

**Interfaces:**
- Consumes: 12 frozen successful episodes, best frozen Analyzer condition, at most one projected optimization candidate per episode, and existing same-state continuation infrastructure.
- Produces: registered success pilot cells and labels `SUCCESS_PRESERVED_EFFICIENCY_GAIN`, `SUCCESS_PRESERVED_NO_MEANINGFUL_GAIN`, `SUCCESS_REGRESSION`, or `SUCCESS_EFFECT_UNCERTAIN`.

- [ ] **Step 1: Write label tests**

```python
from pchsi.analyzer.success_optimization import label_success_effect


def test_success_preserved_with_lower_cost_is_gain() -> None:
    assert label_success_effect(f0_success=True, f1_success=True, f0_steps=20, f1_steps=15) == "SUCCESS_PRESERVED_EFFICIENCY_GAIN"


def test_lost_success_is_regression() -> None:
    assert label_success_effect(f0_success=True, f1_success=False, f0_steps=20, f1_steps=12) == "SUCCESS_REGRESSION"
```

- [ ] **Step 2: Verify RED**

```bash
python -m pytest -q tests/analyzer/test_success_optimization.py
```

- [ ] **Step 3: Implement registration and labeling only**

The runner remains execution-closed. Live Task 13 execution is `SECONDARY_NON_BLOCKING` and requires a separate approval; it cannot block the first formal A0–A3 run. It reuses the F0/F1 branch machinery and writes distinct success-effect artifacts. Analyzer redundancy candidates never bypass environment testing.

- [ ] **Step 4: Add metrics**

Report success-preservation rate, verified efficiency-gain rate, success-regression rate, steps/calls/tokens/latency saved, cost per verified gain, and candidate abstention/invalid counts.

- [ ] **Step 5: Commit**

```bash
git add src/pchsi/analyzer/success_optimization.py scripts/analyzer/run_success_optimization_pilot_v1.py tests/analyzer/test_success_optimization.py
git commit -m "Add success-preserving optimization pilot"
```

---

### Task 14: Implement repair-effect decomposition D0–D4 (post-Benefit secondary)

**Files:**
- Create: `src/pchsi/analyzer/repair_decomposition.py`
- Create: `scripts/analyzer/run_repair_effect_decomposition_v1.py`
- Test: `tests/analyzer/test_repair_decomposition.py`

**Interfaces:**
- Consumes: only after at least six formal Benefits exist, 8–12 mechanically selected formal Benefit candidates and existing same-state branch infrastructure.
- Produces: registered D0–D4 cells, `RepairEffectDecompositionTraceV1`, and `RepairEffectDecompositionResultV1`; paper-facing output is a secondary specificity-confirmed subset of EVRY.

- [ ] **Step 1: Write prefix/control/history RED tests**

```python
from pchsi.analyzer.repair_decomposition import build_decomposition_cells


def test_option_registers_every_tested_prefix(three_action_benefit) -> None:
    cells = build_decomposition_cells(three_action_benefit)
    assert [c.prefix_length for c in cells if c.condition == "D2_TESTED_PREFIX"] == [1, 2, 3]


def test_minimal_language_requires_all_shorter_prefixes_definitively_nonbenefit(prefix_results) -> None:
    prefix_results[1].outcome = "Uncertain"
    assert prefix_results.classification() != "MINIMAL_SUFFICIENT_PREFIX"
    assert prefix_results.display_name() == "SHORTEST_TESTED_SUFFICIENT_PREFIX"


def test_matched_control_is_selected_before_outcome(control_menu, frozen_rule) -> None:
    cells_a = build_decomposition_cells(control_menu, frozen_rule)
    control_menu["outcomes"] = {"candidate": "Benefit"}
    cells_b = build_decomposition_cells(control_menu, frozen_rule)
    assert cells_a.matched_control == cells_b.matched_control


def test_history_attenuation_preserves_post_state(d1_result, d4_result) -> None:
    assert d1_result.post_state_sha256 == d4_result.post_state_sha256
    assert d1_result.visible_history_sha256 != d4_result.visible_history_sha256
```

- [ ] **Step 2: Write D3 matching and training-boundary RED tests**

D3 registry rejects a control unless it matches action count, admissibility,
environment-step budget, novelty class, observation opportunities, and
option-termination budget. A D1 formal Benefit remains eligible for verified
training consideration even when specificity is unresolved or fails.

Run:

```bash
python -m pytest -q tests/analyzer/test_repair_decomposition.py
```

Expected: import/missing-interface failure.

- [ ] **Step 3: Implement mechanical cohort and control registration**

If more than 12 Benefits are eligible, sort by candidate SHA and take the first
12. Fewer than six sets `claim_scope=CASE_STUDY_ONLY`. D3 controls use frozen
menu/order rules and cannot inspect outcomes.

- [ ] **Step 4: Implement bounded mechanism labels and claim language**

```text
SPECIFIC_SINGLE_ACTION_EFFECT
MINIMAL_PREFIX_EFFECT              # only if all shorter prefixes definitively fail
SHORTEST_TESTED_PREFIX_EFFECT      # otherwise
COMPOSITIONAL_OPTION_EFFECT
HISTORY_CONTEXT_DEPENDENT
NONSPECIFIC_PERTURBATION_EFFECT
BUDGET_OR_EXTRA_OBSERVATION_CONFOUNDED
UNRESOLVED_MULTI_CHANNEL_EFFECT
```

Live D0–D4 execution is `POST_BENEFIT_SECONDARY` and cannot block the first A0–A3/F0–F1 run. Do not claim full causal mediation. D3 supports specificity only relative to the
registered matched controls. D4 remains separate.

- [ ] **Step 5: Commit**

```bash
git add src/pchsi/analyzer/repair_decomposition.py scripts/analyzer/run_repair_effect_decomposition_v1.py tests/analyzer/test_repair_decomposition.py
git commit -m "Decompose verified Analyzer repair effects"
```

---

### Task 15: Integrate A0–A3 registry, common repair budget, and execution dedup

**Files:**
- Modify: `configs/analyzer/analyzer_a0_a3_experiment_contract_v1.json`
- Modify: `configs/analyzer/hierarchical_analyzer_v2_contract_v1.json`
- Create: `src/pchsi/analyzer/experiment_registry.py`
- Test: `tests/analyzer/test_experiment_registry.py`

**Interfaces:**
- Consumes: common preregistered `U_reg`, frozen panel manifests, A0/A1 raw local calls, A1 result hashes, A2/A3 group runs, projected candidates, protected-baseline manifest, and execution-result bindings.
- Produces: `AnalyzerExperimentRegistryV1` proving common-universe identity, K=1 candidate-or-ABSTAIN, fair computation reuse, no Memory leakage, equal repair budgets, protected safety-cohort separation, and duplicate execution sharing.

- [ ] **Step 1: Write registry tests**

```python
from pchsi.analyzer.experiment_registry import validate_registry


def test_a2_a3_bind_exact_same_a1_local_results(valid_registry) -> None:
    validate_registry(valid_registry)
    assert valid_registry.a2.local_result_sha256s == valid_registry.a3.local_result_sha256s


def test_a3_memory_does_not_change_common_evidence(valid_registry) -> None:
    assert valid_registry.a2.common_evidence_pack_sha256s == valid_registry.a3.common_evidence_pack_sha256s


def test_all_conditions_bind_same_registered_universe(valid_registry) -> None:
    assert valid_registry.a0.registered_universe_sha256 == valid_registry.a1.registered_universe_sha256 == valid_registry.a2.registered_universe_sha256 == valid_registry.a3.registered_universe_sha256


def test_k1_candidate_or_abstain_per_unit(valid_registry) -> None:
    assert valid_registry.max_formal_candidate_count_per_unit == 1


def test_duplicate_candidates_share_execution_not_discovery_record(valid_registry) -> None:
    duplicate_rows = valid_registry.duplicate_candidate_rows()
    assert len({row.execution_result_sha256 for row in duplicate_rows}) == 1
    assert len({row.discovery_record_sha256 for row in duplicate_rows}) == len(duplicate_rows)
```

- [ ] **Step 2: Verify RED and implement**

```bash
python -m pytest -q tests/analyzer/test_experiment_registry.py
```

- [ ] **Step 3: Freeze source-conditioned proposal fairness**

A2/A3 use the already registered G-stage source-conditioned repair field and do
not receive an extra proposal call. Registry rejects abstract templates that
project to executable actions, byte rewriting by C/P/X, or unequal model-call
counts hidden as projection.

- [ ] **Step 4: Freeze primitive/option stratification and budgets**

The registry records maximum repair actions, actual intervention actions, observations acquired, and total environment budget for every condition. It rejects Analyzer prose in Task Policy inputs.

- [ ] **Step 5: Commit**

```bash
git add configs/analyzer/analyzer_a0_a3_experiment_contract_v1.json configs/analyzer/hierarchical_analyzer_v2_contract_v1.json src/pchsi/analyzer/experiment_registry.py tests/analyzer/test_experiment_registry.py
git commit -m "Harden A0-A3 Analyzer experiment attribution"
```

---

### Task 16: Add static scientific audits, documentation, and deterministic-infrastructure closure

**Files:**
- Create: `scripts/analyzer/audit_outcome_aware_analyzer_v2.py`
- Create: `docs/audits/OUTCOME_AWARE_HIERARCHICAL_ANALYZER_V2_CODE_REVIEW.md`
- Modify: Analyzer design/output/pilot/gold docs and `docs/code_map.md`
- Test: `tests/analyzer/test_static_scientific_audit.py`

**Interfaces:**
- Consumes: all Tasks 1–15 artifacts and frozen review disposition.
- Produces: a fixed-head deterministic scientific-infrastructure code-review
  bundle and runtime-activation handoff; still no model/environment authorization.

- [ ] **Step 1: Write static scientific audit RED tests**

The audit rejects Analyzer effect/promotion authority, infrastructure→failure
coercion, online-policy privileged outcome fields, Memory in the local pass,
model-selected sampling regime, scheduler mutation of `U_reg`, episode-single-
onset grouping, semantic component inference in the deterministic aggregator,
projector action invention/rewriting, unequal A2/A3 proposal calls, fuzzy/menu
normalization, silent outcome deletion, and Researcher targets fabricated from
Analyzer artifacts.

- [ ] **Step 2: Audit Task 13/14 execution roles**

Assert:

```text
TASK13_LIVE_EXECUTION_ROLE = SECONDARY_NON_BLOCKING
TASK14_LIVE_EXECUTION_ROLE = POST_BENEFIT_SECONDARY
```

Their implementation may be complete while live execution remains unapproved.

- [ ] **Step 3: Run focused, native, and full regression checks**

```bash
make -C native/s1_backend_probe clean all unit
python -m pytest -q tests/analyzer
python -m pytest -q
python -m compileall -q src scripts tests
python scripts/analyzer/audit_outcome_aware_analyzer_v2.py --repo-root .
```

Do not weaken or skip existing security tests.

- [ ] **Step 4: Perform fixed-head scope and source-of-truth audit**

Confirm one metric registry, exact H1–H7 markers, content-addressed error-instance
memberships, explicit C-stage producer, source-conditioned proposal bytes,
`RepairEffectDecompositionTraceV1`, Human/API Researcher record dependency, and
no Runtime Core/Memory/evaluator/trainer rewrite beyond planned compatibility.

- [ ] **Step 5: Commit deterministic infrastructure closure**

```bash
git add scripts/analyzer docs/analyzer docs/audits/OUTCOME_AWARE_HIERARCHICAL_ANALYZER_V2_CODE_REVIEW.md docs/code_map.md tests/analyzer/test_static_scientific_audit.py
git commit -m "Close Analyzer V2 deterministic scientific infrastructure"
```

- [ ] **Step 6: Push and stop at the runtime activation gate**

```bash
git push --porcelain origin HEAD
git fetch origin "$(git branch --show-current)"
test "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$(git branch --show-current)")"
```

Final state:

```text
ANALYZER_DETERMINISTIC_SCIENTIFIC_INFRASTRUCTURE_CODE_APPROVED = candidate_for_human_review
FORMAL_ANALYZER_EXECUTION_AUTHORIZED = false
ANALYZER_MODEL_CALLS_AUTHORIZED = false
ENVIRONMENT_EXECUTION_AUTHORIZED = false
POLICY_TRAINING_AUTHORIZED = false
IMPLEMENTATION_MERGED_TO_MAIN = false
NEXT_GATE = ANALYZER_V2_STRONG_MODEL_RUNTIME_ACTIVATION_V1
```

---

