from __future__ import annotations

def validate_handoff(gap,post):
    if gap.get('schema_id')!='STRONG_PRIMARY_R1_HYDRATED_DOWNSTREAM_BINDING_GAP_V1': raise ValueError('V110_GAP_SCHEMA_REQUIRED')
    if post.get('schema_id')!='STRONG_PRIMARY_R1_HYDRATED_PLANNER_POST_ACCEPTED_V1': raise ValueError('V110_POST_SCHEMA_REQUIRED')
    if gap.get('round_id')!=post.get('round_id'): raise ValueError('V110_ROUND_ID_MISMATCH')
    if gap.get('result_package_sha256')!=post.get('result_package_sha256'): raise ValueError('V110_RESULT_SHA_MISMATCH')
    r=gap.get('route')
    if r not in {'NO_TRAINING_UPDATE','VERIFIED_BENEFIT_TRAINING'}: raise ValueError('V110_ROUTE_INVALID')
    return {'round_id':gap['round_id'],'route':r,'result_package_sha256':gap['result_package_sha256']}

def classify_v110_boundary(*,gap,post,verifier_gate):
    if post is None: return {'action':'WAIT_PREDECESSOR'}
    if post.get('schema_id')!='STRONG_PRIMARY_R1_HYDRATED_PLANNER_POST_ACCEPTED_V1': raise ValueError('V110_POST_SCHEMA_REQUIRED')
    if post.get('round_id')!=verifier_gate.get('round_id') or post.get('result_package_sha256')!=verifier_gate.get('result_package_sha256'):
        raise ValueError('V110_POST_VERIFIER_BINDING_MISMATCH')
    counts=verifier_gate.get('stable_effect_counts')
    if not isinstance(counts,dict) or type(counts.get('BENEFIT')) is not int: raise ValueError('VERIFIER_COUNTS_REQUIRED')
    if gap is not None:
        return {'action':'USE_EXACT_V110_GAP','handoff':validate_handoff(gap,post)}
    if post.get('route')=='NO_TRAINING_UPDATE' and post.get('verified_benefit_count')==0 and counts['BENEFIT']==0:
        return {'action':'RECOVER_NO_TRAIN_POST_ONLY','round_id':post['round_id'],'route':'NO_TRAINING_UPDATE'}
    if post.get('route')=='VERIFIED_BENEFIT_TRAINING' or counts['BENEFIT']>0:
        return {'action':'WAIT_EXACT_TRAIN_GAP_NO_FABRICATION','round_id':post['round_id'],'route':'VERIFIED_BENEFIT_TRAINING'}
    return {'action':'FAIL_CLOSED'}

def transition_after_round(status):
    if status.get('phase')!='HYDRATED_DOWNSTREAM_GAP': return {'action':'WAIT_PREDECESSOR'}
    if status.get('route')=='NO_TRAINING_UPDATE': return {'action':'AUTO_CLOSE_NO_TRAIN'}
    if status.get('route')=='VERIFIED_BENEFIT_TRAINING': return {'action':'AUTO_TRAIN_EVALUATE'}
    return {'action':'FAIL_CLOSED'}
