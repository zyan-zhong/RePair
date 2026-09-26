"""Registered Stage4D ordinal partition and graceful partial worker ownership.

Scheduler submission and the native COMPLETED/0:0 check belong to the resident
owner. This module never retries failed jobs or unfinished individual episodes.
"""
from pathlib import Path
import os

from continuity_binding.api import read_ref, write_once, regular_path
from .native import Native, ARRAY_CONFIG
from .materialize import need, prepare, materialize
from .execute import _registered_decider, execute_binding, finalize_binding


def _parallel_components(binding_ref):
    binding = read_ref(binding_ref)
    need(binding.get('schema_id') == 'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1', 'OFFOFF_BINDING_SCHEMA')
    native = Native.load(binding['native_repo_root'], binding['source_refs'])
    context = prepare(native=native, **binding['input_refs'])
    need(materialize(native=native, **binding['input_refs'], sink=Path(binding_ref['path']).parent) == binding_ref,
         'OFFOFF_PARALLEL_CURRENT_BINDING_DRIFT')
    _registered_decider(native, read_ref(context['protocol']['promotion_rule_ref']))
    config_ref = native.sources[str(native.root / ARRAY_CONFIG)]
    policy = read_ref(config_ref)['array_policy']
    parallel = native.parallel()
    need(policy['shards'] == parallel.PARALLEL_SHARD_COUNT and policy['automatic_failed_job_retry'] is False,
         'NATIVE_ARRAY_EXECUTION_POLICY_MISMATCH')
    assignments = parallel.partition_ordinals(
        parallel.remaining_ordinals(completed_prefix_count=0, total_pairs=binding['paired_cell_count']),
        shard_count=policy['shards'])
    return binding, native, config_ref, policy, assignments


def materialize_parallel(binding_ref, *, sink):
    """Freeze all shard assignments before execution; same native science grid."""
    binding, _, config_ref, policy, assignments = _parallel_components(binding_ref)
    sink = regular_path(Path(sink).absolute())
    value = {'schema_id':'CURRENT_NATIVE_OFFOFF_PARALLEL_BINDING_V1', 'binding_ref':binding_ref,
        'request_sha256':binding['request_sha256'], 'execution_attempt_id':binding['execution_attempt_id'],
        'native_array_config_ref':config_ref, 'array_policy':policy,
        'shards':[{'shard_id':number,'ordinals':list(rows),
                   'execution_root':str(sink/f'shard_{number}/execution')}
                  for number,rows in enumerate(assignments)]}
    return write_once(sink/'CURRENT_NATIVE_OFFOFF_PARALLEL_BINDING.json', value)


def _load_parallel(ref):
    value = read_ref(ref)
    need(value.get('schema_id') == 'CURRENT_NATIVE_OFFOFF_PARALLEL_BINDING_V1', 'OFFOFF_PARALLEL_SCHEMA')
    need(materialize_parallel(value['binding_ref'], sink=Path(ref['path']).parent) == ref,
         'OFFOFF_PARALLEL_ASSIGNMENT_DRIFT')
    return value


def _status(ref, *, parallel_ref, shard_id, resumption_ordinal, assigned):
    value = read_ref(ref)
    for key, expected in {'schema_id':'CURRENT_NATIVE_OFFOFF_SHARD_STATUS_V1', 'parallel_ref':parallel_ref,
        'shard_id':shard_id, 'resumption_ordinal':resumption_ordinal, 'assigned_pair_count':assigned}.items():
        need(type(value.get(key)) is type(expected) and value.get(key) == expected, 'OFFOFF_SHARD_STATUS_IDENTITY:' + key)
    counts = [value.get(key) for key in ('parent_cell_count','candidate_cell_count')]
    need(all(type(count) is int and 0 <= count <= assigned for count in counts), 'OFFOFF_SHARD_STATUS_COUNTS')
    need(type(value.get('complete')) is bool and value['complete'] == (counts[0] == counts[1] == assigned),
         'OFFOFF_SHARD_STATUS_COMPLETENESS')
    need(type(value.get('graceful_partial')) is bool, 'OFFOFF_SHARD_STATUS_PARTIAL_TYPE')
    need(value['complete'] or (value['graceful_partial'] and counts[0] == counts[1]), 'OFFOFF_SHARD_NOT_GRACEFUL_PARTIAL')
    return value


def _file_ref(path):
    import hashlib
    path = regular_path(path)
    return {'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def check_worker_resume(*, root, parallel_ref, shard_id, resumption_ordinal, assigned, maximum):
    """Read only the finite current/prior worker receipts; never infer a retry."""
    need(type(resumption_ordinal) is int and 0 <= resumption_ordinal <= maximum,
         'OFFOFF_PARTIAL_RESUMPTION_BUDGET_EXHAUSTED')
    root = Path(root)
    if resumption_ordinal:
        previous_ref = _file_ref(root/f'SHARD_STATUS_{resumption_ordinal-1:03d}.json')
        previous = _status(previous_ref, parallel_ref=parallel_ref, shard_id=shard_id,
            resumption_ordinal=resumption_ordinal-1, assigned=assigned)
        need(not previous['complete'] and previous['graceful_partial'], 'OFFOFF_RESUME_ONLY_GRACEFUL_PARTIAL')
    status_path = root/f'SHARD_STATUS_{resumption_ordinal:03d}.json'
    if status_path.exists():
        ref = _file_ref(status_path)
        _status(ref, parallel_ref=parallel_ref, shard_id=shard_id, resumption_ordinal=resumption_ordinal, assigned=assigned)
        return ref
    need(not (root/f'WORKER_STARTED_{resumption_ordinal:03d}.json').exists(), 'OFFOFF_AMBIGUOUS_WORKER_NO_BLIND_RETRY')
    return None


def execute_parallel_worker(parallel_ref, *, shard_id, resumption_ordinal, host, port):
    """Invoke one original native worker subset inside the owner's one-GPU job."""
    need(os.name == 'posix', 'OFFOFF_LIVE_REQUIRES_REGISTERED_LINUX_RUNTIME')
    import fcntl
    parallel = _load_parallel(parallel_ref)
    policy = parallel['array_policy']
    need(type(shard_id) is int and 0 <= shard_id < policy['shards'], 'OFFOFF_SHARD_ID')
    need(type(resumption_ordinal) is int and 0 <= resumption_ordinal <= policy['max_partial_resumptions'],
         'OFFOFF_PARTIAL_RESUMPTION_BUDGET_EXHAUSTED')
    binding = read_ref(parallel['binding_ref'])
    native = Native.load(binding['native_repo_root'], binding['source_refs'])
    native.parallel().require_single_visible_device(os.environ.get('CUDA_VISIBLE_DEVICES',''))
    shard = parallel['shards'][shard_id]
    root = regular_path(Path(shard['execution_root']).parent)
    root.mkdir(parents=True, exist_ok=True)
    fd = os.open(root/'SHARD_WRITER.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status_path = root/f'SHARD_STATUS_{resumption_ordinal:03d}.json'
        reused = check_worker_resume(root=root,parallel_ref=parallel_ref,shard_id=shard_id,
            resumption_ordinal=resumption_ordinal,assigned=len(shard['ordinals']),maximum=policy['max_partial_resumptions'])
        if reused is not None:
            return reused
        intent_path = root/f'WORKER_STARTED_{resumption_ordinal:03d}.json'
        runtime_sink = root/f'runtime_{resumption_ordinal:03d}'
        write_once(intent_path, {'schema_id':'CURRENT_NATIVE_OFFOFF_WORKER_INTENT_V1',
            'parallel_ref':parallel_ref, 'shard_id':shard_id, 'resumption_ordinal':resumption_ordinal,
            'slurm_job_id':os.environ.get('SLURM_JOB_ID'), 'host':host, 'port':port})
        status = execute_binding(parallel['binding_ref'], host=host, port=port,
            _worker={'ordinals':shard['ordinals'], 'execution_root':shard['execution_root'],
                     'runtime_sink':str(runtime_sink), 'worker_budget_seconds':policy['worker_budget_seconds']})
        value = {'schema_id':'CURRENT_NATIVE_OFFOFF_SHARD_STATUS_V1', 'parallel_ref':parallel_ref,
            'shard_id':shard_id, 'resumption_ordinal':resumption_ordinal, **status,
            'result_interpretation_authorized':False, 'promotion_authorized':False}
        ref = write_once(status_path, value)
        _status(ref, parallel_ref=parallel_ref, shard_id=shard_id, resumption_ordinal=resumption_ordinal,
                assigned=len(shard['ordinals']))
        return ref
    finally:
        os.close(fd)


def finalize_parallel(parallel_ref):
    """Require all registered shards, then replay all native audits and aggregate."""
    parallel = _load_parallel(parallel_ref)
    binding = read_ref(parallel['binding_ref'])
    roots = [None] * binding['paired_cell_count']
    statuses = []
    for shard in parallel['shards']:
        root = Path(shard['execution_root']).parent
        selected = None
        # Finite registered count, never latest/mtime or recursive discovery.
        for ordinal in range(parallel['array_policy']['max_partial_resumptions'] + 1):
            path = root/f'SHARD_STATUS_{ordinal:03d}.json'
            if not path.exists():
                break
            ref = _file_ref(path)
            value = _status(ref, parallel_ref=parallel_ref, shard_id=shard['shard_id'],
                            resumption_ordinal=ordinal, assigned=len(shard['ordinals']))
            need(selected is None or (not selected[1]['complete'] and selected[1]['graceful_partial']),
                 'OFFOFF_UNAUTHORIZED_EXTRA_RESUMPTION')
            selected = (ref,value)
        need(selected is not None and selected[1]['complete'], 'OFFOFF_ALL_SHARDS_MUST_BE_COMPLETE')
        statuses.append(selected[0])
        for ordinal in shard['ordinals']:
            need(roots[ordinal] is None, 'OFFOFF_SHARD_ORDINAL_OVERLAP')
            roots[ordinal] = shard['execution_root']
    need(all(root is not None for root in roots), 'OFFOFF_SHARD_GRID_INCOMPLETE')
    terminal = finalize_binding(parallel['binding_ref'], execution_roots_by_ordinal=roots)
    write_once(Path(parallel_ref['path']).parent/'PARALLEL_FINALIZATION.json',
        {'schema_id':'CURRENT_NATIVE_OFFOFF_PARALLEL_FINALIZATION_V1', 'parallel_ref':parallel_ref,
         'shard_status_refs':statuses, 'terminal_ref':terminal})
    return terminal
