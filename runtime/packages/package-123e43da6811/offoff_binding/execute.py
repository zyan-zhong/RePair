"""Invoke the existing native cell runner and audits; no evaluation algorithm."""
from __future__ import annotations
from functools import partial
import importlib.metadata
import importlib.util
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time

from continuity_binding.api import (ContinuityError, canonical, read_ref,
    read_bytes_ref, regular_path, write_once)
from .materialize import prepare, materialize, server_command, need
from .native import Native


def require_resumable_cell(state):
    """Publication can be adopted; uncertain execution cannot be blindly resent."""
    unresolved = ('started_only_attempt_ids', 'terminal_without_publish_attempt_ids',
                  'staged_without_publish_attempt_ids')
    need(not any(state[name] for name in unresolved), 'OFFOFF_INTERRUPTED_CELL_NO_BLIND_RETRY')
    if not state['published_attempt_ids']:
        need(state['next_attempt_ordinal'] == 0, 'OFFOFF_UNREGISTERED_RETRY')


def registered_decision_source(rule):
    """Resolve a registered implementation in this package or an exact asset."""
    producer = rule.get('decision_producer')
    need(isinstance(producer, dict), 'FROZEN_PROMOTION_DECISION_PRODUCER_REQUIRED')
    if 'source_member' in producer:
        need('source_ref' not in producer, 'AMBIGUOUS_PROMOTION_SOURCE')
        member = PurePosixPath(producer['source_member'])
        need(not member.is_absolute() and '..' not in member.parts and
             '\\' not in producer['source_member'] and ':' not in producer['source_member']
             and member.suffix == '.py', 'PROMOTION_SOURCE_MEMBER_INVALID')
        source = {'path': str(Path(__file__).resolve().parents[1] / member),
                  'sha256': producer['sha256']}
    else:
        source = producer['source_ref']
    return source


def _registered_decider(native, rule):
    source = registered_decision_source(rule)
    producer = rule['decision_producer']
    need(native.sources.get(source['path']) == source, 'PROMOTION_PRODUCER_NOT_REGISTERED')
    read_bytes_ref(source)
    entrypoint = producer['entrypoint']
    need(isinstance(entrypoint, str) and entrypoint.isidentifier() and not entrypoint.startswith('_'),
         'EXACT_PROMOTION_ENTRYPOINT_REQUIRED')
    module_name = '_registered_current_offoff_decider_' + source['sha256']
    spec = importlib.util.spec_from_file_location(module_name, source['path'])
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if 'source_member' in producer:
        module.validate_rule(rule)
    result = getattr(module, entrypoint)
    need(callable(result), 'REGISTERED_PROMOTION_ENTRYPOINT_NOT_CALLABLE')
    return result


def freeze_registered_promotion(*, native, protocol, aggregate, summary_ref, parent, candidate):
    """Execute only the rule producer frozen before OFF/OFF and use native closeout."""
    from pchsi.round_control.promotion import freeze_promotion_decision
    need(read_ref(summary_ref) == aggregate, 'PROMOTION_AGGREGATE_BYTES_CHANGED')
    rule = read_ref(protocol['promotion_rule_ref'])
    verdict = _registered_decider(native, rule)(frozen_rule=rule, aggregate=aggregate)
    need(isinstance(verdict, dict) and set(verdict) == {'decision', 'decision_rule_id'},
         'NATIVE_REGISTERED_PROMOTION_VERDICT_REQUIRED')
    need(verdict['decision_rule_id'] == rule['decision_rule_id'], 'FROZEN_PROMOTION_RULE_IDENTITY')
    need(verdict['decision'] in {'PROMOTE', 'ROLLBACK'}, 'ROUND_TERMINAL_REQUIRES_PROMOTE_OR_ROLLBACK')
    return freeze_promotion_decision(round_id=aggregate['round_id'], **verdict,
        evidence_access_class='TRAIN_SELECT', evidence_sha256=summary_ref['sha256'],
        parent_policy_id=parent['policy_id'], candidate_policy_id=candidate['policy_id'])


def _audit_one(*, audit, native_audit, loaded, row, expected, bundle, protocol, infra, access, root):
    condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha = bundle
    audit.audit_loaded_cell(native=native_audit, loaded=loaded, row=row, expected=expected,
        condition=condition, runtime=runtime, runtime_sha=runtime_sha,
        request_sha=protocol['policy_request_schema_sha256'])
    episode = loaded.episode_artifact
    task = access.records[episode.task_index]
    checks = {'task_access_manifest_sha256': protocol['task_access_ref']['sha256'],
        'gamefile_identity_manifest_sha256': infra['gamefile_identity_ref']['sha256'],
        'environment_runtime_manifest_sha256': infra['environment_runtime_ref']['sha256'],
        'gamefile_sha256': task.gamefile_sha256, 'gamefile_sha1': task.gamefile_sha1,
        'raw_protocol_sha256': protocol['raw_protocol_sha256'],
        'evaluator_commit': protocol['evaluator_commit'], 'runtime_core_commit': protocol['runtime_core_commit'],
        'design_merge_commit': protocol['design_merge_commit']}
    for key, value in checks.items():
        need(getattr(episode, key) == value, 'OFFOFF_EPISODE_UPSTREAM_IDENTITY:' + key)
    return audit.audit_publication_metadata(native=native_audit, evaluator_root=root, row=row, loaded=loaded)


def execute_binding(binding_ref, *, host, port, readiness_timeout_seconds=600.0, _worker=None):
    """Run inside the owner's authorized allocation. Never submits a GPU job.

    The child vLLM process belongs to this invocation, and both native arms use
    its content-verified static registry. Existing external aliases are not used.
    """
    need(os.name == 'posix', 'OFFOFF_LIVE_REQUIRES_REGISTERED_LINUX_RUNTIME')
    import fcntl
    from pchsi.evaluation.select_execution_identity import (
        build_select_i1_execution_profile, validate_select_execution_profile_binding)
    from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
    from pchsi.evaluation.budget import BudgetLimits

    binding = read_ref(binding_ref)
    need(binding['schema_id'] == 'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1', 'OFFOFF_BINDING_SCHEMA')
    native = Native.load(binding['native_repo_root'], binding['source_refs'])
    context = prepare(native=native, **binding['input_refs'])
    sink = Path(binding_ref['path']).parent
    need(materialize(native=native, **binding['input_refs'], sink=sink) == binding_ref,
         'OFFOFF_CURRENT_MATERIALIZATION_DRIFT')
    rule = read_ref(context['protocol']['promotion_rule_ref'])
    _registered_decider(native, rule)  # Resolve the frozen producer before seeing outcomes.
    live, audit, aggregate, server, types, loader = native.runners()
    audit_native = audit.load_native(native.root)
    need(importlib.metadata.version('vllm') == context['server'].vllm_version, 'OFFOFF_VLLM_VERSION')
    live.BASE_MODEL_PATH = Path(context['base']['artifact_root'])
    live.TASK_ACCESS_SHA256 = context['protocol']['task_access_ref']['sha256']
    live.CURRENT_RUN_NAMESPACE = 'formal-offoff-' + context['start']['request_sha256'][:24]
    i1_sha = context['protocol']['policy_request_schema_sha256']
    types['build_select_execution_profile'] = lambda identity: build_select_i1_execution_profile(
        identity, request_contract_sha256=i1_sha)
    types['validate_select_execution_profile_binding'] = lambda *, identity, profile: validate_select_execution_profile_binding(
        identity=identity, profile=profile, expected_request_schema_sha256=i1_sha)
    types['EpisodeExecutionConfig'] = partial(types['EpisodeExecutionConfig'],
        budget_limits=BudgetLimits(**context['protocol']['episode_budget']))
    schedules = {label: bundle[2] for label, bundle in context['bundles'].items()}
    expected = derive_expected_select_cells_from_master_schedules(schedules=schedules,
        authorized_schedule_sha256={label: b[5] for label, b in context['bundles'].items()})
    expected_map = {(cell.schedule_name, cell.condition_cell_id): cell for cell in expected}
    preflight = dict(environment_runtime_manifest_sha256=context['infra']['environment_runtime_ref']['sha256'],
        gamefile_identity_manifest_sha256=context['infra']['gamefile_identity_ref']['sha256'],
        base_model_revision=context['server'].base_model_revision,
        chat_template_sha256=context['server'].chat_template_sha256,
        policy_request_schema_sha256=i1_sha,
        **{k: context['protocol'][k] for k in ('evaluator_commit', 'design_merge_commit',
                                             'runtime_core_commit', 'raw_protocol_sha256')})
    execution = regular_path(binding['execution_root'] if _worker is None else _worker['execution_root'])
    execution.mkdir(parents=True, exist_ok=True)
    ordinals = tuple(range(binding['paired_cell_count'])) if _worker is None else tuple(_worker['ordinals'])
    need(len(set(ordinals)) == len(ordinals) and all(type(n) is int and 0 <= n < binding['paired_cell_count'] for n in ordinals),
         'OFFOFF_WORKER_ORDINALS_INVALID')
    runtime_sink = sink if _worker is None else regular_path(_worker['runtime_sink'])
    runtime_sink.mkdir(parents=True, exist_ok=True)
    # These globals are native readiness helpers only; evaluation identities remain native objects.
    server.PARENT_CHECKPOINT_ID = context['bundles']['parent'][1].served_model_name
    server.CANDIDATE_CHECKPOINT_ID = context['bundles']['candidate'][1].served_model_name
    command = server_command(context, host=host, port=port)
    lockfd = os.open(runtime_sink / 'OFFOFF_WRITER.lock', os.O_CREAT | os.O_RDWR, 0o600)
    process = None
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Reject ambiguous existing cells before starting a new server.
        for label, bundle in context['bundles'].items():
            for ordinal in ordinals:
                cell = bundle[2].cells[ordinal]
                state = live.audit_cell_attempt_state(evaluator_root=execution / label / 'evaluator_run',
                                                     scheduled_cell_id=cell.condition_cell_id)
                require_resumable_cell(state)
        write_once(runtime_sink / 'SERVER_INVOCATION.json', {'schema_id': 'CURRENT_OFFOFF_SERVER_INVOCATION_V1',
            'binding_ref': binding_ref, 'argv': command, 'server_runtime': context['server'].to_dict()})
        stop_before = None if _worker is None else time.monotonic() + _worker['worker_budget_seconds']
        graceful_partial = False
        with (runtime_sink / 'vllm.log').open('ab') as log:
            from rollout_adapter.endpoint_lease import launch_with_lease
            process, base_url = launch_with_lease(command, output_root=runtime_sink,
                stdout=log, stderr=subprocess.STDOUT)
            server.wait_for_server(base_url=base_url, process=process, timeout_seconds=readiness_timeout_seconds)
            # Health/model names are not weight authority: real files were checked above.
            server.probe_registered_models(base_url=base_url)
            audits = []
            for ordinal in ordinals:
                # Preserve native Stage4D's paired stop boundary, including finishing
                # the second arm if an earlier graceful run published only one arm.
                done = [context['bundles'][label][2].cells[ordinal].condition_cell_id in
                    {row['condition_cell_id'] for row in live.load_receipts(execution / label / 'cell_receipts.jsonl')}
                    for label in ('parent','candidate')]
                if stop_before is not None and time.monotonic() >= stop_before and done[0] == done[1]:
                    graceful_partial = True
                    break
                for label in ('parent', 'candidate'):
                    need(process.poll() is None, 'OWNED_OFFOFF_SERVER_EXITED')
                    bundle = context['bundles'][label]
                    condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha = bundle
                    cell = schedule.cells[ordinal]
                    evaluator = execution / label / 'evaluator_run'
                    state = live.audit_cell_attempt_state(evaluator_root=evaluator, scheduled_cell_id=cell.condition_cell_id)
                    require_resumable_cell(state)
                    row = live._recover_or_execute_cell(label=label, cell=cell,
                        task_access_record=context['access'].records[cell.manifest_index], condition=condition,
                        runtime=runtime, condition_sha=condition_sha, runtime_sha=runtime_sha, schedule_sha=schedule_sha,
                        preflight=preflight, base_url=base_url, types=types, attempt_auditor=loader,
                        condition_root=execution / label)
                    loaded = loader.load_attempt_directory_v1(evaluator / 'attempts' / row['execution_attempt_id'])
                    metadata = _audit_one(audit=audit, native_audit=audit_native, loaded=loaded, row=row,
                        expected=expected_map[(label, cell.condition_cell_id)], bundle=bundle,
                        protocol=context['protocol'], infra=context['infra'], access=context['access'], root=evaluator)
                    audits.append({'label': label, 'ordinal': ordinal, 'execution_attempt_id': row['execution_attempt_id'],
                                   'attempt_bundle_sha256': row['attempt_bundle_sha256'], **metadata})
        if _worker is not None:
            counts = {}
            for label in ('parent','candidate'):
                rows = live.load_receipts(execution / label / 'cell_receipts.jsonl')
                assigned = {context['bundles'][label][2].cells[n].condition_cell_id for n in ordinals}
                ids = [row['condition_cell_id'] for row in rows]
                need(len(ids) == len(set(ids)) and set(ids) <= assigned, 'OFFOFF_SHARD_RECEIPT_GRID')
                counts[label] = len(rows)
            return {'assigned_pair_count':len(ordinals), 'parent_cell_count':counts['parent'],
                'candidate_cell_count':counts['candidate'], 'graceful_partial':graceful_partial,
                'complete':counts['parent'] == counts['candidate'] == len(ordinals)}
        return finalize_binding(binding_ref)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=30)
        os.close(lockfd)


def finalize_binding(binding_ref, *, execution_roots_by_ordinal=None):
        """Read-only original cell audit then complete-grid native aggregation.

        execution_roots_by_ordinal is emitted by the registered partition adapter.
        No server, episode, missing-cell retry or partial-result decision runs here.
        """
        from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
        binding = read_ref(binding_ref)
        need(binding['schema_id'] == 'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1', 'OFFOFF_BINDING_SCHEMA')
        native = Native.load(binding['native_repo_root'], binding['source_refs'])
        context = prepare(native=native, **binding['input_refs'])
        sink = Path(binding_ref['path']).parent
        need(materialize(native=native, **binding['input_refs'], sink=sink) == binding_ref,
             'OFFOFF_CURRENT_MATERIALIZATION_DRIFT')
        _registered_decider(native, read_ref(context['protocol']['promotion_rule_ref']))
        live, audit, aggregate, _, _, loader = native.runners()
        audit_native = audit.load_native(native.root)
        expected = derive_expected_select_cells_from_master_schedules(
            schedules={label:bundle[2] for label,bundle in context['bundles'].items()},
            authorized_schedule_sha256={label:bundle[5] for label,bundle in context['bundles'].items()})
        expected_map = {(cell.schedule_name,cell.condition_cell_id):cell for cell in expected}
        roots = ([binding['execution_root']] * binding['paired_cell_count'] if execution_roots_by_ordinal is None
                 else list(execution_roots_by_ordinal))
        need(len(roots) == binding['paired_cell_count'], 'OFFOFF_FINALIZE_ROOT_GRID')
        receipts = {}
        for root in dict.fromkeys(roots):
            for label in ('parent','candidate'):
                values = live.load_receipts(regular_path(root) / label / 'cell_receipts.jsonl')
                ids = [row['condition_cell_id'] for row in values]
                need(len(ids) == len(set(ids)), 'OFFOFF_DUPLICATE_PUBLISHED_CELL')
                allowed = {context['bundles'][label][2].cells[n].condition_cell_id
                           for n, owned in enumerate(roots) if owned == root}
                need(set(ids) == allowed, 'OFFOFF_COMPLETE_ASSIGNED_GRID_REQUIRED')
                receipts[(root,label)] = dict(zip(ids,values))
        rows, audits = {'parent':[], 'candidate':[]}, []
        for ordinal, root in enumerate(roots):
            for label, bundle in context['bundles'].items():
                cell = bundle[2].cells[ordinal]
                row = receipts[(root,label)][cell.condition_cell_id]
                evaluator = regular_path(root) / label / 'evaluator_run'
                loaded = loader.load_attempt_directory_v1(evaluator / 'attempts' / row['execution_attempt_id'])
                metadata = _audit_one(audit=audit,native_audit=audit_native,loaded=loaded,row=row,
                    expected=expected_map[(label,cell.condition_cell_id)],bundle=bundle,
                    protocol=context['protocol'],infra=context['infra'],access=context['access'],root=evaluator)
                rows[label].append(row)
                audits.append({'label':label,'ordinal':ordinal,'execution_attempt_id':row['execution_attempt_id'],
                    'attempt_bundle_sha256':row['attempt_bundle_sha256'],**metadata})
        # All scientific rows must be present and have passed the original audit.
        for label, bundle in context['bundles'].items():
            audit.check_receipt_grid(rows[label], [c.to_dict() for c in bundle[2].cells],
                                     condition_id=bundle[0].policy_condition_id)
        paired = aggregate(parent_receipts=rows['parent'], candidate_receipts=rows['candidate'],
            expected_task_count=len(context['access'].records), expected_seeds=tuple(context['protocol']['replicate_seeds']))
        # Preserve native numeric computation, while retaining its historical metadata in restricted evidence.
        paired_ref = write_once(sink / 'restricted' / 'NATIVE_PAIRED_RESULTS.json', paired)
        audit_ref = write_once(sink / 'restricted' / 'NATIVE_IDENTITY_AUDIT.json',
                               {'schema_id': 'CURRENT_OFFOFF_IDENTITY_AUDIT_V1', 'binding_ref': binding_ref,
                                'execution_roots_by_ordinal':roots, 'rows': audits})
        fields = ('unique_task_count', 'replicate_seeds', 'paired_cell_count', 'total_condition_cell_count',
                  'parent_success_cells', 'candidate_success_cells', 'both_success_cells', 'both_failure_cells',
                  'parent_only_success_cells', 'candidate_only_success_cells', 'mean_task_success_rate_delta')
        summary = {name: paired[name] for name in fields}
        summary.update(schema_id='CURRENT_TRAIN_SELECT_AGGREGATE_V1', round_id=context['start']['round_id'],
            request_sha256=context['start']['request_sha256'], parent_policy_id=context['parent']['policy_id'],
            candidate_policy_id=context['candidate']['policy_id'], memory_state='OFF', harness_state='OFF',
            primary_statistical_unit='unique_task', replicates_are_not_independent_tasks=True,
            evidence_access_class='TRAIN_SELECT', benchmark_feedback_used=False,
            frozen_protocol_ref=binding['input_refs']['protocol_ref'], identity_audit_ref=audit_ref,
            native_paired_results_ref=paired_ref)
        summary_ref = write_once(sink / 'TRAIN_SELECT_AGGREGATE.json', summary)
        decision = freeze_registered_promotion(native=native, protocol=context['protocol'], aggregate=summary,
            summary_ref=summary_ref, parent=context['parent'], candidate=context['candidate'])
        decision_ref = write_once(sink / 'PROMOTION_DECISION.json', decision.to_dict())
        # Recheck all frozen inputs after execution before publishing the terminal.
        prepare(native=native, **binding['input_refs'])
        terminal = dict(schema_id='CURRENT_NATIVE_OFFOFF_TERMINAL_V1', round_id=context['start']['round_id'],
            request_sha256=context['start']['request_sha256'], binding_ref=binding_ref, summary_ref=summary_ref,
            promotion_ref=decision_ref, outcome='PROMOTED' if decision.decision == 'PROMOTE' else 'ROLLED_BACK',
            next_parent_policy_id=decision.next_parent_policy_id,
            next_parent_policy_artifact_sha256=(context['candidate'] if decision.decision == 'PROMOTE' else context['parent'])['artifact_sha256'],
            human_scientific_decision_count=0, benchmark_feedback_used=False)
        return write_once(sink / 'CURRENT_NATIVE_OFFOFF_TERMINAL.json', terminal)


def validate_completed_offoff_terminal(terminal_ref):
    """Re-audit the persisted actual evaluation; no server or environment calls."""
    terminal = read_ref(terminal_ref)
    need(terminal.get('schema_id') == 'CURRENT_NATIVE_OFFOFF_TERMINAL_V1', 'OFFOFF_TERMINAL_SCHEMA')
    summary = read_ref(terminal['summary_ref'])
    audit = read_ref(summary['identity_audit_ref'])
    need(audit.get('schema_id') == 'CURRENT_OFFOFF_IDENTITY_AUDIT_V1' and
         audit.get('binding_ref') == terminal['binding_ref'], 'OFFOFF_TERMINAL_AUDIT_BINDING')
    observed = finalize_binding(terminal['binding_ref'],
        execution_roots_by_ordinal=audit['execution_roots_by_ordinal'])
    need(observed == terminal_ref, 'OFFOFF_RECOVERED_NATIVE_TERMINAL_MISMATCH')
    return True
