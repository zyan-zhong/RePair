from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pchsi.evaluation.alfworld_contracts import ResetPublicState, StepPublicState
from pchsi.evaluation.canonical_evidence import sha256_text
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
    SourceStateReplayReportV1,
    build_source_decision_state_fingerprint_v1,
)


class ReplayAdapterV1(Protocol):
    @property
    def exact_gamefile(self) -> str: ...
    def reset(self) -> ResetPublicState: ...
    def step(self, action: str) -> StepPublicState: ...
    def close(self) -> object: ...


class SourceStateReplayError(ValueError):
    pass


def replay_source_decision_state_v1(
    *,
    source: RegisteredReplaySourceV1,
    adapter: ReplayAdapterV1,
) -> SourceStateReplayReportV1:
    if not isinstance(source, RegisteredReplaySourceV1):
        raise TypeError("source type mismatch")
    expected_gamefile = str(Path(source.exact_gamefile).resolve())
    if str(Path(adapter.exact_gamefile).resolve()) != expected_gamefile:
        raise SourceStateReplayError("ADAPTER_GAMEFILE_IDENTITY_MISMATCH")
    current_obs = current_menu = None
    completed = 0
    try:
        reset = adapter.reset()
        if not isinstance(reset, ResetPublicState):
            raise SourceStateReplayError("RESET_PUBLIC_STATE_TYPE_MISMATCH")
        if str(Path(reset.gamefile_latch.resolved_gamefile).resolve()) != expected_gamefile:
            raise SourceStateReplayError("RESET_GAMEFILE_LATCH_MISMATCH")
        current_obs = sha256_text(reset.observation)
        current_menu = reset.menu.sequence_sha256
        if current_obs != source.reset_observation_sha256:
            raise SourceStateReplayError("RESET_OBSERVATION_MISMATCH")
        if current_menu != source.reset_menu_sequence_sha256:
            raise SourceStateReplayError("RESET_MENU_MISMATCH")

        for expected in source.transitions:
            if current_obs != expected.pre_observation_sha256:
                raise SourceStateReplayError("REPLAY_PRE_OBSERVATION_MISMATCH")
            if current_menu != expected.pre_menu_sequence_sha256:
                raise SourceStateReplayError("REPLAY_PRE_MENU_MISMATCH")
            result = adapter.step(expected.action)
            if not isinstance(result, StepPublicState):
                raise SourceStateReplayError("STEP_PUBLIC_STATE_TYPE_MISMATCH")
            obs_sha = sha256_text(result.observation)
            menu_sha = result.menu.sequence_sha256
            if obs_sha != expected.resulting_observation_sha256:
                raise SourceStateReplayError("REPLAY_RESULT_OBSERVATION_MISMATCH")
            if menu_sha != expected.resulting_menu_sequence_sha256:
                raise SourceStateReplayError("REPLAY_RESULT_MENU_MISMATCH")
            if result.score != expected.score:
                raise SourceStateReplayError("REPLAY_SCORE_MISMATCH")
            if result.done is not expected.done:
                raise SourceStateReplayError("REPLAY_DONE_MISMATCH")
            if result.won is not expected.won:
                raise SourceStateReplayError("REPLAY_WON_MISMATCH")
            completed += 1
            current_obs, current_menu = obs_sha, menu_sha
            if result.done and completed != len(source.transitions):
                raise SourceStateReplayError("REPLAY_EARLY_TERMINAL")

        replay = build_source_decision_state_fingerprint_v1(
            source_task_id=source.source_task_id,
            source_gamefile_sha256=source.source_gamefile_sha256,
            source_bundle_sha256=source.source_bundle_sha256,
            source_policy_condition=source.source_policy_condition,
            executed_prefix_sha256=source.executed_prefix_sha256,
            observation_sha256=current_obs,
            menu_sequence_sha256=current_menu,
            memory_m0_sha256=source.memory_m0_sha256,
            interface_feedback_code=source.interface_feedback_code,
            budget_state=source.budget_state,
            model_call_index=source.model_call_index,
            base_policy_input_sha256=source.base_policy_input_sha256,
        )
        expected_sha = source.expected_source_fingerprint.fingerprint_sha256
        if replay.fingerprint_sha256 != expected_sha:
            raise SourceStateReplayError("SOURCE_STATE_FINGERPRINT_MISMATCH")
        return SourceStateReplayReportV1(
            schema_id="SOURCE_STATE_REPLAY_REPORT_V1",
            schema_version=1,
            source_fingerprint_sha256=expected_sha,
            replay_fingerprint_sha256=replay.fingerprint_sha256,
            transition_count=completed,
            status="PASS",
            failure_code=None,
            report_sha256=None,
        )
    finally:
        adapter.close()
