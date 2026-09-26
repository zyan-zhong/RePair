#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from pchsi.reference_loop.task_access import (
    revalidate_task_access_file,
)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value = revalidate_task_access_file(
        source_manifest_path=Path(args.source_manifest),
        output_path=Path(args.output),
    )
    dispositions = {}
    for row in value["rows"]:
        dispositions[row["revalidation_disposition"]] = (
            dispositions.get(row["revalidation_disposition"], 0) + 1
        )
    print("TASK_ACCESS_REVALIDATION_V1_PASS")
    print("ROW_COUNT=" + str(value["row_count"]))
    print("DISPOSITIONS=" + repr(dispositions))
    print("OUTPUT=" + str(Path(args.output).resolve()))

if __name__ == "__main__":
    main()
