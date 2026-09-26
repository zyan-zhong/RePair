"""Current round tail using the original Memory, closeout and governor APIs.

The resident driver first replays the registered Analyzer/H4.4 verifier and,
on TRAIN, validates the trainer and OFF/OFF execution. This module consumes
their exact artifacts; it never supplies a promotion verdict or advances the
campaign governor. Importing this module does not import pchsi, so the entry
can install the registered Memory overlay before importing native modules.
"""
from pathlib import Path


def _ref(value):
    """Mechanical conversion of the two already-existing exact-ref spellings."""
    from continuity_binding.api import ContinuityError, read_bytes_ref
    if not isinstance(value, dict) or set(value) not in ({'path', 'sha256'}, {'path', 'file_sha256'}):
        raise ContinuityError('TAIL_EXACT_FILE_REFERENCE_REQUIRED')
    result = {'path': value['path'], 'sha256': value.get('sha256', value.get('file_sha256'))}
    read_bytes_ref(result)
    return result


def _memory_ref(value):
    ref = _ref(value)
    return {'path': ref['path'], 'file_sha256': ref['sha256']}


def _current_inputs(start, binding, current_inputs_ref):
    from continuity_binding.api import _equal, read_ref
    inputs = read_ref(_ref(current_inputs_ref))
    _equal(inputs.get('schema_id'), 'ROUND_ROLLOUT_INPUT_REFERENCES_V1', 'TAIL_CURRENT_INPUT_SCHEMA')
    for role, field, analyzer_role in (
        ('runtime', 'policy_runtime_binding_sha256', 'actor_runtime'),
        ('profile', 'execution_profile_sha256', None),
        ('memory', 'round_memory_runtime_authority_sha256', 'memory_runtime'),
        ('train_manifest', 'train_update_manifest_sha256', 'train_update_manifest'),
    ):
        inputs[role] = _ref(inputs[role])
        _equal(inputs[role]['sha256'], start[field], 'TAIL_CURRENT_INPUT_REQUEST:' + role)
        if analyzer_role is not None:
            # Capsules may hold a second exact copy; the byte identity is fixed.
            _equal(_ref(binding['refs'][analyzer_role])['sha256'], inputs[role]['sha256'],
                   'TAIL_ANALYZER_INPUT_REQUEST:' + role)
    _equal(read_ref(_ref(binding['refs']['request'])), start, 'TAIL_ANALYZER_CURRENT_REQUEST')
    return inputs


def _training_terminal(start, terminal_ref):
    """Revalidate an actual registered OFF/OFF terminal, never choose a verdict."""
    from continuity_binding.api import _equal, read_ref, ContinuityError
    from pchsi.round_control.promotion import freeze_promotion_decision
    terminal = read_ref(_ref(terminal_ref))
    for key, expected in {'schema_id':'CURRENT_NATIVE_OFFOFF_TERMINAL_V1',
        'round_id':start['round_id'], 'request_sha256':start['request_sha256'],
        'human_scientific_decision_count':0, 'benchmark_feedback_used':False}.items():
        _equal(terminal.get(key), expected, 'TAIL_OFFOFF_TERMINAL:' + key)
    binding = read_ref(_ref(terminal['binding_ref']))
    _equal(binding.get('schema_id'), 'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1', 'TAIL_OFFOFF_BINDING_SCHEMA')
    inputs = binding['input_refs']
    _equal(read_ref(_ref(inputs['request_ref'])), start, 'TAIL_OFFOFF_CURRENT_REQUEST')
    parent = read_ref(_ref(inputs['parent_ref']))
    candidate = read_ref(_ref(inputs['candidate_ref']))
    for key, expected in {'policy_id':start['parent_policy_id'],
                         'artifact_sha256':start['parent_policy_artifact_sha256']}.items():
        _equal(parent.get(key), expected, 'TAIL_OFFOFF_PARENT:' + key)
    for key, expected in {'round_id':start['round_id'], 'request_sha256':start['request_sha256'],
        'execution_attempt_id':start['execution_attempt_id'], 'parent_policy_id':start['parent_policy_id'],
        'parent_policy_artifact_sha256':start['parent_policy_artifact_sha256']}.items():
        _equal(candidate.get(key), expected, 'TAIL_OFFOFF_CANDIDATE:' + key)
    summary_ref = _ref(terminal['summary_ref'])
    summary = read_ref(summary_ref)
    _equal(_ref(summary['frozen_protocol_ref']), _ref(inputs['protocol_ref']), 'TAIL_OFFOFF_FROZEN_PROTOCOL')
    protocol = read_ref(_ref(inputs['protocol_ref']))
    rule = read_ref(_ref(protocol['promotion_rule_ref']))
    for key, expected in {'schema_id':'CURRENT_TRAIN_SELECT_AGGREGATE_V1',
        'round_id':start['round_id'], 'request_sha256':start['request_sha256'],
        'parent_policy_id':parent['policy_id'], 'candidate_policy_id':candidate['policy_id'],
        'memory_state':'OFF', 'harness_state':'OFF', 'evidence_access_class':'TRAIN_SELECT',
        'benchmark_feedback_used':False}.items():
        _equal(summary.get(key), expected, 'TAIL_OFFOFF_AGGREGATE:' + key)
    promotion_ref = _ref(terminal['promotion_ref'])
    raw = read_ref(promotion_ref)
    promotion = freeze_promotion_decision(**{key: raw[key] for key in (
        'round_id','decision','decision_rule_id','evidence_access_class','evidence_sha256',
        'parent_policy_id','candidate_policy_id')})
    _equal(raw, promotion.to_dict(), 'TAIL_NATIVE_PROMOTION_CONTENT')
    _equal(promotion.decision_rule_id, rule['decision_rule_id'], 'TAIL_NATIVE_PROMOTION_FROZEN_RULE')
    if promotion.decision not in {'PROMOTE', 'ROLLBACK'}:
        raise ContinuityError('TAIL_HOLD_IS_NOT_PROMOTION_OR_ROLLBACK')
    for actual, expected, label in (
        (promotion.round_id, start['round_id'], 'ROUND'),
        (promotion.parent_policy_id, parent['policy_id'], 'PARENT'),
        (promotion.candidate_policy_id, candidate['policy_id'], 'CANDIDATE'),
        (promotion.evidence_sha256, summary_ref['sha256'], 'EVIDENCE'),
    ):
        _equal(actual, expected, 'TAIL_NATIVE_PROMOTION_' + label)
    chosen = candidate if promotion.decision == 'PROMOTE' else parent
    outcome = 'PROMOTED' if promotion.decision == 'PROMOTE' else 'ROLLED_BACK'
    _equal(terminal.get('outcome'), outcome, 'TAIL_PROMOTION_OUTCOME')
    _equal(terminal.get('next_parent_policy_id'), chosen['policy_id'], 'TAIL_PROMOTION_NEXT_POLICY')
    _equal(terminal.get('next_parent_policy_artifact_sha256'), chosen['artifact_sha256'], 'TAIL_PROMOTION_NEXT_ARTIFACT')
    if candidate['policy_id'] == parent['policy_id'] or candidate['artifact_sha256'] == parent['artifact_sha256']:
        raise ContinuityError('TAIL_CANDIDATE_REQUIRES_NEW_POLICY_AND_ARTIFACT')
    return terminal, promotion_ref


def _next_partitions(*, current_ref, new_ref, closure, sink):
    from continuity_binding.api import _equal, read_ref, write_once, ContinuityError
    from pchsi.memory.consumer_views import (MemorySourcePartitionBindingV1,
        MemorySourcePartitionV1, MemoryPartitionAuthorityScopeV1)
    current = read_ref(_ref(current_ref))
    added = read_ref(_ref(new_ref))
    selected = {row.memory_lineage_id for row in closure.next_active_record_bindings}
    if set(added) - selected:
        raise ContinuityError('TAIL_NEW_PARTITION_NOT_ADMITTED_BY_NATIVE_CLOSURE')
    combined = {**current, **added}
    if selected - set(combined):
        raise ContinuityError('TAIL_NEXT_ACTIVE_MEMORY_PARTITION_MISSING')
    output = {}
    for lineage in sorted(selected):
        row = combined[lineage]
        parsed = MemorySourcePartitionBindingV1(**{**row,
            'source_partition':MemorySourcePartitionV1(row['source_partition']),
            'authority_scope':MemoryPartitionAuthorityScopeV1(row['authority_scope'])})
        _equal(parsed.memory_lineage_id, lineage, 'TAIL_MEMORY_PARTITION_LINEAGE')
        _equal(parsed.to_dict(), row, 'TAIL_MEMORY_PARTITION_NATIVE_SERIALIZATION')
        output[lineage] = row
    return write_once(Path(sink)/'MEMORY_SOURCE_PARTITIONS.json', output)


def close_round_tail(*, start, analyzer_binding, analyzer_output_root, attempt_root,
                     stage_evidence_refs, current_execution_binding_ref, current_inputs_ref,
                     current_memory_state_ref=None, training_result_ref=None,
                     next_policy_input_refs=None, tokenizer=None):
    """Materialize the actual Memory producer, native closeout and next inputs.

    Call after the original independent verifier has replayed all current arms.
    tokenizer=None uses the producer's registered local tokenizer; an explicit
    counter is useful in native fixture tests and remains identity-validated.
    A promoted policy needs its actual newly published runtime/launch refs.
    """
    from memory_binding.source_overlay import install_memory_overlay
    install_memory_overlay(analyzer_binding['scientific_repo_root'])
    from continuity_binding.api import (native_request, validate_current_post, read_ref,
        materialize_no_training_update, native_memory_closure, write_once, _equal, ContinuityError,
        validate_round_tail)
    from continuity_binding.memory_materializer import (register_initial_memory_state,
        materialize_next_memory_runtime)
    from continuity_binding.next_request import resolve_next_inputs, rebind_execution
    from memory_binding.api import materialize_round_memory
    native_request(start)
    refs = {name:_ref(ref) for name, ref in stage_evidence_refs.items()}
    post, _ = validate_current_post(start=start, evidence_refs=refs)
    inputs = _current_inputs(start, analyzer_binding, current_inputs_ref)
    execution_ref = _ref(current_execution_binding_ref)
    rebind_execution(read_ref(execution_ref), start['request_sha256'], start['request_sha256'])
    sink = Path(attempt_root).absolute()/'tail'
    if post['researcher_training_recommendation'] == 'NO_TRAIN':
        if training_result_ref is not None or next_policy_input_refs is not None:
            raise ContinuityError('TAIL_NO_TRAIN_CANNOT_CONSUME_TRAINING_OR_CHANGED_POLICY')
        outcome, next_id, next_artifact = ('NO_TRAINING_UPDATE', start['parent_policy_id'], start['parent_policy_artifact_sha256'])
        terminal_ref = materialize_no_training_update(start=start, evidence_refs=refs, sink=sink/'closeout')
        refs['no_training_update'] = terminal_ref
    else:
        if training_result_ref is None:
            raise ContinuityError('TAIL_TRAIN_REQUIRES_NATIVE_OFFOFF_TERMINAL')
        terminal_ref = _ref(training_result_ref)
        terminal, refs['promotion'] = _training_terminal(start, terminal_ref)
        outcome, next_id, next_artifact = (terminal['outcome'], terminal['next_parent_policy_id'],
                                          terminal['next_parent_policy_artifact_sha256'])
        refs['training_terminal'] = terminal_ref
        if outcome == 'PROMOTED':
            required = {'runtime','profile','policy_launch_authority','engine_profile'}
            if not isinstance(next_policy_input_refs, dict) or set(next_policy_input_refs) != required:
                raise ContinuityError('TAIL_PROMOTED_ACTUAL_RUNTIME_LAUNCH_REFS_REQUIRED')
            inputs.update({name:_ref(ref) for name, ref in next_policy_input_refs.items()})
        elif next_policy_input_refs is not None:
            raise ContinuityError('TAIL_ROLLBACK_RETAINS_CURRENT_POLICY_INPUTS')
    materialized = materialize_round_memory(binding=analyzer_binding,
        analyzer_output_root=analyzer_output_root,
        execution_plan_ref=_memory_ref(refs['execution_plan']), verifier_ref=_memory_ref(refs['verifier']),
        output_root=sink/'memory_producer', tokenizer=tokenizer)
    _equal(materialized.get('round_id'), start['round_id'], 'TAIL_MEMORY_PRODUCER_ROUND')
    _equal(materialized.get('request_sha256'), start['request_sha256'], 'TAIL_MEMORY_PRODUCER_REQUEST')
    state_ref = (_ref(current_memory_state_ref) if current_memory_state_ref is not None else
        register_initial_memory_state(start=start, runtime_ref=inputs['memory'], sink=sink/'initial_memory'))
    event_refs = [_ref(ref) for ref in materialized['event_refs']]
    next_memory = materialize_next_memory_runtime(start=start, state_ref=state_ref, event_refs=event_refs,
        current_runtime_ref=inputs['memory'],
        additional_member_refs=[{key:_ref(ref) for key, ref in row.items()}
                                for row in materialized['additional_member_refs']], sink=sink/'memory_close')
    _, closure = native_memory_closure(start=start, state_ref=state_ref, event_refs=event_refs)
    partitions = _next_partitions(current_ref=analyzer_binding['refs']['memory_source_partitions'],
        new_ref=materialized['new_partition_ref'], closure=closure, sink=sink/'next_inputs')
    inputs.update(memory=next_memory['runtime'], memory_source_partitions=partitions)
    # A prior request identity cannot be carried in next input authority.
    inputs.pop('request_sha256', None)
    refs.update(memory_state=state_ref, memory_shadow_events=event_refs,
        memory_closure=next_memory['memory_closure'], memory_materialization=_ref(materialized['receipt_ref']),
        memory_source_partitions=partitions, rollout_execution_binding=execution_ref,
        current_inputs=_ref(current_inputs_ref))
    identity_names = ('round_id','execution_attempt_id','request_sha256','parent_policy_id',
                      'parent_policy_artifact_sha256','round_start_memory_snapshot_sha256')
    result = {**{name:start[name] for name in identity_names}, 'schema_id':'FORMAL_NATIVE_ROUND_RESULT_V1',
        'outcome':outcome, 'next_parent_policy_id':next_id, 'next_parent_policy_artifact_sha256':next_artifact,
        'terminal_ref':terminal_ref, 'human_scientific_decision_count':0, 'benchmark_feedback_used':False,
        'invalid_attempt_adaptive_evidence_reuse':False, 'next_request':None, 'stage_evidence_refs':refs}
    resolve_next_inputs(start=start, result=result, inputs=inputs, closure=closure)
    refs['next_inputs_pending'] = write_once(sink/'next_inputs/ROUND_ROLLOUT_INPUT_REFERENCES_V1.json', inputs)
    validate_closed_round_tail(start=start, result=result)
    return result


def validate_closed_round_tail(*, start, result):
    """Read-only recovery of tail evidence; upstream science is checked by driver."""
    from continuity_binding.api import validate_round_tail, read_ref, _equal
    validate_round_tail(start=start, result=result)
    refs = result['stage_evidence_refs']
    producer = read_ref(_ref(refs['memory_materialization']))
    for key in ('round_id', 'request_sha256'):
        _equal(producer.get(key), start[key], 'TAIL_MEMORY_RECEIPT_CURRENT:' + key)
    _equal([_ref(ref) for ref in producer['event_refs']], refs['memory_shadow_events'], 'TAIL_MEMORY_RECEIPT_EVENTS')
    if result['outcome'] == 'NO_TRAINING_UPDATE':
        _equal(_ref(result['terminal_ref']), _ref(refs['no_training_update']), 'TAIL_NO_TRAIN_TERMINAL_REF')
    else:
        _equal(_ref(result['terminal_ref']), _ref(refs['training_terminal']), 'TAIL_TRAIN_TERMINAL_REF')
        terminal, promotion = _training_terminal(start, result['terminal_ref'])
        _equal(promotion, _ref(refs['promotion']), 'TAIL_PROMOTION_REF')
        for key in ('outcome','next_parent_policy_id','next_parent_policy_artifact_sha256'):
            _equal(result[key], terminal[key], 'TAIL_TRAIN_RESULT:' + key)
    return True


def build_next_round_tail(*, start, result, governance, attempt_root):
    """Return request AND exact registrations; never mutate the owner's RESULT.

    The caller uses next_request as NativeRoundDriver.build_next's return value
    and registers the other refs under that exact request SHA for the next round.
    The already-advanced original governor forbids materialization after STOP.
    """
    from continuity_binding.api import write_once
    from continuity_binding.next_request import materialize_next_request, validate_native_next_request
    validate_closed_round_tail(start=start, result=result)
    refs = result['stage_evidence_refs']
    out = materialize_next_request(start=start, result=result, governance=governance,
        next_inputs_ref=refs['next_inputs_pending'], current_binding_ref=refs['rollout_execution_binding'],
        sink=Path(attempt_root).absolute()/'tail/next_round')
    next_refs = {**refs, 'next_inputs':out['input_refs'], 'next_execution_binding':out['execution_binding'],
                 'next_memory_state':out['memory_state']}
    if 'next_creation' in out:
        next_refs['next_creation'] = out['next_creation']
    validated_result = {**result, 'next_request':out['next_request'], 'stage_evidence_refs':next_refs}
    validate_native_next_request(start=start, result=validated_result,
        next_request=out['next_request'], governance=governance)
    out['memory_source_partitions'] = refs['memory_source_partitions']
    out['validation_receipt'] = write_once(Path(attempt_root).absolute()/'tail/next_round/NEXT_ROUND_VALIDATION.json',
        {'schema_id':'CURRENT_NATIVE_NEXT_ROUND_VALIDATION_V1', 'previous_request_sha256':start['request_sha256'],
         'governance_sha256':governance.governance_sha256, 'result':validated_result})
    return out
