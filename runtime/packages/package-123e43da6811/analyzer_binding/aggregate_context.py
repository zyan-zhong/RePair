"""Restricted, prior-round TRAIN_SELECT context for the native Researcher view.

The caller must first use the existing native terminal, round-tail and next-request
validators and read the summary through its hash-checked reference. This pure
projection grants no execution, training, promotion or Memory-write authority.
"""
from math import isfinite


COUNT_FIELDS = (
    'unique_task_count', 'paired_cell_count', 'total_condition_cell_count',
    'parent_success_cells', 'candidate_success_cells', 'both_success_cells',
    'both_failure_cells', 'parent_only_success_cells', 'candidate_only_success_cells',
)


def _need(condition, message):
    if not condition:
        raise ValueError('SELECT_RESEARCH_CONTEXT:' + message)


def _sha(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def project_previous_select_context(*, summary, summary_sha256, closed_result, next_request):
    """Return only aggregate metadata after a validated round-to-round transition.

    Feed the returned object to ``heldout_aggregate_metrics`` on the existing
    ``ROUND_RESEARCH_PLANNING`` view builder. Never feed it to train-side records,
    shadow events, Policy retrieval, supervision materialization or current-round
    active Memory. NO_TRAIN has no new SELECT observation and must not fabricate one.
    """
    _need(isinstance(summary, dict) and isinstance(closed_result, dict)
          and isinstance(next_request, dict), 'OBJECTS_REQUIRED')
    _need(_sha(summary_sha256), 'AGGREGATE_SHA_REQUIRED')
    _need(closed_result.get('schema_id') == 'FORMAL_NATIVE_ROUND_RESULT_V1', 'CLOSED_RESULT_SCHEMA')
    _need(next_request.get('schema_id') == 'ROUND_ROLLOUT_COLLECTION_REQUEST_V1', 'NEXT_REQUEST_SCHEMA')
    _need(summary.get('schema_id') == 'CURRENT_TRAIN_SELECT_AGGREGATE_V1', 'AGGREGATE_SCHEMA')
    _need(summary.get('evidence_access_class') == 'TRAIN_SELECT', 'TRAIN_SELECT_ONLY')
    _need(summary.get('memory_state') == summary.get('harness_state') == 'OFF', 'OFF_OFF_REQUIRED')
    _need(summary.get('benchmark_feedback_used') is False
          and closed_result.get('benchmark_feedback_used') is False, 'BENCHMARK_FEEDBACK_FORBIDDEN')
    _need(summary.get('primary_statistical_unit') == 'unique_task'
          and summary.get('replicates_are_not_independent_tasks') is True, 'STATISTICAL_UNIT')
    for key in ('round_id', 'request_sha256', 'parent_policy_id'):
        _need(summary.get(key) == closed_result.get(key) and summary.get(key), 'SOURCE_IDENTITY:' + key)
    _need(_sha(summary['request_sha256']) and _sha(next_request.get('request_sha256')), 'REQUEST_SHA')
    _need(next_request.get('round_id') != summary['round_id']
          and next_request['request_sha256'] != summary['request_sha256'], 'NEXT_ROUND_ONLY')
    _need(_sha(next_request.get('round_start_memory_snapshot_sha256')), 'NEXT_SNAPSHOT_SHA')
    outcome = closed_result.get('outcome')
    _need(outcome in {'PROMOTED', 'ROLLED_BACK'}, 'COMPLETED_EVALUATION_REQUIRED')
    _need(isinstance(summary.get('candidate_policy_id'), str) and summary['candidate_policy_id'],
          'CANDIDATE_IDENTITY_REQUIRED')
    chosen = summary.get('candidate_policy_id') if outcome == 'PROMOTED' else summary['parent_policy_id']
    _need(isinstance(chosen, str) and chosen and chosen == closed_result.get('next_parent_policy_id')
          == next_request.get('parent_policy_id'), 'NEXT_PARENT_IDENTITY')
    counts = {}
    for name in COUNT_FIELDS:
        value = summary.get(name)
        _need(type(value) is int and value >= 0, 'COUNT_TYPE:' + name)
        counts[name] = value
    seeds = summary.get('replicate_seeds')
    _need(isinstance(seeds, (list, tuple)) and seeds and all(type(x) is int for x in seeds), 'SEED_METADATA')
    delta = summary.get('mean_task_success_rate_delta')
    _need(type(delta) in {int, float} and isfinite(delta), 'DELTA_METADATA')
    # An explicit allowlist is intentional: the native aggregate also contains
    # references to restricted per-task results and environment audit details.
    return {
        'schema_id': 'PREVIOUS_TRAIN_SELECT_RESEARCH_CONTEXT_V1',
        'source_access': 'TRAIN_SELECT_AGGREGATE_ONLY',
        'source_round_id': summary['round_id'],
        'source_request_sha256': summary['request_sha256'],
        'source_aggregate_sha256': summary_sha256,
        'consumer_round_id': next_request['round_id'],
        'consumer_request_sha256': next_request['request_sha256'],
        'consumer_memory_snapshot_sha256': next_request['round_start_memory_snapshot_sha256'],
        'parent_policy_id': summary['parent_policy_id'],
        'candidate_policy_id': summary['candidate_policy_id'],
        'promotion_outcome': outcome,
        'metrics': {**counts, 'replicate_seeds': list(seeds), 'mean_task_success_rate_delta': delta},
        'primary_statistical_unit': 'unique_task',
        'replicates_are_not_independent_tasks': True,
        'explanatory_only': True,
        'per_task_select_data_authorized': False,
        'benchmark_feedback_authorized': False,
        'training_supervision_authorized': False,
        'active_memory_writeback_authorized': False,
    }


def validate_previous_select_context(context, *, current_request):
    """Recheck the exact allowlist and consumer binding after hash-checked transport."""
    _need(isinstance(context, dict), 'CONTEXT_OBJECT_REQUIRED')
    for field, current in (
        ('consumer_round_id', 'round_id'),
        ('consumer_request_sha256', 'request_sha256'),
        ('consumer_memory_snapshot_sha256', 'round_start_memory_snapshot_sha256'),
    ):
        _need(context.get(field) == current_request.get(current), 'CONSUMER_IDENTITY:' + field)
    metrics = context.get('metrics')
    _need(isinstance(metrics, dict), 'METRICS_REQUIRED')
    summary = {**metrics, 'schema_id': 'CURRENT_TRAIN_SELECT_AGGREGATE_V1',
        'round_id': context.get('source_round_id'), 'request_sha256': context.get('source_request_sha256'),
        'parent_policy_id': context.get('parent_policy_id'), 'candidate_policy_id': context.get('candidate_policy_id'),
        'evidence_access_class': 'TRAIN_SELECT', 'memory_state': 'OFF', 'harness_state': 'OFF',
        'benchmark_feedback_used': False, 'primary_statistical_unit': 'unique_task',
        'replicates_are_not_independent_tasks': True}
    closed = {'schema_id': 'FORMAL_NATIVE_ROUND_RESULT_V1', 'round_id': summary['round_id'],
        'request_sha256': summary['request_sha256'], 'parent_policy_id': summary['parent_policy_id'],
        'next_parent_policy_id': current_request.get('parent_policy_id'),
        'outcome': context.get('promotion_outcome'), 'benchmark_feedback_used': False}
    rebuilt = project_previous_select_context(summary=summary,
        summary_sha256=context.get('source_aggregate_sha256'), closed_result=closed, next_request=current_request)
    _need(context == rebuilt, 'EXACT_PROJECTED_CONTEXT_REQUIRED')
    return rebuilt
