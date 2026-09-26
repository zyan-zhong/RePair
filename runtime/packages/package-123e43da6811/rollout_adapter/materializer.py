"""Build fresh N4 artifacts from exact typed authorities, without live execution."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import sys
import tempfile
import zipfile


class AuthorityError(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def no_symlink_ancestors(path):
    p = Path(path).absolute()
    for node in (p, *p.parents):
        if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
            raise AuthorityError('PATH_ALIAS_FORBIDDEN:' + str(node))
    return p


def checked(ref):
    p = no_symlink_ancestors(ref['path'])
    if p.is_symlink() or not p.is_file():
        raise AuthorityError('REGISTERED_FILE_MISSING:' + str(p))
    raw = p.read_bytes()
    if digest(raw) != ref['sha256']:
        raise AuthorityError('REGISTERED_FILE_SHA_CHANGED:' + str(p))
    return raw


def obj(ref):
    value = json.loads(checked(ref))
    if not isinstance(value, dict):
        raise AuthorityError('REGISTERED_OBJECT_REQUIRED')
    return value


def ref(path):
    p = no_symlink_ancestors(path)
    if p.is_symlink() or not p.is_file():
        raise AuthorityError('REGISTERED_FILE_MISSING:' + str(p))
    return {'path': str(p.resolve()), 'sha256': digest(p.read_bytes())}


def put(path, raw):
    path = no_symlink_ancestors(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.' + path.name + '.', suffix='.pending', dir=path.parent, delete=False) as f:
            temp = Path(f.name)
            f.write(raw); f.flush(); os.fsync(f.fileno())
        try:
            os.link(temp, path)
            return True
        except FileExistsError:
            no_symlink_ancestors(path)
            if path.read_bytes() != raw:
                raise AuthorityError('IMMUTABLE_CONFLICT:' + str(path))
            return False
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def native_contracts(worktree):
    p = Path(worktree) / 'src/pchsi/round_control/rollout_collection.py'
    name = '_registered_rollout_' + digest(p.read_bytes())[:16]
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module(raw, name):
    scope = {'__name__': name}
    exec(compile(raw, name, 'exec'), scope)
    return scope


def _replace_function(raw, name, replacement):
    text = raw.decode(); nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(nodes) != 1:
        raise AuthorityError('REGISTERED_SOURCE_FUNCTION_SHAPE:' + name)
    node = nodes[0]; lines = text.splitlines(keepends=True)
    return (''.join(lines[:node.lineno - 1]) + replacement + '\n' + ''.join(lines[node.end_lineno:])).encode()


EXACT_RESOLVER = '''from pathlib import Path
from safe_io import load_json, sha_file

def find_exact_member(root, *, expected_sha256, suffixes=None):
    root=Path(root).resolve()
    authority=load_json(root/'ROUND_ROLLOUT_EXACT_INPUT_MEMBERS_V1.json')
    if authority.get('schema_id')!='ROUND_ROLLOUT_EXACT_INPUT_MEMBERS_V1':raise ValueError('EXACT_MEMBER_SCHEMA')
    matches=[r for r in authority['members'].values() if r['sha256']==expected_sha256]
    if len(matches)!=1:raise ValueError('EXACT_MEMBER_NOT_UNIQUE')
    relative=Path(matches[0]['member'])
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('EXACT_MEMBER_ESCAPE')
    p=root/relative
    if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():raise ValueError('EXACT_MEMBER_NOT_REGULAR')
    if suffixes is not None and p.suffix.lower() not in suffixes:raise ValueError('EXACT_MEMBER_SUFFIX')
    if sha_file(p)!=expected_sha256:raise ValueError('EXACT_MEMBER_SHA_CHANGED')
    return p

def validate_memory_references(path):
    value=load_json(Path(path))
    # token_budget_contract_sha256 is native semantic identity, checked by the loader below.
    for label in ('formal_b_result','source_runtime_binding'):
        p=Path(value[label+'_path'])
        if p.is_symlink() or not p.is_file() or sha_file(p)!=value[label+'_sha256']:raise ValueError('MEMORY_REFERENCE_CHANGED:'+label)
    from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
    load_calibrated_dev_snapshot_v2(snapshot_directory=Path(value['active_snapshot_directory']),expected_snapshot_sha256=value['active_snapshot_sha256'],token_budget_contract_path=Path(value['token_budget_contract_path']),expected_token_budget_contract_sha256=value['token_budget_contract_sha256'])
'''


def _patched_sources(files):
    out = dict(files)
    out['producer/exact_inputs.py'] = EXACT_RESOLVER.encode()
    out['producer/formal_rollout_support.py'] = _replace_function(
        out['producer/formal_rollout_support.py'], 'find_capsule_file_by_sha',
        'def find_capsule_file_by_sha(root, *, expected_sha256, suffixes=None):\n'
        '    from exact_inputs import find_exact_member\n'
        '    return find_exact_member(root, expected_sha256=expected_sha256, suffixes=suffixes)\n')
    text = out['producer/global_finalize.py'].decode()
    start = text.index('        manifest_candidates=[')
    end = text.index('        runtime_obj=load_json(runtime_path)', start)
    text = text[:start] + '''        from exact_inputs import find_exact_member
        manifest=find_exact_member(extracted_capsule,expected_sha256=train['manifest_sha256'],suffixes=('.jsonl',))
        runtime_path=find_exact_member(extracted_capsule,expected_sha256=runtime['runtime_binding_file_sha256'],suffixes=('.json',))
        memory_path=find_exact_member(extracted_capsule,expected_sha256=memory['runtime_identity_file_sha256'],suffixes=('.json',))
''' + text[end:]
    out['producer/global_finalize.py'] = text.encode()
    text = out['producer/shard_worker.py'].decode()
    if text.count('v1230/"build/worktree"') != 2:
        raise AuthorityError('WORKER_IMPLEMENTATION_LOCATION_SHAPE')
    out['producer/shard_worker.py'] = text.replace('v1230/"build/worktree"', 'Path(shard_plan["implementation_worktree"])').encode()
    # Keep the source-bound producer; replace only service endpoint ownership.
    worker = out['producer/shard_worker.py'].decode()
    begin = worker.index('        pre=service_mod.probe_policy_runtime_service')
    end = worker.index('        deadline=time.monotonic()+1800', begin)
    worker = worker[:begin] + """        from endpoint_lease import launch_with_lease
        launch=binding["service_launch_contract"]["launch_command"]
        service_out=(shard_root/"vllm.stdout.log").open("wb")
        service_err=(shard_root/"vllm.stderr.log").open("wb")
        service,endpoint=launch_with_lease(launch,output_root=shard_root,
          cwd=worktree,env=dict(os.environ),stdout=service_out,stderr=service_err)
        runtime=dict(runtime,policy_base_url=endpoint)
        pre=service_mod.probe_policy_runtime_service(runtime,timeout_seconds=1.0)
        write_new_json(shard_root/"PCHSI_V1232S_PRELAUNCH_ENDPOINT_PROBE_V1.json",pre)
""" + worker[end:]
    worker = worker.replace('    try:\n        if sha_file(capsule)', '''    def _progress():
        from progress import update
        update(shard_root,completed=len(rows),scheduled=0 if assigned is None else len(assigned),
          success=sum(r.get("status")=="SCIENTIFIC_SUCCESS" for r in rows),
          failure=sum(r.get("status")=="SCIENTIFIC_FAILURE" for r in rows),
          invalid=sum(r.get("status") in {"INFRASTRUCTURE_INVALID","PROTOCOL_INVALID"} for r in rows))
    try:
        if sha_file(capsule)''')
    worker = worker.replace('rows.append(row);continue','rows.append(row);_progress();continue')
    worker = worker.replace('rows.append(row);abort=True;continue','rows.append(row);_progress();abort=True;continue')
    worker = worker.replace('rows.append({**value,"terminal_receipt_sha256":sha_file(sidecar)})',
      'rows.append({**value,"terminal_receipt_sha256":sha_file(sidecar)});_progress()')
    worker = worker.replace('                rows.append(value)', '                rows.append(value);_progress()')
    out['producer/progress.py'] = (Path(__file__).parent.parent/'entry/progress.py').read_bytes()
    out['producer/shard_worker.py'] = worker.encode()
    out['producer/endpoint_lease.py'] = (Path(__file__).parent/'endpoint_lease.py').read_bytes()
    text = out['native_preflight.py'].decode()
    marker = '    _,profile=profile_from_binding(binding)'
    if text.count(marker) != 1:
        raise AuthorityError('NATIVE_PREFLIGHT_SHAPE')
    text = text.replace(marker, '    from exact_inputs import validate_memory_references\n    validate_memory_references(mp)\n' + marker)
    marker = '    equal_or_new(output,result)'
    if text.count(marker) != 1:
        raise AuthorityError('NATIVE_PREFLIGHT_RESULT_SHAPE')
    text = text.replace(marker, "    result['schedule_rows']=[{'scientific_cell_id':s.scientific_cell_id,'execution_attempt_id':s.execution_attempt_id,'task_id':s.cell.task_id,'task_index':s.cell.task_index} for s in schedule]\n" + marker)
    out['native_preflight.py'] = text.encode()
    for name, raw in out.items():
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return out


def _archive(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rows = z.infolist()
        if len(rows) != len({r.filename for r in rows}):
            raise AuthorityError('CAPSULE_DUPLICATE_MEMBER')
        out = {}
        for row in rows:
            p = PurePosixPath(row.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in row.filename or ':' in row.filename or ((row.external_attr >> 16) & 0o170000) == 0o120000:
                raise AuthorityError('CAPSULE_MEMBER_ESCAPE')
            if {'cell_terminals', 'attempts', 'results', 'training_outputs'} & set(p.parts):
                raise AuthorityError('CAPSULE_CONTAINS_OLD_OUTPUTS')
            if not row.is_dir():
                out[row.filename] = z.read(row)
        return out


def _input_from_archive(members, expected):
    # This iterates a single SHA-bound archive inventory, never the filesystem.
    matches = [(n, b) for n, b in members.items() if digest(b) == expected]
    if len(matches) != 1:
        raise AuthorityError('REGISTERED_ARCHIVE_INPUT_NOT_UNIQUE:' + expected)
    return matches[0][1]


def materialize(spec, output_root):
    if spec.get('schema_id') != 'REGISTERED_FRESH_ROLLOUT_SPEC_V1':
        raise AuthorityError('SPEC_SCHEMA')
    ready = obj(spec['ready']); owner = obj(spec['owner'])
    if ready.get('schema_id') != 'NATIVE_R2_RECOVERY_READY_V1' or owner.get('schema_id') != 'R2_NATIVE_RECOVERY_OWNER_V1':
        raise AuthorityError('SOURCE_AUTHORITY_SCHEMA')
    if (owner['root'] != ready['root'] or owner['request_sha256'] != ready['request_file_sha256'] or owner['source_identity'] != ready['source_identity']):
        raise AuthorityError('READY_OWNER_CONFLICT')
    source_root = Path(spec.get('source_package', ready['source_package']))
    files = {}
    for name, h in ready['source_identity']['files'].items():
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts:
            raise AuthorityError('SOURCE_MEMBER_ESCAPE')
        files[name] = checked({'path': source_root / name, 'sha256': h})
    cap_ref = {'path': spec.get('capsule_path', ready['capsule_path']), 'sha256': ready['capsule_sha256']}
    members = _archive(checked(cap_ref))
    binding_name = 'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json'
    binding = json.loads(members[binding_name])
    worktree = no_symlink_ancestors(spec['implementation']['path']).resolve()
    formal = obj(spec['execution_binding'])
    checked({'path': worktree / 'src/pchsi/round_control/rollout_collection.py', 'sha256': formal['rollout_control_source_sha256']})
    native = native_contracts(worktree)
    request_value = obj(spec['request'])
    if request_value['schema_id'] != 'ROUND_ROLLOUT_COLLECTION_REQUEST_V1':
        raise AuthorityError('CURRENT_REQUEST_SCHEMA')
    request = native.RoundRolloutCollectionRequestV1(**{k: v for k, v in request_value.items() if k not in {'schema_id', 'schema_version', 'selection_rule'}})
    if request.to_dict() != request_value:
        raise AuthorityError('CURRENT_REQUEST_NONCANONICAL')
    roles = {
        'runtime': ('runtime_authority', 'runtime_binding_file_sha256', 'policy_runtime_binding_sha256'),
        'memory': ('memory_authority', 'runtime_identity_file_sha256', 'round_memory_runtime_authority_sha256'),
        'train_manifest': ('train_update_authority', 'manifest_sha256', 'train_update_manifest_sha256'),
    }
    current_refs = obj(spec['input_refs']) if spec.get('input_refs') else {}
    if current_refs and current_refs.get('schema_id') != 'ROUND_ROLLOUT_INPUT_REFERENCES_V1':
        raise AuthorityError('CURRENT_INPUT_REFERENCE_SCHEMA')
    if current_refs and current_refs.get('request_sha256') != request.request_sha256:
        raise AuthorityError('CURRENT_INPUT_REFERENCE_REQUEST_MISMATCH')
    input_bytes = {}
    for role, (section, field, request_field) in roles.items():
        expected = getattr(request, request_field)
        if role in current_refs:
            raw = checked(current_refs[role])
        else:
            if expected != binding[section][field]:
                raise AuthorityError('CURRENT_' + role.upper() + '_AUTHORITY_MISSING')
            raw = _input_from_archive(members, expected)
        if digest(raw) != expected:
            raise AuthorityError('CURRENT_' + role.upper() + '_SHA_MISMATCH')
        input_bytes[role] = raw
    runtime = json.loads(input_bytes['runtime']); memory = json.loads(input_bytes['memory'])
    changed_policy = (request.parent_policy_id != binding['parent_policy_id'] or request.policy_runtime_binding_sha256 != binding['runtime_authority']['runtime_binding_file_sha256'])
    if runtime['policy_runtime_manifest_sha256'] != request.parent_policy_artifact_sha256:
        raise AuthorityError('CURRENT_POLICY_ARTIFACT_MISMATCH')
    if changed_policy and 'policy_launch_authority' not in current_refs:
        raise AuthorityError('CURRENT_POLICY_NATIVE_LAUNCH_AUTHORITY_MISSING')
    for key in ('active_snapshot_sha256', 'token_budget_contract_sha256'):
        expected = request.round_start_memory_snapshot_sha256 if key == 'active_snapshot_sha256' else request.token_budget_contract_sha256
        if memory[key] != expected:
            raise AuthorityError('CURRENT_MEMORY_IDENTITY_MISMATCH:' + key)
    engine = obj(current_refs['engine_profile']) if 'engine_profile' in current_refs else binding['engine_profile_authority']
    validator = _module(members['policy_runtime_lifecycle_source/policy_runtime_engine_profile_receipt.py'], 'registered_engine_validator')
    validator['validate_engine_profile_receipt'](engine, runtime)
    builder = _module(members['policy_runtime_lifecycle_source/policy_runtime_engine_profile.py'], 'registered_engine_builder')
    launch = builder['build_current_runtime_service_launch_contract'](runtime, engine, python_executable=sys.executable)
    if 'policy_launch_authority' in current_refs:
        authority = obj(current_refs['policy_launch_authority'])
        if authority.get('schema_id') != 'ROUND_POLICY_NATIVE_LAUNCH_AUTHORITY_V1' or authority.get('runtime_binding_file_sha256') != request.policy_runtime_binding_sha256 or authority.get('parent_policy_artifact_sha256') != request.parent_policy_artifact_sha256 or authority.get('parent_policy_id') != request.parent_policy_id:
            raise AuthorityError('CURRENT_POLICY_LAUNCH_AUTHORITY_MISMATCH')
        launch = obj(authority['launch_contract'])
        for key in ('base_model_local_path', 'served_model_name', 'policy_base_url', 'context_window_tokens', 'vllm_version'):
            if launch.get(key) != runtime.get(key):
                raise AuthorityError('CURRENT_POLICY_LAUNCH_RUNTIME_MISMATCH:' + key)
        if launch.get('engine_profile_sha256') != engine['engine_profile_sha256']:
            raise AuthorityError('CURRENT_POLICY_LAUNCH_ENGINE_MISMATCH')
    launch_validator = _module(members['policy_runtime_lifecycle_source/policy_runtime_slurm_execution.py'], 'registered_launch_validator')
    launch_validator['validate_launch_contract'](launch)
    profile = dict(binding['policy_execution_profile'])
    profile.update(served_model_name=runtime['served_model_name'], continuation_request_contract=runtime['continuation_request_contract'], policy_version=request.parent_policy_id)
    profile_artifact = {'schema_id': 'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1', 'schema_version': 1,
                        'profile_kind': profile['profile_kind'], 'arm_id': 'I1_STRUCTURED_SERIALIZATION_CONSTRAINT_V1',
                        'policy_version': profile['policy_version'], 'served_model_name': profile['served_model_name'],
                        'continuation_request_contract': profile['continuation_request_contract']}
    if digest(canonical(profile_artifact)) != request.execution_profile_sha256:
        raise AuthorityError('CURRENT_PROFILE_AUTHORITY_MISMATCH')
    if formal.get('request_sha256') != request.request_sha256:
        raise AuthorityError('FORMAL_EXECUTION_REQUEST_MISMATCH')
    source_roles = {'rollout_control_source_sha256': 'src/pchsi/round_control/rollout_collection.py',
                    'clean_execution_binding_source_sha256': 'src/pchsi/round_control/clean_execution_binding.py',
                    'episode_evaluator_source_sha256': 'src/pchsi/evaluation/episode_evaluator.py',
                    'attempt_receipts_source_sha256': 'src/pchsi/round_control/attempt_receipts.py',
                    'policy_runtime_adapter_sha256': 'src/pchsi/evaluation/policy_attempt_adapter.py'}
    for role, relative in source_roles.items():
        members['repo_source/' + relative] = checked({'path': worktree / relative, 'sha256': formal[role]})
    validated_binding = native.RoundRolloutExecutionBindingV1(**{k: v for k, v in formal.items() if k not in {'schema_id', 'schema_version', 'shell', 'human_runtime_selection_required'}})
    if validated_binding.to_dict() != formal or formal.get('scientific_execution_authorized') is not True:
        raise AuthorityError('FORMAL_EXECUTION_BINDING_INVALID')
    train = dict(binding['train_update_authority'])
    if 'train_authority' in current_refs:
        train = obj(current_refs['train_authority'])
    if train['manifest_sha256'] != request.train_update_manifest_sha256:
        raise AuthorityError('CURRENT_TRAIN_AUTHORITY_MISMATCH')
    train['rollout_seed'] = request.rollout_seed
    count = len(input_bytes['train_manifest'].splitlines())
    if count != train['row_count']:
        raise AuthorityError('TRAIN_MANIFEST_COUNT_MISMATCH')
    mapping = {}
    for role, raw in input_bytes.items():
        name = 'inputs/' + role + ('.jsonl' if role == 'train_manifest' else '.json')
        members[name] = raw
        mapping[role] = {'member': name, 'sha256': digest(raw)}
    # Remove original aliases for the three inputs; the new explicit map owns lookup.
    for name in tuple(members):
        if name not in {r['member'] for r in mapping.values()} and digest(members[name]) in {digest(b) for b in input_bytes.values()}:
            del members[name]
    binding.update(round_id=request.round_id, parent_policy_id=request.parent_policy_id, implementation_head=spec['implementation']['head'],
                   policy_execution_profile=profile, service_launch_contract=launch, engine_profile_authority=engine, train_update_authority=train)
    binding['runtime_authority'].update(runtime_binding_file_sha256=request.policy_runtime_binding_sha256, runtime_binding_path=current_refs.get('runtime', {}).get('path', binding['runtime_authority']['runtime_binding_path']))
    binding['memory_authority'].update(runtime_identity_file_sha256=request.round_memory_runtime_authority_sha256, active_snapshot_sha256=request.round_start_memory_snapshot_sha256, token_budget_contract_sha256=request.token_budget_contract_sha256)
    members[binding_name] = canonical(binding)
    members['ROUND_ROLLOUT_EXACT_INPUT_MEMBERS_V1.json'] = canonical({'schema_id': 'ROUND_ROLLOUT_EXACT_INPUT_MEMBERS_V1', 'members': mapping, 'request_sha256': request.request_sha256})
    resource_name = 'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1.json'
    resources = json.loads(members[resource_name])
    if 'resource_plan' in current_refs:
        resources = obj(current_refs['resource_plan'])
    if resources['gpus'] != engine['tensor_parallel_size']:
        raise AuthorityError('CURRENT_ENGINE_RESOURCE_AUTHORITY_MISMATCH')
    resources.update(execution_binding_sha256=digest(members[binding_name]), round_memory_snapshot_sha256=request.round_start_memory_snapshot_sha256, train_update_manifest_sha256=request.train_update_manifest_sha256)
    resources['plan_sha256'] = digest(b'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1\0' + canonical({k: v for k, v in resources.items() if k != 'plan_sha256'}))
    members[resource_name] = canonical(resources)
    allocation = _module(members['allocation_preflight.py'], 'registered_allocation')['build_allocation_preflight_contract'](resources)
    members['ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_ALLOCATION_PREFLIGHT_V1.json'] = canonical(allocation)
    root = no_symlink_ancestors(output_root).resolve()
    owner_record = {'schema_id': 'FRESH_ROLLOUT_MATERIALIZATION_OWNER_V1', 'request_sha256': request.request_sha256, 'spec_sha256': digest(canonical(spec))}
    put(root / 'MATERIALIZATION_OWNER.json', canonical(owner_record))
    outbuf = io.BytesIO()
    with zipfile.ZipFile(outbuf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, raw)
    cap_path = root / 'CURRENT_ROUND_SOURCE_CAPSULE.zip'; put(cap_path, outbuf.getvalue())
    for name, raw in members.items():
        put(root / 'input_capsule' / name, raw)
    patched = _patched_sources(files)
    for name, raw in patched.items():
        put(root / 'producer_source' / name, raw)
    request_path = root / 'round_evidence/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json'
    put(request_path, checked(spec['request']))
    plan = dict(spec['shard_plan'])
    if type(spec['attempt_ordinal']) is not int or spec['attempt_ordinal'] < 0:
        raise AuthorityError('ATTEMPT_ORDINAL_INVALID')
    plan.update(activation_id=request.execution_attempt_id, current_round_request_path=str(request_path), current_round_request_file_sha256=digest(request_path.read_bytes()),
                repaired_capsule_sha256=digest(cap_path.read_bytes()), fresh_execution_attempt_ordinal=spec['attempt_ordinal'], total_schedule_count=count, implementation_worktree=str(worktree))
    plan_path = root / 'PCHSI_V1232K_SHARD_PLAN_V1.json'; put(plan_path, canonical(plan))
    script_path = root / 'run_current_array.sh'
    argv = [sys.executable, '-B', str(root / 'producer_source/producer/shard_worker.py'), '--state-root', str(root), '--v1230-output-root', str(worktree.parent), '--capsule', str(cap_path), '--shard-plan', str(plan_path)]
    put(script_path, ('#!/usr/bin/env bash\nexec ' + ' '.join(shlex.quote(v) for v in argv) + ' --shard-id "${SLURM_ARRAY_TASK_ID}"\n').encode())
    sub = _module(files['producer/submission_contract.py'], 'registered_submission')
    sbatch = sub['build_array_sbatch_argv'](slurm_plan=resources, shard_count=plan['shard_count'], max_concurrent_shards=plan['max_concurrent_shards'], walltime_minutes=plan['derived_walltime_minutes_per_shard'], script_path=script_path, stdout_path=root / 'slurm-%A_%a.out', stderr_path=root / 'slurm-%A_%a.err', activation=request.execution_attempt_id)
    manifest_path = root / 'MATERIALIZED_ROLLOUT.json'
    # Publish the already validated current profile as a typed downstream asset.
    # Its identity was compared with request.execution_profile_sha256 above.
    profile_path = root / 'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json'
    put(profile_path, canonical(profile_artifact))
    value = {'schema_id': 'REGISTERED_FRESH_ROLLOUT_MATERIALIZATION_V1', 'manifest_path': str(manifest_path), 'root': str(root), 'round_id': request.round_id,
             'request_path': str(request_path), 'request_file_sha256': digest(request_path.read_bytes()), 'request_sha256': request.request_sha256,
             'formal_execution_binding': formal, 'capsule_path': str(cap_path), 'capsule_sha256': digest(cap_path.read_bytes()),
             'shard_plan_path': str(plan_path), 'shard_plan_sha256': digest(plan_path.read_bytes()), 'implementation_worktree': str(worktree),
             'source_root': str(root / 'producer_source'), 'source_files': {n: digest(b) for n, b in patched.items()},
             'capsule_member_sha256': {n: digest(b) for n, b in members.items()},
             'runner_path': str(script_path), 'runner_sha256': digest(script_path.read_bytes()),
             'sbatch_argv': sbatch, 'gate_shard_id': plan['staged_release_gate']['initially_release_only_shard_id'],
             'input_member_manifest': mapping, 'execution_profile_ref': ref(profile_path),
             'source_ready_sha256': spec['ready']['sha256'], 'spec_sha256': owner_record['spec_sha256'],
             'scientific_execution_started': False, 'native_preflight_passed': False, 'filesystem_discovery_used': False,
             'bounded_registered_archive_inventory_used': True, 'full_campaign_released': False}
    put(manifest_path, canonical(value))
    return value


def build_registered_spec(*, captured_root, formal_root, implementation_worktree, current_request=None, current_binding=None, input_refs=None, attempt_ordinal=0):
    """Machine-facing bootstrap from exact capture layout; no operator choices.

    implementation_worktree is supplied by the full-round registered source
    resolver, not selected by basename, git branch search, or an operator.
    """
    captured = Path(captured_root); formal = Path(formal_root)
    ready_ref = ref(captured / 'typed_authorities/READY.json')
    owner_ref = ref(captured / 'typed_authorities/RECOVERY_OWNER.json')
    chain = obj(ref(captured / 'anchors/LIVE_TYPED_CHAIN.json'))
    for label, bound in [('READY', ready_ref), ('RECOVERY_OWNER', owner_ref)]:
        rows = [r for r in chain['typed_authorities'] if r.get('label') == label and r.get('present') is True]
        if len(rows) != 1 or rows[0].get('sha256') != bound['sha256']:
            raise AuthorityError('CAPTURED_' + label + '_IDENTITY_MISMATCH')
    ready = obj(ready_ref)
    plan = obj({'path': ready['shard_plan_path'], 'sha256': ready['shard_plan_sha256']})
    capture = obj(ref(captured / 'anchors/evidence/FORMAL_MAX10_EXECUTION_ENTRY_SOURCE_CAPTURE_V1.json'))
    authorities = capture['formal_state_authority']
    for name, identity in authorities.items():
        checked({'path': formal / name, 'sha256': identity['sha256']})
    prelaunch = json.loads((formal / 'FORMAL_MAX10_PRELAUNCH_AUTHORITY_V1.json').read_bytes())
    request_ref = current_request or ref(formal / 'ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json')
    binding_ref = current_binding or ref(formal / 'ROUND_ROLLOUT_EXECUTION_BINDING_V1.json')
    if current_request is None:
        if obj(request_ref)['request_sha256'] != prelaunch['first_round_request_sha256'] or obj(binding_ref)['binding_sha256'] != prelaunch['first_round_rollout_binding_sha256']:
            raise AuthorityError('FORMAL_PRELAUNCH_CURRENT_REQUEST_BINDING_MISMATCH')
    value = {'schema_id': 'REGISTERED_FRESH_ROLLOUT_SPEC_V1', 'ready': ready_ref, 'owner': owner_ref,
             'request': request_ref, 'execution_binding': binding_ref,
             'implementation': {'path': str(implementation_worktree), 'head': prelaunch['integration_commit_oid']},
             'attempt_ordinal': attempt_ordinal, 'shard_plan': plan}
    if input_refs is not None:
        value['input_refs'] = input_refs
    return value
