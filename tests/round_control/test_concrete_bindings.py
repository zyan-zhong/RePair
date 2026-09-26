from pathlib import Path

from pchsi.round_control.bindings import (
    REQUIRED_REUSE_COMPONENT_IDS,
)
from pchsi.round_control.concrete_bindings import (
    BindingKindV1,
    binding_map,
    build_concrete_component_bindings,
    required_concrete_component_ids,
)
from pchsi.round_control.orchestrator import _ROUTING


AUTO_NEXT = "AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION"


def test_concrete_registry_extends_existing_stage1_reuse_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bindings = build_concrete_component_bindings(repo_root)
    observed = binding_map(bindings)

    required = set(REQUIRED_REUSE_COMPONENT_IDS) | {
        AUTO_NEXT,
    }

    assert set(required_concrete_component_ids()) == required
    assert set(observed) == required
    assert all(
        binding.scientific_execution_authorized is False
        for binding in bindings
    )


def test_every_orchestrator_action_has_a_concrete_binding() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    observed = binding_map(
        build_concrete_component_bindings(repo_root)
    )

    action_ids = {
        component_id
        for components, _next_stage in _ROUTING.values()
        for component_id in components
    }

    assert action_ids <= set(observed)


def test_external_runtime_assets_are_bound_not_reimplemented() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    observed = binding_map(
        build_concrete_component_bindings(repo_root)
    )

    assert observed["SCHEMA_AWARE_RENDERER"].binding_kind is (
        BindingKindV1.ENGINEERING_SNAPSHOT
    )
    assert observed["GENERIC_TRAINING_STAGE_V2_1"].entrypoint == (
        "round_training.stage_runner"
    )
    assert observed["SAME_STATE_F0F1"].binding_kind is (
        BindingKindV1.PORT_CONTRACT
    )
    assert observed["SAME_STATE_F0F1"].adapter_required is True
