"""Software fixtures only: no provider, optimizer, environment or science results."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

WORK = Path(__file__).resolve().parents[3]
GENERIC = WORK / "v17/native_bba_full/scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build"
DUAL = WORK / "v16/reference/STRONG_PRIMARY_AUTONOMOUS_CAMPAIGN_DRIVER_V1_11_0/dual_view_training_adapter.py"
sys.path.insert(0, str(WORK / "v17"))


def _module():
    path = WORK / "v17/training_binding/materializer.py"
    assert path.is_file(), "current-round structured recipe materializer is not implemented"
    from training_binding import materializer
    return materializer


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _native():
    m = _module()
    paths = [GENERIC / "round_training" / x for x in (
        "__init__.py", "common.py", "contracts.py", "receipts.py", "stage_runner.py",
        "adapters/frozen_formal_train_peft.py",
    )] + [DUAL]
    return m.NativeTraining.load(GENERIC, DUAL, {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


def _fixture(tmp_path):
    m = _module()
    native = _native()
    rows = []
    for ordinal, view in enumerate(("I1_EXECUTION_ACTION", "STRATEGY_AUXILIARY")):
        rows.append({
            "schema_id": "POLICY_STRATEGY_DUAL_VIEW_NATIVE_ROW_V1", "schema_version": 1,
            "ordinal": ordinal, "view_kind": view,
            "source_identity": {"source_state_sha256": "a" * 64, "source_example_sha256": str(ordinal + 1) * 64},
            "trainer_native_row_sha256": str(ordinal + 3) * 64,
            "tokenization": {"input_ids": [1, 2, 3], "labels": [-100, 2, 3], "completion_loss_token_count": 2},
            "deployment_i1_execution_view": ordinal == 0, "training_auxiliary_strategy_view": ordinal == 1,
            "promotion_eligible": False,
        })
    dataset = tmp_path / "rows.jsonl"
    dataset.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
    dataset_ref = {"path": str(dataset), "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest()}
    manifest = {"schema_id": "SYNTHETIC_STAGE6AN_MANIFEST", "manifest_sha256": "e" * 64, "dataset_sha256": dataset_ref["sha256"]}
    manifest_ref = _write(tmp_path / "manifest.json", manifest)
    post = {"round_id": "synthetic-round", "researcher_training_recommendation": "TRAIN", "primary_record_sha256": "b" * 64,
            "primary_pre_record_sha256": "c" * 64, "environment_result_package_sha256": "d" * 64}
    handoff = {"schema_id": "CURRENT_VERIFIED_TRAINING_HANDOFF_V1", "schema_version": 1,
               "round_id": post["round_id"], "parent_policy_id": "synthetic-parent", "plan_sha256": "f" * 64,
               "source_pre_primary_record_sha256": "c" * 64, "post_primary_record_sha256": "b" * 64,
               "environment_result_package_sha256": "d" * 64, "verified_benefit_state_count": 1,
               "verified_benefit_state_results": [{"source_state_sha256": "a" * 64, "stable_effect": "BENEFIT"}],
               "strategy_materialization_pending": True, "training_execution_authorized": False, "training_execution_count": 0}
    handoff["handoff_sha256"] = hashlib.sha256(m.canonical(handoff) + b"\n").hexdigest()
    census = {k: 2 for k in ("STRATEGY_TARGET_TOKEN_COUNT", "STRATEGY_LOSS_BEARING_TOKEN_COUNT", "ACTION_TARGET_TOKEN_COUNT", "ACTION_LOSS_BEARING_TOKEN_COUNT", "PROMPT_MASKED_TOKEN_COUNT")}
    census.update(STRATEGY_ROW_COUNT=1, VERIFIED_BENEFIT_ROW_COUNT=1, TOTAL_LOSS_BEARING_TOKEN_COUNT=4, ACTION_ONLY_STRATEGY_ROW_COUNT=0, NON_VERIFIED_STRATEGY_ROW_COUNT=0)
    adapter_root = tmp_path / "adapter"
    adapter_root.mkdir()
    adapter_config = {"peft_type": "LORA", "task_type": "CAUSAL_LM", "r": 2, "lora_alpha": 2,
                      "lora_dropout": 0.0, "bias": "none", "target_modules": ["q_proj"],
                      "base_model_name_or_path": "synthetic/synthetic-revision"}
    _write(adapter_root / "adapter_config.json", adapter_config)
    (adapter_root / "adapter_model.safetensors").write_bytes(b"SYNTHETIC SOFTWARE FIXTURE, NOT A MODEL")
    files = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size_bytes": p.stat().st_size} for p in adapter_root.iterdir()}
    parent_manifest = _write(tmp_path / "parent_manifest.json", {"adapter_bundle_sha256": "a" * 64, "files": files})
    source = tmp_path / "formal_train.py"
    source.write_text("def build_training_orders(*, example_count, seed, passes):\n    return tuple(tuple(range(example_count)) for _ in range(passes))\n", encoding="utf-8")
    training_config = _write(tmp_path / "parent_training_config.json", {"synthetic": True})
    base_manifest = _write(tmp_path / "base_manifest.json", {"synthetic": True})
    parent = {"policy_id": "synthetic-parent", "policy_training_seed": 7, "adapter_bundle_sha256": "a" * 64,
              "final_trainable_parameter_sha256": "b" * 64, "formal_train_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "formal_train_path": str(source), "adapter_path": str(adapter_root),
              "adapter_artifact_manifest_path": parent_manifest["path"], "adapter_artifact_manifest_sha256": parent_manifest["sha256"],
              "base_model_artifact_manifest_path": base_manifest["path"], "base_model_artifact_manifest_sha256": base_manifest["sha256"],
              "training_config_path": training_config["path"], "training_config_sha256": training_config["sha256"],
              "base_model_repository": "SYNTHETIC", "base_model_revision": "synthetic-revision",
              "load_semantics": "PEFT_FROM_PRETRAINED_IS_TRAINABLE_TRUE"}
    context = {"round_index": 0, "parent": parent,
               "peft": {**native.adapter.SUPPORTED_PEFT, "r": 2, "lora_alpha": 2, "lora_dropout": 0.0, "target_modules": ["q_proj"]},
               "execution": {**native.adapter.SUPPORTED_EXECUTION, "checkpoint_rule": "FINAL_STEP_ONLY", "early_stopping": False, "within_training_evaluation": False, "intermediate_checkpoint_selection": False, "infrastructure_node_exclusions": [], "ambient_environment_variables_forbidden": []},
               "training_seed": 7, "data_seed": 7, "ordering_domain": "SYNTHETIC_TEST_ONLY", "runner_freeze_root_sha256": "f" * 64,
               "output_parent": str(tmp_path / "training"), "attempt_parent": str(tmp_path / "attempts"), "execution_attempt_id": "attempt-0",
               "current_parent_binding_sha256": "c" * 64}
    projection = m.build_recipe_projection(native=native, accepted_post=post, handoff=handoff,
        dataset_ref=dataset_ref, dataset_manifest_ref=manifest_ref, manifest_domain_sha_field="manifest_sha256",
        census=census, current=context, validate_accepted_post=lambda x: copy.deepcopy(x))
    recipe = {"epochs": 2, "micro_batch_size": 1, "gradient_accumulation_steps": 2,
              "learning_rate": 0.00003, "weight_decay": 0.01, "max_grad_norm": 1.0, "warmup_steps": 0,
              "training_seed": 7, "data_seed": 7, "dataset_sha256": dataset_ref["sha256"],
              "data_semantics": "VERIFIED_BENEFIT_DUAL_VIEW_COMPLETE_PAIRS", "rationale": "Synthetic software fixture only."}
    raw = m.build_recipe_receipt(recipe=recipe, context=m.recipe_context(projection), accepted_post=post,
        logical_call_id="synthetic-one-post", raw_response_sha256="e" * 64, logical_call_status="ACCEPTED")
    decision = m.accept_recipe_decision(raw, projection=projection)
    return m, native, projection, decision


def test_materializer_is_present():
    _module()


def test_current_recipe_builds_native_contract_and_separate_authorization(tmp_path):
    m, native, projection, decision = _fixture(tmp_path)
    result = m.materialize_training_binding(native=native, projection=projection, decision=decision,
        output_root=tmp_path / "binding", build_training_orders=lambda **k: tuple(tuple(range(k["example_count"])) for _ in range(k["passes"])))
    context = native.contracts.load_stage_context(Path(result["stage_binding_path"]))
    auth = native.contracts.load_execution_authorization(Path(result["authorization_path"]), context=context, runner_freeze_root_sha256="f" * 64)
    assert context.training_contract["schema_id"] == "ROUND_LOCAL_TRAINING_CONTRACT_V2"
    assert context.training_contract["budget"]["optimizer_steps"] == 2
    assert context.training_contract["budget"]["target_loss_token_budget"] == 8
    assert context.training_contract["optimization"]["learning_rate"] == 0.00003
    assert context.training_contract["training_execution_authorized"] is False
    assert auth["authorization_status"] == "APPROVED"
    assert context.training_contract["diagnostic_only"] is False
    assert context.training_contract["promotion_eligible"] is True
    assert result["training_execution_count"] == 0
    # Real legacy runtime order validation also sees truthful repeated source states.
    class Parent:
        build_training_orders = staticmethod(lambda **k: tuple(tuple(range(k["example_count"])) for _ in range(k["passes"])))
    records = native.dual.load_dual_view_records(Path(projection["dataset_ref"]["path"]))
    native.adapter._verify_order(Parent, records=records, contract=context.training_contract, sample_order=context.sample_order)


@pytest.mark.parametrize("change", ["no_train", "foreign_post", "zero_benefit", "wrong_parent", "bad_handoff_hash", "census_not_positive"])
def test_fails_closed_before_files_for_ineligible_input(tmp_path, change):
    m, native, projection, decision = _fixture(tmp_path)
    broken = copy.deepcopy(projection)
    if change == "no_train": broken["accepted_post"]["researcher_training_recommendation"] = "NO_TRAIN"
    if change == "foreign_post": broken["accepted_post"]["primary_record_sha256"] = "e" * 64
    if change == "zero_benefit": broken["handoff"]["verified_benefit_state_count"] = 0
    if change == "wrong_parent": broken["current"]["parent"]["policy_id"] = "other"
    if change == "bad_handoff_hash": broken["handoff"]["handoff_sha256"] = "0" * 64
    if change == "census_not_positive": broken["census"]["STRATEGY_LOSS_BEARING_TOKEN_COUNT"] = 0
    with pytest.raises((ValueError, RuntimeError)):
        m.materialize_training_binding(native=native, projection=broken, decision=decision,
            output_root=tmp_path / "rejected", build_training_orders=lambda **k: ())
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("field,value", [("epochs", 0), ("epochs", True), ("learning_rate", -1), ("training_seed", 17), ("data_semantics", "ACTION_ONLY"), ("dataset_sha256", "0" * 64)])
def test_recipe_schema_rejects_bad_or_unbound_choices(tmp_path, field, value):
    m, native, projection, decision = _fixture(tmp_path)
    recipe = dict(decision["recipe"], **{field: value})
    with pytest.raises(ValueError): m.validate_recipe(recipe, m.recipe_context(projection))


def test_old_dataset_injection_and_source_integrity_fail(tmp_path):
    m, native, projection, decision = _fixture(tmp_path)
    Path(projection["dataset_ref"]["path"]).write_text("{}\n")
    with pytest.raises((ValueError, RuntimeError)):
        m.materialize_training_binding(native=native, projection=projection, decision=decision,
            output_root=tmp_path / "rejected", build_training_orders=lambda **k: ())
    assert not (tmp_path / "rejected").exists()


def test_recipe_has_no_numeric_fallback(tmp_path):
    m, _, projection, decision = _fixture(tmp_path)
    recipe = dict(decision["recipe"])
    del recipe["epochs"]
    with pytest.raises(ValueError): m.validate_recipe(recipe, m.recipe_context(projection))


def test_no_train_needs_no_future_training_inputs():
    m = _module()
    post = {"round_id": "synthetic-no-train", "primary_record_sha256": "a" * 64, "researcher_training_recommendation": "NO_TRAIN"}
    receipt = m.build_recipe_receipt(recipe=None, context=None, accepted_post=post, logical_call_id="no-train",
        raw_response_sha256="b" * 64, logical_call_status="ACCEPTED")
    assert receipt["recipe"] is None
    assert receipt["training_execution_authorized"] is False
    assert receipt["training_execution_count"] == 0


def test_strong_supplies_seeds_when_no_current_constraint(tmp_path):
    m, _, projection, decision = _fixture(tmp_path)
    ctx = m.recipe_context(projection)
    del ctx["training_seed"]
    del ctx["data_seed"]
    recipe = dict(decision["recipe"], training_seed=123, data_seed=123)
    assert m.validate_recipe(recipe, ctx) == recipe


def test_typed_decision_without_same_post_receipt_is_rejected(tmp_path):
    m, _, projection, decision = _fixture(tmp_path)
    del decision["same_call_recipe_receipt"]
    decision = m._seal(decision, "decision_sha256")
    with pytest.raises(ValueError, match="SAME_ACCEPTED_POST_CALL"):
        m.accept_recipe_decision(decision, projection=projection)


def test_current_parent_without_existing_adapter_is_not_t2_upgraded(tmp_path):
    m, native, projection, decision = _fixture(tmp_path)
    del projection["current"]["parent"]["adapter_path"]
    projection = m._seal(projection, "projection_sha256")
    decision = m.accept_recipe_decision(decision["same_call_recipe_receipt"], projection=projection)
    with pytest.raises(ValueError, match="CURRENT_PEFT_PARENT_BINDING_INCOMPLETE"):
        m.materialize_training_binding(native=native, projection=projection, decision=decision, output_root=tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_native_parent_order_source_and_idempotent_materialization(tmp_path):
    m, native, projection, decision = _fixture(tmp_path)
    first = m.materialize_training_binding(native=native, projection=projection, decision=decision, output_root=tmp_path / "bound")
    second = m.materialize_training_binding(native=native, projection=projection, decision=decision, output_root=tmp_path / "bound")
    assert first == second
    Path(projection["current"]["attempt_parent"]).mkdir()
    (Path(projection["current"]["attempt_parent"]) / projection["current"]["execution_attempt_id"]).mkdir()
    with pytest.raises(ValueError, match="NO_BLIND_RERUN"):
        m.materialize_training_binding(native=native, projection=projection, decision=decision, output_root=tmp_path / "bound")


def test_single_post_schema_extension_does_not_mutate_native_schema(tmp_path):
    m, _, projection, _ = _fixture(tmp_path)
    base = {"type": "object", "additionalProperties": False, "properties": {"researcher_training_recommendation": {"enum": ["TRAIN", "NO_TRAIN"]}}, "required": ["researcher_training_recommendation"]}
    original = copy.deepcopy(base)
    extended = m.extend_post_schema(base, m.recipe_context(projection))
    assert base == original
    assert "training_recipe" in extended["required"]
    assert extended["properties"]["training_recipe"]["anyOf"][1] == {"type": "null"}


def test_native_remainder_and_same_call_status_checked(tmp_path):
    m, _, projection, decision = _fixture(tmp_path)
    recipe = dict(decision["recipe"], gradient_accumulation_steps=3)
    with pytest.raises(ValueError, match="NATIVE_GENERIC_V2_REMAINDER_UNSUPPORTED"):
        m.validate_recipe(recipe, m.recipe_context(projection))
    with pytest.raises(ValueError, match="ACCEPTED_LOGICAL_CALL"):
        m.build_recipe_receipt(recipe=decision["recipe"], context=m.recipe_context(projection), accepted_post=projection["accepted_post"],
            logical_call_id="fixture", raw_response_sha256="a" * 64, logical_call_status="STARTED")


def test_real_native_singleton_collator_and_matched_seed_boundaries(tmp_path):
    m, _, projection, decision = _fixture(tmp_path)
    with pytest.raises(ValueError, match="STRUCTURED_TRAINING_RECIPE_INVALID"):
        m.validate_recipe(dict(decision["recipe"], micro_batch_size=2, gradient_accumulation_steps=1), m.recipe_context(projection))
    ctx = {k: v for k, v in m.recipe_context(projection).items() if k not in ("training_seed", "data_seed")}
    with pytest.raises(ValueError, match="NATIVE_FORMAL_MATCHED_SEEDS_REQUIRED"):
        m.validate_recipe(dict(decision["recipe"], training_seed=1, data_seed=2), ctx)
