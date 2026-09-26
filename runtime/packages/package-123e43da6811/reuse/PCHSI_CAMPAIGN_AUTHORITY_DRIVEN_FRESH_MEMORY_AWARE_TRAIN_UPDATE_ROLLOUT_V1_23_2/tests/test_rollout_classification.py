from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from live_rollout_job import classify_episode_result


class E:
    def __init__(self,value): self.value=value


def result(sci,op,reason,success):
    return SimpleNamespace(
        scientific_outcome_status=E(sci),
        operational_finalization_status=E(op),
        termination_reason=reason,
        success=success,
    )


def test_scientific_success_and_failure_require_operationally_valid_result():
    assert classify_episode_result(
        result=result("SUCCESS","PUBLISHED","ENVIRONMENT_TERMINATED",True),
        terminal_receipt={"error_code":None},
    )=="SCIENTIFIC_SUCCESS"
    assert classify_episode_result(
        result=result("TASK_FAILURE","PUBLISHED","ENVIRONMENT_TERMINATED",False),
        terminal_receipt={"error_code":None},
    )=="SCIENTIFIC_FAILURE"


def test_reaped_close_preserves_scientific_result_but_unreaped_does_not():
    assert classify_episode_result(
        result=result("TASK_FAILURE","CLOSE_FAILED_RECORDED","ENVIRONMENT_TERMINATED",False),
        terminal_receipt={"error_code":"WORKER_REAPED_NO_CONTAMINATION"},
    )=="SCIENTIFIC_FAILURE"
    assert classify_episode_result(
        result=result("TASK_FAILURE","CLOSE_FAILED_RECORDED","ENVIRONMENT_TERMINATED",False),
        terminal_receipt={"error_code":"WORKER_NOT_REAPED"},
    )=="INFRASTRUCTURE_INVALID"


def test_protocol_and_infrastructure_remain_outside_scientific_failure_count():
    assert classify_episode_result(
        result=result("NOT_PRODUCED","PUBLISHED","PROTOCOL_CONFIGURATION_ERROR",None),
        terminal_receipt={},
    )=="PROTOCOL_INVALID"
    assert classify_episode_result(
        result=result("NOT_PRODUCED","PUBLISHED","INFRASTRUCTURE_ERROR",None),
        terminal_receipt={},
    )=="INFRASTRUCTURE_INVALID"
