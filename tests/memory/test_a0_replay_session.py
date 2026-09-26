from __future__ import annotations

from dataclasses import dataclass
import pytest

import pchsi.memory.a0_replay_session as target
from pchsi.evaluation.alfworld_contracts import (
    GamefileIdentityLatch,
    MenuSnapshot,
    ResetPublicState,
)
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
    SourceDecisionStateFingerprintV1,
    SourceStateReplayReportV1,
)
from pchsi.evaluation.budget import BudgetState


def _sha(ch: str) -> str:
    return ch * 64


def _source() -> RegisteredReplaySourceV1:
    fp = SourceDecisionStateFingerprintV1(
        schema_id="SOURCE_DECISION_STATE_FINGERPRINT_V1",
        schema_version=1,
        source_task_id="task",
        source_gamefile_sha256=_sha("a"),
        source_bundle_sha256=_sha("b"),
        source_policy_condition="P4-R1-Q2-BAD-TRAIN17",
        executed_prefix_sha256=_sha("c"),
        observation_sha256=_sha("3"),
        menu_sequence_sha256=_sha("4"),
        memory_m0_sha256=_sha("f"),
        interface_feedback_code=None,
        budget_state=BudgetState(),
        model_call_index=0,
        base_policy_input_sha256=_sha("1"),
        fingerprint_sha256=None,
    )
    return RegisteredReplaySourceV1(
        schema_id="REGISTERED_SOURCE_STATE_REPLAY_V1",
        schema_version=1,
        source_task_id="task",
        exact_gamefile="/tmp/game.tw-pddl",
        source_gamefile_sha256=_sha("a"),
        source_bundle_sha256=_sha("b"),
        source_policy_condition="P4-R1-Q2-BAD-TRAIN17",
        runtime_manifest_sha256=_sha("2"),
        executed_prefix_sha256=_sha("c"),
        reset_observation_sha256=_sha("3"),
        reset_menu_sequence_sha256=_sha("4"),
        transitions=(),
        memory_m0_sha256=_sha("f"),
        interface_feedback_code=None,
        budget_state=BudgetState(),
        model_call_index=0,
        base_policy_input_sha256=_sha("1"),
        expected_source_fingerprint=fp,
    )


@dataclass
class FakeAdapter:
    exact_gamefile: str = "/tmp/game.tw-pddl"
    close_count: int = 0

    def reset(self):
        return ResetPublicState(
            observation="Your task is to: test",
            menu=MenuSnapshot(("look",), _sha("4")),
            gamefile_latch=GamefileIdentityLatch(self.exact_gamefile),
        )

    def step(self, action):
        raise AssertionError("unexpected step")

    def close(self):
        self.close_count += 1
        return "closed"


def _report(source):
    return SourceStateReplayReportV1(
        schema_id="SOURCE_STATE_REPLAY_REPORT_V1",
        schema_version=1,
        source_fingerprint_sha256=source.expected_source_fingerprint.fingerprint_sha256,
        replay_fingerprint_sha256=source.expected_source_fingerprint.fingerprint_sha256,
        transition_count=0,
        status="PASS",
        failure_code=None,
        report_sha256=None,
    )


def test_successful_replay_is_kept_open_until_session_close(monkeypatch):
    source = _source()
    adapter = FakeAdapter()

    def fake_replay(*, source, adapter):
        adapter.reset()
        adapter.close()
        return _report(source)

    monkeypatch.setattr(target, "replay_source_decision_state_v1", fake_replay)
    session = target.replay_source_decision_state_hold_open_v1(
        source=source,
        adapter=adapter,
    )

    assert adapter.close_count == 0
    assert session.current_commands == ("look",)
    assert session.close() == "closed"
    assert adapter.close_count == 1
    assert session.close() is None
    assert adapter.close_count == 1


def test_failed_replay_closes_real_adapter(monkeypatch):
    source = _source()
    adapter = FakeAdapter()

    def fail(*, source, adapter):
        adapter.close()
        raise ValueError("replay failed")

    monkeypatch.setattr(target, "replay_source_decision_state_v1", fail)

    with pytest.raises(ValueError, match="replay failed"):
        target.replay_source_decision_state_hold_open_v1(
            source=source,
            adapter=adapter,
        )

    assert adapter.close_count == 1
