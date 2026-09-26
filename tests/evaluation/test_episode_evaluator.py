from __future__ import annotations

from collections import deque
from dataclasses import replace
from pathlib import Path

import pytest

import pchsi.evaluation.episode_evaluator as evaluator_module
from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_contracts import (
    GamefileIdentityLatch,
    MenuSnapshot,
    ResetPublicState,
    StepPublicState,
)
from pchsi.evaluation.attempt_state import (
    OperationalFinalizationStatus,
    ScientificOutcomeStatus,
)
from pchsi.evaluation.budget import BudgetLimits
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_text,
)
from pchsi.evaluation.episode_evaluator import (
    EpisodeDependencies,
    EpisodeExecutionConfig,
    run_single_episode,
)
from pchsi.evaluation.policy_response import PolicyGeneration
from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence
from pchsi.evaluation.run_schedule import ScheduledCell
from pchsi.evaluation.schema_models import (
    AttemptReceiptV1,
    ScientificCellLockV1,
)
from pchsi.evaluation.task_manifest import FrozenTaskRecord
from pchsi.evaluation.alfworld_worker_protocol import WorkerTerminalStatus


DIGEST = "a" * 64


def _menu(commands: tuple[str, ...]) -> MenuSnapshot:
    return MenuSnapshot(
        commands=commands,
        sequence_sha256=sha256_string_sequence(commands),
    )


class FakeEnvironment:
    def __init__(
        self,
        *,
        reset_state: ResetPublicState,
        steps: list[object],
        close_status: str = "CLOSED",
        worker_alive_after_close: bool = False,
        process_exitcode_after_close: int | None = 0,
    ) -> None:
        self.reset_state = reset_state
        self.steps = deque(steps)
        self.close_status = close_status
        self.worker_alive_after_close = worker_alive_after_close
        self.process_exitcode_after_close = process_exitcode_after_close
        self.reset_calls = 0
        self.step_calls: list[str] = []
        self.close_calls = 0

    def reset(self):
        self.reset_calls += 1
        if isinstance(self.reset_state, BaseException):
            raise self.reset_state
        return self.reset_state

    def step(self, action: str):
        self.step_calls.append(action)
        if not self.steps:
            raise AssertionError("unexpected environment step")
        value = self.steps.popleft()
        if isinstance(value, BaseException):
            raise value
        return value

    @property
    def worker_alive(self) -> bool:
        return self.worker_alive_after_close

    @property
    def process_exitcode(self) -> int | None:
        return self.process_exitcode_after_close

    def close(self) -> WorkerTerminalStatus:
        self.close_calls += 1
        return WorkerTerminalStatus(
            status=self.close_status,
            detail=None,
            exit_code=self.process_exitcode_after_close,
        )


class FakeRenderer:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def render(self, *, prompt_text: str) -> RenderedPromptEvidence:
        self.prompts.append(prompt_text)
        ids = (1, 2, 3)
        return RenderedPromptEvidence(
            raw_policy_prompt_sha256=sha256_text(prompt_text),
            chat_template_sha256="b" * 64,
            rendered_prompt_text_sha256="c" * 64,
            rendered_token_ids=ids,
            rendered_token_ids_sha256=sha256_bytes(
                canonical_json_bytes(list(ids))
            ),
            prompt_token_count=3,
        )


class FakePolicyClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = deque(responses)
        self.requests = []

    def generate(self, *, request, expected_prompt):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected policy call")
        value = self.responses.popleft()
        if isinstance(value, BaseException):
            raise value
        return PolicyGeneration(
            raw_response_text=value,
            raw_response_body=value.encode("utf-8"),
            provider_request_id=request.request_id,
            client_request_id=request.request_id,
            finish_reason="stop",
            prompt_tokens=expected_prompt.prompt_token_count,
            completion_tokens=2,
            prompt_token_ids=expected_prompt.rendered_token_ids,
            token_ids=(4, 5),
            latency_ms=1,
        )


class FakePublisher:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.started: list[AttemptReceiptV1] = []
        self.staged = []
        self.locks: list[ScientificCellLockV1] = []
        self.published: list[tuple[str, ScientificCellLockV1]] = []
        self.terminals: list[AttemptReceiptV1] = []

    def write_started_receipt(self, receipt):
        self.started.append(receipt)
        if self.fail_on == "started":
            raise OSError("started failed")
        return Path("/tmp/started")

    def stage_bundle(self, *, execution_attempt_id, bundle):
        self.staged.append((execution_attempt_id, bundle))
        if self.fail_on == "stage":
            raise OSError("stage failed")
        return Path("/tmp/staging")

    def write_scientific_cell_lock(self, lock):
        self.locks.append(lock)
        if self.fail_on == "lock":
            raise OSError("lock failed")
        return Path("/tmp/lock")

    def publish_staged_directory(
        self,
        *,
        execution_attempt_id,
        lock,
    ):
        self.published.append(
            (execution_attempt_id, lock)
        )
        if self.fail_on == "publish":
            raise OSError("publish failed")
        return Path("/tmp/published")

    def write_terminal_receipt(self, receipt):
        self.terminals.append(receipt)
        if self.fail_on == "terminal":
            raise OSError("terminal failed")
        return Path("/tmp/terminal")


def _reset(
    menu: tuple[str, ...] = ("look", "inventory"),
) -> ResetPublicState:
    gamefile = "/dataset/task-0000/game.tw-pddl"
    return ResetPublicState(
        observation=(
            "Your task is to: put the object away\n"
            "You are in a room."
        ),
        menu=_menu(menu),
        gamefile_latch=GamefileIdentityLatch(
            resolved_gamefile=gamefile
        ),
    )


def _config(
    *,
    budget_limits: BudgetLimits = BudgetLimits(),
) -> EpisodeExecutionConfig:
    return EpisodeExecutionConfig(
        run_id="run-e1",
        cell=ScheduledCell(
            scheduled_cell_id="e1-t0000-s0000000017",
            task_index=0,
            task_id="alfworld_valid_unseen_all134_0000",
            seed=17,
        ),
        execution_attempt_id="e1-t0000-s0000000017-a000",
        attempt_ordinal=0,
        task=FrozenTaskRecord(
            index=0,
            task_id="alfworld_valid_unseen_all134_0000",
            split="valid_unseen",
            task_type="pick_and_place_simple",
            gamefile="/dataset/task-0000/game.tw-pddl",
            gamefile_sha1="b" * 40,
            root="/dataset/task-0000",
            traj_file="/dataset/task-0000/traj_data.json",
        ),
        seed=17,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256=DIGEST,
        split_access_sha256=DIGEST,
        gamefile_identity_manifest_sha256=DIGEST,
        environment_runtime_manifest_sha256=DIGEST,
        policy_runtime_manifest_sha256=DIGEST,
        policy_request_schema_sha256=DIGEST,
        run_schedule_sha256="f" * 64,
        gamefile_sha256="c" * 64,
        budget_limits=budget_limits,
    )


def _deps(
    *,
    responses: list[object],
    steps: list[object],
    reset_state: ResetPublicState | None = None,
    publisher: FakePublisher | None = None,
    close_status: str = "CLOSED",
    worker_alive_after_close: bool = False,
    process_exitcode_after_close: int | None = 0,
):
    environment = FakeEnvironment(
        reset_state=_reset() if reset_state is None else reset_state,
        steps=steps,
        close_status=close_status,
        worker_alive_after_close=worker_alive_after_close,
        process_exitcode_after_close=process_exitcode_after_close,
    )
    policy = FakePolicyClient(responses)
    renderer = FakeRenderer()
    evidence = FakePublisher() if publisher is None else publisher
    return (
        EpisodeDependencies(
            environment=environment,
            policy_client=policy,
            prompt_renderer=renderer,
            artifact_publisher=evidence,
        ),
        environment,
        policy,
        renderer,
        evidence,
    )


def test_first_action_success() -> None:
    result_state = StepPublicState(
        observation="done",
        menu=_menu(()),
        score=1,
        done=True,
        won=True,
    )
    deps, env, policy, _, publisher = _deps(
        responses=['{"action":"look"}'],
        steps=[result_state],
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.SUCCESS
    )
    assert result.success is True
    assert result.termination_reason == "ENVIRONMENT_TERMINATED"
    assert len(result.traces) == 1
    assert len(result.transitions) == 1
    assert result.attempt_bundle is not None
    assert env.step_calls == ["look"]
    assert len(policy.requests) == 1
    assert len(publisher.started) == 1
    assert len(publisher.terminals) == 1



def test_successful_episode_forwards_scientific_lock_to_publication(
) -> None:
    result_state = StepPublicState(
        observation="done",
        menu=_menu(()),
        score=1,
        done=True,
        won=True,
    )
    deps, _, _, _, publisher = _deps(
        responses=['{"action":"look"}'],
        steps=[result_state],
    )
    config = _config()

    result = run_single_episode(
        config=config,
        dependencies=deps,
    )

    assert result.operational_finalization_status is (
        OperationalFinalizationStatus.PUBLISHED
    )
    assert len(publisher.locks) == 1
    assert publisher.published == [
        (
            config.execution_attempt_id,
            publisher.locks[0],
        )
    ]

def test_format_failure_then_off_list_then_success() -> None:
    deps, env, policy, renderer, _ = _deps(
        responses=[
            "not-json",
            '{"action":"go north"}',
            '{"action":"look"}',
        ],
        steps=[
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            )
        ],
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert len(result.traces) == 3
    assert len(result.transitions) == 1
    assert env.step_calls == ["look"]
    assert len(policy.requests) == 3
    assert "FORMAT_ERROR_V1" in renderer.prompts[1]
    assert "INVALID_ACTION_V1" in renderer.prompts[2]


def test_three_consecutive_nonexecuted_attempts_terminate() -> None:
    deps, env, policy, _, _ = _deps(
        responses=["not-json"] * 3,
        steps=[],
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.TASK_FAILURE
    )
    assert result.termination_reason == (
        "CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED"
    )
    assert len(policy.requests) == 3
    assert env.step_calls == []


def test_policy_attempt_sixty_terminates_without_sixty_first_call() -> None:
    limits = BudgetLimits(
        max_policy_attempts=60,
        max_environment_steps=100,
        max_consecutive_nonexecuted_attempts=100,
    )
    deps, _, policy, _, _ = _deps(
        responses=["not-json"] * 60,
        steps=[],
    )
    result = run_single_episode(
        config=_config(budget_limits=limits),
        dependencies=deps,
    )

    assert result.termination_reason == (
        "POLICY_ATTEMPT_BUDGET_EXHAUSTED"
    )
    assert len(policy.requests) == 60
    assert result.final_budget.policy_attempt_count == 60


def test_environment_step_thirty_executes_then_budget_terminates() -> None:
    nonterminal = StepPublicState(
        observation="still running",
        menu=_menu(("look",)),
        score=0,
        done=False,
        won=False,
    )
    deps, env, policy, _, _ = _deps(
        responses=['{"action":"look"}'] * 30,
        steps=[nonterminal] * 30,
        reset_state=_reset(("look",)),
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.termination_reason == (
        "ENVIRONMENT_STEP_BUDGET_EXHAUSTED"
    )
    assert len(policy.requests) == 30
    assert len(env.step_calls) == 30
    assert result.final_budget.environment_step_count == 30


def test_invalid_menu_stops_before_policy_and_budget_change() -> None:
    deps, env, policy, _, _ = _deps(
        responses=[],
        steps=[],
        reset_state=_reset(("",)),
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.NOT_PRODUCED
    )
    assert result.termination_reason == (
        "PROTOCOL_CONFIGURATION_ERROR"
    )
    assert result.final_budget.policy_attempt_count == 0
    assert policy.requests == []
    assert env.step_calls == []


def test_policy_transport_failure_consumes_no_policy_attempt() -> None:
    deps, _, policy, _, _ = _deps(
        responses=[OSError("transport")],
        steps=[],
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.NOT_PRODUCED
    )
    assert result.termination_reason == "INFRASTRUCTURE_ERROR"
    assert result.final_budget.policy_attempt_count == 0
    assert len(policy.requests) == 1


def test_env_step_exception_keeps_reserved_step_and_no_transition() -> None:
    deps, env, _, _, _ = _deps(
        responses=['{"action":"look"}'],
        steps=[RuntimeError("step failed")],
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.termination_reason == "INFRASTRUCTURE_ERROR"
    assert result.final_budget.environment_step_count == 1
    assert len(result.traces) == 1
    assert result.traces[0].attempt_outcome == "INFRASTRUCTURE_ERROR"
    assert result.transitions == ()
    assert env.step_calls == ["look"]


def test_malformed_step_is_infrastructure_error_before_finalization(
    monkeypatch,
) -> None:
    events: list[tuple[bool, bool]] = []
    original = evaluator_module.finalize_environment_result

    def spy(decision, *, environment_terminated, infrastructure_error):
        events.append((environment_terminated, infrastructure_error))
        return original(
            decision,
            environment_terminated=environment_terminated,
            infrastructure_error=infrastructure_error,
        )

    monkeypatch.setattr(
        evaluator_module,
        "finalize_environment_result",
        spy,
    )
    deps, _, _, _, _ = _deps(
        responses=['{"action":"look"}'],
        steps=[("malformed",)],
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.termination_reason == "INFRASTRUCTURE_ERROR"
    assert events == [(False, True)]
    assert result.transitions == ()


def test_failed_generations_do_not_enter_m0() -> None:
    deps, _, _, renderer, _ = _deps(
        responses=[
            "not-json",
            '{"action":"go north"}',
            '{"action":"look"}',
        ],
        steps=[
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            )
        ],
    )
    run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert "EXECUTED_TRANSITIONS_JSON=[]" in renderer.prompts[0]
    assert "EXECUTED_TRANSITIONS_JSON=[]" in renderer.prompts[1]
    assert "EXECUTED_TRANSITIONS_JSON=[]" in renderer.prompts[2]


def test_only_accepted_transitions_enter_m0() -> None:
    deps, _, _, renderer, _ = _deps(
        responses=[
            '{"action":"look"}',
            '{"action":"inventory"}',
        ],
        steps=[
            StepPublicState(
                observation="after look",
                menu=_menu(("inventory",)),
                score=0,
                done=False,
                won=False,
            ),
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            ),
        ],
    )
    run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert '"action":"look"' in renderer.prompts[1]
    assert '"resulting_observation":"after look"' in (
        renderer.prompts[1]
    )


def test_step_result_is_validated_before_finalize_environment_result(
    monkeypatch,
) -> None:
    finalized: list[bool] = []
    original = evaluator_module.finalize_environment_result

    def spy(decision, *, environment_terminated, infrastructure_error):
        finalized.append(infrastructure_error)
        return original(
            decision,
            environment_terminated=environment_terminated,
            infrastructure_error=infrastructure_error,
        )

    monkeypatch.setattr(
        evaluator_module,
        "finalize_environment_result",
        spy,
    )
    deps, _, _, _, _ = _deps(
        responses=['{"action":"look"}'],
        steps=[object()],
    )
    run_single_episode(
        config=_config(),
        dependencies=deps,
    )
    assert finalized == [True]


def test_scientific_outcome_does_not_rerun_after_publication_failure() -> None:
    publisher = FakePublisher(fail_on="stage")
    deps, _, policy, _, _ = _deps(
        responses=['{"action":"look"}'],
        steps=[
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            )
        ],
        publisher=publisher,
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.SUCCESS
    )
    assert result.operational_finalization_status is (
        OperationalFinalizationStatus.PUBLICATION_PENDING
    )
    assert len(policy.requests) == 1


def test_environment_close_failure_is_operational_not_new_trajectory() -> None:
    deps, env, policy, _, _ = _deps(
        responses=['{"action":"look"}'],
        steps=[
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            )
        ],
        close_status="CLOSE_FAILURE",
    )
    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.SUCCESS
    )
    assert result.operational_finalization_status is (
        OperationalFinalizationStatus.CLOSE_FAILED_RECORDED
    )
    assert len(policy.requests) == 1
    assert env.close_calls == 1



# ---------------------------------------------------------------------------
# Fixed-head source-review correction: close-failure evidence integration
# ---------------------------------------------------------------------------


def test_close_failure_reaped_worker_records_formal_audit_code() -> None:
    deps, env, policy, _, publisher = _deps(
        responses=['{"action":"look"}'],
        steps=[
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            )
        ],
        close_status="CLOSE_FAILURE",
        worker_alive_after_close=False,
        process_exitcode_after_close=-15,
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.SUCCESS
    )
    assert result.operational_finalization_status is (
        OperationalFinalizationStatus.CLOSE_FAILED_RECORDED
    )
    assert len(policy.requests) == 1
    assert env.close_calls == 1
    assert len(publisher.terminals) == 1
    terminal = publisher.terminals[0]
    assert terminal.terminal_class == "POST_RESULT_OPERATIONAL_ERROR"
    assert terminal.error_code == "WORKER_REAPED_NO_CONTAMINATION"


def test_close_failure_unreaped_worker_records_rejecting_code() -> None:
    deps, env, policy, _, publisher = _deps(
        responses=['{"action":"look"}'],
        steps=[
            StepPublicState(
                observation="done",
                menu=_menu(()),
                score=1,
                done=True,
                won=True,
            )
        ],
        close_status="CLOSE_TIMEOUT",
        worker_alive_after_close=True,
        process_exitcode_after_close=None,
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.SUCCESS
    )
    assert result.operational_finalization_status is (
        OperationalFinalizationStatus.CLOSE_FAILED_RECORDED
    )
    assert len(policy.requests) == 1
    assert env.close_calls == 1
    assert len(publisher.terminals) == 1
    terminal = publisher.terminals[0]
    assert terminal.terminal_class == "POST_RESULT_OPERATIONAL_ERROR"
    assert terminal.error_code == "WORKER_NOT_REAPED"



# ---------------------------------------------------------------------------
# Fixed-head source-review correction: started-receipt failure cleanup
# ---------------------------------------------------------------------------


def test_started_receipt_failure_closes_environment_without_name_error() -> None:
    publisher = FakePublisher(fail_on="started")
    deps, env, policy, _, evidence = _deps(
        responses=[],
        steps=[],
        publisher=publisher,
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.scientific_outcome_status is (
        ScientificOutcomeStatus.NOT_PRODUCED
    )
    assert result.operational_finalization_status is (
        OperationalFinalizationStatus.ARTIFACT_IO_FAILED
    )
    assert result.termination_reason == "INFRASTRUCTURE_ERROR"
    assert result.final_budget.policy_attempt_count == 0
    assert env.close_calls == 1
    assert policy.requests == []
    assert len(evidence.started) == 1
    assert evidence.terminals == []

def test_p1_condition_bound_episode_publishes_policy_calls() -> None:
    from pchsi.evaluation.condition_execution_binding import (
        ConditionBoundEpisodeCellV1,
    )
    from pchsi.evaluation.distillation_access import DistillationAccessClass
    from pchsi.evaluation.policy_call_evidence import (
        PolicyCallResultV1,
        PolicyCallTransportEvidenceV1,
        allowlisted_response_headers,
    )

    class P1Renderer:
        def render(self, *, prompt_text: str) -> RenderedPromptEvidence:
            ids = (1, 2, 3)
            rendered = "<user>" + prompt_text + "</user>"
            return RenderedPromptEvidence(
                raw_policy_prompt_sha256=sha256_text(prompt_text),
                chat_template_sha256="b" * 64,
                rendered_prompt_text_sha256=sha256_text(rendered),
                rendered_token_ids=ids,
                rendered_token_ids_sha256=sha256_bytes(
                    canonical_json_bytes(list(ids))
                ),
                prompt_token_count=3,
                rendered_prompt_text=rendered,
            )

    class P1PolicyClient:
        def generate_with_evidence(self, *, request, expected_prompt):
            raw = '{"action":"look"}'
            body = canonical_json_bytes(
                {
                    "id": request.request_id,
                    "choices": [
                        {
                            "message": {"content": raw},
                            "finish_reason": "stop",
                            "token_ids": [4, 5],
                        }
                    ],
                    "usage": {
                        "prompt_tokens": expected_prompt.prompt_token_count,
                        "completion_tokens": 2,
                    },
                    "prompt_token_ids": list(
                        expected_prompt.rendered_token_ids
                    ),
                }
            )
            generation = PolicyGeneration(
                raw_response_text=raw,
                raw_response_body=body,
                provider_request_id=request.request_id,
                client_request_id=request.request_id,
                finish_reason="stop",
                prompt_tokens=expected_prompt.prompt_token_count,
                completion_tokens=2,
                prompt_token_ids=expected_prompt.rendered_token_ids,
                token_ids=(4, 5),
                latency_ms=1,
            )
            transport = PolicyCallTransportEvidenceV1(
                request_wire_bytes=request.to_wire_bytes(),
                http_status=200,
                response_headers_allowlisted=tuple(
                    allowlisted_response_headers(
                        {
                            "x-request-id": request.request_id,
                            "content-type": "application/json",
                        }
                    ).items()
                ),
                raw_response_body=body,
                latency_ms=1,
            )
            return PolicyCallResultV1(generation, transport)

    base = _config()
    cell_id = "p4-P4-R0-PI0-t00000-s0000000017"
    config = replace(
        base,
        cell=ConditionBoundEpisodeCellV1(
            scheduled_cell_id=cell_id,
            task_index=0,
            task_id=base.task.task_id,
            seed=17,
            policy_condition_id="P4-R0-PI0",
            access_class=DistillationAccessClass.DEV_VISIBLE,
        ),
        execution_attempt_id=cell_id + "-a000",
        split_access_sha256="1" * 64,
        run_schedule_sha256="3" * 64,
        task_access_manifest_sha256="1" * 64,
        policy_condition_manifest_sha256="2" * 64,
        condition_run_schedule_sha256="3" * 64,
        access_class="DEV_VISIBLE",
        policy_condition_id="P4-R0-PI0",
        condition_cell_id=cell_id,
    )
    environment = FakeEnvironment(
        reset_state=_reset(),
        steps=[
            StepPublicState(
                observation="Task complete.",
                menu=_menu(("look",)),
                score=1,
                done=True,
                won=True,
            )
        ],
    )
    result = run_single_episode(
        config=config,
        dependencies=EpisodeDependencies(
            environment=environment,
            policy_client=P1PolicyClient(),
            prompt_renderer=P1Renderer(),
            artifact_publisher=FakePublisher(),
        ),
    )
    assert result.success is True
    assert result.attempt_bundle is not None
    assert result.attempt_bundle.policy_calls_jsonl is not None
    assert b'"model_call_index":0' in result.attempt_bundle.policy_calls_jsonl
