from __future__ import annotations
import fcntl,json,os
from pathlib import Path


def writer_lock_state(root:Path)->str:
    p=Path(root)/'.tail_writer.lock'
    if not p.exists(): return 'INACTIVE_NO_LOCK_FILE'
    if p.is_symlink(): raise ValueError('V110_TAIL_LOCK_SYMLINK_FORBIDDEN')
    fd=os.open(p,os.O_RDWR|getattr(os,'O_NOFOLLOW',0))
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return 'ACTIVE'
        fcntl.flock(fd,fcntl.LOCK_UN); return 'INACTIVE'
    finally: os.close(fd)


def _post_runtime_state(closure_root:Path)->dict[str,object]:
    runtime=Path(closure_root)/'hydrated_planner_post_runtime'
    if not runtime.exists(): return {'accepted':0,'partial':0,'total':0}
    if runtime.is_symlink() or not runtime.is_dir(): raise ValueError('V110_POST_RUNTIME_INVALID')
    accepted=partial=total=0
    for call in sorted(runtime.iterdir()):
        if not call.is_dir() or call.is_symlink(): continue
        total+=1; method=call/'method_result.json'
        if not method.is_file() or method.is_symlink(): partial+=1; continue
        try: obj=json.loads(method.read_text(encoding='utf-8'))
        except Exception: partial+=1; continue
        if isinstance(obj,dict) and obj.get('status')=='ACCEPTED': accepted+=1
        else: partial+=1
    return {'accepted':accepted,'partial':partial,'total':total}


def decide_takeover_action(*,closure_root:Path,verifier_ready:bool)->dict[str,object]:
    state=writer_lock_state(Path(closure_root))
    if state=='ACTIVE':
        return {'action':'WAIT_V110_WRITER','side_effect_authorized':False,'provider_resend_authorized':False,'writer_lock_state':state}
    if not verifier_ready:
        return {'action':'WAIT_VERIFIER','side_effect_authorized':False,'provider_resend_authorized':False,'writer_lock_state':state}
    posts=_post_runtime_state(Path(closure_root))
    if posts['accepted']>1 or (posts['accepted'] and posts['partial']):
        return {'action':'FAIL_CLOSED_AMBIGUOUS_POST_STATE','side_effect_authorized':False,'provider_resend_authorized':False,'writer_lock_state':state,**posts}
    if posts['partial']:
        return {'action':'FAIL_CLOSED_PARTIAL_POST_NO_RESEND','side_effect_authorized':False,'provider_resend_authorized':False,'writer_lock_state':state,**posts}
    if posts['accepted']==1:
        return {'action':'ADOPT_ACCEPTED_V110_POST','side_effect_authorized':True,'provider_resend_authorized':False,'writer_lock_state':state,**posts}
    return {'action':'RUN_V110_POST_ONCE','side_effect_authorized':True,'fresh_single_send_authorized':True,'provider_resend_authorized':False,'writer_lock_state':state,**posts}
