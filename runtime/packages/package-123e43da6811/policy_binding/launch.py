"""Extend the original base service command with the actual registered LoRA."""
import copy
import hashlib
import json
from pathlib import Path

RUNTIME_SCHEMA = 'CURRENT_TRAINED_POLICY_RUNTIME_BINDING_V1'


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def read_ref(ref):
    from continuity_binding.api import read_bytes_ref
    return json.loads(read_bytes_ref(ref))


def verify_adapter(runtime):
    """Audit the finite trained file map at launch, including actual weight bytes."""
    from continuity_binding.api import read_bytes_ref, regular_path
    manifest=read_ref(runtime['adapter_artifact_manifest_ref'])
    material={'required_files':manifest['required_files'],'files':manifest['files']}
    # The Generic trainer uses canonical JSON without a trailing LF.
    bundle=sha(canonical(material)[:-1])
    if bundle!=runtime['adapter_bundle_sha256'] or manifest['adapter_bundle_sha256']!=bundle:
        raise ValueError('CANDIDATE_ADAPTER_BUNDLE_IDENTITY')
    root=regular_path(runtime['adapter_path'])
    files=manifest['files']
    if not {'adapter_config.json','adapter_model.safetensors'}<=set(files):
        raise ValueError('CANDIDATE_ACTUAL_LORA_WEIGHT_MEMBERS_REQUIRED')
    for name, spec in files.items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('CANDIDATE_ADAPTER_MEMBER_ESCAPE')
        raw=read_bytes_ref({'path':str(root/relative),'sha256':spec['sha256']})
        if len(raw)!=spec['size_bytes']: raise ValueError('CANDIDATE_ADAPTER_MEMBER_SIZE')
    config=json.loads(read_bytes_ref({'path':str(root/'adapter_config.json'),'sha256':files['adapter_config.json']['sha256']}))
    if config.get('peft_type')!='LORA' or type(config.get('r')) is not int or config['r']<=0:
        raise ValueError('CANDIDATE_LORA_CONFIGURATION')
    if config['r']!=runtime['adapter_rank']:
        raise ValueError('CANDIDATE_LORA_RANK_IDENTITY')
    if runtime['policy_runtime_manifest_sha256']!=bundle:
        raise ValueError('CANDIDATE_POLICY_WEIGHT_IDENTITY')
    return manifest


def extend_lora_launch(launch, runtime):
    """Retain original base launch for base runtime, bind real weights for V1."""
    if runtime.get('schema_id')!=RUNTIME_SCHEMA:
        return launch
    verify_adapter(runtime)
    result=copy.deepcopy(launch)
    command=result['launch_command']
    if '--enable-lora' in command or '--lora-modules' in command:
        raise ValueError('CANDIDATE_LORA_LAUNCH_ALREADY_EXTENDED')
    position=command.index('--served-model-name')+1
    if command[position]!=runtime['served_model_name']:
        raise ValueError('CANDIDATE_LORA_REQUEST_ALIAS_MISMATCH')
    # Base and adapter names must differ: the request model denotes the adapter,
    # while the underlying base retains its registered base service name.
    base_name=runtime['base_served_model_name']
    if not base_name or base_name==runtime['served_model_name']:
        raise ValueError('CANDIDATE_BASE_AND_ADAPTER_ALIAS_COLLISION')
    command[position]=base_name
    # Same CLI form as the pinned native run_memory_final_gpu_job_v1.py.
    module=runtime['served_model_name']+'='+runtime['adapter_path']
    command += ['--enable-lora','--max-lora-rank',str(runtime['adapter_rank']),
                '--lora-modules',module]
    result['trained_adapter_binding']={key:runtime[key] for key in (
        'adapter_path','adapter_bundle_sha256','adapter_rank','final_trainable_parameter_sha256',
        'adapter_artifact_manifest_ref','candidate_policy_ref','base_served_model_name')}
    result['launch_command_sha256']=sha(canonical(command))
    result['launch_contract_sha256']=sha(b'POLICY_RUNTIME_SERVICE_LAUNCH_CONTRACT_V1\0'+
        canonical({k:v for k,v in result.items() if k!='launch_contract_sha256'}))
    return result
