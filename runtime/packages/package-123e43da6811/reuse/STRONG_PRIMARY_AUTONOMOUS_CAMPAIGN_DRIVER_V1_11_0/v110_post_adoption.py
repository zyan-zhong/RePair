from __future__ import annotations
import hashlib
from pathlib import Path
from collections.abc import Mapping
from safe_io import load_obj
from post_route_recovery import validate_primary_post_and_route


def _sha(name: str, value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(name + '_INVALID_SHA256')
    return value


def _sha_file(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError('REGULAR_FILE_REQUIRED:' + str(path))
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _authority(closure_root: Path, verifier_gate: Mapping[str, object]) -> dict[str, object]:
    path=Path(closure_root)/'HYDRATED_POST_INPUT_AUTHORITY_V1.json'
    if not path.is_file() or path.is_symlink():
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_MISSING')
    value=load_obj(path)
    if not isinstance(value,dict) or value.get('schema_id')!='HYDRATED_POST_INPUT_AUTHORITY_V1':
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_SCHEMA_MISMATCH')
    if value.get('round_id')!=verifier_gate.get('round_id'):
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_ROUND_MISMATCH')
    if value.get('result_package_sha256')!=verifier_gate.get('result_package_sha256'):
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_RESULT_MISMATCH')
    if value.get('primary_pre_record_sha256')!=verifier_gate.get('primary_pre_record_sha256'):
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_PRE_MISMATCH')
    _sha('V110_MEMORY_PACK',value.get('memory_pack_sha256'))
    if value.get('hash_only_scientific_input_forbidden') is not True:
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_NOT_FULLY_HYDRATED')
    if value.get('human_scientific_decision_count')!=0:
        raise ValueError('V110_HYDRATED_POST_INPUT_AUTHORITY_HUMAN_DECISION_DETECTED')
    return value


def adopt_accepted_v110_post(*, closure_root: Path, verifier_gate: Mapping[str, object]) -> dict[str, object]:
    """Adopt an already-accepted V1.10 cognitive-runtime call without another provider send.

    This is used only when V1.10 reached execute_one()/validated_artifact but failed in its
    downstream adapter before writing HYDRATED_PLANNER_POST_ACCEPTED_V1.json.
    """
    closure=Path(closure_root).resolve()
    auth=_authority(closure,verifier_gate)
    runtime=closure/'hydrated_planner_post_runtime'
    if not runtime.is_dir() or runtime.is_symlink():
        raise ValueError('V110_POST_RUNTIME_ROOT_MISSING')
    accepted=[]; partial=[]
    for call in sorted(runtime.iterdir()):
        if not call.is_dir() or call.is_symlink():
            continue
        method=call/'method_result.json'
        if not method.is_file() or method.is_symlink():
            partial.append(call)
            continue
        result=load_obj(method)
        status=result.get('status') if isinstance(result,dict) else None
        if status=='ACCEPTED':
            artifact_path=call/'validated_artifact.json'
            if not artifact_path.is_file() or artifact_path.is_symlink():
                raise ValueError('V110_ACCEPTED_POST_MISSING_VALIDATED_ARTIFACT')
            artifact=load_obj(artifact_path)
            accepted.append((call,artifact_path,artifact))
        else:
            partial.append(call)
    if len(accepted)>1:
        raise ValueError('V110_ACCEPTED_POST_CALL_AMBIGUOUS')
    if not accepted:
        if partial:
            raise ValueError('V110_POST_CALL_PARTIAL_NO_RESEND')
        raise ValueError('V110_ACCEPTED_POST_CALL_NOT_FOUND')
    if partial:
        # Any second/partial logical call makes provider state ambiguous. Do not guess which
        # call is authoritative just because another call was accepted.
        raise ValueError('V110_ACCEPTED_PLUS_PARTIAL_POST_CALL_AMBIGUOUS')
    call,artifact_path,artifact=accepted[0]
    route=validate_primary_post_and_route(post=artifact,verifier_gate=verifier_gate)
    if artifact.get('primary_pre_record_sha256')!=auth.get('primary_pre_record_sha256'):
        raise ValueError('V110_ADOPTED_POST_PRE_MISMATCH')
    return {
        'schema_id':'STRONG_PRIMARY_V1_11_ADOPTED_V110_PLANNER_POST_V1',
        'schema_version':1,
        'adopted':True,
        'round_id':route['round_id'],
        'route':route['route'],
        'verified_benefit_count':route['verified_benefit_count'],
        'stable_effect_counts':route['stable_effect_counts'],
        'result_package_sha256':str(verifier_gate['result_package_sha256']),
        'primary_pre_record_sha256':str(verifier_gate['primary_pre_record_sha256']),
        'memory_pack_sha256':str(auth['memory_pack_sha256']),
        'post_plan_sha256':_sha('POST_PLAN',artifact.get('primary_record_sha256')),
        'call_dir':str(call.resolve()),
        'validated_artifact_path':str(artifact_path.resolve()),
        'validated_artifact_file_sha256':_sha_file(artifact_path),
        'provider_resend_count':0,
        'post_effect_authority_used':False,
        'post_training_authority_used':False,
        'post_promotion_authority_used':False,
    }
