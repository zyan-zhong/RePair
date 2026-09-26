from __future__ import annotations
import json,os,subprocess,sys
from pathlib import Path
from safe_io import load_obj,write_once

def git_head(repo:Path):
    cp=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True,check=False)
    if cp.returncode:return None
    return cp.stdout.strip()

def assert_fixed_head(repo:Path,expected:str):
    h=git_head(repo)
    if h!=expected:raise ValueError('FIXED_HEAD_MISMATCH:'+str(h))
    return h

def find_predecessor(closure:Path):
    gp=closure/'HYDRATED_DOWNSTREAM_BINDING_GAP_V1.json'; pp=closure/'HYDRATED_PLANNER_POST_ACCEPTED_V1.json'
    if not gp.is_file() or not pp.is_file(): return None
    return load_obj(gp),load_obj(pp)

def write_blocked(state_root:Path,phase:str,reasons:list[str]):
    write_once(state_root/'AUTONOMOUS_BINDING_STATUS_V1.json',{'schema_id':'AUTONOMOUS_BINDING_STATUS_V1','schema_version':1,'phase':phase,'reasons':sorted(set(reasons)),'human_scientific_decision_required':False,'supervisor_remains_authoritative':True})
