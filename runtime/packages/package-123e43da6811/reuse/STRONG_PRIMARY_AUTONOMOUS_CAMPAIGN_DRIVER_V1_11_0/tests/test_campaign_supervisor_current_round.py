import json
from pathlib import Path
import campaign_supervisor as s

FIXED='61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a'

def test_runtime_snapshot_is_persisted_and_reused(tmp_path,monkeypatch):
    state=tmp_path/'state'; state.mkdir()
    snap={'schema_id':'V110_RUNTIME_INHERITANCE_V1','schema_version':1,'pid':99,'v110_package_root':'/v','upstream_root':'/u','closure_root':'/c','prepared_root':'/p','repo':'/r','fixed_head':FIXED,'inheritance_authority':'LIVE_V110_EXEC_TRANSFORMED_CMDLINE','human_rebinding_count':0}
    monkeypatch.setattr(s,'snapshot_v110_runtime',lambda **kw:snap)
    got=s.load_or_snapshot_runtime(state_root=state,v110_pid=99)
    assert got==snap
    monkeypatch.setattr(s,'snapshot_v110_runtime',lambda **kw:(_ for _ in ()).throw(AssertionError('must reuse')))
    assert s.load_or_snapshot_runtime(state_root=state,v110_pid=99)==snap

def test_one_supervisor_iteration_calls_corrected_current_round_driver(tmp_path,monkeypatch):
    snap={'schema_id':'V110_RUNTIME_INHERITANCE_V1','schema_version':1,'pid':99,'v110_package_root':str(tmp_path/'v'),'upstream_root':str(tmp_path/'u'),'closure_root':str(tmp_path/'c'),'prepared_root':str(tmp_path/'p'),'repo':str(tmp_path/'r'),'fixed_head':FIXED,'inheritance_authority':'LIVE_V110_EXEC_TRANSFORMED_CMDLINE','human_rebinding_count':0}
    for k in ('v','u','c','p','r'): (tmp_path/k).mkdir()
    monkeypatch.setattr(s,'assert_fixed_head',lambda *a,**kw:FIXED)
    seen={}
    def advance(**kw):
        seen.update(kw); return {'phase':'WAIT_V110_WRITER','terminal':False,'side_effect':False}
    monkeypatch.setattr(s,'advance_current_round',advance)
    x=s.supervisor_iteration(runtime=snap,state_root=tmp_path/'state')
    assert x['phase']=='WAIT_V110_WRITER'
    assert seen['v110_package_root']==tmp_path/'v'
    assert seen['closure_root']==tmp_path/'c'
