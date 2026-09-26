#!/usr/bin/env python3
from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path

from common import (
    ContractError,
    finalize,
    load_json_object,
    sha256_file,
    write_new_json,
)


def copy_regular(src: Path, dst: Path) -> None:
    if src.is_symlink() or not src.is_file():
        raise ContractError(f"REVIEW_SOURCE_NOT_REGULAR:{src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise ContractError(f"REVIEW_TARGET_EXISTS:{dst}")
    dst.write_bytes(src.read_bytes())
    dst.chmod(0o600)


def zip_tree(root: Path, out: Path) -> None:
    temp = out.with_suffix(".tmp.zip")
    if temp.exists():
        temp.unlink()
    with zipfile.ZipFile(
        temp, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root.parent).as_posix()
            info = zipfile.ZipInfo(
                rel, date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(info, path.read_bytes())
    out.write_bytes(temp.read_bytes())
    out.chmod(0o600)
    temp.unlink()


def main() -> int:
    census_path = (
        Path(os.environ["CENSUS_ROOT"])
        / "FROZEN_Q2_RENDERER_INTERFACE_CENSUS_V1.json"
    )
    excerpt_path = (
        Path(os.environ["CENSUS_ROOT"])
        / "MATERIALIZER_RELEVANT_SOURCE_EXCERPTS_V1.txt"
    )
    bridge_path = (
        Path(os.environ["BRIDGE_ROOT"])
        / "REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_V1.json"
    )
    census = load_json_object(census_path)
    bridge = load_json_object(bridge_path)

    review = Path(os.environ["REVIEW_ROOT"])
    review.mkdir(parents=True, exist_ok=False)

    sources = [
        census_path,
        excerpt_path,
        bridge_path,
        Path(os.environ["PI1_ROW_RENDERER_PATH"]),
        Path(os.environ["PI1_FINAL_MATERIALIZATION_MANIFEST_PATH"]),
        Path(os.environ["V13_SEMANTIC_ROOT"])
        / "DETERMINISTIC_SEMANTIC_DATASET_MATERIALIZATION_V1.json",
        Path(os.environ["V14_PREFLIGHT_ROOT"])
        / "POSTSEMANTIC_SERIALIZATION_AND_TRAINER_PREFLIGHT_SUMMARY_V1.json",
    ]

    files = []
    for source in sources:
        target = review / "evidence" / source.name
        copy_regular(source, target)
        files.append(
            {
                "path": target.relative_to(review).as_posix(),
                "sha256": sha256_file(target),
                "size_bytes": target.stat().st_size,
            }
        )

    manifest = finalize(
        "FROZEN_Q2_RENDERER_CENSUS_REFERENCE_BRIDGE_REVIEW_V1",
        "review_manifest_sha256",
        {
            "schema_id": "FROZEN_Q2_RENDERER_CENSUS_REFERENCE_BRIDGE_REVIEW_V1",
            "schema_version": 1,
            "renderer_interface_census_sha256": census[
                "renderer_interface_census_sha256"
            ],
            "normative_bridge_sha256": bridge[
                "normative_bridge_sha256"
            ],
            "files": files,
            "renderer_source_executed": False,
            "trainer_native_dataset_materialized": False,
            "trainer_execution_authorized": False,
            "training_execution_count": 0,
            "next_gate": (
                "BUILD_EXACT_SCHEMA_AWARE_RENDERER_ADAPTER_FROM_CENSUS"
            ),
        },
    )
    write_new_json(review / "REVIEW_MANIFEST_V1.json", manifest)

    out = Path(os.environ["OUTPUT_ROOT"]) / "review.zip"
    zip_tree(review, out)

    print("FROZEN_RENDERER_CENSUS_REFERENCE_BRIDGE_REVIEW_PASS")
    print(
        "REVIEW_MANIFEST_SHA256="
        + manifest["review_manifest_sha256"]
    )
    print("REVIEW_ZIP=" + str(out))
    print("REVIEW_ZIP_SHA256=" + sha256_file(out))
    print("RENDERER_SOURCE_EXECUTED=false")
    print("TRAINER_NATIVE_DATASET_MATERIALIZED=false")
    print("TRAINER_EXECUTION_AUTHORIZED=false")
    print(
        "NEXT_GATE="
        "BUILD_EXACT_SCHEMA_AWARE_RENDERER_ADAPTER_FROM_CENSUS"
    )
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
