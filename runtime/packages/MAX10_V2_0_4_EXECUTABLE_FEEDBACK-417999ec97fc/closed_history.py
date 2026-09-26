"""Reuse hash-bound closed rounds; fresh rounds retain the native full audit."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch


def require(ok, label):
    if not ok:
        raise ValueError('CLOSED_HISTORY_' + label)


def closed_transition(driver, start, result):
    import entry.campaign_owner as owner
    from pchsi.round_control.campaign_authority import CampaignStartupAuthorityV1
    from pchsi.round_control.scientific_round_governance import new_scientific_round_governance
    root = Path(driver.owner_root)
    attempt = Path(result['attempt_root'])
    require(attempt.parent == root / 'attempts', 'ATTEMPT_OWNER')
    require(attempt.name.isdigit() and len(attempt.name) == 6, 'ATTEMPT_ORDINAL')
    ordinal = int(attempt.name)
    require(ordinal > 0, 'ATTEMPT_ORDINAL')
    target = root / 'transitions' / (attempt.name + '.json')
    if not target.exists():
        return None
    binding = owner._read(root / 'OWNER_BINDING.json')
    require(binding['native_driver_source_sha256'] == driver.source_identity_sha256, 'DRIVER_IDENTITY')
    require(binding['initial'] == driver.initial, 'INITIAL_IDENTITY')
    authority = CampaignStartupAuthorityV1.from_dict(binding['authority'])
    state = new_scientific_round_governance(authority=authority)
    previous = owner._digest(binding)
    cursor = binding['initial']
    retries = 0
    for number in range(1, ordinal + 1):
        path = root / 'transitions' / f'{number:06d}.json'
        event = owner._read(path)
        payload = {k:v for k,v in event.items() if k != 'event_sha256'}
        require(event['event_sha256'] == owner._digest(payload), 'EVENT_DIGEST')
        require(payload['previous_event_sha256'] == previous and payload['ordinal'] == number, 'CHAIN')
        require(payload['start'] == cursor and payload['governance_before'] == state.to_dict(), 'START_GOVERNANCE')
        directory = root / 'attempts' / f'{number:06d}'
        intent = owner._read(directory / 'INTENT.json')
        require(intent == {'schema_id':'FORMAL_CAMPAIGN_OWNER_ROUND_INTENT_V1', 'start':cursor,
            'previous_event_sha256':previous, 'native_driver_source_sha256':driver.source_identity_sha256}, 'INTENT')
        closed = owner._read(directory / 'RESULT.json')
        require(owner._digest(closed) == payload['result_sha256'], 'RESULT_DIGEST')
        state, retries, stop = owner._transition(state=state,start=cursor,result=closed,retry_used=retries)
        require(payload['governance_after'] == state.to_dict() and payload['restarts_used_after'] == retries
                and payload['stop_reason'] == stop, 'GOVERNANCE_AFTER')
        if stop is None:
            owner._check_next(cursor,closed,payload['next_start'])
        else:
            require(payload['next_start'] is None and number == ordinal, 'AFTER_STOP')
        if number == ordinal:
            require(cursor == start and closed == result, 'CURRENT_CLOSED_RESULT')
        cursor = payload['next_start']
        previous = event['event_sha256']
    return {'path':str(target),'sha256':owner._sha(target),'event_sha256':previous}


def receipts(terminal_ref, read, *, allow_exception=True):
    terminal = read(terminal_ref)
    require(terminal['schema_id'] == 'CURRENT_NATIVE_OFFOFF_TERMINAL_V1', 'TERMINAL_SCHEMA')
    binding = read(terminal['binding_ref'])
    summary = read(terminal['summary_ref'])
    decision = read(terminal['promotion_ref'])
    protocol = read(summary['frozen_protocol_ref'])
    rule = read(protocol['promotion_rule_ref'])
    audit = read(summary['identity_audit_ref'])
    paired = read(summary['native_paired_results_ref'])
    parent = read(binding['input_refs']['parent_ref'])
    candidate = read(binding['input_refs']['candidate_ref'])
    require(binding['input_refs']['protocol_ref'] == summary['frozen_protocol_ref'], 'PROTOCOL_BINDING')
    require(audit['binding_ref'] == terminal['binding_ref'], 'AUDIT_BINDING')
    require(terminal['benchmark_feedback_used'] is False and summary['benchmark_feedback_used'] is False, 'BENCHMARK')
    require(summary['memory_state'] == summary['harness_state'] == 'OFF' and summary['evidence_access_class'] == 'TRAIN_SELECT', 'SELECT_ISOLATION')
    for key in ('round_id','request_sha256'):
        require(terminal[key] == summary[key] == binding[key], 'ROUND_IDENTITY')
    require(summary['parent_policy_id'] == parent['policy_id'] and summary['candidate_policy_id'] == candidate['policy_id'], 'POLICY_IDENTITY')
    for key in ('unique_task_count','replicate_seeds','paired_cell_count','total_condition_cell_count',
                'parent_success_cells','candidate_success_cells','both_success_cells','both_failure_cells',
                'parent_only_success_cells','candidate_only_success_cells','mean_task_success_rate_delta'):
        require(summary[key] == paired[key], 'PAIRED_SUMMARY_' + key)
    require(summary['replicate_seeds'] == protocol['replicate_seeds'], 'SEEDS')
    require(terminal['outcome'] in ('PROMOTED','ROLLED_BACK'), 'OUTCOME')
    require(decision['schema_id'] == 'PROMOTION_DECISION_V1' and decision['round_id'] == terminal['round_id']
            and decision['decision_rule_id'] == rule['decision_rule_id']
            and decision['evidence_sha256'] == terminal['summary_ref']['sha256']
            and decision['evidence_access_class'] == 'TRAIN_SELECT', 'DECISION_BINDING')
    chosen = candidate if terminal['outcome'] == 'PROMOTED' else parent
    require(terminal['next_parent_policy_id'] == chosen['policy_id'] and
            terminal['next_parent_policy_artifact_sha256'] == chosen['artifact_sha256'], 'NEXT_PARENT')
    require(decision['next_parent_policy_id'] == chosen['policy_id'] and decision['parent_policy_id'] == parent['policy_id']
            and decision['candidate_policy_id'] == candidate['policy_id'], 'DECISION_POLICY')
    if 'promotion_exception_ref' in terminal:
        require(allow_exception, 'NESTED_EXCEPTION')
        authorization = read(terminal['promotion_exception_ref'])
        original_ref = terminal['original_automatic_terminal_ref']
        original = receipts(original_ref,read,allow_exception=False)
        require(authorization['original_automatic_terminal_ref'] == original_ref, 'EXCEPTION_ORIGINAL')
        require(rule['authorization_ref'] == terminal['promotion_exception_ref'] and
                protocol['promotion_exception_ref'] == terminal['promotion_exception_ref'], 'EXCEPTION_AUTHORITY')
        require(authorization['request_sha256'] == terminal['request_sha256'] and
                authorization['candidate_policy_id'] == candidate['policy_id'], 'EXCEPTION_SCOPE')
        require(terminal['outcome'] == 'PROMOTED' and original['outcome'] == 'ROLLED_BACK', 'EXCEPTION_OUTCOMES')
        for value in (terminal,summary,authorization,rule):
            require(type(value['human_scientific_decision_count']) is int and value['human_scientific_decision_count'] == 1
                    and value['automatic_promotion_claimed'] is False, 'EXCEPTION_DISCLOSURE')
        require(summary['original_automatic_terminal_ref'] == original_ref and summary['promotion_exception_ref'] == terminal['promotion_exception_ref'], 'EXCEPTION_SUMMARY')
        original_summary = read(original['summary_ref'])
        require(summary['native_paired_results_ref'] == original_summary['native_paired_results_ref'], 'EXCEPTION_EVIDENCE')
        require(audit['original_identity_audit_ref'] == original_summary['identity_audit_ref'], 'EXCEPTION_AUDIT')
    else:
        require(terminal['human_scientific_decision_count'] == 0, 'AUTOMATIC_DISCLOSURE')
    # The decision is a closed immutable artifact. Do not call decide/freezer.
    require(decision['decision'] == ('PROMOTE' if terminal['outcome'] == 'PROMOTED' else 'ROLLBACK'), 'DECISION_OUTCOME')
    return terminal


@contextmanager
def installed(authority, identity):
    import entry.driver as driver_module
    import offoff_binding.execute as execution
    from continuity_binding.api import read_ref
    from exact_bindings import immutable_json
    original = driver_module.ExistingComponentRoundDriver.validate_result
    def validate(driver,start,result):
        require(Path(driver.owner_root) == Path(authority['owner_root']), 'REGISTERED_OWNER')
        if result['outcome'] not in ('PROMOTED','ROLLED_BACK'):
            return original(driver,start,result)
        closure = closed_transition(driver,start,result)
        if closure is None:
            return original(driver,start,result)
        native = execution.validate_completed_offoff_terminal
        def reuse(ref):
            if ref != result['terminal_ref']:
                return native(ref)
            receipts(ref,read_ref)
            return True
        with patch.object(execution,'validate_completed_offoff_terminal',reuse):
            answer = original(driver,start,result)
        immutable_json(Path(driver.owner_root)/'runtime_extensions'/identity/'closed_history'/
            (Path(result['attempt_root']).name+'.json'),
            {'schema_id':'REGISTERED_CLOSED_ROUND_RECEIPT_REUSE_V1','transition_ref':closure,
             'terminal_ref':result['terminal_ref'],'round_id':start['round_id'],
             'raw_episode_payloads_reaudited':False,'native_h44_tail_and_candidate_validation_preserved':True,
             'scientific_decision_recomputed':False,'directory_discovery_used':False})
        return answer
    with patch.object(driver_module.ExistingComponentRoundDriver,'validate_result',validate):
        yield
