"""Registered native renderer and child composition replay. No provider or jobs."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,sys,ast,hashlib,importlib.util
import closure_entry

def server():
    root=closure_entry.ROOT;identity=closure_entry.verify();a=json.loads((root/'AUTHORITY.json').read_bytes())
    from repair_feedback import checked,sha,group_scope,eligible,prior_facts
    from trajectory_facts import project,researcher_summary
    from repair_guidance import PRE_GUIDANCE,POST_GUIDANCE
    prior=Path(a['repair_predecessor']['root']);manifest=prior/'PACKAGE_FILES.sha256'
    assert sha(manifest)==a['repair_predecessor']['manifest_sha256']
    for source in [a['repair_predecessor'],*a['repair_sources'].values()]:
        p=Path(source['root']);assert sha(p/'PACKAGE_FILES.sha256')==source['manifest_sha256']
        for line in (p/'PACKAGE_FILES.sha256').read_text().splitlines():
            h,n=line.split(maxsplit=1);assert sha(p/n)==h
    previous=json.loads((prior/'SERVER_VALIDATION.json').read_bytes())
    assert previous['closed_history_validator_verified'] and previous['pre_lossless_verified']
    for r in a['group_interface_refs']:assert sha(r['path'])==r['sha256']
    sys.path.insert(0,a['native_entry_root']);sys.path.insert(0,str(Path(a['native_entry_root'])/'live_adapter'))
    sys.path.insert(0,str(Path(a['scientific_repo_root'])/'src'))
    sys.path.insert(0,a['repair_sources']['promotion_exception']['root'])
    sys.path.insert(0,a['repair_sources']['promotion']['root'])
    sys.path.insert(0,a['repair_sources']['planner_context']['root'])
    from pchsi.cognitive_runtime import request_renderer as rr,orchestrator as orch,registry_runner as reg
    from pchsi.reference_loop.canonical import domain_hash
    from group_prompt import rendering_scope as old_group
    from pre_context import rendering_scope as pre_scope,restore,canonical
    from exact_bindings import immutable_json
    authority={'path':str(root/'AUTHORITY.json'),'sha256':sha(root/'AUTHORITY.json')}
    core=SimpleNamespace(api={'render_stage_request':rr.render_stage_request},rr=rr,orch=orch,runner=reg,domain_hash=domain_hash)
    reports=[]
    for f in json.loads((root/'GROUP_REQUEST_FIXTURES.json').read_bytes()):
        old=f['bundle'];projection=old['input_projection'];assert rr.render_stage_request(stage_id=old['stage_id'],projection=projection)==old
        with group_scope(core),old_group(core,authority):
            values=[fn(stage_id=old['stage_id'],projection=projection) for fn in [core.api['render_stage_request'],rr.render_stage_request,orch.render_stage_request,reg.render_stage_request]]
            assert all(v==values[0] for v in values)
            v=values[0];assert v['provider_request']['text']==old['provider_request']['text']
            assert v['request_body_sha256']==domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',v['provider_request'])
            reports.append({'stage':old['stage_id'],'hash':v['request_body_sha256'],'all_aliases_equal':True})
    binding=checked(a['repair_binding_ref']);assert eligible(a,binding)
    request=checked(binding['refs']['request']);facts=prior_facts(a,request,root/'verification',identity)
    # Replay largest previous PRE through the actual native guard, with all prior facts.
    prior_binding=checked(a['recovery_binding_ref']);pre=Path(prior_binding['output_root'])/'pre'
    projection=json.loads((pre/'V1232V_PRE_PROJECTION_V1.json').read_bytes());projection['blind_input']['prior_closed_round_trajectory_facts']=facts
    manifest=json.loads((pre/'EXACT_RUNTIME_MANIFEST.json').read_bytes())
    native_rr=rr.render_stage_request
    def render(**kwargs):
        value=native_rr(**kwargs);value['provider_request']['input'][0]['content'][0]['text']+=PRE_GUIDANCE
        value['request_body_sha256']=domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',value['provider_request']);return value
    tree=ast.parse(Path(a['pre_context_overlay_ref']['path']).read_text());gate=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='render')
    source_authority=checked(a['pre_context_source_authority_ref'])
    universe=json.loads((Path(prior_binding['output_root'])/'group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json').read_bytes())
    with patch.object(rr,'load_runtime_manifest',lambda *x,**kw:manifest),patch.object(rr,'render_stage_request',render),pre_scope(core,a['pre_context_encoding_policy'],authority):
        ns={'native_render':rr.render_stage_request,'view':projection['blind_input']['analyzer_evidence_view'],
            'authority':source_authority,'canonical':canonical,'immutable_json':immutable_json,'Path':Path,
            'out':root/'verification','source_ref':authority,'universe':universe}
        exec(compile(ast.Module(body=[gate],type_ignores=[]),str(a['pre_context_overlay_ref']['path']),'exec'),ns)
        rendered=ns['render'](stage_id='R-PRE-PRIMARY-V2',projection=projection)
        assert rendered==orch.render_stage_request(stage_id='R-PRE-PRIMARY-V2',projection=projection)
        doc=json.loads(rendered['provider_request']['input'][1]['content'][0]['text'])
        assert restore(doc['projection'],doc['encoding']['file_ref_roots'])==projection
    # Full native POST compactor with registered R4 evidence, then current summary.
    import post_context
    context_a=json.loads((Path(a['repair_sources']['planner_context']['root'])/'AUTHORITY.json').read_bytes())
    ref=context_a['post_compactor_ref'];raw=Path(ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['file_sha256']
    post=checked(a['repair_post_projection_ref']);view=post_context.compact_projection(post,{'source':raw.decode(),'sha256':ref['file_sha256']})
    view['registered_trajectory_facts']=researcher_summary(project(post['environment_result_package']))
    # Child installer composes with the exact existing recipe hook and compact module.
    sys.path.insert(0,a['repair_sources']['recipe_contract']['root']);import recipe_worker,recipe_contract
    assert 'original(*args)' in Path(recipe_worker.__file__).read_text()
    assert hasattr(recipe_contract,'install') and post_context.renderer.__globals__['compact_projection'] is post_context.compact_projection
    from semantic_adoption import adopt
    checked(a['semantic_terminal_ref'])
    def forbidden(call):raise AssertionError('NO_NATIVE_PARTIAL_REJECTION_OR_RESEND')
    semantic_result=adopt(Path(a['semantic_terminal_ref']['path']).parent,forbidden,domain_hash)
    assert semantic_result['status']=='SEMANTIC_INVALID' and semantic_result['reused_terminal']
    assert not semantic_result['same_logical_call_resend_authorized']
    sys.path.insert(0,a['repair_sources']['durable_transport']['root']);import transport_worker
    assert 'with installed_transport(a,identity):return module.main()' in Path(transport_worker.__file__).read_text()
    result={'schema_id':'REGISTERED_REPAIR_FEEDBACK_NATIVE_VALIDATION_V1','manifest_sha256':identity,
        'closed_history_validator_verified':True,'group_interface_replay_verified':True,'repair_feedback_verified':True,
        'pre_lossless_verified':True,'current_closed_round_facts':len(facts['rounds']),
        'pre_bytes':len(canonical(rendered['provider_request'])),'post_augmented_projection_bytes':len(canonical(view)),
        'native_pre_gate_passed':True,'group_alias_replays':reports,'registered_recipe_child_import_verified':True,
        'native_semantic_invalid_terminal_reused':semantic_result,
        'durable_post_worker_preserved':True,
        'source_post_state_results_unchanged':view['environment_result_package']['state_results']==post['environment_result_package']['state_results'],
        'previous_validation_ref':{'path':str(prior/'SERVER_VALIDATION.json'),'sha256':sha(prior/'SERVER_VALIDATION.json')},
        'provider_calls':0,'slurm_submissions':0,'git_mutation_count':0}
    (root/'SERVER_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':server()
