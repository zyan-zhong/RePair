"""Bind two existing SHA contracts without altering either contract or input bytes.

Stage4D BINDING_IDENTITY pins compact JSON without LF. Native typed objects use
pchsi.evaluation.canonical_evidence (compact JSON plus LF). A native hash is
returned ONLY after the original binding identity and artifact payload match.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any

ROOT = Path(__file__).resolve().parent
PINS = json.loads((ROOT/'source_pins.json').read_bytes())
SCHEDULE_OLD = "allowed_schedule_hashes = {label:identity['artifacts'][f'{label}_CONDITION_RUN_SCHEDULE_V1.json'] for label in ('T0','T2')}"
SCHEDULE_NEW = "allowed_schedule_hashes = {label:_registered_native_hash(schedules[label], identity, f'{label}_CONDITION_RUN_SCHEDULE_V1.json', cfg['binding_sha256'], native) for label in ('T0','T2')}"
RUNTIME_OLD = "runtime_sha=identity['artifacts'][f'{label}_SELECT_POLICY_RUNTIME_MANIFEST_V1.json'],"
RUNTIME_NEW = "runtime_sha=_registered_native_hash(runtimes[label], identity, f'{label}_SELECT_POLICY_RUNTIME_MANIFEST_V1.json', cfg['binding_sha256'], native),"


def registered_native_hash(model: Any, identity: dict, name: str,
                           binding_sha: str, native: dict) -> str:
    from stage4e import GateError, semantic_sha
    if semantic_sha(identity) != binding_sha:
        raise GateError('HASH_BRIDGE_BINDING_IDENTITY_CHANGED')
    artifacts = identity.get('artifacts')
    if not isinstance(artifacts,dict) or name not in artifacts:
        raise GateError('HASH_BRIDGE_UNREGISTERED_ARTIFACT:'+name)
    payload=model.to_dict()
    if semantic_sha(payload) != artifacts[name]:
        raise GateError('HASH_BRIDGE_MODEL_NOT_BOUND:'+name)
    # Exactly the same function used by Stage4D prepare/live and native SELECT audit.
    return native['canonical_model_sha256'](model)


def verify_native_sources(repo: Path) -> None:
    from stage4e import require_file_sha, safe_child
    for name,digest in PINS['native_files'].items():
        require_file_sha(safe_child(repo,name),digest)


def corrected_audit_source(raw: bytes) -> str:
    from stage4e import GateError
    if hashlib.sha256(raw).hexdigest()!=PINS['old_audit_sha256']:
        raise GateError('ORIGINAL_AUDIT_CHANGED')
    text=raw.decode('utf-8')
    for old,new in ((SCHEDULE_OLD,SCHEDULE_NEW),(RUNTIME_OLD,RUNTIME_NEW)):
        if text.count(old)!=1:raise GateError('AUDIT_BRIDGE_CALL_SITE_CHANGED')
        text=text.replace(old,new,1)
    return text


def load_corrected_audit(old_root: Path):
    path=old_root/'stage4e/audit.py'
    from stage4e import regular
    text=corrected_audit_source(regular(path).read_bytes())
    name='stage4e._registered_native_hash_audit'
    module=types.ModuleType(name)
    module.__file__=str(path)
    module.__package__='stage4e'
    module._registered_native_hash=registered_native_hash
    sys.modules[name]=module
    exec(compile(text,str(path),'exec'),module.__dict__)
    return module


def build_bridge_report(cfg: dict, repo: Path, binding: Path) -> dict:
    """Only frozen metadata is read. No SELECT result, model, or environment call."""
    from stage4e import read_json, file_sha, canonical, semantic_sha, GateError
    verify_native_sources(repo)
    sys.path.insert(0,str(repo/'src'))
    from pchsi.evaluation.distillation_governance import canonical_model_sha256
    from pchsi.evaluation.condition_run_schedule import ConditionRunScheduleV1
    from pchsi.evaluation.select_policy_runtime import SelectPolicyRuntimeManifestV1
    from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
    identity=read_json(binding/'BINDING_IDENTITY.json')
    native={'canonical_model_sha256':canonical_model_sha256}
    schedules={}; schedule_hashes={}; entries=[]
    for label in ('T0','T2'):
        for suffix,cls in (('CONDITION_RUN_SCHEDULE_V1.json',ConditionRunScheduleV1),
                           ('SELECT_POLICY_RUNTIME_MANIFEST_V1.json',SelectPolicyRuntimeManifestV1)):
            name=label+'_'+suffix
            obj=read_json(binding/name); model=cls.from_dict(obj)
            if canonical(model.to_dict())!=canonical(obj):
                raise GateError('HASH_BRIDGE_TYPED_ROUNDTRIP_CHANGED:'+name)
            value=registered_native_hash(model,identity,name,cfg['binding_sha256'],native)
            entries.append({'path':name,'frozen_binding_artifact_sha256':identity['artifacts'][name],
                'native_model_sha256':value,'file_sha256':file_sha(binding/name),
                'binding_serialization':'COMPACT_SORTED_UTF8_NO_LF',
                'native_serialization':'REPOSITORY_CANONICAL_UTF8_WITH_LF'})
            if suffix.startswith('CONDITION'):
                schedules[label]=model;schedule_hashes[label]=value
    expected=derive_expected_select_cells_from_master_schedules(schedules=schedules,authorized_schedule_sha256=schedule_hashes)
    if len(expected)!=2*cfg['pair_count']:
        raise GateError('HASH_BRIDGE_NATIVE_CELL_UNIVERSE_CHANGED')
    return {'schema_id':'STAGE4E_REGISTERED_NATIVE_HASH_BRIDGE_V1','schema_version':1,
        'binding_sha256':cfg['binding_sha256'],'authorization_sha256':cfg['authorization_sha256'],
        'original_audit_file_sha256':PINS['old_audit_sha256'],
        'entries':entries,'native_expected_condition_cells':len(expected),
        'existing_binding_inventory_required':True,'native_validator_changed':False,
        'frozen_input_bytes_changed':False,'new_scientific_cells_executed':0,
        'strong_execution_authorized':False}
