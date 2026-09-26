#!/usr/bin/env python3
"""Run/resume registered Memory live cells locally or through Slurm arrays."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads

APPROVAL = "EXECUTION_APPROVED_FAILURE_MEMORY_LIVE_STAGES_V1"


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=JSON_ARTIFACT_NOT_REGULAR:" + str(path))
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or raw not in {canonical_json_bytes(value), canonical_json_bytes(value)}:
        raise SystemExit("STOP=JSON_ARTIFACT_NOT_CANONICAL:" + str(path))
    return value


def parse_cells(path: Path) -> list[dict[str, object]]:
    rows = []
    for raw in path.read_bytes().splitlines(keepends=True):
        if not raw:
            continue
        value = strict_json_loads(raw)
        if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
            raise SystemExit("STOP=CELL_MANIFEST_NOT_CANONICAL")
        rows.append(value)
    return rows


def verify_manifest(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest = canonical_object(path)
    if manifest.get("schema_id") != "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2" or manifest.get("schema_version") != 2:
        raise SystemExit("STOP=EXECUTION_MANIFEST_SCHEMA")
    expected = hashlib.sha256(
        b"FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2\0"
        + canonical_json_bytes({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    ).hexdigest()
    if manifest.get("manifest_sha256") != expected:
        raise SystemExit("STOP=EXECUTION_MANIFEST_SELF_HASH")
    if manifest.get("scientific_execution_authorized") is not False or manifest.get("preoutcome_frozen") is not True:
        raise SystemExit("STOP=EXECUTION_MANIFEST_AUTHORITY_FLAGS")
    bindings = manifest.get("bindings")
    paths = manifest.get("operational_paths")
    if not isinstance(bindings, dict) or not isinstance(paths, dict):
        raise SystemExit("STOP=EXECUTION_MANIFEST_BINDINGS")
    for name, row in bindings.items():
        if not isinstance(row, dict) or set(row) != {"file_sha256", "semantic_sha256", "size_bytes", "role"}:
            raise SystemExit("STOP=EXECUTION_BINDING_ROW:" + name)
        path_value = Path(str(paths.get(name, "")))
        if path_value.is_symlink() or not path_value.is_file():
            raise SystemExit("STOP=EXECUTION_BINDING_PATH:" + name)
        raw = path_value.read_bytes()
        if len(raw) != row["size_bytes"] or hashlib.sha256(raw).hexdigest() != row["file_sha256"]:
            raise SystemExit("STOP=EXECUTION_BINDING_BYTES:" + name)
        if row["role"] != name:
            raise SystemExit("STOP=EXECUTION_BINDING_ROLE:" + name)
    executor = Path(str(paths["cell_executor"]))
    if not os.access(executor, os.X_OK):
        raise SystemExit("STOP=CELL_EXECUTOR_NOT_EXECUTABLE")
    cells_path = Path(str(paths["cell_manifest"]))
    cells = parse_cells(cells_path)
    if len(cells) != manifest.get("registered_cell_count"):
        raise SystemExit("STOP=REGISTERED_CELL_COUNT_MISMATCH")
    ids = [row.get("cell_id") for row in cells]
    if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
        raise SystemExit("STOP=CELL_ID_POPULATION_INVALID")
    return manifest, cells


def verify_cell_output(cell_root: Path, *, cell_id: str, manifest_sha: str) -> None:
    receipt_path = cell_root / "CELL_TERMINAL_RECEIPT_V1.json"
    result_path = cell_root / "CELL_SCIENTIFIC_RESULT_V1.json"
    if not receipt_path.is_file() or receipt_path.is_symlink() or not result_path.is_file() or result_path.is_symlink():
        raise SystemExit("STOP=CELL_OUTPUT_INCOMPLETE:" + cell_id)
    receipt = canonical_object(receipt_path)
    result = canonical_object(result_path)
    if receipt.get("cell_id") != cell_id or result.get("cell_id") != cell_id:
        raise SystemExit("STOP=CELL_OUTPUT_IDENTITY:" + cell_id)
    if receipt.get("execution_manifest_sha256") != manifest_sha or result.get("execution_manifest_sha256") != manifest_sha:
        raise SystemExit("STOP=CELL_OUTPUT_MANIFEST_BINDING:" + cell_id)
    if receipt.get("cell_complete") is not True or receipt.get("scientific_outcome_produced") is not True or receipt.get("infrastructure_error") is not False:
        raise SystemExit("STOP=CELL_OUTPUT_NOT_SCIENTIFICALLY_COMPLETE:" + cell_id)
    if receipt.get("cell_result_sha256") != result.get("cell_result_sha256"):
        raise SystemExit("STOP=CELL_OUTPUT_CROSS_BINDING:" + cell_id)


def run_one(
    *,
    manifest_path: Path,
    manifest: dict[str, object],
    cells: list[dict[str, object]],
    output_root: Path,
    cell_index: int,
) -> None:
    if cell_index < 0 or cell_index >= len(cells):
        raise SystemExit("STOP=CELL_INDEX_OUT_OF_RANGE")
    row = cells[cell_index]
    cell_id = str(row["cell_id"])
    stage_root = output_root / str(manifest["stage"]) / str(manifest["manifest_sha256"])
    cell_root = stage_root / "cells" / cell_id
    if cell_root.exists():
        verify_cell_output(
            cell_root,
            cell_id=cell_id,
            manifest_sha=str(manifest["manifest_sha256"]),
        )
        print("CELL_RESUME_PASS=" + cell_id)
        return
    cell_root.parent.mkdir(parents=True, exist_ok=True)
    executor = Path(str(manifest["operational_paths"]["cell_executor"]))
    cell_manifest = Path(str(manifest["operational_paths"]["cell_manifest"]))
    command = [
        str(executor),
        "--execution-manifest", str(manifest_path.resolve()),
        "--cell-manifest", str(cell_manifest.resolve()),
        "--cell-index", str(cell_index),
        "--output-dir", str(cell_root),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"STOP=CELL_EXECUTION_FAILED:{cell_id}:rc={completed.returncode}")
    verify_cell_output(
        cell_root,
        cell_id=cell_id,
        manifest_sha=str(manifest["manifest_sha256"]),
    )
    print("CELL_EXECUTION_PASS=" + cell_id)


def write_new(path: Path, data: bytes, mode: int = 0o600) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--mode", required=True, choices=("preflight", "run-local", "run-one", "submit-slurm"))
    parser.add_argument("--cell-index", type=int)
    parser.add_argument("--max-parallel", type=int, default=8)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest, cells = verify_manifest(manifest_path)
    output_root = Path(args.output_root)

    if args.mode == "preflight":
        print("MEMORY_LIVE_PREFLIGHT_V2_PASS")
        print("STAGE=" + str(manifest["stage"]))
        print("CELL_COUNT=" + str(len(cells)))
        return
    if os.environ.get("FAILURE_MEMORY_LIVE_EXECUTION_APPROVAL") != APPROVAL:
        raise SystemExit("STOP=LIVE_EXECUTION_APPROVAL_MISSING")
    if args.mode == "run-one":
        if args.cell_index is None:
            raise SystemExit("STOP=CELL_INDEX_REQUIRED")
        run_one(
            manifest_path=manifest_path,
            manifest=manifest,
            cells=cells,
            output_root=output_root,
            cell_index=args.cell_index,
        )
        return
    if args.mode == "run-local":
        for index in range(len(cells)):
            run_one(
                manifest_path=manifest_path,
                manifest=manifest,
                cells=cells,
                output_root=output_root,
                cell_index=index,
            )
        print("MEMORY_LIVE_LOCAL_EXECUTION_V2_PASS")
        return
    if args.max_parallel < 1:
        raise SystemExit("STOP=MAX_PARALLEL_INVALID")
    stage_root = output_root / str(manifest["stage"]) / str(manifest["manifest_sha256"])
    script = stage_root / "slurm_array.sh"
    runner = Path(__file__).resolve()
    lines = [
        "#!/usr/bin/env bash",
        "#SBATCH --job-name=fm-live",
        f"#SBATCH --output={stage_root}/slurm-%A_%a.out",
        f"#SBATCH --error={stage_root}/slurm-%A_%a.err",
        f"#SBATCH --array=0-{len(cells)-1}%{args.max_parallel}",
        "set -euo pipefail",
        f"export FAILURE_MEMORY_LIVE_EXECUTION_APPROVAL={APPROVAL}",
        "exec " + " ".join((
            json.dumps(sys.executable),
            json.dumps(str(runner)),
            "--manifest", json.dumps(str(manifest_path.resolve())),
            "--output-root", json.dumps(str(output_root.resolve())),
            "--mode", "run-one",
            "--cell-index", '"${SLURM_ARRAY_TASK_ID}"',
        )),
    ]
    write_new(script, ("\n".join(lines) + "\n").encode(), mode=0o700)
    subprocess.run(["sbatch", str(script)], check=True)
    print("MEMORY_LIVE_SLURM_SUBMITTED_V2")
    print("SLURM_SCRIPT=" + str(script))


if __name__ == "__main__":
    main()
