from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib,sys,importlib
ROOT=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify():
    manifest=ROOT/'PACKAGE_FILES.sha256';seen=set()
    for line in manifest.read_text().splitlines():
        expected,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name)
        if (ROOT/name).is_symlink() or digest(ROOT/name)!=expected:raise ValueError('PACKAGE_SOURCE_CHANGED:'+name)
    return digest(manifest)

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['predecessor_root'])
    if digest(root/'PACKAGE_FILES.sha256')!=a['predecessor_manifest_sha256']:raise ValueError('CLOSED_HISTORY_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));prior=importlib.import_module('profile_entry')
    prepared=prior.load()
    for row in a['native_entry_refs']:
        if digest(row['path'])!=row['sha256']:raise ValueError('NATIVE_ENTRY_SOURCE_CHANGED')
    return a,prior,identity,prepared

@contextmanager
def prepared_once(prepared):
    resume=prepared[3][3][3][1];value=prepared[3][3][3][3]
    if len(value)!=6 or len(value[4])!=7 or not hasattr(value[1],'prepare'):raise ValueError('PREPARED_CHAIN_SHAPE')
    if resume.__name__!='resume_entry' or value[1].__name__!='continuation':raise ValueError('PREPARED_MODULE_IDENTITY')
    base=value[1];resume_root=Path(resume.ROOT);base_root=Path(base.ROOT)
    if Path(resume.__file__).parent!=resume_root or Path(base.__file__).parent!=base_root:raise ValueError('PREPARED_MODULE_ROOT')
    resume_sha=value[3];base_sha=value[4][3]
    def checked_resume():
        if resume.verify()!=resume_sha:raise ValueError('PREPARED_RESUME_CHANGED')
        return value
    def checked_base():
        base.verify_package()
        if digest(base_root/'PACKAGE_FILES.sha256')!=base_sha:raise ValueError('PREPARED_BASE_CHANGED')
        return value[4]
    with patch.object(resume,'load',checked_resume),patch.object(base,'prepare',checked_base):yield

def run(invocation):
    a,prior,identity,prepared=load()
    import entry.main as native_main,entry.progress as progress,environment
    from closed_history import installed
    from environment_deadline import loader
    from group_prompt import installed as group_installed
    from pre_context import installed as pre_installed
    original=native_main.main;update=progress.update
    def main(argv):
        with installed(a,identity),group_installed(a,identity,ROOT),pre_installed(a,identity,ROOT):return original(argv)
    def status(owner,**fields):
        return update(owner,**{**fields,'closed_history_entry_root':str(ROOT),'closed_history_manifest_sha256':identity,
            'group_prompt_manifest_sha256':identity,'group_prompt_activation':a['group_prompt_activation'],
            'x_prompt_manifest_sha256':identity,'x_prompt_activation':a['x_prompt_activation'],
            'pre_context_encoding_manifest_sha256':identity})
    with prepared_once(prepared),patch.object(native_main,'main',main),patch.object(progress,'update',status),\
         patch.object(environment,'load_environment',loader(a,environment)):
        return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))
