"""CPU scheduler/receipt recovery tests; no real scheduler or optimizer calls."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'work/v17'), str(ROOT / 'work/v17/live_adapter'),
               str(ROOT / 'work/v17/training_binding/tests')]
from entry import training_job as job
from training_binding.clean_base import NativeClean


def case(tmp_path, monkeypatch):
    cleanroot = ROOT / 'work/v17/native_bba_full/scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1'
    native = NativeClean.load(cleanroot, {name: hashlib.sha256((cleanroot / name).read_bytes()).hexdigest()
        for name in ('clean_adapter.py', 'run_stage.py')})
    monkeypatch.setattr(job, '_clean_owner', lambda registration, repo: native)
    operational = tmp_path / 'operational.json'
    job.immutable_json(operational, {'python': str(Path(sys.executable).resolve()),
        'slurm': {'partition': 'cpu-mocked-gpu-partition', 'time': '00:20:00'}})
    registration = {'operational_request_ref': job._native_ref(operational)}
    binding = {'scientific_repo_root': str(cleanroot), 'training_source_registration': registration}
    args = dict(start={'round_id': 'synthetic-round', 'request_sha256': 'a' * 64,
                      'parent_policy_id': 'synthetic-parent', 'parent_policy_artifact_sha256': 'b' * 64},
        analyzer_binding=binding, h44_run_root=tmp_path / 'h44', output_root=tmp_path / 'job',
        current_parent_context={'software_fixture': 'accepted-parent'}, round_index=1,
        deployment={'scientific_repo_root': str(cleanroot), 'training_source_registration': registration,
            'entry_source_sha256': 'c' * 64, 'rollout_settings': {'watch_timeout_seconds': 10,
                'publication_grace_seconds': 2, 'poll_seconds': 1, 'native_preflight_timeout_seconds': 1}})
    epoch = [100.0]
    monkeypatch.setattr(job.time, 'time', lambda: epoch[0])
    monkeypatch.setattr(job.time, 'sleep', lambda seconds: epoch.__setitem__(0, epoch[0] + seconds))
    calls = []
    def invoke(script, log, resources):
        calls.append((script, log, resources))
        return '12345'
    monkeypatch.setattr(native.runner, 'invoke_sbatch', invoke)
    queries = []
    def command(argv, **kwargs):
        queries.append(argv)
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(job.subprocess, 'run', command)
    return args, native, calls, queries


def test_native_submit_parameters_and_durable_no_resend_after_watch_stop(tmp_path, monkeypatch):
    args, native, calls, queries = case(tmp_path, monkeypatch)
    for _ in range(2):
        with pytest.raises(job.BindingError, match='MISSING_TERMINAL_NO_BLIND_RESEND'):
            job.execute_current_training_job(**args)
    assert len(calls) == 1
    assert calls[0][0] == tmp_path / 'job/training.sbatch'
    assert calls[0][1] == tmp_path / 'job/training-%j.log'
    assert calls[0][2] == {'partition': 'cpu-mocked-gpu-partition', 'time': '00:20:00'}
    assert sum(cmd[0] == 'scancel' for cmd in queries) == 1


def test_native_ambiguous_submission_intent_is_never_retried(tmp_path, monkeypatch):
    args, native, calls, _ = case(tmp_path, monkeypatch)
    def ambiguous(script, log, resources):
        calls.append(script)
        raise subprocess.TimeoutExpired('mock sbatch', 60)
    monkeypatch.setattr(native.runner, 'invoke_sbatch', ambiguous)
    with pytest.raises(subprocess.TimeoutExpired):
        job.execute_current_training_job(**args)
    with pytest.raises(ValueError, match='SUBMISSION_UNCONFIRMED_NO_AUTOMATIC_RETRY'):
        job.execute_current_training_job(**args)
    assert len(calls) == 1
    assert (tmp_path / 'job/training.SUBMIT_INTENT.json').exists()
    assert not (tmp_path / 'job/training.SUBMIT_RECEIPT.json').exists()


def test_wrapper_does_not_accept_half_finished_training_result(tmp_path, monkeypatch):
    args, native, calls, _ = case(tmp_path, monkeypatch)
    def submit(script, log, resources):
        calls.append(script)
        request_path = tmp_path / 'job/TRAINING_JOB_REQUEST.json'
        job.immutable_json(tmp_path / 'job/TRAINING_JOB_RESULT.json', {
            'schema_id': 'CURRENT_RESIDENT_TRAINING_JOB_RESULT_V1',
            'request_ref': job._native_ref(request_path),
            'result': {'schema_id': 'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT_V1', 'model_training_executed': True}})
        return '12345'
    monkeypatch.setattr(native.runner, 'invoke_sbatch', submit)
    with pytest.raises(job.BindingError, match='TRAINING_WORKER_RESULT'):
        job.execute_current_training_job(**args)
    assert len(calls) == 1


def test_invalid_operational_settings_rejected_before_submit(tmp_path, monkeypatch):
    args, _, calls, _ = case(tmp_path, monkeypatch)
    args['deployment']['rollout_settings']['watch_timeout_seconds'] = float('inf')
    with pytest.raises(job.BindingError, match='REGISTERED_TRAINING_OPERATIONAL_LIMIT'):
        job.execute_current_training_job(**args)
    assert calls == []


@pytest.mark.parametrize('wrapper_published', [True, False])
def test_completed_native_result_adopted_without_any_scheduler_submission(tmp_path, monkeypatch, wrapper_published):
    from test_training_entry import _accepted_artifacts
    from entry import training
    native_root = tmp_path / 'job/native'; native_root.mkdir(parents=True)
    refs, _ = _accepted_artifacts(native_root, monkeypatch)
    args, native, calls, queries = case(tmp_path, monkeypatch)
    recipe = tmp_path / 'h44/post/POST_ACCEPTED_RECIPE_BINDING.json'
    job.immutable_json(recipe, {'software_fixture': True})
    result = training._publish_result(args['start'], tmp_path / 'h44', native_root, refs)
    # This test exercises actual native artifacts; registration/bootstrap was
    # independently validated and is not the scheduler property under test.
    monkeypatch.setattr(training, 'load_training_sources', lambda binding: None)
    root = tmp_path / 'job'
    request = {'schema_id': 'CURRENT_RESIDENT_TRAINING_JOB_REQUEST_V1', 'start': args['start'],
        'analyzer_binding': args['analyzer_binding'], 'h44_run_root': str(tmp_path / 'h44'),
        'output_root': str(native_root), 'current_parent_context': args['current_parent_context'], 'round_index': 1,
        'result_path': str(root / 'TRAINING_JOB_RESULT.json'), 'source_identity_sha256': 'c' * 64}
    job.immutable_json(root / 'TRAINING_JOB_REQUEST.json', request)
    wrapper = {'schema_id': 'CURRENT_RESIDENT_TRAINING_JOB_RESULT_V1',
        'request_ref': job._native_ref(root / 'TRAINING_JOB_REQUEST.json'), 'result': result}
    if wrapper_published:
        job._publish_json(root / 'TRAINING_JOB_RESULT.json', wrapper)
    assert job.execute_current_training_job(**args) == result
    assert calls == [] and queries == []
    # A complete JSON wrapper cannot hide changed final adapter bytes.
    (Path(result['adapter_path']) / 'adapter_model.safetensors').write_bytes(b'changed')
    with pytest.raises(ValueError, match='INPUT_REF_SHA_MISMATCH'):
        job.execute_current_training_job(**args)
    assert calls == []


def test_query_and_containment_timeouts_leave_durable_stop_without_resend(tmp_path, monkeypatch):
    args, _, calls, _ = case(tmp_path, monkeypatch)
    queries = []
    def unavailable(argv, **kwargs):
        queries.append(argv)
        raise subprocess.TimeoutExpired(argv[0], 1)
    monkeypatch.setattr(job.subprocess, 'run', unavailable)
    with pytest.raises(job.BindingError, match='MISSING_TERMINAL_NO_BLIND_RESEND'):
        job.execute_current_training_job(**args)
    stop = job.read_json(tmp_path / 'job/TRAINING_WATCH_STOP.json')
    assert stop['containment_error'] == 'TimeoutExpired'
    assert stop['containment_rc'] is None
    assert stop['training_success_claimed'] is False
    count = len(queries)
    with pytest.raises(job.BindingError, match='MISSING_TERMINAL_NO_BLIND_RESEND'):
        job.execute_current_training_job(**args)
    assert len(calls) == 1 and len(queries) == count


def test_worker_bootstrap_failure_is_recorded_before_training(tmp_path, monkeypatch):
    from memory_binding import worker_bootstrap
    request = {'schema_id': 'CURRENT_RESIDENT_TRAINING_JOB_REQUEST_V1',
        'analyzer_binding': {'scientific_repo_root': 'fixture-repo'},
        'result_path': str(tmp_path / 'TRAINING_JOB_RESULT.json'), 'output_root': str(tmp_path / 'native')}
    path = tmp_path / 'TRAINING_JOB_REQUEST.json'; job.immutable_json(path, request)
    def reject(repo):
        raise ValueError('BOOTSTRAP_SOURCE_IDENTITY_CHANGED')
    monkeypatch.setattr(worker_bootstrap, 'bootstrap_current_and_children', reject)
    with pytest.raises(ValueError, match='BOOTSTRAP_SOURCE_IDENTITY_CHANGED'):
        job.worker(path, job.file_ref(path)['file_sha256'])
    stop = job.read_json(tmp_path / 'TRAINING_JOB_STOP.json')
    assert stop['request_ref'] == job._native_ref(path)
    assert stop['training_success_claimed'] is False
    assert not (tmp_path / 'TRAINING_JOB_RESULT.json').exists()


def test_atomic_publication_exposes_no_partial_destination(tmp_path, monkeypatch):
    destination = tmp_path / 'result.json'
    real_link = job.os.link
    observed = []
    def link(source, target):
        assert not Path(target).exists()
        observed.append(job.read_json(Path(source)))
        return real_link(source, target)
    monkeypatch.setattr(job.os, 'link', link)
    expected = {'complete_result': 'large enough to require a finished write' * 1000}
    job._publish_json(destination, expected)
    assert observed == [expected]
    assert job.read_json(destination) == expected
    job._publish_json(destination, expected)
    with pytest.raises(job.BindingError, match='ATOMIC_PUBLICATION_CONFLICT'):
        job._publish_json(destination, {'different': True})


def test_first_parent_gets_separate_original_smoke_and_training_allocations(tmp_path, monkeypatch):
    args, native, calls, _ = case(tmp_path, monkeypatch)
    args['current_parent_context'] = None
    phase_calls = []
    smoke = {'schema_id': 'CURRENT_NATIVE_INITIALIZATION_RESULT_V1',
             'training_execution_count': 0, 'optimizer_executed': False}
    trained = {'fixture_completed_native_training': True}
    # Receipt validation itself has native integration tests. This scenario
    # isolates job ordering, shared frozen request and original resource reuse.
    from entry import training
    monkeypatch.setattr(training, 'validate_initialization_result', lambda result, **kw: result)
    monkeypatch.setattr(job, '_validate_result', lambda result, request: result)
    def submit(script, log, resources):
        phase = script.stem
        request_path = tmp_path / 'job/TRAINING_JOB_REQUEST.json'
        if phase == 'training':
            assert (tmp_path / 'job/SMOKE_JOB_RESULT.json').is_file()
        phase_calls.append((phase, dict(resources), script.read_text()))
        schema = ('CURRENT_RESIDENT_INITIALIZATION_JOB_RESULT_V1' if phase == 'smoke'
                  else 'CURRENT_RESIDENT_TRAINING_JOB_RESULT_V1')
        job._publish_json(tmp_path / 'job' / (phase.upper() + '_JOB_RESULT.json'),
            {'schema_id': schema, 'request_ref': job._native_ref(request_path),
             'result': smoke if phase == 'smoke' else trained})
        return str(12345 + len(phase_calls))
    monkeypatch.setattr(native.runner, 'invoke_sbatch', submit)
    assert job.execute_current_training_job(**args) == trained
    assert [row[0] for row in phase_calls] == ['smoke', 'training']
    assert all(row[1] == {'partition': 'cpu-mocked-gpu-partition', 'time': '00:20:00'} for row in phase_calls)
    request_sha = job.file_ref(tmp_path / 'job/TRAINING_JOB_REQUEST.json')['file_sha256']
    assert all(request_sha in row[2] for row in phase_calls)
    assert '--phase smoke' in phase_calls[0][2] and '--phase training' in phase_calls[1][2]
    assert job.execute_current_training_job(**args) == trained
    assert len(phase_calls) == 2


def test_initialization_result_cannot_claim_optimizer_execution(tmp_path, monkeypatch):
    args, native, calls, _ = case(tmp_path, monkeypatch)
    args['current_parent_context'] = None
    def submit(script, log, resources):
        calls.append(script.stem)
        job._publish_json(tmp_path / 'job/SMOKE_JOB_RESULT.json', {
            'schema_id': 'CURRENT_RESIDENT_INITIALIZATION_JOB_RESULT_V1',
            'request_ref': job._native_ref(tmp_path / 'job/TRAINING_JOB_REQUEST.json'),
            'result': {'schema_id': 'CURRENT_NATIVE_INITIALIZATION_RESULT_V1',
                       'training_execution_count': 1, 'optimizer_executed': True}})
        return '12345'
    monkeypatch.setattr(native.runner, 'invoke_sbatch', submit)
    with pytest.raises(job.BindingError, match='ZERO_OPTIMIZER_EXECUTION'):
        job.execute_current_training_job(**args)
    assert calls == ['smoke']
    assert not (tmp_path / 'job/training.SUBMIT_INTENT.json').exists()
