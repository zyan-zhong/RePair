#!/usr/bin/env python3
"""Bind the exact three Formal-A replay sources to exact B-DIRECT records.

Offline only: no model, environment, retrieval, or scheduler execution.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    strict_json_loads,
)
from pchsi.memory.procedural_builder import ProceduralFailureMemoryRecordV1
from pchsi.memory.scientific_validation import (
    A0ArmBindingV1,
    A0SourceBindingV1,
    build_a0_scientific_manifest_v1,
)
from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1


EXPECTED_POLICY = "P4-R1-Q2-BAD-TRAIN17"
EXPECTED_SNAPSHOT = (
    "8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189"
)
EXPECTED_TOKEN_CONTRACT = (
    "613166c9f092795cb03c892ee0046f0af5bf7fc13ba44f7fccb950027c329262"
)
ENGINEERING_BASE = "112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("output parent invalid")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _load_replay_manifest(
    path: Path,
) -> tuple[
    dict[str, object],
    tuple[tuple[dict[str, object], RegisteredReplaySourceV1], ...],
]:
    payload = strict_json_loads(path.read_bytes())
    if (
        not isinstance(payload, dict)
        or set(payload) != {"authority_commit", "cases"}
    ):
        raise ValueError("replay qualification manifest contract mismatch")
    cases = payload["cases"]
    if not isinstance(cases, list) or len(cases) != 3:
        raise ValueError("Formal A requires exactly three replay cases")

    result = []
    for case in cases:
        if not isinstance(case, dict):
            raise TypeError("replay case must be object")
        for key in (
            "case_id",
            "registration_id",
            "replay_source_path",
            "replay_source_sha256",
        ):
            if key not in case:
                raise ValueError(f"replay case missing {key}")
        source_path = Path(case["replay_source_path"])
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError("replay source path invalid")
        data = source_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != case["replay_source_sha256"]:
            raise ValueError("replay source SHA mismatch")
        source = RegisteredReplaySourceV1.from_json(data)
        if source.canonical_bytes() != data:
            raise ValueError("replay source must be canonical")
        if source.source_policy_condition != EXPECTED_POLICY:
            raise ValueError("replay source policy condition mismatch")
        result.append((case, source))

    sources = tuple(item[1] for item in result)
    if len({x.source_task_id for x in sources}) != 3:
        raise ValueError("source task IDs must be unique")
    if len({x.source_gamefile_sha256 for x in sources}) != 3:
        raise ValueError("source gamefile groups must be unique")
    return payload, tuple(result)


def _load_index(path: Path) -> dict[str, object]:
    payload = strict_json_loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise TypeError("representation index must be object")
    expected = {
        "schema_id": "PACKAGE_B_DIRECT_REPRESENTATION_INDEX_V1",
        "schema_version": 1,
        "snapshot_sha256": EXPECTED_SNAPSHOT,
        "token_budget_contract_sha256": EXPECTED_TOKEN_CONTRACT,
        "record_count": 3,
        "core_matched_record_count": 3,
        "b_direct_infrastructure_ready": True,
        "pi1_matched_memory_representation_ablation_ready": True,
        "scientific_execution_authorized": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"representation index mismatch at {key}")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 3:
        raise ValueError("representation index requires three records")
    return payload


def _record_map(snapshot_root: Path):
    paths = tuple(sorted(snapshot_root.rglob("governed_record.json")))
    if len(paths) != 3:
        raise ValueError(
            f"active snapshot must expose exactly three governed records: {len(paths)}"
        )
    result = []
    for path in paths:
        data = path.read_bytes()
        record = ProceduralFailureMemoryRecordV1.from_json(data)
        if record.canonical_bytes() != data:
            raise ValueError("governed record must be canonical")
        result.append((path, record))
    return tuple(result)


def _matching_record(source, records):
    matches = []
    for record_path, record in records:
        for factual in record.provenance.factual_sequence_bindings:
            if (
                factual.source_task_id == source.source_task_id
                and factual.source_bundle_sha256 == source.source_bundle_sha256
            ):
                matches.append((record_path, record))
                break
    if len(matches) != 1:
        raise ValueError(
            "source-to-governed-record match count must be one: "
            f"{source.source_task_id} -> {len(matches)}"
        )
    return matches[0]


def _template_for(record, index_root: Path, index_payload):
    matches = [
        x
        for x in index_payload["records"]
        if x.get("memory_lineage_id") == record.memory_lineage_id
        and x.get("record_version") == record.record_version
    ]
    if len(matches) != 1:
        raise ValueError("representation index lineage/version count mismatch")
    row = matches[0]
    if row.get("core_matched_ready") is not True:
        raise ValueError("representation template not core-matched ready")

    path = (
        index_root
        / f"{record.memory_lineage_id}.v{record.record_version}"
        / "representation_template.json"
    )
    if path.is_symlink() or not path.is_file():
        raise ValueError("representation template path invalid")
    payload = strict_json_loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise TypeError("representation template must be object")
    if payload.get("snapshot_sha256") != EXPECTED_SNAPSHOT:
        raise ValueError("template snapshot mismatch")
    if payload.get("memory_lineage_id") != record.memory_lineage_id:
        raise ValueError("template lineage mismatch")
    if payload.get("record_version") != record.record_version:
        raise ValueError("template record version mismatch")
    if payload.get("template_sha256") != row.get("template_sha256"):
        raise ValueError("template/index SHA identity mismatch")
    if payload.get("core_matched_ready") is not True:
        raise ValueError("template core matched readiness false")

    arms = payload.get("arms")
    if (
        not isinstance(arms, list)
        or [x.get("arm_id") for x in arms[:4]] != ["M0", "M1", "M2", "M3"]
    ):
        raise ValueError("template core arm order mismatch")
    if any(x.get("availability") != "AVAILABLE" for x in arms[:4]):
        raise ValueError("all four Formal-A core arms must be available")
    return path, payload


def _arm_binding(value):
    arm_id = value["arm_id"]
    payload = value.get("policy_visible_payload")
    if arm_id == "M0":
        if payload != []:
            raise ValueError("M0 must have empty Memory payload")
        policy_payload_sha = None
    else:
        if not isinstance(payload, dict):
            raise ValueError("Memory arm payload must be object")
        policy_payload_sha = hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest()

    return A0ArmBindingV1(
        arm_id=arm_id,
        representation_class=value["representation_class"],
        availability=value["availability"],
        artifact_sha256=value.get("artifact_sha256"),
        policy_payload_sha256=policy_payload_sha,
        token_count=value["token_count"],
        retrieval_mode=value["retrieval_mode"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-manifest", required=True)
    parser.add_argument("--representation-index", required=True)
    parser.add_argument("--dependency-binding", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    replay_path = Path(args.replay_manifest)
    index_path = Path(args.representation_index)
    dependency_path = Path(args.dependency_binding)
    for path in (replay_path, index_path, dependency_path):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("STOP=FORMAL_A_INPUT_PATH_INVALID")

    dependency = strict_json_loads(dependency_path.read_bytes())
    if (
        not isinstance(dependency, dict)
        or dependency.get("schema_id")
        != "PACKAGE_B_FAILURE_MEMORY_DEPENDENCY_V1"
    ):
        raise SystemExit("STOP=PACKAGE_B_DEPENDENCY_INVALID")
    if dependency.get("active_snapshot_sha256") != EXPECTED_SNAPSHOT:
        raise SystemExit("STOP=FORMAL_A_ACTIVE_SNAPSHOT_MISMATCH")
    if dependency.get("token_budget_contract_sha256") != EXPECTED_TOKEN_CONTRACT:
        raise SystemExit("STOP=FORMAL_A_TOKEN_CONTRACT_MISMATCH")

    snapshot_root = Path(dependency["active_snapshot_external_directory"])
    if snapshot_root.is_symlink() or not snapshot_root.is_dir():
        raise SystemExit("STOP=FORMAL_A_ACTIVE_SNAPSHOT_DIRECTORY_INVALID")

    replay_payload, cases = _load_replay_manifest(replay_path)
    index_payload = _load_index(index_path)
    records = _record_map(snapshot_root)

    output_root = Path(args.output_root)
    if output_root.exists() or output_root.is_symlink():
        raise SystemExit("STOP=FORMAL_A_BINDING_OUTPUT_EXISTS")
    output_root.mkdir(parents=True, mode=0o700)

    source_bindings = []
    binding_rows = []
    seen_lineages = set()

    for position, (case, source) in enumerate(cases):
        record_path, record = _matching_record(source, records)
        if record.memory_lineage_id in seen_lineages:
            raise SystemExit("STOP=FORMAL_A_DUPLICATE_MEMORY_LINEAGE")
        seen_lineages.add(record.memory_lineage_id)

        template_path, template = _template_for(
            record,
            index_path.parent,
            index_payload,
        )
        arms = tuple(_arm_binding(x) for x in template["arms"][:4])
        source_binding = A0SourceBindingV1(
            source_state_id=(
                source.expected_source_fingerprint.fingerprint_sha256
            ),
            source_task_id=source.source_task_id,
            task_gamefile_group_id=source.source_gamefile_sha256,
            source_fingerprint_sha256=(
                source.expected_source_fingerprint.fingerprint_sha256
            ),
            source_bundle_sha256=source.source_bundle_sha256,
            memory_lineage_id=record.memory_lineage_id,
            record_version=record.record_version,
            snapshot_sha256=EXPECTED_SNAPSHOT,
            representation_template_sha256=template["template_sha256"],
            continuation_seed=17,
            arms=arms,
        )
        source_bindings.append(source_binding)
        binding_rows.append(
            {
                "source_position": position,
                "case_id": case["case_id"],
                "registration_id": case["registration_id"],
                "replay_source_path": str(
                    Path(case["replay_source_path"]).resolve()
                ),
                "replay_source_sha256": case["replay_source_sha256"],
                "source_state_id": source_binding.source_state_id,
                "source_task_id": source.source_task_id,
                "source_gamefile_sha256": source.source_gamefile_sha256,
                "source_bundle_sha256": source.source_bundle_sha256,
                "governed_record_path": str(record_path.resolve()),
                "governed_record_file_sha256": _sha(record_path),
                "memory_lineage_id": record.memory_lineage_id,
                "record_version": record.record_version,
                "representation_template_path": str(template_path.resolve()),
                "representation_template_file_sha256": _sha(template_path),
                "representation_template_sha256": template["template_sha256"],
                "continuation_seed": 17,
            }
        )

        _write_once(
            output_root / f"source_binding_{position}.json",
            canonical_json_bytes(source_binding.to_dict()),
        )

    if len(source_bindings) != 3 or len(seen_lineages) != 3:
        raise SystemExit(
            "STOP=FORMAL_A_REQUIRES_THREE_DISTINCT_SOURCE_RECORDS"
        )

    manifest = build_a0_scientific_manifest_v1(
        engineering_base_head=ENGINEERING_BASE,
        sources=tuple(source_bindings),
    )
    _write_once(
        output_root / "a0_scientific_manifest.json",
        manifest.canonical_bytes(),
    )

    binding = {
        "schema_id": "FORMAL_A0_REAL_INPUT_BINDING_V1",
        "schema_version": 1,
        "replay_qualification_manifest_path": str(replay_path.resolve()),
        "replay_qualification_manifest_sha256": _sha(replay_path),
        "replay_authority_commit": replay_payload["authority_commit"],
        "representation_index_path": str(index_path.resolve()),
        "representation_index_file_sha256": _sha(index_path),
        "active_snapshot_sha256": EXPECTED_SNAPSHOT,
        "token_budget_contract_sha256": EXPECTED_TOKEN_CONTRACT,
        "policy_condition_id": EXPECTED_POLICY,
        "source_count": 3,
        "cell_count": 12,
        "sources": binding_rows,
        "a0_scientific_manifest_sha256": manifest.manifest_sha256,
        "scientific_execution_authorized": False,
        "memory_on_scientific_execution": False,
        "effect_authority": "UNTESTED",
    }
    _write_once(
        output_root / "formal_a0_real_input_binding.json",
        canonical_json_bytes(binding),
    )

    print("FORMAL_A0_REAL_INPUT_BINDING_PASS")
    print("FORMAL_A0_SOURCE_COUNT=3")
    print("FORMAL_A0_CELL_COUNT=12")
    print("A0_SCIENTIFIC_MANIFEST_SHA256=" + manifest.manifest_sha256)
    print("SCIENTIFIC_EXECUTION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
