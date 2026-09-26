from dataclasses import fields
import hashlib
import json

import pytest

from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
from pchsi.cognitive_runtime.identity import build_logical_call_record
from captured_h44_io import canonical as h44_canonical, sha as h44_sha
from pchsi.reference_loop.canonical import domain_hash
from pchsi.memory.round_maintenance import (
    MemoryRecordBindingV1, MemoryRoundStateV1, MemoryShadowEventV1,
    MemorySourcePartitionV1, VerifierEffectV1,
)


def put(root, name, obj):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()
    path.write_bytes(raw)
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest()}


def request():
    sha_fields = {f.name: 'a' * 64 for f in fields(RoundRolloutCollectionRequestV1)
                  if f.name.endswith('_sha256') and f.name != 'request_sha256'}
    return RoundRolloutCollectionRequestV1(round_id='fixture-r1', execution_attempt_id='fixture-attempt',
        parent_policy_id='fixture-parent', execution_namespace='fixture-namespace', rollout_seed=4,
        **sha_fields).to_dict()


def evidence(root, *, benefits=2, recommendation='NO_TRAIN', start=None):
    start = request() if start is None else start
    plan = {'round_id': start['round_id'], 'source_request': start,
            'handoff': {'source_pre_primary_record_sha256': 'b' * 64}}
    plan['plan_sha256'] = h44_sha(h44_canonical(plan))
    counts = {'BENEFIT': benefits, 'HARM': 1, 'NEUTRAL': 0, 'UNCERTAIN': 0}
    verifier = {'schema_id': 'CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1',
                'round_id': start['round_id'], 'plan_sha256': plan['plan_sha256'],
                'scientifically_complete_pair_count': 5, 'selected_state_count': benefits + 1,
                'stable_effect_counts': counts, 'state_results': [], 'pair_results': []}
    verifier['environment_result_package_sha256'] = h44_sha(h44_canonical(verifier))
    projection = {'round_id': start['round_id'], 'primary_pre_record_sha256': 'b' * 64,
        'environment_result_package_sha256': verifier['environment_result_package_sha256'],
        'environment_result_package': verifier}
    artifact = finalize_api_post_primary_v1({
        'schema_id': 'API_RESEARCHER_POST_PRIMARY_V1', 'schema_version': 1,
        'round_id': start['round_id'], 'protocol_audit': 'Synthetic interface test only',
        'observed_outcome': 'Test fixture', 'numerator': benefits, 'denominator': benefits + 1,
        'unexpected_evidence': [], 'hypothesis_status': 'UNRESOLVED',
        'alternative_explanations': ['Synthetic'], 'researcher_training_recommendation': recommendation,
        'researcher_promotion_recommendation': 'HOLD', 'lesson': 'Synthetic',
        'next_round_implication': 'Retain parent', 'primary_record_sha256': '0' * 64,
    }, projection=projection)
    key = {'scientific_unit_identity_sha256': 'c' * 64, 'stage_id': 'R-POST-PRIMARY-V1',
           'condition_id': None, 'round_id': start['round_id'],
           'policy_version': start['parent_policy_id'], 'request_body_sha256': 'd' * 64}
    logical = build_logical_call_record(**key, logical_call_id=domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1', key),
        terminal_method_status='ACCEPTED', contributing_attempt_id='fixture-attempt',
        role='TRAINING_RESEARCHER', runtime_manifest_sha256='e'*64)
    call = 'calls/' + logical['logical_call_id']
    locations = {'post_artifact': call + '/validated_artifact.json',
                 'post_logical_call': call + '/logical_call.json'}
    return start, {name: put(root, locations.get(name, name + '.json'), obj) for name, obj in {
        'execution_plan': plan, 'verifier': verifier, 'post_projection': projection,
        'post_artifact': artifact, 'post_logical_call': logical}.items()}


def test_actual_native_post_finalizer_and_no_train_preserve_benefit(tmp_path):
    from continuity_binding.api import materialize_no_training_update, read_ref
    start, refs = evidence(tmp_path)
    result = materialize_no_training_update(start=start, evidence_refs=refs, sink=tmp_path/'out')
    value = read_ref(result)
    assert value['verified_benefit_count'] == 2
    assert value['reason'] == 'PLANNER_SELECTED_NO_TRAIN'
    assert value['training_execution_count'] == 0
    assert result == materialize_no_training_update(start=start, evidence_refs=refs, sink=tmp_path/'out')


@pytest.mark.parametrize('mutation,match', [
    ('old_attempt', 'CURRENT_REQUEST'), ('not_accepted', 'POST_NOT_ACCEPTED'),
    ('hash_only', 'SHA'), ('train', 'POST_DID_NOT_SELECT_NO_TRAIN'),
    ('no_pairs', 'INVALID_ATTEMPT'),
])
def test_no_training_rejects_wrong_authority(tmp_path, mutation, match):
    from continuity_binding.api import materialize_no_training_update, read_ref
    start, refs = evidence(tmp_path, recommendation='TRAIN' if mutation == 'train' else 'NO_TRAIN')
    if mutation == 'old_attempt':
        start = dict(start, execution_attempt_id='different', request_sha256=None)
        start = RoundRolloutCollectionRequestV1(**{f.name: start[f.name] for f in fields(RoundRolloutCollectionRequestV1)}).to_dict()
    elif mutation == 'not_accepted':
        value = read_ref(refs['post_logical_call']); value['terminal_method_status'] = 'AMBIGUOUS_POST_SEND'
        refs['post_logical_call'] = put(tmp_path, 'bad_call.json', value)
    elif mutation == 'hash_only':
        value = read_ref(refs['post_artifact']); value['lesson'] = 'Forged after acceptance'
        refs['post_artifact'] = put(tmp_path, 'bad_post.json', value)
    elif mutation == 'no_pairs':
        value = read_ref(refs['verifier']); value['scientifically_complete_pair_count'] = 0
        value.pop('environment_result_package_sha256')
        value['environment_result_package_sha256'] = h44_sha(h44_canonical(value))
        refs['verifier'] = put(tmp_path, 'bad_verifier.json', value)
    with pytest.raises(ValueError, match=match):
        materialize_no_training_update(start=start, evidence_refs=refs, sink=tmp_path/'out')
    assert not (tmp_path/'out/NO_TRAINING_UPDATE_V1.json').exists()


def test_accepted_call_and_artifact_cannot_be_mixed_across_locations(tmp_path):
    from continuity_binding.api import materialize_no_training_update, read_ref
    start, refs = evidence(tmp_path)
    refs['post_artifact'] = put(tmp_path, 'unrelated/validated_artifact.json', read_ref(refs['post_artifact']))
    with pytest.raises(ValueError, match='POST_CALL_ARTIFACT_LOCATION'):
        materialize_no_training_update(start=start, evidence_refs=refs, sink=tmp_path/'out')


def test_memory_close_calls_native_harm_neutral_and_benefit_governance(tmp_path):
    from continuity_binding.api import close_memory_round_from_refs, read_ref
    start = request()
    state = MemoryRoundStateV1(round_id=start['round_id'],
        policy_identity_sha256=start['parent_policy_artifact_sha256'],
        active_snapshot_sha256=start['round_start_memory_snapshot_sha256'], active_record_bindings=())
    event_refs = []
    for number, effect in enumerate((VerifierEffectV1.HARM, VerifierEffectV1.NEUTRAL, VerifierEffectV1.BENEFIT), 1):
        event = MemoryShadowEventV1(round_id=state.round_id,
            record_binding=MemoryRecordBindingV1(str(number)*64, 1, 'b'*64),
            source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
            analyzer_finding_sha256='c'*64, candidate_repair_sha256='d'*64,
            verifier_effect=effect, f0_evidence_sha256='e'*64, f1_evidence_sha256='f'*64,
            evidence_complete=True, evaluation_contamination_clean=True)
        event_refs.append(put(tmp_path, f'event{number}.json', event.to_dict()))
    ref = close_memory_round_from_refs(start=start, state_ref=put(tmp_path, 'state.json', state.to_dict()),
        event_refs=event_refs, sink=tmp_path/'closed')
    closure = read_ref(ref)
    assert {d['disposition'] for d in closure['dispositions']} == {'QUARANTINE','DESCRIPTIVE_ONLY','PROMOTE_NEXT_ROUND'}
    assert len(closure['next_active_record_bindings']) == 1
    assert closure['parent_state_sha256'] == state.state_sha256


def test_exact_ref_rejects_duplicates_and_mutation(tmp_path):
    from continuity_binding.api import read_ref
    ref = put(tmp_path, 'ref.json', {'a': 1})
    (tmp_path/'ref.json').write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match='SHA'):
        read_ref(ref)
    ref['sha256'] = hashlib.sha256((tmp_path/'ref.json').read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        read_ref(ref)
