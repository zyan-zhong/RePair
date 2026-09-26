#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from pchsi.reference_loop.discovery import (
    discover_reference_loop_inputs_file,
)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value = discover_reference_loop_inputs_file(
        roots=tuple(Path(item) for item in args.root),
        output_path=Path(args.output),
    )
    print("REFERENCE_LOOP_INPUT_DISCOVERY_V1_PASS")
    print("COMPLETE_BUNDLES=" + str(value["complete_bundle_count"]))
    print(
        "PI1_DEV_COMPLETE_BUNDLES="
        + str(value["pi1_dev_complete_bundle_count"])
    )
    print("DISCOVERY_STATUS=" + str(value["discovery_status"]))
    print("OUTPUT=" + str(Path(args.output).resolve()))

if __name__ == "__main__":
    main()
