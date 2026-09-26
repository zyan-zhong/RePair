"""Training glue validation; fixtures never claim model training readiness."""
from pathlib import Path
import hashlib
import copy
import json
import sys
import pytest

WORK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORK / 'v17'))


def test_training_entry_requires_existing_gpu_allocation(monkeypatch, tmp_path):
    from entry.training import execute_current_training
    monkeypatch.delenv('SLURM_JOB_ID', raising=False)
    with pytest.raises(ValueError, match='EXISTING_GPU_ALLOCATION_REQUIRED'):
        execute_current_training(start={}, analyzer_binding={}, h44_run_root=tmp_path,
            output_root=tmp_path / 'out', round_index=1)
    assert not (tmp_path / 'out').exists()


def test_source_registration_rejects_changed_native_bytes():
    from entry.training import load_training_sources
    from test_materializer import GENERIC, DUAL
    repo = WORK / 'v17/native_bba_full'
    with pytest.raises(ValueError, match='SOURCE_REGISTRATION_INCOMPLETE'):
        load_training_sources({'scientific_repo_root': str(repo),
            'training_source_registration': {'repo_head': 'bba400738a7a53d0402552ecc3576f736ca0eec8',
                'generic_root_relative': GENERIC.relative_to(repo).as_posix(),
                'dual_adapter': {'path': str(DUAL), 'sha256': hashlib.sha256(DUAL.read_bytes()).hexdigest()},
                'source_files': {}, 'binding_source_files': {}}})


def test_real_registered_formal_source_order_builder_and_generic_validation(tmp_path):
    from training_binding.clean_base import NativeClean
    from test_materializer import _fixture
    m, native, projection, decision = _fixture(tmp_path)
    source = WORK / 'v17/server_training_sources_04/formal_train.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == '4709c32d34b437d2884fa83d4967f4d898e4cd17d5a56ce0b9e72a250f0ad9e7'
    cleanroot = WORK / 'v17/native_bba_full/scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1'
    clean = NativeClean.load(cleanroot, {n: hashlib.sha256((cleanroot / n).read_bytes()).hexdigest()
        for n in ('clean_adapter.py', 'run_stage.py')})
    contract, rows, _ = m.build_current_contract(native=native, projection=projection, decision=decision)
    contract['clean_runtime'] = {'formal_source': {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
                               'base_binding': {'snapshot_path': str(tmp_path / 'base')}}
    formal = clean.adapter.load_clean_formal(contract, {'ordering_domain': 'SOFTWARE_TEST_CURRENT_ORDER'})
    orders = [list(x) for x in formal.build_training_orders(example_count=len(rows), seed=7, passes=2)]
    order = m._order_manifest(rows, decision['recipe'], orders, 'SOFTWARE_TEST_CURRENT_ORDER')
    native.contracts.validate_training_contract(contract, order)
    assert formal.FORMAL_OPTIMIZER_STEPS == 2
    assert len(orders) == 2


def _accepted_artifacts(tmp_path, monkeypatch, fixture_rank=2):
    """Synthetic weights, real original manifest builders/native receipts only."""
    from test_materializer import _fixture
    from entry.training import _ref
    m, native, projection, decision = _fixture(tmp_path)
    from round_training.receipts import (build_input_artifact_index, build_output_artifact_index,
        build_stage_receipt, artifact_ref_for_output)
    actual = WORK / 'v17/server_training_sources_04/formal_train.py'
    current = copy.deepcopy(projection['current'])
    if fixture_rank != 2:
        config_path = tmp_path / 'adapter/adapter_config.json'
        config = json.loads(config_path.read_bytes())
        config.update(r=fixture_rank, lora_alpha=fixture_rank * 2)
        config_path.write_bytes(m.canonical(config))
        parent_manifest_path = Path(current['parent']['adapter_artifact_manifest_path'])
        parent_manifest = json.loads(parent_manifest_path.read_bytes())
        parent_manifest['files']['adapter_config.json'] = {'sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
            'size_bytes': config_path.stat().st_size}
        parent_manifest_path.write_bytes(m.canonical(parent_manifest))
        current['parent']['adapter_artifact_manifest_sha256'] = hashlib.sha256(parent_manifest_path.read_bytes()).hexdigest()
        current['peft'].update(r=fixture_rank, lora_alpha=fixture_rank * 2)
    current['parent'].update(formal_train_path=str(actual), formal_train_sha256=hashlib.sha256(actual.read_bytes()).hexdigest())
    projection = m._seal({**projection, 'current': current}, 'projection_sha256')
    decision = m.accept_recipe_decision(decision['same_call_recipe_receipt'], projection=projection)
    materialized = m.materialize_training_binding(native=native, projection=projection, decision=decision,
        output_root=tmp_path / 'materialized')
    context = native.contracts.load_stage_context(Path(materialized['stage_binding_path']))
    auth = json.loads(Path(materialized['authorization_path']).read_bytes())
    formal = native.adapter._load_parent_module(context.training_contract)
    monkeypatch.setattr(native.adapter, '_load_records', native.dual._records_for_contract)
    native.adapter._install_parent_adapter(formal, context=context)
    out, attempt = Path(auth['authorized_output_dir']), Path(auth['stage_attempt_root'])
    adapter = out / 'adapter'
    adapter.mkdir(parents=True)
    (adapter / 'adapter_config.json').write_bytes((tmp_path / 'adapter/adapter_config.json').read_bytes())
    (adapter / 'adapter_model.safetensors').write_bytes(b'SYNTHETIC ACCEPTED-ARTIFACT FORMAT TEST; NOT MODEL WEIGHTS')
    manifest = formal.build_adapter_artifact_manifest(adapter)
    budget = context.training_contract['budget']
    run = formal.build_formal_run_manifest(seed=budget['training_seed'],
        ledger_summary={'optimizer_step_count': budget['optimizer_steps'], 'dataset_pass_count': budget['epochs'],
            'target_loss_token_count': budget['target_loss_token_budget'], 'all_losses_finite': True, 'all_grad_norms_finite': True},
        initial_trainable_sha256=current['parent']['final_trainable_parameter_sha256'],
        final_trainable_sha256='9' * 64, adapter_manifest=manifest,
        runner_freeze_root_sha256=materialized['runner_freeze_root_sha256'])
    native.common.write_json_create_once(out / 'adapter_artifact_manifest.json', manifest)
    native.common.write_json_create_once(out / 'formal_run_manifest.json', run)
    (out / 'training_step_ledger.jsonl').write_text('{"software_fixture":true}\n')
    outputs = [artifact_ref_for_output(logical_name=name, path=out / filename, retention_class='RAW_EVIDENCE')
        for name, filename in (('FORMAL_RUN_MANIFEST', 'formal_run_manifest.json'),
            ('ADAPTER_ARTIFACT_MANIFEST', 'adapter_artifact_manifest.json'), ('TRAINING_STEP_LEDGER', 'training_step_ledger.jsonl'))]
    index = build_output_artifact_index(round_id=run['round_id'], stage_id='TRAINING_EXECUTION', artifacts=outputs)
    inp = build_input_artifact_index(round_id=run['round_id'], stage_id='TRAINING_EXECUTION',
        refs=[dict(_ref(tmp_path / 'materialized/ROUND_LOCAL_TRAINING_CONTRACT_V2.json'), logical_name='TRAINING_CONTRACT')])
    terminal = build_stage_receipt(round_id=run['round_id'], stage_id='TRAINING_EXECUTION',
        stage_attempt_id=auth['execution_attempt_id'], input_artifact_index_sha256=inp['artifact_index_sha256'],
        output_artifact_index_sha256=index['artifact_index_sha256'], runner_freeze_root_sha256=materialized['runner_freeze_root_sha256'],
        authorization_sha256=auth['authorization_sha256'], started_from_receipt_sha256='1' * 64,
        previous_stage_receipt_sha256=None, terminal_status='ACCEPTED', scientific_missingness_class=None,
        model_training_executed=True, model_training_execution_status='COMPLETED', failure_summary=None)
    started = dict(terminal, terminal_status='STARTED', model_training_executed=False,
        model_training_execution_status='NOT_STARTED', output_artifact_index_sha256=None,
        started_from_receipt_sha256=None)
    started['stage_receipt_sha256'] = native.common.domain_sha256(started['schema_id'], started, sha_field='stage_receipt_sha256')
    terminal['started_from_receipt_sha256'] = started['stage_receipt_sha256']
    terminal['stage_receipt_sha256'] = native.common.domain_sha256(terminal['schema_id'], terminal, sha_field='stage_receipt_sha256')
    attempt.mkdir(parents=True)
    for name, value in (('terminal_stage_receipt.json', terminal), ('started_stage_receipt.json', started),
                       ('output_artifact_index.json', index), ('input_artifact_index.json', inp)):
        native.common.write_json_create_once(attempt / name, value)
    refs = {'stage_receipt_ref': _ref(attempt / 'terminal_stage_receipt.json'),
        'output_artifact_index_ref': _ref(attempt / 'output_artifact_index.json'),
        'training_contract_ref': _ref(tmp_path / 'materialized/ROUND_LOCAL_TRAINING_CONTRACT_V2.json'),
        'stage_binding_ref': _ref(materialized['stage_binding_path']), 'execution_authorization_ref': _ref(materialized['authorization_path'])}
    return refs, out


def test_accepted_artifact_reader_uses_native_domains_and_real_formal_manifest_builder(tmp_path, monkeypatch):
    from training_binding.accepted_output import read_accepted_output
    refs, out = _accepted_artifacts(tmp_path, monkeypatch)
    value = read_accepted_output(refs)
    assert value['adapter_path'] == str((out / 'adapter').resolve())
    assert value['run_manifest']['optimizer_step_count'] == 2
    (out / 'adapter/adapter_model.safetensors').write_bytes(b'changed')
    with pytest.raises(ValueError, match='INPUT_REF_SHA_MISMATCH'):
        read_accepted_output(refs)


def test_continuation_uses_accepted_parent_instead_of_reinitialization(tmp_path, monkeypatch):
    from entry import training
    refs, out = _accepted_artifacts(tmp_path, monkeypatch)
    accepted = training.read_accepted_output(refs)
    accepted['contract']['clean_runtime'] = {'base_binding': {'snapshot_path': '/exact/current/base', 'revision': 'revision'},
        'source_code_root_sha256': '3' * 64, 'initialization_receipt_ref': {'path': '/ancestor/initialization', 'sha256': '4' * 64}}
    monkeypatch.setattr(training, 'read_accepted_output', lambda context: accepted)
    runtime = {key: accepted[key] for key in ('adapter_path', 'adapter_bundle_sha256', 'final_trainable_parameter_sha256')}
    runtime.update(base_model_local_path='/exact/current/base', tokenizer_revision='revision')
    start = {'parent_policy_id': 'ACCEPTED_PROMOTED_POLICY', 'policy_runtime_binding_sha256': 'a' * 64}
    value = training._continuation_metadata(current_parent_context=refs, runtime=runtime, start=start)
    assert value['parent']['adapter_path'] == accepted['adapter_path']
    assert value['parent']['policy_id'] == start['parent_policy_id']
    assert value['parent']['load_semantics'] == 'PEFT_FROM_PRETRAINED_IS_TRAINABLE_TRUE'
    assert value['clean_runtime']['accepted_parent_context'] == refs
    runtime['adapter_bundle_sha256'] = 'e' * 64
    with pytest.raises(ValueError, match='CURRENT_PROMOTED_RUNTIME_ACCEPTED_PARENT_MISMATCH'):
        training._continuation_metadata(current_parent_context=refs, runtime=runtime, start=start)
