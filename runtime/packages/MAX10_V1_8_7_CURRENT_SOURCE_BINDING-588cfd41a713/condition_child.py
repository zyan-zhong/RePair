"""Keep V186 transport and original H44; install current actor provenance first."""
from pathlib import Path
import json,sys,hashlib,types
ROOT=Path(__file__).resolve().parent

def main():
    from condition_entry import verify
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=Path(a['predecessor_source_root'])
    request=json.loads(Path(sys.argv[sys.argv.index('--request')+1]).read_bytes())
    if request['registered_condition_entry']!={'path':str(ROOT/'AUTHORITY.json'),'sha256':hashlib.sha256((ROOT/'AUTHORITY.json').read_bytes()).hexdigest()}:raise ValueError('CHILD_CONDITION_ENTRY_CHANGED')
    if request['registered_condition_manifest']!={'path':str(ROOT/'PACKAGE_FILES.sha256'),'sha256':identity}:raise ValueError('CHILD_CONDITION_SOURCE_CHANGED')
    if hashlib.sha256((prior/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['predecessor_manifest_sha256']:raise ValueError('CHILD_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(prior))
    from resume_entry import verify as verify_prior
    verify_prior()
    source=(prior/'child_entry.py').read_text();needle='        return module.main()'
    if source.count(needle)!=1:raise ValueError('CHILD_PROVENANCE_OVERLAY_SOURCE_DRIFT')
    source=source.replace(needle,'        _install_current_actor(request, binding)\n'+needle)
    module=types.ModuleType('_registered_transport_child');module.__file__=str(prior/'child_entry.py')
    from actor_provenance import install_round_plan
    module._install_current_actor=lambda request,binding:install_round_plan(request,binding,a)
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    return module.main()

if __name__=='__main__':raise SystemExit(main())
