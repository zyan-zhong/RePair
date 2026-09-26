from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.formal_x_lineage import (
    bind_selected_candidates_to_formal_x_v1,
    build_formal_x_indexes_v1,
    canonical_json_bytes,
    resolve_registered_path,
    validate_crosscheck_result_v1,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _crosscheck(
    *,
    target: str,
    disposition: str = "ACCEPT",
    current: bool = True,
) -> dict[str, object]:
    value = {
        "schema_id": "ANALYZER_CROSSCHECK_RESULT_V1",
        "schema_version": 1,
        "target_artifact_sha256": target,
        "disposition": disposition,
        "supporting_evidence_sha256s": [_sha("support:" + target)],
        "contradiction_evidence_sha256s": (
            [_sha("contradiction:" + target)]
            if disposition == "DOWNGRADE_SCOPE"
            else []
        ),
        "residual_case_ids": (
            ["residual-1"] if disposition == "DOWNGRADE_SCOPE" else []
        ),
        "current_evidence_sha256s": (
            [_sha("current:" + target)] if current else []
        ),
        "historical_evidence_sha256s": [_sha("history:" + target)],
        "crosscheck_sha256": "0" * 64,
    }
    value["crosscheck_sha256"] = domain_hash(
        "ANALYZER_CROSSCHECK_RESULT_V1",
        value,
        excluded_field="crosscheck_sha256",
    )
    return value


def _memory_pack(group: int) -> dict[str, object]:
    value = {
        "schema_id": "FAILURE_MEMORY_ROLE_PACK_V1",
        "schema_version": 1,
        "role": "ANALYZER",
        "cell_id": f"group-{group}",
        "execution_manifest_sha256": _sha(f"manifest:{group}"),
        "payload": {
            "schema_id": "ANALYZER_MEMORY_VIEW_V1",
            "snapshot_sha256": _sha(f"snapshot:{group}"),
            "candidates": [],
        },
        "pack_sha256": "0" * 64,
    }
    value["pack_sha256"] = domain_hash(
        "FAILURE_MEMORY_ROLE_PACK_V1",
        value,
        excluded_field="pack_sha256",
    )
    return value


def _fixture(tmp_path: Path) -> tuple[Path, list[dict[str, object]]]:
    root = tmp_path / "formal"
    root.mkdir()
    wrappers = []
    batch_rows = []
    registry_rows = []
    selected = []

    for state_index in range(30):
        state_sha = _sha(f"state:{state_index}")
        for condition_index, condition in enumerate(("A2", "A3")):
            candidate_index = state_index * 2 + condition_index
            group_index = state_index // 3
            group_sha = _sha(f"group:{condition}:{group_index}")
            proposal_sha = _sha(f"proposal:{candidate_index}")
            candidate_sha = _sha(f"candidate:{candidate_index}")
            g_custom = f"G_{condition}_{group_index}"
            x_custom = f"X_{condition}_{group_index}"
            disposition = (
                "DOWNGRADE_SCOPE"
                if condition == "A2" and group_index == 0
                else "ACCEPT"
            )
            candidate = {
                "schema_id": "ANALYZER_REPAIR_CANDIDATE_V1",
                "schema_version": 1,
                "candidate_kind": "FAILURE_REPAIR",
                "source_state_sha256": state_sha,
                "menu_sha256": _sha(f"menu:{state_index}"),
                "source_proposal_sha256": proposal_sha,
                "candidate_status": "EXECUTABLE_EXACT_ACTION",
                "exact_action": f"take object {candidate_index}",
                "option_actions": [],
                "termination_condition": None,
                "requires_environment_verification": True,
                "candidate_sha256": candidate_sha,
                "live_menu_revalidation_required": True,
                "all_intervention_actions_count_against_environment_budget": True,
            }
            wrapper = {
                "condition_id": condition,
                "g_custom_id": g_custom,
                "x_custom_id": x_custom,
                "group_manifest_sha256": group_sha,
                "source_proposal_sha256": proposal_sha,
                "source_state_sha256": state_sha,
                "projection_status": "SELECTED",
                "proposal_index": candidate_index,
                "x_available_and_valid": True,
                "x_disposition": disposition,
                "candidate": candidate,
            }
            wrappers.append(wrapper)
            selected.append(
                {
                    "condition_id": condition,
                    "candidate_sha256": candidate_sha,
                    "source_state_sha256": state_sha,
                    "source_proposal_sha256": proposal_sha,
                }
            )

            # Only one G/X execution exists per condition/group, even though
            # three source candidates share it.
            if any(row["custom_id"] == x_custom for row in batch_rows):
                continue

            group_result = {
                "schema_id": "ANALYZER_GROUP_RESULT_V2",
                "schema_version": 2,
                "group_id": f"group-{condition}-{group_index}",
                "group_manifest_sha256": group_sha,
                "mechanism_hypotheses": [],
                "source_conditioned_proposals": [],
                "group_result_sha256": "0" * 64,
            }
            group_result["group_result_sha256"] = domain_hash(
                "ANALYZER_GROUP_RESULT_V2",
                group_result,
                excluded_field="group_result_sha256",
            )
            g_path = root / "g" / f"{g_custom}.json"
            g_file_sha = _write(g_path, group_result)

            crosscheck = _crosscheck(
                target=str(group_result["group_result_sha256"]),
                disposition=disposition,
            )
            x_path = root / "x" / f"{x_custom}.json"
            x_file_sha = _write(x_path, crosscheck)

            pack = _memory_pack(group_index) if condition == "A3" else None
            projection = {
                "schema_id": "ANALYZER_GROUP_RUNTIME_PROJECTION_V1",
                "condition_id": condition,
                "group_manifest_sha256": group_sha,
                "memory_pack_sha256": pack["pack_sha256"] if pack else None,
                "memory_pack": pack,
            }
            projection_path = root / "projection" / f"{x_custom}.json"
            _write(projection_path, projection)

            batch_rows.extend(
                [
                    {
                        "schema_id": "FORMAL_BATCH_UNIT_RESULT_V1",
                        "custom_id": g_custom,
                        "condition_id": condition,
                        "stage_id": "G-" + condition,
                        "target_custom_id": None,
                        "group_manifest_sha256": group_sha,
                        "status": "VALIDATED",
                        "validated_artifact_path": str(g_path),
                        "validated_artifact_file_sha256": g_file_sha,
                        "validated_semantic_sha256": group_result[
                            "group_result_sha256"
                        ],
                    },
                    {
                        "schema_id": "FORMAL_BATCH_UNIT_RESULT_V1",
                        "custom_id": x_custom,
                        "condition_id": condition,
                        "stage_id": "X",
                        "target_custom_id": g_custom,
                        "group_manifest_sha256": group_sha,
                        "status": "VALIDATED",
                        "validated_artifact_path": str(x_path),
                        "validated_artifact_file_sha256": x_file_sha,
                        "validated_semantic_sha256": crosscheck[
                            "crosscheck_sha256"
                        ],
                    },
                ]
            )
            registry_rows.append(
                {
                    "custom_id": x_custom,
                    "condition_id": condition,
                    "stage_id": "X",
                    "target_custom_id": g_custom,
                    "group_manifest_sha256": group_sha,
                    "projection_path": str(projection_path),
                    "expected_memory_pack_sha256": (
                        pack["pack_sha256"] if pack else None
                    ),
                }
            )

    _write(root / "candidate_pool.json", {"wrappers": wrappers})
    _write(root / "batch_results.json", {"results": batch_rows})
    _write(root / "x_registry.json", {"rows": registry_rows})
    return root, selected


def test_shared_group_condition_x_units_bind_all_60_candidates(tmp_path: Path) -> None:
    root, selected = _fixture(tmp_path)
    indexes = build_formal_x_indexes_v1(root)
    result = bind_selected_candidates_to_formal_x_v1(
        selected_candidates=selected,
        indexes=indexes,
        allowed_artifact_roots=[root],
    )["authority"]

    assert result["candidate_binding_count"] == 60
    assert result["condition_counts"] == {"A2": 30, "A3": 30}
    assert result["unique_x_scientific_unit_count"] == 20
    assert result["x_candidate_multiplicity_distribution"] == {"3": 20}
    assert result["candidate_disposition_counts"] == {
        "ACCEPT": 57,
        "DOWNGRADE_SCOPE": 3,
    }
    assert result["a2_candidate_memory_binding_count"] == 0
    assert result["a3_candidate_memory_binding_count"] == 30
    assert result["unique_a3_analyzer_memory_pack_count"] == 10


def test_rejects_x_target_that_is_not_validated_g_result(tmp_path: Path) -> None:
    value = _crosscheck(target=_sha("G"))
    value["target_artifact_sha256"] = _sha("wrong")
    value["crosscheck_sha256"] = domain_hash(
        "ANALYZER_CROSSCHECK_RESULT_V1",
        value,
        excluded_field="crosscheck_sha256",
    )
    with pytest.raises(ValueError, match="target artifact"):
        validate_crosscheck_result_v1(
            value,
            expected_target_artifact_sha256=_sha("G"),
            expected_disposition="ACCEPT",
            expected_semantic_sha256=str(value["crosscheck_sha256"]),
        )


def test_rejects_projector_and_x_disposition_mismatch() -> None:
    value = _crosscheck(target=_sha("G"), disposition="ACCEPT")
    with pytest.raises(ValueError, match="disposition mismatch"):
        validate_crosscheck_result_v1(
            value,
            expected_target_artifact_sha256=_sha("G"),
            expected_disposition="DOWNGRADE_SCOPE",
            expected_semantic_sha256=str(value["crosscheck_sha256"]),
        )


def test_historical_only_evidence_cannot_accept() -> None:
    value = _crosscheck(target=_sha("G"), current=False)
    with pytest.raises(ValueError, match="historical-only"):
        validate_crosscheck_result_v1(
            value,
            expected_target_artifact_sha256=_sha("G"),
            expected_disposition="ACCEPT",
            expected_semantic_sha256=str(value["crosscheck_sha256"]),
        )


def test_registered_path_cannot_escape_allowed_roots(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one allowed file"):
        resolve_registered_path(
            str(outside),
            allowed_roots=[root],
        )

def _minimal_x_registry_row(
    *,
    custom_id: str,
    condition: str = "A2",
    target_custom_id: str = "G_A2_0",
    group_manifest_sha256: str | None = None,
    projection_path: str = "/tmp/projection-a.json",
) -> dict[str, object]:
    return {
        "stage_id": "X",
        "custom_id": custom_id,
        "condition_id": condition,
        "target_custom_id": target_custom_id,
        "group_manifest_sha256": (
            group_manifest_sha256
            if group_manifest_sha256 is not None
            else _sha("group")
        ),
        "projection_path": projection_path,
        "expected_memory_pack_sha256": (
            None if condition == "A2" else _sha("memory")
        ),
    }


def test_same_x_scientific_identity_allows_different_registry_wrappers(
    tmp_path: Path,
) -> None:
    root = tmp_path / "formal"
    root.mkdir()
    custom_id = "X_A2_00_shared"
    base = _minimal_x_registry_row(custom_id=custom_id)
    richer = dict(base)
    richer.update(
        {
            "projection_path": "/tmp/projection-b.json",
            "request_body_sha256": _sha("request"),
            "prompt_sha256": _sha("prompt"),
            "container_note": "SECOND_REGISTERED_REPRESENTATION",
        }
    )
    _write(root / "registry_a.json", {"rows": [base]})
    _write(root / "registry_b.json", {"rows": [richer]})

    indexes = build_formal_x_indexes_v1(root)

    merged, sources = indexes.x_registry_rows[custom_id]
    assert merged["custom_id"] == custom_id
    assert merged["target_custom_id"] == "G_A2_0"
    assert len(sources) == 2
    assert len(indexes.x_registry_representations[custom_id]) == 2


def test_same_x_custom_id_rejects_conflicting_scientific_identity(
    tmp_path: Path,
) -> None:
    root = tmp_path / "formal"
    root.mkdir()
    custom_id = "X_A2_00_conflict"
    first = _minimal_x_registry_row(custom_id=custom_id)
    second = dict(first)
    second["target_custom_id"] = "G_A2_DIFFERENT"
    second["projection_path"] = "/tmp/projection-b.json"
    _write(root / "registry_a.json", {"rows": [first]})
    _write(root / "registry_b.json", {"rows": [second]})

    with pytest.raises(ValueError, match="scientific identity conflict"):
        build_formal_x_indexes_v1(root)


def test_x_registry_representation_audit_preserves_all_sources(
    tmp_path: Path,
) -> None:
    root = tmp_path / "formal"
    root.mkdir()
    custom_id = "X_A2_00_audit"
    first = _minimal_x_registry_row(custom_id=custom_id)
    second = dict(first)
    second["projection_path"] = "/tmp/projection-copy.json"
    second["request_body_sha256"] = _sha("request")
    _write(root / "registry_a.json", {"rows": [first]})
    _write(root / "registry_b.json", {"rows": [second]})

    indexes = build_formal_x_indexes_v1(root)
    from pchsi.research_intelligence.formal_x_lineage import (
        x_registry_representation_audit_v1,
    )

    audit = x_registry_representation_audit_v1(indexes)
    assert audit["recognized_representation_count"] == 2
    assert audit["unique_custom_id_count"] == 1
    assert audit["duplicate_custom_id_count"] == 1
    row = audit["rows"][0]
    assert row["custom_id"] == custom_id
    assert row["representation_count"] == 2
    assert len(row["representation_object_sha256s"]) == 2
    assert len(row["source_records"]) == 2
