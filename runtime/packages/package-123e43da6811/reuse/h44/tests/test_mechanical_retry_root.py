from pathlib import Path
import controller
from io_utils import put_json


def test_zero_side_effect_diagnostic_gets_separate_deterministic_mechanical_recovery_root(tmp_path):
    base=tmp_path/'scientific-root';base.mkdir()
    put_json(base/'ROUND_EXECUTION_TERMINAL.json',{
        'schema_id':'CURRENT_CAUSAL_EXECUTION_CONTROLLER_TERMINAL_V1',
        'status':'CURRENT_EXECUTION_STOPPED_WITH_DIAGNOSTIC',
        'training_execution_count':0,
        'full_round_closed':False,
        'next_round_launched':False,
        'max10_released':False,
        'human_scientific_decision_count':0,
        'plan_sha256':'a'*64,
        'error_type':'ImportError','error_message':'fixture'})
    selected=controller.select_operational_attempt_root(base)
    assert selected!=base
    assert selected.parent==base/'mechanical_recovery_attempts'
    assert selected.name
    assert not selected.exists()


def test_side_effected_attempt_is_never_automatically_retried(tmp_path):
    base=tmp_path/'scientific-root';base.mkdir()
    put_json(base/'ROUND_EXECUTION_TERMINAL.json',{
        'schema_id':'CURRENT_CAUSAL_EXECUTION_CONTROLLER_TERMINAL_V1',
        'status':'CURRENT_EXECUTION_STOPPED_WITH_DIAGNOSTIC',
        'training_execution_count':0,
        'full_round_closed':False,'next_round_launched':False,'max10_released':False,
        'human_scientific_decision_count':0,'plan_sha256':'a'*64,
        'error_type':'RuntimeError','error_message':'fixture'})
    put_json(base/'SBATCH_SUBMISSION_INTENT.json',{'plan_sha256':'a'*64,'argv':['sbatch']})
    try:
        controller.select_operational_attempt_root(base)
    except RuntimeError as exc:
        assert 'NO_AUTOMATIC_MECHANICAL_RETRY' in str(exc)
    else:
        raise AssertionError('side-effected attempt was incorrectly retried')
