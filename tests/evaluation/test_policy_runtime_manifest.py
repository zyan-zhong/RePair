from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from pchsi.evaluation.policy_runtime_manifest import (
    PolicyRuntimeInputs,
    PolicyRuntimeManifestV1,
    build_policy_runtime_manifest,
    validate_policy_runtime_manifest,
)

REVISION="aa8e72537993ba99e69dfaafa59ed015b17504d1"

def _inputs():
    return PolicyRuntimeInputs(
        vllm_version="0.11.0",
        model_repository="Qwen/Qwen2.5-3B-Instruct",
        model_revision=REVISION,
        tokenizer_revision=REVISION,
        served_model_name="Qwen2.5-3B-Instruct-E1",
        dtype="bfloat16",
        tensor_parallel_size=1,
        generation_config_mode="vllm",
        chat_template_content_format="string",
        request_id_headers_enabled=True,
        return_token_ids_supported=True,
        prompt_token_ids_supported=True,
        tokenizer_manifest_sha256="a"*64,
        tokenizer_config_sha256="b"*64,
        special_tokens_map_sha256="c"*64,
        chat_template_sha256="d"*64,
    )

def test_policy_runtime_manifest_binds_server_and_tokenizer_identity(tmp_path: Path) -> None:
    output=tmp_path/"policy.json"
    manifest=build_policy_runtime_manifest(inputs=_inputs(),output_path=output)
    validate_policy_runtime_manifest(manifest)
    assert manifest.vllm_version=="0.11.0"
    assert manifest.model_revision==REVISION and manifest.tokenizer_revision==REVISION
    assert manifest.generation_config_mode=="vllm"
    assert stat.S_IMODE(output.stat().st_mode)==0o600
    assert PolicyRuntimeManifestV1.from_json(output.read_bytes())==manifest
    with pytest.raises(ValueError): validate_policy_runtime_manifest(replace(manifest,vllm_version="0.11.1"))

def test_policy_readiness_builder_uses_explicit_fixture_inputs_only(tmp_path: Path) -> None:
    root=Path(__file__).resolve().parents[2]
    build=root/"scripts/evaluation/build_policy_runtime_manifest.py"
    validate=root/"scripts/evaluation/validate_e1_vllm_readiness.py"
    output=tmp_path/"policy.json"
    command=[sys.executable,"-S",str(build),
        "--vllm-version","0.11.0","--model-repository","Qwen/Qwen2.5-3B-Instruct",
        "--model-revision",REVISION,"--tokenizer-revision",REVISION,
        "--served-model-name","Qwen2.5-3B-Instruct-E1","--dtype","bfloat16",
        "--tensor-parallel-size","1","--generation-config-mode","vllm",
        "--chat-template-content-format","string","--tokenizer-manifest-sha256","a"*64,
        "--tokenizer-config-sha256","b"*64,"--special-tokens-map-sha256","c"*64,
        "--chat-template-sha256","d"*64,"--output",str(output)]
    result=subprocess.run(command,text=True,capture_output=True,check=False)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)["status"]=="E1_POLICY_RUNTIME_MANIFEST_CREATED"
    result=subprocess.run([sys.executable,"-S",str(validate),"--manifest",str(output)],text=True,capture_output=True,check=False)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)["status"]=="E1_POLICY_RUNTIME_MANIFEST_VALID"
    source=build.read_text()+validate.read_text()
    for forbidden in ("requests.","httpx.","socket.","import vllm","import torch","from transformers","huggingface_hub"):
        assert forbidden not in source
