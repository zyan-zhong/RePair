from pathlib import Path
from supervisor_policy import can_launch_stage, classify_partial

def test_v110_active_means_observe_only(tmp_path:Path):
    assert can_launch_stage(predecessor_done=False, campaign_lock_owned=True) is False

def test_campaign_stage_requires_own_lock():
    assert can_launch_stage(predecessor_done=True, campaign_lock_owned=False) is False

def test_started_without_terminal_never_blind_resends():
    assert classify_partial(started=True,terminal=False)=='AMBIGUOUS_NO_BLIND_RESEND'
