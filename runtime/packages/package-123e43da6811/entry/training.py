"""Execute the accepted same-POST recipe through the existing native trainer.

The caller owns the registered GPU allocation. This module submits no jobs,
calls no provider, chooses no recipe, and never retries an ambiguous optimizer.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from training_binding.materializer import (NativeTraining, _read_ref, _verify_h44_seal,
    accept_recipe_decision, build_recipe_projection, canonical, digest,
    materialize_training_binding)
from training_binding.clean_base import NativeClean, PROFILE_REL, TRAINER_REL, derive_clean_parent_metadata
from training_binding.accepted_output import read_accepted_output

CLEAN_REL = Path('scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1')


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('TRAINING_REGULAR_INPUT_REQUIRED:' + str(path))
    return json.loads(path.read_bytes())


def _ref(path):
    path = Path(path).resolve()
    if path.is_symlink() or not path.is_file():
        raise ValueError('TRAINING_REF_REGULAR_FILE_REQUIRED:' + str(path))
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _write(path, value):
    path = Path(path)
    raw = canonical(value)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError('TRAINING_IMMUTABLE_OUTPUT_CONFLICT:' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def load_training_sources(analyzer_binding):
    """Validate the finite registered source map against exact Git object bytes."""
    repo = Path(analyzer_binding['scientific_repo_root']).resolve()
    reg = analyzer_binding['training_source_registration']
    required = [TRAINER_REL / 'round_training' / name for name in (
        '__init__.py', 'common.py', 'contracts.py', 'receipts.py', 'stage_runner.py',
        'adapters/frozen_formal_train_peft.py')]
    required += [CLEAN_REL / name for name in ('clean_adapter.py', 'run_stage.py')]
    required += [PROFILE_REL, Path('src/pchsi/__init__.py'), Path('src/pchsi/reference_loop/__init__.py'),
                 Path('src/pchsi/reference_loop/canonical.py')]
    if not all(path.as_posix() in reg.get('source_files', {}) for path in required):
        raise ValueError('SOURCE_REGISTRATION_INCOMPLETE')
    if (reg['generic_root_relative'] != TRAINER_REL.as_posix()
        or reg['clean_root_relative'] != CLEAN_REL.as_posix()
        or reg['profile_relative'] != PROFILE_REL.as_posix()):
        raise ValueError('TRAINING_REGISTERED_NATIVE_LAYOUT_MISMATCH')
    head = reg['repo_head']
    if (len(head) != 40 or any(c not in '0123456789abcdef' for c in head)
        or analyzer_binding['source_registration']['scientific_repo_head'] != head):
        raise ValueError('TRAINING_CURRENT_NATIVE_COMMIT_MISMATCH')
    object_root = analyzer_binding['source_registration'].get('scientific_git_object_root', str(repo))
    sources = {}
    for relative, expected in reg['source_files'].items():
        part = Path(relative)
        if part.is_absolute() or '..' in part.parts or '\\' in relative:
            raise ValueError('TRAINING_SOURCE_MEMBER_PATH')
        path = repo / part
        raw = _read_ref({'path': str(path), 'sha256': expected})
        blob = subprocess.run(['git', '-C', object_root, 'cat-file', 'blob', head + ':' + relative],
            check=True, capture_output=True).stdout
        if raw != blob:
            raise ValueError('TRAINING_SOURCE_REGISTERED_GIT_BYTES:' + relative)
        sources[str(path)] = expected
    for path, expected in reg['binding_source_files'].items():
        _read_ref({'path': path, 'sha256': expected})
    for name in ('materializer.py', 'clean_base.py', 'clean_dual_runtime.py', 'accepted_output.py'):
        path = Path(__file__).resolve().parents[1] / 'training_binding' / name
        if str(path) not in reg['binding_source_files']:
            raise ValueError('CURRENT_TRAINING_BINDING_SOURCE_MISSING:' + name)
    dual = reg['dual_adapter']
    _read_ref(dual)
    sources[str(Path(dual['path']).resolve())] = dual['sha256']
    native = NativeTraining.load(repo / TRAINER_REL, Path(dual['path']), sources)
    clean = NativeClean.load(repo / CLEAN_REL,
        {name: reg['source_files'][(CLEAN_REL / name).as_posix()] for name in ('clean_adapter.py', 'run_stage.py')})
    sys.path.insert(0, str(repo / 'src'))
    return native, clean, reg


def _accepted_post(run_root, start):
    from post_binding.runtime import adopt_recipe
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    plan = _read(run_root / 'EXECUTION_PLAN.json')
    verifier = _read(run_root / 'verifier/ENVIRONMENT_RESULT_PACKAGE.json')
    for value, field in ((plan, 'plan_sha256'), (verifier, 'environment_result_package_sha256')):
        _verify_h44_seal(value, field)
    if plan['source_request'] != start or verifier['plan_sha256'] != plan['plan_sha256']:
        raise ValueError('TRAINING_CURRENT_PLAN_START_MISMATCH')
    record = _read(run_root / 'post/CURRENT_NATIVE_DATASET_CONTEXT.json')
    if (record['round_id'] != start['round_id'] or record['plan_sha256'] != plan['plan_sha256']
        or record['verifier_sha256'] != verifier['environment_result_package_sha256']
        or record['training_execution_count'] != 0 or record['additional_provider_call_count'] != 0):
        raise ValueError('TRAINING_CURRENT_DATASET_CONTEXT_IDENTITY')
    binding_path = run_root / 'post/POST_ACCEPTED_RECIPE_BINDING.json'
    binding = _read(binding_path)
    projection = _read(run_root / 'post/projection.json')
    if (projection['round_id'] != start['round_id']
        or projection['environment_result_package_sha256'] != verifier['environment_result_package_sha256']
        or projection['primary_pre_record_sha256'] != plan['handoff']['source_pre_primary_record_sha256']
        or projection['training_materialization_context'] != record['recipe_context']):
        raise ValueError('TRAINING_CURRENT_POST_PROJECTION_IDENTITY')
    logical = json.loads(_read_ref({'path': binding['native_logical_call']['path'],
        'sha256': binding['native_logical_call']['file_sha256']}))
    expected = {name: logical[name] for name in ('logical_call_id', 'scientific_unit_identity_sha256',
        'stage_id', 'condition_id', 'round_id', 'policy_version', 'request_body_sha256', 'runtime_manifest_sha256')}
    adopted = adopt_recipe(call_dir=run_root / 'post/calls' / logical['logical_call_id'],
        output_root=run_root / 'post', expected=expected, projection=projection,
        native_finalize=finalize_api_post_primary_v1)
    if adopted['file_sha256'] != _ref(binding_path)['sha256']:
        raise ValueError('TRAINING_CURRENT_POST_RECIPE_ADOPTION_CHANGED')
    post = json.loads(_read_ref({'path': binding['native_post']['path'], 'sha256': binding['native_post']['file_sha256']}))
    if post['researcher_training_recommendation'] != 'TRAIN' or record['dataset'] is None:
        raise ValueError('POST_NO_TRAIN_FORBIDS_OPTIMIZER_EXECUTION')
    handoff = _read(run_root / 'post/CURRENT_VERIFIED_TRAINING_HANDOFF_V1.json')
    if handoff['plan_sha256'] != plan['plan_sha256']:
        raise ValueError('TRAINING_HANDOFF_CURRENT_PLAN_MISMATCH')
    runtime_ref = {'path': plan['runtime_path'], 'sha256': plan['runtime_file_sha256']}
    raw = _read_ref(runtime_ref)
    if runtime_ref['sha256'] != start['policy_runtime_binding_sha256']:
        raise ValueError('TRAINING_CURRENT_RUNTIME_FILE_MISMATCH')
    runtime = json.loads(raw)
    if runtime['policy_runtime_manifest_sha256'] != start['parent_policy_artifact_sha256']:
        raise ValueError('TRAINING_CURRENT_RUNTIME_ARTIFACT_MISMATCH')
    return plan, record, binding, post, handoff, projection, raw, runtime


def _continuation_metadata(*, current_parent_context, runtime, start):
    accepted = read_accepted_output(current_parent_context)
    old = accepted['contract']
    if 'clean_runtime' not in old:
        raise ValueError('CURRENT_ACCEPTED_PARENT_CLEAN_BASE_PROVENANCE_REQUIRED')
    for key in ('adapter_path', 'adapter_bundle_sha256', 'final_trainable_parameter_sha256'):
        if runtime.get(key) != accepted[key]:
            raise ValueError('CURRENT_PROMOTED_RUNTIME_ACCEPTED_PARENT_MISMATCH:' + key)
    clean_runtime = copy.deepcopy(old['clean_runtime'])
    clean_runtime['accepted_parent_context'] = copy.deepcopy(current_parent_context)
    parent = copy.deepcopy(old['parent'])
    parent.update(policy_id=start['parent_policy_id'], adapter_path=accepted['adapter_path'],
        adapter_bundle_sha256=accepted['adapter_bundle_sha256'],
        final_trainable_parameter_sha256=accepted['final_trainable_parameter_sha256'],
        adapter_artifact_manifest_path=accepted['adapter_artifact_manifest_ref']['path'],
        adapter_artifact_manifest_sha256=accepted['adapter_artifact_manifest_ref']['sha256'],
        load_semantics='PEFT_FROM_PRETRAINED_IS_TRAINABLE_TRUE', pilot_adapter_reuse_allowed=False)
    if (runtime['base_model_local_path'] != clean_runtime['base_binding']['snapshot_path']
        or runtime['tokenizer_revision'] != clean_runtime['base_binding']['revision']):
        raise ValueError('CURRENT_CONTINUATION_BASE_MODEL_IDENTITY')
    return {'parent': parent, 'peft': copy.deepcopy(old['peft']), 'execution': copy.deepcopy(old['execution']),
        'clean_runtime': clean_runtime, 'ordering_domain': 'CURRENT_STRONG_PRIMARY_VERIFIED_DUAL_VIEW_ORDER_V1',
        'current_parent_binding_sha256': start['policy_runtime_binding_sha256'],
        'runner_freeze_root_sha256': clean_runtime['source_code_root_sha256']}


def _context_refs(root, auth):
    return {'schema_id': 'CURRENT_ACCEPTED_TRAINING_PARENT_CONTEXT_V1',
        'stage_receipt_ref': _ref(Path(auth['stage_attempt_root']) / 'terminal_stage_receipt.json'),
        'output_artifact_index_ref': _ref(Path(auth['stage_attempt_root']) / 'output_artifact_index.json'),
        'training_contract_ref': _ref(root / 'materialized/ROUND_LOCAL_TRAINING_CONTRACT_V2.json'),
        'stage_binding_ref': _ref(root / 'materialized/ROUND_TRAINING_STAGE_BINDING_V1.json'),
        'execution_authorization_ref': _ref(root / 'materialized/ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json')}


def _publish_result(start, h44, root, context_refs):
    accepted = read_accepted_output(context_refs)
    result = {'schema_id': 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT_V1', 'round_id': start['round_id'],
        'request_sha256': start['request_sha256'], 'parent_policy_id': start['parent_policy_id'],
        'parent_policy_artifact_sha256': start['parent_policy_artifact_sha256'],
        'training_execution_count': 1, 'model_training_executed': True,
        'source_recipe_binding_ref': _ref(h44 / 'post/POST_ACCEPTED_RECIPE_BINDING.json'),
        'current_parent_context': context_refs,
        **{key: value for key, value in context_refs.items() if key.endswith('_ref')},
        **{key: accepted[key] for key in ('formal_run_manifest_ref', 'adapter_artifact_manifest_ref',
            'adapter_path', 'adapter_bundle_sha256', 'final_trainable_parameter_sha256')}}
    for key in ('formal_run_manifest_ref', 'adapter_artifact_manifest_ref'):
        result[key] = {field: result[key][field] for field in ('path', 'sha256')}
    path = root / 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT.json'
    _write(path, result)
    return dict(result, result_ref=_ref(path))


def _execute_current_phase(*, start, analyzer_binding, h44_run_root, output_root,
                           current_parent_context=None, round_index, phase):
    """Run one exact accepted recipe only within the caller's GPU allocation."""
    if not os.environ.get('SLURM_JOB_ID'):
        raise ValueError('EXISTING_GPU_ALLOCATION_REQUIRED')
    if phase not in ('smoke', 'training') or (phase == 'smoke' and current_parent_context is not None):
        raise ValueError('CURRENT_TRAINING_PHASE_INVALID')
    if type(round_index) is not int or round_index < 1:
        raise ValueError('NATIVE_GOVERNANCE_ROUND_INDEX_REQUIRED')
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported():
        raise ValueError('EXISTING_SINGLE_BF16_CUDA_ALLOCATION_REQUIRED')
    native, clean, reg = load_training_sources(analyzer_binding)
    root, h44 = Path(output_root).resolve(), Path(h44_run_root).resolve()
    plan, data, binding, post, handoff, post_projection, runtime_raw, runtime = _accepted_post(h44, start)
    result_path = root / 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT.json'
    if phase == 'training' and result_path.exists():
        result = _read(result_path)
        if (result['request_sha256'] != start['request_sha256'] or result['round_id'] != start['round_id']
            or result['source_recipe_binding_ref'] != _ref(h44 / 'post/POST_ACCEPTED_RECIPE_BINDING.json')):
            raise ValueError('EXISTING_TRAINING_RESULT_CURRENT_IDENTITY')
        read_accepted_output(result['current_parent_context'])
        return dict(result, result_ref=_ref(result_path))
    auth_path = root / 'materialized/ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json'
    if phase == 'training' and auth_path.exists():
        auth = _read(auth_path)
        terminal = Path(auth['stage_attempt_root']) / 'terminal_stage_receipt.json'
        if terminal.exists():
            # A crash after native ACCEPTED and before our result is recoverable
            # by exact receipt adoption. An unresolved/failed attempt is rejected.
            frozen = _read(root / 'materialized/CURRENT_TRAINING_INPUT_V1.json')
            prior_decision = _read(root / 'materialized/CURRENT_STRONG_POST_TRAINING_RECIPE_V1.json')
            from training_binding.materializer import _verify_seal, _check_projection
            _verify_seal(frozen, 'projection_sha256')
            _check_projection(native, frozen)
            if (frozen['accepted_post'] != post or frozen['handoff'] != handoff
                or frozen['current']['round_index'] != round_index
                or frozen['current']['current_parent_binding_sha256'] != start['policy_runtime_binding_sha256']
                or accept_recipe_decision(binding['recipe_receipt'], projection=frozen) != prior_decision):
                raise ValueError('TRAINING_RECOVERY_CURRENT_AUTHORITY_MISMATCH')
            return _publish_result(start, h44, root, _context_refs(root, auth))
    if current_parent_context is None:
        current = derive_clean_parent_metadata(source_request=start, runtime_bytes=runtime_raw,
            native_repo_root=Path(analyzer_binding['scientific_repo_root']),
            profile_file_sha256=reg['source_files'][PROFILE_REL.as_posix()])
        current['runner_freeze_root_sha256'] = digest({**native.source_sha256s, **reg['binding_source_files']})
    else:
        current = _continuation_metadata(current_parent_context=current_parent_context, runtime=runtime, start=start)
    current.update(round_index=round_index, output_parent=str(root / 'outputs'),
        attempt_parent=str(root / 'attempts'), execution_attempt_id=start['execution_attempt_id'])
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    dataset = data['dataset']
    projection = build_recipe_projection(native=native, accepted_post=post, handoff=handoff,
        dataset_ref=dataset['dataset_ref'], dataset_manifest_ref=dataset['dataset_manifest_ref'],
        manifest_domain_sha_field=dataset['manifest_domain_sha_field'], census=dataset['census'], current=current,
        validate_accepted_post=lambda value: finalize_api_post_primary_v1(value, projection=post_projection))
    decision = accept_recipe_decision(binding['recipe_receipt'], projection=projection)
    if current_parent_context is None:
        prepared = clean.prepare(native=native, projection=projection, decision=decision,
            base_binding=current['base_binding'], formal_source=current['formal_source'],
            output_root=root / 'initialization', binding_source_sha256s=reg['binding_source_files'])
        initialized = clean.execute(native=native, request_path=Path(prepared['request_path']),
                                    adopt_only=phase == 'training')
        projection, decision = initialized['projection'], initialized['decision']
        if phase == 'smoke':
            result = _initialization_result(start, h44, root)
            path = root / 'CURRENT_NATIVE_INITIALIZATION_RESULT.json'
            _write(path, result)
            return dict(result, result_ref=_ref(path))
    from training_binding.materializer import build_current_contract
    contract, _, _ = build_current_contract(native=native, projection=projection, decision=decision)
    formal = clean.adapter.load_clean_formal(contract, {'ordering_domain': current['ordering_domain']})
    materialized = materialize_training_binding(native=native, projection=projection, decision=decision,
        output_root=root / 'materialized', build_training_orders=formal.build_training_orders)
    for key, value in materialized['required_environment'].items():
        if os.environ.get(key) not in (None, '', value):
            raise ValueError('TRAINING_FIXED_ENVIRONMENT_CONFLICT:' + key)
        os.environ[key] = value
    from round_training.stage_runner import run_training_stage
    run_training_stage(binding_path=Path(materialized['stage_binding_path']),
        authorization_path=Path(materialized['authorization_path']),
        runner_freeze_root_sha256=materialized['runner_freeze_root_sha256'])
    auth = _read(materialized['authorization_path'])
    return _publish_result(start, h44, root, _context_refs(root, auth))


def _initialization_result(start, h44, root):
    return {'schema_id': 'CURRENT_NATIVE_INITIALIZATION_RESULT_V1',
        **{key: start[key] for key in ('round_id', 'request_sha256', 'parent_policy_id', 'parent_policy_artifact_sha256')},
        'training_execution_count': 0, 'optimizer_executed': False, 'initialization_executed': True,
        'source_recipe_binding_ref': _ref(h44 / 'post/POST_ACCEPTED_RECIPE_BINDING.json'),
        'initialization_request_ref': _ref(root / 'initialization/INITIALIZATION_REQUEST.json'),
        'initialization_receipt_ref': _ref(root / 'initialization/INITIALIZATION_RECEIPT.json')}


def adopt_current_initialization(*, start, analyzer_binding, h44_run_root, output_root,
                                 current_parent_context=None, round_index):
    """CPU receipt adoption; this function has no initialization execution path."""
    if current_parent_context is not None:
        raise ValueError('CONTINUATION_MUST_NOT_REQUEST_CLEAN_INITIALIZATION')
    root, h44 = Path(output_root).resolve(), Path(h44_run_root).resolve()
    native, clean, _ = load_training_sources(analyzer_binding)
    _, _, binding, post, handoff, _, _, _ = _accepted_post(h44, start)
    initialized = clean.execute(native=native, request_path=root / 'initialization/INITIALIZATION_REQUEST.json', adopt_only=True)
    projection, decision = initialized['projection'], initialized['decision']
    from training_binding.materializer import build_current_contract
    contract, _, _ = build_current_contract(native=native, projection=projection, decision=decision)
    native.adapter._verify_parent_adapter_files(contract)
    if (projection['accepted_post'] != post or projection['handoff'] != handoff
        or projection['current']['round_index'] != round_index
        or projection['current']['current_parent_binding_sha256'] != start['policy_runtime_binding_sha256']
        or decision['same_call_recipe_receipt'] != binding['recipe_receipt']):
        raise ValueError('INITIALIZATION_CURRENT_POST_RECIPE_IDENTITY_MISMATCH')
    expected = _initialization_result(start, h44, root)
    path = root / 'CURRENT_NATIVE_INITIALIZATION_RESULT.json'
    _write(path, expected)
    return dict(expected, result_ref=_ref(path))


def validate_initialization_result(result, **arguments):
    if result != adopt_current_initialization(**arguments):
        raise ValueError('INITIALIZATION_RESULT_IDENTITY_MISMATCH')
    return result


def execute_current_initialization(*, start, analyzer_binding, h44_run_root, output_root,
                                   current_parent_context=None, round_index):
    return _execute_current_phase(start=start, analyzer_binding=analyzer_binding,
        h44_run_root=h44_run_root, output_root=output_root, current_parent_context=current_parent_context,
        round_index=round_index, phase='smoke')


def execute_current_training(*, start, analyzer_binding, h44_run_root, output_root,
                             current_parent_context=None, round_index):
    return _execute_current_phase(start=start, analyzer_binding=analyzer_binding,
        h44_run_root=h44_run_root, output_root=output_root, current_parent_context=current_parent_context,
        round_index=round_index, phase='training')
