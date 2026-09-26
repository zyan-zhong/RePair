"""Closed-round transport and real native Researcher-view projection tests."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve()
RUNTIME = HERE.parents[2]
# The delivery verifier materializes runtime overlays into its work/v17 fixture.
PROJECT = RUNTIME.parents[1] if RUNTIME.name == 'v17' else RUNTIME.parents[2]
V17 = PROJECT / 'work/v17'
sys.path[:0] = [str(RUNTIME), str(V17), str(V17/'live_adapter'), str(V17/'native_bba_full/src')]
from analyzer_binding import source_binding as binding
from analyzer_binding.aggregate_context import project_previous_select_context, validate_previous_select_context
from entry import driver

# Reuse the existing published native snapshot and rollout fixture unchanged.
spec = importlib.util.spec_from_file_location('_prior_native_source_fixture', V17/'analyzer_binding/tests/test_source_binding.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def summary_for(outcome='PROMOTED'):
    return dict(schema_id='CURRENT_TRAIN_SELECT_AGGREGATE_V1', round_id='R1', request_sha256='1'*64,
        parent_policy_id='P0', candidate_policy_id='P1', evidence_access_class='TRAIN_SELECT',
        memory_state='OFF', harness_state='OFF', benchmark_feedback_used=False,
        primary_statistical_unit='unique_task', replicates_are_not_independent_tasks=True,
        unique_task_count=2, replicate_seeds=[17,31], paired_cell_count=4, total_condition_cell_count=8,
        parent_success_cells=1, candidate_success_cells=2 if outcome=='PROMOTED' else 0,
        both_success_cells=1 if outcome=='PROMOTED' else 0,
        both_failure_cells=2 if outcome=='PROMOTED' else 3,
        parent_only_success_cells=0 if outcome=='PROMOTED' else 1,
        candidate_only_success_cells=1 if outcome=='PROMOTED' else 0,
        mean_task_success_rate_delta=0.25 if outcome=='PROMOTED' else -0.25,
        identity_audit_ref={'path':'restricted/task_audit.json','sha256':'8'*64},
        native_paired_results_ref={'path':'restricted/task_results.json','sha256':'9'*64},
        frozen_protocol_ref={'path':'restricted/task_grid.json','sha256':'a'*64},
        trajectory='PRIVATE_TRAJECTORY', task_id='PRIVATE_TASK')


def closed_for(outcome='PROMOTED'):
    return dict(schema_id='FORMAL_NATIVE_ROUND_RESULT_V1', round_id='R1', request_sha256='1'*64,
        parent_policy_id='P0', next_parent_policy_id='P1' if outcome=='PROMOTED' else 'P0',
        outcome=outcome, benchmark_feedback_used=False, current_parent_context=None)


@pytest.mark.parametrize('outcome', ['PROMOTED', 'ROLLED_BACK', 'NO_TRAINING_UPDATE'])
def test_actual_driver_next_index_publishes_only_closed_aggregate(tmp_path, monkeypatch, outcome):
    from entry import tail
    obj = driver.ExistingComponentRoundDriver(bundle_root=tmp_path/'bundle',formal_root=tmp_path/'formal',
        owner_root=tmp_path/'owner', deployment={'entry_source_sha256':'b'*64,'scientific_repo_root':str(V17/'native_bba_full')},initial={})
    result = closed_for(outcome)
    result['attempt_root'] = str(tmp_path/'attempt')
    if outcome != 'NO_TRAINING_UPDATE':
        sref = prior.put(tmp_path/'restricted/aggregate.json', summary_for(outcome))
        result['terminal_ref'] = driver._native_ref(prior.put(tmp_path/'terminal.json', {'summary_ref':driver._native_ref(sref)}))
    nxt_request = dict(schema_id='ROUND_ROLLOUT_COLLECTION_REQUEST_V1', round_id='R2', request_sha256='2'*64,
        parent_policy_id=result['next_parent_policy_id'], round_start_memory_snapshot_sha256='3'*64)
    inputs = {'request_sha256':nxt_request['request_sha256']}
    for role,field in [('runtime','policy_runtime_binding_sha256'),('profile','execution_profile_sha256'),
                       ('memory','round_memory_runtime_authority_sha256'),('train_manifest','train_update_manifest_sha256')]:
        inputs[role] = driver._native_ref(prior.put(tmp_path/(role+'.json'), {'fixture':role}))
        nxt_request[field] = inputs[role]['sha256']
    nxt = {'next_request':nxt_request,
        'request':driver._native_ref(prior.put(tmp_path/'request.json',nxt_request)),
        'input_refs':driver._native_ref(prior.put(tmp_path/'inputs.json',inputs)),
        'execution_binding':driver._native_ref(prior.put(tmp_path/'execution.json',{'request_sha256':nxt_request['request_sha256']})),
        'memory_state':driver._native_ref(prior.put(tmp_path/'state.json',{'fixture':'native-state'})),
        'memory_source_partitions':driver._native_ref(prior.put(tmp_path/'partitions.json',{'fixture':'partitions'}))}
    validated=[]
    monkeypatch.setattr(obj,'validate_result',lambda start,value:validated.append(value))
    monkeypatch.setattr(tail,'build_next_round_tail',lambda **kwargs:nxt)
    assert obj.build_next({},result,SimpleNamespace(valid_rounds_consumed=1)) == nxt_request
    assert validated == [result]
    registered = driver.read_json(obj._binding_path(nxt_request))
    index = driver.read_ref(driver._file_ref(registered['current_index']))
    if outcome == 'NO_TRAINING_UPDATE':
        assert set(index['refs']) == {'memory_source_partitions'}
        assert not (Path(result['attempt_root'])/'tail/next_round/PREVIOUS_TRAIN_SELECT_RESEARCH_CONTEXT.json').exists()
    else:
        context = driver.read_ref(index['refs']['previous_select_context'])
        assert validate_previous_select_context(context,current_request=nxt_request) == context
        assert context['promotion_outcome'] == outcome
        assert 'PRIVATE_' not in repr(context) and 'restricted/' not in repr(context)
        assert context['consumer_memory_snapshot_sha256'] == '3'*64
        assert obj.build_next({},result,SimpleNamespace(valid_rounds_consumed=1)) == nxt_request


@pytest.fixture
def native_case(tmp_path, monkeypatch):
    (tmp_path/'native').mkdir()
    loaded, contract, token_path = prior.published_native_snapshot(tmp_path/'native',monkeypatch)
    result = prior.rollout(tmp_path/'round')
    result['implementation_worktree'] = str(V17/'native_bba_full')
    memory_path = Path(result['root'])/'input_capsule/inputs/memory.json'
    memory = json.loads(memory_path.read_bytes())
    memory.update(active_snapshot_sha256=loaded.snapshot.snapshot_sha256,
        active_snapshot_directory=str(loaded.snapshot_directory), token_budget_contract_path=str(token_path),
        token_budget_contract_sha256=contract.contract_sha256)
    memory_ref = prior.put(memory_path,memory)
    result['input_member_manifest']['memory']['sha256'] = memory_ref['file_sha256']
    request = json.loads(Path(result['request_path']).read_bytes())
    request.update(schema_id='ROUND_ROLLOUT_COLLECTION_REQUEST_V1',parent_policy_id='P1',
        round_start_memory_snapshot_sha256=loaded.snapshot.snapshot_sha256,
        token_budget_contract_sha256=contract.contract_sha256,round_memory_runtime_authority_sha256=memory_ref['file_sha256'])
    result['request_file_sha256'] = prior.put(Path(result['request_path']),request)['file_sha256']
    from pchsi.memory import consumer_views as views
    partitions = binding.initial_source_partitions(snapshot=loaded,
        dependency={'active_snapshot_sha256':loaded.snapshot.snapshot_sha256,'token_budget_contract_sha256':contract.contract_sha256},
        native_source=(V17/'native_bba_full/scripts/memory/run_role_view_smoke_v1.py').read_bytes(),consumer_views=views)
    context = project_previous_select_context(summary=summary_for(),summary_sha256='7'*64,
        closed_result=closed_for(),next_request=request)
    context_ref = prior.put(tmp_path/'previous_select_context.json',context)
    part_ref = prior.put(tmp_path/'partitions.json',{k:v.to_dict() for k,v in partitions.items()})
    index = {'round_id':result['round_id'],'request_sha256':result['request_sha256'],
        'refs':{'memory_source_partitions':part_ref,'previous_select_context':context_ref}}
    return loaded,result,request,context,index


def test_actual_source_constructor_populates_native_slot_preserves_snapshot_records(native_case,tmp_path):
    loaded,result,request,context,index = native_case
    built = binding.build_source_binding(result,layout=binding.SourceLayout.project(PROJECT),
        output_root=tmp_path/'view',current_index=index)
    value = binding._read_ref(built['refs']['researcher_view'])
    assert value['heldout_aggregate_metrics'] == context
    assert value['snapshot_sha256'] == loaded.snapshot.snapshot_sha256
    assert value['train_side_records'][0]['governed_record'] == loaded.members[0].record.to_dict()
    assert value['purpose'] == 'ROUND_RESEARCH_PLANNING' and value['round_evidence'] == {}
    assert value['benefit_harm_authority'] is False
    assert built['refs']['previous_select_context'] == index['refs']['previous_select_context']
    # Native prebuilt views must preserve the exact registered context.
    prebuilt={'round_id':result['round_id'],'request_sha256':result['request_sha256'],
        'refs':{'previous_select_context':index['refs']['previous_select_context'],
                'researcher_view':built['refs']['researcher_view']}}
    reused=binding.build_source_binding(result,layout=binding.SourceLayout.project(PROJECT),
        output_root=tmp_path/'reused',current_index=prebuilt)
    assert reused['refs']['researcher_views']==[built['refs']['researcher_view']]
    stale=copy.deepcopy(value);stale['heldout_aggregate_metrics']={}
    prebuilt['refs']['researcher_view']=prior.put(tmp_path/'stale.json',stale)
    with pytest.raises(binding.SourceBindingError,match='RESEARCHER_VIEW_SELECT_CONTEXT_IDENTITY'):
        binding.build_source_binding(result,layout=binding.SourceLayout.project(PROJECT),
            output_root=tmp_path/'rejected',current_index=prebuilt)


def test_absent_context_keeps_native_slot_empty(native_case,tmp_path):
    loaded,result,request,context,index=native_case
    del index['refs']['previous_select_context']
    built=binding.build_source_binding(result,layout=binding.SourceLayout.project(PROJECT),
        output_root=tmp_path/'empty',current_index=index)
    value=binding._read_ref(built['refs']['researcher_view'])
    assert value['heldout_aggregate_metrics']=={}
    assert value['train_side_records'][0]['governed_record']==loaded.members[0].record.to_dict()


@pytest.mark.parametrize('field,value', [('consumer_round_id','OTHER'),('consumer_request_sha256','f'*64),
    ('consumer_memory_snapshot_sha256','f'*64),('source_access','FINAL134'),('active_memory_writeback_authorized',True),
    ('trajectory','PRIVATE')])
def test_indexed_context_requires_exact_safe_payload_and_current_consumer(native_case,tmp_path,field,value):
    _,result,_,context,index=native_case
    context[field]=value
    index['refs']['previous_select_context']=prior.put(tmp_path/'changed_context.json',context)
    with pytest.raises(ValueError,match='SELECT_RESEARCH_CONTEXT:'):
        binding.build_source_binding(result,layout=binding.SourceLayout.project(PROJECT),
            output_root=tmp_path/'reject',current_index=index)


@pytest.mark.parametrize('with_context',[True,False])
def test_pre_preserves_registered_context_in_actual_native_renderer_before_provider(tmp_path,monkeypatch,with_context):
    pre_spec=importlib.util.spec_from_file_location('_current_context_pre_stage',RUNTIME/'live_adapter/pre_stage.py')
    pre=importlib.util.module_from_spec(pre_spec);pre_spec.loader.exec_module(pre)
    from pchsi.memory.consumer_views import ResearcherMemoryViewV1,ResearcherPurposeV1
    from pchsi.cognitive_runtime import request_renderer as renderer
    request=dict(schema_id='ROUND_ROLLOUT_COLLECTION_REQUEST_V1',round_id='R2',request_sha256='2'*64,
        parent_policy_id='P1',round_start_memory_snapshot_sha256='3'*64)
    context=(project_previous_select_context(summary=summary_for(),summary_sha256='7'*64,
        closed_result=closed_for(),next_request=request) if with_context else {})
    memory=ResearcherMemoryViewV1(snapshot_sha256='3'*64,purpose=ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,
        train_side_records=(),round_evidence={},heldout_aggregate_metrics=context).to_dict()
    bound={'round_id':'R2','parent_policy_id':'P1','refs':{},'source_registration':{}}
    if with_context:bound['refs']['previous_select_context']=prior.put(tmp_path/'context.json',context)
    values={'request':request,'f0f1_protocol':{},'researcher_view':memory}
    x=SimpleNamespace(translate_pair_universe=lambda *args:{'pair_table':[]},
        build_dynamic_pre_contract_v2=lambda **kwargs:{'contract_sha256':'4'*64},
        build_current_round_evidence=lambda **kwargs:{'pre_outcome_only':True},
        partition_predecessor_memory_candidates=lambda rows,**kwargs:(rows,[]),
        resolve_stable_memory_authority=lambda rows,**kwargs:{'train_side_records':rows[0]['train_side_records']})
    core=SimpleNamespace(x=x,repo=V17/'native_bba_full',domain_hash=lambda *args,**kwargs:'5'*64,
        researcher_view=ResearcherMemoryViewV1,researcher_purpose=ResearcherPurposeV1)
    monkeypatch.setattr(pre,'load_native_labels',lambda *args:None)
    captured={}
    class BeforeProvider(Exception):pass
    def capture(core,domain,payload,hash_field):
        captured.update(payload)
        raise BeforeProvider()
    monkeypatch.setattr(pre,'sealed',capture)
    with pytest.raises(BeforeProvider):
        pre.run_pre(bound,values,core,{'terminal_sha256':'6'*64},{'pair_universe_sha256':'7'*64},tmp_path/'pre')
    assert captured['researcher_memory_view']['heldout_aggregate_metrics']==context
    assert captured['current_or_future_f0f1_outcomes_visible'] is False
    prompt=tmp_path/'prompt.txt';prompt.write_text('Review the registered input.',encoding='utf-8')
    schema=tmp_path/'schema.json';schema.write_text('{"type":"object"}',encoding='utf-8')
    spec={'stage_id':'R-PRE-PRIMARY-V2','role':'RESEARCHER','required_projection_identity_fields':['blind_input'],
        'prompt_relative_path':str(prompt),'prompt_sha256':pre.digest(prompt.read_bytes()),
        'output_schema_id':'TEST_PRE','output_schema_relative_path':str(schema),
        'output_schema_sha256':pre.digest(schema.read_bytes()),'max_output_tokens':100}
    manifest={'stage_rows':[spec],'requested_model':'fixture-model','reasoning':{'effort':'low'},'runtime_manifest_sha256':'8'*64}
    monkeypatch.setattr(renderer,'load_runtime_manifest',lambda:manifest)
    rendered=renderer.render_stage_request(stage_id='R-PRE-PRIMARY-V2',projection={'blind_input':captured})
    user=json.loads(rendered['provider_request']['input'][1]['content'][0]['text'])
    assert user['blind_input']['researcher_memory_view']['heldout_aggregate_metrics']==context
    assert 'PRIVATE_' not in repr(user) and 'restricted/' not in repr(user)
    if with_context:
        values['researcher_view']={**memory,'heldout_aggregate_metrics':{}}
        with pytest.raises(ValueError,match='PRE_RESEARCHER_SELECT_CONTEXT_IDENTITY'):
            pre.run_pre(bound,values,core,{'terminal_sha256':'6'*64},{'pair_universe_sha256':'7'*64},tmp_path/'mismatch')
