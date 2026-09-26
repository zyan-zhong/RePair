"""Verify exact package bytes, syntax and whole package tests. No live actions."""
from pathlib import Path
import ast,hashlib,os,subprocess,sys
ROOT=Path(__file__).resolve().parent

def main():
    rows=(ROOT/'PACKAGE_FILES.sha256').read_text().splitlines()
    registered=set()
    for line in rows:
        digest,rel=line.split('  ',1);p=ROOT/rel
        if rel in registered or p.is_symlink() or not p.is_file():raise ValueError('PACKAGE_FILE_INVALID:'+rel)
        if Path(rel).is_absolute() or '..' in Path(rel).parts:raise ValueError('PACKAGE_PATH_ESCAPE')
        registered.add(rel)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('PACKAGE_SHA_CHANGED:'+rel)
    for p in ROOT.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
    for p in ROOT.rglob('*.sh'):
        cp=subprocess.run(['bash','-n',str(p)],check=False)
        if cp.returncode:return cp.returncode
    print('PACKAGE_SHA256_AND_SYNTAX_VERIFY_PASS',flush=True)
    env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
    cp=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider'],cwd=ROOT,env=env,check=False)
    if cp.returncode:return cp.returncode
    print('V1233N4_3_WHOLE_PACKAGE_VERIFY_PASS',flush=True)
    print('SERVER_LIVE_RECOVERY_PROVEN=false',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
