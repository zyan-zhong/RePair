"""Fixture-only end-to-end case; every scientific builder/validator stays native."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys

from memory_binding.current_source import canonical,sha
from memory_binding.producer import file_ref,write_once
from memory_binding.api import materialize_round_memory
from pchsi.memory import sequence_failure_experience as seq
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
from pchsi.reference_loop.canonical import domain_hash
from pchsi.cognitive_runtime.identity import build_scientific_unit_identity,build_logical_call_record
from pchsi.cognitive_runtime.output_validation import validate_stage_output
from pchsi.cognitive_runtime.request_renderer import render_stage_request


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def put(path,value): return write_once(path,canonical(value))


def seal(schema,fields,field):
    value={'schema_id':schema,'schema_version':1,**fields}
    value[field]=domain_hash(schema,value,excluded_field=field)
    return value


root=Path(case_root)  # injected by the test in a fresh interpreter
native=Path.cwd()
helpers=load(native/'tests/memory/test_sequence_failure_experience.py','source_helpers')
source,old_access,_,_=helpers._t4_fixture(seq)
episode=replace(source.episode_artifact,policy_condition_id='P4-R0-PI0',
    task_access_manifest_sha256='1'*64,policy_condition_manifest_sha256='2'*64,
    condition_run_schedule_sha256='3'*64,access_class='DEV_VISIBLE',condition_cell_id=source.episode_artifact.scheduled_cell_id)
source=replace(source,episode_artifact=episode,attempt_bundle=helpers._t3_build_attempt_bundle_bytes(
    episode_artifact=episode,traces=source.traces,policy_calls=source.policy_calls,public_transitions=source.public_transitions))
attempt=root/'sealed_attempt';attempt.mkdir()
for name,raw in source.attempt_bundle.file_bytes(): (attempt/name).write_bytes(raw)
train_ref=put(root/'TRAIN_UPDATE.jsonl',{'schema_id':'ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1',
    'id':episode.task_id,'split':'train','train_pool':'TRAIN_UPDATE','gamefile_sha256':episode.gamefile_sha256,
    'gamefile_relpath':old_access.dataset_relative_gamefile,'task_type':episode.task_type})
request_fields=dict(round_id='ROUND1',execution_attempt_id='round-attempt',parent_policy_id='pi0',
    parent_policy_artifact_sha256='a'*64,policy_runtime_binding_sha256='b'*64,execution_profile_sha256='c'*64,
    train_update_manifest_sha256=train_ref['file_sha256'],round_memory_runtime_authority_sha256='d'*64,
    round_start_memory_snapshot_sha256='e'*64,token_budget_contract_sha256='f'*64,execution_namespace='test',rollout_seed=17)
request_fields.update(globals().get('request_overrides', {}))
request_fields['train_update_manifest_sha256']=train_ref['file_sha256']
request=RoundRolloutCollectionRequestV1(**request_fields)
request_ref=put(root/'request.json',request.to_dict())
local_helpers=load(native/'tests/analyzer/test_local_results.py','local_helpers')
renderer_helpers=load(native/'tests/cognitive_runtime/test_request_renderer.py','renderer_helpers')
pack=local_helpers._pack();pack['task_identity']['task_id']=episode.task_id
pack['trajectory']=[{'model_call_index':call.model_call_index,'admissible_commands':list(call.admissible_commands)} for call in source.policy_calls]
pack['evidence_pack_sha256']=domain_hash(pack['schema_id'],pack,excluded_field='evidence_pack_sha256')
payload=local_helpers._base(pack);payload['task_id']=episode.task_id
error=local_helpers._error(pack,'e1','h1',0);error['critical_window_end_call_index']=1
payload['error_instances']=[error]
payload['memory_boundary_registrations']=[{'error_instance_id':'e1','status':'REGISTERED','unresolved_reason':None,
    'applicability':{'activation':['The visible interface reports an invalid response format.'],
    'continuation':[],'revalidation_requirement':'NOT_REQUIRED','revalidation':[],
    'release':['A response matching the interface format is accepted.'],'termination':[],
    'non_applicability_disposition':'UNRESOLVED_NO_REGISTERED_CONDITION','non_applicability':[],
    'policy_visible_state_change_trigger':[]}}]
catalog=renderer_helpers._catalog();catalog['evidence_pack_sha256']=pack['evidence_pack_sha256']
catalog['trajectory_calls']=[local_helpers._ref(pack,i) for i in range(2)]
projection={'evidence_pack_sha256':pack['evidence_pack_sha256'],'evidence_pack':pack,
    'evidence_reference_catalog':catalog,'local_repair_contract':renderer_helpers._repair_contract(),'memory_pack_sha256':None}
rendered=render_stage_request(stage_id='L-A1',projection=projection)
raw=canonical({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(payload)}]}]})
local=validate_stage_output(stage_id='L-A1',text=json.dumps(payload),raw_response_sha256=sha(raw),projection=projection)
sid='source_unit';state='a'*64
handoff_ref=put(root/'handoff.json',{'fixture':'current handoff'})
sm=seal('V1232Q_ANALYZER_SOURCE_UNIT_MANIFEST_V1',{'round_id':request.round_id,'source_unit_id':sid,
    'rollout_handoff_sha256':handoff_ref['file_sha256'],'attempt_bundle_sha256':source.attempt_bundle.attempt_bundle_sha256,
    'attempt_bundle_path':str(attempt),'evidence_pack_sha256':pack['evidence_pack_sha256']},'source_unit_manifest_sha256')
analyzer=root/'analyzer';unit=analyzer/'local/units'/sid
sm_ref=put(unit/'source_unit_manifest.json',sm)
identity=build_scientific_unit_identity(scientific_unit_type='EPISODE',scientific_unit_id=sid,
    source_unit_manifest_sha256=sm['source_unit_manifest_sha256'],task_set_manifest_sha256='b'*64,
    task_id=episode.task_id,gamefile_sha256=episode.gamefile_sha256,group_manifest_sha256=None,round_evidence_package_sha256='c'*64)
put(unit/'scientific_unit_identity.json',identity)
lid=domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1',{'scientific_unit_identity_sha256':identity['identity_sha256'],
    'stage_id':'L-A1','condition_id':'A1','round_id':request.round_id,'policy_version':request.parent_policy_id,
    'request_body_sha256':rendered['request_body_sha256']})
call=analyzer/'local/strong_local_runtime'/lid
logical=build_logical_call_record(logical_call_id=lid,scientific_unit_identity_sha256=identity['identity_sha256'],
    role='ANALYZER',stage_id='L-A1',condition_id='A1',round_id=request.round_id,policy_version=request.parent_policy_id,
    runtime_manifest_sha256=rendered['runtime_manifest_sha256'],request_body_sha256=rendered['request_body_sha256'],
    terminal_method_status='ACCEPTED',contributing_attempt_id='d'*64)
put(call/'logical_call.json',logical);put(call/'rendered_request.json',rendered)
put(call/'validated_artifact.json',local);write_once(call/'raw_response.json',raw)
put(analyzer/'local/strong_local_runtime/execution_manifest.json',{'round_id':request.round_id,'policy_version':request.parent_policy_id,
    'rows':[{'source_unit_id':sid,'stage_id':'L-A1','status':'ACCEPTED','call_dir':str(call)}]})
put(analyzer/'local/SOURCE_UNITS.json',{'rows':[{'source_unit_id':sid,'source_manifest':sm_ref}]})
put(analyzer/'local/GROUP_PREPARATION_CENSUS.json',{'round_id':request.round_id,'sources':{state:{'source_unit_id':sid,
    'bundle_path':str(attempt),'bundle_sha256':source.attempt_bundle.attempt_bundle_sha256,
    'context':{'local_result_sha256':local['local_result_sha256'],'error_instance_id':'e1'}}}})
candidate=seal('ANALYZER_REPAIR_CANDIDATE_V1',{'candidate_kind':'FAILURE_REPAIR','source_state_sha256':state,'menu_sha256':'c'*64,
    'source_proposal_sha256':'d'*64,'candidate_status':'EXECUTABLE_EXACT_ACTION','exact_action':'look','option_actions':[],
    'termination_condition':None,'requires_environment_verification':True,'live_menu_revalidation_required':True,
    'all_intervention_actions_count_against_environment_budget':True},'candidate_sha256')
entry={'candidate_sha256':candidate['candidate_sha256'],'candidate':candidate}
put(analyzer/'group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json',seal('V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1',
    {'round_id':request.round_id,'parent_policy_id':request.parent_policy_id,
     'pair_table':[{'source_state_sha256':state,'A2':entry,'A3':entry}]},'pair_universe_sha256'))
project=Path(__file__).resolve().parents[4]
h44=project/'work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4'
sys.path.insert(0,str(h44))
if sys.platform=='win32':
    import types
    sys.modules.setdefault('fcntl',types.ModuleType('fcntl'))
    from pchsi.memory import candidate_materialization as cm
    def binary_once(path,raw):
        with Path(path).open('xb') as stream: stream.write(raw)
    cm._write_once=binary_once
h4=load(h44/'tests/test_verifier.py','verifier_helpers');run=root/'verifier_run'
plan_path=h4.fixture_plan(run);plan=json.loads(plan_path.read_bytes())
plan.update(round_id=request.round_id,source_request=request.to_dict())
plan['handoff'].update(globals().get('handoff_overrides', {}))
plan['states'][0]['source_candidate_sha256']=candidate['candidate_sha256']
for bound in plan['branch_bindings']:
    body=bound['binding'];body['source_candidate_sha256']=candidate['candidate_sha256'];body.pop('binding_sha256')
    body['binding_sha256']=sha(canonical(body));Path(bound['path']).write_bytes(canonical(body));bound['file_sha256']=sha(canonical(body))
    terminal=run/'branches'/body['branch_key_sha256']/'BRANCH_TERMINAL.json'
    value=json.loads(terminal.read_bytes());value.update(source_candidate_sha256=candidate['candidate_sha256'],binding_sha256=body['binding_sha256'])
    value.pop('evidence_sha256');value['evidence_sha256']=sha(canonical(value));terminal.write_bytes(canonical(value))
plan.pop('plan_sha256');plan['plan_sha256']=sha(canonical(plan));plan_path.write_bytes(canonical(plan))
h4.verify_plan(plan_path,run)
class FixtureTokenizer:
    tokenizer_id='PACKAGE_B_TEST_TOKENIZER'
    tokenizer_revision='f'*64
    def count_tokens(self,text): return max(1,len(text)//100)
token_ref=put(root/'token.json',{'tokenizer_id':FixtureTokenizer.tokenizer_id,'tokenizer_revision':FixtureTokenizer.tokenizer_revision})
binding={'scientific_repo_root':str(native),'refs':{'request':request_ref,'handoff':handoff_ref,
    'train_update_manifest':train_ref,'analyzer_token_contract':token_ref}}
kwargs=dict(binding=binding,analyzer_output_root=analyzer,execution_plan_ref=file_ref(plan_path),
    verifier_ref=file_ref(run/'verifier/ENVIRONMENT_RESULT_PACKAGE.json'),output_root=root/'memory',tokenizer=FixtureTokenizer())
result=materialize_round_memory(**kwargs)
assert len(result['event_refs'])==len(result['additional_member_refs'])==1
assert result['results'][0]['native_eligibility']=='ELIGIBLE'
assert result['results'][0]['native_disposition']['disposition']=='PROMOTE_NEXT_ROUND'
assert materialize_round_memory(**kwargs)==result
record=json.loads(Path(result['additional_member_refs'][0]['record']['path']).read_bytes())
assert record['proposed_recoveries'][0]['procedure_steps']==['look']
assert json.loads(Path(result['new_partition_ref']['path']).read_bytes())[record['memory_lineage_id']]['source_partition']=='TRAIN_UPDATE'

# The existing nonempty native snapshot is retained in the next publication.
# This exercises the producer output through unchanged native close/publish/load.
from pchsi.memory import dev_descriptive_snapshot_v2 as snapshots
if sys.platform=='win32':
    snapshots._write_once=binary_once
    snapshots._fsync_directory=lambda path:None
snapshot_helpers=load(native/'tests/memory/package_b_direct_test_helpers.py','snapshot_helpers')
old_root,old_snapshot,contract,contract_path,_=snapshot_helpers.published_snapshot(root)
from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
old=load_calibrated_dev_snapshot_v2(snapshot_directory=old_root,expected_snapshot_sha256=old_snapshot.snapshot_sha256,
    token_budget_contract_path=contract_path,expected_token_budget_contract_sha256=contract.contract_sha256)
from pchsi.memory.round_maintenance import MemoryRoundStateV1,MemoryRecordBindingV1,MemoryShadowEventV1,close_memory_round_v1
state=MemoryRoundStateV1(round_id=request.round_id,policy_identity_sha256=request.parent_policy_artifact_sha256,
    active_snapshot_sha256=old.snapshot.snapshot_sha256,active_record_bindings=tuple(MemoryRecordBindingV1(
    item.record.memory_lineage_id,item.record.record_version,item.record.canonical_record_sha256) for item in old.members))
event=MemoryShadowEventV1.from_dict(json.loads(Path(result['event_refs'][0]['path']).read_bytes()))
closure=close_memory_round_v1(state=state,shadow_events=(event,))
assert len(closure.next_active_record_bindings)==2
member_artifacts=[tuple((item.member_directory/name).read_bytes() for name in ('governed_record.json','retrieval_key.json','fm1.json','fm2.json')) for item in old.members]
member_artifacts.extend(tuple(Path(refs[key]['path']).read_bytes() for key in ('record','retrieval_key','fm1','fm2')) for refs in result['additional_member_refs'])
next_snapshot,files=snapshots.build_calibrated_snapshot_v2(package_a_sealed_head=old.snapshot.package_a_sealed_head,
    historical_package_a_snapshot_sha256=old.snapshot.historical_package_a_snapshot_sha256,token_budget_contract=contract,
    source_materialization_manifest_sha256=result['receipt_ref']['file_sha256'],member_artifacts=tuple(member_artifacts))
next_dir=root/'next_snapshots';next_dir.mkdir()
published=snapshots.publish_calibrated_snapshot_v2(output_root=next_dir,snapshot=next_snapshot,member_files=files)
loaded=load_calibrated_dev_snapshot_v2(snapshot_directory=published,expected_snapshot_sha256=next_snapshot.snapshot_sha256,
    token_budget_contract_path=contract_path,expected_token_budget_contract_sha256=contract.contract_sha256)
assert len(loaded.members)==2
assert old.members[0].record.to_dict() in [item.record.to_dict() for item in loaded.members]
from pchsi.memory.consumer_views import MemorySourcePartitionBindingV1,MemorySourcePartitionV1,MemoryPartitionAuthorityScopeV1,build_researcher_memory_view_v1,ResearcherPurposeV1
partitions={old.members[0].record.memory_lineage_id:MemorySourcePartitionBindingV1(old.members[0].record.memory_lineage_id,
    MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,old.snapshot.snapshot_sha256)}
for lineage,part in json.loads(Path(result['new_partition_ref']['path']).read_bytes()).items():
    part['source_partition']=MemorySourcePartitionV1(part['source_partition'])
    part['authority_scope']=MemoryPartitionAuthorityScopeV1(part['authority_scope'])
    partitions[lineage]=MemorySourcePartitionBindingV1(**part)
view=build_researcher_memory_view_v1(snapshot=loaded,purpose=ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,source_partition_by_lineage=partitions)
assert {row['source_partition'] for row in view.train_side_records}=={'TRAIN_MEMORY_SOURCE','TRAIN_UPDATE'}

# A future round cannot adopt this exact source/plan/call chain.
future=replace(request,round_id='ROUND2',request_sha256=None)
future_ref=put(root/'future_request.json',future.to_dict())
future_binding={**binding,'refs':{**binding['refs'],'request':future_ref}}
try: materialize_round_memory(**{**kwargs,'binding':future_binding,'output_root':root/'future'})
except ValueError as exc: assert 'CURRENT_PLAN_REQUEST_IDENTITY' in str(exc)
else: raise AssertionError('future round adopted prior evidence')
