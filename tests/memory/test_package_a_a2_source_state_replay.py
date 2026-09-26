from pathlib import Path
import pytest
from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_contracts import GamefileIdentityLatch, MenuSnapshot, ResetPublicState, StepPublicState
from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import sha256_text
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1, ReplayTransitionExpectationV1,
    build_source_decision_state_fingerprint_v1,
)
from pchsi.memory.source_state_replay import replay_source_decision_state_v1, SourceStateReplayError

class Adapter:
    def __init__(self, gamefile, wrong=False):
        self.exact_gamefile = gamefile
        self.wrong = wrong
        self.closed = False
    def reset(self):
        return ResetPublicState(
            observation="reset",
            menu=MenuSnapshot(commands=("look",), sequence_sha256=sha256_string_sequence(("look",))),
            gamefile_latch=GamefileIdentityLatch(resolved_gamefile=self.exact_gamefile),
        )
    def step(self, action):
        return StepPublicState(
            observation="wrong" if self.wrong else "result",
            menu=MenuSnapshot(commands=("inventory",), sequence_sha256=sha256_string_sequence(("inventory",))),
            score=0, done=False, won=False,
        )
    def close(self):
        self.closed = True

def _source(tmp_path):
    gamefile = str((tmp_path/"g.tw-pddl").resolve())
    reset_obs, result_obs = sha256_text("reset"), sha256_text("result")
    reset_menu = sha256_string_sequence(("look",))
    result_menu = sha256_string_sequence(("inventory",))
    budget = BudgetState(policy_attempt_count=1, environment_step_count=1)
    fp = build_source_decision_state_fingerprint_v1(
        source_task_id="task", source_gamefile_sha256="a"*64,
        source_bundle_sha256="b"*64, source_policy_condition="P4-R1-Q2-BAD-TRAIN17",
        executed_prefix_sha256="c"*64, observation_sha256=result_obs,
        menu_sequence_sha256=result_menu, memory_m0_sha256="d"*64,
        interface_feedback_code=None, budget_state=budget, model_call_index=1,
        base_policy_input_sha256="e"*64,
    )
    return RegisteredReplaySourceV1(
        schema_id="REGISTERED_SOURCE_STATE_REPLAY_V1", schema_version=1,
        source_task_id="task", exact_gamefile=gamefile,
        source_gamefile_sha256="a"*64, source_bundle_sha256="b"*64,
        source_policy_condition="P4-R1-Q2-BAD-TRAIN17",
        runtime_manifest_sha256="f"*64, executed_prefix_sha256="c"*64,
        reset_observation_sha256=reset_obs, reset_menu_sequence_sha256=reset_menu,
        transitions=(ReplayTransitionExpectationV1(
            0, "look", reset_obs, reset_menu, result_obs, result_menu, 0, False, False
        ),),
        memory_m0_sha256="d"*64, interface_feedback_code=None,
        budget_state=budget, model_call_index=1, base_policy_input_sha256="e"*64,
        expected_source_fingerprint=fp,
    )

def test_replay_pass_and_fail_closed(tmp_path):
    source = _source(tmp_path)
    ok = Adapter(source.exact_gamefile)
    assert replay_source_decision_state_v1(source=source, adapter=ok).status == "PASS"
    assert ok.closed
    bad = Adapter(source.exact_gamefile, wrong=True)
    with pytest.raises(SourceStateReplayError):
        replay_source_decision_state_v1(source=source, adapter=bad)
    assert bad.closed
