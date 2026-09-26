"""Exact Analyzer -> PRE -> native H4.4 execution adapter, called by either operation."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import os
from pathlib import Path
from unittest.mock import patch

from exact_bindings import (BindingError, read_json, read_ref, require_refs, immutable_json,
                            file_ref, digest, build_from_index)
from reuse import load_cores
from local_stage import materialize_local, prepare_groups
from group_stage import run_group_tail
from pre_stage import run_pre
from h44_input import materialize_capture, run_h44


REQUIRED_REFS = ('request', 'handoff', 'global_terminal', 'universe', 'cohort', 'bundle_index',
                 'runtime_manifest', 'experiment_contract', 'role_authority', 'analyzer_token_contract',
                 'f0f1_protocol', 'actor_runtime', 'memory_runtime', 'train_update_manifest')


def describe_required_bindings():
    return {'source': 'current typed output index /refs merged with authorized operation /refs',
        'required_refs': list(REQUIRED_REFS),
        'researcher_memory': 'exact /refs/researcher_view or finite /refs/researcher_views[]',
        'directories': ['state_root', 'scientific_repo_root', 'analyzer_snapshot_directory', 'train_root'],
        'packages': ['q', 'u', 'x', 'h44'],
        'package_contract': {'root': 'absolute registered source directory',
                             'manifest': {'path': 'PACKAGE_FILES.sha256', 'file_sha256': 'registered file SHA'}},
        'optional': ['campaign_startup_authority', 'bounded_pre_recovery_authority'],
        'top_level_operation_count_changed': False}


@contextmanager
def exclusive_owner(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'ANALYZER_ADAPTER.lock').open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            if stream.tell() == 0:
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise BindingError('ANALYZER_ADAPTER_ALREADY_ACTIVE') from exc
            try:
                yield
            finally:
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise BindingError('ANALYZER_ADAPTER_ALREADY_ACTIVE') from exc
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def validate_binding(binding):
    if binding.get('schema_id') != 'FORMAL_ANALYZER_PRE_EXECUTION_BINDING_V1_6':
        raise BindingError('ANALYZER_BINDING_SCHEMA')
    refs = dict(binding['refs'])
    # TRAIN_UPDATE is JSONL and is verified by native H4.4; do not parse it as one JSON object.
    values = require_refs(binding, [x for x in REQUIRED_REFS if x != 'train_update_manifest'])
    if 'train_update_manifest' not in refs:
        raise BindingError('REGISTERED_MATERIALIZATION_MISSING:/refs/train_update_manifest')
    read_ref(refs['train_update_manifest'], as_bytes=True)
    if 'researcher_view' in refs:
        values['researcher_view'] = read_ref(refs['researcher_view'])
    elif not isinstance(refs.get('researcher_views'), list) or not refs['researcher_views']:
        raise BindingError('REGISTERED_MATERIALIZATION_MISSING:/refs/researcher_view(s)')
    req = values['request']; rid = binding['round_id']; pid = binding['parent_policy_id']
    for name in ('request', 'handoff'):
        if values[name].get('round_id') != rid or values[name].get('parent_policy_id') != pid:
            raise BindingError('ROUND_POLICY_BINDING:' + name)
    handoff = values['handoff']
    if Path(handoff['rollout_request_path']).resolve() != Path(refs['request']['path']).resolve():
        raise BindingError('HANDOFF_REQUEST_PATH_MISMATCH')
    if handoff['rollout_request_sha256'] != refs['request']['file_sha256']:
        raise BindingError('HANDOFF_REQUEST_SHA_MISMATCH')
    for name, field in [('actor_runtime', 'policy_runtime_binding_sha256'),
                        ('memory_runtime', 'round_memory_runtime_authority_sha256'),
                        ('train_update_manifest', 'train_update_manifest_sha256')]:
        if refs[name]['file_sha256'] != req[field]:
            raise BindingError('REQUEST_FILE_BINDING:' + name)
    memory = values['memory_runtime']
    for field, reqfield in [('active_snapshot_sha256', 'round_start_memory_snapshot_sha256'),
                            ('token_budget_contract_sha256', 'token_budget_contract_sha256')]:
        if memory.get(field) != req[reqfield]:
            raise BindingError('CURRENT_MEMORY_BINDING:' + field)
    # Read-only Memory objects need no invented round_id.
    if values['analyzer_token_contract'].get('contract_sha256') != req['token_budget_contract_sha256']:
        raise BindingError('TOKEN_CONTRACT_IDENTITY')
    authority = values['role_authority']
    if authority.get('strong_primary_fresh_round_execution_authorized') is not True or not {
            'ANALYZER', 'RESEARCH_PLANNER_PRE', 'RESEARCH_PLANNER_POST'} <= set(authority.get('strong_primary_roles', [])):
        raise BindingError('STRONG_PRIMARY_ROLE_AUTHORITY_MISSING')
    # Source state refs must address the finite protocol paths under the bound producer.
    state = Path(binding['state_root']).absolute()
    for name, filename in [('handoff', 'ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'),
        ('global_terminal', 'PCHSI_V1232K_GLOBAL_TERMINAL_V1.json'),
        ('universe', 'ROUND_ROLLOUT_UNIVERSE_SEAL_V1.json'),
        ('cohort', 'ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1.json'),
        ('bundle_index', 'ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1.json')]:
        if Path(refs[name]['path']).resolve() != (state / 'round_evidence' / filename).resolve():
            raise BindingError('PRODUCER_TYPED_PATH_MISMATCH:' + name)
    return values


def run_bound_round(binding_path, output_root=None, execute=False, *, core=None):
    """One execution path for first-round and resident bindings.

    execute=False performs exact reference checks and materializes local inputs;
    execute=True invokes existing scientific engines, then original H4.4.
    No success receipt is emitted when any stage is incomplete.
    """
    binding = read_json(Path(binding_path).absolute()) if not isinstance(binding_path, dict) else dict(binding_path)
    if output_root is not None:
        binding['output_root'] = str(Path(output_root).absolute())
    out = Path(binding['output_root']).absolute()
    with exclusive_owner(out):
        immutable_json(out / 'EXACT_ANALYZER_OPERATION_INPUT.json', binding)
        values = validate_binding(binding)
        core = core or load_cores(binding)
        runtime = values['runtime_manifest']
        if runtime['runtime_manifest_sha256'] != core.domain_hash('UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1',
                                                               runtime, excluded_field='runtime_manifest_sha256'):
            raise BindingError('RUNTIME_MANIFEST_DOMAIN_HASH')
        binding['_request'] = values['request']
        local = out / 'local'; group = out / 'group'; pre = out / 'pre'
        registry = materialize_local(binding, values, core, local)
        if not execute:
            return {'status': 'ANALYZER_LOCAL_REGISTRY_MATERIALIZED_NO_EXECUTION',
                    'registry': file_ref(registry), 'scientific_execution_started': False}
        campaign = None
        if binding.get('campaign_startup_authority'):
            from pchsi.round_control.campaign_authority import CampaignStartupAuthorityV1
            campaign = CampaignStartupAuthorityV1.from_dict(read_ref(binding['campaign_startup_authority']))
        with ExitStack() as stack:
            stack.enter_context(patch.object(core.rr, 'load_runtime_manifest', lambda *a, **k: runtime))
            stack.enter_context(patch.object(core.orch, 'load_runtime_manifest', lambda *a, **k: runtime))
            execution, rc = core.runner.run_registry(registry_path=registry,
                output_root=local / 'strong_local_runtime', campaign_authority=campaign)
            if rc != 0 or execution.get('terminal_route') is not None:
                raise BindingError('LOCAL_RUNTIME_TYPED_GLOBAL_STOP:' + str(execution.get('terminal_route')))
            prepared, accesses, sources = prepare_groups(binding, core, local, execution)
            tail, universe = run_group_tail(binding, values, core, prepared, accesses, group)
        accepted, handoff = run_pre(binding, values, core, tail, universe, pre)
        if not handoff['selected_states']:
            # Existing H4.4 explicitly cannot turn zero verified pairs into no-train.
            raise BindingError('REGISTERED_ZERO_SELECTED_PRE_GOVERNANCE_MATERIALIZATION_REQUIRED')
        capture = materialize_capture(binding, values, core, pre, accepted, handoff, sources, out / 'h44')
        terminal = run_h44(binding, capture, out / 'h44', execute=True)
        value = read_ref(terminal)
        result = {'schema_id': 'EXACT_ANALYZER_PRE_H44_EXECUTION_RESULT_V1_6',
            'round_id': binding['round_id'], 'parent_policy_id': binding['parent_policy_id'],
            'status': value['status'], 'accepted_pre': file_ref(pre / 'ACCEPTED_PRE_REF.json'),
            'h44_capture': capture, 'h44_terminal': terminal, 'full_campaign_closed': False,
            'training_execution_count': value.get('training_execution_count', 0)}
        immutable_json(out / 'ANALYZER_PRE_H44_RESULT.json', result)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    result = run_bound_round(args.binding, args.output_root, args.execute)
    print(result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
