from __future__ import annotations

from dataclasses import dataclass
from .common import hashed_payload, require_nonnegative_int, require_text

OUTCOMES={'PROMOTED','ROLLED_BACK','NO_TRAINING_UPDATE','PROTOCOL_INFRA_INVALID'}

@dataclass(frozen=True)
class ScientificRoundGovernanceV1:
    valid_rounds_consumed: int
    consecutive_no_promotion: int
    invalid_attempt_count: int
    max_valid_rounds: int
    no_promotion_patience: int
    stop: bool
    stop_reason: str | None
    last_outcome: str | None
    governance_sha256: str
    def to_dict(self)->dict[str,object]:
        return {'schema_id':'SCIENTIFIC_ROUND_GOVERNANCE_V1','schema_version':1,
            'valid_rounds_consumed':self.valid_rounds_consumed,
            'consecutive_no_promotion':self.consecutive_no_promotion,
            'invalid_attempt_count':self.invalid_attempt_count,
            'max_valid_rounds':self.max_valid_rounds,
            'no_promotion_patience':self.no_promotion_patience,
            'stop':self.stop,'stop_reason':self.stop_reason,
            'last_outcome':self.last_outcome,'governance_sha256':self.governance_sha256}

def _freeze(v:int,n:int,i:int,last:str|None)->ScientificRoundGovernanceV1:
    stop=False; reason=None
    if v>=10: stop=True; reason='MAX_SCIENTIFIC_ROUNDS_REACHED'
    elif n>=3: stop=True; reason='NO_PROMOTION_PATIENCE_EXHAUSTED'
    payload={'schema_id':'SCIENTIFIC_ROUND_GOVERNANCE_V1','schema_version':1,
        'valid_rounds_consumed':v,'consecutive_no_promotion':n,'invalid_attempt_count':i,
        'max_valid_rounds':10,'no_promotion_patience':3,'stop':stop,'stop_reason':reason,'last_outcome':last}
    h=hashed_payload(domain='SCIENTIFIC_ROUND_GOVERNANCE_V1',hash_field='governance_sha256',payload=payload)
    return ScientificRoundGovernanceV1(**{k:h[k] for k in ScientificRoundGovernanceV1.__dataclass_fields__})

def new_scientific_round_governance()->ScientificRoundGovernanceV1:
    return _freeze(0,0,0,None)

def advance_scientific_round_governance(state:ScientificRoundGovernanceV1, *, outcome:str)->ScientificRoundGovernanceV1:
    if not isinstance(state,ScientificRoundGovernanceV1): raise TypeError('state must be ScientificRoundGovernanceV1')
    require_text('outcome',outcome)
    if outcome not in OUTCOMES: raise ValueError('unsupported round outcome')
    if state.stop: raise ValueError('outer loop already stopped')
    v,n,i=state.valid_rounds_consumed,state.consecutive_no_promotion,state.invalid_attempt_count
    if outcome=='PROTOCOL_INFRA_INVALID': i+=1
    else:
        v+=1
        n=0 if outcome=='PROMOTED' else n+1
    return _freeze(v,n,i,outcome)
