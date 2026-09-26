def can_launch_stage(*,predecessor_done,campaign_lock_owned): return bool(predecessor_done and campaign_lock_owned)
def classify_partial(*,started,terminal):
    if started and not terminal:return 'AMBIGUOUS_NO_BLIND_RESEND'
    if terminal:return 'TERMINAL_REUSE'
    return 'SAFE_FIRST_ATTEMPT'
