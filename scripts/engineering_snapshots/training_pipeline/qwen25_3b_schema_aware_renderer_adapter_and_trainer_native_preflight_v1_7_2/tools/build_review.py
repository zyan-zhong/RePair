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
    review = Path(os.environ["REVIEW_ROOT"])
    review.mkdir(parents=True, exist_ok=False)

    sources = [
        Path(os.environ["REPRO_ROOT"])
        / "HISTORICAL_Q2_RENDERER_EXACT_REPRODUCTION_V1.json",
        Path(os.environ["SOURCE_ADAPTER_ROOT"])
        / "POLICY_T2_SCHEMA_AWARE_RENDERER_SOURCE_V1.jsonl",
        Path(os.environ["NATIVE_ROOT"])
        / "POLICY_T2_TRAINER_NATIVE_V1.jsonl",
        Path(os.environ["NATIVE_ROOT"])
        / "POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json",
        Path(os.environ["MAINLINE_ROOT"])
        / "RESEARCH_MAINLINE_ZH_VIEW_V1.json",
        Path(os.environ["PREFLIGHT_ROOT"])
        / "TRAINER_EXECUTION_PREFLIGHT_V5.json",
        Path(os.environ["V16_CENSUS_PATH"]),
        Path(os.environ["V16_NORMATIVE_BRIDGE_PATH"]),
        Path(os.environ["V16_MATERIALIZER_EXCERPT_PATH"]),
        Path(os.environ["PI1_ROW_RENDERER_PATH"]),
        Path(os.environ["PI1_FINAL_MATERIALIZATION_MANIFEST_PATH"]),
        Path(os.environ["STRONG_PLAN_PATH"]),
        Path(os.environ["PARENT_CHECKPOINT_SET_MANIFEST"]),
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

    native = load_json_object(
        Path(os.environ["NATIVE_ROOT"])
        / "POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json"
    )
    mainline = load_json_object(
        Path(os.environ["MAINLINE_ROOT"])
        / "RESEARCH_MAINLINE_ZH_VIEW_V1.json"
    )
    preflight = load_json_object(
        Path(os.environ["PREFLIGHT_ROOT"])
        / "TRAINER_EXECUTION_PREFLIGHT_V5.json"
    )

    manifest = finalize(
        "SCHEMA_AWARE_RENDERER_ADAPTER_REVIEW_MANIFEST_V1",
        "review_manifest_sha256",
        {
            "schema_id": "SCHEMA_AWARE_RENDERER_ADAPTER_REVIEW_MANIFEST_V1",
            "schema_version": 1,
            "trainer_native_dataset_manifest_sha256": native[
                "trainer_native_dataset_manifest_sha256"
            ],
            "research_mainline_zh_view_sha256": mainline[
                "research_mainline_zh_view_sha256"
            ],
            "trainer_preflight_v5_sha256": preflight[
                "trainer_preflight_v5_sha256"
            ],
            "files": files,
            "historical_renderer_reproduction_required": True,
            "historical_renderer_84_exact_match_required": True,
            "policy_hindsight_leakage_forbidden": True,
            "trainer_execution_authorized": False,
            "training_execution_count": 0,
            "next_gate": (
                "BUILD_AND_REVIEW_PARENT_TRAIN17_LORA_CONTINUATION_TRAINER_RUNNER"
            ),
        },
    )
    write_new_json(review / "REVIEW_MANIFEST_V1.json", manifest)

    out = Path(os.environ["OUTPUT_ROOT"]) / "review.zip"
    zip_tree(review, out)

    print("【阶段50】V1.7 Review 包：通过")
    print("REVIEW_MANIFEST_SHA256=" + manifest["review_manifest_sha256"])
    print("REVIEW_ZIP=" + str(out))
    print("REVIEW_ZIP_SHA256=" + sha256_file(out))
    print("下一关=构建并审核Train17_LoRA继续训练Runner")
    print("TRAINER_EXECUTION_AUTHORIZED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
