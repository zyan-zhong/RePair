"""Hydrated current POST using the frozen cognitive runtime; never a new client.

The native trainer and next-round consumer are not implemented by this adapter.
A successful causal/PRE+POST receipt is not a full round-closure claim.
"""
from __future__ import annotations
from contextlib import ExitStack
import copy, fcntl, json, sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'native_repo/src'),str(ROOT)]
from io_utils import read_json, put_json, sha, canonical as canon, digest_file



def _resolve_scientific_input_root(run_root: Path, plan: dict) -> Path:
    """Resolve the immutable capture input without assuming operational-root layout.

    Normal attempts own ``run_root/input``. Recovery attempts deliberately may
    not duplicate that tree; in that case the hash-bound ``runtime_path`` in
    EXECUTION_PLAN anchors the exact original capture input.
    """
    run_input = Path(run_root) / 'input'
    direct_required = (
        run_input / 'pre_root' / 'PCHSI_V1232Z_TERMINAL_V1.json',
        run_input / 'native_execution_gate' / 'HYPOTHESIS_SCOPE_NOTICE_V1.json',
    )
    if all(path.is_file() and not path.is_symlink() for path in direct_required):
        return run_input

    runtime_value = plan.get('runtime_path')
    runtime_sha = plan.get('runtime_file_sha256')
    if not isinstance(runtime_value, str) or not runtime_value:
        raise ValueError('POST_PLAN_RUNTIME_PATH_MISSING')
    if not isinstance(runtime_sha, str) or len(runtime_sha) != 64:
        raise ValueError('POST_PLAN_RUNTIME_SHA_MISSING')
    runtime_path = Path(runtime_value)
    if runtime_path.is_symlink() or not runtime_path.is_file():
        raise FileNotFoundError('POST_PLAN_RUNTIME_PATH_NOT_FILE:' + str(runtime_path))
    if digest_file(runtime_path) != runtime_sha:
        raise ValueError('POST_PLAN_RUNTIME_FILE_HASH_MISMATCH')
    input_root = runtime_path.parent.parent
    required = (
        input_root / 'pre_root' / 'PCHSI_V1232Z_TERMINAL_V1.json',
        input_root / 'native_execution_gate' / 'HYPOTHESIS_SCOPE_NOTICE_V1.json',
    )
    for path in required:
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError('POST_SCIENTIFIC_INPUT_REQUIRED_FILE_MISSING:' + str(path))
    return input_root


def _terminal(call:Path, *, expected:dict, projection:dict):
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    from pchsi.reference_loop.canonical import domain_hash
    logical=read_json(call/'logical_call.json')
    for k,v in expected.items():
        if logical.get(k)!=v:raise ValueError('POST_LOGICAL_IDENTITY_MISMATCH:'+k)
    if logical.get('terminal_method_status')!='ACCEPTED':
        return None,str(logical.get('terminal_method_status'))
    a=read_json(call/'validated_artifact.json')
    if a.get('primary_record_sha256')!=domain_hash('API_RESEARCHER_POST_PRIMARY_V1',a,excluded_field='primary_record_sha256'):
        raise ValueError('POST_ARTIFACT_CONTENT_HASH_MISMATCH')
    if finalize_api_post_primary_v1(a,projection=projection)!=a:raise ValueError('POST_FINALIZER_DRIFT')
    return a,'ACCEPTED'



def route_accepted_post_artifact(*, run_root: Path, plan: dict, verifier: dict, artifact: dict, logical_call_id: str, provider_calls: int = 0) -> dict:
    """Route one already-validated accepted POST without another provider call."""
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.round_control.no_training_update import freeze_no_training_update

    postdir = Path(run_root) / 'post'
    projection = read_json(postdir / 'projection.json')
    if finalize_api_post_primary_v1(artifact, projection=projection) != artifact:
        raise ValueError('POST_ROUTING_FINALIZER_DRIFT')
    if artifact.get('primary_record_sha256') != domain_hash(
        'API_RESEARCHER_POST_PRIMARY_V1', artifact, excluded_field='primary_record_sha256'
    ):
        raise ValueError('POST_ROUTING_ARTIFACT_HASH_MISMATCH')
    if verifier.get('environment_result_package_sha256') != artifact.get('environment_result_package_sha256'):
        raise ValueError('POST_ROUTING_VERIFIER_MISMATCH')

    input_root = _resolve_scientific_input_root(Path(run_root), plan)
    z = read_json(input_root / 'pre_root' / 'PCHSI_V1232Z_TERMINAL_V1.json')
    pre = read_json(input_root / 'pre_root' / 'strong_pre_runtime' / z['accepted_pre_logical_call_id'] / 'validated_artifact.json')
    if pre.get('primary_record_sha256') != plan['handoff']['source_pre_primary_record_sha256']:
        raise ValueError('POST_ROUTING_PRE_HANDOFF_MISMATCH')

    counts = verifier['stable_effect_counts']
    benefits = counts['BENEFIT']
    rec = artifact['researcher_training_recommendation']
    if rec not in ('TRAIN', 'NO_TRAIN') or (benefits == 0 and rec != 'NO_TRAIN'):
        raise ValueError('POST_TYPED_TRAINING_ROUTE_INVALID')

    result = {
        'schema_id':'CURRENT_CAUSAL_POST_TERMINAL_V1',
        'round_id':plan['round_id'],
        'plan_sha256':plan['plan_sha256'],
        'post_sha256':artifact['primary_record_sha256'],
        'logical_call_id':logical_call_id,
        'training_recommendation':rec,
        'verified_benefit_count':benefits,
        'training_execution_count':0,
        'round_closed':False,
        'next_round_launched':False,
        'full_max10_released':False,
        'human_disposition_required':False,
    }
    if rec == 'TRAIN':
        benefit_states = [
            dict(row) for row in verifier.get('state_results', [])
            if row.get('stable_effect') == 'BENEFIT'
        ]
        if len(benefit_states) != benefits:
            raise ValueError('POST_BENEFIT_STATE_COUNT_MISMATCH')
        training_handoff = {
            'schema_id':'CURRENT_VERIFIED_TRAINING_HANDOFF_V1',
            'schema_version':1,
            'round_id':plan['round_id'],
            'plan_sha256':plan['plan_sha256'],
            'parent_policy_id':plan['source_request']['parent_policy_id'],
            'source_pre_primary_record_sha256':pre['primary_record_sha256'],
            'post_primary_record_sha256':artifact['primary_record_sha256'],
            'environment_result_package_sha256':verifier['environment_result_package_sha256'],
            'verified_benefit_state_count':benefits,
            'verified_benefit_state_results':benefit_states,
            'comparison_scope':'SELECTED_REPAIR_VS_PARENT_CONTINUATION_NOT_A3_VS_A2',
            'strategy_materialization_pending':True,
            'training_execution_authorized':False,
            'training_execution_count':0,
            'human_scientific_decision_required':False,
        }
        training_handoff['handoff_sha256'] = sha(canon(training_handoff))
        put_json(postdir / 'CURRENT_VERIFIED_TRAINING_HANDOFF_V1.json', training_handoff)
        result['training_handoff_sha256'] = training_handoff['handoff_sha256']
        result['status'] = 'CAUSAL_ROUND_POST_TRAIN_SELECTED_NATIVE_TRAINING_BINDING_PENDING'
    elif benefits:
        result['status'] = 'PLANNER_NO_TRAIN_WITH_BENEFIT_NATIVE_DISPOSITION_NOT_BOUND'
    else:
        no = freeze_no_training_update(
            round_id=plan['round_id'],
            parent_policy_id=plan['source_request']['parent_policy_id'],
            post_plan_sha256=artifact['primary_record_sha256'],
            verifier_result_sha256=verifier['environment_result_package_sha256'],
            verified_benefit_count=0,
            verified_harm_count=counts['HARM'],
            verified_neutral_count=counts['NEUTRAL'],
            verified_uncertain_count=counts['UNCERTAIN'],
            scientifically_valid_round=True,
        ).to_dict()
        put_json(postdir / 'NO_TRAINING_UPDATE_V1.json', no)
        result['no_training_update_sha256'] = no['disposition_sha256']
        result['status'] = 'CAUSAL_ROUND_POST_NO_TRAIN_RECORDED_RESIDENT_HANDOFF_PENDING'
    put_json(postdir / 'POST_TERMINAL.json', result)
    return dict(result, provider_calls=provider_calls)

def execute_post(run_root:Path,plan:dict,verifier:dict)->dict:
    from pchsi.cognitive_runtime import request_renderer,orchestrator
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.round_control.no_training_update import freeze_no_training_update
    from structured_output_schema_compatibility import normalize_const_types
    import jsonschema
    if verifier.get('environment_result_package_sha256')!=sha(canon({k:v for k,v in verifier.items() if k!='environment_result_package_sha256'})):
        raise ValueError('POST_VERIFIER_CONTENT_HASH_MISMATCH')
    if verifier.get('plan_sha256')!=plan['plan_sha256']:raise ValueError('POST_VERIFIER_PLAN_MISMATCH')
    if verifier['scientifically_complete_pair_count']==0:
        return {'status':'PROTOCOL_OR_INFRA_INVALID_NO_SCIENTIFIC_NO_TRAIN','provider_calls':0,'round_closed':False}
    postdir=run_root/'post';postdir.mkdir(exist_ok=True)
    input_root=_resolve_scientific_input_root(run_root,plan)
    inp=input_root/'pre_root'
    z=read_json(inp/'PCHSI_V1232Z_TERMINAL_V1.json')
    pre=read_json(inp/'strong_pre_runtime'/z['accepted_pre_logical_call_id']/'validated_artifact.json')
    if pre['primary_record_sha256']!=domain_hash('STRONG_RESEARCHER_PRE_PRIMARY_V2',pre,excluded_field='primary_record_sha256'):
        raise ValueError('POST_PRE_HASH_MISMATCH')
    if pre['primary_record_sha256']!=plan['handoff']['source_pre_primary_record_sha256']:raise ValueError('POST_PRE_HANDOFF_MISMATCH')
    memory=read_json(inp/'RESEARCHER_MEMORY_VIEW_V1.json')
    scope=read_json(input_root/'native_execution_gate/HYPOTHESIS_SCOPE_NOTICE_V1.json')
    counts=verifier['stable_effect_counts'];benefits=counts['BENEFIT']
    projection={
      'round_id':plan['round_id'],'environment_result_package_sha256':verifier['environment_result_package_sha256'],
      'environment_result_package':verifier,'primary_pre_record_sha256':pre['primary_record_sha256'],
      'primary_pre_record':pre,'memory_pack_sha256':memory['view_sha256'],'researcher_memory_view':memory,
      'verifier_state_results':verifier['state_results'],'verifier_pair_results':verifier['pair_results'],
      'protocol_audit':{'comparison_scope_notice':scope,'selected_denominator':len(plan['states']),
        'missingness_preserved':True,'post_hypothesis_scope':'A3_VERSUS_A2_NOT_TESTED_BY_PARENT_VERSUS_REPAIR'},
      'machine_output_contract':{'researcher_training_recommendation':'TRAIN_OR_NO_TRAIN',
        'no_benefit_requires_no_train':benefits==0,'promotion_is_hold_until_independent_evaluation':True,
        'numerator_is_verified_benefit_state_count':benefits,'denominator_is_all_selected_states':len(plan['states']),
        'hypothesis_status':'UNRESOLVED_FOR_ORIGINAL_A3_VERSUS_A2_CLAIM',
        'invalid_pairs_are_not_policy_failures':True,'human_scientific_decision_required':False}}
    # Adopt a complete, hash-bound manifest already captured with the accepted PRE.
    manifests=list((inp/'schema_compatibility_repair').glob('*/REPAIRED_RUNTIME_MANIFEST_V1.json'))
    if len(manifests)!=1:raise ValueError('POST_SOURCE_RUNTIME_MANIFEST_NOT_UNIQUE')
    manifest=read_json(manifests[0])
    if manifest['runtime_manifest_sha256']!=domain_hash('UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1',manifest,excluded_field='runtime_manifest_sha256'):
        raise ValueError('POST_SOURCE_RUNTIME_MANIFEST_HASH_MISMATCH')
    spec=copy.deepcopy(next(s for s in manifest['stage_rows'] if s['stage_id']=='R-POST-PRIMARY-V1'))
    prompt=(ROOT/'assets/RESEARCHER_POST_PRIMARY_V1.txt').read_bytes()
    if sha(prompt)!=spec['prompt_sha256']:raise ValueError('ORIGINAL_POST_PROMPT_HASH_MISMATCH')
    schema_path=ROOT/'native_repo'/spec['output_schema_relative_path'];raw=schema_path.read_bytes()
    if sha(raw)!=spec['output_schema_sha256']:raise ValueError('ORIGINAL_POST_SCHEMA_HASH_MISMATCH')
    schema,_=normalize_const_types(json.loads(raw));props=schema['properties']
    for key,val in {'round_id':plan['round_id'],'primary_pre_record_sha256':pre['primary_record_sha256'],
      'environment_result_package_sha256':verifier['environment_result_package_sha256'],
      'numerator':benefits,'denominator':len(plan['states']),'researcher_promotion_recommendation':'HOLD',
      'primary_record_sha256':'0'*64,'hypothesis_status':'UNRESOLVED'}.items():props[key]['enum']=[val]
    props['researcher_training_recommendation']['enum']=['TRAIN','NO_TRAIN'] if benefits else ['NO_TRAIN']
    put_json(postdir/'provider_schema.json',schema);put_json(postdir/'projection.json',projection)
    spec.update(prompt_relative_path=str(ROOT/'assets/RESEARCHER_POST_PRIMARY_V1.txt'),
        output_schema_relative_path=str(postdir/'provider_schema.json'),output_schema_sha256=sha(canon(schema)))
    manifest['stage_rows']=[spec if s['stage_id']==spec['stage_id'] else s for s in manifest['stage_rows']]
    manifest['runtime_manifest_sha256']=domain_hash('UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1',manifest,excluded_field='runtime_manifest_sha256')
    put_json(postdir/'runtime_manifest.json',manifest)
    unitraw=read_json(inp/'V1232V_PRE_SCIENTIFIC_UNIT_IDENTITY_V1.json')
    for key in ('schema_id','schema_version','identity_sha256'):unitraw.pop(key,None)
    unitraw['scientific_unit_id']=domain_hash('CURRENT_ROUND_POST_UNIT_V1',{'round_id':plan['round_id'],'verifier':verifier['environment_result_package_sha256']})
    unitraw['source_unit_manifest_sha256']=verifier['environment_result_package_sha256']
    unitraw['round_evidence_package_sha256']=verifier['environment_result_package_sha256']
    unit=build_scientific_unit_identity(**unitraw);put_json(postdir/'unit.json',unit)
    access=read_json(inp/'V1232V_PRE_TASK_ACCESS_V1.json')
    def validate_output(*,stage_id,text,raw_response_sha256,projection):
        if stage_id!='R-POST-PRIMARY-V1':raise ValueError('POST_STAGE_ONLY')
        value=json.loads(text);jsonschema.Draft202012Validator(schema).validate(value)
        return finalize_api_post_primary_v1(value,projection=projection)
    with (postdir/'POST_WRITER.lock').open('a+b') as lock, ExitStack() as stack:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stack.enter_context(patch.object(request_renderer,'load_runtime_manifest',lambda:manifest))
        stack.enter_context(patch.object(orchestrator,'load_runtime_manifest',lambda:manifest))
        stack.enter_context(patch.object(orchestrator,'validate_stage_output',validate_output))
        bundle=request_renderer.render_stage_request(stage_id='R-POST-PRIMARY-V1',projection=projection)
        logical_key={'scientific_unit_identity_sha256':unit['identity_sha256'],'stage_id':'R-POST-PRIMARY-V1',
          'condition_id':None,'round_id':plan['round_id'],'policy_version':plan['source_request']['parent_policy_id'],
          'request_body_sha256':bundle['request_body_sha256']}
        logical_id=domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1',logical_key)
        call=postdir/'calls'/logical_id;calls=0
        if not call.exists():
            orchestrator.execute_one(output_root=postdir/'calls',unit_identity=unit,stage_id='R-POST-PRIMARY-V1',
              condition_id=None,round_id=plan['round_id'],policy_version=plan['source_request']['parent_policy_id'],projection=projection,task_access=access)
            calls=1
        if not (call/'logical_call.json').is_file():
            return {'status':'POST_PARTIAL_NO_RESEND','logical_call_id':logical_id,'provider_calls':calls,'round_closed':False}
        artifact,status=_terminal(call,expected={'logical_call_id':logical_id,**logical_key},projection=projection)
        if artifact is None:
            return {'status':'POST_NOT_ACCEPTED_NO_RESEND','method_status':status,'provider_calls':calls,'round_closed':False}
        return route_accepted_post_artifact(
            run_root=run_root,
            plan=plan,
            verifier=verifier,
            artifact=artifact,
            logical_call_id=logical_id,
            provider_calls=calls,
        )
