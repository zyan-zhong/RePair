from __future__ import annotations

from collections import deque
from pathlib import Path

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_contracts import (
    GamefileIdentityLatch,
    MenuSnapshot,
    ResetPublicState,
    StepPublicState,
)
from pchsi.evaluation.alfworld_worker_protocol import WorkerTerminalStatus
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
from pchsi.evaluation.interface_isolation_request import (
    i1_structured_serialization_schema_dict,
)
from pchsi.evaluation.policy_call_evidence import (
    PolicyCallResultV1,
    PolicyCallTransportEvidenceV1,
    allowlisted_response_headers,
)
from pchsi.evaluation.policy_execution_profile import (
    I1_EXECUTION_PROFILE_V1,
    I2_EXECUTION_PROFILE_V1,
)
from pchsi.evaluation.policy_response import PolicyGeneration
from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence
from pchsi.evaluation.run_schedule import ScheduledCell
from pchsi.evaluation.schema_models import (
    AttemptReceiptV1,
    ScientificCellLockV1,
)
from pchsi.evaluation.task_manifest import FrozenTaskRecord


DIGEST = "a" * 64


def _menu(commands: tuple[str, ...]) -> MenuSnapshot:
    return MenuSnapshot(
        commands=commands,
        sequence_sha256=sha256_string_sequence(commands),
    )


class _Environment:
    def __init__(self, *, steps: list[object]) -> None:
        self.steps = deque(steps)
        self.step_calls: list[str] = []

    def reset(self) -> ResetPublicState:
        return ResetPublicState(
            observation=(
                "Your task is to: put the object away\n"
                "You are in a room."
            ),
            menu=_menu(("look", "inventory")),
            gamefile_latch=GamefileIdentityLatch(
                resolved_gamefile="/dataset/task-0000/game.tw-pddl"
            ),
        )

    def step(self, action: str):
        self.step_calls.append(action)
        value = self.steps.popleft()
        if isinstance(value, BaseException):
            raise value
        return value

    @property
    def worker_alive(self) -> bool:
        return False

    @property
    def process_exitcode(self) -> int:
        return 0

    def close(self) -> WorkerTerminalStatus:
        return WorkerTerminalStatus(
            status="CLOSED",
            detail=None,
            exit_code=0,
        )


class _Renderer:
    def render(self, *, prompt_text: str) -> RenderedPromptEvidence:
        rendered = (
            "<|im_start|>user\n"
            + prompt_text
            + "<|im_end|>\n<|im_start|>assistant\n"
        )
        ids = (1, 2, 3)
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


class _I1PolicyClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = deque(responses)
        self.requests = []

    def generate(self, **kwargs):
        raise AssertionError("I1 must use generate_with_evidence")

    def generate_with_evidence(
        self,
        *,
        request,
        expected_prompt,
    ) -> PolicyCallResultV1:
        self.requests.append(request)

        raw = self.responses.popleft()
        provider_id = request.request_id

        body = canonical_json_bytes(
            {
                "id": provider_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": raw,
                        },
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
            provider_request_id=provider_id,
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
                        "x-request-id": provider_id,
                        "content-type": "application/json",
                        "content-length": str(len(body)),
                    }
                ).items()
            ),
            raw_response_body=body,
            latency_ms=1,
        )

        return PolicyCallResultV1(
            generation=generation,
            transport_evidence=transport,
        )


class _Publisher:
    def __init__(self) -> None:
        self.started: list[AttemptReceiptV1] = []
        self.terminals: list[AttemptReceiptV1] = []
        self.locks: list[ScientificCellLockV1] = []
        self.staged = []
        self.published = []

    def write_started_receipt(self, receipt):
        self.started.append(receipt)
        return Path("/tmp/started")

    def stage_bundle(self, *, execution_attempt_id, bundle):
        self.staged.append((execution_attempt_id, bundle))
        return Path("/tmp/staging")

    def write_scientific_cell_lock(self, lock):
        self.locks.append(lock)
        return Path("/tmp/lock")

    def publish_staged_directory(
        self,
        *,
        execution_attempt_id,
        lock,
    ):
        self.published.append((execution_attempt_id, lock))
        return Path("/tmp/published")

    def write_terminal_receipt(self, receipt):
        self.terminals.append(receipt)
        return Path("/tmp/terminal")


def _config() -> EpisodeExecutionConfig:
    return EpisodeExecutionConfig(
        run_id="i1-test",
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
    )


def _dependencies(
    *,
    responses: list[str],
    steps: list[object],
):
    environment = _Environment(steps=steps)
    policy = _I1PolicyClient(responses)
    publisher = _Publisher()

    dependencies = EpisodeDependencies(
        environment=environment,
        policy_client=policy,
        prompt_renderer=_Renderer(),
        artifact_publisher=publisher,
        policy_execution_profile=I1_EXECUTION_PROFILE_V1,
    )

    return dependencies, environment, policy, publisher


def test_i1_off_list_string_is_not_repaired() -> None:
    deps, env, policy, _ = _dependencies(
        responses=[
            '{"action":"go north"}',
            '{"action":"go north"}',
            '{"action":"go north"}',
        ],
        steps=[],
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert env.step_calls == []
    assert len(result.traces) == 3
    assert {
        trace.attempt_outcome
        for trace in result.traces
    } == {"ACTION_NOT_ADMISSIBLE"}

    assert result.attempt_bundle is not None
    assert result.attempt_bundle.policy_calls_jsonl is not None
    assert len(policy.requests) == 3

    for request in policy.requests:
        assert request.to_wire_dict()["structured_outputs"] == {
            "json": i1_structured_serialization_schema_dict()
        }

    for trace in result.traces:
        assert (
            trace.provenance.arm_id
            == "I1_STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
        )
        assert (
            trace.provenance.policy_version
            == "STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
        )


def test_i1_still_uses_strict_action_normalization() -> None:
    deps, env, _, _ = _dependencies(
        responses=[
            '{"action":"look\\nlook"}',
            '{"action":"look\\nlook"}',
            '{"action":"look\\nlook"}',
        ],
        steps=[],
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert env.step_calls == []
    assert {
        trace.attempt_outcome
        for trace in result.traces
    } == {"FORMAT_PROTOCOL_FAILURE"}
    assert {
        trace.failure_stage
        for trace in result.traces
    } == {"action_normalization"}


def test_i1_exact_admissible_action_reaches_environment() -> None:
    terminal = StepPublicState(
        observation="done",
        menu=_menu(()),
        score=1,
        done=True,
        won=True,
    )

    deps, env, _, _ = _dependencies(
        responses=['{"action":"look"}'],
        steps=[terminal],
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert env.step_calls == ["look"]
    assert len(result.transitions) == 1
    assert result.success is True
    assert result.attempt_bundle is not None
    assert result.attempt_bundle.policy_calls_jsonl is not None



def _i2_dependencies(
    *,
    responses: list[str],
    steps: list[object],
):
    environment = _Environment(steps=steps)
    policy = _I1PolicyClient(responses)
    publisher = _Publisher()

    dependencies = EpisodeDependencies(
        environment=environment,
        policy_client=policy,
        prompt_renderer=_Renderer(),
        artifact_publisher=publisher,
        policy_execution_profile=I2_EXECUTION_PROFILE_V1,
    )

    return dependencies, environment, policy, publisher


def test_i2_injects_exact_current_menu_on_every_call() -> None:
    second_menu = (
        "take mug 1 from desk 1",
        "look",
    )
    first_result = StepPublicState(
        observation="You are at desk 1.",
        menu=_menu(second_menu),
        score=0,
        done=False,
        won=False,
    )
    terminal = StepPublicState(
        observation="done",
        menu=_menu(()),
        score=1,
        done=True,
        won=True,
    )

    deps, env, policy, _ = _i2_dependencies(
        responses=[
            '{"action":"look"}',
            '{"action":"take mug 1 from desk 1"}',
        ],
        steps=[first_result, terminal],
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert result.success is True
    assert env.step_calls == [
        "look",
        "take mug 1 from desk 1",
    ]
    assert len(policy.requests) == 2

    first_enum = (
        policy.requests[0]
        .to_wire_dict()["structured_outputs"]["json"]
        ["properties"]["action"]["enum"]
    )
    second_enum = (
        policy.requests[1]
        .to_wire_dict()["structured_outputs"]["json"]
        ["properties"]["action"]["enum"]
    )

    assert first_enum == ["look", "inventory"]
    assert second_enum == list(second_menu)


def test_i2_keeps_runtime_membership_as_defense_in_depth() -> None:
    deps, env, policy, _ = _i2_dependencies(
        responses=[
            '{"action":"go north"}',
            '{"action":"go north"}',
            '{"action":"go north"}',
        ],
        steps=[],
    )

    result = run_single_episode(
        config=_config(),
        dependencies=deps,
    )

    assert env.step_calls == []
    assert len(policy.requests) == 3
    assert {
        trace.attempt_outcome
        for trace in result.traces
    } == {"ACTION_NOT_ADMISSIBLE"}

    for request in policy.requests:
        enum_values = (
            request.to_wire_dict()
            ["structured_outputs"]["json"]
            ["properties"]["action"]["enum"]
        )
        assert enum_values == ["look", "inventory"]
