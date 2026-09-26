"""Driver validation/next registration over the actual native Memory tail fixture."""
from pathlib import Path
import runpy

g=runpy.run_path(str(Path(__file__).with_name('native_tail_case.py')),init_globals={'case_root':case_root})
from entry.driver import ExistingComponentRoundDriver,_file_ref
from exact_bindings import immutable_json,read_json,read_ref,file_ref
root=Path(case_root)
start=g['start']
obj=ExistingComponentRoundDriver(bundle_root=root/'bundle',formal_root=root/'formal',
    owner_root=root/'owner',deployment={'entry_source_sha256':'a'*64,'scientific_repo_root':str(Path.cwd())},initial=start)
current={'current_parent_context':None}
obj._binding=lambda supplied:current
attempt=root/'driver-next'
project=Path(__file__).resolve().parents[4]
h44=project/'work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4'
immutable_json(attempt/'CURRENT_ANALYZER_BINDING.json',{'packages':{'h44':{
    'root':str(h44),'manifest':file_ref(h44/'PACKAGE_FILES.sha256')}}})
result={**g['result'],'attempt_root':str(attempt),'current_parent_context':None}
assert obj.validate_result(start,result) is None
immutable_json(attempt/'DRIVER_ROUND_RESULT.json',result)
assert obj.recover_round(start,attempt)==result
nxt=obj.build_next(start,result,g['governor'](2))
registered=read_json(obj._binding_path(nxt))
assert registered['round_index']==2 and registered['current_parent_context'] is None
assert read_ref(_file_ref(registered['request']))==nxt
assert read_ref(_file_ref(registered['execution_binding']))['request_sha256']==nxt['request_sha256']
inputs=read_ref(_file_ref(registered['input_refs']))
assert inputs['request_sha256']==nxt['request_sha256']
index=read_ref(_file_ref(registered['current_index']))
assert index['round_id']==nxt['round_id'] and index['request_sha256']==nxt['request_sha256']
assert read_ref(index['refs']['memory_source_partitions'])==read_ref(_file_ref(g['nxt']['memory_source_partitions']))
assert read_ref(_file_ref(registered['memory_state']))['round_id']==nxt['round_id']
assert obj.build_next(start,result,g['governor'](2))==nxt
assert result['next_request'] is None
try: obj.validate_result(start,{**result,'current_parent_context':{'invented':'context'}})
except ValueError as exc: assert 'CURRENT_PARENT_CONTEXT' in str(exc)
else: raise AssertionError('retained policy changed continuation context')
