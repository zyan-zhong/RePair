"""Offline, fail-closed P1-B access artifact materialization."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.evaluation.distillation_access import (
    HistoricalAccessAuditV1,
)
from pchsi.evaluation.distillation_governance import (
    freeze_governance_inputs,
)
from pchsi.evaluation.p1b_access_crosswalk import (
    LegacyCurrentTaskCrosswalkV1,
    LegacyTaskIdentityV1,
    match_legacy_to_current,
)
from pchsi.evaluation.p1b_access_materializer import (
    materialize_task_access_manifest,
)
from pchsi.evaluation.p1b_lineage import (
    CurrentPilotDataLineageV1,
    build_p1_dev_policy_condition,
    build_p1_dev_schedule,
)
from pchsi.evaluation.p1b_split import (
    P1BSplitContractV1,
    assign_p1b_access,
)
from pchsi.evaluation.task_manifest import (
    load_frozen_task_manifest,
)


_ALLOWED_LEGACY_FIELDS = {
    "legacy_source",
    "legacy_task_id",
    "legacy_gamefile",
    "legacy_gamefile_sha1",
    "current_manifest_index",
    "evidence_source",
    "manual_same_gamefile_confirmed",
}

_FORBIDDEN_RESULT_FIELDS = {
    "success",
    "reward",
    "failure_type",
    "model_output",
    "teacher_reason",
    "failure_reason",
    "trajectory",
}

_FROZEN_TASK_MANIFEST_RELATIVE_PATH = Path(
    "data/manifests/"
    "alfworld_strict_valid_unseen_all134_v1.jsonl"
)

_FROZEN_TASK_MANIFEST_SHA256 = (
    "6e480bb663a6f17207aa2c7a6e1b504a"
    "dad8448f6e8a2615c5e62fea0b64c0f4"
)


def _load_json(path: Path) -> object:
    return strict_json_loads(path.read_bytes())


def _validate_frozen_manifest_input(
    *,
    manifest_path: Path,
    manifest_sha256: str,
) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    expected = (
        repo_root / _FROZEN_TASK_MANIFEST_RELATIVE_PATH
    ).resolve(strict=True)

    supplied = Path(manifest_path)
    if supplied.is_symlink():
        raise ValueError(
            "task manifest path must not be a symlink"
        )
    observed = supplied.resolve(strict=True)

    if observed != expected:
        raise ValueError(
            "task manifest path is not the frozen "
            "strict-134 manifest"
        )
    if manifest_sha256 != _FROZEN_TASK_MANIFEST_SHA256:
        raise ValueError(
            "task manifest SHA-256 is not the frozen "
            "strict-134 identity"
        )
    return observed


def _strict_object_list(
    path: Path,
) -> list[dict[str, object]]:
    root = _load_json(path)
    if not isinstance(root, list):
        raise TypeError(
            f"{path} must contain JSON array"
        )

    records: list[dict[str, object]] = []
    for index, item in enumerate(root):
        if not isinstance(item, dict):
            raise TypeError(
                f"record {index} must be object"
            )

        forbidden = set(item) & _FORBIDDEN_RESULT_FIELDS
        if forbidden:
            raise ValueError(
                "legacy identity input contains forbidden "
                f"result fields: {sorted(forbidden)}"
            )

        unknown = set(item) - _ALLOWED_LEGACY_FIELDS
        if unknown:
            raise ValueError(
                "legacy identity input contains unknown "
                f"fields: {sorted(unknown)}"
            )

        for required in (
            "legacy_source",
            "evidence_source",
            "current_manifest_index",
        ):
            if required not in item:
                raise ValueError(
                    "legacy identity input missing "
                    f"{required}"
                )

        if (
            not isinstance(item["legacy_source"], str)
            or not item["legacy_source"]
        ):
            raise ValueError(
                "legacy_source must be non-empty string"
            )
        if (
            not isinstance(item["evidence_source"], str)
            or not item["evidence_source"]
        ):
            raise ValueError(
                "evidence_source must be non-empty string"
            )
        if (
            type(item["current_manifest_index"]) is not int
            or item["current_manifest_index"] < 0
        ):
            raise ValueError(
                "current_manifest_index must be "
                "non-negative int"
            )
        if (
            "manual_same_gamefile_confirmed" in item
            and type(
                item["manual_same_gamefile_confirmed"]
            ) is not bool
        ):
            raise ValueError(
                "manual_same_gamefile_confirmed must be bool"
            )

        records.append(item)
    return records


def _write_exclusive(
    path: Path,
    data: bytes,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def materialize(
    *,
    manifest_path: Path,
    manifest_sha256: str,
    legacy_identities_path: Path,
    historical_audit_path: Path,
    forced_dev_evidence_path: Path,
    gamefile_sha256_path: Path,
    runtime_identity_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    output_dir = Path(output_dir)
    if os.path.lexists(output_dir):
        raise FileExistsError(output_dir)
    if (
        not output_dir.parent.is_dir()
        or output_dir.parent.is_symlink()
    ):
        raise ValueError(
            "output parent must be existing "
            "non-symlink directory"
        )

    frozen_manifest_path = (
        _validate_frozen_manifest_input(
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
        )
    )

    records = load_frozen_task_manifest(
        manifest_path=frozen_manifest_path,
        expected_sha256=(
            _FROZEN_TASK_MANIFEST_SHA256
        ),
    )

    audit = HistoricalAccessAuditV1.from_json(
        Path(historical_audit_path).read_bytes()
    )

    forced_raw = _load_json(
        Path(forced_dev_evidence_path)
    )
    if not isinstance(forced_raw, dict):
        raise TypeError(
            "forced DEV evidence ledger must be object"
        )

    forced: dict[str, tuple[str, ...]] = {}
    for key, value in forced_raw.items():
        if not isinstance(key, str) or not key:
            raise ValueError(
                "forced DEV evidence task IDs must be "
                "non-empty strings"
            )
        if (
            not isinstance(value, list)
            or not value
            or any(
                not isinstance(item, str) or not item
                for item in value
            )
        ):
            raise ValueError(
                f"forced DEV evidence for {key} must "
                "be a non-empty string list"
            )
        forced[key] = tuple(value)

    sha_raw = _load_json(
        Path(gamefile_sha256_path)
    )
    if not isinstance(sha_raw, dict):
        raise TypeError(
            "gamefile SHA-256 map must be object"
        )

    legacy_rows = _strict_object_list(
        Path(legacy_identities_path)
    )
    current_by_index = {
        record.index: record
        for record in records
    }

    crosswalk_rows = []
    for item in legacy_rows:
        manifest_index = item[
            "current_manifest_index"
        ]
        if (
            type(manifest_index) is not int
            or manifest_index not in current_by_index
        ):
            raise ValueError(
                "legacy current_manifest_index invalid"
            )

        legacy = LegacyTaskIdentityV1(
            item["legacy_source"],
            item.get("legacy_task_id"),
            item.get("legacy_gamefile"),
            item.get("legacy_gamefile_sha1"),
            item["evidence_source"],
            item.get(
                "manual_same_gamefile_confirmed",
                False,
            ),
        )
        crosswalk_rows.append(
            match_legacy_to_current(
                legacy=legacy,
                current=current_by_index[manifest_index],
            )
        )

    crosswalk = LegacyCurrentTaskCrosswalkV1(
        "LEGACY_CURRENT_TASK_CROSSWALK_V1",
        1,
        "P1_B_LEGACY_CURRENT_CROSSWALK_V1",
        _FROZEN_TASK_MANIFEST_SHA256,
        len(crosswalk_rows),
        tuple(crosswalk_rows),
    )

    contract = P1BSplitContractV1()
    proof = assign_p1b_access(
        records=records,
        audit=audit,
        forced_dev_evidence=forced,
    )

    access = materialize_task_access_manifest(
        records=records,
        audit=audit,
        split_proof=proof,
        gamefile_sha256_by_task_id=sha_raw,
    )

    runtime = _load_json(
        Path(runtime_identity_path)
    )
    required_runtime_fields = {
        "policy_runtime_manifest_sha256",
        "tokenizer_identity_manifest_sha256",
        "chat_template_sha256",
        "raw_protocol_sha256",
        "runtime_core_commit",
        "evaluator_commit",
    }
    if (
        not isinstance(runtime, dict)
        or set(runtime) != required_runtime_fields
    ):
        raise ValueError(
            "runtime identity fields mismatch"
        )

    policy = build_p1_dev_policy_condition(
        **runtime
    )
    schedule = build_p1_dev_schedule(
        task_access_manifest=access,
        policy_condition=policy,
    )
    lineage = CurrentPilotDataLineageV1()

    os.mkdir(output_dir, 0o700)

    objects = {
        "legacy_current_task_crosswalk.json": (
            crosswalk.to_json().encode()
        ),
        "historical_access_audit.json": (
            audit.to_json().encode()
        ),
        "forced_dev_tasks.json": (
            canonical_json_bytes(forced)
        ),
        "split_contract.json": (
            contract.to_json().encode()
        ),
        "split_proof.json": proof.to_json().encode(),
        "task_access_manifest.json": (
            access.to_json().encode()
        ),
        "current_pilot_data_lineage.json": (
            lineage.to_json().encode()
        ),
        "policy_condition_manifest.json": (
            policy.to_json().encode()
        ),
        "condition_run_schedule.json": (
            schedule.to_json().encode()
        ),
    }

    for name, data in objects.items():
        _write_exclusive(
            output_dir / name,
            data,
        )

    governance = output_dir / "governance"
    freeze_governance_inputs(
        historical_access_audit=audit,
        task_access_manifest=access,
        policy_condition=policy,
        schedule=schedule,
        output_dir=governance,
    )

    checksums = "".join(
        f"{sha256_bytes(data)}  {name}\n"
        for name, data in sorted(objects.items())
    ).encode()
    _write_exclusive(
        output_dir / "P1B_SHA256SUMS",
        checksums,
    )

    return {
        "dev_count": sum(
            record.access_class.value == "DEV_VISIBLE"
            for record in access.records
        ),
        "select_count": sum(
            record.access_class.value
            == "SELECT_SUMMARY_ONLY"
            for record in access.records
        ),
        "output_dir": str(output_dir),
    }


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser()

    for name in (
        "manifest-path",
        "legacy-identities-path",
        "historical-audit-path",
        "forced-dev-evidence-path",
        "gamefile-sha256-path",
        "runtime-identity-path",
        "output-dir",
    ):
        parser.add_argument(
            f"--{name}",
            required=True,
            type=Path,
        )

    parser.add_argument(
        "--manifest-sha256",
        required=True,
    )

    args = parser.parse_args(argv)

    result = materialize(
        manifest_path=args.manifest_path,
        manifest_sha256=args.manifest_sha256,
        legacy_identities_path=(
            args.legacy_identities_path
        ),
        historical_audit_path=(
            args.historical_audit_path
        ),
        forced_dev_evidence_path=(
            args.forced_dev_evidence_path
        ),
        gamefile_sha256_path=(
            args.gamefile_sha256_path
        ),
        runtime_identity_path=(
            args.runtime_identity_path
        ),
        output_dir=args.output_dir,
    )

    print(
        json.dumps(
            result,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
