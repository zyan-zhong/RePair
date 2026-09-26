"""Existing Stage4A single-submission owner around the current Generic trainer."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'live_adapter')]
from exact_bindings import BindingError, canonical, digest, immutable_bytes, immutable_json, file_ref, read_ref, read_json


def _native_ref(path):
    ref = file_ref(path)
    return {'path': ref['path'], 'sha256': ref['file_sha256']}


def _clean_owner(registration, repo):
    from training_binding.clean_base import NativeClean
    relative = registration['clean_root_relative']
    return NativeClean.load(Path(repo) / relative,
        {name: registration['source_files'][relative + '/' + name]
         for name in ('clean_adapter.py', 'run_stage.py')})


def _publish_json(path, value):
    """Expose only a completely flushed result; preserve no-overwrite semantics."""
    path = Path(path); raw = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != raw:
            raise BindingError('TRAINING_ATOMIC_PUBLICATION_CONFLICT:' + str(path))
        return
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != raw:
                raise BindingError('TRAINING_ATOMIC_PUBLICATION_CONFLICT:' + str(path))
        if os.name == 'posix':
            directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try: os.fsync(directory)
            finally: os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_result(result, request):
    """A worker wrapper is insufficient: require the actual accepted chain."""
    from entry.training import load_training_sources
    from training_binding.accepted_output import read_accepted_output
    start = request['start']
    checks = {'schema_id': 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT_V1',
        'round_id': start['round_id'], 'request_sha256': start['request_sha256'],
        'parent_policy_id': start['parent_policy_id'],
        'parent_policy_artifact_sha256': start['parent_policy_artifact_sha256'],
        'training_execution_count': 1, 'model_training_executed': True}
    if not isinstance(result, dict) or any(type(result.get(k)) is not type(v) or result.get(k) != v
                                          for k, v in checks.items()):
        raise BindingError('TRAINING_WORKER_RESULT_INCOMPLETE_OR_DIFFERENT_CURRENT_REQUEST')
    required = ('result_ref', 'current_parent_context', 'source_recipe_binding_ref',
        'stage_receipt_ref', 'output_artifact_index_ref', 'training_contract_ref', 'stage_binding_ref',
        'execution_authorization_ref', 'formal_run_manifest_ref', 'adapter_artifact_manifest_ref',
        'adapter_path', 'adapter_bundle_sha256', 'final_trainable_parameter_sha256')
    if any(key not in result for key in required):
        raise BindingError('TRAINING_WORKER_RESULT_NATIVE_REFERENCES_REQUIRED')
    result_path = Path(request['output_root']) / 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT.json'
    if result['result_ref'] != _native_ref(result_path):
        raise BindingError('TRAINING_WORKER_RESULT_NATIVE_FILE_IDENTITY')
    stored = read_ref({'path': result['result_ref']['path'], 'file_sha256': result['result_ref']['sha256']})
    if stored != {k: v for k, v in result.items() if k != 'result_ref'}:
        raise BindingError('TRAINING_WORKER_RESULT_WRAPPER_PAYLOAD_DRIFT')
    if result['source_recipe_binding_ref'] != _native_ref(Path(request['h44_run_root']) / 'post/POST_ACCEPTED_RECIPE_BINDING.json'):
        raise BindingError('TRAINING_WORKER_RESULT_SAME_POST_IDENTITY')
    if Path(result['stage_binding_ref']['path']) != Path(request['output_root']) / 'materialized/ROUND_TRAINING_STAGE_BINDING_V1.json':
        raise BindingError('TRAINING_WORKER_RESULT_NATIVE_ROOT_IDENTITY')
    for key in ('stage_receipt_ref', 'output_artifact_index_ref', 'training_contract_ref',
                'stage_binding_ref', 'execution_authorization_ref'):
        if result['current_parent_context'].get(key) != result[key]:
            raise BindingError('TRAINING_WORKER_RESULT_PARENT_CONTEXT_IDENTITY')
    load_training_sources(request['analyzer_binding'])
    accepted = read_accepted_output(result['current_parent_context'])
    for key in ('adapter_path', 'adapter_bundle_sha256', 'final_trainable_parameter_sha256'):
        if result[key] != accepted[key]:
            raise BindingError('TRAINING_WORKER_RESULT_NATIVE_OUTPUT_IDENTITY:' + key)
    for key in ('formal_run_manifest_ref', 'adapter_artifact_manifest_ref'):
        if result[key] != {field: accepted[key][field] for field in ('path', 'sha256')}:
            raise BindingError('TRAINING_WORKER_RESULT_NATIVE_OUTPUT_REFERENCE:' + key)
    if (accepted['contract']['round_id'] != start['round_id']
        or accepted['contract']['parent']['policy_id'] != start['parent_policy_id']):
        raise BindingError('TRAINING_WORKER_RESULT_NATIVE_CONTRACT_CURRENT_IDENTITY')
    return result


def _read_result(path, request_path, request, phase='training'):
    value = read_json(path)
    schema = ('CURRENT_RESIDENT_INITIALIZATION_JOB_RESULT_V1' if phase == 'smoke'
              else 'CURRENT_RESIDENT_TRAINING_JOB_RESULT_V1')
    if (value.get('schema_id') != schema
        or value.get('request_ref') != _native_ref(request_path)):
        raise BindingError('TRAINING_WORKER_RESULT_DIFFERENT_REQUEST')
    if phase == 'smoke':
        return _validate_smoke_result(value.get('result'), request)
    return _validate_result(value.get('result'), request)


def _validate_smoke_result(result, request):
    if (not isinstance(result, dict) or result.get('schema_id') != 'CURRENT_NATIVE_INITIALIZATION_RESULT_V1'
        or type(result.get('training_execution_count')) is not int or result['training_execution_count'] != 0
        or result.get('optimizer_executed') is not False):
        raise BindingError('INITIALIZATION_RESULT_MUST_HAVE_ZERO_OPTIMIZER_EXECUTION')
    from entry.training import validate_initialization_result
    return validate_initialization_result(result, **{key: request[key] for key in (
        'start', 'analyzer_binding', 'h44_run_root', 'output_root', 'current_parent_context', 'round_index')})


def _check_stop(root, request_path, phase='training'):
    for suffix in ('JOB_STOP.json', 'WATCH_STOP.json'):
        filename = phase.upper() + '_' + suffix
        path = root / filename
        if path.exists():
            value = read_json(path)
            if value.get('request_ref') != _native_ref(request_path):
                raise BindingError('TRAINING_STOP_CURRENT_IDENTITY_MISMATCH')
            if suffix == 'WATCH_STOP.json':
                raise BindingError('CURRENT_TRAINING_MISSING_TERMINAL_NO_BLIND_RESEND')
            raise BindingError('CURRENT_TRAINING_NATIVE_STOP:' + value['error_type'] + ':' + value['message'])


def execute_current_training_job(*, start, analyzer_binding, h44_run_root, output_root,
                                 current_parent_context, round_index, deployment):
    settings = deployment['rollout_settings']
    for key in ('watch_timeout_seconds', 'poll_seconds', 'publication_grace_seconds', 'native_preflight_timeout_seconds'):
        value = settings.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise BindingError('REGISTERED_TRAINING_OPERATIONAL_LIMIT_REQUIRED:' + key)
    if type(round_index) is not int or round_index < 1:
        raise BindingError('NATIVE_GOVERNANCE_ROUND_INDEX_REQUIRED')
    root = Path(output_root).absolute(); root.mkdir(parents=True, exist_ok=True)
    registration = deployment['training_source_registration']
    if (analyzer_binding['training_source_registration'] != registration
        or analyzer_binding['scientific_repo_root'] != deployment['scientific_repo_root']):
        raise BindingError('TRAINING_JOB_CURRENT_SOURCE_REGISTRATION_MISMATCH')
    operational = read_ref({'path': registration['operational_request_ref']['path'],
                           'file_sha256': registration['operational_request_ref']['sha256']})
    native = _clean_owner(registration, deployment['scientific_repo_root'])
    request = {'schema_id': 'CURRENT_RESIDENT_TRAINING_JOB_REQUEST_V1',
        'start': start, 'analyzer_binding': analyzer_binding, 'h44_run_root': str(Path(h44_run_root).absolute()),
        'output_root': str(root / 'native'), 'current_parent_context': current_parent_context,
        'round_index': round_index, 'result_path': str(root / 'TRAINING_JOB_RESULT.json'),
        'source_identity_sha256': deployment['entry_source_sha256']}
    request_path = root / 'TRAINING_JOB_REQUEST.json'; immutable_json(request_path, request)
    result_path = Path(request['result_path'])
    if result_path.exists():
        return _read_result(result_path, request_path, request)
    if not (Path(request['output_root']) / 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT.json').is_file():
        _check_stop(root, request_path)
    python = operational['python']
    if not Path(python).is_absolute() or not Path(python).is_file():
        raise BindingError('REGISTERED_TRAINING_PYTHON_UNAVAILABLE')
    if current_parent_context is None:
        _run_phase(phase='smoke', root=root, request=request, request_path=request_path,
                   native=native, operational=operational, settings=settings)
    return _run_phase(phase='training', root=root, request=request, request_path=request_path,
                      native=native, operational=operational, settings=settings)


def _run_phase(*, phase, root, request, request_path, native, operational, settings):
    result_path = root / (phase.upper() + '_JOB_RESULT.json')
    def adopt_finished_native_result():
        if result_path.exists():
            return
        if phase == 'smoke' and (Path(request['output_root']) / 'initialization/INITIALIZATION_RECEIPT.json').is_file():
            from entry.training import adopt_current_initialization
            result = adopt_current_initialization(**{key: request[key] for key in (
                'start', 'analyzer_binding', 'h44_run_root', 'output_root', 'current_parent_context', 'round_index')})
            schema = 'CURRENT_RESIDENT_INITIALIZATION_JOB_RESULT_V1'
        elif phase == 'training' and (Path(request['output_root']) / 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT.json').is_file():
            path = Path(request['output_root']) / 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT.json'
            result = dict(read_json(path), result_ref=_native_ref(path))
            _validate_result(result, request)
            schema = 'CURRENT_RESIDENT_TRAINING_JOB_RESULT_V1'
        else:
            return
        _publish_json(result_path, {'schema_id': schema, 'request_ref': _native_ref(request_path), 'result': result})
    adopt_finished_native_result()
    if result_path.exists():
        return _read_result(result_path, request_path, request, phase)
    _check_stop(root, request_path, phase)
    python = operational['python']
    argv = [python, '-B', str(Path(__file__).resolve()), '--worker', str(request_path),
            '--request-sha256', file_ref(request_path)['file_sha256'], '--phase', phase]
    script = root / (phase + '.sbatch')
    immutable_bytes(script, ('#!/usr/bin/env bash\nexec ' + ' '.join(shlex.quote(x) for x in argv) + '\n').encode())
    # Reuse native atomic intent/receipt and exact-script adoption unchanged.
    receipt = native.runner.submit_once(root, phase, script, operational['slurm'])
    if (receipt.get('phase') != phase or not isinstance(receipt.get('job_id'), str)
        or re.fullmatch(r'[0-9]+', receipt['job_id']) is None):
        raise BindingError('TRAINING_NATIVE_SUBMISSION_RECEIPT_INVALID')
    watched = root / (phase.upper() + '_WATCH_START.json')
    if not watched.exists():
        immutable_json(watched, {'job_id': receipt['job_id'], 'started_at': time.time(),
                                  'settings': settings, 'request': _native_ref(request_path)})
    watch = read_json(watched)
    if watch['job_id'] != receipt['job_id'] or watch['settings'] != settings or watch['request'] != _native_ref(request_path):
        raise BindingError('TRAINING_WATCH_CURRENT_IDENTITY_MISMATCH')
    inactive = root / (phase.upper() + '_FIRST_INACTIVE.json')
    while not result_path.is_file():
        adopt_finished_native_result()
        if result_path.is_file():
            break
        _check_stop(root, request_path, phase)
        try:
            query = subprocess.run(['squeue', '--noheader', '--jobs', receipt['job_id'], '--format', '%i|%T'],
                capture_output=True, text=True, check=False, timeout=settings['native_preflight_timeout_seconds'])
            inactive_now = not query.stdout.strip() and (query.returncode == 0 or 'Invalid job id' in query.stderr)
            status = query.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            inactive_now = False
            status = 'STATUS_QUERY_UNAVAILABLE:' + type(exc).__name__
        now = time.time()
        print('FORMAL_' + phase.upper() + '_JOB=' + receipt['job_id'] + ' ' + status, flush=True)
        if inactive_now and not inactive.exists():
            immutable_json(inactive, {'job_id': receipt['job_id'], 'epoch': now, 'request_ref': _native_ref(request_path)})
        if inactive.exists():
            event = read_json(inactive)
            if event.get('job_id') != receipt['job_id'] or event.get('request_ref') != _native_ref(request_path):
                raise BindingError('TRAINING_INACTIVE_JOB_IDENTITY_MISMATCH')
        if (now - watch['started_at'] >= settings['watch_timeout_seconds']
                or (inactive_now and inactive.exists() and now - read_json(inactive)['epoch'] >= settings['publication_grace_seconds'])):
            # A terminal published during the status query wins over containment.
            if result_path.exists():
                return _read_result(result_path, request_path, request, phase)
            containment_rc, containment_error = None, None
            try:
                containment = subprocess.run(['scancel', receipt['job_id']], capture_output=True, text=True,
                    check=False, timeout=settings['native_preflight_timeout_seconds'])
                containment_rc = containment.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                containment_error = type(exc).__name__
            _publish_json(root / (phase.upper() + '_WATCH_STOP.json'), {'job_id': receipt['job_id'],
                'request_ref': _native_ref(request_path),
                'reason': 'NO_NATIVE_TRAINING_RESULT_WITHIN_REGISTERED_BUDGET',
                'containment_rc': containment_rc, 'containment_error': containment_error,
                'blind_resend_authorized': False, 'training_success_claimed': False})
            raise BindingError('CURRENT_TRAINING_MISSING_TERMINAL_NO_BLIND_RESEND')
        time.sleep(settings['poll_seconds'])
    return _read_result(result_path, request_path, request, phase)


def worker(request_path, expected_sha, phase='training'):
    request_path = Path(request_path).absolute()
    request = read_ref({'path': str(request_path), 'file_sha256': expected_sha})
    try:
        if (phase not in ('smoke', 'training')
            or request.get('schema_id') != 'CURRENT_RESIDENT_TRAINING_JOB_REQUEST_V1'
            or Path(request['result_path']) != request_path.parent / 'TRAINING_JOB_RESULT.json'
            or Path(request['output_root']) != request_path.parent / 'native'):
            raise BindingError('TRAINING_WORKER_REQUEST_LAYOUT_INVALID')
        from memory_binding.worker_bootstrap import bootstrap_current_and_children
        bootstrap_current_and_children(request['analyzer_binding']['scientific_repo_root'])
        from entry.training import execute_current_training, execute_current_initialization
        execute = execute_current_initialization if phase == 'smoke' else execute_current_training
        result = execute(**{key: request[key] for key in (
            'start', 'analyzer_binding', 'h44_run_root', 'output_root', 'current_parent_context', 'round_index')})
        if phase == 'smoke':
            _validate_smoke_result(result, request)
        else:
            _validate_result(result, request)
        schema = ('CURRENT_RESIDENT_INITIALIZATION_JOB_RESULT_V1' if phase == 'smoke'
                  else 'CURRENT_RESIDENT_TRAINING_JOB_RESULT_V1')
        _publish_json(request_path.parent / (phase.upper() + '_JOB_RESULT.json'), {'schema_id': schema,
                       'request_ref': _native_ref(request_path), 'result': result})
    except Exception as exc:
        _publish_json(request_path.parent / (phase.upper() + '_JOB_STOP.json'), {
            'schema_id': 'CURRENT_RESIDENT_TRAINING_JOB_STOP_V1', 'request_ref': _native_ref(request_path),
            'error_type': type(exc).__name__, 'message': str(exc), 'blind_resend_authorized': False,
            'training_success_claimed': False})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--phase', choices=('smoke', 'training'), default='training')
    args = parser.parse_args()
    worker(args.worker, args.request_sha256, args.phase)
