"""Read accepted native training artifacts, preserving their original identities."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .materializer import _read_ref, canonical


def read_accepted_output(refs):
    from round_training.common import require_domain_sha
    from round_training.contracts import load_stage_context
    required = ('stage_receipt_ref', 'output_artifact_index_ref', 'training_contract_ref',
                'stage_binding_ref', 'execution_authorization_ref')
    values = {key: json.loads(_read_ref(refs[key])) for key in required}
    terminal, index = values['stage_receipt_ref'], values['output_artifact_index_ref']
    for value, schema, field in ((terminal, 'ROUND_STAGE_RECEIPT_V1', 'stage_receipt_sha256'),
        (index, 'ROUND_ARTIFACT_INDEX_V1', 'artifact_index_sha256')):
        require_domain_sha(value, schema_id=schema, sha_field=field)
    if (terminal['terminal_status'] != 'ACCEPTED' or terminal['model_training_executed'] is not True
            or terminal['model_training_execution_status'] != 'COMPLETED'
            or terminal['scientific_missingness_class'] is not None
            or index['direction'] != 'OUTPUT'
            or terminal['output_artifact_index_sha256'] != index['artifact_index_sha256']):
        raise ValueError('CURRENT_PARENT_NATIVE_TRAINING_NOT_ACCEPTED')
    context = load_stage_context(Path(refs['stage_binding_ref']['path']))
    contract = context.training_contract
    # Native load_execution_authorization is a pre-execution validator: it
    # deliberately rejects an existing output directory. For an accepted output
    # audit, retain its domain/contract/path checks and require those outputs.
    auth = values['execution_authorization_ref']
    require_domain_sha(auth, schema_id='ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1', sha_field='authorization_sha256')
    expected_auth = {'authorization_status': 'APPROVED', 'round_id': contract['round_id'],
        'stage_id': context.binding['stage_id'], 'profile_id': context.binding['profile_id'],
        'stage_binding_sha256': context.binding['stage_binding_sha256'],
        'runner_freeze_root_sha256': terminal['runner_freeze_root_sha256'],
        'authorized_optimizer_steps': contract['budget']['optimizer_steps'],
        'authorized_target_loss_tokens': contract['budget']['target_loss_token_budget'],
        'diagnostic_only': contract['diagnostic_only'], 'promotion_eligible': contract['promotion_eligible'],
        'training_execution_count_before': 0}
    if any(type(auth.get(k)) is not type(v) or auth.get(k) != v for k, v in expected_auth.items()):
        raise ValueError('ACCEPTED_OUTPUT_NATIVE_AUTHORIZATION_MISMATCH')
    policy = context.binding['output_policy']
    if policy['require_direct_child'] is not True or policy['require_basename_equals_execution_attempt_id'] is not True:
        raise ValueError('ACCEPTED_OUTPUT_NATIVE_DIRECTORY_POLICY')
    for field, parent_field in (('authorized_output_dir', 'training_output_parent'), ('stage_attempt_root', 'stage_attempt_parent')):
        path = Path(auth[field])
        if (path.resolve().parent != Path(policy[parent_field]).resolve()
            or path.name != auth['execution_attempt_id'] or not path.is_dir() or path.is_symlink()):
            raise ValueError('ACCEPTED_OUTPUT_NATIVE_DIRECTORY_IDENTITY')
    if (contract != values['training_contract_ref'] or
        context.binding['training_contract_ref']['sha256'] != refs['training_contract_ref']['sha256'] or
        terminal['authorization_sha256'] != auth['authorization_sha256'] or
        terminal['stage_attempt_id'] != auth['execution_attempt_id'] or
        any(value['round_id'] != contract['round_id'] or value['stage_id'] != context.binding['stage_id']
            for value in (terminal, index))):
        raise ValueError('CURRENT_PARENT_NATIVE_STAGE_IDENTITY')
    attempt = Path(auth['stage_attempt_root'])
    for key, name in (('stage_receipt_ref', 'terminal_stage_receipt.json'),
                      ('output_artifact_index_ref', 'output_artifact_index.json')):
        if Path(refs[key]['path']).resolve() != (attempt / name).resolve():
            raise ValueError('CURRENT_PARENT_NATIVE_RECEIPT_PATH')
    input_index = json.loads((attempt / 'input_artifact_index.json').read_bytes())
    require_domain_sha(input_index, schema_id='ROUND_ARTIFACT_INDEX_V1', sha_field='artifact_index_sha256')
    if (input_index['artifact_index_sha256'] != terminal['input_artifact_index_sha256']
        or input_index['direction'] != 'INPUT' or input_index['round_id'] != contract['round_id']
        or input_index['stage_id'] != context.binding['stage_id']):
        raise ValueError('CURRENT_PARENT_NATIVE_INPUT_INDEX')
    started = json.loads((attempt / 'started_stage_receipt.json').read_bytes())
    require_domain_sha(started, schema_id='ROUND_STAGE_RECEIPT_V1', sha_field='stage_receipt_sha256')
    if (started['stage_receipt_sha256'] != terminal['started_from_receipt_sha256']
        or started['terminal_status'] != 'STARTED' or started['model_training_executed'] is not False
        or started['model_training_execution_status'] != 'NOT_STARTED'
        or any(started[key] != terminal[key] for key in ('round_id', 'stage_id', 'stage_attempt_id',
            'input_artifact_index_sha256', 'runner_freeze_root_sha256', 'authorization_sha256'))):
        raise ValueError('CURRENT_PARENT_NATIVE_STARTED_RECEIPT')
    for ref in input_index['artifacts']:
        _read_ref(ref)
    artifacts = {}
    for ref in index['artifacts']:
        if ref['logical_name'] in artifacts:
            raise ValueError('CURRENT_PARENT_DUPLICATE_OUTPUT_ARTIFACT')
        _read_ref(ref)
        artifacts[ref['logical_name']] = ref
    expected = {'FORMAL_RUN_MANIFEST': 'formal_run_manifest.json',
                'ADAPTER_ARTIFACT_MANIFEST': 'adapter_artifact_manifest.json',
                'TRAINING_STEP_LEDGER': 'training_step_ledger.jsonl'}
    out = Path(auth['authorized_output_dir'])
    for name, filename in expected.items():
        if Path(artifacts[name]['path']).resolve() != (out / filename).resolve():
            raise ValueError('CURRENT_PARENT_NATIVE_OUTPUT_PATH')
    run = json.loads(_read_ref(artifacts['FORMAL_RUN_MANIFEST']))
    manifest = json.loads(_read_ref(artifacts['ADAPTER_ARTIFACT_MANIFEST']))
    checks = {'run_status': 'FORMAL_TRAINING_COMPLETED', 'round_id': contract['round_id'],
        'training_contract_file_sha256': refs['training_contract_ref']['sha256'],
        'stage_binding_sha256': context.binding['stage_binding_sha256'],
        'runner_freeze_root_sha256': terminal['runner_freeze_root_sha256'],
        'parent_policy_id': contract['parent']['policy_id'],
        'parent_adapter_bundle_sha256': contract['parent']['adapter_bundle_sha256'],
        'initial_trainable_parameter_sha256': contract['parent']['final_trainable_parameter_sha256'],
        'adapter_bundle_sha256': manifest['adapter_bundle_sha256'],
        'optimizer_step_count': contract['budget']['optimizer_steps'],
        'dataset_pass_count': contract['budget']['epochs'],
        'target_loss_token_count': contract['budget']['target_loss_token_budget'],
        'all_losses_finite': True, 'all_grad_norms_finite': True,
        'diagnostic_only': False, 'promotion_eligible': True,
        'checkpoint_rule': 'FINAL_STEP_ONLY', 'intermediate_scientific_checkpoint_used': False,
        'early_stopping_used': False, 'within_training_evaluation_used': False,
        'resume_from_checkpoint_used': False}
    if any(type(run.get(k)) is not type(v) or run.get(k) != v for k, v in checks.items()):
        raise ValueError('CURRENT_PARENT_NATIVE_RUN_MANIFEST')
    if run['final_trainable_parameter_sha256'] == run['initial_trainable_parameter_sha256']:
        raise ValueError('CURRENT_PARENT_TRAINABLE_STATE_UNCHANGED')
    bundle = {'required_files': manifest['required_files'], 'files': manifest['files']}
    if hashlib.sha256(canonical(bundle)).hexdigest() != manifest['adapter_bundle_sha256']:
        raise ValueError('CURRENT_PARENT_ADAPTER_BUNDLE_HASH')
    adapter = out / 'adapter'
    for name, spec in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('CURRENT_PARENT_ADAPTER_MEMBER_PATH')
        raw = _read_ref({'path': str(adapter / relative), 'sha256': spec['sha256']})
        if len(raw) != spec['size_bytes']:
            raise ValueError('CURRENT_PARENT_ADAPTER_MEMBER_SIZE')
    return {'contract': contract, 'context': context, 'authorization': auth,
        'terminal': terminal, 'output_index': index, 'run_manifest': run,
        'formal_run_manifest_ref': artifacts['FORMAL_RUN_MANIFEST'],
        'adapter_artifact_manifest_ref': artifacts['ADAPTER_ARTIFACT_MANIFEST'],
        'adapter_path': str(adapter.resolve()), 'adapter_bundle_sha256': manifest['adapter_bundle_sha256'],
        'final_trainable_parameter_sha256': run['final_trainable_parameter_sha256']}
