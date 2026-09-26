"""Materialize installation locators from the finite, reviewed source registry."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from .preflight import _raw


def build_deployment(bundle_root, *, entry_source_sha256):
    root = Path(bundle_root).absolute()
    template = json.loads((root / 'EXECUTION_SOURCE_REGISTRY.json').read_bytes())
    if template.get('schema_id') != 'FORMAL_REGISTERED_EXECUTION_SOURCE_REGISTRY_V1':
        raise ValueError('EXECUTION_SOURCE_REGISTRY_SCHEMA')

    def installed(row):
        member = PurePosixPath(row['member'])
        if (member.is_absolute() or '..' in member.parts or '\\' in row['member']
                or ':' in row['member']):
            raise ValueError('REGISTERED_PACKAGE_MEMBER_INVALID')
        ref = {'path': str(root / member), 'sha256': row['sha256']}
        _raw(ref)
        return ref

    capture = json.loads(_raw(installed(template['capture'])))
    plan = json.loads(_raw(installed(template['source_plan'])))
    ready = json.loads(_raw(installed(template['ready'])))
    gate2 = json.loads(_raw(installed(template['gate2'])))
    rows = [r for r in gate2['manifest'] if r['kind'] == 'git_relevant_sources_archive']
    if len(rows) != 1:
        raise ValueError('REGISTERED_SCIENTIFIC_REPO_NOT_UNIQUE')
    repo = Path(rows[0]['source_path'])
    if (capture['formal_state_root'] not in plan['protected_roots']
            or capture['repo']['head'] != template['native_commit']):
        raise ValueError('REGISTERED_FORMAL_SOURCE_IDENTITY_CONFLICT')
    formal_files = json.loads(_raw(installed(template['authority_members'])))['files']
    training = dict(template['training'])
    training['repo_head'] = capture['repo']['head']
    training['dual_adapter'] = installed(training.pop('dual_adapter_member'))
    operational = training.pop('operational_request_relative')
    training['operational_request_ref'] = {'path': str(repo / operational),
                                          'sha256': training['source_files'][operational]}
    training['binding_source_files'] = {installed(row)['path']: row['sha256']
                                        for row in training.pop('binding_members')}
    offoff = dict(template['offoff'])
    offoff['native_repo_root'] = str(repo)
    offoff['source_refs'] = [{'path': str(repo / row['member']), 'sha256': row['sha256']}
                             for row in offoff.pop('native_sources')]
    offoff['source_refs'].extend(installed(row) for row in offoff.pop('binding_members', []))
    offoff['code_source_ref'] = installed(offoff.pop('code_source_member'))
    # These are exact server registrations, not local archive aliases.
    offoff['assets'] = {k: dict(v) for k, v in offoff['assets'].items()}
    rule = template.get('promotion_rule')
    rule_ref = installed(rule) if rule else None
    offoff['promotion_rule_ref'] = rule_ref
    return {'schema_id': 'CURRENT_FORMAL_EXECUTION_DEPLOYMENT_V1',
        'entry_source_sha256': entry_source_sha256,
        'scientific_repo_root': str(repo),
        'formal_state_root': capture['formal_state_root'],
        'formal_files': {row['name']: row['sha256'] for row in formal_files},
        'training_source_registration': training,
        'offoff_source_registration': offoff,
        'promotion_rule_ref': rule_ref,
        'rollout_settings': ready['settings'],
        'candidate_source_registration': {
            'scientific_repo_root': str(repo),
            'source_registration': {'scientific_repo_head': capture['repo']['head']},
            'training_source_registration': training,
            'rollout_capsule_ref': {'path': ready['capsule_path'], 'sha256': ready['capsule_sha256']}},
        'scientific_execution_started': False}
