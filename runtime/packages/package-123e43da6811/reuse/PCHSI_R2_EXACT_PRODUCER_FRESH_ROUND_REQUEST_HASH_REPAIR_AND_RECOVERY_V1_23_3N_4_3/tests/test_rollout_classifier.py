from dataclasses import dataclass
from enum import Enum

from formal_rollout_support import classify_episode_result

class Sci(str, Enum):
    NOT_PRODUCED = "FUTURE_NOT_PRODUCED"
    SUCCESS = "FUTURE_SUCCESS_VALUE"
    TASK_FAILURE = "FUTURE_FAILURE_VALUE"

class Op(str, Enum):
    STAGING = "FUTURE_STAGING"
    PUBLISHED = "FUTURE_PUBLISHED"
    PUBLICATION_PENDING = "FUTURE_PENDING"
    CLOSE_FAILED_RECORDED = "FUTURE_CLOSE"
    ARTIFACT_IO_FAILED = "FUTURE_IO"

@dataclass
class Result:
    scientific_outcome_status: Sci
    operational_finalization_status: Op
    termination_reason: str
    success: bool | None

def test_scientific_success_uses_member_identity_not_value_literal():
    r=Result(Sci.SUCCESS,Op.PUBLISHED,"ENVIRONMENT_TERMINATED",True)
    assert classify_episode_result(result=r,terminal_receipt=None)=="SCIENTIFIC_SUCCESS"

def test_scientific_failure_uses_member_identity_not_value_literal():
    r=Result(Sci.TASK_FAILURE,Op.PUBLISHED,"ENVIRONMENT_STEP_BUDGET_EXHAUSTED",False)
    assert classify_episode_result(result=r,terminal_receipt=None)=="SCIENTIFIC_FAILURE"
