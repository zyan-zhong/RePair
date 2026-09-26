from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from pchsi.reference_loop.canonical import (
    domain_hash,
    strict_json_loads,
    write_new_json,
)
from pchsi.round_control.campaign_authority import (
    CampaignStartupAuthorityV1,
)

from .orchestrator import execute_one
from .request_renderer import render_stage_request
from .runtime_disposition import (
    GLOBAL_INFRASTRUCTURE_FAIL_CLOSED,
    QUARANTINE_SOURCE_CONTINUE_UNRELATED,
    classify_hard_stop,
)
from .schema_registry import validate_artifact


def _obj(path: Path) -> dict[str, object]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _logical_id(
    *,
    identity: Mapping[str, object],
    unit: Mapping[str, object],
    registry: Mapping[str, object],
    projection: Mapping[str, object],
) -> str:
    bundle = render_stage_request(
        stage_id=unit["stage_id"],
        projection=projection,
    )
    return domain_hash(
        "COGNITIVE_LOGICAL_CALL_ID_V1",
        {
            "scientific_unit_identity_sha256": identity[
                "identity_sha256"
            ],
            "stage_id": unit["stage_id"],
            "condition_id": unit.get("condition_id"),
            "round_id": registry["round_id"],
            "policy_version": registry["policy_version"],
            "request_body_sha256": bundle["request_body_sha256"],
        },
    )


def _attempt_for_logical(
    call_dir: Path,
    logical: Mapping[str, object],
) -> dict[str, object]:
    contributing = logical.get("contributing_attempt_id")
    if not isinstance(contributing, str) or ":" not in contributing:
        raise ValueError("terminal logical call has invalid attempt identity")
    try:
        index = int(contributing.rsplit(":", 1)[1])
    except ValueError as error:
        raise ValueError("invalid terminal attempt index") from error
    return _obj(call_dir / f"attempt_{index:03d}.json")


def _adopt_terminal(call_dir: Path) -> dict[str, object]:
    logical_path = call_dir / "logical_call.json"
    method_path = call_dir / "method_result.json"
    if not logical_path.is_file() or not method_path.is_file():
        raise RuntimeError(
            "PARTIAL_LOGICAL_CALL_FAIL_CLOSED:" + call_dir.name
        )
    logical = _obj(logical_path)
    method = _obj(method_path)
    attempt = _attempt_for_logical(call_dir, logical)
    return {
        "logical_call_id": logical.get("logical_call_id"),
        "call_dir": str(call_dir),
        "status": logical.get("terminal_method_status")
        or method.get("status"),
        "method_failure_reason": method.get("failure_class"),
        "hard_stop": bool(method.get("hard_stop", False)),
        "reused_terminal": True,
        "same_logical_call_resend_authorized": False,
        "transport_attempt_id": attempt.get("transport_attempt_id"),
    }


def run_registry(
    *,
    registry_path: Path,
    output_root: Path,
    limit: int | None = None,
    campaign_authority: CampaignStartupAuthorityV1 | None = None,
) -> tuple[dict[str, object], int]:
    reg = _obj(registry_path)
    validate_artifact("RUNTIME_INPUT_REGISTRY_V1", reg)
    units = reg["units"] if limit is None else reg["units"][:limit]
    if not isinstance(units, list):
        raise TypeError("registry units must be list")

    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "execution_manifest.json"
    if manifest_path.is_file():
        existing = _obj(manifest_path)
        if existing.get("registry_sha256") != reg.get("registry_sha256"):
            raise ValueError("existing execution manifest registry mismatch")
        status = existing.get("terminal_route")
        return existing, 20 if status == GLOBAL_INFRASTRUCTURE_FAIL_CLOSED else 0

    rows: list[dict[str, object]] = []
    quarantined: set[str] = set()
    terminal_route: str | None = None
    base = registry_path.resolve().parent
    max_restarts = (
        0
        if campaign_authority is None
        else campaign_authority.max_infrastructure_attempt_restarts
    )

    for unit in units:
        source_unit_id = str(unit["source_unit_id"])
        identity = _obj(base / unit["scientific_unit_identity_path"])
        projection = _obj(base / unit["input_projection_path"])
        access = _obj(base / unit["task_access_record_path"])

        for field, expected_key in (
            ("evidence_pack_sha256", "expected_common_evidence_sha256"),
            ("a1_local_result_sha256", "expected_a1_local_result_sha256"),
            ("memory_pack_sha256", "expected_memory_pack_sha256"),
        ):
            expected = unit.get(expected_key)
            if (
                expected is not None
                and projection.get(field) != expected
            ):
                raise ValueError(
                    f"registry binding mismatch for {field}"
                )

        if source_unit_id in quarantined:
            rows.append(
                {
                    "source_unit_id": source_unit_id,
                    "stage_id": unit["stage_id"],
                    "condition_id": unit.get("condition_id"),
                    "scientific_unit_id": identity[
                        "scientific_unit_id"
                    ],
                    "logical_call_id": None,
                    "call_dir": None,
                    "status": "QUARANTINED_SOURCE_SKIPPED",
                    "method_failure_reason": (
                        "SOURCE_QUARANTINED_AFTER_AMBIGUOUS_POST_SEND"
                    ),
                    "hard_stop": False,
                    "provider_call_executed": False,
                    "same_logical_call_resend_authorized": False,
                }
            )
            continue

        logical_id = _logical_id(
            identity=identity,
            unit=unit,
            registry=reg,
            projection=projection,
        )
        call_dir = out / logical_id
        if call_dir.exists():
            result = _adopt_terminal(call_dir)
        else:
            result = execute_one(
                output_root=out,
                unit_identity=identity,
                stage_id=unit["stage_id"],
                condition_id=unit["condition_id"],
                round_id=reg["round_id"],
                policy_version=reg["policy_version"],
                projection=projection,
                task_access=access,
                max_infrastructure_attempt_restarts=max_restarts,
            )
            result["reused_terminal"] = False
            result["same_logical_call_resend_authorized"] = False

        row = {
            "source_unit_id": source_unit_id,
            "stage_id": unit["stage_id"],
            "condition_id": unit["condition_id"],
            "scientific_unit_id": identity["scientific_unit_id"],
            **result,
        }
        rows.append(row)

        if row.get("hard_stop") is True:
            route = classify_hard_stop(
                row=row,
                call_dir=Path(str(row["call_dir"])),
            )
            if (
                route["route"]
                == QUARANTINE_SOURCE_CONTINUE_UNRELATED
            ):
                quarantined.add(source_unit_id)
                continue
            terminal_route = str(route["route"])
            break

    manifest = {
        "schema_id": "COGNITIVE_RUNTIME_EXECUTION_MANIFEST_V2",
        "schema_version": 2,
        "registry_sha256": reg["registry_sha256"],
        "round_id": reg["round_id"],
        "policy_version": reg["policy_version"],
        "campaign_authority_sha256": (
            None
            if campaign_authority is None
            else campaign_authority.authority_sha256
        ),
        "max_infrastructure_attempt_restarts": max_restarts,
        "quarantined_source_ids": sorted(quarantined),
        "terminal_route": terminal_route,
        "rows": rows,
    }
    write_new_json(manifest_path, manifest)
    rc = 20 if terminal_route is not None else 0
    return manifest, rc
