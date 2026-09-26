"""Exact typed I/O for the two existing operation bindings; no discovery."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class BindingError(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def loads(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise BindingError('DUPLICATE_JSON_KEY:' + key)
            result[key] = value
        return result
    def bad(value):
        raise BindingError('NONFINITE_JSON:' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def regular(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise BindingError('EXACT_REGULAR_FILE_REQUIRED:' + str(path))
    if path.resolve() != path:
        raise BindingError('SYMLINK_COMPONENT_FORBIDDEN:' + str(path))
    return path


def read_json(path):
    return loads(regular(path).read_bytes())


def file_ref(path, *, schema_id=None):
    path = regular(Path(path).absolute())
    result = {'path': str(path), 'file_sha256': digest(path.read_bytes())}
    if schema_id is not None:
        result['schema_id'] = schema_id
    return result


def read_ref(ref, *, as_bytes=False):
    if not isinstance(ref, dict):
        raise BindingError('TYPED_REF_REQUIRED')
    path = regular(ref['path'])
    raw = path.read_bytes()
    if digest(raw) != ref.get('file_sha256'):
        raise BindingError('FILE_SHA_MISMATCH:' + str(path))
    if as_bytes:
        return raw
    value = loads(raw)
    if ref.get('schema_id') is not None and value.get('schema_id') != ref['schema_id']:
        raise BindingError('SCHEMA_MISMATCH:' + str(path))
    return value


def immutable_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise BindingError('OUTPUT_SYMLINK:' + str(path))
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise BindingError('IMMUTABLE_OUTPUT_MISMATCH:' + str(path))
        return
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def immutable_json(path, value):
    immutable_bytes(path, canonical(value))


def build_from_index(index, *, source_binding, output_root):
    """Only /refs is traversed. No child receipts, glob, cwd or mtime fallback.

    The producer writes its finite stage refs into the current typed index;
    package/runtime/Memory defaults come from the already-authorized operation's
    /refs. Per-round index refs take precedence, preserving promoted identity.
    """
    if isinstance(index, (str, Path)):
        index = read_json(Path(index).absolute())
    refs = {**source_binding.get('refs', {}), **index.get('refs', {})}
    if 'request' not in refs:
        raise BindingError('REGISTERED_MATERIALIZATION_MISSING:/refs/request')
    request = read_ref(refs['request'])
    for key in ('round_id', 'parent_policy_id'):
        if not isinstance(request.get(key), str) or not request[key]:
            raise BindingError('REQUEST_IDENTITY_MISSING:' + key)
    if 'memory_runtime' in refs:
        memory = read_ref(refs['memory_runtime'])
        if memory.get('active_snapshot_sha256') != request.get('round_start_memory_snapshot_sha256'):
            raise BindingError('MEMORY_SNAPSHOT_MISMATCH')
        expected = request.get('round_memory_runtime_authority_sha256')
        if expected is not None and refs['memory_runtime']['file_sha256'] != expected:
            raise BindingError('MEMORY_RUNTIME_FILE_IDENTITY_MISMATCH')
    out = {k: v for k, v in source_binding.items() if k != 'refs'}
    out.update(schema_id='FORMAL_ANALYZER_PRE_EXECUTION_BINDING_V1_6', schema_version=1,
               round_id=request['round_id'], parent_policy_id=request['parent_policy_id'],
               state_root=index.get('state_root', source_binding.get('state_root')),
               output_root=str(Path(output_root).absolute()), refs=refs)
    return out


def build_from_rollout_result(result, *, source_binding, output_root, current_index=None):
    """Map the existing rollout materializer's finite outputs to stage inputs.

    Call after rollout publication. Scientific/source configuration remains inside
    the caller's existing first-round or resident operation binding.
    """
    if isinstance(result, (str, Path)):
        result = read_json(Path(result).absolute())
    if result.get('schema_id') != 'REGISTERED_FRESH_ROLLOUT_MATERIALIZATION_V1':
        raise BindingError('ROLLOUT_MATERIALIZATION_SCHEMA')
    root = Path(result['root'])
    if not root.is_absolute() or root.resolve() != root:
        raise BindingError('ROLLOUT_ROOT_MUST_BE_EXACT_ABSOLUTE')
    refs = {'request': {'path': result['request_path'],
                        'file_sha256': result['request_file_sha256']}}
    request = read_ref(refs['request'])
    if request.get('round_id') != result['round_id'] or request.get('request_sha256') != result['request_sha256']:
        raise BindingError('ROLLOUT_RESULT_REQUEST_IDENTITY')
    for name, filename in [('handoff', 'ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'),
        ('global_terminal', 'PCHSI_V1232K_GLOBAL_TERMINAL_V1.json'),
        ('universe', 'ROUND_ROLLOUT_UNIVERSE_SEAL_V1.json'),
        ('cohort', 'ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1.json'),
        ('bundle_index', 'ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1.json')]:
        refs[name] = file_ref(root / 'round_evidence' / filename)
    for role, name in [('runtime', 'actor_runtime'), ('memory', 'memory_runtime'),
                       ('train_manifest', 'train_update_manifest')]:
        member = result['input_member_manifest'][role]
        relative = Path(member['member'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in member['member']:
            raise BindingError('ROLLOUT_CAPSULE_MEMBER_ESCAPE:' + role)
        refs[name] = {'path': str(root / 'input_capsule' / relative),
                      'file_sha256': member['sha256']}
        read_ref(refs[name], as_bytes=True)
    index = current_index or {}
    if isinstance(index, (str, Path)):
        index = read_json(Path(index).absolute())
    for name, ref in index.get('refs', {}).items():
        if name in refs and refs[name] != ref:
            raise BindingError('CURRENT_INDEX_ROLLOUT_REF_CONFLICT:' + name)
        refs[name] = ref
    return build_from_index({'refs': refs, 'state_root': str(root)},
                            source_binding=source_binding, output_root=output_root)


def accept_pre(call_dir, *, expected, finalizer):
    call_dir = Path(call_dir)
    if call_dir.is_symlink() or not call_dir.is_dir() or not (call_dir / 'logical_call.json').is_file():
        raise BindingError('PARTIAL_PRE_NO_RESEND:' + str(call_dir))
    logical = read_json(call_dir / 'logical_call.json')
    for key, value in expected.items():
        if logical.get(key) != value:
            raise BindingError('PRE_LOGICAL_IDENTITY:' + key)
    if logical.get('terminal_method_status') != 'ACCEPTED':
        raise BindingError('PRE_TERMINAL_NOT_ACCEPTED_NO_RESEND:' + str(logical.get('terminal_method_status')))
    value = read_json(call_dir / 'validated_artifact.json')
    finalized = finalizer(value)
    if finalized != value:
        raise BindingError('PRE_ARTIFACT_IDENTITY_DRIFT')
    return finalized


def require_refs(binding, names):
    missing = [name for name in names if name not in binding.get('refs', {})]
    if missing:
        raise BindingError('REGISTERED_MATERIALIZATION_MISSING:' + ','.join('/refs/' + x for x in missing))
    return {name: read_ref(binding['refs'][name]) for name in names}
