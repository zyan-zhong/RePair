"""Real native fixture chain; only counter and input evidence are test fixtures."""
from dataclasses import fields
import importlib.util
from pathlib import Path
import runpy
import sys

from continuity_binding.api import write_once, read_ref
from pchsi.memory import dev_descriptive_snapshot_v2 as snapshots
from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
from pchsi.memory.consumer_views import MemorySourcePartitionBindingV1, MemorySourcePartitionV1
from pchsi.round_control.rollout_collection import RoundRolloutExecutionBindingV1
from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
from pchsi.cognitive_runtime.identity import build_logical_call_record
from pchsi.reference_loop.canonical import domain_hash
from pchsi.round_control.campaign_authority import freeze_campaign_startup_authority
from pchsi.round_control.scientific_round_governance import new_scientific_round_governance, advance_scientific_round_governance
from entry.tail import close_round_tail, build_next_round_tail, _training_terminal

root = Path(case_root)
native = Path.cwd()
project = Path(__file__).resolve().parents[4]
if sys.platform == 'win32':
    # Native publisher assumes POSIX binary writes and directory fsync.
    def binary_once(path, raw):
        with Path(path).open('xb') as stream:
            stream.write(raw)
    snapshots._write_once = binary_once
    snapshots._fsync_directory = lambda path: None
spec = importlib.util.spec_from_file_location('tail_snapshot_helpers', native/'tests/memory/package_b_direct_test_helpers.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
initial = root/'initial'; initial.mkdir()
directory, snapshot, contract, contract_path, tokenizer = helpers.published_snapshot(initial)
runtime_ref = write_once(initial/'actor.json', {'policy_runtime_manifest_sha256':'a'*64,
    'served_model_name':'fixture-pi0', 'continuation_request_contract':{'fixture':'I1'}})
profile_ref = write_once(initial/'profile.json', {'schema_id':'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1',
    'policy_version':'pi0', 'served_model_name':'fixture-pi0', 'continuation_request_contract':{'fixture':'I1'}})
memory_ref = write_once(initial/'memory.json', {'schema_id':'FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1',
    'active_snapshot_directory':str(directory), 'active_snapshot_sha256':snapshot.snapshot_sha256,
    'token_budget_contract_path':str(contract_path), 'token_budget_contract_sha256':contract.contract_sha256})
fixture = runpy.run_path(str(project/'work/v17/memory_binding/tests/native_end_to_end_case.py'), init_globals={
    'case_root':str(root), 'request_overrides':{
        'policy_runtime_binding_sha256':runtime_ref['sha256'], 'execution_profile_sha256':profile_ref['sha256'],
        'round_memory_runtime_authority_sha256':memory_ref['sha256'],
        'round_start_memory_snapshot_sha256':snapshot.snapshot_sha256,
        'token_budget_contract_sha256':contract.contract_sha256},
    'handoff_overrides':{'source_pre_primary_record_sha256':'b'*64}})
start = fixture['request'].to_dict()
file_ref = fixture['file_ref']
def memory_ref_shape(ref): return {'path':ref['path'], 'file_sha256':ref['sha256']}
def tail_ref_shape(ref): return {'path':ref['path'], 'sha256':ref['file_sha256']}
loaded = load_calibrated_dev_snapshot_v2(snapshot_directory=directory,
    expected_snapshot_sha256=snapshot.snapshot_sha256, token_budget_contract_path=contract_path,
    expected_token_budget_contract_sha256=contract.contract_sha256)
parts = {member.record.memory_lineage_id:MemorySourcePartitionBindingV1(
    member.record.memory_lineage_id, MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
    snapshot.snapshot_sha256).to_dict() for member in loaded.members}
parts_ref = write_once(initial/'partitions.json', parts)
binding = {**fixture['binding'], 'refs':{**fixture['binding']['refs'],
    'actor_runtime':memory_ref_shape(runtime_ref), 'memory_runtime':memory_ref_shape(memory_ref),
    'analyzer_token_contract':file_ref(contract_path), 'memory_source_partitions':memory_ref_shape(parts_ref)}}
current_inputs_ref = write_once(initial/'inputs.json', {'schema_id':'ROUND_ROLLOUT_INPUT_REFERENCES_V1',
    'runtime':runtime_ref, 'profile':profile_ref, 'memory':memory_ref,
    'train_manifest':tail_ref_shape(fixture['train_ref'])})
execution = RoundRolloutExecutionBindingV1(request_sha256=start['request_sha256'],
    scientific_execution_authorized=True, **{f.name:'a'*64 for f in fields(RoundRolloutExecutionBindingV1)
        if f.name.endswith('_sha256') and f.name not in {'request_sha256','binding_sha256'}})
execution_ref = write_once(initial/'execution.json', execution.to_dict())
plan_ref = tail_ref_shape(file_ref(fixture['plan_path']))
verifier_ref = tail_ref_shape(file_ref(fixture['run']/'verifier/ENVIRONMENT_RESULT_PACKAGE.json'))
verifier = read_ref(verifier_ref)
projection = {'round_id':start['round_id'], 'primary_pre_record_sha256':'b'*64,
    'environment_result_package_sha256':verifier['environment_result_package_sha256'],
    'environment_result_package':verifier}
post = finalize_api_post_primary_v1({'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','schema_version':1,
    'round_id':start['round_id'],'protocol_audit':'Native fixture only', 'observed_outcome':'Fixture',
    'numerator':1,'denominator':1,'unexpected_evidence':[],'hypothesis_status':'UNRESOLVED',
    'alternative_explanations':['Fixture'], 'researcher_training_recommendation':'NO_TRAIN',
    'researcher_promotion_recommendation':'HOLD','lesson':'Fixture','next_round_implication':'Retain parent',
    'primary_record_sha256':'0'*64}, projection=projection)
identity = {'scientific_unit_identity_sha256':'c'*64,'stage_id':'R-POST-PRIMARY-V1','condition_id':None,
    'round_id':start['round_id'],'policy_version':start['parent_policy_id'],'request_body_sha256':'d'*64}
logical_id = domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1', identity)
logical = build_logical_call_record(**identity, logical_call_id=logical_id,
    terminal_method_status='ACCEPTED', contributing_attempt_id='fixture', role='TRAINING_RESEARCHER',
    runtime_manifest_sha256='e'*64)
post_root = root/'post'/logical_id
evidence = {'execution_plan':plan_ref,'verifier':verifier_ref,
    'post_projection':write_once(root/'post/projection.json', projection),
    'post_artifact':write_once(post_root/'validated_artifact.json', post),
    'post_logical_call':write_once(post_root/'logical_call.json', logical)}
kwargs = dict(start=start, analyzer_binding=binding, analyzer_output_root=fixture['analyzer'],
    attempt_root=root/'attempt', stage_evidence_refs=evidence, current_inputs_ref=current_inputs_ref,
    current_execution_binding_ref=execution_ref, tokenizer=tokenizer)
result = close_round_tail(**kwargs)
assert result['outcome'] == 'NO_TRAINING_UPDATE'
assert read_ref(result['terminal_ref'])['verified_benefit_count'] == 1
assert read_ref(result['terminal_ref'])['training_execution_count'] == 0
assert len(read_ref(result['stage_evidence_refs']['memory_source_partitions'])) == 2
assert len(read_ref(result['stage_evidence_refs']['memory_closure'])['next_active_record_bindings']) == 2
assert close_round_tail(**kwargs) == result

def governor(maximum):
    authority = freeze_campaign_startup_authority(campaign_id='tail-fixture',requested_max_valid_rounds=maximum,
        no_promotion_patience=4,max_infrastructure_attempt_restarts=1,force_run_all_rounds=False,
        campaign_purpose_sha256='a'*64,heldout_firewall_sha256='b'*64,paper_export_contract_sha256='c'*64)
    return advance_scientific_round_governance(new_scientific_round_governance(authority=authority),outcome=result['outcome'])

nxt = build_next_round_tail(start=start,result=result,governance=governor(2),attempt_root=root/'attempt')
assert nxt['next_request']['parent_policy_id'] == start['parent_policy_id']
assert nxt['next_request']['round_start_memory_snapshot_sha256'] != start['round_start_memory_snapshot_sha256']
assert read_ref(nxt['memory_state'])['parent_round_id'] == start['round_id']
assert result['next_request'] is None  # owner's immutable result was not changed
assert build_next_round_tail(start=start,result=result,governance=governor(2),attempt_root=root/'attempt') == nxt
try:
    build_next_round_tail(start=start,result=result,governance=governor(1),attempt_root=root/'stopped')
except ValueError as exc:
    assert 'GOVERNOR_STOP' in str(exc)
else:
    raise AssertionError('created next request after native STOP')
assert not (root/'stopped').exists()
try:
    close_round_tail(**{**kwargs,'training_result_ref':result['terminal_ref'],'attempt_root':root/'bad-no-train'})
except ValueError as exc:
    assert 'NO_TRAIN_CANNOT_CONSUME' in str(exc)
else:
    raise AssertionError('NO_TRAIN consumed training input')
assert not (root/'bad-no-train').exists()

# GIVEN native promotion fixture: validate identity without claiming evaluation.
from pchsi.round_control.promotion import freeze_promotion_decision
parent = {'policy_id':start['parent_policy_id'],'artifact_sha256':start['parent_policy_artifact_sha256']}
candidate = {'policy_id':'fixture-trained','artifact_sha256':'7'*64,
    **{key:start[key] for key in ('round_id','request_sha256','execution_attempt_id','parent_policy_id','parent_policy_artifact_sha256')}}
rule_ref = write_once(root/'promotion-fixture/rule.json', {'decision_rule_id':'GIVEN_FIXTURE_ONLY'})
protocol_ref = write_once(root/'promotion-fixture/protocol.json', {'promotion_rule_ref':rule_ref})
off_binding_ref = write_once(root/'promotion-fixture/binding.json',
    {'schema_id':'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1','input_refs':{
        'request_ref':tail_ref_shape(fixture['request_ref']), 'protocol_ref':protocol_ref,
        'parent_ref':write_once(root/'promotion-fixture/parent.json', parent),
        'candidate_ref':write_once(root/'promotion-fixture/candidate.json', candidate)}})
summary_ref = write_once(root/'promotion-fixture/summary.json', {'schema_id':'CURRENT_TRAIN_SELECT_AGGREGATE_V1',
    'round_id':start['round_id'],'request_sha256':start['request_sha256'],'parent_policy_id':parent['policy_id'],
    'candidate_policy_id':candidate['policy_id'],'memory_state':'OFF','harness_state':'OFF',
    'evidence_access_class':'TRAIN_SELECT','benchmark_feedback_used':False,'frozen_protocol_ref':protocol_ref})
for decision, outcome in [('PROMOTE','PROMOTED'),('ROLLBACK','ROLLED_BACK')]:
    promotion = freeze_promotion_decision(round_id=start['round_id'],decision=decision,decision_rule_id='GIVEN_FIXTURE_ONLY',
        evidence_access_class='TRAIN_SELECT',evidence_sha256=summary_ref['sha256'],
        parent_policy_id=parent['policy_id'],candidate_policy_id=candidate['policy_id'])
    promotion_ref = write_once(root/f'promotion-fixture/{decision}.json', promotion.to_dict())
    chosen = candidate if decision == 'PROMOTE' else parent
    terminal = {'schema_id':'CURRENT_NATIVE_OFFOFF_TERMINAL_V1','round_id':start['round_id'],
        'request_sha256':start['request_sha256'],'binding_ref':off_binding_ref,'summary_ref':summary_ref,
        'promotion_ref':promotion_ref,'outcome':outcome,'next_parent_policy_id':chosen['policy_id'],
        'next_parent_policy_artifact_sha256':chosen['artifact_sha256'],'human_scientific_decision_count':0,
        'benchmark_feedback_used':False}
    terminal_ref = write_once(root/f'promotion-fixture/{decision}-terminal.json', terminal)
    assert _training_terminal(start,terminal_ref) == (terminal,promotion_ref)
    bad = write_once(root/f'promotion-fixture/{decision}-wrong-policy.json',
        {**terminal,'next_parent_policy_artifact_sha256':'8'*64})
    try:
        _training_terminal(start,bad)
    except ValueError as exc:
        assert 'NEXT_ARTIFACT' in str(exc)
    else:
        raise AssertionError('adopted different policy bytes under native promotion')
