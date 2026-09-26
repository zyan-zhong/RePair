"""Bounded paper projections from exact, immutable native receipts."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from entry.paper_export import export_attempt


SEALED = Path(__file__).resolve().parents[2] / 'validation' / 'V16_SEALED_FIXTURE.zip'


def sealed(name):
    with zipfile.ZipFile(SEALED) as archive:
        return json.loads(archive.read('MAX10_V1_6_BINDING_CANDIDATE/authority/' + name))


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding='utf8')
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def put_lines(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf8')
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read(ref):
    raw = Path(ref['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ref['sha256']
    return json.loads(raw)


def local_index(ref):
    return read(read(ref)['attempt_export_index_ref'])


def setup(tmp_path, outcome='NO_TRAINING_UPDATE'):
    formal = tmp_path / 'formal'
    formal.mkdir(parents=True)
    contract = sealed('PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json')
    contract_ref = put(formal / 'PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json', contract)
    binding = sealed('FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1.json')
    binding['paper_export_root'] = str(formal / 'paper_export')
    binding['paper_export_contract_file_sha256'] = contract_ref['sha256']
    put(formal / 'FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1.json', binding)
    start = {'round_id': binding['formal_round_id'], 'request_sha256': binding['formal_rollout_request_sha256'],
             'execution_attempt_id': 'attempt-1', 'parent_policy_id': 'parent',
             'parent_policy_artifact_sha256': 'a' * 64}
    verifier = {'schema_id': 'CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1',
                'stable_effect_counts': {'BENEFIT': 1, 'HARM': 0, 'NEUTRAL': 0, 'UNCERTAIN': 0},
                'selected_state_count': 1, 'scientifically_complete_pair_count': 5,
                'state_results': [{'source_state_sha256': 'b' * 64, 'source_task_id': 'task-1',
                                   'stable_effect': 'BENEFIT', 'source_candidate_sha256': 'c' * 64}],
                'pair_results': [], 'branch_records': []}
    verifier_ref = put(tmp_path / 'verifier.json', verifier)
    terminal_ref = put(tmp_path / 'terminal.json', {'schema_id': 'NO_TRAINING_UPDATE_V1'})
    result = {'round_id': start['round_id'], 'request_sha256': start['request_sha256'],
              'execution_attempt_id': start['execution_attempt_id'], 'outcome': outcome,
              'next_parent_policy_id': 'parent', 'human_scientific_decision_count': 0,
              'terminal_ref': terminal_ref, 'stage_evidence_refs': {'verifier': verifier_ref}}
    return tmp_path / 'attempt', start, result, {'formal_state_root': str(formal)}


def test_no_train_exact_rows_and_missing_cost(tmp_path):
    attempt, start, result, deployment = setup(tmp_path)
    ref = export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment)
    index = local_index(ref)
    assert index['valid_round_contribution'] == 1
    assert index['independent_sample_unit'] == 'UNIQUE_TASK_OR_SOURCE_STATE'
    summary = read(index['lanes']['round_summary'])['rows'][0]
    assert summary['benefit_count'] == 1 and summary['candidate_count'] == 1
    assert summary['api_cost_usd'] is None and 'api_cost_usd' in read(index['lanes']['round_summary'])['missingness'][0]
    assert summary['decision'] == 'NO_TRAINING_UPDATE'
    failure = read(index['lanes']['failure_analyzer_candidate_verifier_label_efficiency'])['rows'][0]
    assert failure['source_state_sha256'] == 'b' * 64
    assert failure['task_id'] == 'task-1'
    assert failure['candidate_sha256'] == 'c' * 64
    assert failure['verification_label'] == 'BENEFIT'
    assert failure['f0f1_pair_seed'] is None
    assert read(index['lanes']['training_arm'])['rows'] == []
    assert read(index['lanes']['evaluation_episode'])['rows'] == []
    assert export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment) == ref


def test_invalid_attempt_contributes_zero_and_no_scientific_rows(tmp_path):
    attempt, start, result, deployment = setup(tmp_path, 'PROTOCOL_INFRA_INVALID')
    result['stage_evidence_refs'] = {}
    result['rollout_manifest_ref'] = put(tmp_path / 'rollout.json', {'status': 'INVALID'})
    result['terminal_ref'] = put(tmp_path / 'invalid.json', {'classification': 'PROTOCOL_INFRA_INVALID'})
    index = local_index(export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment))
    assert index['valid_round_contribution'] == 0
    for name in ('training_arm', 'evaluation_episode', 'failure_analyzer_candidate_verifier_label_efficiency'):
        assert read(index['lanes'][name])['rows'] == []
    assert read(index['lanes']['round_summary'])['rows'][0]['decision'] == 'PROTOCOL_INFRA_INVALID'


def test_train_select_aggregate_is_labeled_and_training_is_source_bound(tmp_path):
    attempt, start, result, deployment = setup(tmp_path, 'ROLLED_BACK')
    native = tmp_path / 'native'
    run_ref = put(native / 'run.json', {'run_status': 'FORMAL_TRAINING_COMPLETED',
        'optimizer_step_count': 6, 'initial_trainable_parameter_sha256': 'd' * 64,
        'final_trainable_parameter_sha256': 'e' * 64})
    index_ref = put(native / 'output_index.json', {'artifacts': [
        {'logical_name': 'FORMAL_RUN_MANIFEST', **run_ref}]})
    pairs_ref = put_lines(native / 'source_pairs.jsonl', [
        {'source_state_sha256': 'b' * 64, 'verified_strategy_sha256': 'f' * 64},
        {'source_state_sha256': 'c' * 64, 'verified_strategy_sha256': '1' * 64}])
    census_ref = put(native / 'census.json', {'schema_id': 'STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1',
        'STRATEGY_ROW_COUNT': 2, 'native_example_count': 4,
        'ACTION_TARGET_TOKEN_COUNT': 30, 'ACTION_LOSS_BEARING_TOKEN_COUNT': 20,
        'STRATEGY_TARGET_TOKEN_COUNT': 40, 'STRATEGY_LOSS_BEARING_TOKEN_COUNT': 25,
        'PROMPT_MASKED_TOKEN_COUNT': 10, 'TOTAL_LOSS_BEARING_TOKEN_COUNT': 45,
        'source_pair_path': pairs_ref['path'], 'source_pair_sha256': pairs_ref['sha256']})
    order_ref = put(native / 'ROUND_SAMPLE_ORDER_MANIFEST_V2.json', {
        'schema_id': 'ROUND_SAMPLE_ORDER_MANIFEST_V2', 'row_count': 4, 'dataset_passes': 2,
        'ordered_source_state_sha256s': ['b' * 64, 'c' * 64, 'b' * 64, 'c' * 64] * 2,
        'ordered_row_sha256s': ['2' * 64, '3' * 64, '2' * 64, '3' * 64]})
    stage_ref = put(native / 'ROUND_TRAINING_STAGE_BINDING_V1.json', {
        'sample_order_ref': {'path': Path(order_ref['path']).name,
                             'sha256': order_ref['sha256']}})
    contract_ref = put(native / 'training_contract.json', {
        'profile_id': 'CURRENT_VERIFIED_STRATEGY_DUAL_VIEW_PROFILE_V1',
        'dataset': {'row_count': 4, 'manifest_path': census_ref['path'],
                    'manifest_file_sha256': census_ref['sha256']},
        'budget': {'epochs': 2, 'training_seed': 7},
        'optimization': {'learning_rate': 0.0001}, 'peft': {'r': 8},
        'parent': {'final_trainable_parameter_sha256': 'a' * 64}})
    trained_ref = put(native / 'trained.json', {'current_parent_context': {
        'training_contract_ref': contract_ref, 'stage_binding_ref': stage_ref,
        'output_artifact_index_ref': index_ref}})
    candidate_ref = put(native / 'candidate.json', {'training_result_ref': trained_ref})
    binding_ref = put(native / 'binding.json', {'input_refs': {'candidate_ref': candidate_ref}})
    paired_ref = put(native / 'paired.json', {'task_results': [{'task_id': 'restricted-task',
        'replicate_count': 2, 'success_rate_delta': 0.5}]})
    summary_ref = put(native / 'aggregate.json', {'schema_id': 'CURRENT_TRAIN_SELECT_AGGREGATE_V1',
        'evidence_access_class': 'TRAIN_SELECT', 'round_id': start['round_id'],
        'request_sha256': start['request_sha256'], 'candidate_policy_id': 'candidate',
        'candidate_success_cells': 3, 'paired_cell_count': 4,
        'mean_task_success_rate_delta': 0.25, 'native_paired_results_ref': paired_ref})
    result['terminal_ref'] = put(native / 'terminal.json', {'binding_ref': binding_ref,
                                                           'summary_ref': summary_ref})
    index = local_index(export_attempt(attempt_root=attempt, start=start,
                                       result=result, deployment=deployment))
    assert index['evaluation_access_class'] == 'TRAIN_SELECT'
    assert index['final_heldout_claim'] is False
    assert index['native_source_refs']['train_select_paired_results'] == paired_ref
    summary = read(index['lanes']['round_summary'])['rows'][0]
    assert summary['off_off_success'] == 0.75
    assert summary['delta_success_vs_parent'] == 0.25
    assert summary['strategy_training_rows'] == 2
    training = read(index['lanes']['training_arm'])['rows'][0]
    assert training['training_arm'] == 'CURRENT_VERIFIED_STRATEGY_DUAL_VIEW_PROFILE_V1'
    assert training['row_count'] == 4
    assert training['training_source_state_sha256s'] == ['b' * 64, 'c' * 64]
    assert training['verified_strategy_sha256s'] == ['f' * 64, '1' * 64]
    assert training['action_target_tokens'] == 30
    assert training['strategy_loss_bearing_tokens'] == 25
    assert training['sample_order_sha256'] == order_ref['sha256']
    assert training['optimizer_steps'] == 6
    assert training['final_checkpoint_sha256'] == 'e' * 64
    assert read(index['lanes']['evaluation_episode'])['rows'] == []


def test_repeated_source_state_does_not_increase_independent_n(tmp_path):
    attempt, start, result, deployment = setup(tmp_path)
    verifier = read(result['stage_evidence_refs']['verifier'])
    verifier['state_results'].append({**verifier['state_results'][0], 'pair_seed': 99})
    verifier['stable_effect_counts']['BENEFIT'] = 2
    verifier['selected_state_count'] = 2
    result['stage_evidence_refs']['verifier'] = put(tmp_path / 'verifier.json', verifier)
    index = local_index(export_attempt(attempt_root=attempt, start=start,
                                       result=result, deployment=deployment))
    assert index['independent_sample_count'] == 1
    assert index['paired_repetitions_are_independent_samples'] is False
    assert len(read(index['lanes']['failure_analyzer_candidate_verifier_label_efficiency'])['rows']) == 2


def test_published_branch_terminal_is_not_counted_as_environment_start(tmp_path):
    attempt, start, result, deployment = setup(tmp_path)
    verifier = read(result['stage_evidence_refs']['verifier'])
    verifier['branch_records'] = [{'arm': 'F1', 'terminal_status': 'PUBLISHED',
                                   'option_environment_step_count': 0}]
    result['stage_evidence_refs']['verifier'] = put(tmp_path / 'verifier.json', verifier)
    index = local_index(export_attempt(attempt_root=attempt, start=start,
                                       result=result, deployment=deployment))
    lane = read(index['lanes']['round_summary'])
    assert lane['rows'][0]['environment_branch_runs'] is None
    assert lane['missingness'][0]['environment_branch_runs'] == 'ENVIRONMENT_START_COUNT_NOT_PROVEN_BY_BRANCH_TERMINALS'
    assert lane['auxiliary_observations']['published_branch_terminal_count'] == 1


def test_rejects_tampered_native_ref_and_immutable_projection(tmp_path):
    attempt, start, result, deployment = setup(tmp_path)
    export_ref = export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment)
    Path(result['stage_evidence_refs']['verifier']['path']).write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='SHA'):
        export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment)
    attempt, start, result, deployment = setup(tmp_path / 'second')
    ref = export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment)
    Path(local_index(ref)['lanes']['round_summary']['path']).write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='IMMUTABLE'):
        export_attempt(attempt_root=attempt, start=start, result=result, deployment=deployment)
