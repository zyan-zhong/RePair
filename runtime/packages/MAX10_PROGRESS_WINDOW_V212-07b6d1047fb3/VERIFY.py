from pathlib import Path
import argparse,hashlib,json,subprocess,sys
R=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--hash-only',action='store_true');p.add_argument('--server',action='store_true');a=p.parse_args()
    for line in (R/'PACKAGE_FILES.sha256').read_text().splitlines():
        sha,name=line.split(maxsplit=1);target=R/name
        assert target.resolve().is_relative_to(R.resolve()) and not target.is_symlink()
        assert hashlib.sha256(target.read_bytes()).hexdigest()==sha,name
    if a.hash_only:return 0
    test=subprocess.run([sys.executable,'-B','-m','pytest','tests','--rootdir=.','-q','-p','no:cacheprovider'],cwd=R)
    if test.returncode:return test.returncode
    if a.server:
        cfg=json.loads((R/'AUTHORITY.json').read_bytes())
        inherited=subprocess.run([cfg['registered_python'],'-B',str(Path(cfg['base_root'])/'VERIFY.py')],capture_output=True,text=True,timeout=40)
        assert inherited.returncode==0,inherited.stdout+inherited.stderr
        print(inherited.stdout)
        for mode in [[],['--formal']]:
            result=subprocess.run([sys.executable,'-B',str(R/'WATCH.py'),'--json',*mode],capture_output=True,text=True,timeout=50)
            assert result.returncode==0,result.stdout+result.stderr
            view=json.loads(result.stdout);assert len(view['rows'])>=16
            assert view['phase']!='MONITOR_READ_UNAVAILABLE'
    print('MONITOR_SHA_TESTS_PASS; READ_ONLY=true; NO_SCIENTIFIC_MUTATION=true')
    return 0
if __name__=='__main__':raise SystemExit(main())
