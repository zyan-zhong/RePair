"""Approved π1 identity + historical rebinding + Analyzer-pack materialization."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .analyzer_evidence_pack import write_analyzer_evidence_pack
from .bundle_reader import validate_attempt_bundle
from .canonical import (
    canonical_json_bytes,
    domain_hash,
    ensure_regular_no_symlink,
    sha256_file,
    strict_json_loads,
    write_new_json,
    write_new_text,
)
from .historical_rebinding import (
    write_historical_trajectory_rebinding_manifest,
)
from .identity import (
    build_registration_payload,
    materialize_pi1_reference_identity_file,
)
from .task_access import revalidate_task_access_file


APPROVAL_TOKEN = "PI1_IDENTITY_REGISTRATION_APPROVED_REFERENCE_LOOP_V1"


def _load_object(path: Path) -> dict[str, object]:
    source = ensure_regular_no_symlink(path, name=path.name)
    value = strict_json_loads(source.read_bytes())
    if not isinstance(value, dict):
        raise TypeError(f"{path.name} must be an object")
    return value


def _selected_candidate(
    review: dict[str, object],
    approval: dict[str, object],
    *,
    slot: str,
) -> dict[str, object]:
    review_slots = review.get("artifact_slots")
    selections = approval.get("artifact_selections")
    if not isinstance(review_slots, dict) or not isinstance(selections, dict):
        raise TypeError("artifact review/approval maps missing")
    item = review_slots.get(slot)
    selected_id = selections.get(slot)
    if not isinstance(item, dict) or not isinstance(selected_id, str):
        raise ValueError(f"missing approval for artifact slot {slot}")
    candidates = item.get("candidates")
    if not isinstance(candidates, list):
        raise TypeError(f"artifact candidates missing for {slot}")
    matches = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("candidate_id") == selected_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"approved candidate for {slot} is not uniquely present in review"
        )
    return matches[0]


def _selected_scalar(
    review: dict[str, object],
    approval: dict[str, object],
    *,
    slot: str,
) -> object:
    review_slots = review.get("scalar_slots")
    selections = approval.get("scalar_selections")
    if not isinstance(review_slots, dict) or not isinstance(selections, dict):
        raise TypeError("scalar review/approval maps missing")
    item = review_slots.get(slot)
    selected = selections.get(slot)
    if not isinstance(item, dict):
        raise ValueError(f"review scalar slot missing: {slot}")
    candidates = item.get("candidates")
    if not isinstance(candidates, list) or selected not in candidates:
        raise ValueError(
            f"approved scalar for {slot} is not present in review candidates"
        )
    return selected


def _materialize_candidate_input(
    *,
    slot: str,
    candidate: dict[str, object],
    derived_root: Path,
) -> dict[str, object]:
    kind = candidate["kind"]
    expected_sha = candidate["sha256"]
    if kind == "INLINE_TEXT":
        value = candidate.get("value")
        if not isinstance(value, str):
            raise ValueError(f"inline candidate value missing for {slot}")
        path = derived_root / f"{slot}.txt"
        write_new_text(path, value)
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected_sha:
            raise ValueError(f"derived inline SHA mismatch for {slot}")
        return {
            "name": slot,
            "kind": "FILE",
            "path": str(path),
            "expected_sha256": expected_sha,
        }

    path_value = candidate.get("path")
    if not isinstance(path_value, str):
        raise ValueError(f"path missing for approved slot {slot}")
    return {
        "name": slot,
        "kind": kind,
        "path": path_value,
        "expected_sha256": expected_sha,
    }


def materialize_approved_reference_loop_foundation(
    *,
    review_path: Path,
    approval_path: Path,
    lineage_bridge_path: Path,
    mechanical_panel_path: Path,
    protected_task_access_path: Path,
    output_root: Path,
) -> dict[str, object]:
    review = _load_object(review_path)
    approval = _load_object(approval_path)
    lineage = _load_object(lineage_bridge_path)
    panel = _load_object(mechanical_panel_path)

    if review.get("schema_id") != "PI1_IDENTITY_SLOT_REVIEW_V1":
        raise ValueError("identity review schema mismatch")
    if approval.get("schema_id") != "PI1_IDENTITY_SLOT_APPROVAL_V1":
        raise ValueError("identity approval schema mismatch")
    if approval.get("schema_version") != 1:
        raise ValueError("identity approval version mismatch")
    if approval.get("approval_token") != APPROVAL_TOKEN:
        raise ValueError("identity approval token mismatch")
    if approval.get("decision") != "APPROVED":
        raise ValueError("identity approval decision is not APPROVED")
    if approval.get("review_sha256") != review.get("review_sha256"):
        raise ValueError("identity approval is not bound to this review")

    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(f"output root already exists: {output_root}")
    output_root.mkdir(parents=True)
    derived_root = output_root / "identity_inputs"
    derived_root.mkdir()

    artifact_slots = (
        "base_model_artifact",
        "adapter_artifact",
        "tokenizer_artifact",
        "chat_template",
        "policy_runtime_manifest",
        "decoding_contract",
        "raw_policy_prompt_protocol",
        "training_config",
        "training_data_manifest",
        "reference_evaluation_manifest",
    )
    registrations = [
        _materialize_candidate_input(
            slot=slot,
            candidate=_selected_candidate(
                review,
                approval,
                slot=slot,
            ),
            derived_root=derived_root,
        )
        for slot in artifact_slots
    ]

    registration = build_registration_payload(
        logical_policy_id=str(review["logical_policy_id"]),
        checkpoint_instance_id=str(review["checkpoint_instance_id"]),
        base_model_id=str(
            _selected_scalar(review, approval, slot="base_model_id")
        ),
        adapter_id=str(
            _selected_scalar(review, approval, slot="adapter_id")
        ),
        tokenizer_identity=str(
            _selected_scalar(review, approval, slot="tokenizer_identity")
        ),
        runtime_core_commit=str(
            _selected_scalar(
                review,
                approval,
                slot="runtime_core_commit",
            )
        ),
        evaluator_commit=str(
            _selected_scalar(
                review,
                approval,
                slot="evaluator_commit",
            )
        ),
        training_seed=int(
            _selected_scalar(review, approval, slot="training_seed")
        ),
        artifact_registrations=registrations,
    )
    registration_path = (
        output_root / "PI1_IDENTITY_SOURCE_REGISTRATION_V1.json"
    )
    write_new_json(registration_path, registration)

    identity_path = output_root / "PI1_REFERENCE_IDENTITY_V1.json"
    identity = materialize_pi1_reference_identity_file(
        registration_path=registration_path,
        output_path=identity_path,
    )

    task_access_path = output_root / "TASK_ACCESS_REVALIDATION_V1.json"
    task_access = revalidate_task_access_file(
        source_manifest_path=protected_task_access_path,
        output_path=task_access_path,
    )

    if lineage.get("schema_id") != "SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_V1":
        raise ValueError("lineage bridge schema mismatch")
    if panel.get("schema_id") != (
        "SOURCE_COLLECTION_MECHANICAL_EVIDENCE_PANEL_V1"
    ):
        raise ValueError("mechanical panel schema mismatch")
    if panel.get("lineage_bridge_sha256") != lineage.get("bridge_sha256"):
        raise ValueError("mechanical panel lineage differs from bridge")

    panel_rows = panel.get("rows")
    lineage_rows = lineage.get("rows")
    if not isinstance(panel_rows, list) or not isinstance(lineage_rows, list):
        raise TypeError("panel/lineage rows must be arrays")
    mechanical_by_bundle = {
        row["attempt_bundle_sha256"]: row
        for row in panel_rows
        if isinstance(row, dict)
    }
    if len(mechanical_by_bundle) != 12 or len(lineage_rows) != 12:
        raise ValueError("approved materialization requires exactly 12 rows")

    pack_root = output_root / "analyzer_evidence_packs"
    rebinding_root = output_root / "trajectory_rebinding"
    pack_root.mkdir()
    rebinding_root.mkdir()
    manifest_rows = []

    for index, lineage_row in enumerate(lineage_rows):
        if not isinstance(lineage_row, dict):
            raise TypeError("lineage row must be object")
        bundle = validate_attempt_bundle(
            Path(str(lineage_row["source_bundle_path"]))
        )
        if (
            bundle.attempt_bundle_sha256
            != lineage_row["attempt_bundle_sha256"]
        ):
            raise ValueError("lineage bundle SHA drift")

        rebinding_path = (
            rebinding_root / f"{index:02d}_{lineage_row['source_attempt_id']}.json"
        )
        rebinding = write_historical_trajectory_rebinding_manifest(
            bundle=bundle,
            pi1_identity=identity,
            task_access=task_access,
            lineage_bridge=lineage,
            output_path=rebinding_path,
        )

        mechanical_row = mechanical_by_bundle.get(
            bundle.attempt_bundle_sha256
        )
        if not isinstance(mechanical_row, dict):
            raise ValueError("mechanical evidence row missing for bundle")
        mechanical_path = Path(
            str(mechanical_row["mechanical_evidence_path"])
        )
        mechanical = _load_object(mechanical_path)
        if mechanical.get("evidence_sha256") != mechanical_row.get(
            "mechanical_evidence_sha256"
        ):
            raise ValueError("mechanical evidence SHA binding mismatch")

        pack_path = (
            pack_root / f"{index:02d}_{lineage_row['source_attempt_id']}.json"
        )
        pack = write_analyzer_evidence_pack(
            bundle=bundle,
            pi1_identity=identity,
            rebinding_manifest=rebinding,
            mechanical_evidence=mechanical,
            lineage_bridge=lineage,
            output_path=pack_path,
        )
        manifest_rows.append(
            {
                "source_attempt_id": lineage_row["source_attempt_id"],
                "task_id": bundle.task_id,
                "task_type": bundle.episode.get("task_type"),
                "attempt_bundle_sha256": bundle.attempt_bundle_sha256,
                "trajectory_rebinding_path": str(rebinding_path),
                "trajectory_rebinding_sha256": rebinding[
                    "manifest_sha256"
                ],
                "analyzer_evidence_pack_path": str(pack_path),
                "analyzer_evidence_pack_sha256": pack[
                    "evidence_pack_sha256"
                ],
            }
        )

    final_manifest = {
        "schema_id": "REFERENCE_LOOP_ANALYZER_EVIDENCE_FOUNDATION_V1",
        "schema_version": 1,
        "pi1_identity_path": str(identity_path),
        "pi1_identity_sha256": identity["identity_sha256"],
        "task_access_revalidation_path": str(task_access_path),
        "task_access_revalidation_sha256": task_access[
            "revalidation_sha256"
        ],
        "lineage_bridge_path": str(lineage_bridge_path),
        "lineage_bridge_sha256": lineage["bridge_sha256"],
        "mechanical_panel_path": str(mechanical_panel_path),
        "mechanical_panel_sha256": panel["panel_sha256"],
        "row_count": len(manifest_rows),
        "rows": manifest_rows,
        "analyzer_model_called": False,
        "environment_execution_performed": False,
        "scientific_outcome_created": False,
        "formal_analyzer_execution_authorized": False,
        "manifest_sha256": "0" * 64,
    }
    final_manifest["manifest_sha256"] = domain_hash(
        "REFERENCE_LOOP_ANALYZER_EVIDENCE_FOUNDATION_V1",
        final_manifest,
        excluded_field="manifest_sha256",
    )
    final_manifest_path = (
        output_root / "REFERENCE_LOOP_ANALYZER_EVIDENCE_FOUNDATION_V1.json"
    )
    write_new_json(final_manifest_path, final_manifest)
    return final_manifest
