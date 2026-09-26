import importlib.util
from pathlib import Path

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_contracts import (
    GamefileIdentityLatch, MenuSnapshot, ResetPublicState, StepPublicState,
)
from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import sha256_text
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1, ReplayTransitionExpectationV1,
    build_source_decision_state_fingerprint_v1,
)

def _qualifier():
    path = Path("scripts/memory/qualify_source_state_replay_v1.py")
    spec = importlib.util.spec_from_file_location("_qualifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Adapter:
    def __init__(self, gamefile):
        self.exact_gamefile = gamefile
    def reset(self):
        return ResetPublicState(
            observation="reset",
            menu=MenuSnapshot(commands=("look",), sequence_sha256=sha256_string_sequence(("look",))),
            gamefile_latch=GamefileIdentityLatch(resolved_gamefile=self.exact_gamefile),
        )
    def step(self, action):
        return StepPublicState(
            observation="result",
            menu=MenuSnapshot(commands=("inventory",), sequence_sha256=sha256_string_sequence(("inventory",))),
            score=0, done=False, won=False,
        )
    def close(self): pass

def test_two_independent_replays_match(tmp_path):
    gamefile = str((tmp_path/"game.tw-pddl").resolve())
    reset_obs, result_obs = sha256_text("reset"), sha256_text("result")
    reset_menu, result_menu = sha256_string_sequence(("look",)), sha256_string_sequence(("inventory",))
    budget = BudgetState(policy_attempt_count=1, environment_step_count=1)
    fp = build_source_decision_state_fingerprint_v1(
        source_task_id="task", source_gamefile_sha256="a"*64,
        source_bundle_sha256="b"*64, source_policy_condition="cond",
        executed_prefix_sha256="c"*64, observation_sha256=result_obs,
        menu_sequence_sha256=result_menu, memory_m0_sha256="d"*64,
        interface_feedback_code=None, budget_state=budget,
        model_call_index=1, base_policy_input_sha256="e"*64,
    )
    source = RegisteredReplaySourceV1(
        "REGISTERED_SOURCE_STATE_REPLAY_V1", 1, "task", gamefile,
        "a"*64, "b"*64, "cond", "f"*64, "c"*64,
        reset_obs, reset_menu,
        (ReplayTransitionExpectationV1(
            0, "look", reset_obs, reset_menu, result_obs, result_menu, 0, False, False
        ),),
        "d"*64, None, budget, 1, "e"*64, fp,
    )
    first, second = _qualifier().qualify_case_with_adapter_factory_v1(
        source=source,
        adapter_factory=lambda s: Adapter(s.exact_gamefile),
    )
    assert first.replay_fingerprint_sha256 == second.replay_fingerprint_sha256
