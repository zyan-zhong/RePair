from pathlib import Path
import sys,json,subprocess,os
from recipe_entry import ROOT,verify

def server():
    from recipe_entry import load
    from post_recovery import materialize
    a,prior,identity,prepared=load()
    from exact_bindings import read_ref,immutable_json,file_ref
    index=materialize(a,identity,ROOT,publish=False);run=Path(index['execution_run_root'])
    request=read_ref(a['post_recovery_refs']['H44_ADAPTER_REQUEST.json'])
    request={**request,'run_root':str(run),'execute':True,'registered_recipe_source':file_ref(ROOT/'AUTHORITY.json')}
    path=run.parent/'POST_RECIPE_PREFLIGHT_REQUEST.json';immutable_json(path,request)
    r=subprocess.run([a['registered_python'],'-B',str(ROOT/'recipe_worker.py'),'--request',str(path),'--verify'],capture_output=True,text=True)
    print(r.stdout,flush=True)
    if r.returncode:raise ValueError('ACTUAL_POST_NO_SEND_PREFLIGHT:'+r.stderr[-16000:])
    if (run/'ROUND_EXECUTION_TERMINAL.json').exists() or (run/'SBATCH_SUBMISSION_INTENT.json').exists():raise ValueError('PREFLIGHT_SIDE_EFFECT')
    from post_recovery import check_original
    check_original(a)
    print('ORIGINAL_REJECTED_POST_AND_60_BRANCH_RESULTS_PRESERVED=true')

if __name__=='__main__':
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    base=Path(sys.argv[sys.argv.index('--base')+1]) if '--base' in sys.argv else Path(a['base_source_root'])
    base=base.resolve()
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT),str(base),str(base/'live_adapter')])}
    r=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'test_recipe_contract.py'),str(ROOT/'test_recovery_index.py')],cwd=ROOT,env=env)
    if r.returncode:raise SystemExit(r.returncode)
    if '--server' in sys.argv:server()
    print('PACKAGE_SHA_AND_POST_RECIPE_CONTRACT_VERIFY_PASS='+identity)
