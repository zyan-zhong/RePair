#!/usr/bin/env python3
"""Execute exactly one Formal-A A0 scientific cell.

Committed for review only. Real execution requires explicit human approval plus a
separately frozen runtime binding.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_adapter import (
    SpawnedAlfworldAdapter,
    WorkerAdapterError,
)
from pchsi.evaluation.budget import BudgetLimits
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_text,
    strict_json_loads,
)
from pchsi.evaluation.policy_call_evidence import build_policy_call_evidence
from pchsi.evaluation.policy_client import (
    HttpPolicyTransport,
    PolicyClient,
    PolicyTransportError,
    PromptTokenMismatchError,
)
from pchsi.evaluation.policy_execution_profile import PolicyExecutionProfileV1
from pchsi.evaluation.policy_response import PolicyResponseError
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
)
from pchsi.evaluation.rendered_prompt import (
    HuggingFaceTokenizerFactory,
    LocalTokenizerPromptRenderer,
)
from pchsi.evaluation.runtime_core import finalize_environment_result
from pchsi.memory.a0_formal_execution import (
    A0CellResultV1,
    A0ContinuationTransitionV1,
    A0FrozenCellExecutionIdentityV1,
    A0PromptCensusRecordV1,
    validate_a0_manifest_binding_top_level_v1,
    validate_runtime_representation_binding_v1,
)
from pchsi.memory.a0_replay_session import (
    replay_source_decision_state_hold_open_v1,
)
from pchsi.memory.memory_runtime_bridge import (
    prepare_memory_policy_attempt_v1,
    process_memory_policy_generation_v1,
)
from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1


APPROVAL = "PACKAGE_A0_LOCAL_MECHANISM_EXECUTION_APPROVED"
EXPECTED_MODEL = "P4-R1-Q2-BAD-TRAIN17"
EXPECTED_RUNTIME_SHA = (
    "215bbe3981668181c8b2eb51c4568af944512f7c20c4504ad75faa012cc83faa"
)
EXPECTED_SNAPSHOT = (
    "8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189"
)
EXPECTED_TOKEN = (
    "613166c9f092795cb03c892ee0046f0af5bf7fc13ba44f7fccb950027c329262"
)
MAX_GENERATION = 128


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _task_goal(reset_observation: str) -> str:
    prefix = "Your task is to:"
    for line in reset_observation.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if value:
                return value
    raise ValueError("public task goal parser contract failure")


def _budget_payload(value):
    return {
        "policy_attempt_count": value.policy_attempt_count,
        "environment_step_count": value.environment_step_count,
        "protocol_failure_count": value.protocol_failure_count,
        "inadmissible_action_count": value.inadmissible_action_count,
        "consecutive_nonexecuted_attempt_count": (
            value.consecutive_nonexecuted_attempt_count
        ),
    }


def _budget_sha(value) -> str:
    return hashlib.sha256(
        canonical_json_bytes(_budget_payload(value))
    ).hexdigest()


def _load_runtime(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("runtime binding must be a regular non-symlink file")
    payload = strict_json_loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("runtime binding must be object")
    required = {
        "schema_id",
        "schema_version",
        "served_model_name",
        "policy_runtime_manifest_sha256",
        "decoding_contract_sha256",
        "policy_base_url",
        "base_model_local_path",
        "tokenizer_revision",
        "chat_template_sha256",
        "context_window_tokens",
        "vllm_version",
        "scientific_execution_authorized",
    }
    if set(payload) != required:
        raise ValueError("runtime binding fields mismatch")
    if (
        payload["schema_id"] != "FORMAL_A0_RUNTIME_BINDING_V1"
        or payload["schema_version"] != 1
    ):
        raise ValueError("runtime binding schema mismatch")
    if payload["served_model_name"] != EXPECTED_MODEL:
        raise ValueError("served model mismatch")
    if payload["policy_runtime_manifest_sha256"] != EXPECTED_RUNTIME_SHA:
        raise ValueError("policy runtime SHA mismatch")
    if payload["vllm_version"] != "0.11.0":
        raise ValueError("vLLM version mismatch")
    if payload["scientific_execution_authorized"] is not False:
        raise ValueError("runtime binding cannot self-authorize execution")
    if (
        type(payload["context_window_tokens"]) is not int
        or payload["context_window_tokens"] <= MAX_GENERATION
    ):
        raise ValueError("context window invalid")
    return payload


def _failure_payload(
    *,
    kind: str,
    cell_index: int,
    cell_id: str,
    attempt_index: int,
    identity_sha: str,
    error: BaseException,
    scientific_execution_started: bool,
    exact_retry: bool,
    failure_stage: str,
):
    return {
        "schema_id": kind,
        "schema_version": 1,
        "cell_index": cell_index,
        "cell_id": cell_id,
        "attempt_index": attempt_index,
        "execution_identity_sha256": identity_sha,
        "failure_type": type(error).__name__,
        "failure_stage": failure_stage,
        "scientific_execution_started": scientific_execution_started,
        "scientific_outcome_produced": False,
        "retry_exact_same_frozen_cell": exact_retry,
    }


def _write_ambiguity(
    *,
    out: Path,
    args,
    cell,
    identity,
    error: BaseException,
    failure_stage: str,
) -> int:
    payload = _failure_payload(
        kind="FORMAL_A0_POST_EXECUTION_INFRASTRUCTURE_AMBIGUITY_V1",
        cell_index=args.cell_index,
        cell_id=cell["cell_id"],
        attempt_index=args.attempt_index,
        identity_sha=identity.execution_identity_sha256,
        error=error,
        scientific_execution_started=True,
        exact_retry=False,
        failure_stage=failure_stage,
    )
    _write_once(
        out / "post_execution_ambiguity.json",
        canonical_json_bytes(payload),
    )
    print("FORMAL_A0_POST_EXECUTION_AMBIGUITY_NO_AUTO_RETRY")
    return 76


def main() -> int:
    if os.environ.get("PACKAGE_A0_SCIENTIFIC_EXECUTION_APPROVAL") != APPROVAL:
        raise SystemExit("STOP=FORMAL_A0_SCIENTIFIC_EXECUTION_APPROVAL_MISSING")

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--input-binding", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--cell-index", type=int, required=True)
    parser.add_argument("--attempt-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if args.attempt_index < 0:
        raise SystemExit("STOP=FORMAL_A0_ATTEMPT_INDEX_INVALID")

    manifest_path = Path(args.manifest)
    binding_path = Path(args.input_binding)
    for path in (manifest_path, binding_path):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("STOP=FORMAL_A0_MANIFEST_OR_BINDING_PATH_INVALID")

    manifest = strict_json_loads(manifest_path.read_bytes())
    binding = strict_json_loads(binding_path.read_bytes())
    runtime = _load_runtime(Path(args.runtime_binding))
    validate_a0_manifest_binding_top_level_v1(
        manifest=manifest,
        binding=binding,
    )

    cells = manifest["cells"]
    if args.cell_index not in range(12):
        raise SystemExit("STOP=FORMAL_A0_CELL_INDEX_INVALID")
    cell = cells[args.cell_index]

    if cell["scientific_execution_authorized"] is not False:
        raise SystemExit("STOP=MANIFEST_CELL_SELF_AUTHORIZED")
    if cell["snapshot_sha256"] != EXPECTED_SNAPSHOT:
        raise SystemExit("STOP=CELL_SNAPSHOT_MISMATCH")

    source_rows = [
        item
        for item in binding["sources"]
        if item["source_state_id"] == cell["source_state_id"]
    ]
    if len(source_rows) != 1:
        raise SystemExit("STOP=CELL_SOURCE_BINDING_COUNT_MISMATCH")
    row = source_rows[0]

    source_path = Path(row["replay_source_path"])
    if source_path.is_symlink() or not source_path.is_file():
        raise SystemExit("STOP=REPLAY_SOURCE_PATH_INVALID")
    source_raw = source_path.read_bytes()
    if hashlib.sha256(source_raw).hexdigest() != row["replay_source_sha256"]:
        raise SystemExit("STOP=REPLAY_SOURCE_SHA_MISMATCH")
    source = RegisteredReplaySourceV1.from_json(source_raw)
    if source.canonical_bytes() != source_raw:
        raise SystemExit("STOP=REPLAY_SOURCE_NOT_CANONICAL")
    if (
        source.expected_source_fingerprint.fingerprint_sha256
        != cell["source_state_id"]
    ):
        raise SystemExit("STOP=REPLAY_SOURCE_STATE_ID_MISMATCH")
    if source.source_task_id != cell["source_task_id"]:
        raise SystemExit("STOP=REPLAY_SOURCE_TASK_ID_MISMATCH")
    if source.source_bundle_sha256 != cell["source_bundle_sha256"]:
        raise SystemExit("STOP=REPLAY_SOURCE_BUNDLE_MISMATCH")
    if source.source_gamefile_sha256 != cell["task_gamefile_group_id"]:
        raise SystemExit("STOP=REPLAY_SOURCE_GAMEFILE_GROUP_MISMATCH")
    if source.source_policy_condition != EXPECTED_MODEL:
        raise SystemExit("STOP=REPLAY_SOURCE_POLICY_CONDITION_MISMATCH")

    template_path = Path(row["representation_template_path"])
    if template_path.is_symlink() or not template_path.is_file():
        raise SystemExit("STOP=REPRESENTATION_TEMPLATE_PATH_INVALID")
    template_raw = template_path.read_bytes()
    if (
        hashlib.sha256(template_raw).hexdigest()
        != row["representation_template_file_sha256"]
    ):
        raise SystemExit("STOP=REPRESENTATION_TEMPLATE_FILE_SHA_MISMATCH")
    template = strict_json_loads(template_raw)
    arm = validate_runtime_representation_binding_v1(
        cell=cell,
        binding_row=row,
        representation_template=template,
    )

    memory_payloads = (
        ()
        if arm["arm_id"] == "M0"
        else (arm["policy_visible_payload"],)
    )

    identity = A0FrozenCellExecutionIdentityV1(
        cell_id=cell["cell_id"],
        source_fingerprint_sha256=cell["source_fingerprint_sha256"],
        arm_id=arm["arm_id"],
        continuation_seed=cell["continuation_seed"],
        policy_runtime_manifest_sha256=runtime[
            "policy_runtime_manifest_sha256"
        ],
        decoding_contract_sha256=runtime["decoding_contract_sha256"],
        active_snapshot_sha256=cell["snapshot_sha256"],
        representation_template_sha256=cell[
            "representation_template_sha256"
        ],
    )

    out = Path(args.output_dir)
    if out.exists() or out.is_symlink():
        raise SystemExit("STOP=FORMAL_A0_ATTEMPT_OUTPUT_EXISTS")
    out.mkdir(parents=True, mode=0o700)

    calls = []
    census = []
    continuation_transitions = []
    session = None
    scientific_execution_started = False

    try:
        adapter = SpawnedAlfworldAdapter.start(
            exact_gamefile=Path(source.exact_gamefile),
            registration_id=row["registration_id"],
            runtime_manifest_sha256=source.runtime_manifest_sha256,
        )
        session = replay_source_decision_state_hold_open_v1(
            source=source,
            adapter=adapter,
        )

        goal = _task_goal(session.reset_state.observation)
        history = tuple(
            ExecutedTransition(expected.action, observed.observation)
            for expected, observed in zip(
                source.transitions,
                session.step_states,
            )
        )
        observation = session.current_observation
        commands = session.current_commands
        budget = source.budget_state
        feedback = (
            None
            if source.interface_feedback_code is None
            else InterfaceFeedbackCode(source.interface_feedback_code)
        )
        model_call_index = source.model_call_index

        renderer = LocalTokenizerPromptRenderer(
            model_path=runtime["base_model_local_path"],
            revision=runtime["tokenizer_revision"],
            chat_template_sha256=runtime["chat_template_sha256"],
            tokenizer_factory=HuggingFaceTokenizerFactory(),
        )
        client = PolicyClient(
            transport=HttpPolicyTransport(
                base_url=runtime["policy_base_url"],
                timeout_seconds=60.0,
            )
        )
        profile = PolicyExecutionProfileV1(
            profile_id="FORMAL_A0_PI1_RAW_PROFILE_V1",
            arm_id="FORMAL_A0_" + arm["arm_id"],
            policy_version="PI1_BAD",
            request_kind="R0",
            requires_diagnostic_policy_call_evidence=False,
            requires_current_admissible_commands=False,
            served_model_name=EXPECTED_MODEL,
        )

        success = None
        terminal_reason = None
        environment_steps_from_source = 0

        while True:
            budget_before_attempt = budget
            prepared = prepare_memory_policy_attempt_v1(
                public_task_goal=goal,
                observation=observation,
                executed_transitions=history,
                memory_payloads=memory_payloads,
                policy_visible_commands=commands,
                harness_visible_commands=commands,
                environment_commands=commands,
                interface_feedback=feedback,
                budget_state=budget,
                snapshot_sha256=EXPECTED_SNAPSHOT,
                token_budget_contract_sha256=EXPECTED_TOKEN,
                retrieval_mode="DIRECT_FIXED_RECORD_NO_RETRIEVAL",
                branch_role="FORMAL_A0_LOCAL_REPRESENTATION_PROBE",
                representation_class=arm["representation_class"],
                memory_lineage_id=(
                    None
                    if arm["arm_id"] == "M0"
                    else row["memory_lineage_id"]
                ),
                record_version=(
                    None
                    if arm["arm_id"] == "M0"
                    else row["record_version"]
                ),
                projection_artifact_sha256=arm["artifact_sha256"],
                packed_token_count=arm["token_count"],
                budget_limits=BudgetLimits(),
            )
            if not prepared.precondition.should_call_policy:
                terminal_reason = prepared.precondition.termination_reason.value
                if not scientific_execution_started:
                    payload = {
                        "schema_id": "FORMAL_A0_NO_POLICY_EXPOSURE_V1",
                        "schema_version": 1,
                        "cell_index": args.cell_index,
                        "cell_id": cell["cell_id"],
                        "attempt_index": args.attempt_index,
                        "execution_identity_sha256": (
                            identity.execution_identity_sha256
                        ),
                        "termination_reason": terminal_reason,
                        "scientific_execution_started": False,
                        "scientific_outcome_produced": False,
                        "retry_exact_same_frozen_cell": False,
                    }
                    _write_once(
                        out / "no_policy_exposure.json",
                        canonical_json_bytes(payload),
                    )
                    print("FORMAL_A0_NO_POLICY_EXPOSURE_NO_SCIENTIFIC_OUTCOME")
                    return 77
                success = False
                break

            if prepared.prompt is None:
                raise RuntimeError("authorized attempt has no prompt")

            try:
                rendered = renderer.render(prompt_text=prepared.prompt)
            except (ValueError, TypeError) as exc:
                if not scientific_execution_started:
                    payload = _failure_payload(
                        kind="FORMAL_A0_PRE_EXECUTION_IDENTITY_FAILURE_V1",
                        cell_index=args.cell_index,
                        cell_id=cell["cell_id"],
                        attempt_index=args.attempt_index,
                        identity_sha=identity.execution_identity_sha256,
                        error=exc,
                        scientific_execution_started=False,
                        exact_retry=False,
                        failure_stage="LOCAL_PROMPT_RENDERING",
                    )
                    _write_once(
                        out / "pre_execution_identity_failure.json",
                        canonical_json_bytes(payload),
                    )
                    print("FORMAL_A0_PRE_EXECUTION_IDENTITY_FAILURE")
                    return 77
                return _write_ambiguity(
                    out=out,
                    args=args,
                    cell=cell,
                    identity=identity,
                    error=exc,
                    failure_stage="LOCAL_PROMPT_RENDERING_AFTER_EXECUTION",
                )

            census_record = A0PromptCensusRecordV1(
                cell_id=cell["cell_id"],
                policy_call_index=model_call_index,
                raw_prompt_sha256=sha256_text(prepared.prompt),
                rendered_prompt_sha256=rendered.rendered_prompt_text_sha256,
                rendered_token_ids_sha256=rendered.rendered_token_ids_sha256,
                prompt_token_count=rendered.prompt_token_count,
                max_generation_tokens=MAX_GENERATION,
                context_window_tokens=runtime["context_window_tokens"],
                truncation_applied=False,
                fits_context=(
                    rendered.prompt_token_count + MAX_GENERATION
                    <= runtime["context_window_tokens"]
                ),
            )
            census.append(census_record.to_dict())

            request_id = (
                "formal-a0-"
                + cell["cell_id"][:16]
                + "-c"
                + str(model_call_index).zfill(4)
            )
            request = profile.build_request(
                prompt_text=prepared.prompt,
                seed=cell["continuation_seed"],
                request_id=request_id,
            )

            try:
                call_result = client.generate_with_evidence(
                    request=request,
                    expected_prompt=rendered,
                )
            except (PromptTokenMismatchError, PolicyResponseError) as exc:
                # These exception types occur only after the provider response is
                # available enough to parse/compare; therefore retry would be
                # scientifically ambiguous.
                return _write_ambiguity(
                    out=out,
                    args=args,
                    cell=cell,
                    identity=identity,
                    error=exc,
                    failure_stage="PROVIDER_RESPONSE_IDENTITY_OR_TOKEN_EVIDENCE",
                )

            scientific_execution_started = True

            try:
                evidence = build_policy_call_evidence(
                    model_call_index=model_call_index,
                    public_task_goal=goal,
                    observation=observation,
                    admissible_commands=commands,
                    executed_history=history,
                    interface_feedback_before=feedback,
                    budget_before=budget,
                    request=request,
                    expected_prompt=rendered,
                    generation=call_result.generation,
                    transport_evidence=call_result.transport_evidence,
                )
                if prepared.exposure is None:
                    raise RuntimeError("authorized attempt has no Memory exposure")
                calls.append(
                    {
                        "policy_call": evidence.to_dict(),
                        "memory_exposure": prepared.exposure.to_dict(),
                    }
                )

                decision = process_memory_policy_generation_v1(
                    raw_response=call_result.generation.raw_response_text,
                    visible_admissible_commands=commands,
                    prepared=prepared,
                    budget_limits=BudgetLimits(),
                )
            except (ValueError, TypeError, RuntimeError) as exc:
                return _write_ambiguity(
                    out=out,
                    args=args,
                    cell=cell,
                    identity=identity,
                    error=exc,
                    failure_stage="POST_RESPONSE_EVIDENCE_OR_RUNTIME_PROCESSING",
                )

            budget = decision.budget_after
            current_call_index = model_call_index
            model_call_index += 1

            if not decision.should_call_env:
                feedback = decision.feedback_code
                if decision.termination_reason is not None:
                    terminal_reason = decision.termination_reason.value
                    success = False
                    break
                continue

            action = decision.candidate_environment_action
            if action is None:
                return _write_ambiguity(
                    out=out,
                    args=args,
                    cell=cell,
                    identity=identity,
                    error=RuntimeError(
                        "environment-authorized decision has no action"
                    ),
                    failure_stage="ENVIRONMENT_ACTION_IDENTITY",
                )

            pre_observation_sha = sha256_text(observation)
            pre_menu_sha = sha256_string_sequence(commands)

            state = session.adapter.step(action)
            environment_steps_from_source += 1
            decision = finalize_environment_result(
                decision,
                environment_terminated=state.done,
                infrastructure_error=False,
            )
            budget = decision.budget_after

            transition = A0ContinuationTransitionV1(
                environment_step_from_source_index=(
                    environment_steps_from_source - 1
                ),
                policy_call_index=current_call_index,
                action=action,
                pre_observation_sha256=pre_observation_sha,
                pre_menu_sequence_sha256=pre_menu_sha,
                resulting_observation_sha256=sha256_text(state.observation),
                resulting_menu_sequence_sha256=state.menu.sequence_sha256,
                score=state.score,
                done=state.done,
                won=state.won,
                budget_before_policy_attempt_sha256=_budget_sha(
                    budget_before_attempt
                ),
                budget_after_environment_finalization_sha256=_budget_sha(
                    budget
                ),
            )
            continuation_transitions.append(transition.to_dict())

            history = (
                *history,
                ExecutedTransition(action, state.observation),
            )
            observation = state.observation
            commands = state.menu.commands
            feedback = None

            if state.done:
                success = bool(state.won)
                terminal_reason = "ENVIRONMENT_TERMINATED"
                break
            if decision.termination_reason is not None:
                success = False
                terminal_reason = decision.termination_reason.value
                break

        final_budget_sha = _budget_sha(budget)
        result = A0CellResultV1(
            cell_id=cell["cell_id"],
            source_state_id=cell["source_state_id"],
            arm_id=arm["arm_id"],
            continuation_seed=cell["continuation_seed"],
            execution_identity_sha256=identity.execution_identity_sha256,
            scientific_outcome_produced=True,
            terminal_success=success,
            evidence_complete=True,
            pre_result_infrastructure_failure=False,
            final_budget_sha256=final_budget_sha,
            prompt_census_count=len(census),
            policy_call_count=len(calls),
            environment_step_count_from_source=environment_steps_from_source,
        )
        bundle = {
            "schema_id": "FORMAL_A0_CELL_EVIDENCE_V1",
            "schema_version": 1,
            "cell_index": args.cell_index,
            "attempt_index": args.attempt_index,
            "cell": cell,
            "execution_identity": identity.to_dict(),
            "source_replay_report": session.report.to_dict(),
            "prompt_census": census,
            "calls": calls,
            "continuation_transitions": continuation_transitions,
            "terminal_reason": terminal_reason,
            "result": result.to_dict(),
        }
        _write_once(
            out / "cell_evidence.json",
            canonical_json_bytes(bundle),
        )
        _write_once(
            out / "cell_result.json",
            result.canonical_bytes(),
        )
        print("FORMAL_A0_CELL_SCIENTIFIC_OUTCOME_COMPLETE")
        print("CELL_ID=" + cell["cell_id"])
        print("ARM=" + arm["arm_id"])
        print("TERMINAL_SUCCESS=" + str(success))
        return 0

    except (
        PolicyTransportError,
        WorkerAdapterError,
        OSError,
        TimeoutError,
    ) as exc:
        if not scientific_execution_started:
            payload = _failure_payload(
                kind="FORMAL_A0_PRE_RESULT_INFRASTRUCTURE_FAILURE_V1",
                cell_index=args.cell_index,
                cell_id=cell["cell_id"],
                attempt_index=args.attempt_index,
                identity_sha=identity.execution_identity_sha256,
                error=exc,
                scientific_execution_started=False,
                exact_retry=True,
                failure_stage="PRE_RESULT_INFRASTRUCTURE",
            )
            _write_once(
                out / "infra_failure.json",
                canonical_json_bytes(payload),
            )
            print("FORMAL_A0_PRE_RESULT_INFRASTRUCTURE_FAILURE")
            return 75

        return _write_ambiguity(
            out=out,
            args=args,
            cell=cell,
            identity=identity,
            error=exc,
            failure_stage="POST_EXECUTION_INFRASTRUCTURE",
        )

    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
