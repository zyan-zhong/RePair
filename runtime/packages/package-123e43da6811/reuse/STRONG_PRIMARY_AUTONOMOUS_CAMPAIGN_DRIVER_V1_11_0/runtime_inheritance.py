from __future__ import annotations

from pathlib import Path
from typing import Sequence

from autonomy_binding import git_head

V110_PACKAGE='STRONG_PRIMARY_R1_HYDRATED_POST_AND_AUTONOMOUS_DOWNSTREAM_CLOSURE_V1_10_0'
REQUIRED_OPTIONS=('--upstream-root','--closure-root','--prepared-root','--repo')


def _option(argv: Sequence[str], key: str) -> str:
    hits=[]
    for i,item in enumerate(argv):
        if item==key:
            if i+1>=len(argv): raise ValueError('V110_CMDLINE_OPTION_VALUE_MISSING:'+key)
            hits.append(argv[i+1])
    if len(hits)!=1: raise ValueError('V110_CMDLINE_OPTION_CARDINALITY:'+key+':'+str(len(hits)))
    if not hits[0]: raise ValueError('V110_CMDLINE_OPTION_EMPTY:'+key)
    return hits[0]


def parse_v110_cmdline(argv: Sequence[str]) -> dict[str,str]:
    argv=list(argv)
    controllers=[Path(x) for x in argv if Path(x).name=='tail_controller.py']
    if len(controllers)!=1: raise ValueError('V110_TAIL_CONTROLLER_REQUIRED')
    controller=controllers[0]
    if controller.parent.name!=V110_PACKAGE:
        raise ValueError('V110_PACKAGE_IDENTITY_MISMATCH:'+controller.parent.name)
    try:
        ci=argv.index(str(controller))
    except ValueError:
        raise ValueError('V110_TAIL_CONTROLLER_REQUIRED')
    if ci+1>=len(argv) or argv[ci+1]!='run': raise ValueError('V110_RUN_MODE_REQUIRED')
    out={
        'v110_package_root':str(controller.parent),
        'upstream_root':_option(argv,'--upstream-root'),
        'closure_root':_option(argv,'--closure-root'),
        'prepared_root':_option(argv,'--prepared-root'),
        'repo':_option(argv,'--repo'),
    }
    return out


def snapshot_v110_runtime(*,pid:int,proc_root:Path=Path('/proc'),expected_fixed_head:str)->dict[str,object]:
    if type(pid) is not int or pid<=1: raise ValueError('V110_PID_INVALID')
    cmd=Path(proc_root)/str(pid)/'cmdline'
    if not cmd.is_file() or cmd.is_symlink(): raise ValueError('V110_PROC_CMDLINE_UNAVAILABLE')
    raw=cmd.read_bytes()
    argv=[part.decode('utf-8') for part in raw.split(b'\0') if part]
    parsed=parse_v110_cmdline(argv)
    resolved={k:str(Path(v).resolve()) for k,v in parsed.items()}
    for key in ('v110_package_root','upstream_root','closure_root','prepared_root','repo'):
        p=Path(resolved[key])
        if not p.exists() or p.is_symlink(): raise ValueError('V110_INHERITED_PATH_INVALID:'+key)
    head=git_head(Path(resolved['repo']))
    if head!=expected_fixed_head: raise ValueError('FIXED_HEAD_MISMATCH:'+str(head))
    return {
        'schema_id':'V110_RUNTIME_INHERITANCE_V1','schema_version':1,
        'pid':pid,**resolved,'fixed_head':head,
        'inheritance_authority':'LIVE_V110_EXEC_TRANSFORMED_CMDLINE',
        'human_rebinding_count':0,
    }
