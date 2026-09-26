from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,sys,subprocess,ast,hashlib
import context_entry as ce

def server():
    a,identity,prior,prepared,pc=ce.load()
    binding=ce.checked(a['context_recovery_binding_ref']);ce.checked(a['context_recovery_stop_ref'])
    root=Path(binding['output_root']);pre=root/'pre'
    read=lambda p:json.loads(p.read_bytes())
    refs=[]
    for p in [root/'group/GROUP_STAGE_RESULTS.json',root/'local/strong_local_runtime/execution_manifest.json',pre/'V1232V_PRE_PROJECTION_V1.json',pre/'EXACT_RUNTIME_MANIFEST.json']:
        refs.append({'path':str(p),'sha256':ce.digest(p)})
    groups=read(root/'group/GROUP_STAGE_RESULTS.json');calls=[c for row in groups['groups'] for c in row['calls'].values()]+groups['c_calls']+groups['x_calls']
    for cid in calls:
        path=root/'group/strong_group_runtime'/cid/'logical_call.json';logical=read(path)
        assert logical['round_id']==binding['round_id'] and logical['logical_call_id']==cid and logical['terminal_method_status']
        refs.append({'path':str(path),'sha256':ce.digest(path)})
    from pchsi.cognitive_runtime import request_renderer as rr,orchestrator as orch
    from pchsi.reference_loop.canonical import domain_hash
    from exact_bindings import immutable_json
    import pool_context
    projection=read(pre/'V1232V_PRE_PROJECTION_V1.json');manifest=read(pre/'EXACT_RUNTIME_MANIFEST.json');unit=read(pre/'V1232V_PRE_SCIENTIFIC_UNIT_IDENTITY_V1.json');access=read(pre/'V1232V_PRE_TASK_ACCESS_V1.json')
    core=SimpleNamespace(rr=rr,orch=orch,domain_hash=domain_hash)
    assert ce.digest(a['pre_context_overlay_ref']['path'])==a['pre_context_overlay_ref']['sha256']
    source=ce.checked(a['pre_context_source_authority_ref'])
    original_authority={'path':str(Path(a['context_pool_predecessor']['root'])/'AUTHORITY.json'),'sha256':ce.digest(Path(a['context_pool_predecessor']['root'])/'AUTHORITY.json')}
    policy=read(Path(original_authority['path']))['pre_context_encoding_policy']
    tree=ast.parse(Path(a['pre_context_overlay_ref']['path']).read_text());gate=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='render')
    universe=read(root/'group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json')
    class NoSend(BaseException):pass
    with patch.object(rr,'load_runtime_manifest',lambda *args,**kw:manifest),patch.object(orch,'load_runtime_manifest',lambda *args,**kw:manifest),ce.installed(a,identity,pc),pc.rendering_scope(core,policy,original_authority):
        ns={'native_render':rr.render_stage_request,'view':projection['blind_input']['analyzer_evidence_view'],'authority':source,'canonical':pool_context.canonical,'immutable_json':immutable_json,'Path':Path,'out':ce.ROOT/'verification','source_ref':original_authority,'universe':universe}
        exec(compile(ast.Module(body=[gate],type_ignores=[]),a['pre_context_overlay_ref']['path'],'exec'),ns)
        controller=ns['render'](stage_id='R-PRE-PRIMARY-V2',projection=projection)
        sender=orch.render_stage_request(stage_id='R-PRE-PRIMARY-V2',projection=projection)
        assert controller==sender
        doc=json.loads(sender['provider_request']['input'][1]['content'][0]['text'])
        assert pool_context.canonical(pool_context.restore(doc['projection'],doc['encoding']['file_ref_roots']))==pool_context.canonical(projection)
        cid=domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1',{'scientific_unit_identity_sha256':unit['identity_sha256'],'stage_id':'R-PRE-PRIMARY-V2','condition_id':None,'round_id':binding['round_id'],'policy_version':binding['parent_policy_id'],'request_body_sha256':sender['request_body_sha256']})
        seen=[]
        def capture(output_root,logical):seen.append(logical);raise NoSend()
        with patch.object(orch,'create_call_directory',capture):
            try:orch.execute_one(output_root=pre/'strong_pre_runtime',unit_identity=unit,stage_id='R-PRE-PRIMARY-V2',condition_id=None,round_id=binding['round_id'],policy_version=binding['parent_policy_id'],projection=projection,task_access=access)
            except NoSend:pass
        assert seen==[cid] and not (pre/'strong_pre_runtime'/cid).exists()
    pp=Path(a['parallel_runtime_ref']['root'])/'SERVER_VALIDATION.json';pv=read(pp)
    assert pv['manifest_sha256']==a['parallel_runtime_ref']['manifest_sha256'] and pv['native_group_parity_verified'] and pv['native_local_parity_verified']
    report={'manifest_sha256':identity,'registered_completed_analyzer_assets_verified':True,'native_sender_identity_verified':True,'native_context_gate_passed':True,'controller_sender_equal':True,'roundtrip_equal':True,'provider_calls':0,'git_mutations':0,'pre':{'request_bytes':len(pool_context.canonical(sender['provider_request'])),'budget':a['registered_context_window_tokens']-sender['provider_request']['max_output_tokens'],'request_body_sha256':sender['request_body_sha256'],'expected_logical_call_id':cid,'round_id':binding['round_id'],'encoding':sender['registered_pre_context_encoding']},'preserved_refs':refs,'registered_predecessor_validation_ref':{'path':str(pp),'sha256':ce.digest(pp)},'future_parallel_policy':prepared[0]['parallel_policy']}
    (ce.ROOT/'SERVER_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='preserved_refs'}),flush=True)

if __name__=='__main__':
    ce.verify();r=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(ce.ROOT)],cwd=ce.ROOT)
    if r.returncode:raise SystemExit(r.returncode)
    if '--server' in sys.argv:server()
