"""Synthetic current-policy fixtures; never a live evaluation or promotion."""
from dataclasses import fields
import copy
import hashlib
import json
from pathlib import Path

import pytest

from continuity_binding.api import read_ref, write_once, ContinuityError
from offoff_binding.native import Native, REQUIRED
from offoff_binding.materialize import materialize, prepare, server_command
from offoff_binding.execute import require_resumable_cell, _registered_decider, freeze_registered_promotion
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
from pchsi.evaluation.distillation_access import TaskAccessManifestV1, TaskAccessRecordV1, DistillationAccessClass, HistoricalAccessFlag
from pchsi.evaluation.select_execution_identity import select_i1_request_contract_sha256

REPO = Path(__file__).resolve().parents[2] / 'native_bba_full'
MODEL = {'base_model_repository': 'Qwen/Qwen2.5-3B-Instruct',
         'base_model_revision': 'aa8e72537993ba99e69dfaafa59ed015b17504d1'}


def fixture(tmp_path, *, lora_parent=False, clean_runtime_parent=False):
    source_refs = [{'path': str(REPO / name), 'sha256': hashlib.sha256((REPO / name).read_bytes()).hexdigest()}
                   for name in REQUIRED]
    native = Native.load(REPO, source_refs)
    def policy(name, *, lora):
        root = tmp_path / name; root.mkdir()
        members = {'adapter_config.json': b'{"r":16}', 'adapter_model.safetensors': name.encode()} if lora else {'model.safetensors': b'fixture-base'}
        file_map = {}
        for filename, raw in members.items():
            (root / filename).write_bytes(raw)
            file_map[filename] = {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        manifest = {'files': file_map}
        if lora:
            manifest['adapter_bundle_sha256'] = hashlib.sha256(name.encode()).hexdigest()
        else:
            manifest.update(repository_id=MODEL['base_model_repository'], snapshot_revision=MODEL['base_model_revision'],
                            project_adapter=None, lora_enabled=False)
        manifest_ref = write_once(tmp_path / (name + '-manifest.json'), manifest)
        result = dict(policy_id=name, kind='LORA_ADAPTER' if lora else 'BASE_MODEL',
            artifact_root=str(root), artifact_manifest=manifest_ref, **MODEL,
            artifact_sha256=manifest['adapter_bundle_sha256'] if lora else manifest_ref['sha256'])
        if lora:
            result.update(adapter_rank=16, logical_condition_id='FORMAL-' + name,
                checkpoint_instance_id='FORMAL-' + name + '-CKPT', training_seed=71,
                training_config_ref=write_once(tmp_path / (name + '-training.json'), {'fixture': True}),
                training_run_id='fixture-training-' + name)
        return result
    base = policy('base', lora=False)
    parent = policy('parent', lora=True) if lora_parent else base
    if clean_runtime_parent:
        assert not lora_parent
        parent['runtime_ref'] = write_once(tmp_path / 'clean-runtime.json',
            {'schema_id': 'CLEAN_PI0_LIVE_RUNTIME_BINDING_V2', 'policy_runtime_manifest_sha256': '4' * 64,
             'base_model_local_path': parent['artifact_root'], 'tokenizer_revision': parent['base_model_revision']})
        parent['artifact_sha256'] = '4' * 64
    candidate = policy('candidate', lora=True)
    request_fields = {f.name: 'a' * 64 for f in fields(RoundRolloutCollectionRequestV1)
                      if f.name.endswith('_sha256') and f.name != 'request_sha256'}
    request_fields['parent_policy_artifact_sha256'] = parent['artifact_sha256']
    if clean_runtime_parent:
        request_fields['policy_runtime_binding_sha256'] = parent['runtime_ref']['sha256']
    request = RoundRolloutCollectionRequestV1(round_id='fixture-round', execution_attempt_id='fixture-attempt',
        parent_policy_id=parent['policy_id'], execution_namespace='fixture-namespace', rollout_seed=71,
        **request_fields).to_dict()
    candidate.update(parent_policy_id=parent['policy_id'], parent_policy_artifact_sha256=parent['artifact_sha256'],
                     round_id=request['round_id'], execution_attempt_id=request['execution_attempt_id'], request_sha256=request['request_sha256'])
    gamefile = tmp_path / 'game.ulx'; gamefile.write_bytes(b'fixture-game')
    access = TaskAccessManifestV1(schema_id=TaskAccessManifestV1.SCHEMA_ID, schema_version=1,
        manifest_id='fixture-select', dataset_version='fixture', historical_access_audit_sha256='c' * 64, record_count=1,
        records=(TaskAccessRecordV1(manifest_index=0, task_id='fixture-task', dataset_split='train',
            task_type='pick_and_place_simple', gamefile=str(gamefile), gamefile_sha1=hashlib.sha1(gamefile.read_bytes()).hexdigest(),
            gamefile_sha256=hashlib.sha256(gamefile.read_bytes()).hexdigest(), historical_access_flags=(HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,),
            access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY, teacher_call_permitted=False,
            training_permitted=False, select_evaluation_permitted=True, confirmatory_permitted=False,
            provenance_sources=('fixture',)),))
    protocol = dict(schema_id='FIXTURE_FROZEN_SELECT_PROTOCOL', access_class='TRAIN_SELECT', memory_state='OFF', harness_state='OFF',
        protocol_frozen=True, benchmark_feedback_authorized=False, primary_statistical_unit='unique_task',
        task_access_ref=write_once(tmp_path / 'access.json', access.to_dict()), task_ids=['fixture-task'], replicate_seeds=[17, 31],
        promotion_rule_ref=write_once(tmp_path / 'fixture-rule.json', {'decision_rule_id': 'FIXTURE_NO_REAL_RULE'}),
        policy_request_schema_sha256=select_i1_request_contract_sha256(), raw_protocol_sha256='b' * 64,
        evaluator_commit='1' * 40, runtime_core_commit='2' * 40, design_merge_commit='3' * 40,
        episode_budget={'max_policy_attempts': 7, 'max_environment_steps': 4, 'max_consecutive_nonexecuted_attempts': 3})
    infra = dict(base_policy_ref=write_once(tmp_path / 'base-policy.json', base),
        environment_runtime_ref=write_once(tmp_path / 'environment.json', {'fixture': 'environment'}),
        gamefile_identity_ref=write_once(tmp_path / 'gamefile-identity.json', {'fixture': 'identity'}),
        server_runtime_parameters=dict(schema_id='SELECT_SERVER_RUNTIME_MANIFEST_V1', schema_version=1,
            manifest_id='fixture-server', vllm_version='0.11.0', **MODEL,
            tokenizer_identity_manifest_sha256='d' * 64, chat_template_sha256='b' * 64,
            dtype='bfloat16', tensor_parallel_size=1, generation_config_mode='vllm',
            chat_template_content_format='string', enable_lora=True, max_lora_rank=16, max_loras=1,
            max_cpu_loras=2, lora_dtype='auto', runtime_dynamic_lora_updates=False))
    args = dict(native=native, request_ref=write_once(tmp_path / 'request.json', request),
        parent_ref=write_once(tmp_path / 'parent-policy.json', parent), candidate_ref=write_once(tmp_path / 'candidate-policy.json', candidate),
        protocol_ref=write_once(tmp_path / 'protocol.json', protocol), infrastructure_ref=write_once(tmp_path / 'infra.json', infra))
    return args


@pytest.mark.parametrize('lora_parent', [False, True])
def test_native_current_policy_materialization_and_restart(tmp_path, lora_parent):
    args = fixture(tmp_path, lora_parent=lora_parent)
    ref = materialize(**args, sink=tmp_path / 'out')
    assert materialize(**args, sink=tmp_path / 'out') == ref
    binding = read_ref(ref)
    assert binding['paired_cell_count'] == 2
    context = prepare(**args)
    registry = context['server'].static_lora_registry
    assert len(registry) == (2 if lora_parent else 1)
    command = server_command(context, host='127.0.0.1', port=8127)
    assert all(item.served_model_name + '=' + item.adapter_path in command for item in registry)
    assert 'HUMAN-T2' not in ' '.join(command)
    parent = context['bundles']['parent']; candidate = context['bundles']['candidate']
    assert [(c.task_id, c.seed) for c in parent[2].cells] == [(c.task_id, c.seed) for c in candidate[2].cells]
    assert parent[1].adapter_bundle_sha256 != candidate[1].adapter_bundle_sha256


def test_weight_byte_change_fails_before_materialization(tmp_path):
    args = fixture(tmp_path, lora_parent=True)
    policy = read_ref(args['parent_ref'])
    (Path(policy['artifact_root']) / 'adapter_model.safetensors').write_bytes(b'changed')
    with pytest.raises(ContinuityError, match='FILE_SHA'):
        materialize(**args, sink=tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_clean_runtime_parent_domain_is_not_manifest_file_sha(tmp_path):
    args = fixture(tmp_path, clean_runtime_parent=True)
    context = prepare(**args)
    assert context['parent']['artifact_sha256'] != context['parent']['artifact_manifest']['sha256']
    assert context['parent']['artifact_sha256'] == context['start']['parent_policy_artifact_sha256']
    assert context['bundles']['parent'][1].adapter_bundle_sha256 is None


def test_old_candidate_attempt_cannot_be_rebound(tmp_path):
    args = fixture(tmp_path)
    candidate = read_ref(args['candidate_ref']); candidate['execution_attempt_id'] = 'old'
    args['candidate_ref'] = write_once(tmp_path / 'wrong-candidate.json', candidate)
    with pytest.raises(ContinuityError, match='CANDIDATE_LINEAGE'):
        prepare(**args)


def test_frozen_task_order_is_not_reselected(tmp_path):
    args = fixture(tmp_path)
    protocol = read_ref(args['protocol_ref']); protocol['task_ids'] = ['another-task']
    args['protocol_ref'] = write_once(tmp_path / 'wrong-protocol.json', protocol)
    with pytest.raises(ContinuityError, match='TASK_ORDER'):
        prepare(**args)


def test_registered_decision_producer_required_not_invented(tmp_path):
    args = fixture(tmp_path)
    with pytest.raises(ContinuityError, match='FROZEN_PROMOTION_DECISION_PRODUCER_REQUIRED'):
        _registered_decider(args['native'], {'decision_rule_id': 'NO_REGISTERED_PRODUCER'})


def test_only_registered_fixture_verdict_reaches_native_promotion(tmp_path):
    args = fixture(tmp_path)
    source = tmp_path / 'fixture_decider.py'
    source.write_text('def decide(*, frozen_rule, aggregate):\n    assert frozen_rule["fixture_only"] is True\n    return {"decision": "ROLLBACK", "decision_rule_id": frozen_rule["decision_rule_id"]}\n', encoding='utf8')
    ref = {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    args['native'].sources[str(source)] = ref
    rule = {'fixture_only': True, 'decision_rule_id': 'FIXTURE_REGISTERED_RULE',
            'decision_producer': {'source_ref': ref, 'entrypoint': 'decide'}}
    protocol = {'promotion_rule_ref': write_once(tmp_path / 'test-registered-rule.json', rule)}
    summary = {'round_id': 'fixture-round'}
    decision = freeze_registered_promotion(native=args['native'], protocol=protocol, aggregate=summary,
        summary_ref=write_once(tmp_path / 'test-summary.json', summary),
        parent={'policy_id': 'fixture-parent'}, candidate={'policy_id': 'fixture-candidate'})
    assert decision.decision == 'ROLLBACK' and decision.next_parent_policy_id == 'fixture-parent'
    assert decision.evidence_access_class == 'TRAIN_SELECT'
    source.write_text('raise RuntimeError("changed source")\n', encoding='utf8')
    with pytest.raises(ContinuityError, match='FILE_SHA'):
        _registered_decider(args['native'], rule)


@pytest.mark.parametrize('field', ['started_only_attempt_ids', 'terminal_without_publish_attempt_ids', 'staged_without_publish_attempt_ids'])
def test_interrupted_cell_is_not_blindly_retried(field):
    state = {key: [] for key in ('started_only_attempt_ids', 'terminal_without_publish_attempt_ids',
                                'staged_without_publish_attempt_ids', 'published_attempt_ids')}
    state['next_attempt_ordinal'] = 1; state[field] = ['fixture-a000']
    with pytest.raises(ContinuityError, match='NO_BLIND_RETRY'):
        require_resumable_cell(state)
