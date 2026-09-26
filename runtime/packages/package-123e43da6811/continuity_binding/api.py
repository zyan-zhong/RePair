"""Current-request tail adapters. These do not attest Analyzer or F0/F1 execution.

The owner composes these validators with the registered upstream scientific
validator and conditional trainer/OFF-OFF validator. Exact refs are supplied by
the machine-produced stage index; filesystem discovery and arbitrary callbacks
are deliberately absent. A successful tail check alone is not a whole round.
"""
from __future__ import annotations

from dataclasses import fields
import hashlib
import json
import os
from pathlib import Path
import tempfile

from pchsi.reference_loop.canonical import domain_hash, strict_json_loads
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
from pchsi.memory.round_maintenance import (
    MemoryRoundStateV1, MemoryShadowEventV1, close_memory_round_v1,
)
from .no_training_update import freeze_no_training_update


class ContinuityError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def regular_path(value):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ContinuityError('EXACT_ABSOLUTE_PATH_REQUIRED')
    for node in (path, *path.parents):
        if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
            raise ContinuityError('PATH_ALIAS_FORBIDDEN')
    return path


def read_bytes_ref(ref):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ContinuityError('EXACT_FILE_REF_REQUIRED')
    path = regular_path(ref['path'])
    if not path.is_file():
        raise ContinuityError('EXACT_FILE_MISSING:' + str(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise ContinuityError('EXACT_FILE_SHA_MISMATCH:' + str(path))
    return raw


def read_ref(ref):
    value = strict_json_loads(read_bytes_ref(ref))
    if not isinstance(value, dict):
        raise ContinuityError('EXACT_OBJECT_REQUIRED')
    return value


def write_once(path, value):
    path = regular_path(Path(path).absolute())
    raw = canonical(value) + b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        try:
            os.link(temp, path)
        except FileExistsError:
            regular_path(path)
            if path.read_bytes() != raw:
                raise ContinuityError('IMMUTABLE_RECEIPT_CONFLICT:' + str(path))
    finally:
        temp.unlink(missing_ok=True)
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def native_request(start):
    request = RoundRolloutCollectionRequestV1(**{f.name: start[f.name]
        for f in fields(RoundRolloutCollectionRequestV1)})
    if request.to_dict() != start:
        raise ContinuityError('CURRENT_REQUEST_NATIVE_SERIALIZATION_MISMATCH')
    return request


def _equal(observed, expected, name):
    if type(observed) is not type(expected) or observed != expected:
        raise ContinuityError(name)


def _plain_hash(value, field, label):
    # H4.4 io_utils.canonical includes its final LF, unlike domain_hash.
    observed = hashlib.sha256(canonical({k: v for k, v in value.items() if k != field}) + b'\n').hexdigest()
    _equal(value.get(field), observed, label + '_CONTENT_SHA_MISMATCH')


def validate_current_post(*, start, evidence_refs):
    """Revalidate native POST and its exact request/verifier linkage.

    The upstream verifier must separately replay branch evidence through the
    registered H4.4 verify_plan. Hashes/counts here do not replace that replay.
    """
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    from pchsi.cognitive_runtime.identity import build_logical_call_record
    request = native_request(start)
    plan = read_ref(evidence_refs['execution_plan'])
    _plain_hash(plan, 'plan_sha256', 'EXECUTION_PLAN')
    _equal(plan.get('source_request'), start, 'CURRENT_REQUEST_PLAN_MISMATCH')
    _equal(plan.get('round_id'), request.round_id, 'CURRENT_REQUEST_ROUND_MISMATCH')
    verifier = read_ref(evidence_refs['verifier'])
    _equal(verifier.get('schema_id'), 'CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1', 'VERIFIER_SCHEMA_MISMATCH')
    _plain_hash(verifier, 'environment_result_package_sha256', 'VERIFIER')
    _equal(verifier.get('plan_sha256'), plan['plan_sha256'], 'CURRENT_REQUEST_VERIFIER_PLAN_MISMATCH')
    _equal(verifier.get('round_id'), request.round_id, 'CURRENT_REQUEST_VERIFIER_ROUND_MISMATCH')
    complete = verifier.get('scientifically_complete_pair_count')
    if type(complete) is not int or complete <= 0:
        raise ContinuityError('INVALID_ATTEMPT_CANNOT_CLOSE_SCIENTIFIC_ROUND')
    counts = verifier.get('stable_effect_counts')
    if not isinstance(counts, dict) or set(counts) != {'BENEFIT','HARM','NEUTRAL','UNCERTAIN'}:
        raise ContinuityError('NATIVE_VERIFIER_EFFECT_COUNTS_REQUIRED')
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise ContinuityError('NATIVE_VERIFIER_EFFECT_COUNTS_INVALID')
    _equal(sum(counts.values()), verifier.get('selected_state_count'), 'VERIFIER_SELECTED_DENOMINATOR_MISMATCH')
    projection = read_ref(evidence_refs['post_projection'])
    artifact = read_ref(evidence_refs['post_artifact'])
    logical = read_ref(evidence_refs['post_logical_call'])
    _equal(logical.get('terminal_method_status'), 'ACCEPTED', 'POST_NOT_ACCEPTED')
    expected_logical = build_logical_call_record(**{k: v for k, v in logical.items()
        if k not in {'schema_id','schema_version','logical_call_sha256'}})
    _equal(logical, expected_logical, 'POST_NATIVE_LOGICAL_CALL_SHA_MISMATCH')
    for key, expected in {'round_id': request.round_id, 'policy_version': request.parent_policy_id,
                          'stage_id': 'R-POST-PRIMARY-V1', 'condition_id': None}.items():
        _equal(logical.get(key), expected, 'POST_LOGICAL_IDENTITY_MISMATCH:' + key)
    identity = {key: logical[key] for key in ('scientific_unit_identity_sha256','stage_id',
                'condition_id','round_id','policy_version','request_body_sha256')}
    _equal(logical.get('logical_call_id'), domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1', identity), 'POST_LOGICAL_ID_SHA_MISMATCH')
    _equal(projection.get('round_id'), request.round_id, 'POST_PROJECTION_ROUND_MISMATCH')
    _equal(projection.get('environment_result_package'), verifier, 'POST_PROJECTION_VERIFIER_MISMATCH')
    _equal(projection.get('environment_result_package_sha256'), verifier['environment_result_package_sha256'], 'POST_PROJECTION_VERIFIER_SHA_MISMATCH')
    _equal(projection.get('primary_pre_record_sha256'), plan['handoff']['source_pre_primary_record_sha256'], 'POST_PRE_HANDOFF_MISMATCH')
    _equal(artifact.get('primary_record_sha256'), domain_hash('API_RESEARCHER_POST_PRIMARY_V1', artifact,
        excluded_field='primary_record_sha256'), 'POST_ARTIFACT_SHA_MISMATCH')
    _equal(finalize_api_post_primary_v1(artifact, projection=projection), artifact, 'POST_NATIVE_FINALIZER_DRIFT')
    call_path = regular_path(evidence_refs['post_logical_call']['path'])
    artifact_path = regular_path(evidence_refs['post_artifact']['path'])
    if (call_path.name != 'logical_call.json' or artifact_path.name != 'validated_artifact.json'
            or call_path.parent != artifact_path.parent
            or call_path.parent.name != logical['logical_call_id']):
        raise ContinuityError('POST_CALL_ARTIFACT_LOCATION_MISMATCH')
    _equal(artifact.get('numerator'), counts['BENEFIT'], 'POST_NUMERATOR_MISMATCH')
    _equal(artifact.get('denominator'), verifier['selected_state_count'], 'POST_DENOMINATOR_MISMATCH')
    recommendation = artifact.get('researcher_training_recommendation')
    if recommendation not in {'TRAIN', 'NO_TRAIN'} or (not counts['BENEFIT'] and recommendation != 'NO_TRAIN'):
        raise ContinuityError('POST_NATIVE_ROUTE_INVALID')
    return artifact, verifier


def expected_no_training_update(*, start, evidence_refs):
    artifact, verifier = validate_current_post(start=start, evidence_refs=evidence_refs)
    if artifact['researcher_training_recommendation'] != 'NO_TRAIN':
        raise ContinuityError('POST_DID_NOT_SELECT_NO_TRAIN')
    counts = verifier['stable_effect_counts']
    extra = {} if counts['BENEFIT'] == 0 else {
        'reason': 'PLANNER_SELECTED_NO_TRAIN',
        'planner_no_train_primary_record_sha256': artifact['primary_record_sha256'],
    }
    return freeze_no_training_update(round_id=start['round_id'], parent_policy_id=start['parent_policy_id'],
        post_plan_sha256=artifact['primary_record_sha256'],
        verifier_result_sha256=verifier['environment_result_package_sha256'],
        **{'verified_' + key.lower() + '_count': value for key, value in counts.items()},
        scientifically_valid_round=True, **extra)


def materialize_no_training_update(*, start, evidence_refs, sink):
    value = expected_no_training_update(start=start, evidence_refs=evidence_refs)
    return write_once(Path(sink)/'NO_TRAINING_UPDATE_V1.json', value.to_dict())


def native_memory_closure(*, start, state_ref, event_refs):
    request = native_request(start)
    state = MemoryRoundStateV1.from_dict(read_ref(state_ref))
    _equal(state.round_id, request.round_id, 'MEMORY_CURRENT_ROUND_MISMATCH')
    _equal(state.policy_identity_sha256, request.parent_policy_artifact_sha256, 'MEMORY_CURRENT_POLICY_MISMATCH')
    _equal(state.active_snapshot_sha256, request.round_start_memory_snapshot_sha256, 'MEMORY_CURRENT_SNAPSHOT_MISMATCH')
    if not isinstance(event_refs, list):
        raise ContinuityError('EXACT_MEMORY_SHADOW_EVENT_REFS_REQUIRED')
    events = tuple(MemoryShadowEventV1.from_dict(read_ref(ref)) for ref in event_refs)
    return state, close_memory_round_v1(state=state, shadow_events=events)


def close_memory_round_from_refs(*, start, state_ref, event_refs, sink):
    """Consume actual native state/events from the producer's exact stage index."""
    _, closure = native_memory_closure(start=start, state_ref=state_ref, event_refs=event_refs)
    return write_once(Path(sink)/'MEMORY_ROUND_CLOSURE_V1.json', closure.to_dict())


def validate_round_tail(*, start, result, repo=None):
    """Validate tail evidence. TRAIN execution validation remains the trainer's job."""
    native_request(start)
    for key in ('round_id','execution_attempt_id','request_sha256','parent_policy_id',
                'parent_policy_artifact_sha256','round_start_memory_snapshot_sha256'):
        _equal(result.get(key), start[key], 'RESULT_CURRENT_REQUEST_MISMATCH:' + key)
    refs = result['stage_evidence_refs']
    artifact, _ = validate_current_post(start=start, evidence_refs=refs)
    if artifact['researcher_training_recommendation'] == 'NO_TRAIN':
        _equal(result.get('outcome'), 'NO_TRAINING_UPDATE', 'POST_NO_TRAIN_OUTCOME_MISMATCH')
        expected = expected_no_training_update(start=start, evidence_refs=refs).to_dict()
        _equal(read_ref(refs['no_training_update']), expected, 'NATIVE_NO_TRAINING_DISPOSITION_MISMATCH')
        _equal(result.get('next_parent_policy_id'), start['parent_policy_id'], 'NO_TRAIN_PARENT_CHANGED')
        _equal(result.get('next_parent_policy_artifact_sha256'), start['parent_policy_artifact_sha256'], 'NO_TRAIN_POLICY_ARTIFACT_CHANGED')
    elif result.get('outcome') not in {'PROMOTED', 'ROLLED_BACK'}:
        raise ContinuityError('TRAIN_REQUIRES_NATIVE_PROMOTION_OR_ROLLBACK')
    _, closure = native_memory_closure(start=start, state_ref=refs['memory_state'],
                                     event_refs=refs['memory_shadow_events'])
    _equal(read_ref(refs['memory_closure']), closure.to_dict(), 'NATIVE_MEMORY_CLOSURE_MISMATCH')
    return True
