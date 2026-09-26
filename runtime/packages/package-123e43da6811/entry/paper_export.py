"""Immutable, source-bound projection of one native attempt into paper lanes.

This module reads a fixed set of exact refs. It does not execute a stage,
discover receipts, decide promotion, or turn TRAIN_SELECT into final evaluation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile


LANES = ('round_summary', 'training_arm', 'evaluation_episode',
         'failure_analyzer_candidate_verifier_label_efficiency')
VALID = {'NO_TRAINING_UPDATE', 'PROMOTED', 'ROLLED_BACK'}


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf8') + b'\n'


def _file(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('PAPER_REGULAR_ABSOLUTE_FILE_REQUIRED:' + str(path))
    return path.read_bytes()


def _ref(path):
    path = Path(path).absolute()
    return {'path': str(path), 'sha256': hashlib.sha256(_file(path)).hexdigest()}


def _bytes_ref(ref):
    if (not isinstance(ref, dict) or set(ref) not in ({'path', 'sha256'},
                                                      {'path', 'file_sha256'})):
        raise ValueError('PAPER_EXACT_REF_REQUIRED')
    sha = ref.get('sha256', ref.get('file_sha256'))
    if not isinstance(sha, str) or len(sha) != 64:
        raise ValueError('PAPER_SHA256_REQUIRED')
    raw = _file(ref['path'])
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('PAPER_SOURCE_SHA_MISMATCH:' + ref['path'])
    return raw


def _read_ref(ref):
    try:
        return json.loads(_bytes_ref(ref))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('PAPER_SOURCE_JSON_INVALID:' + ref['path']) from exc


def _normalized(ref):
    _bytes_ref(ref)
    return {'path': ref['path'], 'sha256': ref.get('sha256', ref.get('file_sha256'))}


def _write_once(path, value):
    """Atomic no-overwrite publication; equal prior bytes can be adopted."""
    path = Path(path)
    raw = _canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or _file(path) != raw:
            raise ValueError('PAPER_IMMUTABLE_OUTPUT_CONFLICT:' + str(path))
        return _ref(path)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or _file(path) != raw:
                raise ValueError('PAPER_IMMUTABLE_OUTPUT_CONFLICT:' + str(path))
        if os.name == 'posix':
            directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return _ref(path)


def _get(obj, *keys):
    for key in keys:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    return obj


def _row(fields, observed):
    # Null always means unavailable, not zero. Each row records exact missingness.
    value = {field: observed.get(field) for field in fields}
    return value, {field: 'NOT_OBSERVED_IN_NATIVE_SOURCE' for field in fields if value[field] is None}


def _lane(name, required, rows, sources, *, missing_reason=None):
    projected = [_row(required, row) for row in rows]
    return {'schema_id': 'FORMAL_PAPER_LANE_PROJECTION_V1', 'lane': name,
            'required_fields': required, 'rows': [row for row, _ in projected],
            'missingness': [missing for _, missing in projected],
            'empty_reason': missing_reason if not rows else None,
            'source_refs': sources, 'scientific_authority': False}


def _training_sources(terminal):
    """Follow only the declared terminal -> binding -> candidate -> trainer chain."""
    binding_ref = _normalized(terminal['binding_ref'])
    binding = _read_ref(binding_ref)
    candidate_ref = _normalized(binding['input_refs']['candidate_ref'])
    candidate = _read_ref(candidate_ref)
    trained_ref = _normalized(candidate['training_result_ref'])
    trained = _read_ref(trained_ref)
    context = trained['current_parent_context']
    contract_ref = _normalized(context['training_contract_ref'])
    contract = _read_ref(contract_ref)
    dataset = contract['dataset']
    census_ref = _normalized({'path': dataset['manifest_path'],
                              'sha256': dataset['manifest_file_sha256']})
    census = _read_ref(census_ref)
    if census.get('schema_id') != 'STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1':
        raise ValueError('PAPER_NATIVE_LABEL_CENSUS_SCHEMA')
    pair_ref = _normalized({'path': census['source_pair_path'],
                            'sha256': census['source_pair_sha256']})
    pair_raw = _bytes_ref(pair_ref)
    try:
        pairs = [json.loads(line) for line in pair_raw.splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise ValueError('PAPER_SOURCE_PAIR_JSONL_INVALID') from exc
    if (len(pairs) != census.get('STRATEGY_ROW_COUNT')
            or any(not isinstance(row, dict) for row in pairs)):
        raise ValueError('PAPER_SOURCE_PAIR_CENSUS_MISMATCH')
    if (dataset.get('row_count') != census.get('native_example_count')
            or dataset['row_count'] != 2 * census['STRATEGY_ROW_COUNT']):
        raise ValueError('PAPER_DUAL_VIEW_ROW_CENSUS_MISMATCH')
    stage_ref = _normalized(context['stage_binding_ref'])
    stage = _read_ref(stage_ref)
    order_member = stage['sample_order_ref']
    relative = Path(order_member['path'])
    if relative.is_absolute() or relative.name != order_member['path']:
        raise ValueError('PAPER_SAMPLE_ORDER_MEMBER_INVALID')
    order_ref = _normalized({'path': str(Path(stage_ref['path']).parent / relative),
                             'sha256': order_member['sha256']})
    order = _read_ref(order_ref)
    if order.get('schema_id') != 'ROUND_SAMPLE_ORDER_MANIFEST_V2':
        raise ValueError('PAPER_SAMPLE_ORDER_SCHEMA')
    if (order.get('row_count') != dataset['row_count']
            or order.get('dataset_passes') != contract['budget']['epochs']
            or len(order.get('ordered_source_state_sha256s', []))
                != dataset['row_count'] * contract['budget']['epochs']):
        raise ValueError('PAPER_SAMPLE_ORDER_ROW_COUNT_MISMATCH')
    states = [row['source_state_sha256'] for row in pairs]
    if (len(states) != len(set(states))
            or set(states) != set(order['ordered_source_state_sha256s'])):
        raise ValueError('PAPER_SOURCE_PAIR_SAMPLE_ORDER_MISMATCH')
    output_index_ref = _normalized(context['output_artifact_index_ref'])
    output_index = _read_ref(output_index_ref)
    manifest_refs = [r for r in output_index.get('artifacts', [])
                     if r.get('logical_name') == 'FORMAL_RUN_MANIFEST']
    if len(manifest_refs) != 1:
        raise ValueError('PAPER_TRAINING_FORMAL_RUN_MANIFEST_REQUIRED')
    manifest_ref = _normalized({'path': manifest_refs[0]['path'],
        'sha256': manifest_refs[0].get('sha256', manifest_refs[0].get('file_sha256'))})
    manifest = _read_ref(manifest_ref)
    return contract, manifest, census, order_ref, pairs, [binding_ref, candidate_ref,
        trained_ref, contract_ref, census_ref, pair_ref, stage_ref, order_ref,
        output_index_ref, manifest_ref]


def _training_row(contract, run, census, order_ref, pairs):
    dataset = contract.get('dataset', {})
    budget = contract.get('budget', {})
    optimization = contract.get('optimization', {})
    return {'base_checkpoint_sha256': _get(contract, 'parent', 'final_trainable_parameter_sha256'),
            'training_arm': contract.get('profile_id'),
            'training_source_state_sha256s': [row['source_state_sha256'] for row in pairs],
            'verified_strategy_sha256s': [row['verified_strategy_sha256'] for row in pairs],
            'row_count': dataset.get('row_count'),
            'total_prompt_tokens': census.get('TOTAL_PROMPT_TOKEN_COUNT'),
            'masked_prompt_tokens': census.get('PROMPT_MASKED_TOKEN_COUNT'),
            'action_target_tokens': census.get('ACTION_TARGET_TOKEN_COUNT'),
            'action_loss_bearing_tokens': census.get('ACTION_LOSS_BEARING_TOKEN_COUNT'),
            'strategy_target_tokens': census.get('STRATEGY_TARGET_TOKEN_COUNT'),
            'strategy_loss_bearing_tokens': census.get('STRATEGY_LOSS_BEARING_TOKEN_COUNT'),
            'total_loss_bearing_tokens': census.get('TOTAL_LOSS_BEARING_TOKEN_COUNT'),
            'optimizer': optimization.get('optimizer'), 'learning_rate': optimization.get('learning_rate'),
            'epochs': budget.get('epochs'), 'optimizer_steps': run.get('optimizer_step_count'),
            'seed': budget.get('training_seed'), 'sample_order_sha256': order_ref['sha256'],
            'lora_config': contract.get('peft'),
            'initial_checkpoint_sha256': run.get('initial_trainable_parameter_sha256'),
            'final_checkpoint_sha256': run.get('final_trainable_parameter_sha256')}


def _failure_rows(start, verifier):
    rows = []
    for state in verifier.get('state_results', []):
        if not isinstance(state, dict):
            raise ValueError('PAPER_NATIVE_STATE_RESULT_INVALID')
        rows.append({'round': start['round_id'], 'parent_policy': start['parent_policy_id'],
                     'task_id': state.get('source_task_id'), 'task_family': state.get('task_family'),
                     'source_state_sha256': state.get('source_state_sha256'),
                     'analyzer_condition': state.get('condition_id'),
                     'analyzer_stage': state.get('stage_id'),
                     'candidate_sha256': state.get('source_candidate_sha256'),
                     'repair_or_strategy_sha256': state.get('repair_or_strategy_sha256'),
                     'verification_label': state.get('stable_effect'),
                     'abstain': state.get('abstain'),
                     'formal_x_disposition': state.get('formal_x_disposition'),
                     'memory_used': state.get('memory_used'),
                     'retrieved_memory_record_ids': state.get('retrieved_memory_record_ids'),
                     'retrieved_memory_record_count': state.get('retrieved_memory_record_count'),
                     'memory_applicability': state.get('memory_applicability')})
    return rows


def export_attempt(*, attempt_root, start, result, deployment):
    """Export one validated attempt; return its exact registered index ref.

    The campaign owner must validate the native result before calling this.
    Replaying this function validates source bytes and adopts identical output.
    """
    if not isinstance(start, dict) or not isinstance(result, dict):
        raise ValueError('PAPER_START_AND_RESULT_REQUIRED')
    for field in ('round_id', 'request_sha256', 'execution_attempt_id'):
        if result.get(field) != start.get(field) or not isinstance(start.get(field), str):
            raise ValueError('PAPER_ATTEMPT_IDENTITY_MISMATCH:' + field)
    if result.get('outcome') not in VALID | {'PROTOCOL_INFRA_INVALID'}:
        raise ValueError('PAPER_NATIVE_OUTCOME_REQUIRED')
    attempt = Path(attempt_root).absolute()
    if result.get('attempt_root') is not None and Path(result['attempt_root']).absolute() != attempt:
        raise ValueError('PAPER_ATTEMPT_ROOT_MISMATCH')
    formal = Path(deployment['formal_state_root'])
    binding_ref = _ref(formal / 'FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1.json')
    binding = _read_ref(binding_ref)
    contract_ref = _ref(formal / 'PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json')
    contract = _read_ref(contract_ref)
    if (binding.get('schema_id') != 'FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1'
            or contract.get('schema_id') != 'PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1'
            or binding.get('paper_export_contract_file_sha256') != contract_ref['sha256']
            or binding.get('paper_export_contract_sha256') != contract.get('contract_sha256')
            or set(contract.get('lanes', {})) != set(LANES)):
        raise ValueError('PAPER_FORMAL_CONTRACT_BINDING_MISMATCH')
    export_root = Path(binding['paper_export_root'])
    if not export_root.is_absolute() or export_root.is_symlink():
        raise ValueError('PAPER_REGISTERED_EXPORT_ROOT_INVALID')
    terminal_ref = _normalized(result['terminal_ref'])
    terminal = _read_ref(terminal_ref)
    invalid = result['outcome'] == 'PROTOCOL_INFRA_INVALID'
    refs = result.get('stage_evidence_refs', {})
    sources = {'terminal': terminal_ref}
    if invalid:
        verifier = None
        if result.get('rollout_manifest_ref') is not None:
            sources['rollout_manifest'] = _normalized(result['rollout_manifest_ref'])
    else:
        verifier_ref = _normalized(refs['verifier'])
        verifier = _read_ref(verifier_ref)
        if verifier.get('schema_id') != 'CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1':
            raise ValueError('PAPER_NATIVE_VERIFIER_SCHEMA_MISMATCH')
        sources['verifier'] = verifier_ref
    summary = None
    training = None
    train_sources = []
    if result['outcome'] in {'PROMOTED', 'ROLLED_BACK'}:
        summary_ref = _normalized(terminal['summary_ref'])
        summary = _read_ref(summary_ref)
        if (summary.get('schema_id') != 'CURRENT_TRAIN_SELECT_AGGREGATE_V1'
                or summary.get('evidence_access_class') != 'TRAIN_SELECT'
                or summary.get('round_id') != start['round_id']
                or summary.get('request_sha256') != start['request_sha256']):
            raise ValueError('PAPER_TRAIN_SELECT_SUMMARY_IDENTITY')
        sources['train_select_summary'] = summary_ref
        if summary.get('native_paired_results_ref') is not None:
            sources['train_select_paired_results'] = _normalized(summary['native_paired_results_ref'])
        contract_train, run, census, order_ref, pairs, train_sources = _training_sources(terminal)
        training = _training_row(contract_train, run, census, order_ref, pairs)
    state_rows = _failure_rows(start, verifier) if verifier else []
    candidates = [row.get('candidate_sha256') for row in state_rows]
    candidate_count = len(set(candidates)) if candidates and all(candidates) else None
    counts = verifier.get('stable_effect_counts', {}) if verifier else {}
    paired = summary.get('paired_cell_count') if summary else None
    success = (summary['candidate_success_cells'] / paired
               if summary and type(paired) is int and paired > 0
               and type(summary.get('candidate_success_cells')) is int else None)
    round_row = {'round': start['round_id'], 'parent_policy': start['parent_policy_id'],
                 'main_bottleneck_id': verifier.get('main_bottleneck_id') if verifier else None,
                 'candidate_count': candidate_count,
                 'benefit_count': counts.get('BENEFIT'), 'harm_count': counts.get('HARM'),
                 'neutral_count': counts.get('NEUTRAL'), 'uncertain_count': counts.get('UNCERTAIN'),
                 'strategy_training_rows': census.get('STRATEGY_ROW_COUNT') if training else None,
                 'task_policy_update': result.get('outcome') == 'PROMOTED' if not invalid else None,
                 'candidate_policy': summary.get('candidate_policy_id') if summary else None,
                 'off_off_success': success,
                 'delta_success_vs_parent': summary.get('mean_task_success_rate_delta') if summary else None,
                 'decision': result['outcome'],
                 'human_scientific_decision_count': result.get('human_scientific_decision_count')}
    lane_rows = {'round_summary': [round_row], 'training_arm': [training] if training else [],
                 'evaluation_episode': [],
                 'failure_analyzer_candidate_verifier_label_efficiency': state_rows}
    lane_sources = {'round_summary': list(sources.values()), 'training_arm': train_sources,
                    'evaluation_episode': ([sources['train_select_summary']] +
                        ([sources['train_select_paired_results']]
                         if 'train_select_paired_results' in sources else [])) if summary else [],
                    'failure_analyzer_candidate_verifier_label_efficiency':
                        [sources['verifier']] if verifier else []}
    local = attempt / 'paper_export'
    lane_refs = {}
    for name in LANES:
        required = contract['lanes'][name]['required_fields']
        if required != binding[name]:
            raise ValueError('PAPER_LANE_REQUIRED_FIELDS_BINDING:' + name)
        reason = ('INVALID_ATTEMPT_NO_SCIENTIFIC_ROWS' if invalid else
                  'NATIVE_STAGE_NOT_EXECUTED_OR_NO_EPISODE_PROJECTION')
        lane = _lane(name, required, lane_rows[name], lane_sources[name], missing_reason=reason)
        if name == 'round_summary':
            branches = verifier.get('branch_records') if verifier else None
            lane['auxiliary_observations'] = {'published_branch_terminal_count':
                len(branches) if isinstance(branches, list) else None}
            lane['missingness'][0]['environment_branch_runs'] = (
                'ENVIRONMENT_START_COUNT_NOT_PROVEN_BY_BRANCH_TERMINALS')
        lane_refs[name] = _write_once(local / (name + '.json'), lane)
    states = [row.get('source_state_sha256') for row in state_rows]
    independent_n = len(set(states)) if states and all(states) else (0 if invalid else None)
    index = {'schema_id': 'FORMAL_PAPER_ATTEMPT_EXPORT_INDEX_V1',
             'round_id': start['round_id'], 'request_sha256': start['request_sha256'],
             'execution_attempt_id': start['execution_attempt_id'], 'outcome': result['outcome'],
             'valid_round_contribution': 0 if invalid else 1,
             'independent_sample_unit': binding['primary_independent_unit'],
             'independent_sample_count': independent_n,
             'paired_repetitions_are_independent_samples': False,
             'branch_runs_increase_independent_n': False,
             'evaluation_access_class': 'TRAIN_SELECT' if summary else None,
             'final_heldout_claim': False,
             'formal_binding_ref': binding_ref, 'paper_contract_ref': contract_ref,
             'native_source_refs': sources, 'lanes': lane_refs}
    local_ref = _write_once(local / 'INDEX.json', index)
    request_sha = start['request_sha256']
    if (len(request_sha) != 64 or any(c not in '0123456789abcdef' for c in request_sha)):
        raise ValueError('PAPER_REQUEST_SHA_INVALID')
    attempt_key = hashlib.sha256(start['execution_attempt_id'].encode('utf8')).hexdigest()
    return _write_once(export_root / request_sha / attempt_key / 'INDEX.json',
                       {'schema_id': 'FORMAL_REGISTERED_PAPER_EXPORT_ENTRY_V1',
                        'request_sha256': request_sha,
                        'execution_attempt_id': start['execution_attempt_id'],
                        'attempt_export_index_ref': local_ref})
