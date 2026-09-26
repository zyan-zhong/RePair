"""Carry strict trained-parent compatibility through existing worker bootstrap."""
from pathlib import Path
import json,hashlib,os,sys,runpy
ROOT_ENV='PCHSI_REGISTERED_TRAINED_RUNTIME_ENTRY'
SHA_ENV='PCHSI_REGISTERED_TRAINED_RUNTIME_SHA'

def checked(ref):
    p=Path(ref['path']);raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('TRAINED_RUNTIME_SOURCE_CHANGED:'+str(p))
    return raw

def install_reader(a):
    from pchsi.research_intelligence import human_f0f1_runtime as native
    ref=a['native_refs']['human_f0f1_runtime.py'];checked(ref)
    if Path(native.__file__)!=Path(ref['path']):raise ValueError('TRAINED_RUNTIME_NAMESPACE_CHANGED')
    original=native.load_continuation_runtime_binding_v2
    if getattr(original,'_registered_trained_reader',False):return
    from policy_binding.launch import RUNTIME_SCHEMA,verify_adapter,read_ref
    from runtime_contract import TRAINED_SCHEMA,load_trained_runtime
    if RUNTIME_SCHEMA!=TRAINED_SCHEMA:raise ValueError('TRAINED_RUNTIME_PRODUCER_SCHEMA_DRIFT')
    verified=set()
    def artifacts(value):
        # All references are immutable and byte-bound. Reuse verification inside
        # this interpreter; every fresh GPU worker validates the actual weights.
        key=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
        if key in verified:return
        verify_adapter(value)
        candidate=read_ref(value['candidate_policy_ref'])
        for left,right in [('policy_id','policy_id'),('artifact_sha256','adapter_bundle_sha256'),('artifact_root','adapter_path'),
                           ('artifact_manifest','adapter_artifact_manifest_ref'),('final_trainable_parameter_sha256','final_trainable_parameter_sha256'),
                           ('current_parent_context','current_parent_context'),('training_result_ref','training_result_ref')]:
            if candidate.get(left)!=value[right]:raise ValueError('TRAINED_RUNTIME_CANDIDATE_IDENTITY:'+left)
        if candidate.get('schema_id')!='CURRENT_OFFOFF_POLICY_BINDING_V1' or candidate.get('kind')!='LORA_ADAPTER':raise ValueError('TRAINED_RUNTIME_CANDIDATE_TYPE')
        verified.add(key)
    def load(path,*,expected_file_sha256,expected_model):
        p=Path(path)
        if p.is_symlink() or not p.is_file():raise ValueError('TRAINED_RUNTIME_REGULAR_FILE_REQUIRED')
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected_file_sha256:raise ValueError('TRAINED_RUNTIME_FILE_SHA_MISMATCH')
        if json.loads(raw).get('schema_id')!=TRAINED_SCHEMA:return original(path,expected_file_sha256=expected_file_sha256,expected_model=expected_model)
        return load_trained_runtime(path,expected_file_sha256=expected_file_sha256,expected_model=expected_model,
            validate_native_contract=native._continuation_profile_v1,validate_artifacts=artifacts)
    load._registered_trained_reader=True
    native.load_continuation_runtime_binding_v2=load

def configure(a,root,identity):
    root=Path(root);os.environ[ROOT_ENV]=str(root);os.environ[SHA_ENV]=identity
    from memory_binding import worker_bootstrap as bootstrap
    if not getattr(bootstrap.worker_environment,'_registered_trained_environment',False):
        original=bootstrap.worker_environment
        def environment(*args,**kwargs):
            env=original(*args,**kwargs);prefix=str(root/'worker_startup')
            env['PYTHONPATH']=os.pathsep.join([prefix]+[p for p in env['PYTHONPATH'].split(os.pathsep) if p!=prefix])
            env[ROOT_ENV]=str(root);env[SHA_ENV]=identity
            return env
        environment._registered_trained_environment=True;bootstrap.worker_environment=environment
    bootstrap.bootstrap_current_and_children(a['scientific_repo_root'])
    install_reader(a)

def start_worker(root):
    root=Path(root);sys.path.insert(0,str(root))
    from profile_entry import verify
    identity=verify()
    if os.environ.get(ROOT_ENV)!=str(root) or os.environ.get(SHA_ENV)!=identity:raise ValueError('TRAINED_WORKER_AUTHORITY_MISMATCH')
    a=json.loads((root/'AUTHORITY.json').read_bytes())
    for ref in a['native_refs'].values():checked(ref)
    # Preserve the exact historical Memory and LoRA startup before extending it.
    legacy=a['native_refs']['memory_sitecustomize.py'];runpy.run_path(legacy['path'])
    configure(a,root,identity)
