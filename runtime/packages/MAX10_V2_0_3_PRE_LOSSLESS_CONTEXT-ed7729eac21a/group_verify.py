from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys,json,ast,inspect,__future__,re
import closure_entry
ROOT=Path(__file__).resolve().parent

def server():
    identity=closure_entry.verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());base=a['group_prompt_base']
    proof_ref=base['validation_ref']
    assert closure_entry.digest(proof_ref['path'])==proof_ref['sha256']
    proof=json.loads(Path(proof_ref['path']).read_bytes())
    assert proof['manifest_sha256']==base['manifest_sha256'] and proof['closed_history_validator_verified']
    prior_root=Path(base['source_root']);manifest=prior_root/'PACKAGE_FILES.sha256'
    assert closure_entry.digest(manifest)==base['manifest_sha256']
    for line in manifest.read_text().splitlines():
        expected,name=line.split(maxsplit=1);assert closure_entry.digest(prior_root/name)==expected
    for row in a['group_interface_refs']:assert closure_entry.digest(row['path'])==row['sha256']
    sys.path.insert(0,a['native_entry_root']);sys.path.insert(0,str(Path(a['native_entry_root'])/'live_adapter'))
    sys.path.insert(0,str(Path(a['scientific_repo_root'])/'src'))
    from pchsi.cognitive_runtime import request_renderer as rr,orchestrator as orch,registry_runner as reg
    from pchsi.reference_loop.canonical import domain_hash
    from exact_bindings import read_ref
    from group_prompt import rendering_scope
    binding=json.loads(Path(a['validation_group_binding_path']).read_bytes())
    u=binding['packages']['u'];raw=read_ref(u['manifest'],as_bytes=True)
    members={line.split(maxsplit=1)[1].lstrip('*'):line.split(maxsplit=1)[0] for line in raw.decode().splitlines()}
    path=Path(u['root'])/'v1232u_driver.py';assert closure_entry.digest(path)==members[path.name]
    tree=ast.parse(path.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    fn=functions['expected_logical_call_id'];namespace={'Path':Path}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec',flags=__future__.annotations.compiler_flag),namespace)
    expected_id=namespace['expected_logical_call_id']
    authority_ref={'path':str(ROOT/'AUTHORITY.json'),'sha256':closure_entry.digest(ROOT/'AUTHORITY.json')}
    core=SimpleNamespace(api={'render_stage_request':rr.render_stage_request},rr=rr,orch=orch,runner=reg,domain_hash=domain_hash)
    reports=[]
    class Captured(BaseException):pass
    for row in json.loads((ROOT/'GROUP_REQUEST_FIXTURES.json').read_bytes()):
        old=row['bundle'];stage=old['stage_id'];projection=old['input_projection']
        fresh=rr.render_stage_request(stage_id=stage,projection=projection)
        assert fresh==old
        with rendering_scope(core,authority_ref):
            values=[f(stage_id=stage,projection=projection) for f in [core.api['render_stage_request'],rr.render_stage_request,orch.render_stage_request,reg.render_stage_request]]
            assert all(v==values[0] for v in values);value=values[0]
            assert value['provider_request']['text']==old['provider_request']['text']
            assert value['input_projection']==old['input_projection']
            unit={'identity_sha256':'a'*64};condition=stage[2:] if stage.startswith('G-') else None
            inputs={'unit_identity':unit,'stage_id':stage,'condition_id':condition,'round_id':'registered-render-validation','policy_version':'registered-render-validation','projection':projection,'api':core.api,'domain_hash':domain_hash,'request_body_sha256':value['request_body_sha256']}
            predicted=expected_id(**{k:inputs[k] for k in inspect.signature(expected_id).parameters})
            captured=[]
            def stop(root,logical):captured.append(logical);raise Captured()
            with patch.object(orch,'validate_task_access',lambda *args,**kwargs:None),patch.object(orch,'create_call_directory',stop):
                try:orch.execute_one(output_root=ROOT/'verification',task_access={},**{k:inputs[k] for k in ['unit_identity','stage_id','condition_id','round_id','policy_version','projection']})
                except Captured:pass
            assert captured==[predicted]
            reports.append({'stage':stage,'base_hash':old['request_body_sha256'],'effective_hash':value['request_body_sha256'],'logical_call_id':predicted,'request_identity_routes_match':True})
    # The real current round's completed G/C calls must keep their cache identity.
    # Exact IDs come from the registered resident log, never directory discovery.
    native_nodes=[functions[n] for n in ('load_json','expected_logical_call_id','execute_or_reuse')]
    ns={'Path':Path,'json':json}
    exec(compile(ast.Module(body=native_nodes,type_ignores=[]),str(path),'exec',flags=__future__.annotations.compiler_flag),ns)
    from pchsi.cognitive_runtime.output_validation import validated_artifact_identity
    reused=[];runtime=Path(binding['output_root'])/'group/strong_group_runtime'
    def forbidden(**kwargs):raise AssertionError('NO_PROVIDER_ALLOWED_IN_REUSE_VERIFICATION')
    ids=[]
    for line in Path(a['prior_launch']['log_path']).read_text().splitlines():
        m=re.fullmatch(r'V1232U_CALL stage=(G-A2|G-A3|C|X) condition=\S+ status=ACCEPTED reused=\S+ logical_call_id=([0-9a-f]{64})',line)
        if m and m[2] not in ids:ids.append(m[2])
    with rendering_scope(core,authority_ref):
        for cid in ids:
            call_dir=runtime/cid;logical=json.loads((call_dir/'logical_call.json').read_bytes())
            if logical['round_id']!=binding['round_id']:continue
            old=json.loads((call_dir/'rendered_request.json').read_bytes());stage=old['stage_id']
            new=core.rr.render_stage_request(stage_id=stage,projection=old['input_projection'])
            assert new['provider_request']==old['provider_request']
            assert new['request_body_sha256']==logical['request_body_sha256']
            artifact=json.loads((call_dir/'validated_artifact.json').read_bytes())
            api={'render_stage_request':core.rr.render_stage_request,'execute_one':forbidden,
                 'validated_artifact_identity':validated_artifact_identity}
            got=ns['execute_or_reuse'](runtime_root=runtime,unit_identity={'identity_sha256':logical['scientific_unit_identity_sha256']},
                stage_id=stage,condition_id=logical['condition_id'],round_id=logical['round_id'],policy_version=logical['policy_version'],
                projection=old['input_projection'],task_access={},api=api,domain_hash=domain_hash)
            assert got['reused_terminal_call'] and got['logical_call_id']==cid and got['status']=='ACCEPTED'
            reused.append({'stage':stage,'logical_call_id':cid,'validated_artifact_sha256':got['validated_artifact_sha256']})
    assert {'G-A2','G-A3','C'}.issubset({r['stage'] for r in reused})
    result={'schema_id':'REGISTERED_GROUP_INTERFACE_VALIDATION_V1','manifest_sha256':identity,
        'closed_history_validator_verified':True,'group_interface_replay_verified':True,
        'reused_closed_history_validation_ref':proof_ref,'registered_u_identity_source_ref':{'path':str(path),'sha256':closure_entry.digest(path)},
        'replays':reports,'current_round_existing_terminals_reused':reused,
        'provider_calls':0,'slurm_submissions':0,'git_mutation_count':0}
    (ROOT/'SERVER_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
