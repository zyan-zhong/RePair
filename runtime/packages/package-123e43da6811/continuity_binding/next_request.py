"""Bind registered next policy/Memory bytes to native request and execution types.

No round budget is owned here. The caller supplies the state already advanced by
the campaign owner's native governor. No next request is emitted after STOP.
"""
from dataclasses import fields
from pathlib import Path

from pchsi.reference_loop.canonical import domain_hash
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1, RoundRolloutExecutionBindingV1
from pchsi.round_control.scientific_round_governance import ScientificRoundGovernanceV1, _freeze
from pchsi.memory.round_maintenance import next_round_state_v1

from .api import (ContinuityError, _equal, read_ref, read_bytes_ref, write_once,
                  native_request, native_memory_closure, regular_path, validate_round_tail)


def validate_governance(governance, result):
    if not isinstance(governance, ScientificRoundGovernanceV1):
        raise ContinuityError('NATIVE_GOVERNANCE_REQUIRED')
    # Reuse the native freezer rather than recreating stopping/counter rules.
    expected = _freeze(**{f.name: getattr(governance, f.name) for f in fields(ScientificRoundGovernanceV1)
                         if f.name not in {'stop','stop_reason','governance_sha256'}})
    _equal(governance.to_dict(), expected.to_dict(), 'NATIVE_GOVERNANCE_HASH_OR_FIELDS_MISMATCH')
    _equal(governance.last_outcome, result['outcome'], 'NATIVE_GOVERNANCE_OUTCOME_MISMATCH')
    if governance.stop:
        raise ContinuityError('GOVERNOR_STOP_NO_NEXT_REQUEST:' + str(governance.stop_reason))
    if result['outcome'] == 'PROTOCOL_INFRA_INVALID':
        raise ContinuityError('INVALID_ATTEMPT_RETRY_BELONGS_TO_OWNER_NOT_ROUND_CLOSE')


def derive_next_request(*, start, result, governance, resolved_inputs, closure_sha256):
    """Pure native construction after registered inputs have been validated."""
    prior = native_request(start)
    validate_governance(governance, result)
    if result['outcome'] not in {'PROMOTED','ROLLED_BACK','NO_TRAINING_UPDATE'}:
        raise ContinuityError('SCIENTIFIC_ROUND_OUTCOME_REQUIRED')
    if result['outcome'] != 'PROMOTED':
        _equal(result['next_parent_policy_id'], prior.parent_policy_id, 'RETAINED_POLICY_ID_MISMATCH')
        _equal(result['next_parent_policy_artifact_sha256'], prior.parent_policy_artifact_sha256, 'RETAINED_POLICY_ARTIFACT_MISMATCH')
    elif result['next_parent_policy_artifact_sha256'] == prior.parent_policy_artifact_sha256:
        raise ContinuityError('PROMOTION_WITH_UNCHANGED_ARTIFACT')
    # This is an operational identity, not a new scientific hash or budget.
    identity = domain_hash('FORMAL_NEXT_ROUND_OPERATIONAL_ID_V1', {
        'campaign_authority_sha256': governance.campaign_authority_sha256,
        'previous_request_sha256': prior.request_sha256,
        'governance_sha256': governance.governance_sha256,
        'memory_closure_sha256': closure_sha256,
        'next_parent_policy_id': result['next_parent_policy_id'],
        'next_parent_policy_artifact_sha256': result['next_parent_policy_artifact_sha256'],
        'resolved_inputs': resolved_inputs,
    })
    return RoundRolloutCollectionRequestV1(
        round_id=f'FORMAL-R{governance.valid_rounds_consumed + 1}-{identity[:16]}',
        execution_attempt_id=identity, execution_namespace=identity,
        parent_policy_id=result['next_parent_policy_id'],
        parent_policy_artifact_sha256=result['next_parent_policy_artifact_sha256'],
        policy_runtime_binding_sha256=resolved_inputs['runtime_file_sha256'],
        execution_profile_sha256=resolved_inputs['profile_file_sha256'],
        round_memory_runtime_authority_sha256=resolved_inputs['memory_file_sha256'],
        round_start_memory_snapshot_sha256=resolved_inputs['snapshot_sha256'],
        token_budget_contract_sha256=resolved_inputs['token_budget_contract_sha256'],
        train_update_manifest_sha256=resolved_inputs['train_manifest_sha256'],
        rollout_seed=prior.rollout_seed,
    )


def rebind_execution(current_binding, previous_request_sha256, next_request_sha256):
    native = RoundRolloutExecutionBindingV1(**{f.name: current_binding[f.name]
        for f in fields(RoundRolloutExecutionBindingV1)})
    _equal(native.to_dict(), current_binding, 'CURRENT_NATIVE_EXECUTION_BINDING_INVALID')
    _equal(native.request_sha256, previous_request_sha256, 'CURRENT_EXECUTION_REQUEST_MISMATCH')
    if native.scientific_execution_authorized is not True:
        raise ContinuityError('CURRENT_EXECUTION_NOT_AUTHORIZED')
    values = {f.name: getattr(native, f.name) for f in fields(RoundRolloutExecutionBindingV1)}
    values.update(request_sha256=next_request_sha256, binding_sha256=None)
    return RoundRolloutExecutionBindingV1(**values)


def resolve_next_inputs(*, start, result, inputs, closure):
    """Resolve only typed producer refs; changing a policy requires its own launch ref."""
    from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
    _equal(inputs.get('schema_id'), 'ROUND_ROLLOUT_INPUT_REFERENCES_V1', 'NEXT_INPUT_REFERENCE_SCHEMA_MISMATCH')
    runtime = read_ref(inputs['runtime'])
    profile = read_ref(inputs['profile'])
    memory = read_ref(inputs['memory'])
    read_bytes_ref(inputs['train_manifest'])
    # TRAIN_UPDATE/seed/token authority remains frozen for this campaign.
    _equal(inputs['train_manifest']['sha256'], start['train_update_manifest_sha256'], 'NEXT_TRAIN_UNIVERSE_CHANGED')
    _equal(runtime.get('policy_runtime_manifest_sha256'), result['next_parent_policy_artifact_sha256'], 'NEXT_RUNTIME_POLICY_ARTIFACT_MISMATCH')
    _equal(profile.get('schema_id'), 'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1', 'NEXT_PROFILE_SCHEMA_MISMATCH')
    _equal(profile.get('policy_version'), result['next_parent_policy_id'], 'NEXT_PROFILE_POLICY_MISMATCH')
    _equal(profile.get('served_model_name'), runtime.get('served_model_name'), 'NEXT_PROFILE_RUNTIME_MODEL_MISMATCH')
    _equal(profile.get('continuation_request_contract'), runtime.get('continuation_request_contract'), 'NEXT_PROFILE_RUNTIME_CONTRACT_MISMATCH')
    _equal(memory.get('schema_id'), 'FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1', 'NEXT_MEMORY_RUNTIME_SCHEMA_MISMATCH')
    _equal(memory.get('token_budget_contract_sha256'), start['token_budget_contract_sha256'], 'NEXT_TOKEN_CONTRACT_CHANGED')
    snapshot_directory = regular_path(memory['active_snapshot_directory'])
    token_path = regular_path(memory['token_budget_contract_path'])
    snapshot = load_calibrated_dev_snapshot_v2(snapshot_directory=snapshot_directory,
        expected_snapshot_sha256=memory['active_snapshot_sha256'], token_budget_contract_path=token_path,
        expected_token_budget_contract_sha256=memory['token_budget_contract_sha256'])
    observed = sorted((m.record.memory_lineage_id, m.record.record_version, m.record.canonical_record_sha256)
                      for m in snapshot.members)
    expected = sorted((m.memory_lineage_id, m.record_version, m.canonical_record_sha256)
                      for m in closure.next_active_record_bindings)
    _equal(observed, expected, 'NEXT_SNAPSHOT_DOES_NOT_MATERIALIZE_NATIVE_CLOSURE')
    changed = result['next_parent_policy_artifact_sha256'] != start['parent_policy_artifact_sha256']
    if changed and 'policy_launch_authority' not in inputs:
        raise ContinuityError('PROMOTED_POLICY_NATIVE_LAUNCH_AUTHORITY_REQUIRED')
    if 'policy_launch_authority' in inputs:
        authority = read_ref(inputs['policy_launch_authority'])
        for key, value in {'schema_id':'ROUND_POLICY_NATIVE_LAUNCH_AUTHORITY_V1',
            'parent_policy_id':result['next_parent_policy_id'],
            'parent_policy_artifact_sha256':result['next_parent_policy_artifact_sha256'],
            'runtime_binding_file_sha256':inputs['runtime']['sha256']}.items():
            _equal(authority.get(key), value, 'NEXT_POLICY_LAUNCH_AUTHORITY_MISMATCH:' + key)
        launch = read_ref(authority['launch_contract'])
        # Full native engine/Slurm launch validation is still performed by the
        # existing rollout materializer before dispatch. Never reuse old aliases.
        for key in ('base_model_local_path','served_model_name','policy_base_url','context_window_tokens','vllm_version'):
            if key not in runtime or key not in launch:
                raise ContinuityError('NEXT_POLICY_RUNTIME_FIELD_MISSING:' + key)
            _equal(launch[key], runtime[key], 'NEXT_POLICY_LAUNCH_RUNTIME_MISMATCH:' + key)
        engine = read_ref(inputs['engine_profile'])
        _equal(launch.get('engine_profile_sha256'), engine.get('engine_profile_sha256'), 'NEXT_POLICY_LAUNCH_ENGINE_MISMATCH')
    return {'runtime_file_sha256': inputs['runtime']['sha256'],
            'profile_file_sha256': inputs['profile']['sha256'],
            'memory_file_sha256': inputs['memory']['sha256'],
            'snapshot_sha256': memory['active_snapshot_sha256'],
            'token_budget_contract_sha256': memory['token_budget_contract_sha256'],
            'train_manifest_sha256': inputs['train_manifest']['sha256']}


def _next_components(*, start, result, governance, inputs, current_binding):
    validate_governance(governance, result)
    validate_round_tail(start=start, result=result)
    refs = result['stage_evidence_refs']
    state, closure = native_memory_closure(start=start, state_ref=refs['memory_state'],
        event_refs=refs['memory_shadow_events'])
    resolved = resolve_next_inputs(start=start, result=result, inputs=inputs, closure=closure)
    request = derive_next_request(start=start, result=result, governance=governance,
        resolved_inputs=resolved, closure_sha256=closure.closure_sha256)
    next_state = next_round_state_v1(previous_state=state, closure=closure,
        next_round_id=request.round_id, next_snapshot_sha256=request.round_start_memory_snapshot_sha256,
        next_policy_identity_sha256=request.parent_policy_artifact_sha256)
    binding = rebind_execution(current_binding, start['request_sha256'], request.request_sha256)
    creation = None
    if result['outcome'] in {'PROMOTED','ROLLED_BACK'}:
        from pchsi.round_control.promotion import freeze_promotion_decision
        from pchsi.round_control.next_round import freeze_next_round_creation
        raw = read_ref(refs['promotion'])
        promotion = freeze_promotion_decision(**{key: raw[key] for key in (
            'round_id','decision','decision_rule_id','evidence_access_class','evidence_sha256',
            'parent_policy_id','candidate_policy_id')})
        _equal(promotion.to_dict(), raw, 'NATIVE_PROMOTION_ARTIFACT_MISMATCH')
        _equal(promotion.round_id, start['round_id'], 'NATIVE_PROMOTION_ROUND_MISMATCH')
        _equal(promotion.decision, 'PROMOTE' if result['outcome'] == 'PROMOTED' else 'ROLLBACK', 'NATIVE_PROMOTION_OUTCOME_MISMATCH')
        _equal(promotion.parent_policy_id, start['parent_policy_id'], 'NATIVE_PROMOTION_PARENT_MISMATCH')
        _equal(promotion.next_parent_policy_id, request.parent_policy_id, 'NATIVE_PROMOTION_NEXT_PARENT_MISMATCH')
        creation = freeze_next_round_creation(closed_round_id=start['round_id'],
            next_round_id=request.round_id, promotion_decision=promotion)
    return request, binding, next_state, creation


def materialize_next_request(*, start, result, governance, next_inputs_ref, current_binding_ref, sink):
    inputs = read_ref(next_inputs_ref)
    request, binding, state, creation = _next_components(start=start, result=result,
        governance=governance, inputs=inputs, current_binding=read_ref(current_binding_ref))
    sink = Path(sink)
    output = {
        'request': write_once(sink/'ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json', request.to_dict()),
        'execution_binding': write_once(sink/'ROUND_ROLLOUT_EXECUTION_BINDING_V1.json', binding.to_dict()),
        'memory_state': write_once(sink/'MEMORY_ROUND_STATE_V1.json', state.to_dict()),
        'input_refs': write_once(sink/'ROUND_ROLLOUT_INPUT_REFERENCES_V1.json',
                                 {**inputs, 'request_sha256':request.request_sha256}),
        'next_request': request.to_dict(),
    }
    if creation is not None:
        output['next_creation'] = write_once(sink/'NEXT_ROUND_CREATION_V1.json', creation.to_dict())
    return output


def validate_native_next_request(*, start, result, next_request, governance, repo=None):
    """Existing entry protocol; all refs belong to the validated stage index."""
    refs = result['stage_evidence_refs']
    inputs = read_ref(refs['next_inputs'])
    expected, binding, state, creation = _next_components(start=start, result=result,
        governance=governance, inputs=inputs, current_binding=read_ref(refs['rollout_execution_binding']))
    _equal(next_request, expected.to_dict(), 'NATIVE_NEXT_REQUEST_MISMATCH')
    _equal(read_ref(refs['next_execution_binding']), binding.to_dict(), 'NATIVE_NEXT_EXECUTION_BINDING_MISMATCH')
    _equal(read_ref(refs['next_memory_state']), state.to_dict(), 'NATIVE_NEXT_MEMORY_STATE_MISMATCH')
    _equal(inputs.get('request_sha256'), expected.request_sha256, 'NEXT_INPUT_REFERENCE_REQUEST_MISMATCH')
    if creation is not None:
        _equal(read_ref(refs['next_creation']), creation.to_dict(), 'NATIVE_NEXT_CREATION_MISMATCH')
    return True
