from pathlib import Path
import pytest
from runtime_inheritance import parse_v110_cmdline, snapshot_v110_runtime

FIXED='61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a'

def argv(pkg='/srv/STRONG_PRIMARY_R1_HYDRATED_POST_AND_AUTONOMOUS_DOWNSTREAM_CLOSURE_V1_10_0',up='/u',cl='/c',pre='/p',repo='/r'):
    return ['python',f'{pkg}/tail_controller.py','run','--upstream-root',up,'--closure-root',cl,'--prepared-root',pre,'--repo',repo]

def test_parse_exec_transformed_v110_worker():
    x=parse_v110_cmdline(argv())
    assert x['v110_package_root']=='/srv/STRONG_PRIMARY_R1_HYDRATED_POST_AND_AUTONOMOUS_DOWNSTREAM_CLOSURE_V1_10_0'
    assert x['upstream_root']=='/u'
    assert x['closure_root']=='/c'
    assert x['prepared_root']=='/p'
    assert x['repo']=='/r'

def test_rejects_wrong_controller():
    with pytest.raises(ValueError,match='V110_TAIL_CONTROLLER_REQUIRED'):
        parse_v110_cmdline(['python','/x/other.py','run','--upstream-root','/u','--closure-root','/c','--prepared-root','/p','--repo','/r'])

def test_snapshot_reads_proc_cmdline_and_head(tmp_path,monkeypatch):
    proc=tmp_path/'proc'; pid=42; (proc/str(pid)).mkdir(parents=True)
    pkg=tmp_path/'STRONG_PRIMARY_R1_HYDRATED_POST_AND_AUTONOMOUS_DOWNSTREAM_CLOSURE_V1_10_0'; pkg.mkdir(); (pkg/'tail_controller.py').write_text('# x')
    repo=tmp_path/'repo'; repo.mkdir(); up=tmp_path/'u'; up.mkdir(); cl=tmp_path/'c';cl.mkdir();pre=tmp_path/'p';pre.mkdir()
    (proc/str(pid)/'cmdline').write_bytes(('\0'.join(argv(str(pkg),str(up),str(cl),str(pre),str(repo)))+'\0').encode())
    monkeypatch.setattr('runtime_inheritance.git_head',lambda p:FIXED)
    x=snapshot_v110_runtime(pid=pid,proc_root=proc,expected_fixed_head=FIXED)
    assert x['pid']==42 and x['fixed_head']==FIXED
    assert x['repo']==str(repo.resolve())

