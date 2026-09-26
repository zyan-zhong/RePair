"""Exact deployment checks for the already-authorized Formal campaign."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def _raw(ref):
    path = Path(ref['path'])
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('REGISTERED_FILE_UNAVAILABLE:' + str(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise ValueError('REGISTERED_FILE_SHA_MISMATCH:' + str(path))
    return raw


def verify_package(root):
    root = Path(root).absolute()
    manifest = root / 'PACKAGE_FILES.sha256'
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('PACKAGE_SOURCE_MANIFEST_REQUIRED')
    raw = manifest.read_bytes(); seen = set()
    for line in raw.decode('utf8').splitlines():
        if not line.strip():
            continue
        sha, name = line.split(maxsplit=1); name = name.lstrip('*')
        member = PurePosixPath(name)
        if member.is_absolute() or '..' in member.parts or '\\' in name or name in seen:
            raise ValueError('PACKAGE_MEMBER_INVALID:' + name)
        seen.add(name)
        _raw({'path': str(root / name), 'sha256': sha})
    return hashlib.sha256(raw).hexdigest(), len(seen)


def validate_deployment(deployment, *, formal_root, bundle_root):
    identity, count = verify_package(bundle_root)
    if deployment['entry_source_sha256'] != identity:
        raise ValueError('DEPLOYMENT_ENTRY_SOURCE_CHANGED')
    for name, sha in deployment['formal_files'].items():
        _raw({'path': str(Path(formal_root) / name), 'sha256': sha})
    repo = Path(deployment['scientific_repo_root'])
    registration = deployment['training_source_registration']
    head = registration['repo_head']
    for relative, expected in registration['source_files'].items():
        raw = _raw({'path': str(repo / relative), 'sha256': expected})
        blob = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', head + ':' + relative],
                              capture_output=True, check=False)
        if blob.returncode or blob.stdout != raw:
            raise ValueError('REGISTERED_NATIVE_GIT_BLOB_CHANGED:' + relative)
    for name in ('dual_adapter', 'operational_request_ref'):
        _raw(registration[name])
    for path, sha in registration['binding_source_files'].items():
        _raw({'path': path, 'sha256': sha})
    offoff = deployment['offoff_source_registration']
    for row in offoff['source_refs']:
        _raw(row)
    for row in offoff['assets'].values():
        _raw(row)
    _raw(offoff['code_source_ref'])
    # No outcome-contingent scientific choices may first be invented after a
    # candidate is trained. A missing frozen rule is reported precisely here.
    if deployment.get('promotion_rule_ref') is None:
        raise ValueError('FORMAL_PROMOTION_RULE_MATERIALIZATION_MISSING:registered native promotion.py '
                         'freezes a provided decision; the old diagnostic rollback rule is not a Formal criterion')
    if deployment['promotion_rule_ref'] != offoff.get('promotion_rule_ref'):
        raise ValueError('FORMAL_PROMOTION_PREFLIGHT_EXECUTION_RULE_MISMATCH')
    rule = json.loads(_raw(deployment['promotion_rule_ref']))
    if (rule.get('schema_id') != 'FROZEN_TRAIN_SELECT_PROMOTION_RULE_V1'
            or rule.get('frozen_before_outcomes') is not True
            or rule.get('evidence_access_class') != 'TRAIN_SELECT'):
        raise ValueError('FORMAL_PROMOTION_RULE_AUTHORITY_INVALID')
    from offoff_binding.execute import registered_decision_source
    source = registered_decision_source(rule)
    _raw(source)
    offoff = deployment['offoff_source_registration']
    if source not in offoff['source_refs']:
        raise ValueError('FORMAL_PROMOTION_PRODUCER_NOT_REGISTERED')
    if 'source_member' in rule['decision_producer']:
        from offoff_binding.promotion_rule import validate_rule
        validate_rule(rule)
        original = json.loads(_raw(offoff['assets']['historical_protocol']))
        if (rule['expected_task_count'] != original['grid']['task_count']
                or rule['replicate_seeds'] != original['grid']['replicate_seeds']
                or rule['registered_select_task_access_sha256'] != offoff['assets']['task_access']['sha256']):
            raise ValueError('PROMOTION_RULE_REGISTERED_SELECT_GRID_CHANGED')
    return {'package_file_count': count, 'entry_source_sha256': identity,
            'scientific_execution_started': False}
