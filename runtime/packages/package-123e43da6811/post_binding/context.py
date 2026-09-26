"""Materialize native verified labels before the existing single POST call."""
from __future__ import annotations

import hashlib
from pathlib import Path

from exact_bindings import BindingError, canonical, digest, immutable_json, read_json, read_ref


def check_current_verifier(plan, verifier):
    # H4.4 seals canonical JSON with a trailing LF. Its byte identity is not
    # the domain-hash identity used by cognitive-runtime artifacts.
    for value, field in ((plan, 'plan_sha256'), (verifier, 'environment_result_package_sha256')):
        if value.get(field) != digest(canonical({k: v for k, v in value.items() if k != field})):
            raise BindingError('H44_CURRENT_OBJECT_HASH:' + field)
    if (verifier.get('plan_sha256') != plan['plan_sha256']
            or verifier.get('round_id') != plan['round_id']):
        raise BindingError('CURRENT_VERIFIER_PLAN_IDENTITY')
    benefits = [r for r in verifier['state_results'] if r['stable_effect'] == 'BENEFIT']
    if len(benefits) != verifier['stable_effect_counts']['BENEFIT']:
        raise BindingError('CURRENT_VERIFIER_BENEFIT_CENSUS')
    return benefits


def load_current_tokenizer(plan, *, loader=None):
    runtime = read_ref({'path': plan['runtime_path'], 'file_sha256': plan['runtime_file_sha256']})
    if runtime.get('policy_runtime_manifest_sha256') != plan['source_request']['parent_policy_artifact_sha256']:
        raise BindingError('TRAINING_TOKENIZER_CURRENT_POLICY_IDENTITY')
    path = Path(runtime['base_model_local_path'])
    if not path.is_absolute() or not path.is_dir():
        raise BindingError('CURRENT_TOKENIZER_EXACT_LOCAL_SNAPSHOT_REQUIRED')
    if loader is None:
        from transformers import AutoTokenizer
        loader = AutoTokenizer.from_pretrained
    tokenizer = loader(str(path), revision=runtime['tokenizer_revision'], local_files_only=True,
                       trust_remote_code=False)
    template = tokenizer.chat_template
    if not isinstance(template, str) or hashlib.sha256(template.encode('utf8')).hexdigest() != runtime['chat_template_sha256']:
        raise BindingError('CURRENT_TOKENIZER_CHAT_TEMPLATE_IDENTITY')
    return tokenizer


def materialize_post_context(*, request, run_root, plan, verifier, source_loader,
                             labels_loader=None, tokenizer_loader=None, receipt_loader=None):
    """Use current verifier and same-PRE evidence; no provider, effect or recipe decision."""
    benefits = check_current_verifier(plan, verifier)
    if verifier['scientifically_complete_pair_count'] == 0:
        raise BindingError('POST_REQUIRES_INDEPENDENT_COMPLETE_PAIR')
    root = Path(run_root).absolute()
    record = {'schema_id': 'CURRENT_POST_NATIVE_DATASET_CONTEXT_V1',
              'round_id': plan['round_id'], 'plan_sha256': plan['plan_sha256'],
              'verifier_sha256': verifier['environment_result_package_sha256'],
              'dataset': None, 'recipe_context': None,
              'additional_provider_call_count': 0, 'training_execution_count': 0}
    if benefits:
        from training_binding.native_labels import NativeLabels
        from training_binding.strategy_source import derive_current_verified_rows
        labels_loader = labels_loader or NativeLabels.load
        repo = Path(request['scientific_repo_root'])
        native = labels_loader(repo / 'scripts/engineering_snapshots/training_pipeline/'
            'qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2/tools',
            request['native_labels_sources'])
        if receipt_loader is None:
            from training_binding.capture import load_captured_pre_strategy_receipt
            receipt_loader = load_captured_pre_strategy_receipt
        # Capture index and all exact references are verified by the loader.
        receipt = receipt_loader(root / 'input')
        rows = derive_current_verified_rows(plan=plan, verifier=verifier,
            source_rows=source_loader(root / 'input'), pre_receipt=receipt, native_labels=native)
        tokenizer = load_current_tokenizer(plan, loader=tokenizer_loader)
        dataset = native.materialize(verified_rows=rows, tokenizer=tokenizer,
            output_root=root / 'verified_training_data',
            verifier_result_sha256=verifier['environment_result_package_sha256'],
            verified_benefit_state_sha256s=[row['source_state_sha256'] for row in benefits])
        record.update(dataset=dataset, recipe_context=dataset['recipe_context'])
    immutable_json(root / 'post' / 'CURRENT_NATIVE_DATASET_CONTEXT.json', record)
    return record
