from pathlib import Path
import importlib.util
import os
import pytest

from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1, RoundRolloutExecutionBindingV1
from pchsi.memory.round_maintenance import MemoryRoundStateV1
from test_api import put, request, evidence
from test_next_request import governance


def snapshot_fixture(tmp_path, monkeypatch):
    native = Path(__file__).resolve().parents[2] / 'native_bba_full'
    monkeypatch.chdir(native)
    # Windows has no POSIX directory fsync. Scientific builders, serializer,
    # member hashes, publisher and loader remain the real captured functions.
    if os.name == 'nt':
        import pchsi.memory.dev_descriptive_snapshot_v2 as m
        monkeypatch.setattr(m, '_fsync_directory', lambda path: None)
        # Native POSIX os.open omits O_BINARY; Windows otherwise translates LF.
        def binary_exclusive_write(path, raw):
            with path.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        monkeypatch.setattr(m, '_write_once', binary_exclusive_write)
    spec = importlib.util.spec_from_file_location('native_snapshot_fixture_helpers',
        native/'tests/memory/package_b_direct_test_helpers.py')
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    return helpers.published_snapshot(tmp_path)


def test_actual_snapshot_to_initial_state_close_next_request_and_revalidation(tmp_path, monkeypatch):
    from continuity_binding.memory_materializer import register_initial_memory_state, materialize_next_memory_runtime
    from continuity_binding.api import read_ref, materialize_no_training_update, close_memory_round_from_refs
    from continuity_binding.next_request import materialize_next_request, validate_native_next_request
    from dataclasses import fields
    final, snapshot, contract, contract_path, _ = snapshot_fixture(tmp_path, monkeypatch)
    memory_ref = put(tmp_path, 'memory_runtime.json', {'schema_id':'FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1',
        'active_snapshot_directory':str(final), 'active_snapshot_sha256':snapshot.snapshot_sha256,
        'token_budget_contract_path':str(contract_path), 'token_budget_contract_sha256':contract.contract_sha256})
    runtime = {'policy_runtime_manifest_sha256':'a'*64,'served_model_name':'fixture-parent',
               'continuation_request_contract':{'fixture':True}}
    runtime_ref = put(tmp_path, 'runtime.json', runtime)
    profile_ref = put(tmp_path, 'profile.json', {'schema_id':'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1',
        'policy_version':'fixture-parent','served_model_name':'fixture-parent',
        'continuation_request_contract':runtime['continuation_request_contract']})
    train_ref = put(tmp_path, 'train_manifest.jsonl', {'fixture':'TRAIN_UPDATE'})
    start = request()
    start.update(policy_runtime_binding_sha256=runtime_ref['sha256'],
        execution_profile_sha256=profile_ref['sha256'], train_update_manifest_sha256=train_ref['sha256'],
        round_memory_runtime_authority_sha256=memory_ref['sha256'],
        round_start_memory_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_sha256=contract.contract_sha256, request_sha256=None)
    start = RoundRolloutCollectionRequestV1(**{f.name:start[f.name] for f in fields(RoundRolloutCollectionRequestV1)}).to_dict()
    start, refs = evidence(tmp_path/'round', benefits=0, start=start)
    state_ref = register_initial_memory_state(start=start, runtime_ref=memory_ref, sink=tmp_path/'state')
    assert len(MemoryRoundStateV1.from_dict(read_ref(state_ref)).active_record_bindings) == 1
    closure_ref = close_memory_round_from_refs(start=start, state_ref=state_ref, event_refs=[], sink=tmp_path/'closed')
    next_memory = materialize_next_memory_runtime(start=start, state_ref=state_ref, event_refs=[],
        current_runtime_ref=memory_ref, additional_member_refs=[], sink=tmp_path/'memory-next')
    assert next_memory['runtime'] == memory_ref
    refs.update(memory_state=state_ref, memory_shadow_events=[], memory_closure=closure_ref,
        no_training_update=materialize_no_training_update(start=start, evidence_refs=refs, sink=tmp_path/'closed'))
    result = {**start, 'outcome':'NO_TRAINING_UPDATE', 'next_parent_policy_id':start['parent_policy_id'],
        'next_parent_policy_artifact_sha256':start['parent_policy_artifact_sha256'], 'stage_evidence_refs':refs}
    inputs_ref = put(tmp_path, 'inputs.json', {'schema_id':'ROUND_ROLLOUT_INPUT_REFERENCES_V1',
        'runtime':runtime_ref,'profile':profile_ref,'memory':next_memory['runtime'],'train_manifest':train_ref})
    binding = RoundRolloutExecutionBindingV1(request_sha256=start['request_sha256'], scientific_execution_authorized=True,
        **{f.name:'a'*64 for f in fields(RoundRolloutExecutionBindingV1)
           if f.name.endswith('_sha256') and f.name not in {'request_sha256','binding_sha256'}})
    binding_ref = put(tmp_path, 'execution_binding.json', binding.to_dict())
    out = materialize_next_request(start=start, result=result, governance=governance(),
        next_inputs_ref=inputs_ref, current_binding_ref=binding_ref, sink=tmp_path/'next')
    refs.update(next_inputs=out['input_refs'], next_memory_state=out['memory_state'],
                next_execution_binding=out['execution_binding'], rollout_execution_binding=binding_ref)
    assert validate_native_next_request(start=start,result=result,next_request=out['next_request'],governance=governance())
    assert out['next_request']['round_id'] != start['round_id']
    assert out['next_request']['round_start_memory_snapshot_sha256'] == snapshot.snapshot_sha256


def test_native_benefit_record_publishes_changed_snapshot_and_missing_record_is_rejected(tmp_path, monkeypatch):
    from dataclasses import fields, replace
    import pchsi.memory.procedural_builder as builder
    from pchsi.memory.procedural_record import ProceduralMemoryLineageV1, PreviousProceduralRecordBindingV1
    from pchsi.memory.source_integrity import audit_memory_source_integrity_v1
    from pchsi.memory.descriptive_eligibility import govern_descriptive_dev_record_v1
    from pchsi.memory.lifecycle_relations import EvaluationContaminationStatusV1
    from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
    from pchsi.memory.retrieval_key import build_memory_retrieval_key_v1
    from pchsi.memory.matched_raw_view import build_fm1_matched_raw_episodic_view_v1
    from pchsi.memory.policy_projection import build_failure_memory_policy_projection_v1
    from pchsi.memory.projection_common import ProjectionClassV1
    from pchsi.memory.round_maintenance import MemoryShadowEventV1, MemoryRecordBindingV1, MemorySourcePartitionV1, VerifierEffectV1
    from continuity_binding.memory_materializer import register_initial_memory_state, materialize_next_memory_runtime
    from continuity_binding.api import read_ref
    final, snapshot, contract, contract_path, tokenizer = snapshot_fixture(tmp_path, monkeypatch)
    loaded = load_calibrated_dev_snapshot_v2(snapshot_directory=final, expected_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_path=contract_path, expected_token_budget_contract_sha256=contract.contract_sha256)
    previous = loaded.members[0].record
    spec = importlib.util.spec_from_file_location('native_builder_helpers', 'tests/memory/test_procedural_memory_builder.py')
    helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
    experience = helpers._experience()
    lineage = ProceduralMemoryLineageV1(memory_lineage_id=previous.memory_lineage_id,
        record_version=previous.record_version+1, previous_record_binding=PreviousProceduralRecordBindingV1(
            memory_lineage_id=previous.memory_lineage_id, record_version=previous.record_version,
            canonical_record_sha256=previous.canonical_record_sha256))
    assembly = helpers._assembly_input(builder,(experience,),lineage=lineage,
        semantic=previous.semantic_hypotheses, rid='TEST-NATIVE-NEXT-ASSEMBLY')
    assembly = replace(assembly, applicability=previous.applicability)
    record = builder.build_procedural_failure_memory_record_v1(assembly_input=assembly,
        assembly_registration_binding=helpers._registration_binding(builder,assembly),
        source_experiences=(experience,), previous_record=previous)
    report = audit_memory_source_integrity_v1(record=record,registered_experiences=(experience,))
    bundle = govern_descriptive_dev_record_v1(record=record,source_report=report,source_experience=experience,
        tokenizer=tokenizer,evaluation_contamination_status=EvaluationContaminationStatusV1.CLEAN)
    governed = bundle.governed_record
    assert governed is not None, bundle.failure_codes
    key = build_memory_retrieval_key_v1(governed)
    fm1 = build_fm1_matched_raw_episodic_view_v1(record=governed,experience=experience,tokenizer=tokenizer,
        hard_ceiling=contract.single_record_hard_ceiling)
    fm2 = build_failure_memory_policy_projection_v1(record=governed,projection_class=ProjectionClassV1.FM2,
        tokenizer=tokenizer,hard_ceiling=contract.single_record_hard_ceiling)
    refs = {name:put(tmp_path,'new-member/'+name+'.json',obj.to_dict())
            for name,obj in {'record':governed,'retrieval_key':key,'fm1':fm1,'fm2':fm2}.items()}
    runtime_ref = put(tmp_path,'runtime.json',{'schema_id':'FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1',
        'active_snapshot_directory':str(final),'active_snapshot_sha256':snapshot.snapshot_sha256,
        'token_budget_contract_path':str(contract_path),'token_budget_contract_sha256':contract.contract_sha256})
    start = request(); start.update(round_start_memory_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_sha256=contract.contract_sha256,round_memory_runtime_authority_sha256=runtime_ref['sha256'],request_sha256=None)
    start = RoundRolloutCollectionRequestV1(**{f.name:start[f.name] for f in fields(RoundRolloutCollectionRequestV1)}).to_dict()
    state_ref = register_initial_memory_state(start=start,runtime_ref=runtime_ref,sink=tmp_path/'state')
    event = MemoryShadowEventV1(round_id=start['round_id'],record_binding=MemoryRecordBindingV1(
        governed.memory_lineage_id,governed.record_version,governed.canonical_record_sha256),
        source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,analyzer_finding_sha256='c'*64,
        candidate_repair_sha256='d'*64,verifier_effect=VerifierEffectV1.BENEFIT,
        f0_evidence_sha256='e'*64,f1_evidence_sha256='f'*64,evidence_complete=True,evaluation_contamination_clean=True)
    event_refs = [put(tmp_path,'event.json',event.to_dict())]
    with pytest.raises(ValueError,match='MEMORY_NEXT_RECORD_ARTIFACTS_NOT_PRODUCED'):
        materialize_next_memory_runtime(start=start,state_ref=state_ref,event_refs=event_refs,
            current_runtime_ref=runtime_ref,additional_member_refs=[],sink=tmp_path/'missing')
    assert not (tmp_path/'missing').exists()
    out = materialize_next_memory_runtime(start=start,state_ref=state_ref,event_refs=event_refs,
        current_runtime_ref=runtime_ref,additional_member_refs=[refs],sink=tmp_path/'next-memory')
    assert out['snapshot_retained'] is False
    assert out['snapshot_sha256'] != snapshot.snapshot_sha256
    nxt = read_ref(out['runtime'])
    reloaded = load_calibrated_dev_snapshot_v2(snapshot_directory=Path(nxt['active_snapshot_directory']),
        expected_snapshot_sha256=nxt['active_snapshot_sha256'],token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=contract.contract_sha256)
    assert reloaded.members[0].record.canonical_record_sha256 == governed.canonical_record_sha256
    assert materialize_next_memory_runtime(start=start,state_ref=state_ref,event_refs=event_refs,
        current_runtime_ref=runtime_ref,additional_member_refs=[refs],sink=tmp_path/'next-memory') == out
