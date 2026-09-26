"""Thin data/authority producer; contains no provider client or optimizer.

Recipe decisions belong to the existing Strong POST call (ledger 20663-20675).
Only current, verified Stage6AN dual-view data is accepted. Native Generic V2
validators and the existing V1.11 PEFT delegate retain execution semantics.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable

DECISION_SCHEMA = "CURRENT_STRONG_POST_TRAINING_RECIPE_V1"
RECEIPT_SCHEMA = "CURRENT_STRONG_POST_TRAINING_RECIPE_RECEIPT_V1"
SEMANTICS = "VERIFIED_BENEFIT_DUAL_VIEW_COMPLETE_PAIRS"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(name + "_SHA_INVALID")
    return value


def _seal(value: dict, field: str) -> dict:
    result = copy.deepcopy(value)
    result[field] = digest({k: v for k, v in result.items() if k != field})
    return result


def _verify_seal(value: dict, field: str) -> None:
    if _sha(value.get(field), field) != digest({k: v for k, v in value.items() if k != field}):
        raise ValueError(field + "_MISMATCH")


def _verify_h44_seal(value: dict, field: str) -> None:
    """H4.4 io_utils.canonical includes LF; never reinterpret native identities."""
    payload = {k: v for k, v in value.items() if k != field}
    if _sha(value.get(field), field) != hashlib.sha256(canonical(payload) + b"\n").hexdigest():
        raise ValueError("H44_" + field + "_MISMATCH")


def _read_ref(ref: dict) -> bytes:
    path = Path(ref["path"])
    if not path.is_file() or path.is_symlink():
        raise ValueError("INPUT_REF_NOT_REGULAR_FILE:" + str(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != _sha(ref.get("sha256"), "INPUT_REF"):
        raise ValueError("INPUT_REF_SHA_MISMATCH:" + str(path))
    return raw


def recipe_schema(context: dict | None = None) -> dict:
    """No numeric defaults: Strong supplies every optimization choice."""
    props = {
        "epochs": {"type": "integer", "minimum": 1},
        "micro_batch_size": {"type": "integer", "const": 1},
        "gradient_accumulation_steps": {"type": "integer", "minimum": 1},
        "learning_rate": {"type": "number", "exclusiveMinimum": 0},
        "weight_decay": {"type": "number", "minimum": 0},
        "max_grad_norm": {"type": "number", "exclusiveMinimum": 0},
        "warmup_steps": {"type": "integer", "minimum": 0},
        "training_seed": {"type": "integer", "minimum": 0},
        "data_seed": {"type": "integer", "minimum": 0},
        "dataset_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "data_semantics": {"type": "string", "const": SEMANTICS},
        "rationale": {"type": "string", "minLength": 1},
    }
    if context is not None:
        props["dataset_sha256"]["const"] = _sha(context["dataset_sha256"], "DATASET")
        for seed in ("training_seed", "data_seed"):
            if seed in context:
                props[seed]["const"] = context[seed]
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


def extend_post_schema(base_schema: dict, context: dict | None = None) -> dict:
    """Extend the SAME POST output; caller strips recipe before native finalizer.

    The provider-facing nullable schema avoids imposing a second scientific call.
    validate_recipe and the POST binding enforce route-dependent nullability.
    """
    out = copy.deepcopy(base_schema)
    out.setdefault("properties", {})["training_recipe"] = {"anyOf": [recipe_schema(context), {"type": "null"}]}
    required = out.setdefault("required", [])
    if "training_recipe" not in required:
        required.append("training_recipe")
    return out


def validate_recipe(recipe: Any, context: dict) -> dict:
    import jsonschema
    if not isinstance(context, dict):
        raise ValueError("TRAIN_RECIPE_REQUIRES_CURRENT_DATASET_CONTEXT")
    try:
        jsonschema.Draft202012Validator(recipe_schema(context)).validate(recipe)
    except jsonschema.ValidationError as exc:
        raise ValueError("STRUCTURED_TRAINING_RECIPE_INVALID:" + exc.message) from exc
    # jsonschema treats 1.0 as integer; native contracts require Python integers.
    for key in ("epochs", "micro_batch_size", "gradient_accumulation_steps", "warmup_steps", "training_seed", "data_seed"):
        if type(recipe[key]) is not int:
            raise ValueError("RECIPE_EXACT_INTEGER_REQUIRED:" + key)
    for key in ("learning_rate", "weight_decay", "max_grad_norm"):
        if type(recipe[key]) not in (int, float) or not math.isfinite(recipe[key]):
            raise ValueError("RECIPE_FINITE_NUMBER_REQUIRED:" + key)
    if recipe["training_seed"] != recipe["data_seed"]:
        raise ValueError("NATIVE_FORMAL_MATCHED_SEEDS_REQUIRED")
    n = context["row_count"]
    if type(n) is not int or n <= 0:
        raise ValueError("CURRENT_NATIVE_ROW_COUNT_INVALID")
    batch = recipe["micro_batch_size"] * recipe["gradient_accumulation_steps"]
    # Native V2 contracts.py:393-395 forbids partial accumulation groups.
    if n % batch:
        raise ValueError("NATIVE_GENERIC_V2_REMAINDER_UNSUPPORTED")
    steps = (n // batch) * recipe["epochs"]
    if recipe["warmup_steps"] > steps:
        raise ValueError("WARMUP_EXCEEDS_NATIVE_DERIVED_STEPS")
    return copy.deepcopy(recipe)


def build_recipe_receipt(*, recipe: Any, context: dict | None, accepted_post: dict,
                         logical_call_id: str, raw_response_sha256: str,
                         logical_call_status: str) -> dict:
    """Call only after native POST validation and logical terminal acceptance."""
    if logical_call_status != "ACCEPTED" or not isinstance(logical_call_id, str) or not logical_call_id:
        raise ValueError("RECIPE_REQUIRES_ACCEPTED_LOGICAL_CALL")
    route = accepted_post.get("researcher_training_recommendation")
    if route == "NO_TRAIN":
        if recipe is not None:
            raise ValueError("NO_TRAIN_RECIPE_MUST_BE_NULL")
        normalized = None
    elif route == "TRAIN":
        normalized = validate_recipe(recipe, context)
    else:
        raise ValueError("POST_TYPED_TRAINING_ROUTE_INVALID")
    return _seal({"schema_id": RECEIPT_SCHEMA, "schema_version": 1,
                  "round_id": accepted_post["round_id"],
                  "post_primary_record_sha256": _sha(accepted_post["primary_record_sha256"], "POST"),
                  "logical_call_id": logical_call_id, "logical_call_status": logical_call_status,
                  "raw_response_sha256": _sha(raw_response_sha256, "RAW_RESPONSE"),
                  "training_recommendation": route, "context": copy.deepcopy(context),
                  "recipe": normalized, "training_execution_count": 0,
                  "training_execution_authorized": False}, "recipe_receipt_sha256")


@dataclass(frozen=True)
class NativeTraining:
    root: Path
    dual_path: Path
    contracts: Any
    common: Any
    adapter: Any
    dual: Any
    source_sha256s: dict[str, str]

    @classmethod
    def load(cls, generic_root: Path, dual_adapter: Path, source_sha256s: dict[str, str]):
        generic_root, dual_adapter = Path(generic_root).resolve(), Path(dual_adapter).resolve()
        required = [generic_root / "round_training" / x for x in (
            "__init__.py", "common.py", "contracts.py", "receipts.py", "stage_runner.py",
            "adapters/frozen_formal_train_peft.py",
        )] + [dual_adapter]
        for path in required:
            _read_ref({"path": str(path), "sha256": source_sha256s.get(str(path))})
        sys.path.insert(0, str(generic_root))
        contracts = importlib.import_module("round_training.contracts")
        common = importlib.import_module("round_training.common")
        for module in (contracts, common):
            if Path(module.__file__).resolve().parent != generic_root / "round_training":
                raise ValueError("NATIVE_TRAINING_IMPORT_ROOT_CONFLICT")
        def load_file(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        adapter = load_file("v17_native_frozen_peft", generic_root / "round_training/adapters/frozen_formal_train_peft.py")
        dual = load_file("v17_native_dual_view", dual_adapter)
        return cls(generic_root, dual_adapter, contracts, common, adapter, dual, dict(source_sha256s))

    def revalidate_sources(self):
        for path, expected in self.source_sha256s.items():
            _read_ref({"path": path, "sha256": expected})


def build_recipe_projection(*, native: NativeTraining, accepted_post: dict, handoff: dict,
                            dataset_ref: dict, dataset_manifest_ref: dict,
                            manifest_domain_sha_field: str, census: dict, current: dict,
                            validate_accepted_post: Callable[[dict], dict]) -> dict:
    """Freeze current native inputs AFTER the original POST was accepted.

    A same-call recipe receipt can be accepted against this projection afterward.
    This function does not call the provider, relabel rows, or choose a recipe.
    """
    if validate_accepted_post(copy.deepcopy(accepted_post)) != accepted_post:
        raise ValueError("NATIVE_POST_VALIDATOR_DRIFT")
    result = {"schema_id": "CURRENT_TRAINING_MATERIALIZATION_INPUT_V1", "schema_version": 1,
              "accepted_post": copy.deepcopy(accepted_post), "handoff": copy.deepcopy(handoff),
              "dataset_ref": copy.deepcopy(dataset_ref), "dataset_manifest_ref": copy.deepcopy(dataset_manifest_ref),
              "manifest_domain_sha_field": manifest_domain_sha_field, "census": copy.deepcopy(census),
              "current": copy.deepcopy(current)}
    _check_projection(native, result)
    return _seal(result, "projection_sha256")


def _check_projection(native, projection):
    native.revalidate_sources()
    post, handoff, current = projection["accepted_post"], projection["handoff"], projection["current"]
    if post.get("researcher_training_recommendation") != "TRAIN":
        raise ValueError("POST_NO_TRAIN_FORBIDS_MATERIALIZATION")
    if handoff.get("schema_id") != "CURRENT_VERIFIED_TRAINING_HANDOFF_V1":
        raise ValueError("CURRENT_TRAINING_HANDOFF_SCHEMA_MISMATCH")
    _verify_h44_seal(handoff, "handoff_sha256")
    expected = {"round_id": post["round_id"], "post_primary_record_sha256": post["primary_record_sha256"],
                "source_pre_primary_record_sha256": post["primary_pre_record_sha256"],
                "environment_result_package_sha256": post["environment_result_package_sha256"],
                "parent_policy_id": current["parent"]["policy_id"], "training_execution_authorized": False,
                "training_execution_count": 0}
    if any(handoff.get(k) != v for k, v in expected.items()):
        raise ValueError("CURRENT_TRAINING_HANDOFF_IDENTITY_MISMATCH")
    benefits = handoff["verified_benefit_state_results"]
    if type(handoff["verified_benefit_state_count"]) is not int or handoff["verified_benefit_state_count"] <= 0:
        raise ValueError("CURRENT_BENEFIT_REQUIRED")
    if len(benefits) != handoff["verified_benefit_state_count"] or any(x.get("stable_effect") != "BENEFIT" for x in benefits):
        raise ValueError("CURRENT_BENEFIT_SET_INVALID")
    _read_ref(projection["dataset_ref"])
    manifest = json.loads(_read_ref(projection["dataset_manifest_ref"]))
    _sha(manifest[projection["manifest_domain_sha_field"]], "DATASET_MANIFEST_DOMAIN")
    rows = native.dual.load_dual_view_records(Path(projection["dataset_ref"]["path"]))
    states = {r["source_state_sha256"] for r in rows}
    eligible = {x["source_state_sha256"] for x in benefits}
    if not states <= eligible:
        raise ValueError("DATASET_CONTAINS_NON_CURRENT_BENEFIT_STATE")
    native.dual.validate_dual_view_census(projection["census"])
    if projection["census"]["STRATEGY_ROW_COUNT"] != len(states):
        raise ValueError("CENSUS_NATIVE_STRATEGY_ROW_COUNT_MISMATCH")
    actual_total = sum(r["tokenization"]["completion_loss_token_count"] for r in rows)
    if projection["census"]["TOTAL_LOSS_BEARING_TOKEN_COUNT"] != actual_total:
        raise ValueError("CENSUS_NATIVE_TOTAL_TOKEN_MISMATCH")
    _sha(current["current_parent_binding_sha256"], "CURRENT_PARENT_BINDING")
    _sha(current["runner_freeze_root_sha256"], "RUNNER_FREEZE")
    return rows, manifest


def recipe_context(projection: dict) -> dict:
    current = projection["current"]
    result = {"dataset_sha256": projection["dataset_ref"]["sha256"],
              "row_count": projection["census"]["STRATEGY_ROW_COUNT"] * 2}
    # Parent's original training seed is provenance, not automatically a new-round constraint.
    for key in ("training_seed", "data_seed"):
        if key in current:
            result[key] = current[key]
    return result


def accept_recipe_decision(raw: dict, *, projection: dict) -> dict:
    """Normalize a structured decision, or a same-POST receipt supplied by caller."""
    _verify_seal(projection, "projection_sha256")
    if raw.get("schema_id") == RECEIPT_SCHEMA:
        _verify_seal(raw, "recipe_receipt_sha256")
        if raw.get("logical_call_status") != "ACCEPTED" or raw.get("training_recommendation") != "TRAIN":
            raise ValueError("RECIPE_RECEIPT_NOT_ACCEPTED_TRAIN")
        if raw.get("context") != recipe_context(projection):
            raise ValueError("RECIPE_RECEIPT_CONTEXT_MISMATCH")
        value = {"schema_id": DECISION_SCHEMA, "schema_version": 1, "round_id": raw["round_id"],
                 "post_primary_record_sha256": raw["post_primary_record_sha256"],
                 "projection_sha256": projection["projection_sha256"], "recipe": raw["recipe"],
                 "same_call_recipe_receipt": copy.deepcopy(raw)}
    elif raw.get("schema_id") == DECISION_SCHEMA and isinstance(raw.get("same_call_recipe_receipt"), dict):
        value = accept_recipe_decision(raw["same_call_recipe_receipt"], projection=projection)
        if raw != value:
            raise ValueError("RECIPE_DECISION_SAME_CALL_RECEIPT_MISMATCH")
        return value
    else:
        raise ValueError("RECIPE_REQUIRES_SAME_ACCEPTED_POST_CALL_RECEIPT")
    expected = {"schema_id": DECISION_SCHEMA, "schema_version": 1,
                "round_id": projection["accepted_post"]["round_id"],
                "post_primary_record_sha256": projection["accepted_post"]["primary_record_sha256"],
                "projection_sha256": projection["projection_sha256"]}
    if any(value.get(k) != v for k, v in expected.items()):
        raise ValueError("STRUCTURED_RECIPE_CURRENT_IDENTITY_MISMATCH")
    value["recipe"] = validate_recipe(value.get("recipe"), recipe_context(projection))
    return _seal(value, "decision_sha256")


def _order_manifest(rows, recipe, orders, ordering_domain):
    batch = recipe["micro_batch_size"] * recipe["gradient_accumulation_steps"]
    groups, flat_rows, flat_examples, flat_states = [], [], [], []
    for pass_index, order in enumerate(orders):
        for step_in_pass, start in enumerate(range(0, len(rows), batch), 1):
            ordinals = list(order[start:start + batch])
            selected = [rows[i] for i in ordinals]
            shas = [r["trainer_native_row_sha256"] for r in selected]
            examples = [r["source_example_sha256"] for r in selected]
            states = [r["source_state_sha256"] for r in selected]
            groups.append({"global_step": len(groups) + 1, "pass_index": pass_index, "step_in_pass": step_in_pass,
                           "ordinals": ordinals, "row_sha256s": shas, "source_identity_sha256s": examples,
                           "source_state_sha256s": states,
                           "target_loss_tokens": sum(r["tokenization"]["completion_loss_token_count"] for r in selected)})
            flat_rows.extend(shas); flat_examples.extend(examples); flat_states.extend(states)
    return {"schema_id": "ROUND_SAMPLE_ORDER_MANIFEST_V2", "schema_version": 2,
            "identity_domain": "SOURCE_EXAMPLE_SHA256", "row_count": len(rows), "dataset_passes": recipe["epochs"],
            "training_seed": recipe["training_seed"], "data_seed": recipe["data_seed"], "shuffle_during_training": False,
            "world_size": 1, "effective_batch_size": batch, "pass_orders": orders, "optimizer_groups": groups,
            "ordered_row_sha256s": flat_rows, "ordered_source_identity_sha256s": flat_examples,
            "ordered_source_state_sha256s": flat_states, "ordering_domain": ordering_domain}


def build_current_contract(*, native: NativeTraining, projection: dict, decision: dict):
    """Build the immutable scientific contract before mechanical initialization."""
    _verify_seal(projection, "projection_sha256")
    _verify_seal(decision, "decision_sha256")
    if accept_recipe_decision(decision, projection=projection) != decision:
        raise ValueError("RECIPE_DECISION_VALIDATOR_DRIFT")
    rows, manifest = _check_projection(native, projection)
    recipe, current = decision["recipe"], projection["current"]
    n, batch = len(rows), recipe["micro_batch_size"] * recipe["gradient_accumulation_steps"]
    total_tokens = sum(r["tokenization"]["completion_loss_token_count"] for r in rows)
    profile = "CURRENT_VERIFIED_STRATEGY_DUAL_VIEW_PROFILE_V1"
    contract = {"schema_id": "ROUND_LOCAL_TRAINING_CONTRACT_V2", "schema_version": 2,
        "round_id": projection["accepted_post"]["round_id"], "profile_id": profile,
        "condition_id": SEMANTICS, "diagnostic_only": False, "promotion_eligible": True,
        "training_execution_authorized": False, "training_execution_count": 0,
        "scientific_status": "PREREGISTERED_BEFORE_TRAINING_EXECUTION",
        "parent": copy.deepcopy(current["parent"]), "peft": copy.deepcopy(current["peft"]),
        "parent_compatibility_approval_token": "CURRENT_STRONG_POST_RECIPE:" + decision["decision_sha256"],
        "dataset": {**native.adapter.SUPPORTED_DATASET, "dataset_id": SEMANTICS,
            "path": projection["dataset_ref"]["path"], "sha256": projection["dataset_ref"]["sha256"],
            "manifest_path": projection["dataset_manifest_ref"]["path"], "manifest_file_sha256": projection["dataset_manifest_ref"]["sha256"],
            "manifest_domain_sha_field": projection["manifest_domain_sha_field"],
            "manifest_domain_sha256": manifest[projection["manifest_domain_sha_field"]],
            "research_planner_training_plan_domain_sha256": decision["decision_sha256"],
            "research_planner_training_plan_file_sha256": hashlib.sha256(canonical(decision)).hexdigest(),
            "row_count": n, "sequence_lengths": [len(r["tokenization"]["input_ids"]) for r in rows],
            "max_sequence_length": max(len(r["tokenization"]["input_ids"]) for r in rows),
            "one_pass_target_loss_token_count": total_tokens,
            "row_adapter": {"schema_id": native.dual.SCHEMA, "identity_domain": "SOURCE_EXAMPLE_SHA256", "source_identity_sha_field": "source_example_sha256"}},
        "budget": {k: recipe[k] for k in ("epochs", "micro_batch_size", "gradient_accumulation_steps", "training_seed", "data_seed")},
        "optimization": {**native.adapter.SUPPORTED_OPTIMIZATION, **{k: recipe[k] for k in ("learning_rate", "weight_decay", "max_grad_norm", "warmup_steps")},
                         "fresh_optimizer": True, "fresh_scheduler": True, "resume_from_checkpoint": False},
        "execution": {**copy.deepcopy(current["execution"]), "world_size": 1, "per_rank_micro_batch_size": recipe["micro_batch_size"], "distributed_backend": "none"},
        "output_contracts": {"adapter_artifact_manifest_relative_path": "adapter_artifact_manifest.json", "adapter_artifact_manifest_schema_id": "ROUND_TRAINING_ADAPTER_ARTIFACT_MANIFEST_V1",
            "formal_run_manifest_relative_path": "formal_run_manifest.json", "formal_run_manifest_schema_id": "ROUND_TRAINING_FORMAL_RUN_MANIFEST_V1",
            "training_step_ledger_relative_path": "training_step_ledger.jsonl", "training_step_ledger_schema_id": "ROUND_TRAINING_STEP_LEDGER_V1"}}
    contract["budget"].update(effective_batch_size=batch, partial_final_accumulation_group=False,
                              optimizer_steps=(n // batch) * recipe["epochs"], target_loss_token_budget=total_tokens * recipe["epochs"])
    if "clean_runtime" in current:
        contract["clean_runtime"] = copy.deepcopy(current["clean_runtime"])
    return contract, rows, manifest


def materialize_training_binding(*, native: NativeTraining, projection: dict, decision: dict,
                                 output_root: Path, build_training_orders: Callable | None = None) -> dict:
    """Produce current Generic V2 contract/order/binding/authorization; no execution.

    A caller may inject the already-imported native order builder. Otherwise the
    original frozen parent module is loaded and its build_training_orders used.
    """
    contract, rows, manifest = build_current_contract(native=native, projection=projection, decision=decision)
    recipe, current = decision["recipe"], projection["current"]
    root, n, profile = Path(output_root).resolve(), len(rows), contract["profile_id"]
    native.adapter.validate_runtime_capabilities(contract)
    parent_ref = contract["parent"]
    required_parent = (
        "policy_id", "adapter_path", "adapter_bundle_sha256", "final_trainable_parameter_sha256",
        "base_model_repository", "base_model_revision", "load_semantics", "formal_train_path", "formal_train_sha256",
        "adapter_artifact_manifest_path", "adapter_artifact_manifest_sha256",
        "base_model_artifact_manifest_path", "base_model_artifact_manifest_sha256",
    )
    clean_runtime = contract.get("clean_runtime")
    if clean_runtime is None:
        required_parent += ("training_config_path", "training_config_sha256")
    missing = [key for key in required_parent if not isinstance(parent_ref.get(key), str) or not parent_ref[key]]
    if missing:
        raise ValueError("CURRENT_PEFT_PARENT_BINDING_INCOMPLETE:" + ",".join(missing))
    expected_load = ("PEFT_LOAD_FRESH_SEEDED_STEP_ZERO_ADAPTER_IS_TRAINABLE_TRUE"
        if clean_runtime and not clean_runtime.get("accepted_parent_context")
        else "PEFT_FROM_PRETRAINED_IS_TRAINABLE_TRUE")
    if parent_ref["load_semantics"] != expected_load:
        raise ValueError("CURRENT_PARENT_LOAD_SEMANTICS_UNSUPPORTED_BY_NATIVE_PEFT_DELEGATE")
    # Preserve current parent identity: never borrow the Human-T2 adapter or its
    # diagnostic approval token to satisfy the existing PEFT continuation API.
    native.adapter._verify_parent_adapter_files(contract)
    for prefix in (("formal_train", "base_model_artifact_manifest") if clean_runtime else ("formal_train", "base_model_artifact_manifest", "training_config")):
        _read_ref({"path": parent_ref[prefix + "_path"], "sha256": parent_ref[prefix + "_sha256"]})
    for key, expected in {"checkpoint_rule": "FINAL_STEP_ONLY", "early_stopping": False, "within_training_evaluation": False, "intermediate_checkpoint_selection": False}.items():
        if contract["execution"].get(key) != expected:
            raise ValueError("FROZEN_TRAINING_EXECUTION_SEMANTIC_MISMATCH:" + key)
    if build_training_orders is None:
        parent_module = native.adapter._load_parent_module(contract)
        parent_module._ORDER_DOMAIN = current["ordering_domain"]
        build_training_orders = parent_module.build_training_orders
    orders = [list(x) for x in build_training_orders(example_count=n, seed=recipe["data_seed"], passes=recipe["epochs"])]
    if len(orders) != recipe["epochs"] or any(sorted(x) != list(range(n)) for x in orders):
        raise ValueError("NATIVE_ORDER_BUILDER_INVALID_PERMUTATION")
    order = _order_manifest(rows, recipe, orders, current["ordering_domain"])
    native.contracts.validate_training_contract(contract, order)
    common = native.common
    documents = {"CURRENT_TRAINING_INPUT_V1.json": projection, "CURRENT_STRONG_POST_TRAINING_RECIPE_V1.json": decision,
                 "ROUND_LOCAL_TRAINING_CONTRACT_V2.json": contract, "ROUND_SAMPLE_ORDER_MANIFEST_V2.json": order}
    def file_ref(name, schema_id):
        return {"path": name, "sha256": hashlib.sha256(canonical(documents[name])).hexdigest(), "schema_id": schema_id}
    role = {"schema_id": "ROUND_ROLE_BINDING_MANIFEST_V1", "schema_version": 1, "role_id": "TRAINER", "role_kind": "TRAINING_EXECUTOR",
            "round_id": contract["round_id"], "shadow_only": False, "implementation_kind": "DETERMINISTIC",
            "authority_profile_id": "EXECUTE_FROZEN_TRAINING_CONTRACT_ONLY", "visibility_profile_id": "TRAINING_ARTIFACTS_ONLY",
            "model_or_human_identity": "FROZEN_FORMAL_TRAIN_COMPAT_ADAPTER_V1", "checkpoint_or_adapter_sha256": current["parent"]["adapter_bundle_sha256"],
            "runtime_manifest_sha256": current["parent"]["formal_train_sha256"], "schema_bundle_sha256": file_ref("ROUND_LOCAL_TRAINING_CONTRACT_V2.json", contract["schema_id"])["sha256"], "prompt_bundle_sha256": None}
    documents["TRAINER_ROLE_BINDING_V1.json"] = role
    runtime_adapter_ref = {"path": str(native.dual_path), "sha256": native.source_sha256s[str(native.dual_path)], "schema_id": None}
    if clean_runtime:
        runtime_path = Path(__file__).with_name("clean_dual_runtime.py").resolve()
        runtime_adapter_ref = {"path": str(runtime_path), "sha256": clean_runtime["source_code_files"].get(str(runtime_path)), "schema_id": None}
        _read_ref(runtime_adapter_ref)
    binding = {"schema_id": "ROUND_TRAINING_STAGE_BINDING_V1", "schema_version": 1, "round_id": contract["round_id"],
               "round_index": current["round_index"], "profile_id": profile, "stage_id": "TRAINING_EXECUTION",
               "package_root_relative_to_binding": ".", "previous_stage_receipt_sha256": None,
               "training_contract_ref": file_ref("ROUND_LOCAL_TRAINING_CONTRACT_V2.json", contract["schema_id"]),
               "sample_order_ref": file_ref("ROUND_SAMPLE_ORDER_MANIFEST_V2.json", order["schema_id"]),
               "trainer_role_binding_ref": file_ref("TRAINER_ROLE_BINDING_V1.json", role["schema_id"]),
               "runtime_adapter_ref": runtime_adapter_ref,
               "upstream_artifact_refs": [{"logical_name": "CURRENT_STRONG_POST_RECIPE", "path": str(root / "CURRENT_STRONG_POST_TRAINING_RECIPE_V1.json"),
                   "sha256": file_ref("CURRENT_STRONG_POST_TRAINING_RECIPE_V1.json", DECISION_SCHEMA)["sha256"], "schema_id": DECISION_SCHEMA, "retention_class": "DECISION_ARTIFACT"}],
               "output_policy": {"require_direct_child": True, "require_basename_equals_execution_attempt_id": True,
                   "training_output_parent": current["output_parent"], "stage_attempt_parent": current["attempt_parent"]}}
    binding["stage_binding_sha256"] = common.domain_sha256(binding["schema_id"], binding, sha_field="stage_binding_sha256")
    attempt = current["execution_attempt_id"]
    if not isinstance(attempt, str) or not attempt or Path(attempt).name != attempt or attempt in (".", "..") or "/" in attempt or "\\" in attempt:
        raise ValueError("EXECUTION_ATTEMPT_BASENAME_INVALID")
    auth = {"schema_id": "ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1", "schema_version": 1, "authorization_status": "APPROVED",
            "round_id": contract["round_id"], "stage_id": binding["stage_id"], "profile_id": profile,
            "stage_binding_sha256": binding["stage_binding_sha256"], "runner_freeze_root_sha256": current["runner_freeze_root_sha256"],
            "authorized_optimizer_steps": contract["budget"]["optimizer_steps"], "authorized_target_loss_tokens": contract["budget"]["target_loss_token_budget"],
            "diagnostic_only": False, "promotion_eligible": True, "training_execution_count_before": 0,
            "execution_attempt_id": attempt, "authorized_output_dir": str(Path(current["output_parent"]).resolve() / attempt),
            "stage_attempt_root": str(Path(current["attempt_parent"]).resolve() / attempt), "source_post_recipe_sha256": decision["decision_sha256"]}
    auth["authorization_sha256"] = common.domain_sha256(auth["schema_id"], auth, sha_field="authorization_sha256")
    if Path(auth["authorized_output_dir"]).exists() or Path(auth["stage_attempt_root"]).exists():
        raise ValueError("TRAINING_ATTEMPT_ALREADY_EXISTS_NO_BLIND_RERUN")
    documents["ROUND_TRAINING_STAGE_BINDING_V1.json"] = binding
    documents["ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json"] = auth
    # Check every destination before any write. Reuse only exact same materialization.
    for name, value in documents.items():
        path = root / name
        if path.exists() and (path.is_symlink() or path.read_bytes() != canonical(value)):
            raise ValueError("EXISTING_MATERIALIZATION_CONFLICT:" + name)
    root.mkdir(parents=True, exist_ok=True)
    for name, value in documents.items():
        path = root / name
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(canonical(value))
    stage_path, auth_path = root / "ROUND_TRAINING_STAGE_BINDING_V1.json", root / "ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json"
    context = native.contracts.load_stage_context(stage_path)
    native.contracts.load_execution_authorization(auth_path, context=context, runner_freeze_root_sha256=current["runner_freeze_root_sha256"])
    return {"schema_id": "CURRENT_TRAINING_MATERIALIZATION_RESULT_V1", "round_id": contract["round_id"],
            "stage_binding_path": str(stage_path), "authorization_path": str(auth_path),
            "stage_binding_sha256": binding["stage_binding_sha256"], "authorization_sha256": auth["authorization_sha256"],
            "recipe_decision_sha256": decision["decision_sha256"], "training_execution_count": 0,
            "native_contract_validated": True, "optimizer_executed": False,
            "required_environment": {"PCHSI_FIXED_REPO_ROOT": str(native.root.parents[3])},
            "native_entrypoint": "round_training.stage_runner",
            "runner_freeze_root_sha256": current["runner_freeze_root_sha256"]}
