from pathlib import Path
import sys,subprocess,json
from exception_entry import ROOT,verify,load

def server():
    a,prior,identity,prepared=load()
    from continuity_binding.api import read_ref,write_once
    from promotion_exception import installed,materialize,inputs
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    from entry.registration import build_deployment
    import hashlib
    base=Path(a['base_source_root']);deployment=build_deployment(base,entry_source_sha256=hashlib.sha256((base/'PACKAGE_FILES.sha256').read_bytes()).hexdigest())
    bootstrap_current_and_children(deployment['scientific_repo_root'])
    auth,old,summary,binding,candidate=inputs(a);start=read_ref(binding['input_refs']['request_ref'])
    old_bytes=Path(auth['original_automatic_terminal_ref']['path']).read_bytes()
    terminal_ref=materialize(a);terminal=read_ref(terminal_ref)
    assert terminal['human_scientific_decision_count']==1 and terminal['automatic_promotion_claimed'] is False
    assert terminal['next_parent_policy_id']==candidate['policy_id'] and terminal['outcome']=='PROMOTED'
    from entry import tail,campaign_owner,offoff_job
    from unittest.mock import patch
    # Original source fully re-audited through the deployed V194 validator; no model or Slurm invocation.
    with prior.install(prepared[0],prepared[2]),installed(a):
        from offoff_binding.execute import validate_completed_offoff_terminal
        validate_completed_offoff_terminal(terminal_ref)
        assert tail._training_terminal(start,terminal_ref)[0]==terminal
        result={**{k:start[k] for k in ('round_id','execution_attempt_id','request_sha256','parent_policy_id','parent_policy_artifact_sha256','round_start_memory_snapshot_sha256')},
            'outcome':'PROMOTED','human_scientific_decision_count':1,'benchmark_feedback_used':False,'invalid_attempt_adaptive_evidence_reuse':False,
            'terminal_ref':terminal_ref,'next_parent_policy_id':candidate['policy_id'],'next_parent_policy_artifact_sha256':candidate['artifact_sha256'],
            'promotion_exception_ref':a['authorization_ref'],'original_automatic_terminal_ref':auth['original_automatic_terminal_ref'],
            'automatic_promotion_claimed':False,'campaign_contains_user_promotion_exception':True}
        class Driver:
            def validate_result(self,start,result):assert result['human_scientific_decision_count']==1
        campaign_owner._check_result(start,result,Driver())
        assert campaign_owner.run_campaign.__globals__['_check_result'] is campaign_owner._check_result
        from promotion_exception import campaign_fields
        terminal_fields=campaign_fields(result,a['authorization_ref'],auth,terminal_ref)
        assert terminal_fields['human_scientific_decision_count']==1 and terminal_fields['campaign_contains_user_promotion_exception'] is True
        for change in ({'human_scientific_decision_count':0},{'automatic_promotion_claimed':True},{'next_parent_policy_artifact_sha256':start['parent_policy_artifact_sha256']}):
            try:campaign_owner._check_result(start,{**result,**change},Driver())
            except (ValueError,RuntimeError):pass
            else:raise AssertionError('INVALID_EXCEPTION_RESULT_ACCEPTED')
        other={**start,'request_sha256':'a'*64}
        try:tail._training_terminal(other,terminal_ref)
        except (ValueError,RuntimeError):pass
        else:raise AssertionError('EXCEPTION_LEAKED_INTO_ANOTHER_ROUND')
    assert Path(auth['original_automatic_terminal_ref']['path']).read_bytes()==old_bytes
    from research_memory import project,installed as research_installed
    history=read_ref(a['research_memory_bootstrap_closed_result_ref']);history_refs=history['stage_evidence_refs']
    lesson=project(start=history,result=history,post=read_ref(history_refs['post_artifact']),memory=read_ref(history_refs['memory_materialization']))
    assert lesson['researcher_post']['lesson'] and lesson['research_reference_only']
    with research_installed(a):pass
    print('REAL_CLOSED_R1_ANALYZER_AND_PLANNER_LESSON_PROJECTION_PASS',flush=True)
    from memory_regression import run as memory_regression
    memory_regression(a)
    receipt={'schema_id':'ONE_TIME_USER_PROMOTION_EXCEPTION_VALIDATION_V1','terminal_ref':terminal_ref,
        'authorization_ref':a['authorization_ref'],'original_automatic_terminal_preserved':True,'original_full710_native_audit_replayed':True,
        'native_tail_checks_passed':True,'owner_guard_and_disclosure_checks_passed':True,'model_calls':0,'slurm_submissions':0,'git_mutations':0}
    write_once(ROOT/'runtime/VALIDATION.json',receipt);print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    verify();code=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'test_exception.py'),str(ROOT/'test_research_memory.py')],cwd=ROOT).returncode
    if code:raise SystemExit(code)
    if '--server' in sys.argv:server()
    print('ONE_TIME_USER_PROMOTION_EXCEPTION_VERIFY_PASS',flush=True)
