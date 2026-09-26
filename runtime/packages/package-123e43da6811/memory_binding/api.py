"""Automatic exact-ref bridge from the existing local Analyzer and verifier outputs."""
import importlib.util
import json
from pathlib import Path

from .current_source import read_ref,sha,canonical
from .producer import (file_ref,write_once,load_attempt,build_experience,build_assembly,
    materialize_native_candidate,partition_for_record)
from .same_call import validate_boundaries
from .source_overlay import overlay_receipt
from .verifier_event import validate_verifier,build_shadow_event


def _read(path): return json.loads(read_ref(file_ref(path)))


def _one(values,label):
    if len(values)!=1: raise ValueError('MEMORY_EXACT_CARDINALITY:'+label)
    return values[0]


def _native_hash(value,field):
    from pchsi.reference_loop.canonical import domain_hash
    if value.get(field)!=domain_hash(value['schema_id'],value,excluded_field=field):
        raise ValueError('MEMORY_NATIVE_OBJECT_IDENTITY:'+field)


def load_registered_tokenizer(binding):
    """Use the original native local counter and exact current Memory runtime refs."""
    from pchsi.memory.token_budget_contract import FailureMemoryTokenBudgetContractV1
    memory=json.loads(read_ref(binding['refs']['memory_runtime']))
    runtime=json.loads(read_ref({'path':memory['source_runtime_binding_path'],
        'file_sha256':memory['source_runtime_binding_sha256']}))
    contract=FailureMemoryTokenBudgetContractV1.from_json(read_ref(binding['refs']['analyzer_token_contract']))
    if runtime.get('schema_id')!='FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1':
        raise ValueError('MEMORY_SOURCE_RUNTIME_SCHEMA')
    if runtime['tokenizer_identity_manifest_sha256']!=contract.tokenizer_revision:
        raise ValueError('MEMORY_TOKENIZER_CONTRACT_RUNTIME_IDENTITY')
    path=Path(binding['scientific_repo_root'])/'scripts/memory/rebuild_budgeted_dev_snapshot_v2.py'
    spec=importlib.util.spec_from_file_location('_current_native_memory_tokenizer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.LocalTokenizerCounter(tokenizer_id=contract.tokenizer_id,
        tokenizer_revision=contract.tokenizer_revision,local_path=Path(runtime['base_model_local_path']))


def _accepted_local(*,call_dir,request,context,unit_identity):
    from pchsi.cognitive_runtime.identity import build_logical_call_record
    from pchsi.cognitive_runtime.output_validation import validate_stage_output
    from pchsi.cognitive_runtime.response import parse_provider_response,extract_output_text
    logical=_read(call_dir/'logical_call.json')
    expected=build_logical_call_record(**{k:v for k,v in logical.items()
        if k not in {'schema_id','schema_version','logical_call_sha256'}})
    if logical!=expected or any(logical.get(k)!=v for k,v in {
            'terminal_method_status':'ACCEPTED','stage_id':'L-A1','condition_id':'A1',
            'round_id':request['round_id'],'policy_version':request['parent_policy_id'],
            'scientific_unit_identity_sha256':unit_identity['identity_sha256']}.items()):
        raise ValueError('MEMORY_ACCEPTED_LOCAL_CURRENT_IDENTITY')
    if call_dir.name!=logical['logical_call_id']:
        raise ValueError('MEMORY_ACCEPTED_CALL_PATH')
    rendered=_read(call_dir/'rendered_request.json')
    from pchsi.reference_loop.canonical import domain_hash
    if (rendered.get('request_body_sha256')!=logical['request_body_sha256'] or
            domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',rendered['provider_request'])!=logical['request_body_sha256']):
        raise ValueError('MEMORY_SAME_CALL_REQUEST_IDENTITY')
    raw=(call_dir/'raw_response.json').read_bytes()
    text=extract_output_text(parse_provider_response(raw))
    result=validate_stage_output(stage_id='L-A1',text=text,raw_response_sha256=sha(raw),projection=rendered['input_projection'])
    artifact=_read(call_dir/'validated_artifact.json')
    if result!=artifact or result['local_result_sha256']!=context['local_result_sha256']:
        raise ValueError('MEMORY_ACCEPTED_LOCAL_BYTES')
    rows=validate_boundaries(json.loads(text)['memory_boundary_registrations'],result)
    return result,rows,sha(raw),logical['logical_call_id']


def materialize_round_memory(*,binding,analyzer_output_root,execution_plan_ref,verifier_ref,output_root,tokenizer=None):
    """No provider/env call: registered current source -> real native objects/events.

The owner replays the original independent verify_plan before this operation.
This bridge additionally checks the exact current plan/request, all persisted arm
records and the original native pair/aggregate classifiers. All refs use
{path,file_sha256}; continuity refs can be projected to {path,sha256} mechanically.
"""
    request=json.loads(read_ref(binding['refs']['request']))
    plan,verifier=validate_verifier(plan_ref=execution_plan_ref,verifier_ref=verifier_ref,request=request)
    root=Path(analyzer_output_root).absolute();sink=Path(output_root).absolute()
    prepared=_read(root/'local/GROUP_PREPARATION_CENSUS.json')
    if prepared['round_id']!=request['round_id']: raise ValueError('MEMORY_SOURCE_CENSUS_ROUND')
    execution=_read(root/'local/strong_local_runtime/execution_manifest.json')
    if execution.get('round_id')!=request['round_id'] or execution.get('policy_version')!=request['parent_policy_id']:
        raise ValueError('MEMORY_LOCAL_EXECUTION_ROUND')
    universe=_read(root/'group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json')
    _native_hash(universe,'pair_universe_sha256')
    if universe['round_id']!=request['round_id'] or universe['parent_policy_id']!=request['parent_policy_id']:
        raise ValueError('MEMORY_PAIR_UNIVERSE_ROUND')
    source_units=_read(root/'local/SOURCE_UNITS.json')['rows']
    if tokenizer is None: tokenizer=load_registered_tokenizer(binding)
    contract=json.loads(read_ref(binding['refs']['analyzer_token_contract']))
    if (tokenizer.tokenizer_id,tokenizer.tokenizer_revision)!=(contract['tokenizer_id'],contract['tokenizer_revision']):
        raise ValueError('MEMORY_TOKENIZER_FROZEN_IDENTITY')
    events=[];members=[];partitions={};results=[]
    for state in verifier['state_results']:
        state_sha=state['source_state_sha256'];candidate_sha=state['source_candidate_sha256']
        pair=_one([row for row in universe['pair_table'] if row['source_state_sha256']==state_sha],'candidate state')
        selected=[pair[key] for key in ('A2','A3') if pair[key]['candidate_sha256']==candidate_sha]
        if not selected: raise ValueError('MEMORY_VERIFIER_CANDIDATE_NOT_REGISTERED')
        if len({canonical(row['candidate']) for row in selected})!=1: raise ValueError('MEMORY_CANDIDATE_BYTES_CONFLICT')
        source_entry=prepared['sources'][state_sha];context=source_entry['context'];sid=source_entry['source_unit_id']
        sm_ref=_one([row['source_manifest'] for row in source_units if row['source_unit_id']==sid],'source unit')
        sm=json.loads(read_ref(sm_ref));_native_hash(sm,'source_unit_manifest_sha256')
        if (sm['round_id']!=request['round_id'] or sm['source_unit_id']!=sid or
                sm['rollout_handoff_sha256']!=binding['refs']['handoff']['file_sha256'] or
                sm['attempt_bundle_sha256']!=source_entry['bundle_sha256'] or
                sm['attempt_bundle_path']!=source_entry['bundle_path']):
            raise ValueError('MEMORY_CURRENT_SOURCE_MANIFEST')
        call=_one([row for row in execution['rows'] if row['source_unit_id']==sid and row['stage_id']=='L-A1'],'accepted local call')
        if call.get('status')!='ACCEPTED': raise ValueError('MEMORY_SOURCE_CALL_NOT_ACCEPTED')
        call_dir=Path(call['call_dir']).absolute()
        if call_dir.parent!=(root/'local/strong_local_runtime'): raise ValueError('MEMORY_LOCAL_CALL_ROOT')
        unit_identity=_read(root/'local/units'/sid/'scientific_unit_identity.json')
        _native_hash(unit_identity,'identity_sha256')
        local,boundaries,raw_sha,logical_id=_accepted_local(call_dir=call_dir,request=request,context=context,unit_identity=unit_identity)
        error=_one([row for row in local['error_instances'] if row['error_instance_id']==context['error_instance_id']],'accepted local error')
        boundary=_one([row for row in boundaries if row['error_instance_id']==error['error_instance_id']],'same call boundary')
        source=load_attempt(binding['scientific_repo_root'],source_entry['bundle_path'])
        if source.attempt_bundle.attempt_bundle_sha256!=source_entry['bundle_sha256']:
            raise ValueError('MEMORY_SOURCE_BUNDLE_BYTES')
        if (local['task_id']!=source.episode_artifact.task_id or local['gamefile_sha256']!=source.episode_artifact.gamefile_sha256
                or local['evidence_pack_sha256']!=sm['evidence_pack_sha256']):
            raise ValueError('MEMORY_LOCAL_SOURCE_EPISODE_IDENTITY')
        condition=source.episode_artifact.policy_condition_id
        if not condition: raise ValueError('MEMORY_ACTUAL_POLICY_CONDITION_REQUIRED')
        experience,access=build_experience(source=source,request_ref=binding['refs']['request'],
            train_manifest_ref=binding['refs']['train_update_manifest'],local_result=local,error=error,
            condition=condition,raw_response_sha256=raw_sha)
        state_root=sink/state_sha
        exp_ref=write_once(state_root/'source_experience.json',experience.canonical_bytes())
        access_ref=write_once(state_root/'CURRENT_SOURCE_ACCESS_V2.json',canonical(access.to_dict()))
        origin_ref=write_once(state_root/'ACCEPTED_ANALYZER_BOUNDARY_ORIGIN.json',canonical({
            'local_result_ref':file_ref(call_dir/'validated_artifact.json'),'raw_response_ref':file_ref(call_dir/'raw_response.json'),
            'logical_call_ref':file_ref(call_dir/'logical_call.json'),'boundary':boundary,'error':error,
            'source_state_sha256':state_sha,'candidate_sha256':candidate_sha,'request_ref':binding['refs']['request']}))
        candidate_ref=write_once(state_root/'SELECTED_ANALYZER_CANDIDATE.json',canonical(selected[0]['candidate']))
        assembly=build_assembly(experience=experience,local_result=local,error=error,boundary=boundary,
            raw_response_sha256=raw_sha,logical_call_id=logical_id,candidate=selected[0]['candidate'])
        row={'source_state_sha256':state_sha,'candidate_sha256':candidate_sha,
             'experience_ref':exp_ref,'source_access_ref':access_ref,'origin_ref':origin_ref,'candidate_ref':candidate_ref}
        if assembly is None:
            results.append(dict(row,status='UNRESOLVED_APPLICABILITY',reason=boundary['unresolved_reason']))
            continue
        record,report,bundle,final,refs=materialize_native_candidate(experience=experience,assembly=assembly,
            tokenizer=tokenizer,output_root=state_root/'native_candidate')
        eligible=bundle is not None and bundle.governed_record is not None
        event_record=bundle.governed_record if eligible else record
        event,event_ref=build_shadow_event(request=request,record=event_record,eligible=eligible,access=access,
            local_result_sha256=local['local_result_sha256'],candidate_sha256=candidate_sha,
            source_state_sha256=state_sha,plan=plan,verifier=verifier,verifier_ref=verifier_ref,output_root=state_root)
        from pchsi.memory.round_maintenance import classify_shadow_event_v1
        disposition=classify_shadow_event_v1(event)
        events.append(event_ref)
        if eligible and disposition.disposition.value=='PROMOTE_NEXT_ROUND':
            members.append({key:file_ref(final/filename) for key,filename in {
                'record':'governed_record.json','retrieval_key':'retrieval_key.json','fm1':'fm1.json','fm2':'fm2.json'}.items()})
            part=partition_for_record(event_record,access,refs['assembly'])
            partitions[event_record.memory_lineage_id]=part.to_dict()
        results.append(dict(row,status='NATIVE_MEMORY_CANDIDATE_MATERIALIZED',assembly_ref=refs['assembly'],
            native_manifest_ref=file_ref(final/'artifact_manifest.json'),native_eligibility=None if bundle is None else bundle.status,
            native_failure_codes=[] if bundle is None else list(bundle.failure_codes),event_ref=event_ref,
            native_disposition=disposition.to_dict()))
    partition_ref=write_once(sink/'NEW_NATIVE_SOURCE_PARTITIONS.json',canonical(partitions))
    receipt={'schema_id':'CURRENT_ROUND_NATIVE_MEMORY_MATERIALIZATION_V2','round_id':request['round_id'],
        'request_sha256':request['request_sha256'],'event_refs':events,'additional_member_refs':members,
        'new_partition_ref':partition_ref,'results':results,'source_overlay':overlay_receipt(),
        'provider_calls_added':0,'same_round_active_memory_writeback':False}
    receipt_ref=write_once(sink/'MEMORY_MATERIALIZATION_RESULT.json',canonical(receipt))
    return dict(receipt,receipt_ref=receipt_ref)
