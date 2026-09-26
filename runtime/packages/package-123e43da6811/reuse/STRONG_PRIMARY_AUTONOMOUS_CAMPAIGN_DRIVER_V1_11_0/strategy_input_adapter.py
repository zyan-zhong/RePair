from __future__ import annotations
from collections.abc import Mapping
REQ=('principal_bottleneck','current_subgoal','expected_next_event','expected_state_change','progress_criterion','recovery_trigger','fallback_condition','action','evidence_refs')
def build_verified_strategy_input(row:Mapping, state_result:Mapping, verification_receipt_sha256:str, strategy_sha256:str):
    strategy=row.get('strategy') if isinstance(row.get('strategy'),Mapping) else row
    for k in REQ:
        if k not in strategy: raise ValueError('STRATEGY_FIELD_MISSING:'+k)
    if str(state_result.get('stable_effect')).upper()!='BENEFIT': raise ValueError('NON_BENEFIT_STRATEGY_FORBIDDEN')
    ctx=row.get('policy_visible_context'); sem=row.get('source_semantic_row_sha256'); ss=row.get('source_state_sha256')
    if not isinstance(ctx,dict) or not isinstance(sem,str) or len(sem)!=64 or not isinstance(ss,str) or len(ss)!=64: raise ValueError('POLICY_CONTEXT_OR_SOURCE_IDENTITY_MISSING')
    return {'schema_id':'VERIFIED_POLICY_STRATEGY_MATERIALIZATION_INPUT_V1','schema_version':1,'source_state_sha256':ss,'source_semantic_row_sha256':sem,'policy_visible_context':ctx,'strategy':{**{k:strategy[k] for k in REQ},'verified_strategy_sha256':strategy_sha256},'verification':{'same_state_f0f1_verified':True,'verification_label':'BENEFIT','outcome_visible_to_policy':False,'reward_visible_to_policy':False,'verified_strategy_sha256':strategy_sha256,'verification_receipt_sha256':verification_receipt_sha256}}
