from __future__ import annotations
from copy import deepcopy
import importlib
import pytest
from pchsi.reference_loop.canonical import domain_hash


def _m():
    return importlib.import_module("pchsi.analyzer.outcome_router")


def _pack(*, success=False, protocol=False, incomplete=False, infra=False):
    generic = {
        "terminal_success": None if incomplete else success,
        "experiment_protocol_valid": not protocol,
        "environment_error_count": 1 if infra else 0,
    }
    pack = {
        "schema_id": "ANALYZER_EVIDENCE_PACK_V1",
        "schema_version": 1,
        "pack_role": "COMMON_EVIDENCE_IDENTICAL_ACROSS_A0_A1_A2_A3",
        "task_identity": {
            "task_id": "task-1",
            "task_type": "pick_and_place_simple",
            "gamefile_sha256": "b"*64,
        },
        "trajectory_identity": {"x": "y"},
        "trajectory": [{"model_call_index": 0, "admissible_commands": ["look"]}],
        "mechanical_evidence": {"generic_episode_facts": generic},
        "memory_support_port": {
            "base_pack_exposes_memory": False, "memory_packet": None
        },
        "analyzer_output_authority": {
            "benefit_harm_authority": False,
            "training_label_authority": False,
            "promotion_authority": False,
        },
        "requires_environment_verification": True,
        "evidence_pack_sha256": "0"*64,
    }
    pack["evidence_pack_sha256"] = domain_hash(
        "ANALYZER_EVIDENCE_PACK_V1",
        pack,
        excluded_field="evidence_pack_sha256",
    )
    return pack


def test_exact_precedence_preserves_all_incidents() -> None:
    m = _m()
    route = m.route_episode(_pack(protocol=True, incomplete=True, infra=True))
    assert route["route_status"] == "PROTOCOL_INVALID"
    assert route["incident_flags"] == {
        "protocol_invalid": True,
        "evidence_incomplete": True,
        "infrastructure_unavailable": True,
    }
    assert set(route["reason_codes"]) >= {
        "PROTOCOL_INVALID", "EVIDENCE_INCOMPLETE", "INFRASTRUCTURE_UNAVAILABLE"
    }
    assert route["trajectory_outcome"] is None


def test_route_is_derived_from_bound_pack_not_caller_booleans() -> None:
    m = _m()
    assert m.route_episode(_pack(success=True))["trajectory_outcome"] == "SUCCESS"
    failure = _pack(success=False)
    assert m.route_episode(failure)["trajectory_outcome"] == "FAILURE"
    tampered = deepcopy(failure)
    tampered["mechanical_evidence"]["generic_episode_facts"]["terminal_success"] = True
    with pytest.raises(ValueError, match="SHA"):
        m.route_episode(tampered)


def test_duplicate_registered_unit_is_rejected() -> None:
    m = _m()
    route = m.route_episode(_pack())
    with pytest.raises(ValueError, match="duplicate"):
        m.build_mechanical_census([route, route])


def test_route_information_boundary_is_machine_readable() -> None:
    route = _m().route_episode(_pack())
    assert route["scientific_use"] == "PRIVILEGED_OFFLINE_ANALYSIS"
    assert route["analysis_time_information_boundary"] == "POST_EPISODE_DEV_ONLY"
