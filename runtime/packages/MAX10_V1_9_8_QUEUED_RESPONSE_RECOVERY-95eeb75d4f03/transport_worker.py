from pathlib import Path
import sys,json,importlib.util
from transport_entry import ROOT,verify,digest,installed_transport

def main():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    source=a['post_worker_ref'];path=Path(source['path'])
    if digest(path)!=source['sha256']:raise ValueError('REGISTERED_POST_WORKER_CHANGED')
    request=json.loads(Path(sys.argv[sys.argv.index('--request')+1]).read_bytes())
    if request['scientific_repo_root']!=a['scientific_repo_root']:raise ValueError('REGISTERED_WORKER_REPO_CHANGED')
    if not Path(request['run_root']).is_relative_to(Path(a['owner_root'])):raise ValueError('REGISTERED_WORKER_OWNER_SCOPE')
    sys.path.insert(0,str(path.parent));sys.path.insert(0,str(Path(a['scientific_repo_root'])/'src'))
    spec=importlib.util.spec_from_file_location('_durable_existing_recipe_worker',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from durable_transport import once
    Path(request['run_root']).mkdir(parents=True,exist_ok=True)
    once(Path(request['run_root'])/'REGISTERED_DURABLE_TRANSPORT_WORKER.json',
        {'schema_id':'REGISTERED_DURABLE_POST_WORKER_ADOPTION_V1','transport_manifest_sha256':identity,
         'prior_worker_ref':source,'request_path':sys.argv[sys.argv.index('--request')+1]})
    with installed_transport(a,identity):return module.main()

if __name__=='__main__':raise SystemExit(main())
