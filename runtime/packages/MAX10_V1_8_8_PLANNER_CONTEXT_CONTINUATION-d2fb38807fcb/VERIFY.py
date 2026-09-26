from pathlib import Path
import subprocess,sys,json
from context_entry import verify,ROOT

def main():
    identity=verify()
    result=subprocess.run([sys.executable,'-B',str(ROOT/'test_views.py')],check=False)
    if result.returncode:return result.returncode
    if '--server' in sys.argv:
        a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
        command=[sys.executable,'-B',str(ROOT/'post_worker.py'),'--verify','--request',a['preserved_refs']['h44_request']['path']]
        result=subprocess.run(command,check=False)
        if result.returncode:return result.returncode
        result=subprocess.run([sys.executable,'-B',str(ROOT/'pre_checks.py')],check=False)
        if result.returncode:return result.returncode
    print(json.dumps({'status':'REGISTERED_PLANNER_CONTEXT_VERIFY_PASS','manifest_sha256':identity,
        'provider_calls':0,'slurm_submissions':0,'git_mutation_count':0}),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
