#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"src"))
def parser():
    p=argparse.ArgumentParser()
    for name in ("vllm-version","model-repository","model-revision","tokenizer-revision","served-model-name","dtype","generation-config-mode","chat-template-content-format","tokenizer-manifest-sha256","tokenizer-config-sha256","special-tokens-map-sha256","chat-template-sha256"): p.add_argument("--"+name,required=True)
    p.add_argument("--tensor-parallel-size",type=int,required=True); p.add_argument("--output",type=Path,required=True); return p

def main():
    a=parser().parse_args()
    from pchsi.evaluation.policy_runtime_manifest import PolicyRuntimeInputs,build_policy_runtime_manifest
    inputs=PolicyRuntimeInputs(vllm_version=a.vllm_version,model_repository=a.model_repository,model_revision=a.model_revision,tokenizer_revision=a.tokenizer_revision,served_model_name=a.served_model_name,dtype=a.dtype,tensor_parallel_size=a.tensor_parallel_size,generation_config_mode=a.generation_config_mode,chat_template_content_format=a.chat_template_content_format,request_id_headers_enabled=True,return_token_ids_supported=True,prompt_token_ids_supported=True,tokenizer_manifest_sha256=a.tokenizer_manifest_sha256,tokenizer_config_sha256=a.tokenizer_config_sha256,special_tokens_map_sha256=a.special_tokens_map_sha256,chat_template_sha256=a.chat_template_sha256)
    m=build_policy_runtime_manifest(inputs=inputs,output_path=a.output)
    print(json.dumps({"manifest_id":m.manifest_id,"output":str(a.output),"status":"E1_POLICY_RUNTIME_MANIFEST_CREATED"},sort_keys=True,separators=(",",":")))
    return 0
if __name__=="__main__": raise SystemExit(main())
