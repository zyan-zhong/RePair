#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.reference_loop.identity_census import (
    build_pi1_identity_authority_census_file,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-a-runtime-root", action="append", default=[])
    parser.add_argument("--select-root", action="append", default=[])
    parser.add_argument("--checkpoint-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    value = build_pi1_identity_authority_census_file(
        formal_a_runtime_roots=tuple(
            Path(item) for item in args.formal_a_runtime_root
        ),
        select_roots=tuple(Path(item) for item in args.select_root),
        checkpoint_root=Path(args.checkpoint_root),
        output_path=Path(args.output),
    )
    print("PI1_IDENTITY_AUTHORITY_CENSUS_V1_PASS")
    print("READINESS_STATUS=" + str(value["readiness_status"]))
    print(
        "FORMAL_A_RUNTIME_DISTINCT_SHA_COUNT="
        + str(len(value["formal_a_runtime_distinct_sha256s"]))
    )
    print(
        "SELECT_RUNTIME_MATCH_COUNT="
        + str(len(value["select_runtime_manifest_matches"]))
    )
    print(
        "SEED17_ADAPTER_DIRECTORY_PRESENT="
        + str(value["seed17_adapter_directory_present"])
    )
    print("CENSUS_SHA256=" + str(value["census_sha256"]))
    print("OUTPUT=" + str(Path(args.output).resolve()))


if __name__ == "__main__":
    main()
