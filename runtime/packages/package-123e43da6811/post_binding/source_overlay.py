"""Exact edits to H4.4's existing POST, retaining its transport/recovery owner."""
from __future__ import annotations
import ast
import hashlib


def adapt_strong_post(source: str, *, expected_source_sha256: str) -> str:
    if hashlib.sha256(source.encode("utf8")).hexdigest() != expected_source_sha256:
        raise ValueError("REGISTERED_H44_POST_SOURCE_DRIFT")

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("H44_POST_OVERLAY_ANCHOR_NOT_UNIQUE:" + old[:80])
        source = source.replace(old, new)

    # The caller injects _POST_MATERIALIZATION_CONTEXT after deriving it from the
    # current verified dual-view dataset, before this module executes any call.
    replace("from io_utils import read_json, put_json, sha, canonical as canon, digest_file",
            "from io_utils import read_json, put_json, sha, canonical as canon, digest_file, write_new_or_equal\n"
            "from post_binding.runtime import prepare_projection, extend_prompt, validate_post_output, adopt_recipe\n"
            "from training_binding.materializer import extend_post_schema")
    replace("    # Adopt a complete, hash-bound manifest already captured with the accepted PRE.",
            "    projection=prepare_projection(projection,_POST_MATERIALIZATION_CONTEXT)\n"
            "    # Adopt a complete, hash-bound manifest already captured with the accepted PRE.")
    replace("    schema,_=normalize_const_types(json.loads(raw));props=schema['properties']",
            "    schema,_=normalize_const_types(json.loads(raw))\n"
            "    schema=extend_post_schema(schema,_POST_MATERIALIZATION_CONTEXT)\n"
            "    props=schema['properties']\n"
            "    prompt=extend_prompt(prompt.decode('utf8')).encode('utf8')\n"
            "    write_new_or_equal(postdir/'POST_MATERIALIZATION_PROMPT.txt',prompt)")
    replace("    spec.update(prompt_relative_path=str(ROOT/'assets/RESEARCHER_POST_PRIMARY_V1.txt'),",
            "    spec.update(prompt_relative_path=str(postdir/'POST_MATERIALIZATION_PROMPT.txt'),prompt_sha256=sha(prompt),")
    replace("        return finalize_api_post_primary_v1(value,projection=projection)",
            "        return validate_post_output(value,projection=projection,raw_response_sha256=raw_response_sha256,\n"
            "            logical_call_id=logical_id,output_root=postdir,native_finalize=finalize_api_post_primary_v1)")
    replace("        return route_accepted_post_artifact(\n            run_root=run_root,",
            "        recipe_ref=adopt_recipe(call_dir=call,output_root=postdir,\n"
            "            expected={'logical_call_id':logical_id,**logical_key,'runtime_manifest_sha256':manifest['runtime_manifest_sha256']},projection=projection,\n"
            "            native_finalize=finalize_api_post_primary_v1)\n"
            "        result=route_accepted_post_artifact(\n            run_root=run_root,")
    replace("            provider_calls=calls,\n        )",
            "            provider_calls=calls,\n        )\n"
            "        return dict(result,accepted_training_recipe_binding=recipe_ref)")
    ast.parse(source, feature_version=(3, 12))
    return source
