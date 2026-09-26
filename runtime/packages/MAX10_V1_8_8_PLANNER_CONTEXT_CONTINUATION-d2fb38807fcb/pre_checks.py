"""Exercise actual registered PRE renderer with current evidence, without a send."""
from pathlib import Path
from unittest.mock import patch
import json,shutil,sys
from context_entry import load,ROOT

def main():
    a,prior,identity,prepared=load()
    import adapter,pre_overlay,pre_stage
    from exact_bindings import read_json,immutable_json,file_ref
    f=read_json(ROOT/'TEST_CHAIN.json');binding=f['binding'];values=adapter.validate_binding(binding)
    core=adapter.load_cores(binding);binding['_request']=values['request']
    out=Path(a['owner_root'])/'runtime_extensions'/identity/'verification/pre';group=out/'group'
    for filename,field in [('ANALYZER_CAPABILITY_PROFILE_V1.json','capability'),('ANALYZER_POLICY_BEHAVIOR_PROFILE_V1.json','behavior')]:
        immutable_json(group/filename,f[field])
    calls=iter(f['calls'])
    def fake_execute(**kwargs):return next(calls)['result']
    def replay_groups(binding,values,core,prepared,accesses,out):
        for call in f['calls']:core.u.execute_or_reuse(stage_id=call['stage'],condition_id=call['condition'])
        return f['tail'],f['universe']
    class NoSend(Exception):pass
    captured={}
    def stop(**kwargs):
        assert kwargs['stage_id']=='R-PRE-PRIMARY-V2'
        projection=kwargs['projection'];captured.update(projection=projection)
        # Compare renderer's direct alias used by native execute_one to the
        # controller-rendered request before allowing any transport side effect.
        b=core.orch.render_stage_request(stage_id=kwargs['stage_id'],projection=projection)
        proof=read_json(out/'pre/READABLE_PRE_REQUEST_PREFLIGHT.json')
        if b['request_body_sha256']!=proof['request_body_sha256']:raise AssertionError('PRE_NATIVE_RENDER_ALIAS_MISMATCH')
        captured['request_body_sha256']=b['request_body_sha256'];raise NoSend()
    with patch.object(adapter,'run_group_tail',replay_groups),patch.object(core.u,'execute_or_reuse',fake_execute),\
         patch.object(pre_overlay,'enabled',lambda *args:True),pre_overlay.install(a,file_ref(ROOT/'PACKAGE_FILES.sha256')),\
         patch.object(core.orch,'execute_one',stop):
        tail,universe=adapter.run_group_tail(binding,values,core,f['prepared'],f['accesses'],group)
        try:adapter.run_pre(binding,values,core,tail,universe,out/'pre')
        except NoSend:pass
    if not captured:raise AssertionError('PRE_NO_SEND_ENTRY_NOT_REACHED')
    view=captured['projection']['blind_input']['analyzer_evidence_view']
    assert all(row['task_family'] for row in captured['projection']['blind_input']['registered_candidate_universe']['pair_table'])
    for ref in a['preserved_refs'].values():
        from continuation import read_ref
        read_ref(ref)
    print(json.dumps({'status':'NEXT_ROUND_PRE_REAL_RENDER_NO_SEND_PASS','request_body_sha256':captured['request_body_sha256'],
        'view_sha256':view['view_sha256'],'public_context_count':len(view['source_contexts']),
        'local_findings':len(view['local_findings']),'groups':len(view['group_findings']),
        'component_attributions':len(view['component_attributions']),'crosschecks':len(view['crosschecks']),
        'provider_calls':0,'current_round_pre_unchanged':True,'fixture_scope':'CURRENT_EVIDENCE_SIMULATED_NEXT_ROUND_RENDER_ONLY'}),flush=True)
if __name__=='__main__':main()
