"""Keep the native POST decision and its recipe in one accepted logical call.

No provider client or retry loop lives here. The existing runtime renders and
executes the call. A validated callback output is not an accepted call until
the native logical terminal and contributing transport attempt agree.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re

from exact_bindings import (BindingError, canonical, digest, file_ref,
                            immutable_json, loads, read_json, read_ref)


def _sha(value, label):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise BindingError("POST_SHA_REQUIRED:" + label)
    return value


def prepare_projection(projection, context):
    """Add current materialized dataset identity, never a chosen recipe default."""
    from training_binding.materializer import extend_post_schema
    if context is not None:
        _sha(context.get("dataset_sha256"), "dataset")
        if type(context.get("row_count")) is not int or context["row_count"] <= 0:
            raise BindingError("POST_CURRENT_DUAL_VIEW_DATASET_REQUIRED")
    result = deepcopy(projection)
    if "training_materialization_context" in result:
        if result["training_materialization_context"] != context:
            raise BindingError("POST_MATERIALIZATION_CONTEXT_CONFLICT")
    result["training_materialization_context"] = deepcopy(context)
    # The same schema function validates the context before render and callback.
    extend_post_schema({"type": "object", "properties": {}, "required": []}, context)
    return result


def extend_prompt(original):
    suffix = (
        "\n\nThe machine output schema additionally requires training_recipe. "
        "When your recommendation is NO_TRAIN, return null. When it is TRAIN, "
        "choose the structured recipe and budget for the supplied current verified "
        "dual-view dataset. Do not invent dataset identity, change effect labels, "
        "alter the frozen PRE, or claim training or promotion has occurred. "
        "The deterministic builder will validate and freeze your explicit choices.\n"
    )
    return original + suffix


def validate_post_output(value, *, projection, raw_response_sha256,
                         logical_call_id, output_root, native_finalize):
    """Called inside the existing native validate_stage_output callback."""
    from training_binding.materializer import validate_recipe
    _sha(logical_call_id, "logical_call_id")
    _sha(raw_response_sha256, "raw_response_sha256")
    if not isinstance(value, dict) or "training_recipe" not in value:
        raise BindingError("STRUCTURED_POST_RECIPE_FIELD_REQUIRED")
    base = deepcopy(value)
    recipe = base.pop("training_recipe")
    for field in ("round_id", "primary_pre_record_sha256", "environment_result_package_sha256"):
        if base.get(field) != projection.get(field):
            raise BindingError("POST_CURRENT_IDENTITY_MISMATCH:" + field)
    recommendation = base.get("researcher_training_recommendation")
    if recommendation == "NO_TRAIN":
        if recipe is not None:
            raise BindingError("NO_TRAIN_CANNOT_CARRY_EXECUTABLE_RECIPE")
    elif recommendation == "TRAIN":
        if recipe is None:
            raise BindingError("TRAIN_REQUIRES_STRUCTURED_RECIPE")
        if projection.get("training_materialization_context") is None:
            raise BindingError("TRAIN_REQUIRES_CURRENT_DATASET_CONTEXT")
        recipe = validate_recipe(recipe, projection["training_materialization_context"])
    else:
        raise BindingError("POST_TYPED_TRAINING_RECOMMENDATION_REQUIRED")
    artifact = native_finalize(base, projection=projection)
    if artifact.get("researcher_training_recommendation") != recommendation:
        raise BindingError("NATIVE_FINALIZER_CHANGED_TRAINING_DECISION")
    candidate = {
        "schema_id": "POST_SAME_CALL_RECIPE_VALIDATED_OUTPUT_V1",
        "logical_call_id": logical_call_id,
        "raw_response_sha256": raw_response_sha256,
        "round_id": artifact["round_id"],
        "post_primary_record_sha256": artifact["primary_record_sha256"],
        "projection_sha256": digest(canonical(projection)),
        "training_recommendation": recommendation,
        "context": deepcopy(projection.get("training_materialization_context")),
        "recipe": recipe,
        "logical_call_acceptance_claimed": False,
        "training_execution_authorized": False,
    }
    immutable_json(Path(output_root) / "recipe_decisions" / (logical_call_id + ".json"), candidate)
    return artifact


def adopt_recipe(*, call_dir, output_root, expected, projection, native_finalize):
    """Adopt only an already accepted native call; sends nothing on recovery."""
    from training_binding.materializer import build_recipe_receipt
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.cognitive_runtime.schema_registry import validate_artifact
    from pchsi.cognitive_runtime.response import parse_provider_response, extract_output_text
    call_dir = Path(call_dir).absolute()
    required = {"logical_call_id", "scientific_unit_identity_sha256", "stage_id", "condition_id",
                "round_id", "policy_version", "request_body_sha256", "runtime_manifest_sha256"}
    if not required <= set(expected) or expected["stage_id"] != "R-POST-PRIMARY-V1":
        raise BindingError("EXACT_CURRENT_POST_LOGICAL_BINDING_REQUIRED")
    logical_id = _sha(expected.get("logical_call_id"), "logical_call_id")
    if call_dir.name != logical_id:
        raise BindingError("POST_CALL_DIRECTORY_IDENTITY")
    logical = read_json(call_dir / "logical_call.json")
    validate_artifact("LOGICAL_CALL_RECORD_V1", logical)
    if logical.get("logical_call_sha256") != domain_hash("LOGICAL_CALL_RECORD_V1", logical,
                                                        excluded_field="logical_call_sha256"):
        raise BindingError("POST_RECIPE_LOGICAL_DOMAIN_HASH")
    for key, value in expected.items():
        if logical.get(key) != value:
            raise BindingError("POST_RECIPE_LOGICAL_IDENTITY:" + key)
    if logical.get("terminal_method_status") != "ACCEPTED":
        raise BindingError("POST_RECIPE_REQUIRES_ACCEPTED_LOGICAL_CALL")
    attempt_id = logical.get("contributing_attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id.startswith(logical_id + ":"):
        raise BindingError("POST_RECIPE_CONTRIBUTING_ATTEMPT_REQUIRED")
    ordinal = attempt_id[len(logical_id) + 1:]
    if re.fullmatch(r"[0-9]+", ordinal) is None:
        raise BindingError("POST_RECIPE_ATTEMPT_INDEX_INVALID")
    attempt = read_json(call_dir / ("attempt_%03d.json" % int(ordinal)))
    validate_artifact("TRANSPORT_ATTEMPT_RECORD_V1", attempt)
    if attempt.get("attempt_sha256") != domain_hash("TRANSPORT_ATTEMPT_RECORD_V1", attempt,
                                                  excluded_field="attempt_sha256"):
        raise BindingError("POST_RECIPE_ATTEMPT_DOMAIN_HASH")
    if (attempt.get("logical_call_id") != logical_id
            or attempt.get("transport_attempt_id") != attempt_id
            or attempt.get("transport_attempt_index") != int(ordinal)
            or attempt.get("terminal_attempt_status") != "SUCCEEDED"):
        raise BindingError("POST_RECIPE_CONTRIBUTING_ATTEMPT_MISMATCH")
    request_ref = {"path": str(call_dir / "raw_request.json"),
                   "file_sha256": _sha(attempt.get("raw_request_sha256"), "raw_request")}
    request = loads(read_ref(request_ref, as_bytes=True))
    if domain_hash("COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1", request) != expected["request_body_sha256"]:
        raise BindingError("POST_RECIPE_RAW_REQUEST_CURRENT_IDENTITY")
    artifact = read_json(call_dir / "validated_artifact.json")
    if native_finalize(artifact, projection=projection) != artifact:
        raise BindingError("POST_RECIPE_NATIVE_ARTIFACT_INVALID")
    decision_path = Path(output_root).absolute() / "recipe_decisions" / (logical_id + ".json")
    decision = read_json(decision_path)
    checks = {
        "schema_id": "POST_SAME_CALL_RECIPE_VALIDATED_OUTPUT_V1",
        "logical_call_id": logical_id,
        "round_id": artifact["round_id"],
        "post_primary_record_sha256": artifact["primary_record_sha256"],
        "projection_sha256": digest(canonical(projection)),
        "raw_response_sha256": attempt.get("raw_response_sha256"),
        "training_recommendation": artifact["researcher_training_recommendation"],
        "context": projection.get("training_materialization_context"),
        "logical_call_acceptance_claimed": False,
        "training_execution_authorized": False,
    }
    for key, value in checks.items():
        if type(decision.get(key)) is not type(value) or decision.get(key) != value:
            raise BindingError("POST_RECIPE_VALIDATED_OUTPUT_MISMATCH:" + key)
    _sha(attempt.get("raw_response_sha256"), "contributing_response")
    response_ref = {"path": str(call_dir / "raw_response.json"),
                    "file_sha256": attempt["raw_response_sha256"]}
    response = parse_provider_response(read_ref(response_ref, as_bytes=True))
    original_output = loads(extract_output_text(response))
    if not isinstance(original_output, dict) or "training_recipe" not in original_output:
        raise BindingError("POST_RECIPE_NOT_IN_ACCEPTED_RAW_RESPONSE")
    original_recipe = original_output.pop("training_recipe")
    if original_recipe != decision["recipe"] or native_finalize(original_output, projection=projection) != artifact:
        raise BindingError("POST_RECIPE_RAW_RESPONSE_DECISION_DRIFT")
    receipt = build_recipe_receipt(
        recipe=decision["recipe"], context=decision["context"], accepted_post=artifact,
        logical_call_id=logical_id, raw_response_sha256=attempt["raw_response_sha256"],
        logical_call_status="ACCEPTED",
    )
    result = {
        "schema_id": "POST_ACCEPTED_SAME_CALL_RECIPE_BINDING_V1",
        "round_id": artifact["round_id"], "logical_call_id": logical_id,
        "post_primary_record_sha256": artifact["primary_record_sha256"],
        "native_post": file_ref(call_dir / "validated_artifact.json"),
        "native_logical_call": file_ref(call_dir / "logical_call.json"),
        "native_contributing_attempt": file_ref(call_dir / ("attempt_%03d.json" % int(ordinal))),
        "native_raw_response": response_ref,
        "native_raw_request": request_ref,
        "validated_decision": file_ref(decision_path),
        "recipe_receipt": receipt,
        "additional_provider_call_count": 0,
        "scientific_execution_started_by_adoption": False,
    }
    path = Path(output_root) / "POST_ACCEPTED_RECIPE_BINDING.json"
    immutable_json(path, result)
    return file_ref(path)
