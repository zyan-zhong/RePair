from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def test_progress_preserves_current_attempt_and_reports_stop(tmp_path):
    assert (ROOT/'entry/progress.py').is_file(), 'terminal progress producer missing'
    from entry.progress import update,read_status
    update(tmp_path,stage='ROLLOUT',attempt_root=str(tmp_path/'attempts/000001'),valid_rounds=0,max_rounds=10)
    update(tmp_path,stage='STOPPED',error='example')
    value=read_status(tmp_path)
    assert value['stage']=='STOPPED'
    assert value['valid_rounds']==0 and value['max_rounds']==10
    assert value['attempt_root']==str(tmp_path/'attempts/000001')


def test_monitor_does_not_create_missing_evidence(tmp_path):
    assert (ROOT/'entry/progress.py').is_file(), 'terminal progress reader missing'
    from entry.progress import read_status
    assert read_status(tmp_path)['stage']=='NOT_STARTED'
    assert list(tmp_path.iterdir())==[]
