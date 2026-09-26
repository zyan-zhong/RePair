#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from pchsi.reference_loop.identity import (
    materialize_pi1_reference_identity_file,
)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value = materialize_pi1_reference_identity_file(
        registration_path=Path(args.registration),
        output_path=Path(args.output),
    )
    print("PI1_REFERENCE_IDENTITY_V1_PASS")
    print("IDENTITY_SHA256=" + str(value["identity_sha256"]))
    print("OUTPUT=" + str(Path(args.output).resolve()))

if __name__ == "__main__":
    main()
