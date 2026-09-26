from pathlib import Path
import subprocess,sys,json,time,uuid
import closure_entry
ROOT=Path(__file__).resolve().parent

def server():
    from unittest.mock import patch
    before=time.monotonic();identity=closure_entry.verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    # V199's full scientific installer/worker preparation is already sealed.
    # Validate only this recovery change, without rebuilding historical repair cores.
    sys.path.insert(0,a['native_entry_root']);sys.path.insert(0,str(Path(a['scientific_repo_root'])/'src'))
    for row in a['native_entry_refs']:
        assert closure_entry.digest(row['path'])==row['sha256']
    proof_ref=a['predecessor_full_preparation_ref']
    assert closure_entry.digest(proof_ref['path'])==proof_ref['sha256']
    prior_proof=json.loads(Path(proof_ref['path']).read_bytes())
    assert prior_proof['manifest_sha256']==a['predecessor_manifest_sha256']
    import importlib.util
    from environment_deadline import loader
    envref=a['environment_loader_source_ref']
    spec=importlib.util.spec_from_file_location('_registered_environment_deadline_validation',envref['path'])
    env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)
    with patch.object(env,'load_environment',loader(a,env)):
        with env.environment_scope(a['environment_initialization']) as environment_proof:
            assert environment_proof['initialized'] and environment_proof['credential_present']
    import entry.campaign_owner as owner
    from closed_history import closed_transition,receipts
    from continuity_binding.api import read_ref
    fixture=json.loads((ROOT/'CLOSED_FIXTURE.json').read_bytes());terminal_ref=fixture['terminal_ref']
    result=owner._read(Path(a['owner_root'])/'attempts'/a['verification_closed_attempt']/'RESULT.json')
    event=owner._read(Path(a['owner_root'])/'transitions'/(a['verification_closed_attempt']+'.json'))
    binding=owner._read(Path(a['owner_root'])/'OWNER_BINDING.json')
    from types import SimpleNamespace
    driver=SimpleNamespace(owner_root=Path(a['owner_root']),source_identity_sha256=binding['native_driver_source_sha256'],initial=binding['initial'])
    closure=closed_transition(driver,event['start'],result)
    assert result['terminal_ref']==terminal_ref
    receipts(terminal_ref,read_ref)
    proof={'schema_id':'REGISTERED_CLOSED_HISTORY_VALIDATION_V1','manifest_sha256':identity,
        'transition_ref':closure,'terminal_ref':terminal_ref,'real_exception_receipt_chain_verified':True,
        'closed_history_validator_verified':True,'predecessor_full_preparation_ref':proof_ref,
        'unchanged_predecessor_preparation_reused':True,'scientific_execution_started':False,
        'registered_environment_initialization':environment_proof,'environment_deadline_seconds':a['environment_policy']['initialization_timeout_seconds'],
        'raw_episode_payloads_reaudited':False,'provider_calls':0,'slurm_jobs_submitted':0,
        'git_mutation_count':0,'seconds':time.monotonic()-before}
    (ROOT/'SERVER_VALIDATION.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))

if __name__=='__main__':
    closure_entry.verify()
    p=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(ROOT/'test_pre_context.py'),str(ROOT/'test_x_prompt.py'),str(ROOT/'test_group_prompt.py'),str(ROOT/'test_closed_history.py'),str(ROOT/'test_environment_deadline.py')],cwd=ROOT)
    if p.returncode:raise SystemExit(p.returncode)
    if '--server' in sys.argv:
        from group_verify import server as group_server
        group_server()
        from pre_verify import server as pre_server
        pre_server()
    print('GROUP_REPAIR_COMPLETENESS_VERIFY_PASS')
