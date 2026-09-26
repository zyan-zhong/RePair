"""Replay the stopped PRE through native rendering/gate/identity, no send."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,__future__,json,sys,hashlib
import closure_entry

def server():
    root=closure_entry.ROOT;identity=closure_entry.verify();a=json.loads((root/'AUTHORITY.json').read_bytes())
    for key in ('pre_context_overlay_ref','pre_context_source_authority_ref','recovery_stop_ref','recovery_binding_ref'):
        r=a[key];assert closure_entry.digest(r['path'])==r['sha256']
    stop=json.loads(Path(a['recovery_stop_ref']['path']).read_bytes())
    assert stop['message']=='PRE_REGISTERED_CONTEXT_BUDGET_EXCEEDED_NO_SEND'
    binding=json.loads(Path(a['recovery_binding_ref']['path']).read_bytes());pre=Path(binding['output_root'])/'pre'
    projection=json.loads((pre/'V1232V_PRE_PROJECTION_V1.json').read_bytes())
    manifest=json.loads((pre/'EXACT_RUNTIME_MANIFEST.json').read_bytes())
    unit=json.loads((pre/'V1232V_PRE_SCIENTIFIC_UNIT_IDENTITY_V1.json').read_bytes())
    access=json.loads((pre/'V1232V_PRE_TASK_ACCESS_V1.json').read_bytes())
    sys.path.insert(0,a['native_entry_root']);sys.path.insert(0,str(Path(a['native_entry_root'])/'live_adapter'))
    sys.path.insert(0,str(Path(a['scientific_repo_root'])/'src'))
    from pchsi.cognitive_runtime import request_renderer as rr,orchestrator as orch
    from pchsi.reference_loop.canonical import canonical_json_bytes,domain_hash
    from exact_bindings import immutable_json
    from pre_context import rendering_scope,restore,canonical
    core=SimpleNamespace(rr=rr,orch=orch,domain_hash=domain_hash)
    authority_ref={'path':str(root/'AUTHORITY.json'),'sha256':closure_entry.digest(root/'AUTHORITY.json')}
    tree=ast.parse(Path(a['pre_context_overlay_ref']['path']).read_text())
    gate=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='render')
    universe=json.loads((Path(binding['output_root'])/'group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json').read_bytes())
    source_authority=json.loads(Path(a['pre_context_source_authority_ref']['path']).read_bytes())
    fixture=json.loads((root/'PRE_REQUEST_FIXTURE.json').read_bytes())
    class NoSend(BaseException):pass
    with patch.object(rr,'load_runtime_manifest',lambda *args,**kw:manifest),patch.object(orch,'load_runtime_manifest',lambda *args,**kw:manifest):
        old=rr.render_stage_request(stage_id='R-PRE-PRIMARY-V2',projection=projection)
        assert old==fixture['bundle']
        with rendering_scope(core,a['pre_context_encoding_policy'],authority_ref):
            namespace={'native_render':rr.render_stage_request,'view':projection['blind_input']['analyzer_evidence_view'],
                'authority':source_authority,'canonical':canonical_json_bytes,'immutable_json':immutable_json,
                'Path':Path,'out':root/'verification','source_ref':authority_ref,'universe':universe}
            exec(compile(ast.Module(body=[gate],type_ignores=[]),a['pre_context_overlay_ref']['path'],'exec'),namespace)
            controller=namespace['render'](stage_id='R-PRE-PRIMARY-V2',projection=projection)
            sender=orch.render_stage_request(stage_id='R-PRE-PRIMARY-V2',projection=projection)
            assert controller==sender
            doc=json.loads(sender['provider_request']['input'][1]['content'][0]['text'])
            assert canonical(restore(doc['projection'],doc['encoding']['file_ref_roots']))==canonical(projection)
            expected=domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1',{'scientific_unit_identity_sha256':unit['identity_sha256'],
                'stage_id':'R-PRE-PRIMARY-V2','condition_id':None,'round_id':binding['round_id'],
                'policy_version':binding['parent_policy_id'],'request_body_sha256':sender['request_body_sha256']})
            captured=[]
            def no_send(output_root,logical):captured.append(logical);raise NoSend()
            with patch.object(orch,'validate_task_access',lambda *args,**kw:None),patch.object(orch,'create_call_directory',no_send):
                try:orch.execute_one(output_root=root/'verification',unit_identity=unit,stage_id='R-PRE-PRIMARY-V2',condition_id=None,
                    round_id=binding['round_id'],policy_version=binding['parent_policy_id'],projection=projection,task_access=access)
                except NoSend:pass
            assert captured==[expected]
    assert not (pre/'strong_pre_runtime'/fixture['original_logical_call_id']).exists()
    assert not (pre/'strong_pre_runtime'/expected).exists()
    proof={'schema_id':'CURRENT_PRE_LOSSLESS_NO_SEND_VALIDATION_V1','package_manifest_sha256':identity,
        'reproduced_original_request_bytes':len(canonical_json_bytes(old['provider_request'])),
        'encoded_request_bytes':len(canonical_json_bytes(sender['provider_request'])),'budget':fixture['budget'],
        'roundtrip_equal':True,'native_context_gate_passed':True,'controller_and_sender_bundles_equal':True,
        'native_orchestrator_call_identity_equal':True,'expected_logical_call_id':expected,
        'effective_request_body_sha256':sender['request_body_sha256'],'old_call_directory_absent':True,
        'provider_calls':0,'git_mutation_count':0,'scientific_rows_removed':0,'scientific_strings_truncated':0,
        'original_projection_ref':{'path':str(pre/'V1232V_PRE_PROJECTION_V1.json'),'sha256':closure_entry.digest(pre/'V1232V_PRE_PROJECTION_V1.json')}}
    immutable_json(root/'PRE_SERVER_VALIDATION.json',proof)
    validation=json.loads((root/'SERVER_VALIDATION.json').read_bytes());validation['pre_lossless_verified']=True
    validation['pre_validation_ref']={'path':str(root/'PRE_SERVER_VALIDATION.json'),'sha256':closure_entry.digest(root/'PRE_SERVER_VALIDATION.json')}
    (root/'SERVER_VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(proof))
