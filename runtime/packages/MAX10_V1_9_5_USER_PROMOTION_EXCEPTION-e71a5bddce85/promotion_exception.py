"""One explicitly authorized intervention; preserve the original automatic result."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import inspect,textwrap

ROOT=Path(__file__).resolve().parent

def check_scope(authorization,terminal,summary,candidate,original_ref):
    checks=(authorization.get('schema_id')=='USER_AUTHORIZED_CURRENT_CANDIDATE_PROMOTION_EXCEPTION_REQUEST_V1',
        type(authorization.get('human_scientific_decision_count')) is int and authorization['human_scientific_decision_count']==1,
        authorization.get('automatic_promotion_claimed') is False,
        authorization.get('original_automatic_terminal_ref')==original_ref,
        terminal.get('schema_id')=='CURRENT_NATIVE_OFFOFF_TERMINAL_V1',terminal.get('outcome')=='ROLLED_BACK',
        terminal.get('human_scientific_decision_count')==0,terminal.get('benchmark_feedback_used') is False,
        summary.get('memory_state')=='OFF',summary.get('harness_state')=='OFF',summary.get('evidence_access_class')=='TRAIN_SELECT',
        summary.get('benchmark_feedback_used') is False,
        authorization.get('candidate_policy_id')==summary.get('candidate_policy_id')==candidate.get('policy_id'),
        authorization.get('request_sha256')==terminal.get('request_sha256')==summary.get('request_sha256')==candidate.get('request_sha256'),
        bool(candidate.get('artifact_sha256')))
    if not all(checks):raise ValueError('USER_PROMOTION_EXCEPTION_SCOPE_OR_DISCLOSURE')
    return True

def inputs(a):
    from continuity_binding.api import read_ref
    auth=read_ref(a['authorization_ref']);original_ref=auth['original_automatic_terminal_ref'];original=read_ref(original_ref)
    summary=read_ref(original['summary_ref']);binding=read_ref(original['binding_ref']);candidate=read_ref(binding['input_refs']['candidate_ref'])
    check_scope(auth,original,summary,candidate,original_ref)
    return auth,original,summary,binding,candidate

def decide(*,frozen_rule,aggregate):
    from continuity_binding.api import read_ref
    rule=frozen_rule
    if rule.get('schema_id')!='USER_AUTHORIZED_ONE_TIME_PROMOTION_RULE_V1' or rule.get('automatic_promotion_claimed') is not False or rule.get('frozen_before_outcomes') is not False:
        raise ValueError('EXCEPTION_RULE_DISCLOSURE')
    a={'authorization_ref':rule['authorization_ref']};auth,old,summary,binding,candidate=inputs(a)
    expected={**summary,'frozen_protocol_ref':aggregate['frozen_protocol_ref'],'identity_audit_ref':aggregate['identity_audit_ref'],
        'promotion_exception_ref':a['authorization_ref'],'original_automatic_terminal_ref':auth['original_automatic_terminal_ref'],
        'human_scientific_decision_count':1,'automatic_promotion_claimed':False}
    if aggregate!=expected:raise ValueError('EXCEPTION_EVALUATION_RESULT_CHANGED')
    protocol=read_ref(aggregate['frozen_protocol_ref'])
    if read_ref(protocol['promotion_rule_ref'])!=rule:raise ValueError('EXCEPTION_PROTOCOL_RULE')
    return {'decision':'PROMOTE','decision_rule_id':rule['decision_rule_id']}

def materialize(a):
    from continuity_binding.api import read_ref,write_once
    from parent_cache import ref
    from offoff_binding.native import Native
    from offoff_binding.materialize import materialize as bind,prepare
    from offoff_binding.execute import freeze_registered_promotion
    auth,old,summary,binding,candidate=inputs(a);sink=ROOT/'runtime/authorized_exception'
    protocol=read_ref(binding['input_refs']['protocol_ref'])
    rule={'schema_id':'USER_AUTHORIZED_ONE_TIME_PROMOTION_RULE_V1','decision_rule_id':'USER_AUTHORIZED_ONE_TIME_CANDIDATE_PROMOTION_'+a['authorization_ref']['sha256'],
        'authorization_ref':a['authorization_ref'],'original_automatic_terminal_ref':auth['original_automatic_terminal_ref'],
        'automatic_promotion_claimed':False,'frozen_before_outcomes':False,'human_scientific_decision_count':1,
        'decision_producer':{'source_ref':ref(Path(__file__)),'entrypoint':'decide'}}
    rule_ref=write_once(sink/'PROMOTION_EXCEPTION_RULE.json',rule)
    protocol_ref=write_once(sink/'PROTOCOL.json',{**protocol,'promotion_rule_ref':rule_ref,'promotion_exception_ref':a['authorization_ref']})
    native=Native.load(binding['native_repo_root'],binding['source_refs']+[ref(Path(__file__))])
    binding_ref=bind(native=native,**{**binding['input_refs'],'protocol_ref':protocol_ref},sink=sink/'binding')
    newbinding=read_ref(binding_ref);context=prepare(native=native,**newbinding['input_refs'])
    audit=read_ref(summary['identity_audit_ref'])
    if audit.get('schema_id')!='CURRENT_OFFOFF_COVERAGE_CUTOVER_AUDIT_V1' or audit['binding_ref']!=old['binding_ref']:raise ValueError('EXCEPTION_SOURCE_IDENTITY_AUDIT')
    audit_ref=write_once(sink/'restricted/NATIVE_IDENTITY_AUDIT.json',{**audit,'binding_ref':binding_ref,
        'original_identity_audit_ref':summary['identity_audit_ref'],'promotion_exception_ref':a['authorization_ref']})
    updated={**summary,'frozen_protocol_ref':protocol_ref,'identity_audit_ref':audit_ref,
        'promotion_exception_ref':a['authorization_ref'],'original_automatic_terminal_ref':auth['original_automatic_terminal_ref'],
        'human_scientific_decision_count':1,'automatic_promotion_claimed':False}
    summary_ref=write_once(sink/'TRAIN_SELECT_AGGREGATE.json',updated)
    promotion=freeze_registered_promotion(native=native,protocol=context['protocol'],aggregate=updated,summary_ref=summary_ref,parent=context['parent'],candidate=context['candidate'])
    promotion_ref=write_once(sink/'PROMOTION_DECISION.json',promotion.to_dict())
    return write_once(sink/'CURRENT_NATIVE_OFFOFF_TERMINAL.json',{**old,'binding_ref':binding_ref,'summary_ref':summary_ref,'promotion_ref':promotion_ref,
        'outcome':'PROMOTED','next_parent_policy_id':candidate['policy_id'],'next_parent_policy_artifact_sha256':candidate['artifact_sha256'],
        'promotion_exception_ref':a['authorization_ref'],'original_automatic_terminal_ref':auth['original_automatic_terminal_ref'],
        'human_scientific_decision_count':1,'automatic_promotion_claimed':False})

def overlay(function,replacements,extra):
    source=textwrap.dedent(inspect.getsource(function))
    for old,new in replacements:
        if source.count(old)!=1:raise ValueError('EXCEPTION_REGISTERED_SOURCE_ANCHOR:'+function.__name__)
        source=source.replace(old,new)
    namespace={**function.__globals__,**extra}
    exec(compile(source,str(ROOT/('registered_overlay_'+function.__name__+'.py')),'exec'),namespace)
    return namespace[function.__name__]

def scope_count(start,terminal,terminal_ref,auth,registered_terminal):
    if start['request_sha256']!=auth['request_sha256']:
        if terminal.get('promotion_exception_ref') is not None or terminal.get('human_scientific_decision_count',0)!=0:raise ValueError('EXCEPTION_CANNOT_APPLY_TO_OTHER_ROUND')
        return 0
    if terminal_ref!=registered_terminal:raise ValueError('EXCEPTION_CURRENT_TERMINAL_REQUIRED')
    return 1

def campaign_fields(result,authorization_ref,auth,registered_terminal):
    count=0
    if result is not None:
        if result.get('request_sha256')!=auth['request_sha256'] or result.get('terminal_ref')!=registered_terminal or result.get('promotion_exception_ref')!=authorization_ref or result.get('human_scientific_decision_count')!=1 or result.get('automatic_promotion_claimed') is not False:
            raise ValueError('CAMPAIGN_EXCEPTION_CLOSED_RESULT_MISMATCH')
        count=1
    return {'human_scientific_decision_count':count,'promotion_exception_authorization_ref':authorization_ref,
        'campaign_contains_user_promotion_exception':bool(count),'fully_unattended_scientific_selection_claimed':False if count else None}

@contextmanager
def installed(a):
    from continuity_binding.api import read_ref,read_bytes_ref
    import entry.tail as tail,entry.driver as driver,entry.campaign_owner as owner
    import entry.offoff_job as job,offoff_binding.execute as execution
    import entry.paper_export as paper
    for source in a['native_overlay_source_refs']:read_bytes_ref(source)
    original_validator=execution.validate_completed_offoff_terminal;original_jobs=job.execute_current_offoff_jobs
    auth,original,_,_,_=inputs(a)
    registered_terminal=materialize(a)
    def final_fields(root):
        if Path(root)!=Path(a['owner_root']):raise ValueError('EXCEPTION_CAMPAIGN_TERMINAL_OWNER')
        result_path=Path(a['authorized_round_result_path'])
        result=owner._read(result_path) if result_path.exists() else None
        return campaign_fields(result,a['authorization_ref'],auth,registered_terminal)
    def terminal_check(start,terminal_ref):
        terminal=read_ref(terminal_ref)
        return scope_count(start,terminal,terminal_ref,auth,registered_terminal)
    def disclosure(start,terminal_ref):
        if terminal_check(start,terminal_ref)==0:return {}
        return {'promotion_exception_ref':a['authorization_ref'],'original_automatic_terminal_ref':auth['original_automatic_terminal_ref'],
            'automatic_promotion_claimed':False,'campaign_contains_user_promotion_exception':True}
    def result_count(start,result):
        if result.get('outcome')=='PROTOCOL_INFRA_INVALID':
            if result.get('promotion_exception_ref') is not None:raise ValueError('EXCEPTION_CANNOT_PROMOTE_INVALID_ATTEMPT')
            return 0
        count=terminal_check(start,result['terminal_ref'])
        for key,value in disclosure(start,result['terminal_ref']).items():
            if result.get(key)!=value:raise ValueError('EXCEPTION_RESULT_DISCLOSURE_REQUIRED:'+key)
        return count
    def validate(ref):
        value=read_ref(ref)
        if 'promotion_exception_ref' not in value:return original_validator(ref)
        if value['promotion_exception_ref']!=a['authorization_ref'] or ref!=registered_terminal:raise ValueError('EXCEPTION_TERMINAL_SCOPE')
        original_validator(auth['original_automatic_terminal_ref'])
        return True
    def jobs(**kwargs):
        result=original_jobs(**kwargs)
        if result!=auth['original_automatic_terminal_ref']:return result
        read_ref(registered_terminal)
        return registered_terminal
    training=overlay(tail._training_terminal,[("'human_scientific_decision_count':0", "'human_scientific_decision_count':_exception_count(start, terminal_ref)")],{'_exception_count':terminal_check})
    with patch.object(tail,'_training_terminal',training):
        close=overlay(tail.close_round_tail,[("'human_scientific_decision_count':0", "'human_scientific_decision_count':_exception_count(start, terminal_ref)"),
            ('    validate_closed_round_tail(start=start, result=result)','    result.update(_exception_disclosure(start, terminal_ref))\n    validate_closed_round_tail(start=start, result=result)')],
            {'_exception_count':terminal_check,'_exception_disclosure':disclosure})
        check=overlay(owner._check_result,[("result['human_scientific_decision_count'] != 0","result['human_scientific_decision_count'] != _exception_result_count(start, result)")],{'_exception_result_count':result_count})
        campaign=overlay(owner.run_campaign,[("'human_scientific_decision_count':0}","**_exception_campaign_fields(root)}")],{'_exception_campaign_fields':final_fields,'_check_result':check})
        export=overlay(paper.export_attempt,[("'final_heldout_claim': False,", "'final_heldout_claim': False,\n             'campaign_promotion_exception_ref':_exception_authority_ref,\n             'campaign_contains_user_promotion_exception':True,\n             'current_round_is_user_exception':start['request_sha256']==_exception_request_sha,")],
            {'_exception_authority_ref':a['authorization_ref'],'_exception_request_sha':auth['request_sha256']})
        with patch.object(tail,'close_round_tail',close),patch.object(owner,'_check_result',check),patch.object(owner,'run_campaign',campaign),patch.object(paper,'export_attempt',export),patch.object(job,'execute_current_offoff_jobs',jobs),patch.object(execution,'validate_completed_offoff_terminal',validate):yield
