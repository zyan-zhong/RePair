"""Hold-open exact source-state replay for Formal Memory Package A.

All source-state identity/state checks remain delegated to the existing audited
replay_source_decision_state_v1().  Only its unconditional final adapter close is
shielded so the verified live environment may continue into a formal cell.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pchsi.evaluation.alfworld_contracts import ResetPublicState, StepPublicState
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
    SourceStateReplayReportV1,
)
from pchsi.memory.source_state_replay import replay_source_decision_state_v1


class ContinuableReplayAdapterV1(Protocol):
    @property
    def exact_gamefile(self) -> str: ...
    def reset(self) -> ResetPublicState: ...
    def step(self, action: str) -> StepPublicState: ...
    def close(self) -> object: ...


class _RecordingCloseShieldV1:
    def __init__(self, adapter: ContinuableReplayAdapterV1):
        self._adapter = adapter
        self.reset_state: ResetPublicState | None = None
        self.step_states: list[StepPublicState] = []
        self.close_request_count = 0

    @property
    def exact_gamefile(self) -> str:
        return self._adapter.exact_gamefile

    def reset(self) -> ResetPublicState:
        value = self._adapter.reset()
        self.reset_state = value
        return value

    def step(self, action: str) -> StepPublicState:
        value = self._adapter.step(action)
        self.step_states.append(value)
        return value

    def close(self) -> None:
        self.close_request_count += 1


@dataclass(slots=True)
class OpenSourceReplaySessionV1:
    source: RegisteredReplaySourceV1
    report: SourceStateReplayReportV1
    adapter: ContinuableReplayAdapterV1
    reset_state: ResetPublicState
    step_states: tuple[StepPublicState, ...]
    _closed: bool = False

    @property
    def current_observation(self) -> str:
        if self.step_states:
            return self.step_states[-1].observation
        return self.reset_state.observation

    @property
    def current_commands(self) -> tuple[str, ...]:
        if self.step_states:
            return self.step_states[-1].menu.commands
        return self.reset_state.menu.commands

    def close(self) -> object | None:
        if self._closed:
            return None
        self._closed = True
        return self.adapter.close()

    def __enter__(self) -> "OpenSourceReplaySessionV1":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def replay_source_decision_state_hold_open_v1(
    *,
    source: RegisteredReplaySourceV1,
    adapter: ContinuableReplayAdapterV1,
) -> OpenSourceReplaySessionV1:
    if not isinstance(source, RegisteredReplaySourceV1):
        raise TypeError("source type mismatch")

    shield = _RecordingCloseShieldV1(adapter)
    try:
        report = replay_source_decision_state_v1(
            source=source,
            adapter=shield,
        )
    except BaseException:
        try:
            adapter.close()
        finally:
            raise

    if shield.close_request_count != 1:
        adapter.close()
        raise RuntimeError("source replay close-shield contract mismatch")
    if shield.reset_state is None:
        adapter.close()
        raise RuntimeError("source replay produced no reset public state")
    if len(shield.step_states) != len(source.transitions):
        adapter.close()
        raise RuntimeError("source replay live transition count mismatch")
    if shield.step_states and shield.step_states[-1].done:
        adapter.close()
        raise RuntimeError("registered source decision state is terminal")

    return OpenSourceReplaySessionV1(
        source=source,
        report=report,
        adapter=adapter,
        reset_state=shield.reset_state,
        step_states=tuple(shield.step_states),
    )
