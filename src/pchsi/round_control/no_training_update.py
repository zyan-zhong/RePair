from __future__ import annotations

from dataclasses import dataclass

from .common import hashed_payload, require_nonnegative_int, require_sha256, require_text


@dataclass(frozen=True)
class NoTrainingUpdateV1:
    round_id: str
    parent_policy_id: str
    post_plan_sha256: str
    verifier_result_sha256: str
    verified_benefit_count: int
    verified_harm_count: int
    verified_neutral_count: int
    verified_uncertain_count: int
    scientifically_valid_round: bool
    scientific_attempt_consumed: bool
    candidate_policy_created: bool
    training_execution_count: int
    parent_policy_retained: bool
    reason: str
    disposition_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            'schema_id': 'NO_TRAINING_UPDATE_V1', 'schema_version': 1,
            'round_id': self.round_id, 'parent_policy_id': self.parent_policy_id,
            'post_plan_sha256': self.post_plan_sha256,
            'verifier_result_sha256': self.verifier_result_sha256,
            'verified_benefit_count': self.verified_benefit_count,
            'verified_harm_count': self.verified_harm_count,
            'verified_neutral_count': self.verified_neutral_count,
            'verified_uncertain_count': self.verified_uncertain_count,
            'scientifically_valid_round': self.scientifically_valid_round,
            'scientific_attempt_consumed': self.scientific_attempt_consumed,
            'candidate_policy_created': self.candidate_policy_created,
            'training_execution_count': self.training_execution_count,
            'parent_policy_retained': self.parent_policy_retained,
            'reason': self.reason,
            'disposition_sha256': self.disposition_sha256,
        }


def freeze_no_training_update(*, round_id: str, parent_policy_id: str,
    post_plan_sha256: str, verifier_result_sha256: str,
    verified_benefit_count: int, verified_harm_count: int,
    verified_neutral_count: int, verified_uncertain_count: int,
    scientifically_valid_round: bool, reason: str='NO_VERIFIED_BENEFIT') -> NoTrainingUpdateV1:
    require_text('round_id', round_id); require_text('parent_policy_id', parent_policy_id)
    require_sha256('post_plan_sha256', post_plan_sha256); require_sha256('verifier_result_sha256', verifier_result_sha256)
    counts={
        'verified_benefit_count':verified_benefit_count,
        'verified_harm_count':verified_harm_count,
        'verified_neutral_count':verified_neutral_count,
        'verified_uncertain_count':verified_uncertain_count,
    }
    for k,v in counts.items(): require_nonnegative_int(k,v)
    if scientifically_valid_round is not True:
        raise ValueError('no-training scientific closeout cannot represent protocol/infrastructure-invalid attempts')
    if verified_benefit_count != 0:
        raise ValueError('no-training closeout requires zero verified Benefit strategies')
    if reason not in {'NO_VERIFIED_BENEFIT','NO_ELIGIBLE_VERIFIED_TRAINING_EVIDENCE'}:
        raise ValueError('unsupported no-training reason')
    payload={
        'schema_id':'NO_TRAINING_UPDATE_V1','schema_version':1,
        'round_id':round_id,'parent_policy_id':parent_policy_id,
        'post_plan_sha256':post_plan_sha256,'verifier_result_sha256':verifier_result_sha256,
        **counts,'scientifically_valid_round':True,'scientific_attempt_consumed':True,
        'candidate_policy_created':False,'training_execution_count':0,
        'parent_policy_retained':True,'reason':reason,
    }
    h=hashed_payload(domain='NO_TRAINING_UPDATE_V1',hash_field='disposition_sha256',payload=payload)
    return NoTrainingUpdateV1(**{k:h[k] for k in NoTrainingUpdateV1.__dataclass_fields__})
