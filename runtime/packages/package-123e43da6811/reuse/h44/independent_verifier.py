"""Independent persisted-evidence validation, using original effect classifiers."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from io_utils import read_json,put_json,sha,canonical,digest_file
import native_branch  # installs only the captured source import path
from pchsi.research_intelligence.human_f0f1_runtime import classify_pair_effect_v1,aggregate_five_pair_effects_v1
from pchsi.memory.source_state_contracts import SourceStateReplayReportV1




def _validate_source_replay_report(value, expected_fingerprint):
    if not isinstance(value, dict):
        raise ValueError('scientific result lacks source replay report')
    try:
        report = SourceStateReplayReportV1(**value)
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid source replay report: ' + str(exc)) from exc
    if report.status != 'PASS' or report.failure_code is not None:
        raise ValueError('scientific result lacks passing replay proof')
    if (
        report.source_fingerprint_sha256 != expected_fingerprint
        or report.replay_fingerprint_sha256 != expected_fingerprint
    ):
        raise ValueError('scientific result replay fingerprint mismatch')
    return report

def verify_plan(plan_path:Path,run_root:Path):
    plan=read_json(plan_path)
    if plan.get('plan_sha256')!=sha(canonical({k:v for k,v in plan.items() if k!='plan_sha256'})):
        raise ValueError('execution plan identity mismatch')
    handoff=plan['handoff'];seeds=handoff['paired_seeds']
    # Native V1 is the already frozen five-repeat protocol; no silent other protocol.
    if len(seeds)!=handoff['paired_repetitions_per_state'] or len(set(seeds))!=len(seeds):
        raise ValueError('paired protocol inconsistent')
    bindings={r['binding']['branch_key_sha256']:r for r in plan['branch_bindings']}
    by_group={};diagnostics=[];branch_records=[]
    keys=set()
    for b in handoff['branch_plan']:
        key=b['branch_key_sha256']
        if key in keys:raise ValueError('duplicate frozen branch key')
        keys.add(key);group=(b['source_state_sha256'],b['replicate_index'])
        by_group.setdefault(group,{})
        if b['arm'] in by_group[group]:raise ValueError('duplicate paired arm')
        row=bindings.get(key);value=None
        if row:
            try:
                if digest_file(Path(row['path']))!=row['file_sha256']:raise ValueError('binding file changed')
                binding=read_json(Path(row['path']))
                value=read_json(run_root/'branches'/key/'BRANCH_TERMINAL.json')
                expected=sha(canonical({k:v for k,v in value.items() if k!='evidence_sha256'}))
                if value.get('evidence_sha256')!=expected:raise ValueError('branch evidence hash mismatch')
                for field,expected_value in {
                    'binding_sha256':binding['binding_sha256'],'branch_key_sha256':key,
                    'source_state_sha256':b['source_state_sha256'],
                    'source_candidate_sha256':binding['source_candidate_sha256'],
                    'native_source_fingerprint_sha256':binding['native_source_fingerprint_sha256'],
                    'arm':b['arm'],'continuation_seed':b['paired_seed'],'replicate_index':b['replicate_index']}.items():
                    if value.get(field)!=expected_value:raise ValueError('branch binding mismatch: '+field)
                if value.get('evidence_complete') and value.get('scientific_outcome_produced'):
                    _validate_source_replay_report(
                        value.get('source_replay_report'),
                        binding['native_source_fingerprint_sha256'],
                    )
                    if type(value.get('terminal_success')) is not bool:raise ValueError('terminal success not bool')
                    if value.get('automatic_retry_count')!=0:raise ValueError('unexpected automatic branch retry')
                    if b['arm']=='F0' and value.get('option_environment_step_count')!=0:
                        raise ValueError('F0 unexpectedly intervened')
                branch_records.append(value)
            except (OSError,ValueError,KeyError) as exc:
                diagnostics.append({'branch_key_sha256':key,'reason':str(exc)})
                value=None
        else:diagnostics.append({'branch_key_sha256':key,'reason':'selected semantics not compiled; no replacement'})
        by_group[group][b['arm']]=value
    pair_results=[];state_results=[]
    for state in plan['states']:
        effects=[]
        for rep,seed in enumerate(seeds):
            arms=by_group.get((state['source_state_sha256'],rep),{})
            if set(arms)!= {'F0','F1'}:raise ValueError('frozen handoff missing paired arm')
            f0,f1=arms['F0'],arms['F1']
            def complete(r):return bool(r and r.get('evidence_complete') is True and r.get('scientific_outcome_produced') is True)
            ok=complete(f0) and complete(f1) and f1.get('option_environment_step_count',0)>0
            effect=classify_pair_effect_v1(f0_success=f0.get('terminal_success') if f0 else None,
                f1_success=f1.get('terminal_success') if f1 else None,f0_complete=ok,f1_complete=ok)
            row={'source_state_sha256':state['source_state_sha256'],'source_candidate_sha256':state['source_candidate_sha256'],
                 'replicate_index':rep,'paired_seed':seed,'complete':ok,**effect,
                 'f0_evidence_sha256':None if f0 is None else f0['evidence_sha256'],
                 'f1_evidence_sha256':None if f1 is None else f1['evidence_sha256']}
            pair_results.append(row);effects.append(effect['effect'])
        aggregate=aggregate_five_pair_effects_v1(effects)
        if handoff['stable_direction_min_pairs']!=4:
            raise ValueError('unsupported changed stability protocol; native V1 not altered')
        state_results.append({**state,**aggregate})
    counts=Counter(r['stable_effect'] for r in state_results)
    complete_count=sum(r['complete'] for r in pair_results)
    result={'schema_id':'CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1','plan_sha256':plan['plan_sha256'],
      'round_id':plan['round_id'],'status':'VERIFIED_WITH_MISSINGNESS' if complete_count else 'NO_SCIENTIFICALLY_COMPLETE_PAIRS',
      'scientifically_complete_pair_count':complete_count,'frozen_pair_count':len(pair_results),
      'selected_state_count':len(state_results),'planned_branch_count':len(handoff['branch_plan']),
      'stable_effect_counts':{k:counts[k] for k in ('BENEFIT','HARM','NEUTRAL','UNCERTAIN')},
      'state_results':state_results,'pair_results':pair_results,'branch_records':branch_records,
      'diagnostics':diagnostics,'hypothesis_scope_notice':plan['scope_notice'],
      'comparison':'SELECTED_REPAIR_VS_PARENT_CONTINUATION_NOT_A3_VS_A2',
      'automatic_environment_effect_assignment':True,'human_decision_count':0,
      'training_authorized_by_this_verifier':False,'max10_released':False}
    if complete_count==len(pair_results) and not diagnostics:result['status']='VERIFIED_COMPLETE'
    result['environment_result_package_sha256']=sha(canonical(result))
    put_json(run_root/'verifier/ENVIRONMENT_RESULT_PACKAGE.json',result)
    return result
