from __future__ import annotations
import hashlib, importlib.util, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('v1232v_driver',ROOT/'v1232v_driver.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
from dynamic_primary_pre_v2 import build_dynamic_pre_contract_v2, finalize_dynamic_primary_pre_v2


def dh(domain,payload,excluded_field=None):
    body=dict(payload)
    if excluded_field is not None: body.pop(excluded_field,None)
    raw=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(domain.encode()+b'\0'+raw).hexdigest()


def candidate(state,tag):
    c={
      'candidate_sha256':hashlib.sha256((state+tag).encode()).hexdigest(),
      'source_state_sha256':state,'menu_sha256':'b'*64,
      'candidate_status':'EXECUTABLE_EXACT_ACTION','exact_action':'go to desk 1',
      'option_actions':[],'termination_condition':None,
    }
    return c


def u_pair_fixture(n=2):
    rows=[]
    for i in range(n):
        state=hashlib.sha256(f'state{i}'.encode()).hexdigest()
        a2=candidate(state,'A2'); a3=candidate(state,'A3')
        rows.append({
          'state_index':i,'source_state_sha256':state,
          'source_context':{'source_state_sha256':state,'menu_sha256':'b'*64,'admissible_commands':['go to desk 1']},
          'source_context_audit':{'execution_context_conflict':False},
          'A2':{'candidate_sha256':a2['candidate_sha256'],'selected_execution_identity_sha256':'c'*64,'candidate':a2,'candidate_provenance':[],'group_result_sha256s':['d'*64],'formal_x_dispositions':['ACCEPT']},
          'A3':{'candidate_sha256':a3['candidate_sha256'],'selected_execution_identity_sha256':'e'*64,'candidate':a3,'candidate_provenance':[],'group_result_sha256s':['f'*64],'formal_x_dispositions':['ACCEPT']},
        })
    value={'pair_universe_sha256':'a'*64,'complete_pair_count':n,'pair_table':rows}
    return value


def protocol():
    return json.loads((ROOT/'assets/configs/planner_bound_f0f1_replication_protocol_v2.json').read_text())


def test_u_pair_representation_view_adds_only_required_pre_contract_bindings():
    src=u_pair_fixture(2)
    before=json.loads(json.dumps(src))
    view=mod.translate_pair_universe(src,dh)
    assert src==before
    assert view['source_v1232u_pair_universe_sha256']=='a'*64
    assert view['pair_count']==2
    assert view['representation_repair_only'] is True
    assert view['scientific_selection_changed'] is False
    for row in view['pair_table']:
        assert row['pair_status']=='COMPLETE_A2_A3'
        for cond in ('A2','A3'):
            assert row[cond]['source_state_sha256']==row['source_state_sha256']
            assert row[cond]['candidate']['candidate_sha256']==row[cond]['candidate_sha256']


def test_dynamic_contract_is_pair_count_driven_and_branch_budget_derived():
    view=mod.translate_pair_universe(u_pair_fixture(2),dh)
    c=build_dynamic_pre_contract_v2(pair_rows=view['pair_table'],f0f1_protocol=protocol(),dynamic_pair_universe_sha256='a'*64)
    assert c['pair_count']==2
    assert c['state_review_count_required']==2
    assert c['selected_state_budget_ceiling']==2
    assert c['paired_repetitions_per_state']==5
    assert c['branch_arms_per_repetition']==2
    assert c['branch_runs_per_state']==10
    assert c['max_derived_branch_runs']==20
    assert c['legacy_exact_30_authority'] is False
    assert c['legacy_select12_authority'] is False


def test_f0f1_handoff_is_selected_count_times_frozen_repetitions_and_arms():
    view=mod.translate_pair_universe(u_pair_fixture(2),dh)
    p=protocol(); c=build_dynamic_pre_contract_v2(pair_rows=view['pair_table'],f0f1_protocol=p,dynamic_pair_universe_sha256='a'*64)
    reviews=[]
    for i,row in enumerate(view['pair_table']):
        reviews.append({'state_index':i,'source_state_sha256':row['source_state_sha256'],'preferred_condition':'A2','preferred_candidate_sha256':row['A2']['candidate_sha256'],'alternative_condition':'A3','alternative_candidate_sha256':row['A3']['candidate_sha256'],'selected_for_verification':i==0,'state_portfolio_disposition':'SELECTED' if i==0 else 'DEFERRED_LOW_VALUE'})
    artifact={'state_reviews':reviews,'selected_state_count':1,'verification_plan':{'selected_branch_run_budget':10},'primary_record_sha256':'9'*64}
    h=mod.freeze_f0f1_handoff(artifact=artifact,pair_view=view,protocol=p,u_pair_sha='a'*64,pre_artifact_sha='9'*64,domain_hash=dh)
    assert h['selected_state_count']==1
    assert h['selected_branch_run_budget']==10
    assert len(h['branch_plan'])==10
    assert {x['arm'] for x in h['branch_plan']}=={'F0','F1'}
    assert len({x['branch_key_sha256'] for x in h['branch_plan']})==10
    assert h['native_f0f1_environment_execution_performed'] is False


def test_production_source_has_no_current_live_denominator_literals_or_environment_runner():
    text=(ROOT/'v1232v_driver.py').read_text()
    for n in ('24','34','39','68','76','78','136'):
        assert not re.search(r'(?<!\d)'+re.escape(n)+r'(?!\d)',text), n
    forbidden=('sbatch','srun','human_f0f1_runtime','env.step(','evaluate_raw_with_menu','training_execution_authorized=true')
    for token in forbidden: assert token not in text


def test_shell_preserves_project_diagnostic_rule():
    text=(ROOT/'RUN_V1232V.sh').read_text()
    for bad in ('set -e','set -u','set -o pipefail','set -euo pipefail'):
        assert bad not in text
    assert 'PCHSI_OPENAI_SECRET_LOADER' in text


def test_prompt_and_schema_are_frozen_package_assets():
    prompt=(ROOT/'assets/prompts/RESEARCHER_PRE_PRIMARY_V2.txt').read_text()
    schema=json.loads((ROOT/'assets/schemas/strong_researcher_pre_primary_v2.json').read_text())
    assert 'Review EVERY row' in prompt
    assert 'HOLD_PENDING_VERIFIED_F0F1_MANIFEST' in prompt
    assert schema['$id']=='STRONG_RESEARCHER_PRE_PRIMARY_V2'
    assert schema['properties']['effect_authority']['const']=='INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY'


def test_full_semantic_validator_accepts_dynamic_two_pair_fixture():
    view=mod.translate_pair_universe(u_pair_fixture(2),dh); c=build_dynamic_pre_contract_v2(pair_rows=view['pair_table'],f0f1_protocol=protocol(),dynamic_pair_universe_sha256='a'*64)
    reviews=[]
    for i,row in enumerate(view['pair_table']):
        sel=i==0
        reviews.append({
          'state_index':i,'source_state_sha256':row['source_state_sha256'],'preferred_condition':'A2','preferred_candidate_sha256':row['A2']['candidate_sha256'],'alternative_condition':'A3','alternative_candidate_sha256':row['A3']['candidate_sha256'],'selected_for_verification':sel,'state_portfolio_disposition':'SELECTED' if sel else 'DEFERRED_LOW_VALUE'
        })
    value={
      'schema_id':'STRONG_RESEARCHER_PRE_PRIMARY_V2','schema_version':2,'round_id':'r','blind_input_sha256':'8'*64,
      'automatic_environment_effect_assignment':False,'effect_authority':'INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY','promotion_authority':'DETERMINISTIC_INDEPENDENT_GATE_ONLY',
      'state_reviews':reviews,'selected_state_count':1,'unused_state_budget':1,'selected_source_state_sha256s':[reviews[0]['source_state_sha256']],
      'selected_candidate_sha256s':[reviews[0]['preferred_candidate_sha256']],'selected_condition_counts':{'A2':1,'A3':0},
      'verification_plan':{'paired_repetitions_per_state':5,'branch_arms_per_repetition':2,'branch_runs_per_state':10,'selected_state_budget_ceiling':2,'selected_branch_run_budget':10,'outcome_adaptive_budget_change_allowed':False,'unfavorable_candidate_replacement_allowed':False},
      'resource_plan':{'expected_environment_branch_runs':10},'memory_usage_summary':{'memory_effect_authority':False},
      'training_policy_at_pre':{'status':'HOLD_PENDING_VERIFIED_F0F1_MANIFEST','exact_training_mixture_frozen':False},
      'candidate_bottlenecks':[{'candidate_id':'b','status':'SELECTED'}],'selected_bottleneck_id':'b','primary_record_sha256':'0'*64,
    }
    out=finalize_dynamic_primary_pre_v2(value=value,pair_rows=view['pair_table'],contract=c,blind_input_sha256='8'*64,round_id='r')
    assert out['selected_state_count']==1
    assert out['verification_plan']['selected_branch_run_budget']==10
    assert out['primary_record_sha256']!='0'*64
