"""Fixture-safe policy runtime identity for E1 evaluator readiness."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
from .canonical_evidence import canonical_json_text, require_lower_sha256, strict_json_loads
from .schema_contract import validate_payload_against_schema
REVISION="aa8e72537993ba99e69dfaafa59ed015b17504d1"
@dataclass(frozen=True,slots=True)
class PolicyRuntimeInputs:
    vllm_version:str; model_repository:str; model_revision:str; tokenizer_revision:str; served_model_name:str; dtype:str; tensor_parallel_size:int; generation_config_mode:str; chat_template_content_format:str; request_id_headers_enabled:bool; return_token_ids_supported:bool; prompt_token_ids_supported:bool; tokenizer_manifest_sha256:str; tokenizer_config_sha256:str; special_tokens_map_sha256:str; chat_template_sha256:str
    def __post_init__(self):
        expected={"vllm_version":"0.11.0","model_repository":"Qwen/Qwen2.5-3B-Instruct","model_revision":REVISION,"tokenizer_revision":REVISION,"served_model_name":"Qwen2.5-3B-Instruct-E1","dtype":"bfloat16","generation_config_mode":"vllm","chat_template_content_format":"string"}
        for name,value in expected.items():
            if getattr(self,name)!=value: raise ValueError(f"{name} mismatch")
        if self.tensor_parallel_size!=1: raise ValueError("tensor_parallel_size must be 1")
        for name in ("request_id_headers_enabled","return_token_ids_supported","prompt_token_ids_supported"):
            if getattr(self,name) is not True: raise ValueError(f"{name} must be true")
        for name in ("tokenizer_manifest_sha256","tokenizer_config_sha256","special_tokens_map_sha256","chat_template_sha256"): require_lower_sha256(name,getattr(self,name))
@dataclass(frozen=True,slots=True)
class PolicyRuntimeManifestV1:
    schema_id:str; schema_version:int; manifest_id:str; vllm_version:str; model_repository:str; model_revision:str; tokenizer_revision:str; served_model_name:str; dtype:str; tensor_parallel_size:int; generation_config_mode:str; chat_template_content_format:str; request_id_headers_enabled:bool; return_token_ids_supported:bool; prompt_token_ids_supported:bool; tokenizer_manifest_sha256:str; tokenizer_config_sha256:str; special_tokens_map_sha256:str; chat_template_sha256:str
    def __post_init__(self):
        validate_policy_runtime_manifest(self); validate_payload_against_schema(schema_id="E1_POLICY_RUNTIME_MANIFEST_V1",payload=self.to_dict())
    def to_dict(self): return {name:getattr(self,name) for name in self.__dataclass_fields__}
    def to_json(self): return canonical_json_text(self.to_dict())
    @classmethod
    def from_json(cls,value):
        payload=strict_json_loads(value)
        if not isinstance(payload,dict) or set(payload)!=set(cls.__dataclass_fields__): raise ValueError("policy runtime fields mismatch")
        return cls(**payload)
def validate_policy_runtime_manifest(manifest:PolicyRuntimeManifestV1)->None:
    PolicyRuntimeInputs(**{name:getattr(manifest,name) for name in PolicyRuntimeInputs.__dataclass_fields__})
def build_policy_runtime_manifest(*,inputs:PolicyRuntimeInputs,output_path:Path)->PolicyRuntimeManifestV1:
    manifest=PolicyRuntimeManifestV1(schema_id="E1_POLICY_RUNTIME_MANIFEST_V1",schema_version=1,manifest_id="E1_POLICY_RUNTIME_MANIFEST_V1",**{name:getattr(inputs,name) for name in PolicyRuntimeInputs.__dataclass_fields__})
    path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try: os.write(fd,manifest.to_json().encode()); os.fsync(fd)
    finally: os.close(fd)
    return manifest
