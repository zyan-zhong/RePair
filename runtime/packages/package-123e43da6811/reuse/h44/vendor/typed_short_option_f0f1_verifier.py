from __future__ import annotations
import hashlib,json
from collections import Counter,defaultdict
from collections.abc import Mapping,Sequence
from typed_short_option_f0f1_contracts import validate_execution_manifest_v2,build_branch_bindings_v2

def _canon(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def _hash(domain,v): return hashlib.sha256(domain.encode()+b'\0'+_canon(v)).hexdigest()

def _effect(f0:bool|None,f1:bool|None,complete:bool)->str:
    if not complete or type(f0) is not bool or type(f1) is not bool: return 'UNCERTAIN'
    if not f0 and f1:return 'BENEFIT'
    if f0 and not f1:return 'HARM'
    return 'NEUTRAL'

def verify_records(manifest:Mapping[str,object],records:Sequence[Mapping[str,object]])->dict[str,object]:
    m=validate_execution_manifest_v2(manifest); expected=build_branch_bindings_v2(m)
    by_sha={str(r.get('branch_binding_sha256')):dict(r) for r in records}
    if len(by_sha)!=len(records): raise ValueError('duplicate branch evidence binding identity')
    pairs=defaultdict(dict); state_meta={}
    for b in expected:
        rec=by_sha.get(b['branch_binding_sha256'])
        if rec is None:
            # missing evidence is represented as an incomplete record
            rec={'evidence_complete':False,'scientific_outcome_produced':False,'terminal_success':None,'intervention_sequence':[],'typed_short_option_execution':None,'option_environment_step_count':0}
        else:
            for key in ('execution_manifest_sha256','pair_id','source_state_sha256','source_candidate_sha256','research_candidate_id','repetition','branch','continuation_seed','intervention_kind','typed_short_option_contract_sha256','typed_short_option_registry_sha256'):
                if rec.get(key)!=b.get(key): raise ValueError('branch evidence differs from binding: '+key)
            seq=rec.get('intervention_sequence')
            if not isinstance(seq,list): raise ValueError('intervention_sequence must be array')
            record_complete=bool(rec.get('evidence_complete')) and bool(rec.get('scientific_outcome_produced'))
            if b['branch']=='F0':
                if seq or rec.get('typed_short_option_execution') is not None or int(rec.get('option_environment_step_count',0))!=0: raise ValueError('F0 must not contain intervention')
            else:
                tx=rec.get('typed_short_option_execution')
                if record_complete:
                    if not isinstance(tx,dict) or tx.get('contract_sha256')!=b['typed_short_option_contract_sha256']: raise ValueError('F1 typed short-option execution identity mismatch')
                elif tx is not None and (not isinstance(tx,dict) or tx.get('contract_sha256')!=b['typed_short_option_contract_sha256']):
                    raise ValueError('incomplete F1 typed short-option execution identity mismatch')
                if int(rec.get('option_environment_step_count',-1))!=len(seq): raise ValueError('F1 option step count mismatch')
                observed=[x.get('action') for x in seq if isinstance(x,dict)]
                registered=list(b['registered_option_actions'])
                mode=b.get('typed_short_option_dispatch_mode')
                if mode=='ORDERED_SEQUENCE':
                    if observed!=registered[:len(observed)]: raise ValueError('F1 intervention sequence differs from registered option prefix')
                elif mode=='FIRST_ADMISSIBLE_THEN_RETURN':
                    if len(observed)>1 or any(action not in registered for action in observed): raise ValueError('F1 first-admissible intervention sequence invalid')
                else:
                    raise ValueError('F1 typed short-option dispatch mode invalid')
        pairs[b['pair_id']][b['branch']]={'binding':b,'record':rec}
        state_meta[b['source_state_sha256']]=b
    pair_rows=[]; state_effects=defaultdict(list); state_costs=defaultdict(int)
    for pair_id,arms in sorted(pairs.items()):
        if set(arms)!={'F0','F1'}: raise ValueError('pair does not contain F0/F1')
        f0=arms['F0']['record']; f1=arms['F1']['record']; b=arms['F1']['binding']
        complete=bool(f0.get('evidence_complete')) and bool(f1.get('evidence_complete')) and bool(f0.get('scientific_outcome_produced')) and bool(f1.get('scientific_outcome_produced')) and int(f1.get('option_environment_step_count',0))>0
        eff=_effect(f0.get('terminal_success'),f1.get('terminal_success'),complete)
        cost=int(f1.get('option_environment_step_count',0))
        coverage=b['typed_short_option_legacy_semantic_coverage']
        pair_rows.append({'pair_id':pair_id,'source_state_sha256':b['source_state_sha256'],'source_candidate_sha256':b['source_candidate_sha256'],'research_candidate_id':b['research_candidate_id'],'repetition':b['repetition'],'continuation_seed':b['continuation_seed'],'effect':eff,'effect_scope':'REGISTERED_TYPED_OPERATIONALIZATION_ONLY','typed_short_option_legacy_semantic_coverage':coverage,'f0_terminal_success':f0.get('terminal_success'),'f1_terminal_success':f1.get('terminal_success'),'option_environment_steps':cost,'evidence_complete':complete})
        state_effects[b['source_state_sha256']].append(eff); state_costs[b['source_state_sha256']]+=cost
    state_rows=[]; stable_counts=Counter()
    threshold=int(m['stable_direction_min_pairs'])
    for state,effects in sorted(state_effects.items()):
        counts=Counter(effects); stable='UNCERTAIN'
        for label in ('BENEFIT','HARM','NEUTRAL'):
            if counts[label]>=threshold: stable=label; break
        stable_counts[stable]+=1; b=state_meta[state]
        coverage=b['typed_short_option_legacy_semantic_coverage']
        state_rows.append({'source_state_sha256':state,'source_candidate_sha256':b['source_candidate_sha256'],'research_candidate_id':b['research_candidate_id'],'typed_short_option_contract_sha256':b['typed_short_option_contract_sha256'],'typed_short_option_legacy_semantic_coverage':coverage,'effect_scope':'REGISTERED_TYPED_OPERATIONALIZATION_ONLY','stable_effect':stable,'effect_counts':{x:counts[x] for x in ('BENEFIT','HARM','NEUTRAL','UNCERTAIN')},'paired_repetition_count':len(effects),'stable_direction_min_pairs':threshold,'option_environment_steps_total':state_costs[state]})
    partial=sum(1 for row in state_rows if row['typed_short_option_legacy_semantic_coverage']!='FULL')
    payload={'schema_id':'CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V2','schema_version':2,'execution_manifest_sha256':m['execution_manifest_sha256'],'effect_authority':'INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY','effect_scope':'REGISTERED_TYPED_OPERATIONALIZATION_ONLY','partial_legacy_operationalization_state_count':partial,'branch_record_count':len(expected),'pair_count':len(pair_rows),'state_count':len(state_rows),'pairs':pair_rows,'states':state_rows,'stable_effect_counts':{x:stable_counts[x] for x in ('BENEFIT','HARM','NEUTRAL','UNCERTAIN')},'result_package_sha256':'0'*64}
    payload['result_package_sha256']=_hash(payload['schema_id'],{k:v for k,v in payload.items() if k!='result_package_sha256'})
    return payload
