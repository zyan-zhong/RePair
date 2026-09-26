from activate_next import eligible,no_unfinished_writes
from pathlib import Path
import os,pytest

def fixture():
    return ({'activation_round_index':6,'current_round_preserved':{'round_id':'R5'}},
        {'round_id':'R6','stage':'ANALYZER_PLANNER_CAUSAL_VERIFICATION'},
        {'round_index':6},{'round_id':'R6','stage_id':'L-A0','state':'ACCEPTED'})

def test_current_round_never_eligible_even_at_terminal():
    p,l,i,c=fixture();l['round_id']=c['round_id']='R5';assert not eligible(p,l,i,c)

def test_next_round_completed_local_call_is_eligible():
    assert eligible(*fixture())

def test_waiting_request_or_other_stage_or_old_round_is_not_boundary():
    p,l,i,c=fixture()
    for changed in [dict(c,state='WAITING_PROVIDER'),dict(c,stage_id='G-A2'),dict(c,round_id='R5')]:
        assert not eligible(p,l,i,changed)
    assert not eligible(p,l,{'round_index':5},c)
    assert not eligible(p,dict(l,stage='STARTING'),i,c)

@pytest.mark.skipif(os.name!='posix',reason='real /proc server check')
def test_real_open_output_write_is_rejected_until_closed(tmp_path):
    import subprocess,sys,signal,time
    target=tmp_path/'incomplete.json'
    code="import sys,time\nf=open(sys.argv[1],'wb');f.write(b'{');print('ready',flush=True);time.sleep(30)"
    child=subprocess.Popen([sys.executable,'-c',code,str(target)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    try:
        assert child.stdout.readline()==b'ready\n'
        os.kill(child.pid,signal.SIGSTOP);proc=Path('/proc')/str(child.pid)
        for _ in range(100):
            if (proc/'stat').read_text().split()[2] in ('T','t'):break
            time.sleep(.001)
        assert not no_unfinished_writes(proc,set())
        assert no_unfinished_writes(proc,{str(target)})
    finally:
        os.kill(child.pid,signal.SIGCONT);child.terminate();child.communicate(timeout=5)

def test_window_distinguishes_pending_from_current_parallel_use():
    from parallel_status import render_parallel
    a={'parallel_policy':{'activation_round_index':6}};live={'round_id':'R6','pid':12}
    assert 'pending' in render_parallel(a,live,{}, {'state':'WAITING_NEXT_ROUND_LOCAL_TERMINAL'}, {})[0]
    progress={'round_id':'R6','coordinator_pid':12,'active_calls':[
        {'source_key':'one','pid':21,'stage_id':'L-A0','state':'WAITING_PROVIDER','started_unix':0},
        {'source_key':'two','pid':22,'stage_id':'L-A1','state':'WAITING_PROVIDER','started_unix':0}],
        'max_concurrent_sources':2,'phase':'L','closed_sources':4,'total_sources':30}
    text='\n'.join(render_parallel(a,live,{}, {'state':'ACTIVATED'},progress))
    assert '2 / 2' in text and 'L-A0' in text and 'L-A1' in text
    assert 'awaiting' in render_parallel(a,dict(live,round_id='R7'),{}, {'state':'ACTIVATED'},progress)[0]

def test_helper_cold_import_does_not_need_scientific_runtime():
    import subprocess,sys
    root=Path(__file__).resolve().parent
    code='import sys;sys.path.insert(0,'+repr(str(root))+');from parallel_install import checked;import activate_next;assert "exact_bindings" not in sys.modules'
    result=subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
