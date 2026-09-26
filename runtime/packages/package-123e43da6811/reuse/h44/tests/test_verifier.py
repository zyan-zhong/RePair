from pathlib import Path
from io_utils import canonical,sha,put_json,digest_file,read_json
from independent_verifier import verify_plan
from pchsi.memory.source_state_contracts import SourceStateReplayReportV1

def fixture_plan(root,win_repetitions=4,missing=None):
    seeds=[17,31,47,73,101];state={'source_state_sha256':'a'*64,'source_candidate_sha256':'b'*64,'semantics_status':'COMPILED'}
    branches=[];bindings=[]
    for rep,seed in enumerate(seeds):
        for arm in ('F0','F1'):
            key=sha((str(rep)+arm).encode())
            branch={'branch_key_sha256':key,'arm':arm,'source_state_sha256':'a'*64,'replicate_index':rep,'paired_seed':seed}
            binding={**branch,'source_candidate_sha256':'b'*64,'native_source_fingerprint_sha256':'c'*64}
            binding['binding_sha256']=sha(canonical(binding))
            bp=root/'bindings'/f'{key}.json';put_json(bp,binding)
            bindings.append({'path':str(bp),'file_sha256':digest_file(bp),'binding':binding});branches.append(branch)
            if missing==(rep,arm):continue
            report=SourceStateReplayReportV1(
                schema_id='SOURCE_STATE_REPLAY_REPORT_V1',schema_version=1,
                source_fingerprint_sha256='c'*64,replay_fingerprint_sha256='c'*64,
                transition_count=1,status='PASS',failure_code=None,report_sha256=None).to_dict()
            result={**binding,'continuation_seed':seed,'terminal_success':arm=='F1' and rep<win_repetitions,
                'evidence_complete':True,'scientific_outcome_produced':True,'source_replay_report':report,
                'automatic_retry_count':0,'option_environment_step_count':1 if arm=='F1' else 0}
            result['evidence_sha256']=sha(canonical(result))
            put_json(root/'branches'/key/'BRANCH_TERMINAL.json',result)
    plan={'round_id':'r','handoff':{'paired_seeds':seeds,'paired_repetitions_per_state':len(seeds),'stable_direction_min_pairs':4,'branch_plan':branches},
          'states':[state],'branch_bindings':bindings,'scope_notice':{'comparison':'F0_PARENT_NOT_A2'}}
    plan['plan_sha256']=sha(canonical(plan));put_json(root/'EXECUTION_PLAN.json',plan)
    return root/'EXECUTION_PLAN.json'

def test_original_classifier_four_of_five_benefit(tmp_path):
    p=fixture_plan(tmp_path);r=verify_plan(p,tmp_path)
    assert r['status']=='VERIFIED_COMPLETE'
    assert r['stable_effect_counts']['BENEFIT']==1 and r['frozen_pair_count']==5

def test_missing_arm_never_dropped_or_counted_as_failure(tmp_path):
    p=fixture_plan(tmp_path,win_repetitions=3,missing=(4,'F1'));r=verify_plan(p,tmp_path)
    assert r['frozen_pair_count']==5 and r['scientifically_complete_pair_count']==4
    assert r['stable_effect_counts']['UNCERTAIN']==1
    assert r['pair_results'][-1]['effect']=='UNCERTAIN'

def test_corrupt_evidence_becomes_missingness_not_benefit(tmp_path):
    p=fixture_plan(tmp_path,win_repetitions=4)
    plan=read_json(p);item=plan['branch_bindings'][1]['binding'];rp=tmp_path/'branches'/item['branch_key_sha256']/'BRANCH_TERMINAL.json'
    r=read_json(rp);r['terminal_success']=False;rp.write_bytes(canonical(r))
    result=verify_plan(p,tmp_path)
    assert result['stable_effect_counts']['BENEFIT']==0
    assert result['scientifically_complete_pair_count']==4

def test_second_verification_is_exact_no_reexecution(tmp_path):
    p=fixture_plan(tmp_path);a=verify_plan(p,tmp_path);b=verify_plan(p,tmp_path)
    assert a==b
