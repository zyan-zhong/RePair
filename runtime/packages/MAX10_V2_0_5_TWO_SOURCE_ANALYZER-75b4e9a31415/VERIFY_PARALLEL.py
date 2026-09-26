from pathlib import Path
import sys,json,subprocess,hashlib
from parallel_entry import ROOT,verify,load

def main():
    identity=verify()
    run=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(ROOT)],cwd=ROOT)
    if run.returncode:raise SystemExit(run.returncode)
    if '--server' in sys.argv:
        a,_,prior,prepared=load()
        # Same checked preparation tuple used by V204.prepared_once; deployment
        # supplies the original formal owner lock still held across recoveries.
        native_prepared=prepared[3][3][3][3][3]
        assert len(native_prepared)==6 and len(native_prepared[4])==7
        deployment=native_prepared[4][2]
        handoff_lock_paths=[str(Path(deployment['formal_state_root'])/'campaign_owner/.campaign_writer.lock')]
        previous=Path(a['parallel_predecessor']['root'])
        previous_proof=json.loads((previous/'SERVER_VALIDATION.json').read_bytes())
        assert previous_proof['manifest_sha256']==a['parallel_predecessor']['manifest_sha256']
        assert a['parallel_policy']['activation_round_index']>a['parallel_policy']['current_round_preserved']['round_index']
        from native_replay import server
        proof=server(ROOT,a)
        from parallel_install import installed
        import adapter
        # Exercise exact fixed-head API checks under the new wrappers, no execution.
        from parallel_install import checked,round_index
        binding=checked(a['repair_binding_ref'])
        assert round_index(a,binding)<a['parallel_policy']['activation_round_index']
        with installed(a,identity,ROOT):
            core=adapter.load_cores(binding)
            assert core.runner.run_registry.__wrapped__ is not None
        result={'schema_id':'ANALYZER_TWO_SOURCE_NATIVE_VALIDATION_V1','manifest_sha256':identity,**proof,
            'current_round_excluded':True,'handoff_lock_paths':handoff_lock_paths,
            'handoff_lock_source':'V204 hash-verified prepared deployment.formal_state_root',
            'registered_predecessor_validation_ref':{'path':str(previous/'SERVER_VALIDATION.json'),
                'sha256':hashlib.sha256((previous/'SERVER_VALIDATION.json').read_bytes()).hexdigest()}}
        (ROOT/'SERVER_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    print('TWO_SOURCE_VERIFY_PASS',identity)
if __name__=='__main__':main()
