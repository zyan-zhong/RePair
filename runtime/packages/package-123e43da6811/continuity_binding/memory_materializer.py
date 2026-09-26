"""Automatic native Memory registration and immutable snapshot publication.

The additional member refs are emitted by the current governed-record producer.
This adapter selects them solely by the native closure's exact record identity;
it neither invents record content nor changes Memory admission decisions.
"""
from pathlib import Path

from pchsi.memory.round_maintenance import MemoryRecordBindingV1, MemoryRoundStateV1
from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
from pchsi.memory.dev_descriptive_snapshot_v2 import (
    build_calibrated_snapshot_v2, publish_calibrated_snapshot_v2, audit_calibrated_snapshot_v2,
)
from pchsi.memory.procedural_builder import ProceduralFailureMemoryRecordV1

from .api import (ContinuityError, _equal, native_request, native_memory_closure,
                  regular_path, read_ref, read_bytes_ref, write_once)


def load_current_snapshot(*, start, runtime_ref):
    request = native_request(start)
    _equal(runtime_ref.get('sha256'), request.round_memory_runtime_authority_sha256, 'CURRENT_MEMORY_RUNTIME_REF_MISMATCH')
    runtime = read_ref(runtime_ref)
    _equal(runtime.get('schema_id'), 'FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1', 'CURRENT_MEMORY_RUNTIME_SCHEMA_MISMATCH')
    _equal(runtime.get('active_snapshot_sha256'), request.round_start_memory_snapshot_sha256, 'CURRENT_MEMORY_SNAPSHOT_MISMATCH')
    _equal(runtime.get('token_budget_contract_sha256'), request.token_budget_contract_sha256, 'CURRENT_MEMORY_TOKEN_CONTRACT_MISMATCH')
    loaded = load_calibrated_dev_snapshot_v2(snapshot_directory=regular_path(runtime['active_snapshot_directory']),
        expected_snapshot_sha256=request.round_start_memory_snapshot_sha256,
        token_budget_contract_path=regular_path(runtime['token_budget_contract_path']),
        expected_token_budget_contract_sha256=request.token_budget_contract_sha256)
    return runtime, loaded


def register_initial_memory_state(*, start, runtime_ref, sink):
    """Cold-start registration from the request's actual frozen native snapshot."""
    _, loaded = load_current_snapshot(start=start, runtime_ref=runtime_ref)
    state = MemoryRoundStateV1(round_id=start['round_id'],
        policy_identity_sha256=start['parent_policy_artifact_sha256'],
        active_snapshot_sha256=loaded.snapshot.snapshot_sha256,
        active_record_bindings=tuple(MemoryRecordBindingV1(
            memory_lineage_id=member.record.memory_lineage_id,
            record_version=member.record.record_version,
            canonical_record_sha256=member.record.canonical_record_sha256)
            for member in loaded.members))
    return write_once(Path(sink)/'MEMORY_ROUND_STATE_V1.json', state.to_dict())


def _key(binding):
    return (binding.memory_lineage_id, binding.record_version, binding.canonical_record_sha256)


def materialize_next_memory_runtime(*, start, state_ref, event_refs, current_runtime_ref,
                                    additional_member_refs, sink):
    """Publish the exact native closure result, retaining identical snapshots.

    additional_member_refs is a list of machine-registered {record,retrieval_key,
    fm1,fm2} exact refs. It is empty for a closure with no new admitted records.
    """
    state, closure = native_memory_closure(start=start, state_ref=state_ref, event_refs=event_refs)
    runtime, loaded = load_current_snapshot(start=start, runtime_ref=current_runtime_ref)
    current = {_key(member.record): member for member in loaded.members}
    _equal(set(current), {_key(b) for b in state.active_record_bindings}, 'CURRENT_STATE_SNAPSHOT_RECORD_MISMATCH')
    required = {_key(b) for b in closure.next_active_record_bindings}
    if not isinstance(additional_member_refs, list):
        raise ContinuityError('CURRENT_GOVERNED_MEMBER_REFERENCE_LIST_REQUIRED')
    supplied = {}
    for refs in additional_member_refs:
        if not isinstance(refs, dict) or set(refs) != {'record','retrieval_key','fm1','fm2'}:
            raise ContinuityError('CURRENT_GOVERNED_MEMBER_REFERENCE_FIELDS_MISMATCH')
        raw = tuple(read_bytes_ref(refs[name]) for name in ('record','retrieval_key','fm1','fm2'))
        record = ProceduralFailureMemoryRecordV1.from_json(raw[0])
        key = _key(record)
        if key in supplied or key not in required or key in current:
            raise ContinuityError('GOVERNED_MEMBER_NOT_EXACT_NEW_CLOSURE_RECORD')
        supplied[key] = raw
    if required - set(current) != set(supplied):
        raise ContinuityError('MEMORY_NEXT_RECORD_ARTIFACTS_NOT_PRODUCED:' + ','.join(
            key[2] for key in sorted(required - set(current) - set(supplied))))
    sink = Path(sink)
    closure_ref = write_once(sink/'MEMORY_ROUND_CLOSURE_V1.json', closure.to_dict())
    if required == set(current):
        return {'runtime': current_runtime_ref, 'memory_closure': closure_ref,
                'snapshot_retained': True, 'snapshot_sha256': loaded.snapshot.snapshot_sha256}
    artifacts = []
    for key in sorted(required):
        if key in supplied:
            artifacts.append(supplied[key])
        else:
            member = current[key]
            # These exact paths and hashes were just validated by the native
            # snapshot loader; no filesystem search or reclassification occurs.
            artifacts.append(tuple((member.member_directory/name).read_bytes()
                for name in ('governed_record.json','retrieval_key.json','fm1.json','fm2.json')))
    registration = write_once(sink/'MEMORY_ROUND_MATERIALIZATION_INPUTS_V1.json', {
        'schema_id':'MEMORY_ROUND_MATERIALIZATION_INPUTS_V1',
        'request_sha256':start['request_sha256'], 'memory_closure_ref':closure_ref,
        'current_runtime_ref':current_runtime_ref, 'additional_member_refs':additional_member_refs,
        'scientific_decision_authority':'NATIVE_MEMORY_ROUND_CLOSURE_ONLY',
    })
    snapshot, files = build_calibrated_snapshot_v2(
        package_a_sealed_head=loaded.snapshot.package_a_sealed_head,
        historical_package_a_snapshot_sha256=loaded.snapshot.historical_package_a_snapshot_sha256,
        token_budget_contract=loaded.token_budget_contract,
        source_materialization_manifest_sha256=registration['sha256'], member_artifacts=tuple(artifacts))
    output = regular_path((sink/'snapshots').absolute())
    output.mkdir(parents=True, exist_ok=True)
    final = output/snapshot.snapshot_sha256
    if final.exists():
        _equal(audit_calibrated_snapshot_v2(snapshot_directory=final,
            expected_snapshot_sha256=snapshot.snapshot_sha256), snapshot, 'EXISTING_NEXT_MEMORY_SNAPSHOT_MISMATCH')
    else:
        final = publish_calibrated_snapshot_v2(output_root=output, snapshot=snapshot, member_files=files)
    # Runtime identity is an unhashed native identity document; raw file SHA is
    # the request's authority. Other registered source/token refs stay intact.
    next_runtime = dict(runtime, active_snapshot_directory=str(final), active_snapshot_sha256=snapshot.snapshot_sha256)
    runtime_ref = write_once(sink/'FINAL_RUNTIME_IDENTITY_V1.json', next_runtime)
    return {'runtime':runtime_ref, 'memory_closure':closure_ref, 'snapshot_retained':False,
            'snapshot_sha256':snapshot.snapshot_sha256, 'materialization_inputs':registration}
