from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
NATIVE = ROOT / 'work/v17/native_bba_full'


def native(code):
    bootstrap = ('import sys,os\n'
        f'sys.path.insert(0,{str(ROOT / "work/v17")!r})\n'
        f'os.chdir({str(NATIVE)!r})\n'
        'from memory_binding.source_overlay import install_memory_overlay\n'
        f'install_memory_overlay({str(NATIVE)!r})\n')
    result = subprocess.run([sys.executable, '-B', '-c', bootstrap + code],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_complete_registered_analyzer_to_native_memory_api(tmp_path):
    case=Path(__file__).with_name('native_end_to_end_case.py')
    native(f'import runpy\nrunpy.run_path({str(case)!r},init_globals={{"case_root":{str(tmp_path)!r}}})')


def test_worker_overlay_inherits_into_child_and_grandchild_and_rejects_wrong_repo(tmp_path):
    sys.path.insert(0, str(ROOT / 'work/v17'))
    from memory_binding.worker_bootstrap import worker_environment
    environment = worker_environment(NATIVE)
    code = ('from pchsi.memory.consumer_views import MemorySourcePartitionV1\n'
            'assert MemorySourcePartitionV1.TRAIN_UPDATE.value=="TRAIN_UPDATE"\n'
            'from memory_binding.source_overlay import overlay_receipt\n'
            'assert overlay_receipt()["base_files_modified"] is False\n')
    launcher = 'import subprocess,sys\n' + code + f'assert subprocess.run([sys.executable,"-B","-c",{code!r}]).returncode==0\n'
    result = subprocess.run([sys.executable, '-B', '-c', launcher], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    environment['PCHSI_CURRENT_MEMORY_NATIVE_REPO'] = str(tmp_path / 'not_registered')
    result = subprocess.run([sys.executable, '-B', '-c', 'print("MUST_NOT_EXECUTE")'],
                            env=environment, capture_output=True, text=True)
    assert result.returncode != 0 and 'MUST_NOT_EXECUTE' not in result.stdout


def test_overlay_preserves_v1_and_accepts_native_current_partition():
    native('''
from pchsi.memory.sequence_failure_experience import SequenceSourceTaskAccessBindingV1
from pchsi.memory.consumer_views import MemorySourcePartitionV1
assert MemorySourcePartitionV1.TRAIN_UPDATE.value == 'TRAIN_UPDATE'
from pchsi.memory.consumer_views import MemorySourcePartitionBindingV1
try: MemorySourcePartitionBindingV1('a'*64,MemorySourcePartitionV1.TRAIN_UPDATE,'b'*64)
except ValueError as exc: assert 'full current source provenance' in str(exc)
else: raise AssertionError('diagnostic-only TRAIN_UPDATE admitted')
from pathlib import Path
source=Path('src/pchsi/memory/sequence_failure_experience.py').read_text(encoding='utf8')
assert 'must be TRAIN_MEMORY_SOURCE' in source
from memory_binding.source_overlay import adapted_sources
assert 'must be TRAIN_MEMORY_SOURCE' in adapted_sources()['pchsi.memory.sequence_failure_experience']
from memory_binding.source_overlay import adapt_source
try: adapt_source('pchsi.memory.sequence_failure_experience',(source+'\\n').encode())
except ValueError as exc: assert 'SOURCE_DRIFT' in str(exc)
else: raise AssertionError('modified native source accepted')
''')


def test_same_call_boundary_registration_is_truthful_and_not_invented():
    native('''
from memory_binding.same_call import extend_local_schema, validate_boundaries
base={'type':'object','properties':{},'required':[],'additionalProperties':False}
assert 'memory_boundary_registrations' in extend_local_schema(base)['required']
assert base['required']==[]
local={'error_instances':[{'error_instance_id':'E1'}]}
row={'error_instance_id':'E1','status':'UNRESOLVED','unresolved_reason':'No supported activation boundary','applicability':None}
assert validate_boundaries([row],local)==[row]
try: validate_boundaries([],local)
except ValueError: pass
else: raise AssertionError('missing error silently accepted')
''')


def test_native_same_call_renderer_and_validation_keep_standard_local_artifact():
    native('''
import importlib.util,json
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
helpers=load('tests/analyzer/test_local_results.py','local_helpers')
request_helpers=load('tests/cognitive_runtime/test_request_renderer.py','request_helpers')
from pchsi.cognitive_runtime.request_renderer import render_stage_request
projection={'evidence_pack_sha256':'a'*64,'evidence_pack':{},'evidence_reference_catalog':request_helpers._catalog(),
 'local_repair_contract':request_helpers._repair_contract(),'memory_pack_sha256':None}
request=render_stage_request(stage_id='L-A1',projection=projection)
schema=request['provider_request']['text']['format']['schema']
assert 'memory_boundary_registrations' in schema['required']
assert 'same Analyzer call' in request['provider_request']['input'][0]['content'][0]['text']
pack=helpers._pack();payload=helpers._failure(helpers._m(),pack,two_errors=False)
payload['memory_boundary_registrations']=[{'error_instance_id':'e1','status':'UNRESOLVED',
 'unresolved_reason':'No supported general release boundary','applicability':None}]
from pchsi.cognitive_runtime.output_validation import validate_stage_output
artifact=validate_stage_output(stage_id='L-A1',text=json.dumps(payload),raw_response_sha256='d'*64,projection={'evidence_pack':pack})
assert 'memory_boundary_registrations' not in artifact
assert artifact['raw_response_sha256']=='d'*64
assert artifact['local_repairs'][0]['exact_action']==payload['local_repairs'][0]['exact_action']
''')


def test_actual_native_reconstruction_roundtrip_assembly_and_partition(tmp_path):
    native(f'''
from pathlib import Path
from dataclasses import replace
import importlib.util,json
from memory_binding.current_source import canonical,sha,build_current_source_access
from memory_binding.producer import file_ref,build_experience,build_assembly,partition_for_record,materialize_native_candidate
from pchsi.memory import sequence_failure_experience as seq
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
spec=importlib.util.spec_from_file_location('native_test','tests/memory/test_sequence_failure_experience.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
source,old_binding,registration,_=helpers._t4_fixture(seq)
try: replace(old_binding,access_class='TRAIN_UPDATE')
except ValueError as exc: assert 'TRAIN_MEMORY_SOURCE' in str(exc)
else: raise AssertionError('V1 constraint was loosened')
root=Path({str(tmp_path)!r})
row={{'schema_id':'ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1','id':source.episode_artifact.task_id,
     'split':'train','train_pool':'TRAIN_UPDATE','gamefile_sha256':source.episode_artifact.gamefile_sha256,
     'gamefile_relpath':old_binding.dataset_relative_gamefile,'task_type':source.episode_artifact.task_type}}
manifest=root/'train.jsonl';manifest.write_bytes(canonical(row))
request=RoundRolloutCollectionRequestV1(round_id='ROUND1',execution_attempt_id='round-attempt',parent_policy_id='pi0',
 parent_policy_artifact_sha256='a'*64,policy_runtime_binding_sha256='b'*64,execution_profile_sha256='c'*64,
 train_update_manifest_sha256=sha(manifest.read_bytes()),round_memory_runtime_authority_sha256='d'*64,
 round_start_memory_snapshot_sha256='e'*64,token_budget_contract_sha256='f'*64,execution_namespace='test',rollout_seed=17)
request_path=root/'request.json';request_path.write_bytes(canonical(request.to_dict()))
local={{'local_result_sha256':'a'*64}}
error={{'error_instance_id':'E1','relevant_start_call_index':0,'trigger_call_index':0,'critical_window_end_call_index':1,
 'mechanism_hypotheses':[{{'hypothesis_id':'H1','statement':'The output did not follow the visible action format.','confidence':0.7}}]}}
experience,access=build_experience(source=source,request_ref=file_ref(request_path),train_manifest_ref=file_ref(manifest),
 local_result=local,error=error,condition='CURRENT_TEST_POLICY',raw_response_sha256='1'*64)
assert experience.task_access_binding.access_class=='TRAIN_UPDATE'
assert seq.SequenceFailureExperienceV1.from_json(experience.canonical_bytes())==experience
assert experience.observed_sequence[0].raw_model_response=='not-json'
boundary={{'error_instance_id':'E1','status':'REGISTERED','unresolved_reason':None,'applicability':{{
 'activation':['The visible interface reports an invalid action format.'],'continuation':[],
 'revalidation_requirement':'NOT_REQUIRED','revalidation':[],
 'release':['A response matching the visible action format is accepted.'],'termination':[],
 'non_applicability_disposition':'UNRESOLVED_NO_REGISTERED_CONDITION','non_applicability':[],
 'policy_visible_state_change_trigger':[]}}}}
assembly=build_assembly(experience=experience,local_result=local,error=error,boundary=boundary,
 raw_response_sha256='1'*64,logical_call_id='call1')
assert assembly.creator_role.startswith('STRONG_ANALYZER')
assert assembly.applicability.activation[0].condition_text==boundary['applicability']['activation'][0]
from pchsi.memory.procedural_builder import build_procedural_failure_memory_record_v1
from pchsi.memory.procedural_record import AssemblyRegistrationBindingV1,MemoryEvidenceRefV1
binding=AssemblyRegistrationBindingV1(schema_id=assembly.schema_id,registration_id=assembly.registration_id,
 assembly_registration_sha256=sha(assembly.canonical_bytes()),lineage_registration_ref=MemoryEvidenceRefV1(
 assembly.schema_id,assembly.registration_id,sha(assembly.canonical_bytes())))
record=build_procedural_failure_memory_record_v1(assembly_input=assembly,assembly_registration_binding=binding,
 source_experiences=(experience,),previous_record=None)
part=partition_for_record(record,access,{{'file_sha256':sha(assembly.canonical_bytes())}})
assert part.source_partition.value=='TRAIN_UPDATE'
assert part.authority_scope.value=='FULL_TRAIN_SOURCE_PROVENANCE'
from pchsi.memory.source_integrity import audit_memory_source_integrity_v1
assert audit_memory_source_integrity_v1(record=record,registered_experiences=(experience,)).status=='VERIFIED'
from pchsi.memory import candidate_materialization as candidates
if sys.platform=='win32':
 def binary_once(path,raw):
  with Path(path).open('xb') as stream: stream.write(raw)
 candidates._write_once=binary_once
class FixtureTokenizer:
 tokenizer_id='FIXTURE_ONLY'
 tokenizer_revision='f'*64
 def count_tokens(self,text): return max(1,len(text)//100)
initial,report,bundle,final,refs=materialize_native_candidate(experience=experience,assembly=assembly,
 tokenizer=FixtureTokenizer(),output_root=root/'candidate')
assert bundle.status=='ELIGIBLE',bundle.failure_codes
assert all((final/name).is_file() for name in ('governed_record.json','retrieval_key.json','fm1.json','fm2.json'))
materialize_native_candidate(experience=experience,assembly=assembly,tokenizer=FixtureTokenizer(),output_root=root/'candidate')
# Original H4.4 independent verifier produces the five-repeat result; the bridge
# preserves all repetitions in distinct arm refs and invokes native Memory rules.
h44=Path({str(ROOT / 'work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4')!r})
sys.path.insert(0,str(h44))
if sys.platform=='win32':
 import types
 sys.modules.setdefault('fcntl',types.ModuleType('fcntl'))  # Verifier never acquires a branch lock.
spec=importlib.util.spec_from_file_location('h44_test',h44/'tests/test_verifier.py')
h4=importlib.util.module_from_spec(spec);spec.loader.exec_module(h4)
plan_path=h4.fixture_plan(root/'verifier_run')
plan=json.loads(plan_path.read_bytes());plan.update(round_id=request.round_id,source_request=request.to_dict())
plan.pop('plan_sha256');plan['plan_sha256']=sha(canonical(plan));plan_path.write_bytes(canonical(plan))
verified=h4.verify_plan(plan_path,root/'verifier_run')
from memory_binding.verifier_event import validate_verifier,build_shadow_event
vref=file_ref(root/'verifier_run/verifier/ENVIRONMENT_RESULT_PACKAGE.json')
plan,verified=validate_verifier(plan_ref=file_ref(plan_path),verifier_ref=vref,request=request.to_dict())
event,eref=build_shadow_event(request=request.to_dict(),record=bundle.governed_record,eligible=True,access=access,
 local_result_sha256=local['local_result_sha256'],candidate_sha256='b'*64,source_state_sha256='a'*64,
 plan=plan,verifier=verified,verifier_ref=vref,output_root=root/'event')
from pchsi.memory.round_maintenance import classify_shadow_event_v1,VerifierEffectV1
assert event.source_partition.value=='TRAIN_UPDATE'
assert classify_shadow_event_v1(event).disposition.value=='PROMOTE_NEXT_ROUND'
for effect,expected in [(VerifierEffectV1.HARM,'QUARANTINE'),(VerifierEffectV1.NEUTRAL,'DESCRIPTIVE_ONLY'),
 (VerifierEffectV1.UNCERTAIN,'STAGING_UNRESOLVED')]:
 assert classify_shadow_event_v1(replace(event,event_id=None,verifier_effect=effect)).disposition.value==expected
assert classify_shadow_event_v1(replace(event,event_id=None,evidence_complete=False)).disposition.value=='STAGING_UNRESOLVED'
assert event.f0_evidence_sha256!=event.f1_evidence_sha256
assert len(json.loads((root/'event/F0_PAIRED_EVIDENCE.json').read_bytes())['pairs'])==5
try:
 build_shadow_event(request=request.to_dict(),record=bundle.governed_record,eligible=True,access=access,
  local_result_sha256=local['local_result_sha256'],candidate_sha256='b'*64,source_state_sha256='a'*64,
  plan=plan,verifier=dict(verified,pair_results=verified['pair_results'][:4]),verifier_ref=vref,output_root=root/'missing_event')
except ValueError as exc: assert 'COMPLETE_REGISTERED_PAIR_SET' in str(exc)
else: raise AssertionError('convenient subset admitted')
# Wrong pool does not become old memory source; future parent/request cannot adopt current episode.
manifest.write_bytes(canonical(dict(row,train_pool='TRAIN_SELECT')))
bad_request=replace(request,train_update_manifest_sha256=sha(manifest.read_bytes()),request_sha256=None)
request_path.write_bytes(canonical(bad_request.to_dict()))
try: build_current_source_access(request_ref=file_ref(request_path),train_manifest_ref=file_ref(manifest),source=source)
except ValueError as exc: assert 'ACTUAL_TRAIN_UPDATE' in str(exc)
else: raise AssertionError('select admitted')
''')
