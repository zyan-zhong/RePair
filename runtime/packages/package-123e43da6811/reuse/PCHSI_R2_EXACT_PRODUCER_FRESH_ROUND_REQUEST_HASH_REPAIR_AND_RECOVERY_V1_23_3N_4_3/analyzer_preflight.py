"""Call the existing Analyzer's own discovery/API preflight; never run its main."""
from __future__ import annotations
import argparse,importlib.util
from pathlib import Path
from recovery_core import checked,equal_or_new
from runtime_surface_preflight import validate_runtime_surface

def existing_driver():
    path=Path(__file__).parent/'vendor/V1232Q/v1232q_driver.py'
    spec=importlib.util.spec_from_file_location('existing_q_preflight',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def run(root:Path,output:Path,*,q=None):
    q=existing_driver() if q is None else q
    repo,role=q.discover_strong_repo(root)
    head=checked(['git','-C',str(repo),'rev-parse','HEAD'])
    analyzer_surface=Path(__file__).resolve().parent/'audit/ANALYZER_RUNTIME_SURFACE_PREFLIGHT_V1.json'
    surface_receipt=validate_runtime_surface(repo,None,analyzer_surface)
    q.import_repo(repo);api=q.assert_fixed_head_api_contract(repo)
    result={'schema_id':'EXISTING_ANALYZER_NATIVE_API_PREFLIGHT_V1','status':'PASS','repo_path':str(repo),
        'repo_head':head,'role_authority':role,'checked_symbols':sorted(api),'runtime_surface_preflight':surface_receipt,'provider_calls':0,
        'environment_calls':0,'entire_hierarchical_analyzer_proven':False}
    equal_or_new(output,result)
    print('EXISTING_ANALYZER_NATIVE_API_PREFLIGHT=PASS',flush=True)
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    n=a.parse_args();run(n.root,n.output)
