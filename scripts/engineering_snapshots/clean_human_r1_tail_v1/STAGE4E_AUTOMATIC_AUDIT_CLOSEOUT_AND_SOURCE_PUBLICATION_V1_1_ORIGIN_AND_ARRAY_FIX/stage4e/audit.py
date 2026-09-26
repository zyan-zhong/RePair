"""Read-only glue to existing attempt, SELECT, aggregation and disposition code.

No evaluator, provider, environment or trainer is invoked by this module.
No legacy pilot closeout metadata is copied into the clean reference round.
"""
from __future__ import annotations
from collections import Counter
import fcntl
import importlib
import importlib.util
import os
from pathlib import Path
import sys
from typing import Any
from . import (GateError, canonical, read_json, strict_loads, file_sha, require_file_sha,
               semantic_sha, write_exact, regular, safe_child, validate_completion,
               project_paired_summary, diagnostic_disposition)

LEGACY = 'scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9'
LOADER = 'scripts/memory/materialize_sequence_failure_experience_v1.py'
COMPLETE = 'STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1.json'

def completion_gate(root: Path, cfg: dict) -> dict:
    path = root / COMPLETE
    if not path.is_file():
        raise GateError('COMPLETION_MARKER_MISSING_NO_OUTCOMES_READ')
    value = read_json(path)
    validate_completion(value, auth_sha=cfg['authorization_sha256'], binding_sha=cfg['binding_sha256'],
                        readiness_sha=cfg['readiness_sha256'], pair_count=cfg['pair_count'])
    return value

def validate_train_reference(path: str) -> None:
    parts = {p.lower() for p in Path(path).parts}
    if parts & {'benchmarks', 'benchmark', 'valid_unseen', 'valid_seen'}:
        raise GateError('BENCHMARK_REFERENCE_FORBIDDEN')

def load_native(repo: Path) -> dict[str, Any]:
    regular(repo / LOADER)
    regular(repo / 'src/pchsi/evaluation/select_result_audit.py')
    sys.path.insert(0, str(repo / 'src'))
    sys.path.insert(0, str(repo / LEGACY))
    from pchsi.evaluation.condition_run_schedule import ConditionRunScheduleV1
    from pchsi.evaluation.policy_condition import PolicyConditionManifestV1
    from pchsi.evaluation.select_policy_runtime import SelectPolicyRuntimeManifestV1
    from pchsi.evaluation.distillation_access import TaskAccessManifestV1
    from pchsi.evaluation.distillation_governance import canonical_model_sha256
    from pchsi.evaluation.select_result_audit import (
        derive_expected_select_cells_from_master_schedules,
        audit_select_cell_identity_chain,
    )
    from pchsi.evaluation.schema_models import ScientificCellLockV1, AttemptReceiptV1
    from pchsi.round_control.promotion import freeze_promotion_decision
    from pchsi.round_control.next_round import freeze_next_round_creation
    from pchsi.round_control.attempt_receipts import freeze_stage_attempt_receipt
    from stage0.receipts import load_receipts
    from stage0.result_audit import aggregate_paired_results
    from stage0.attempt_recovery import audit_cell_attempt_state
    spec = importlib.util.spec_from_file_location('_stage4e_frozen_attempt_loader', repo / LOADER)
    if spec is None or spec.loader is None:
        raise GateError('ATTEMPT_LOADER_IMPORT_FAILED')
    loader = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loader
    spec.loader.exec_module(loader)
    return locals()

def check_receipt_grid(rows, cells, *, condition_id: str) -> None:
    if len(rows) != len(cells):
        raise GateError('RECEIPT_GRID_INCOMPLETE')
    for ordinal, (row, cell) in enumerate(zip(rows, cells, strict=True)):
        for key in ('condition_cell_id','manifest_index','task_id','seed'):
            if type(row.get(key)) is not type(cell[key]) or row.get(key) != cell[key]:
                raise GateError(f'RECEIPT_GRID_CHANGED:{ordinal}:{key}')
        if row.get('condition_id') != condition_id:
            raise GateError('RECEIPT_CONDITION_CHANGED')
        if row.get('memory_state') != 'OFF' or row.get('harness_state') != 'OFF':
            raise GateError('RECEIPT_SCAFFOLD_CHANGED')
        if type(row.get('success')) is not bool:
            raise GateError('MISSING_OUTCOME_MUST_NOT_BE_FAILURE')

def audit_loaded_cell(*, native, loaded, row, expected, condition, runtime, runtime_sha, request_sha):
    episode = loaded.episode_artifact
    if (episode.execution_attempt_id != row['execution_attempt_id']
            or loaded.attempt_bundle.attempt_bundle_sha256 != row['attempt_bundle_sha256']
            or episode.success is not row['success']
            or episode.termination_reason != row['termination_reason']):
        raise GateError('RECEIPT_ATTEMPT_BINDING_CHANGED')
    if type(episode.success) is not bool:
        raise GateError('SCIENTIFIC_OUTCOME_MISSING')
    audit_select_cell_identity_chain = native['audit_select_cell_identity_chain']
    audit_select_cell_identity_chain(
        expected_cell=expected, policy_condition=condition, policy_runtime=runtime,
        authorized_policy_runtime_sha256=runtime_sha, policy_calls=loaded.policy_calls,
        trace_provenances=tuple(t.provenance for t in loaded.traces),
        episode_artifact=episode, expected_request_schema_sha256=request_sha,
    )

def audit_publication_metadata(*, native, evaluator_root: Path, row: dict, loaded) -> dict:
    cell = row['condition_cell_id']
    attempt = row['execution_attempt_id']
    audit_cell_attempt_state = native['audit_cell_attempt_state']
    state = audit_cell_attempt_state(evaluator_root=evaluator_root, scheduled_cell_id=cell)
    if state['published_attempt_ids'] != [attempt]:
        raise GateError('NONUNIQUE_OR_MISSING_PUBLISHED_ATTEMPT')
    # Do not turn an unresolved execution into a valid scientific failure.
    if state['started_only_attempt_ids'] or state['staged_without_publish_attempt_ids']:
        raise GateError('UNRESOLVED_ATTEMPT_STATE_REQUIRES_EXISTING_RECOVERY')
    lock_path = safe_child(evaluator_root / 'cell_locks', cell + '.json')
    lock = native['ScientificCellLockV1'].from_json(regular(lock_path).read_bytes())
    ep = loaded.episode_artifact
    checks = {
        'scheduled_cell_id': cell, 'execution_attempt_id': attempt,
        'run_schedule_sha256': ep.condition_run_schedule_sha256,
        'episode_semantic_sha256': ep.episode_semantic_sha256,
        'attempt_bundle_sha256': row['attempt_bundle_sha256'],
        'evaluator_commit': ep.evaluator_commit,
        'scientific_outcome_status': ep.scientific_outcome_status,
        'run_id': ep.run_id,
    }
    for key,value in checks.items():
        if getattr(lock,key) != value:
            raise GateError('PUBLICATION_CELL_LOCK_MISMATCH:' + key)
    started_path = safe_child(evaluator_root / 'attempt_ledger', attempt + '.started.json')
    started = native['AttemptReceiptV1'].from_json(regular(started_path).read_bytes())
    for key,value in {'scheduled_cell_id':cell,'execution_attempt_id':attempt,
                      'run_id':ep.run_id,'run_schedule_sha256':ep.condition_run_schedule_sha256}.items():
        if getattr(started,key) != value:
            raise GateError('STARTED_RECEIPT_MISMATCH:' + key)
    terminal_path = evaluator_root / 'attempt_ledger' / (attempt + '.terminal.json')
    if terminal_path.exists():
        terminal = native['AttemptReceiptV1'].from_json(regular(terminal_path).read_bytes())
        for key,value in checks.items():
            if hasattr(terminal,key) and getattr(terminal,key) != value:
                raise GateError('TERMINAL_RECEIPT_MISMATCH:' + key)
    return {'cell_lock_file_sha256':file_sha(lock_path),'started_receipt_file_sha256':file_sha(started_path),
            'terminal_receipt_file_sha256':file_sha(terminal_path) if terminal_path.exists() else None,
            'other_terminal_attempt_count':len(state['terminal_without_publish_attempt_ids'])}

def takeover_pending(*, round_id: str, next_parent: str, summary_sha: str) -> dict:
    return {
        'schema_id':'STRONG_PRIMARY_ROUND_HANDOFF_V1','schema_version':1,
        'closed_round_id':round_id,'next_parent_policy_id':next_parent,
        'summary_sha256':summary_sha,'input_access':'TRAIN_SELECT_AGGREGATE_ONLY',
        'target_authority_phase':'STRONG_PRIMARY_LOCAL_SHADOW',
        'status':'PENDING_REGISTERED_TAKEOVER_AND_NEXT_ROUND_BINDINGS',
        'routine_human_decisions_required':0,'human_fallback_allowed':False,
        'strong_execution_authorized':False,'local_execution_authorized':False,
        'unresolved_requirements':['REGISTERED_TAKEOVER_METRICS','NEXT_ROUND_RESOURCE_BUDGET',
                                   'STRONG_PRIMARY_ACTOR_BINDING','LOCAL_SHADOW_MODEL_BINDING'],
        'existing_gate':'pchsi.research_intelligence.takeover.evaluate_takeover_gate',
        'existing_role_resolver':'pchsi.round_control.role_authority.resolve_authority_plan',
        'existing_orchestrator':'pchsi.round_control.orchestrator.next_action_for',
        'benchmark_feedback_authorized':False,'per_task_select_data_authorized':False,
        'fresh_autonomous_round_claim_supported':False,
    }

def execute_audit(*, cfg: dict, output: Path, repo: Path, binding: Path, root: Path) -> dict:
    # The completion gate must run before reading any scientific outcome ledger.
    completion = completion_gate(root, cfg)
    native = load_native(repo)
    lock_fd = os.open(regular(root / 'full_select_execution.lock'), os.O_RDONLY)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return _audit_locked(cfg=cfg,output=output,native=native,binding=binding,root=root,completion=completion)
    finally:
        os.close(lock_fd)

def _audit_locked(*, cfg, output, native, binding, root, completion):
    protocol = read_json(Path(cfg['protocol']['path']))
    candidate = read_json(Path(cfg['candidate']['path']))
    identity = read_json(binding / 'BINDING_IDENTITY.json')
    schedules = {}; conditions = {}; runtimes = {}; rows = {}; ledger_hashes = {}
    for label in ('T0','T2'):
        schedules[label] = native['ConditionRunScheduleV1'].from_dict(read_json(binding / f'{label}_CONDITION_RUN_SCHEDULE_V1.json'))
        conditions[label] = native['PolicyConditionManifestV1'].from_dict(read_json(binding / f'{label}_POLICY_CONDITION_MANIFEST_V1.json'))
        runtimes[label] = native['SelectPolicyRuntimeManifestV1'].from_dict(read_json(binding / f'{label}_SELECT_POLICY_RUNTIME_MANIFEST_V1.json'))
        ledger = root / 'execution' / label.lower() / 'cell_receipts.jsonl'
        ledger_hashes[label] = file_sha(ledger)
        rows[label] = native['load_receipts'](ledger)
        check_receipt_grid(rows[label], read_json(binding / f'{label}_CONDITION_RUN_SCHEDULE_V1.json')['cells'],
                           condition_id=conditions[label].policy_condition_id)
    allowed_schedule_hashes = {label:identity['artifacts'][f'{label}_CONDITION_RUN_SCHEDULE_V1.json'] for label in ('T0','T2')}
    expected = native['derive_expected_select_cells_from_master_schedules'](schedules=schedules,authorized_schedule_sha256=allowed_schedule_hashes)
    by_expected = {(e.schedule_name,e.condition_cell_id):e for e in expected}
    access_path = binding / 'CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json'
    access = native['TaskAccessManifestV1'].from_json(regular(access_path).read_bytes())
    by_access = {x.manifest_index:x for x in access.records}
    expected_gamefile_manifest_sha = file_sha(binding / 'CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1.json')
    expected_env_manifest_sha = file_sha(binding / 'ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json')
    audit_rows=[]; secondary={}; provenance_counts=Counter()
    for label in ('T0','T2'):
        evaluator = root / 'execution' / label.lower() / 'evaluator_run'
        attempts = evaluator / 'attempts'
        observed_dirs = {p.name for p in attempts.iterdir() if p.name != '.staging'}
        expected_dirs = {row['execution_attempt_id'] for row in rows[label]}
        if observed_dirs != expected_dirs:
            raise GateError('PUBLISHED_ATTEMPT_UNIVERSE_CHANGED:' + label)
        observed_locks = {p.name for p in (evaluator/'cell_locks').iterdir()}
        if observed_locks != {row['condition_cell_id']+'.json' for row in rows[label]}:
            raise GateError('CELL_LOCK_UNIVERSE_CHANGED:' + label)
        totals=Counter(); reasons=Counter()
        for ordinal,row in enumerate(rows[label]):
            attempt_dir=safe_child(attempts,row['execution_attempt_id'])
            loaded=native['loader'].load_attempt_directory_v1(attempt_dir)
            e=by_expected[(label,row['condition_cell_id'])]
            audit_loaded_cell(native=native,loaded=loaded,row=row,expected=e,
                condition=conditions[label],runtime=runtimes[label],
                runtime_sha=identity['artifacts'][f'{label}_SELECT_POLICY_RUNTIME_MANIFEST_V1.json'],
                request_sha=cfg['request_schema_sha256'])
            ep=loaded.episode_artifact; task=by_access[ep.task_index]
            for key,value in {
                'task_access_manifest_sha256':file_sha(access_path),
                'gamefile_identity_manifest_sha256':expected_gamefile_manifest_sha,
                'environment_runtime_manifest_sha256':expected_env_manifest_sha,
                'gamefile_sha256':task.gamefile_sha256,
                'gamefile_sha1':task.gamefile_sha1,
                'raw_protocol_sha256':conditions[label].raw_protocol_sha256,
                'evaluator_commit':conditions[label].evaluator_commit,
                'runtime_core_commit':conditions[label].runtime_core_commit,
            }.items():
                if getattr(ep,key) != value: raise GateError('EPISODE_UPSTREAM_IDENTITY_MISMATCH:'+key)
            meta=audit_publication_metadata(native=native,evaluator_root=evaluator,row=row,loaded=loaded)
            provenance_counts['other_terminal_attempt_count'] += meta['other_terminal_attempt_count']
            provenance_counts['terminal_receipt_missing_count'] += meta['terminal_receipt_file_sha256'] is None
            totals['environment_steps']+=ep.final_budget.environment_step_count
            totals['policy_attempts']+=ep.final_budget.policy_attempt_count
            totals['protocol_failures']+=ep.final_budget.protocol_failure_count
            totals['inadmissible_actions']+=ep.final_budget.inadmissible_action_count
            totals['valid_executed_actions']+=sum(t.final_action_admissible is True and t.final_executed_action is not None for t in loaded.traces)
            reasons[ep.termination_reason]+=1
            audit_rows.append({'condition':label,'ordinal':ordinal,'execution_attempt_id':row['execution_attempt_id'],
                'attempt_bundle_sha256':row['attempt_bundle_sha256'],'episode_semantic_sha256':ep.episode_semantic_sha256,**meta})
            if (ordinal+1)%100==0: print(f'STAGE4E_IDENTITY_AUDIT_PROGRESS={label}:{ordinal+1}/{len(rows[label])}',flush=True)
        secondary[label]={**dict(totals),'terminal_reason_counts':dict(sorted(reasons.items()))}
    for label in ('T0','T2'):
        require_file_sha(root/'execution'/label.lower()/'cell_receipts.jsonl',ledger_hashes[label])
    audit_report={'schema_id':'CLEAN_SELECT_IDENTITY_AUDIT_V1','schema_version':1,
        'round_id':cfg['round_id'],'status':'PASS','authorization_sha256':cfg['authorization_sha256'],
        'binding_sha256':cfg['binding_sha256'],'source_completion_file_sha256':file_sha(root/COMPLETE),
        'receipt_ledger_file_sha256s':ledger_hashes,'audited_condition_cells':len(audit_rows),
        'missing_cells':0,'duplicate_cells':0,'model_environment_execution_count':0,
        'native_select_audit_reused':True,**dict(provenance_counts),'attempt_audits':audit_rows}
    audit_sha=semantic_sha(audit_report)
    # Reuse the existing numeric aggregator, not its legacy pilot metadata.
    aggregate_paired_results = native['aggregate_paired_results']
    paired=aggregate_paired_results(parent_receipts=rows['T0'],candidate_receipts=rows['T2'],
        expected_task_count=cfg['task_count'],expected_seeds=tuple(cfg['seeds']))
    aggregate=project_paired_summary(paired,round_id=cfg['round_id'],evidence_sha=audit_sha)
    aggregate['secondary']=secondary
    summary_sha=semantic_sha(aggregate)
    disposition=diagnostic_disposition(protocol=protocol,candidate=candidate,delta=aggregate['mean_task_success_rate_delta'])
    decision=native['freeze_promotion_decision'](round_id=cfg['round_id'],decision=disposition['decision'],
        decision_rule_id=disposition['reason'],evidence_access_class='TRAIN_SELECT',evidence_sha256=summary_sha,
        parent_policy_id=candidate['run_manifest']['parent_policy_id'],candidate_policy_id=candidate['candidate_alias'])
    creation=native['freeze_next_round_creation'](closed_round_id=cfg['round_id'],next_round_id=cfg['next_round_id'],promotion_decision=decision)
    handoff=takeover_pending(round_id=cfg['round_id'],next_parent=decision.next_parent_policy_id,summary_sha=summary_sha)
    handoff['governed_train_reference_index']=[dict(ref) for ref in cfg['input_refs']
        if 'stage3y_existing_training_preparation_v1/' in ref['path']
        or 'stage4a_clean_existing_trainer_v1/' in ref['path']]
    handoff['referenced_artifact_bytes_rechecked']=True
    handoff['nested_historical_semantic_lineage_complete']=False
    handoff['reference_consumption_gate']='EXISTING_ROUND_RESEARCH_INPUTS_AND_RETENTION'
    closeout={'schema_id':'CLEAN_HUMAN_REFERENCE_TAIL_CLOSEOUT_V1','schema_version':1,
        'round_id':cfg['round_id'],'status':'EVALUATION_AND_DISPOSITION_CLOSED',
        'full_historical_archive_provenance_complete':False,
        'archive_provenance_note':'Preserves upstream false; publishing source is not proof of all historical semantic lineage.',
        'source_authorization_sha256':cfg['authorization_sha256'],'identity_audit_sha256':audit_sha,
        'aggregate_sha256':summary_sha,'disposition':disposition,'promotion_decision_sha256':decision.decision_sha256,
        'next_parent_policy_id':decision.next_parent_policy_id,'candidate_promotion_authorized':False,
        'routine_human_decisions_used':0,'benchmark_result_accessed':False,
        'strong_handoff_status':handoff['status'],'fresh_autonomous_round_claim_supported':False}
    # Publish only after every scientific cell has passed all existing identity checks.
    write_exact(output/'restricted/SELECT_IDENTITY_AUDIT.json',audit_report)
    write_exact(output/'restricted/TASK_LEVEL_PAIRED_RESULTS.json',{'schema_id':'CLEAN_SELECT_TASK_PAIRED_RESULTS_V1','task_results':paired['task_results'],'access_class':'SELECT_AUDIT_ONLY_NOT_PLANNER_INPUT'})
    write_exact(output/'TRAIN_SELECT_AGGREGATE.json',aggregate)
    write_exact(output/'POLICY_DISPOSITION.json',decision.to_dict())
    write_exact(output/'NEXT_ROUND_CREATION.json',creation.to_dict())
    write_exact(output/'STRONG_PRIMARY_HANDOFF.json',handoff)
    write_exact(output/'CLEAN_HUMAN_REFERENCE_CLOSEOUT.json',closeout)
    receipt=native['freeze_stage_attempt_receipt'](round_id=cfg['round_id'],stage_id='INTERNAL_EVALUATION_COMPLETED',
        attempt_ordinal=0,status='COMPLETED',input_artifact_sha256=cfg['authorization_sha256'],
        output_artifact_sha256=semantic_sha(closeout),previous_attempt_receipt_sha256=None)
    write_exact(output/'STAGE_ATTEMPT_RECEIPT.json',receipt.to_dict())
    return closeout
