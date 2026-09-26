"""Strict read-only validation of existing five-file attempt bundles."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import (
    ensure_directory_no_symlink,
    ensure_regular_no_symlink,
    sha256_file,
    strict_json_loads,
)
from .types import (
    BudgetCounters,
    NormalizedPolicyCall,
    NormalizedTrace,
    NormalizedTransition,
    ValidatedAttemptBundle,
)


_REQUIRED_PAYLOAD_FILES = (
    "attempt.json",
    "action_traces.jsonl",
    "policy_calls.jsonl",
    "public_transitions.jsonl",
)
_REQUIRED_FILES = (*_REQUIRED_PAYLOAD_FILES, "SHA256SUMS")


def _parse_checksum_manifest(path: Path) -> tuple[tuple[str, str], ...]:
    source = ensure_regular_no_symlink(path, name="attempt SHA256SUMS")
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(
        source.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if not line or "  " not in line:
            raise ValueError(
                f"invalid SHA256SUMS line {line_number}: {line!r}"
            )
        digest, name = line.split("  ", 1)
        if (
            len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or name in seen
            or "/" in name
            or name not in _REQUIRED_PAYLOAD_FILES
        ):
            raise ValueError(
                f"invalid SHA256SUMS row {line_number}: {line!r}"
            )
        seen.add(name)
        rows.append((name, digest))
    if tuple(name for name, _ in rows) != _REQUIRED_PAYLOAD_FILES:
        raise ValueError(
            "SHA256SUMS must list the four payload files in frozen order"
        )
    return tuple(rows)


def _jsonl_lines(path: Path) -> tuple[bytes, ...]:
    source = ensure_regular_no_symlink(path, name=path.name)
    raw = source.read_bytes()
    if not raw:
        return ()
    lines = raw.splitlines(keepends=True)
    if any(not line.endswith(b"\n") or line == b"\n" for line in lines):
        raise ValueError(f"{path.name} must be nonblank newline-terminated JSONL")
    return tuple(line[:-1] for line in lines)


def _load_action_trace(value: dict[str, object]):
    from pchsi.evaluation.action_trace import (
        ActionStage,
        ActionTrace,
        TraceProvenance,
    )

    provenance_raw = value.get("provenance")
    if not isinstance(provenance_raw, dict):
        raise TypeError("ActionTrace provenance must be object")
    provenance = TraceProvenance(**provenance_raw)

    raw_stages = value.get("stages")
    if not isinstance(raw_stages, list):
        raise TypeError("ActionTrace stages must be array")
    stages = tuple(
        ActionStage.build(
            name=item["name"],
            status=item["status"],
            input_action=item["input_action"],
            output_action=item["output_action"],
            metadata=item["metadata"],
        )
        for item in raw_stages
        if isinstance(item, dict)
    )
    if len(stages) != len(raw_stages):
        raise TypeError("ActionTrace stage must be object")

    trace = ActionTrace.build(
        provenance=provenance,
        pipeline_variant=value["pipeline_variant"],
        model_call_index=value["model_call_index"],
        environment_step_index=value["environment_step_index"],
        execution_status=value["execution_status"],
        public_task_goal=value["public_task_goal"],
        observation=value["observation"],
        prompt_text=value["prompt_text"],
        admissible_commands=value["admissible_commands"],
        raw_model_response=value["raw_model_response"],
        literal_action=value["literal_action"],
        parsed_phase=value["parsed_phase"],
        model_reason=value["model_reason"],
        parser_status=value["parser_status"],
        parser_error=value["parser_error"],
        parser_metadata=value["parser_metadata"],
        literal_action_exactly_admissible=(
            value["literal_action_exactly_admissible"]
        ),
        literal_action_casefold_admissible=(
            value["literal_action_casefold_admissible"]
        ),
        stages=stages,
        final_executed_action=value["final_executed_action"],
        final_action_admissible=value["final_action_admissible"],
        attempt_outcome=value.get("attempt_outcome"),
        failure_stage=value.get("failure_stage"),
        failure_code=value.get("failure_code"),
        normalized_action=value.get("normalized_action"),
        admissibility_status=value.get("admissibility_status"),
        feedback_code=value.get("feedback_code"),
        policy_attempt_count_before=value.get(
            "policy_attempt_count_before"
        ),
        policy_attempt_count_after=value.get(
            "policy_attempt_count_after"
        ),
        environment_step_count_before=value.get(
            "environment_step_count_before"
        ),
        environment_step_count_after=value.get(
            "environment_step_count_after"
        ),
        protocol_failure_count=value.get("protocol_failure_count"),
        inadmissible_action_count=value.get("inadmissible_action_count"),
        consecutive_nonexecuted_attempt_count=value.get(
            "consecutive_nonexecuted_attempt_count"
        ),
        episode_termination_reason=value.get(
            "episode_termination_reason"
        ),
        submitted_environment_action=value.get(
            "submitted_environment_action"
        ),
        resulting_observation=value.get("resulting_observation"),
        environment_event_flags=value.get("environment_event_flags"),
        protocol_failure_count_before=value.get(
            "protocol_failure_count_before"
        ),
        inadmissible_action_count_before=value.get(
            "inadmissible_action_count_before"
        ),
        consecutive_nonexecuted_attempt_count_before=value.get(
            "consecutive_nonexecuted_attempt_count_before"
        ),
    )
    if trace.to_dict() != value:
        raise ValueError("ActionTrace roundtrip differs from source bytes")
    return trace


def _normalize_policy_call(obj) -> NormalizedPolicyCall:
    return NormalizedPolicyCall(
        model_call_index=obj.model_call_index,
        environment_step_count_before=(
            obj.environment_step_count_before
        ),
        provider_request_id=obj.provider_request_id,
        public_task_goal=obj.public_task_goal,
        prompt_text=obj.prompt_text,
        observation=obj.observation,
        admissible_commands=tuple(obj.admissible_commands),
        raw_response_text=obj.raw_response_text,
        executed_history=tuple(obj.executed_history),
        budget_before=BudgetCounters.from_mapping(
            dict(obj.budget_before)
        ),
    )


def _normalize_trace(obj) -> NormalizedTrace:
    before = BudgetCounters(
        policy_attempt_count=int(obj.policy_attempt_count_before),
        environment_step_count=int(
            obj.environment_step_count_before
        ),
        protocol_failure_count=int(
            obj.protocol_failure_count_before
        ),
        inadmissible_action_count=int(
            obj.inadmissible_action_count_before
        ),
        consecutive_nonexecuted_attempt_count=int(
            obj.consecutive_nonexecuted_attempt_count_before
        ),
    )
    after = BudgetCounters(
        policy_attempt_count=int(obj.policy_attempt_count_after),
        environment_step_count=int(
            obj.environment_step_count_after
        ),
        protocol_failure_count=int(obj.protocol_failure_count),
        inadmissible_action_count=int(obj.inadmissible_action_count),
        consecutive_nonexecuted_attempt_count=int(
            obj.consecutive_nonexecuted_attempt_count
        ),
    )
    return NormalizedTrace(
        model_call_index=obj.model_call_index,
        environment_step_index=obj.environment_step_index,
        execution_status=obj.execution_status.value,
        public_task_goal=obj.public_task_goal,
        observation=obj.observation,
        prompt_text=obj.prompt_text,
        admissible_commands=tuple(obj.admissible_commands),
        raw_model_response=obj.raw_model_response,
        literal_action=obj.literal_action,
        normalized_action=obj.normalized_action,
        parser_status=obj.parser_status,
        parser_error=obj.parser_error,
        attempt_outcome=obj.attempt_outcome,
        failure_stage=obj.failure_stage,
        failure_code=obj.failure_code,
        submitted_environment_action=obj.submitted_environment_action,
        final_executed_action=obj.final_executed_action,
        resulting_observation=obj.resulting_observation,
        episode_termination_reason=obj.episode_termination_reason,
        budget_before=before,
        budget_after=after,
        provenance=obj.provenance.to_dict(),
    )


def _normalize_transition(obj) -> NormalizedTransition:
    return NormalizedTransition(
        scheduled_cell_id=obj.scheduled_cell_id,
        execution_attempt_id=obj.execution_attempt_id,
        model_call_index=obj.model_call_index,
        environment_step_index=obj.environment_step_index,
        submitted_action=obj.submitted_action,
        pre_observation=obj.pre_action_observation,
        pre_menu=tuple(obj.pre_action_admissible_commands),
        resulting_observation=obj.resulting_observation,
        resulting_menu=tuple(obj.resulting_admissible_commands),
        done=obj.done,
        won=obj.won,
        score=obj.score,
    )


def _validate_alignment(
    *,
    episode: dict[str, object],
    policy_calls: tuple[NormalizedPolicyCall, ...],
    traces: tuple[NormalizedTrace, ...],
    transitions: tuple[NormalizedTransition, ...],
) -> dict[str, int | str | bool]:
    if not traces:
        raise ValueError("formal Analyzer bundle must contain at least one call")
    expected_indices = tuple(range(len(traces)))
    if tuple(item.model_call_index for item in traces) != expected_indices:
        raise ValueError("ActionTrace model-call indices are not contiguous")
    if tuple(item.model_call_index for item in policy_calls) != expected_indices:
        raise ValueError("policy-call indices are not contiguous")

    transition_by_model: dict[int, NormalizedTransition] = {}
    transition_steps: list[int] = []
    for transition in transitions:
        if transition.model_call_index in transition_by_model:
            raise ValueError("multiple transitions bind one model call")
        transition_by_model[transition.model_call_index] = transition
        transition_steps.append(transition.environment_step_index)
    if transition_steps != sorted(transition_steps) or len(
        transition_steps
    ) != len(set(transition_steps)):
        raise ValueError("transition indices are not unique increasing")

    expected_observation = traces[0].observation
    expected_menu = traces[0].admissible_commands
    executed_history: list[tuple[str, str]] = []
    executed_trace_count = 0
    environment_error_count = 0

    for index, (call, trace) in enumerate(zip(policy_calls, traces)):
        if call.model_call_index != trace.model_call_index:
            raise ValueError("policy/trace model-call index mismatch")
        if call.public_task_goal != trace.public_task_goal:
            raise ValueError("policy/trace goal mismatch")
        if call.prompt_text != trace.prompt_text:
            raise ValueError("policy/trace prompt mismatch")
        if call.observation != trace.observation:
            raise ValueError("policy/trace observation mismatch")
        if call.admissible_commands != trace.admissible_commands:
            raise ValueError("policy/trace menu mismatch")
        if call.raw_response_text != trace.raw_model_response:
            raise ValueError("policy/trace raw response mismatch")
        if call.budget_before != trace.budget_before:
            raise ValueError("policy/trace budget-before mismatch")
        if call.executed_history != tuple(executed_history):
            raise ValueError(
                "policy-call executed history differs from prior transitions"
            )
        if trace.observation != expected_observation:
            raise ValueError("call observation breaks transition continuity")
        if trace.admissible_commands != expected_menu:
            raise ValueError("call menu breaks transition continuity")

        if index > 0 and traces[index - 1].budget_after != trace.budget_before:
            raise ValueError("budget continuity between model calls failed")

        transition = transition_by_model.get(index)
        if trace.execution_status == "executed":
            if transition is None:
                raise ValueError("executed trace lacks public transition")
            if trace.environment_step_index != transition.environment_step_index:
                raise ValueError("trace/transition environment index mismatch")
            if (
                trace.submitted_environment_action
                != transition.submitted_action
            ):
                raise ValueError("trace/transition action mismatch")
            if transition.pre_observation != expected_observation:
                raise ValueError("transition pre-observation mismatch")
            if transition.pre_menu != expected_menu:
                raise ValueError("transition pre-menu mismatch")
            if trace.resulting_observation != transition.resulting_observation:
                raise ValueError("trace/transition result mismatch")
            executed_history.append(
                (
                    transition.submitted_action,
                    transition.resulting_observation,
                )
            )
            expected_observation = transition.resulting_observation
            expected_menu = transition.resulting_menu
            executed_trace_count += 1
            if transition.done and index != len(traces) - 1:
                raise ValueError("policy calls continue after done transition")
        elif trace.execution_status == "environment_error":
            if transition is not None:
                raise ValueError("environment error cannot have public transition")
            environment_error_count += 1
        else:
            if transition is not None:
                raise ValueError("nonexecuted trace cannot have public transition")

    if int(episode["trace_count"]) != len(traces):
        raise ValueError("episode trace count mismatch")
    if int(episode["public_transition_count"]) != len(transitions):
        raise ValueError("episode transition count mismatch")
    if int(episode["environment_call_trace_count"]) != (
        executed_trace_count + environment_error_count
    ):
        raise ValueError("episode environment-call count mismatch")

    from pchsi.evaluation.canonical_evidence import sha256_text

    if episode["initial_observation_sha256"] != sha256_text(
        traces[0].observation
    ):
        raise ValueError("episode initial-observation hash mismatch")
    if episode["final_observation_sha256"] != sha256_text(
        expected_observation
    ):
        raise ValueError("episode final-observation hash mismatch")

    final_budget = episode["final_budget"]
    if not isinstance(final_budget, dict):
        raise TypeError("episode final_budget must be object")
    if BudgetCounters.from_mapping(final_budget) != traces[-1].budget_after:
        raise ValueError("episode final budget differs from final trace")

    return {
        "policy_call_count": len(policy_calls),
        "action_trace_count": len(traces),
        "public_transition_count": len(transitions),
        "executed_trace_count": executed_trace_count,
        "environment_error_trace_count": environment_error_count,
        "nonexecuted_trace_count": (
            len(traces) - executed_trace_count - environment_error_count
        ),
        "model_call_indices_contiguous": True,
        "transition_indices_unique_increasing": True,
        "history_continuity_valid": True,
        "budget_continuity_valid": True,
        "observation_menu_continuity_valid": True,
        "status": "VALIDATED",
    }


def validate_attempt_bundle(bundle_root: Path) -> ValidatedAttemptBundle:
    root = ensure_directory_no_symlink(
        bundle_root, name="attempt bundle root"
    )
    observed = {
        item.name
        for item in root.iterdir()
        if item.is_file() or item.is_symlink()
    }
    if observed != set(_REQUIRED_FILES):
        raise ValueError(
            "formal Analyzer attempt bundle must contain exactly five files: "
            f"observed={sorted(observed)}"
        )

    checks = _parse_checksum_manifest(root / "SHA256SUMS")
    for name, expected in checks:
        source = ensure_regular_no_symlink(
            root / name, name=f"attempt bundle file {name}"
        )
        observed_sha = sha256_file(source)
        if observed_sha != expected:
            raise ValueError(
                f"attempt bundle SHA mismatch for {name}: "
                f"expected={expected}, observed={observed_sha}"
            )

    from pchsi.evaluation.episode_artifact import (
        build_attempt_bundle_bytes,
    )
    from pchsi.evaluation.policy_call_evidence import (
        PolicyCallEvidenceV1,
    )
    from pchsi.evaluation.schema_models import (
        EpisodeArtifactV1,
        PublicTransitionRecordV1,
    )
    from pchsi.evaluation.trace_assembler import (
        validate_policy_call_trace_alignment,
    )

    attempt_raw = (root / "attempt.json").read_bytes()
    episode_obj = EpisodeArtifactV1.from_json(attempt_raw)
    if episode_obj.to_json().encode("utf-8") != attempt_raw:
        raise ValueError("attempt.json is not exact canonical EpisodeArtifactV1")

    trace_objs = []
    for raw in _jsonl_lines(root / "action_traces.jsonl"):
        value = strict_json_loads(raw)
        if not isinstance(value, dict):
            raise TypeError("ActionTrace JSONL row must be object")
        obj = _load_action_trace(value)
        if obj.to_json().encode("utf-8") != raw:
            raise ValueError("ActionTrace JSONL row is not exact canonical")
        trace_objs.append(obj)

    call_objs = []
    for raw in _jsonl_lines(root / "policy_calls.jsonl"):
        obj = PolicyCallEvidenceV1.from_json(raw)
        if obj.to_json().rstrip("\n").encode("utf-8") != raw:
            raise ValueError("policy-call JSONL row is not exact canonical")
        call_objs.append(obj)

    transition_objs = []
    for raw in _jsonl_lines(root / "public_transitions.jsonl"):
        obj = PublicTransitionRecordV1.from_json(raw)
        if obj.to_json().rstrip("\n").encode("utf-8") != raw:
            raise ValueError("public transition row is not exact canonical")
        transition_objs.append(obj)

    if len(call_objs) != len(trace_objs):
        raise ValueError("policy-call count must equal ActionTrace count")
    for evidence, trace in zip(call_objs, trace_objs):
        validate_policy_call_trace_alignment(
            evidence=evidence,
            trace=trace,
        )

    rebuilt = build_attempt_bundle_bytes(
        episode_artifact=episode_obj,
        traces=tuple(trace_objs),
        policy_calls=tuple(call_objs),
        public_transitions=tuple(transition_objs),
    )
    for name, expected_raw in rebuilt.file_bytes():
        source_raw = (root / name).read_bytes()
        if source_raw != expected_raw:
            raise ValueError(
                f"attempt bundle exact-byte recomputation differs: {name}"
            )

    normalized_calls = tuple(
        _normalize_policy_call(item) for item in call_objs
    )
    normalized_traces = tuple(_normalize_trace(item) for item in trace_objs)
    normalized_transitions = tuple(
        _normalize_transition(item) for item in transition_objs
    )
    episode = episode_obj.to_dict()
    census = _validate_alignment(
        episode=episode,
        policy_calls=normalized_calls,
        traces=normalized_traces,
        transitions=normalized_transitions,
    )
    source_shas = tuple(
        (name, sha256_file(root / name))
        for name in _REQUIRED_FILES
    )
    return ValidatedAttemptBundle(
        bundle_root=root,
        episode=episode,
        policy_calls=normalized_calls,
        traces=normalized_traces,
        transitions=normalized_transitions,
        source_file_sha256s=source_shas,
        episode_semantic_sha256=rebuilt.episode_semantic_sha256,
        attempt_bundle_sha256=rebuilt.attempt_bundle_sha256,
        alignment_census=census,
    )
