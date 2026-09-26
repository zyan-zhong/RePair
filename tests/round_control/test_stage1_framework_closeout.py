from __future__ import annotations

import ast
import json
from pathlib import Path

from pchsi.round_control.concrete_bindings import (
    BindingKindV1,
    binding_map,
    build_concrete_component_bindings,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT
    / "docs/stage1/STAGE1_ACTUAL_RUNNER_PORT_ADJUDICATION_V1.json"
)


def _function_parameters(path: Path, function_name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                return [
                    argument.arg
                    for argument in (
                        list(node.args.posonlyargs)
                        + list(node.args.args)
                        + list(node.args.kwonlyargs)
                    )
                ]
    raise AssertionError(
        f"function {function_name!r} missing from {path}"
    )


def _manifest() -> dict[str, object]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert value["schema_id"] == "STAGE1_ACTUAL_RUNNER_PORT_ADJUDICATION_V1"
    return value


def test_stage1_closeout_has_exact_four_lane_adjudication() -> None:
    value = _manifest()
    assert set(value["lanes"]) == {
        "GENERIC_TRAINING",
        "SELECT_EVALUATION",
        "SAME_STATE_F0F1",
        "ROLE_INVOCATION",
    }
    assert value["framework_unresolved_runner_port_count"] == 0
    assert value["live_adapter_deferred_count"] == 2
    assert value["scientific_execution_authorized"] is False
    assert value["next_gate"] == (
        "CLEAN_TRAIN_ONLY_HUMAN_REFERENCE_ROUND_BOOTSTRAP"
    )


def test_generic_training_adjudication_matches_actual_stage_runner() -> None:
    value = _manifest()
    lane = value["lanes"]["GENERIC_TRAINING"]
    source = REPO_ROOT / lane["source_path"]
    parameters = _function_parameters(source, lane["callable"])

    assert lane["disposition"] == "FROZEN_ACTUAL_RUNNER"
    assert parameters == lane["required_parameters"]

    bindings = binding_map(
        build_concrete_component_bindings(REPO_ROOT)
    )
    binding = bindings["GENERIC_TRAINING_STAGE_V2_1"]
    assert binding.binding_kind is BindingKindV1.ENGINEERING_SNAPSHOT
    assert lane["source_path"] in binding.source_paths


def test_select_adjudication_matches_actual_episode_evaluator() -> None:
    value = _manifest()
    lane = value["lanes"]["SELECT_EVALUATION"]
    source = REPO_ROOT / lane["source_path"]
    parameters = _function_parameters(source, lane["callable"])

    assert lane["disposition"] == "FROZEN_ACTUAL_RUNNER"
    assert parameters == lane["required_parameters"]

    bindings = binding_map(
        build_concrete_component_bindings(REPO_ROOT)
    )
    binding = bindings["SELECT_EVALUATOR"]
    assert binding.binding_kind is BindingKindV1.REPO_NATIVE
    assert lane["source_path"] in binding.source_paths


def test_f0f1_is_intentionally_a_port_not_a_historical_runner() -> None:
    value = _manifest()
    lane = value["lanes"]["SAME_STATE_F0F1"]
    assert lane["disposition"] == (
        "FROZEN_PORT_CONTRACT_LIVE_ADAPTER_DEFERRED"
    )

    bindings = binding_map(
        build_concrete_component_bindings(REPO_ROOT)
    )
    binding = bindings["SAME_STATE_F0F1"]
    assert binding.binding_kind is BindingKindV1.PORT_CONTRACT
    assert set(lane["source_paths"]) == set(binding.source_paths)
    assert lane["live_adapter_gate"] == (
        "CLEAN_TRAIN_ONLY_HUMAN_REFERENCE_ROUND_BOOTSTRAP"
    )


def test_role_invocation_keeps_role_contract_and_defers_actor_adapter() -> None:
    value = _manifest()
    lane = value["lanes"]["ROLE_INVOCATION"]
    assert lane["disposition"] == (
        "FROZEN_ROLE_CONTRACT_ACTOR_ADAPTER_DEFERRED"
    )
    assert lane["actor_adapter_gate"] == (
        "CLEAN_TRAIN_ONLY_HUMAN_REFERENCE_ROUND_BOOTSTRAP"
    )

    bindings = binding_map(
        build_concrete_component_bindings(REPO_ROOT)
    )
    planner = bindings["RESEARCH_PLANNER_PRE_POST"]
    assert planner.binding_kind is BindingKindV1.REPO_NATIVE
    for relative in planner.source_paths:
        assert relative in lane["source_paths"]
