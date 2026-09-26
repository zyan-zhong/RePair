from __future__ import annotations
import hashlib,json
from collections.abc import Mapping,Sequence

MANIFEST_SCHEMA='CLEAN_REFERENCE_F0F1_EXECUTION_MANIFEST_V2'
BINDING_SCHEMA='CLEAN_REFERENCE_F0F1_BRANCH_BINDING_V2'


def _canon(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def _hash(domain,v): return hashlib.sha256(domain.encode()+b'\0'+_canon(v)).hexdigest()
def _sha(v,n):
    if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v): raise ValueError(n+' must be lowercase SHA-256')
    return v
def _text(v,n):
    if not isinstance(v,str) or not v or '\x00' in v: raise ValueError(n+' must be non-empty NUL-free string')
    return v

def _state_row(row:Mapping[str,object],pos:int)->dict[str,object]:
    req={'source_state_sha256','research_candidate_id','source_candidate_sha256','candidate_artifact_path','candidate_artifact_file_sha256','replay_source_path','replay_source_file_sha256','runtime_binding_path','runtime_binding_file_sha256','active_snapshot_sha256','token_budget_contract_sha256','policy_model','policy_version','source_task_id','intervention_kind','typed_short_option_contract_sha256','typed_short_option_registry_sha256','typed_short_option_registry_path','typed_short_option_dispatch_mode','typed_short_option_max_intervention_steps','typed_short_option_legacy_semantic_coverage','registered_option_actions','source_termination_condition_sha256'}
    if set(row)!=req: raise ValueError('selected state fields mismatch')
    out=dict(row); out['state_position']=pos
    for k in ('source_state_sha256','research_candidate_id','source_candidate_sha256','candidate_artifact_file_sha256','replay_source_file_sha256','runtime_binding_file_sha256','active_snapshot_sha256','token_budget_contract_sha256','typed_short_option_contract_sha256','typed_short_option_registry_sha256','source_termination_condition_sha256'): _sha(out[k],k)
    if out['research_candidate_id']==out['source_candidate_sha256']: raise ValueError('research_candidate_id must be distinct from source_candidate_sha256')
    for k in ('candidate_artifact_path','replay_source_path','runtime_binding_path','typed_short_option_registry_path','policy_model','policy_version','source_task_id'): _text(out[k],k)
    if out['intervention_kind']!='TYPED_SHORT_OPTION': raise ValueError('intervention_kind must be TYPED_SHORT_OPTION')
    if out['typed_short_option_dispatch_mode'] not in {'ORDERED_SEQUENCE','FIRST_ADMISSIBLE_THEN_RETURN'}: raise ValueError('typed_short_option_dispatch_mode invalid')
    if type(out['typed_short_option_max_intervention_steps']) is not int or out['typed_short_option_max_intervention_steps'] <= 0: raise ValueError('typed_short_option_max_intervention_steps invalid')
    _text(out['typed_short_option_legacy_semantic_coverage'],'typed_short_option_legacy_semantic_coverage')
    acts=out['registered_option_actions']
    if not isinstance(acts,list) or not 1<=len(acts)<=4 or any(not isinstance(x,str) or not x for x in acts): raise ValueError('registered_option_actions invalid')
    return out

def build_execution_manifest_v2(*,round_id:str,implementation_commit:str,source_authority_sha256:str,selected_states:Sequence[Mapping[str,object]],paired_seeds:Sequence[int],stable_direction_min_pairs:int)->dict[str,object]:
    _text(round_id,'round_id'); _sha(source_authority_sha256,'source_authority_sha256')
    if not isinstance(implementation_commit,str) or len(implementation_commit)!=40: raise ValueError('implementation_commit must be 40-char git SHA')
    states=[_state_row(r,i) for i,r in enumerate(selected_states)]
    if not states: raise ValueError('selected_states must be non-empty')
    if len({r['source_state_sha256'] for r in states})!=len(states): raise ValueError('duplicate source state')
    seeds=list(paired_seeds)
    if not seeds or any(type(s) is not int or s<0 for s in seeds) or len(set(seeds))!=len(seeds): raise ValueError('paired_seeds invalid')
    if type(stable_direction_min_pairs) is not int or not 1<=stable_direction_min_pairs<=len(seeds): raise ValueError('stable_direction_min_pairs invalid')
    branches=[]
    for st in states:
        for rep,seed in enumerate(seeds,start=1):
            pair_material={'round_id':round_id,'source_state_sha256':st['source_state_sha256'],'source_candidate_sha256':st['source_candidate_sha256'],'repetition':rep,'continuation_seed':seed}
            pair_id=_hash('CLEAN_REFERENCE_F0F1_PAIR_ID_V2',pair_material)
            for branch in ('F0','F1'):
                branches.append({**st,'round_id':round_id,'pair_id':pair_id,'repetition':rep,'branch':branch,'continuation_seed':seed})
    payload={'schema_id':MANIFEST_SCHEMA,'schema_version':2,'round_id':round_id,'implementation_commit':implementation_commit,'source_authority_sha256':source_authority_sha256,'seed_schedule':seeds,'state_count':len(states),'paired_repetitions_per_state':len(seeds),'stable_direction_min_pairs':stable_direction_min_pairs,'pair_count':len(states)*len(seeds),'branch_count':len(states)*len(seeds)*2,'effect_authority':'INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY','outcome_adaptive_reselection_allowed':False,'outcome_adaptive_budget_change_allowed':False,'branches':branches,'execution_manifest_sha256':'0'*64}
    payload['execution_manifest_sha256']=_hash(MANIFEST_SCHEMA,{k:v for k,v in payload.items() if k!='execution_manifest_sha256'})
    return validate_execution_manifest_v2(payload)

def validate_execution_manifest_v2(value:Mapping[str,object])->dict[str,object]:
    p=dict(value)
    if p.get('schema_id')!=MANIFEST_SCHEMA or p.get('schema_version')!=2: raise ValueError('execution manifest schema mismatch')
    branches=p.get('branches'); n=p.get('state_count'); reps=p.get('paired_repetitions_per_state'); seeds=p.get('seed_schedule')
    if type(n) is not int or n<=0 or type(reps) is not int or reps<=0 or not isinstance(branches,list): raise ValueError('execution manifest population invalid')
    if not isinstance(seeds,list) or len(seeds)!=reps or any(type(x) is not int or x<0 for x in seeds) or len(set(seeds))!=len(seeds): raise ValueError('execution manifest seed schedule invalid')
    threshold=p.get('stable_direction_min_pairs')
    if type(threshold) is not int or not 1<=threshold<=reps: raise ValueError('execution manifest stable threshold invalid')
    if p.get('effect_authority')!='INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY' or p.get('outcome_adaptive_reselection_allowed') is not False or p.get('outcome_adaptive_budget_change_allowed') is not False: raise ValueError('execution manifest scientific authority flags invalid')
    if p.get('pair_count')!=n*reps or p.get('branch_count')!=n*reps*2 or len(branches)!=p['branch_count']: raise ValueError('execution manifest population mismatch')
    _sha(p.get('source_authority_sha256'),'source_authority_sha256'); _sha(p.get('execution_manifest_sha256'),'execution_manifest_sha256')
    if not isinstance(p.get('implementation_commit'),str) or len(p['implementation_commit'])!=40: raise ValueError('execution manifest implementation_commit invalid')
    keys=[]; positions=set(); round_id=p.get('round_id')
    state_keys={'source_state_sha256','research_candidate_id','source_candidate_sha256','candidate_artifact_path','candidate_artifact_file_sha256','replay_source_path','replay_source_file_sha256','runtime_binding_path','runtime_binding_file_sha256','active_snapshot_sha256','token_budget_contract_sha256','policy_model','policy_version','source_task_id','intervention_kind','typed_short_option_contract_sha256','typed_short_option_registry_sha256','typed_short_option_registry_path','typed_short_option_dispatch_mode','typed_short_option_max_intervention_steps','typed_short_option_legacy_semantic_coverage','registered_option_actions','source_termination_condition_sha256'}
    for row in branches:
        if not isinstance(row,Mapping): raise ValueError('execution manifest branch must be object')
        if row.get('round_id')!=round_id or row.get('branch') not in {'F0','F1'}: raise ValueError('execution manifest branch identity invalid')
        if type(row.get('state_position')) is not int or not 0<=row['state_position']<n: raise ValueError('execution manifest state position invalid')
        if type(row.get('repetition')) is not int or not 1<=row['repetition']<=reps or row.get('continuation_seed')!=seeds[row['repetition']-1]: raise ValueError('execution manifest repetition/seed invalid')
        _sha(row.get('pair_id'),'pair_id')
        _state_row({k:row[k] for k in state_keys},row['state_position'])
        keys.append((row['pair_id'],row['branch'])); positions.add(row['state_position'])
    if len(set(keys))!=len(keys) or positions!=set(range(n)): raise ValueError('execution manifest branch keys/state positions invalid')
    expected=_hash(MANIFEST_SCHEMA,{k:v for k,v in p.items() if k!='execution_manifest_sha256'})
    if p['execution_manifest_sha256']!=expected: raise ValueError('execution manifest SHA mismatch')
    return p

def build_branch_bindings_v2(manifest:Mapping[str,object])->tuple[dict[str,object],...]:
    m=validate_execution_manifest_v2(manifest); out=[]
    for row in m['branches']:
        b={'schema_id':BINDING_SCHEMA,'schema_version':2,'execution_manifest_sha256':m['execution_manifest_sha256'],'implementation_commit':m['implementation_commit'],**dict(row),'branch_binding_sha256':'0'*64}
        b['branch_binding_sha256']=_hash(BINDING_SCHEMA,{k:v for k,v in b.items() if k!='branch_binding_sha256'})
        out.append(validate_branch_binding_v2(b))
    return tuple(out)

def validate_branch_binding_v2(value:Mapping[str,object])->dict[str,object]:
    p=dict(value)
    if p.get('schema_id')!=BINDING_SCHEMA or p.get('schema_version')!=2: raise ValueError('branch binding schema mismatch')
    if p.get('branch') not in {'F0','F1'}: raise ValueError('branch invalid')
    if not isinstance(p.get('implementation_commit'),str) or len(p['implementation_commit'])!=40: raise ValueError('branch implementation_commit invalid')
    if type(p.get('state_position')) is not int or p['state_position']<0 or type(p.get('repetition')) is not int or p['repetition']<=0 or type(p.get('continuation_seed')) is not int or p['continuation_seed']<0: raise ValueError('branch population identity invalid')
    _sha(p.get('pair_id'),'pair_id'); _sha(p.get('branch_binding_sha256'),'branch_binding_sha256'); _sha(p.get('execution_manifest_sha256'),'execution_manifest_sha256')
    expected=_hash(BINDING_SCHEMA,{k:v for k,v in p.items() if k!='branch_binding_sha256'})
    if p['branch_binding_sha256']!=expected: raise ValueError('branch binding hash mismatch')
    return p
