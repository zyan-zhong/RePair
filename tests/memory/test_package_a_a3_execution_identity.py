from dataclasses import replace
import pytest
from pchsi.evaluation.budget import BudgetState
from pchsi.memory.memory_execution_identity import build_memory_bound_replay_pair_v1
from pchsi.memory.source_state_contracts import build_source_decision_state_fingerprint_v1

def test_pair_differs_only_in_memory_exposure():
    fp = build_source_decision_state_fingerprint_v1(
        source_task_id="task", source_gamefile_sha256="a"*64,
        source_bundle_sha256="b"*64, source_policy_condition="cond",
        executed_prefix_sha256="c"*64, observation_sha256="d"*64,
        menu_sequence_sha256="e"*64, memory_m0_sha256="f"*64,
        interface_feedback_code=None, budget_state=BudgetState(),
        model_call_index=0, base_policy_input_sha256="1"*64,
    )
    pair = build_memory_bound_replay_pair_v1(
        source_fingerprint=fp, policy_checkpoint_id="p1",
        memory_snapshot_id="2"*64,
        memory_on_projection_sha256s=("3"*64,), continuation_seed=17,
    )
    assert pair.memory_off.projection_artifact_sha256s == ()
    assert pair.memory_on.projection_artifact_sha256s == ("3"*64,)
    with pytest.raises(ValueError):
        replace(pair, memory_on=replace(pair.memory_on, source_task_id="other", cell_id=None))
