#!/usr/bin/env python3
"""Run exactly one Human Reference same-state F0/F1 branch.

Scientific semantics are a compatibility port of the historical V7C Phase1F
counterfactual product into the current PCHSI runtime:

  exact registered source-state replay
    -> F0: no repair
       F1: one frozen EXACT_ACTION repair, counted against env budget
    -> return control to the same frozen pi1 RAW continuation
    -> durable branch evidence

This runner never assigns Benefit/Harm/Neutral/Uncertain.  That authority is
held by the offline Environment Verifier aggregation step.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter, WorkerAdapterError
from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_text, strict_json_loads
from pchsi.reference_loop.canonical import domain_hash
from pchsi.evaluation.policy_call_evidence import build_policy_call_evidence
from pchsi.evaluation.policy_client import (
    HttpPolicyTransport,
    PolicyClient,
    PolicyTransportError,
    PromptTokenMismatchError,
)
from pchsi.evaluation.policy_response import PolicyResponseError
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
)
from pchsi.evaluation.rendered_prompt import (
    HuggingFaceTokenizerFactory,
    LocalTokenizerPromptRenderer,
)
from pchsi.evaluation.runtime_core import finalize_environment_result
from pchsi.memory.a0_replay_session import replay_source_decision_state_hold_open_v1
from pchsi.memory.memory_runtime_bridge import (
    prepare_memory_policy_attempt_v1,
    process_memory_policy_generation_v1,
)
from pchsi.research_intelligence.human_f0f1_runtime import (
    build_branch_evidence_hash_v1,
    build_bound_continuation_request_v1,
    load_continuation_runtime_binding_v2,
    validate_continuation_wire_v1,
    load_registered_replay_source_authority_v1,
    reserve_registered_repair_environment_step_v1,
    validate_branch_binding_v1,
    validate_candidate_content_hash_v1,
    validate_candidate_source_provenance_v1,
    validate_executable_exact_candidate_v1,
)


APPROVAL = "EXECUTION_APPROVED_CLEAN_REFERENCE_F0F1_PAIRED_V1"
MAX_GENERATION = 128


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_once(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _canonical_object(path: Path, expected_file_sha: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("bound object path invalid: " + str(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_file_sha:
        raise ValueError("bound object file SHA mismatch: " + str(path))
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise ValueError("bound object is not canonical JSON: " + str(path))
    return value


def _budget_payload(value: BudgetState) -> dict[str, int]:
    return {
        "policy_attempt_count": value.policy_attempt_count,
        "environment_step_count": value.environment_step_count,
        "protocol_failure_count": value.protocol_failure_count,
        "inadmissible_action_count": value.inadmissible_action_count,
        "consecutive_nonexecuted_attempt_count": value.consecutive_nonexecuted_attempt_count,
    }


def _budget_sha(value: BudgetState) -> str:
    return hashlib.sha256(canonical_json_bytes(_budget_payload(value))).hexdigest()


def _load_runtime(path: Path, expected_file_sha: str, *, expected_model: str) -> dict[str, object]:
    value = load_continuation_runtime_binding_v2(
        path, expected_file_sha256=expected_file_sha, expected_model=expected_model,
    )
    if int(value["context_window_tokens"]) <= MAX_GENERATION:
        raise ValueError("runtime context window invalid")
    return value


def _task_goal(reset_observation: str) -> str:
    prefix = "Your task is to:"
    for line in reset_observation.splitlines():
        if line.startswith(prefix):
            goal = line[len(prefix):].strip()
            if goal:
                return goal
    raise ValueError("public task goal parser contract failure")


def _transition_record(
    *,
    role: str,
    source_step_index: int,
    model_call_index: int | None,
    action: str,
    pre_observation: str,
    pre_commands: tuple[str, ...],
    state,
    budget_before: BudgetState,
    budget_after: BudgetState,
) -> dict[str, object]:
    return {
        "role": role,
        "environment_step_from_source_index": source_step_index,
        "model_call_index": model_call_index,
        "action": action,
        "pre_observation_sha256": sha256_text(pre_observation),
        "pre_menu_sequence_sha256": sha256_string_sequence(pre_commands),
        "resulting_observation_sha256": sha256_text(state.observation),
        "resulting_menu_sequence_sha256": state.menu.sequence_sha256,
        "score": state.score,
        "done": state.done,
        "won": state.won,
        "budget_before_sha256": _budget_sha(budget_before),
        "budget_after_sha256": _budget_sha(budget_after),
    }


def _bind_source_raw_m0_prompt_v1(
    prepared,
    *,
    public_task_goal: str,
    observation: str,
    executed_transitions: tuple[ExecutedTransition, ...],
    admissible_commands: tuple[str, ...],
    interface_feedback: InterfaceFeedbackCode | None,
):
    """Rebind an authorized M0 attempt to the registered source RAW prompt."""
    if prepared.prompt is None or prepared.exposure is None:
        raise ValueError("authorized M0 attempt must carry prompt and exposure")
    if prepared.exposure.representation_class != "M0":
        raise ValueError("source RAW continuation requires M0 exposure")
    prompt = build_raw_policy_prompt(
        public_task_goal=public_task_goal,
        observation=observation,
        executed_transitions=executed_transitions,
        admissible_commands=admissible_commands,
        interface_feedback=interface_feedback,
    )
    exposure = replace(
        prepared.exposure,
        final_prompt_sha256=sha256_text(prompt),
        exposure_sha256=None,
    )
    return replace(prepared, prompt=prompt, exposure=exposure)


def _failure_payload(binding: dict[str, object], exc: BaseException, *, started: bool) -> dict[str, object]:
    payload = {
        "schema_id": "CLEAN_REFERENCE_F0F1_BRANCH_FAILURE_V1",
        "schema_version": 1,
        "branch_binding_sha256": binding["branch_binding_sha256"],
        "execution_manifest_sha256": binding["execution_manifest_sha256"],
        "pair_id": binding["pair_id"],
        "state_position": binding["state_position"],
        "repetition": binding["repetition"],
        "branch": binding["branch"],
        "continuation_seed": binding["continuation_seed"],
        "source_state_sha256": binding["source_state_sha256"],
        "research_candidate_id": binding["research_candidate_id"],
        "source_candidate_sha256": binding["source_candidate_sha256"],
        "registered_repair_action": binding["registered_repair_action"],
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "scientific_execution_started": started,
        "scientific_outcome_produced": False,
        "evidence_complete": False,
        "automatic_retry_authorized": False,
        "branch_failure_sha256": "0" * 64,
    }
    payload["branch_failure_sha256"] = hashlib.sha256(
        b"CLEAN_REFERENCE_F0F1_BRANCH_FAILURE_V1\0"
        + canonical_json_bytes({k: v for k, v in payload.items() if k != "branch_failure_sha256"})
    ).hexdigest()
    return payload


def execute(binding: dict[str, object], output_dir: Path) -> int:
    if output_dir.exists() or output_dir.is_symlink():
        raise SystemExit("STOP=HUMAN_F0F1_BRANCH_OUTPUT_EXISTS")
    output_dir.mkdir(parents=True, mode=0o700)

    source_path = Path(str(binding["replay_source_path"]))
    source = load_registered_replay_source_authority_v1(
        source_path, expected_file_sha256=str(binding["replay_source_file_sha256"])
    )
    if source.expected_source_fingerprint.fingerprint_sha256 != binding["source_state_sha256"]:
        raise ValueError("replay source state differs from branch binding")
    candidate = _canonical_object(
        Path(str(binding["candidate_artifact_path"])),
        str(binding["candidate_artifact_file_sha256"]),
    )
    validate_candidate_content_hash_v1(
        candidate, expected_candidate_sha256=str(binding["source_candidate_sha256"])
    )
    validate_candidate_source_provenance_v1(
        candidate,
        expected_source_state_sha256=
            source.expected_source_fingerprint.fingerprint_sha256,
        expected_source_policy_condition=
            source.source_policy_condition,
    )
    if candidate.get("exact_action") != binding["registered_repair_action"]:
        raise ValueError("candidate exact action differs from branch binding")

    runtime = _load_runtime(
        Path(str(binding["runtime_binding_path"])),
        str(binding["runtime_binding_file_sha256"]),
        expected_model=str(binding["policy_model"]),
    )
    if source.runtime_manifest_sha256 != runtime["policy_runtime_manifest_sha256"]:
        raise ValueError("source replay runtime manifest differs from live runtime binding")

    session = None
    scientific_execution_started = False
    try:
        registration_id = (
            "clean-f0f1-" + str(binding["source_state_sha256"])[:12]
            + "-r" + str(binding["repetition"])
            + "-" + str(binding["branch"]).lower()
        )
        adapter = SpawnedAlfworldAdapter.start(
            exact_gamefile=Path(source.exact_gamefile),
            registration_id=registration_id,
            runtime_manifest_sha256=source.runtime_manifest_sha256,
        )
        session = replay_source_decision_state_hold_open_v1(source=source, adapter=adapter)

        goal = _task_goal(session.reset_state.observation)
        history = tuple(
            ExecutedTransition(expected.action, observed.observation)
            for expected, observed in zip(source.transitions, session.step_states)
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
        environment_steps_from_source = 0
        transitions: list[dict[str, object]] = []
        calls: list[dict[str, object]] = []
        intervention = None
        success: bool | None = None
        terminal_reason: str | None = None

        if binding["branch"] == "F1":
            action = validate_executable_exact_candidate_v1(
                candidate,
                expected_candidate_sha256=str(binding["source_candidate_sha256"]),
                expected_source_state_sha256=str(binding["source_state_sha256"]),
                live_commands=commands,
            )
            if action != binding["registered_repair_action"]:
                raise ValueError("live validated repair differs from frozen binding")
            budget_before = budget
            budget = reserve_registered_repair_environment_step_v1(budget, BudgetLimits())
            pre_observation = observation
            pre_commands = commands
            scientific_execution_started = True
            state = session.adapter.step(action)
            intervention = _transition_record(
                role="REGISTERED_REPAIR_INTERVENTION",
                source_step_index=0,
                model_call_index=None,
                action=action,
                pre_observation=pre_observation,
                pre_commands=pre_commands,
                state=state,
                budget_before=budget_before,
                budget_after=budget,
            )
            transitions.append(intervention)
            environment_steps_from_source += 1
            history = (*history, ExecutedTransition(action, state.observation))
            observation = state.observation
            commands = state.menu.commands
            feedback = None
            if state.done:
                success = bool(state.won)
                terminal_reason = "ENVIRONMENT_TERMINATED_BY_REGISTERED_REPAIR"

        renderer = LocalTokenizerPromptRenderer(
            model_path=str(runtime["base_model_local_path"]),
            revision=str(runtime["tokenizer_revision"]),
            chat_template_sha256=str(runtime["chat_template_sha256"]),
            tokenizer_factory=HuggingFaceTokenizerFactory(),
        )
        client = PolicyClient(
            transport=HttpPolicyTransport(
                base_url=str(runtime["policy_base_url"]),
                timeout_seconds=60.0,
            )
        )
        # The hash-bound runtime supplies the profile; missing metadata fails closed.

        while success is None:
            budget_before_attempt = budget
            prepared = prepare_memory_policy_attempt_v1(
                public_task_goal=goal,
                observation=observation,
                executed_transitions=history,
                memory_payloads=(),
                policy_visible_commands=commands,
                harness_visible_commands=commands,
                environment_commands=commands,
                interface_feedback=feedback,
                budget_state=budget,
                snapshot_sha256=str(binding["active_snapshot_sha256"]),
                token_budget_contract_sha256=str(binding["token_budget_contract_sha256"]),
                retrieval_mode="NO_RETRIEVAL",
                branch_role="HUMAN_REFERENCE_F0F1_" + str(binding["branch"]),
                representation_class="M0",
                memory_lineage_id=None,
                record_version=None,
                projection_artifact_sha256=None,
                packed_token_count=0,
                budget_limits=BudgetLimits(),
            )
            if not prepared.precondition.should_call_policy:
                terminal_reason = (
                    None
                    if prepared.precondition.termination_reason is None
                    else prepared.precondition.termination_reason.value
                )
                success = False
                break
            if prepared.prompt is None:
                raise RuntimeError("authorized pi1 continuation attempt has no prompt")
            prepared = _bind_source_raw_m0_prompt_v1(
                prepared,
                public_task_goal=goal,
                observation=observation,
                executed_transitions=history,
                admissible_commands=commands,
                interface_feedback=feedback,
            )
            if (
                binding["branch"] == "F0"
                and model_call_index == source.model_call_index
                and environment_steps_from_source == 0
                and sha256_text(prepared.prompt) != source.base_policy_input_sha256
            ):
                raise RuntimeError(
                    "F0 source prompt differs from registered base policy input"
                )

            rendered = renderer.render(prompt_text=prepared.prompt)
            if rendered.prompt_token_count + MAX_GENERATION > int(runtime["context_window_tokens"]):
                raise RuntimeError("pi1 continuation prompt exceeds frozen context window")
            request = build_bound_continuation_request_v1(
                runtime=runtime,
                prompt_text=prepared.prompt,
                seed=int(binding["continuation_seed"]),
                request_id=(
                    "clean-f0f1-" + str(binding["pair_id"])[:12]
                    + "-" + str(binding["branch"]).lower()
                    + "-c" + str(model_call_index).zfill(4)
                ),
            )
            validate_continuation_wire_v1(
                runtime=runtime, raw=request.to_wire_bytes(),
                expected_prompt=prepared.prompt, expected_seed=int(binding["continuation_seed"]),
                expected_request_id=request.request_id,
            )
            try:
                call_result = client.generate_with_evidence(
                    request=request,
                    expected_prompt=rendered,
                )
            except (PromptTokenMismatchError, PolicyResponseError):
                scientific_execution_started = True
                raise
            scientific_execution_started = True

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
            validate_continuation_wire_v1(
                runtime=runtime, raw=evidence.request_wire_bytes,
                expected_prompt=prepared.prompt, expected_seed=int(binding["continuation_seed"]),
                expected_request_id=request.request_id,
            )
            if prepared.exposure is None:
                raise RuntimeError("authorized continuation attempt lacks M0 exposure evidence")
            calls.append({
                "policy_call": evidence.to_dict(),
                "memory_exposure": prepared.exposure.to_dict(),
            })

            decision = process_memory_policy_generation_v1(
                raw_response=call_result.generation.raw_response_text,
                visible_admissible_commands=commands,
                prepared=prepared,
                budget_limits=BudgetLimits(),
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
                raise RuntimeError("environment-authorized pi1 decision has no exact action")
            pre_observation = observation
            pre_commands = commands
            state = session.adapter.step(action)
            environment_steps_from_source += 1
            decision = finalize_environment_result(
                decision,
                environment_terminated=state.done,
                infrastructure_error=False,
            )
            budget = decision.budget_after
            transitions.append(_transition_record(
                role="PI1_CONTINUATION",
                source_step_index=environment_steps_from_source - 1,
                model_call_index=current_call_index,
                action=action,
                pre_observation=pre_observation,
                pre_commands=pre_commands,
                state=state,
                budget_before=budget_before_attempt,
                budget_after=budget,
            ))
            history = (*history, ExecutedTransition(action, state.observation))
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

        payload: dict[str, Any] = {
            "schema_id": "CLEAN_REFERENCE_F0F1_BRANCH_EVIDENCE_V1",
            "schema_version": 1,
            "branch_binding_sha256": binding["branch_binding_sha256"],
            "execution_manifest_sha256": binding["execution_manifest_sha256"],
            "pair_id": binding["pair_id"],
            "state_position": binding["state_position"],
            "repetition": binding["repetition"],
            "branch": binding["branch"],
            "continuation_seed": binding["continuation_seed"],
            "source_state_sha256": binding["source_state_sha256"],
            "research_candidate_id": binding["research_candidate_id"],
            "source_candidate_sha256": binding["source_candidate_sha256"],
            "registered_repair_action": binding["registered_repair_action"],
            "source_replay_report": session.report.to_dict(),
            "continuation_request_contract": runtime["continuation_request_contract"],
            "intervention": intervention,
            "policy_calls": calls,
            "environment_transitions_from_source": transitions,
            "terminal_success": success,
            "terminal_reason": terminal_reason,
            "final_budget": _budget_payload(budget),
            "final_budget_sha256": _budget_sha(budget),
            "policy_call_count_from_source": len(calls),
            "environment_step_count_from_source": environment_steps_from_source,
            "scientific_outcome_produced": True,
            "evidence_complete": True,
            "automatic_retry_count": 0,
            "branch_evidence_sha256": "0" * 64,
        }
        payload["branch_evidence_sha256"] = build_branch_evidence_hash_v1(payload)
        _write_once(output_dir / "CLEAN_REFERENCE_F0F1_BRANCH_EVIDENCE_V1.json", payload)
        print("HUMAN_REFERENCE_F0F1_BRANCH_SCIENTIFIC_OUTCOME_COMPLETE")
        print("PAIR_ID=" + str(binding["pair_id"]))
        print("BRANCH=" + str(binding["branch"]))
        print("TERMINAL_SUCCESS=" + str(success))
        print("BRANCH_EVIDENCE_SHA256=" + str(payload["branch_evidence_sha256"]))
        return 0

    except (PolicyTransportError, WorkerAdapterError, OSError, TimeoutError, PromptTokenMismatchError, PolicyResponseError, ValueError, TypeError, RuntimeError) as exc:
        failure = _failure_payload(binding, exc, started=scientific_execution_started)
        _write_once(output_dir / "CLEAN_REFERENCE_F0F1_BRANCH_FAILURE_V1.json", failure)
        print("HUMAN_REFERENCE_F0F1_BRANCH_FAILED_NO_AUTO_RETRY")
        print("FAILURE_TYPE=" + type(exc).__name__)
        return 76 if scientific_execution_started else 75
    finally:
        if session is not None:
            session.close()


def main() -> int:
    if os.environ.get("PCHSI_CLEAN_F0F1_EXECUTION_APPROVAL") != APPROVAL:
        raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_APPROVAL_MISSING")
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-binding", required=True)
    parser.add_argument("--branch-binding-sha256", required=True)
    parser.add_argument("--execution-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    binding_path = Path(args.branch_binding)
    if binding_path.is_symlink() or not binding_path.is_file():
        raise SystemExit("STOP=HUMAN_F0F1_BRANCH_BINDING_PATH_INVALID")
    raw = binding_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.branch_binding_sha256:
        raise SystemExit("STOP=HUMAN_F0F1_BRANCH_BINDING_FILE_SHA_MISMATCH")
    value = strict_json_loads(raw)
    binding = validate_branch_binding_v1(value)
    expected_manifest = os.environ.get("PCHSI_CLEAN_F0F1_EXECUTION_MANIFEST_SHA256")
    if expected_manifest != binding["execution_manifest_sha256"]:
        raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_MANIFEST_AUTHORITY_MISMATCH")
    mp=Path(args.execution_manifest)
    if mp.is_symlink() or not mp.is_file(): raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_MANIFEST_PATH_INVALID")
    raw=mp.read_bytes(); manifest=strict_json_loads(raw)
    if not isinstance(manifest,dict) or canonical_json_bytes(manifest)!=raw: raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_MANIFEST_NOT_CANONICAL")
    if manifest.get("schema_id")!="CLEAN_REFERENCE_F0F1_EXECUTION_MANIFEST_V1": raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_MANIFEST_SCHEMA_MISMATCH")
    observed=domain_hash("CLEAN_REFERENCE_F0F1_EXECUTION_MANIFEST_V1",manifest,excluded_field="execution_manifest_sha256")
    if observed!=expected_manifest: raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_MANIFEST_DOMAIN_SHA_MISMATCH")
    matches=[row for row in manifest.get("branches",[]) if isinstance(row,dict) and row.get("pair_id")==binding["pair_id"] and row.get("branch")==binding["branch"]]
    if len(matches)!=1: raise SystemExit("STOP=HUMAN_F0F1_EXECUTION_MANIFEST_BRANCH_COUNT_MISMATCH")
    expected_row=matches[0]
    fields=("round_id","state_position","repetition","continuation_seed","source_state_sha256","research_candidate_id","source_candidate_sha256","registered_repair_action","candidate_artifact_file_sha256","replay_source_file_sha256","runtime_binding_file_sha256","policy_model","policy_version")
    if any(expected_row.get(f)!=binding.get(f) for f in fields): raise SystemExit("STOP=execution manifest branch binding mismatch")
    return execute(binding, Path(args.output_dir))


if __name__ == "__main__":
    raise SystemExit(main())
