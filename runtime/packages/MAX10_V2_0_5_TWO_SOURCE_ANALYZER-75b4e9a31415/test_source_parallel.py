import importlib.util,os,time,json
from pathlib import Path
import pytest


def api():
    assert importlib.util.find_spec('source_parallel') is not None, 'two-source coordinator is not implemented'
    import source_parallel
    return source_parallel

@pytest.mark.skipif(os.name!='posix',reason='production fork isolation requires Linux; server suite mandatory')
def test_two_sources_overlap_but_source_steps_stay_ordered(tmp_path):
    m=api()
    def worker(source):
        events=[]
        for stage in ['A0','A1']:
            m.check_admission();start=time.monotonic();m.emit({'stage_id':stage,'state':'WAITING_PROVIDER'})
            time.sleep(.08);events.append((stage,start,time.monotonic(),os.getpid()))
        return events
    snapshots=[];got=m.map_sources(['s1','s2','s3'],worker,key=lambda x:x,workers=2,observe=snapshots.append)
    assert len(got)==3 and got[0][0][1]<got[1][-1][2] and got[1][0][1]<got[0][-1][2]
    assert all(x[0][2]<=x[1][1] for x in got)
    assert got[0][0][3]!=got[1][0][3]
    assert max(len(s['active_calls']) for s in snapshots)==2
    assert not snapshots[-1]['active_calls']

@pytest.mark.skipif(os.name!='posix',reason='server fork test')
def test_global_stop_drains_sent_work_and_admits_no_next_source(tmp_path):
    m=api()
    def worker(source):
        (tmp_path/str(source)).write_text('started')
        time.sleep(.04 if source==0 else .14)
        if source==0:raise ValueError('GLOBAL_STOP')
        (tmp_path/(str(source)+'done')).write_text('terminal')
        m.check_admission()
        (tmp_path/(str(source)+'next')).write_text('must not start')
    with pytest.raises(RuntimeError,match='GLOBAL_STOP'):
        m.map_sources([0,1,2,3],worker,key=str,workers=2)
    assert (tmp_path/'1done').exists() and not (tmp_path/'2').exists() and not (tmp_path/'1next').exists()

@pytest.mark.skipif(os.name!='posix',reason='server fork test')
def test_crashed_worker_is_fail_closed_and_sibling_drains(tmp_path):
    m=api()
    def worker(source):
        if source==0:os._exit(7)
        time.sleep(.1);(tmp_path/'drained').write_text('yes')
    with pytest.raises(RuntimeError,match='WORKER_EXIT'):
        m.map_sources([0,1,2],worker,key=str,workers=2)
    assert (tmp_path/'drained').exists()

@pytest.mark.skipif(os.name!='posix',reason='server fork test')
def test_duplicate_sources_rejected_before_execution():
    m=api()
    with pytest.raises(ValueError,match='SOURCE_KEYS'):
        m.map_sources(['a','a'],lambda x:x,key=str,workers=2)

def test_policy_requires_positive_registered_integer():
    m=api()
    for n in [True,0,-1,2.5]:
        with pytest.raises(ValueError,match='CONCURRENCY'):
            m.map_sources([],lambda x:x,key=str,workers=n)
