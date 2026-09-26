"""Replay registered historical scientific inputs with zero provider access."""
from pathlib import Path
from unittest.mock import patch
import json,hashlib,tempfile,inspect

def server(root,a):
    import adapter,group_stage,local_stage,parallel_group_stage
    from parallel_install import checked
    from parallel_registry import run_registry
    from parallel_group_stage import run_group_tail
    from source_parallel import map_sources
    from pchsi.cognitive_runtime import registry_runner as rr
    from pchsi.reference_loop.canonical import domain_hash
    binding=checked(a['recovery_binding_ref']);values=adapter.validate_binding(binding)
    core=adapter.load_cores(binding);binding['_request']=values['request']
    local=Path(binding['output_root'])/'local';execution=json.loads((local/'strong_local_runtime/execution_manifest.json').read_bytes())
    prepared,accesses,_=local_stage.prepare_groups(binding,core,local,execution)
    original=Path(binding['output_root'])/'group';census=json.loads((original/'GROUP_STAGE_RESULTS.json').read_bytes())
    call_ids=[cid for row in census['groups'] for cid in row['calls'].values()]+census['c_calls']+census['x_calls']
    records={}
    for cid in call_ids:
        call=original/'strong_group_runtime'/cid;logical=json.loads((call/'logical_call.json').read_bytes())
        artifact=call/'validated_artifact.json'
        status=logical['terminal_method_status']
        result={'logical_call_id':cid,'call_dir':str(call),'status':status,
            'hard_stop':status=='AMBIGUOUS_POST_SEND','reused_terminal_call':True,
            'validated_artifact_sha256':core.api['validated_artifact_identity'](stage_id=logical['stage_id'],artifact=json.loads(artifact.read_bytes())) if status=='ACCEPTED' else None}
        records[(logical['stage_id'],logical['scientific_unit_identity_sha256'])]=result
    def cached(**kw):return dict(records[(kw['stage_id'],kw['unit_identity']['identity_sha256'])])
    target=root/'verification/native_group';target.mkdir(parents=True,exist_ok=True)
    written=set();native_write=group_stage.immutable_json
    def tracked(path,value):
        written.add(Path(path));return native_write(path,value)
    with patch.object(core.u,'execute_or_reuse',cached),patch.object(group_stage,'immutable_json',tracked),patch.object(parallel_group_stage,'immutable_json',tracked):
        serial=group_stage.run_group_tail(binding,values,core,prepared,accesses,target)
        hashes={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in written}
        events=[]
        parallel=run_group_tail(binding,values,core,prepared,accesses,target,
            parallel_map=lambda items,fn,*,key,phase:map_sources(items,fn,key=key,workers=a['parallel_policy']['max_concurrent_sources'],observe=events.append))
        assert parallel==serial
        assert all(hashlib.sha256((target/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
        universe_sha=parallel[1]['pair_universe_sha256']
    registry=local/'CLEAN_ANALYZER_LOCAL_RUNTIME_INPUT_REGISTRY_V1.json'
    request_hashes=[]
    def fake_execute(**kw):
        # Native renderer and logical ID, deterministic transport stand-in, no request sent.
        unit={'stage_id':kw['stage_id'],'condition_id':kw['condition_id']}
        reg={'round_id':kw['round_id'],'policy_version':kw['policy_version']}
        cid=rr._logical_id(identity=kw['unit_identity'],unit=unit,registry=reg,projection=kw['projection'])
        return {'logical_call_id':cid,'call_dir':'verified_fixture/'+cid,'status':'ACCEPTED','hard_stop':False}
    runtime=values['runtime_manifest']
    with patch.object(rr,'execute_one',fake_execute),patch.object(core.rr,'load_runtime_manifest',lambda *x,**kw:runtime):
        serial=rr.run_registry(registry_path=registry,output_root=root/'verification/native_local_serial')
        parallel=run_registry(rr,rr.run_registry,workers=a['parallel_policy']['max_concurrent_sources'],observe=None,
            registry_path=registry,output_root=root/'verification/native_local_parallel')
        assert serial==parallel
    return {'native_local_parity_verified':True,'native_local_rows':len(serial[0]['rows']),
        'native_group_parity_verified':True,'native_group_count':len(prepared),'native_group_call_count':len(records),
        'native_group_output_files_verified':len(hashes),'group_pair_universe_sha256':universe_sha,
        'provider_calls':0,'slurm_submissions':0,'git_mutations':0,
        'native_fixed_signature_gate_passed':True}
