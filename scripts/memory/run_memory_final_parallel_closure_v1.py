#!/usr/bin/env python3
"""Execute Memory stages sequentially but cells concurrently inside one GPU job."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.canonical_evidence import strict_json_loads


def object_value(path: Path) -> dict[str, object]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise SystemExit("STOP=PARALLEL_CLOSURE_OBJECT_REQUIRED:" + str(path))
    return value


def cells(path: Path) -> list[dict[str, object]]:
    result = []
    for raw in path.read_bytes().splitlines():
        if raw:
            value = strict_json_loads(raw)
            if not isinstance(value, dict):
                raise SystemExit("STOP=PARALLEL_CLOSURE_CELL_OBJECT")
            result.append(value)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure-manifest", required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    closure_path = Path(args.closure_manifest)
    closure = object_value(closure_path)
    live_root = Path(str(closure["live_output_root"]))
    closure_root = Path(str(closure["closure_output_root"]))
    max_parallel = int(closure["max_parallel"])
    if max_parallel < 1:
        raise SystemExit("STOP=PARALLEL_CLOSURE_MAX_PARALLEL")

    runner = repo / "scripts/memory/run_memory_live_cells_v2.py"
    aggregator = repo / "scripts/memory/aggregate_memory_live_stage_v2.py"
    stages = (
        ("stage1b", Path(str(
            closure["inputs"]["stage1b_execution_manifest"]["path"]
        ))),
        ("stage2", Path(str(
            closure["inputs"]["stage2_execution_manifest"]["path"]
        ))),
        ("stage3", Path(str(
            closure["inputs"]["stage3_execution_manifest"]["path"]
        ))),
    )

    for stage_name, manifest_path in stages:
        manifest = object_value(manifest_path)
        authority = (
            closure_root
            / "stage_authorities"
            / stage_name
            / "RESULT_AUTHORITY_V2.json"
        )
        if authority.is_file() and not authority.is_symlink():
            print("PARALLEL_STAGE_AUTHORITY_RESUME=" + stage_name)
            continue

        subprocess.run([
            sys.executable, str(runner),
            "--manifest", str(manifest_path),
            "--output-root", str(live_root),
            "--mode", "preflight",
        ], check=True)

        cell_path = Path(str(manifest["operational_paths"]["cell_manifest"]))
        rows = cells(cell_path)
        pending = []
        stage_root = (
            live_root
            / str(manifest["stage"])
            / str(manifest["manifest_sha256"])
        )
        for index, row in enumerate(rows):
            receipt = (
                stage_root / "cells" / str(row["cell_id"])
                / "CELL_TERMINAL_RECEIPT_V1.json"
            )
            if not receipt.is_file():
                pending.append(index)

        print(
            "PARALLEL_STAGE_START="
            + stage_name
            + ":pending="
            + str(len(pending))
            + ":parallel="
            + str(max_parallel)
        )

        def run_one(index: int) -> int:
            completed = subprocess.run([
                sys.executable, str(runner),
                "--manifest", str(manifest_path),
                "--output-root", str(live_root),
                "--mode", "run-one",
                "--cell-index", str(index),
            ], check=False)
            return completed.returncode

        failures = []
        with ThreadPoolExecutor(max_workers=max_parallel) as pool:
            futures = {pool.submit(run_one, index): index for index in pending}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    code = future.result()
                except BaseException as exc:
                    failures.append((index, type(exc).__name__))
                    continue
                if code != 0:
                    failures.append((index, "rc=" + str(code)))
        if failures:
            raise SystemExit(
                "STOP=PARALLEL_STAGE_CELL_FAILURES:"
                + stage_name
                + ":"
                + repr(failures[:20])
            )

        cells_root = stage_root / "cells"
        authority_root = closure_root / "stage_authorities" / stage_name
        subprocess.run([
            sys.executable, str(aggregator),
            "--execution-manifest", str(manifest_path),
            "--cells-root", str(cells_root),
            "--output-dir", str(authority_root),
        ], check=True)
        print("PARALLEL_STAGE_COMPLETE=" + stage_name)

    subprocess.run([
        sys.executable,
        str(repo / "scripts/memory/run_failure_memory_closure_v2.py"),
        "--closure-manifest", str(closure_path),
        "--phase", "finalize",
    ], check=True)
    print("FAILURE_MEMORY_FINAL_PARALLEL_CLOSURE_V1_PASS")


if __name__ == "__main__":
    main()
