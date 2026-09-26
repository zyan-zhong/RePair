#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.reference_loop.identity_review import build_review_files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", required=True)
    parser.add_argument("--lineage-bridge", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--training-materialization-root")
    parser.add_argument("--formal-a-runtime-binding")
    parser.add_argument("--decoding-search-root", action="append", default=[])
    parser.add_argument("--training-config-root")
    parser.add_argument("--training-dataset-manifest")
    parser.add_argument("--reference-evaluation-manifest")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-text", required=True)
    args = parser.parse_args()

    review = build_review_files(
        census_path=Path(args.census),
        lineage_bridge_path=Path(args.lineage_bridge),
        repository_root=Path(args.repository_root),
        training_materialization_root=(
            None
            if args.training_materialization_root is None
            else Path(args.training_materialization_root)
        ),
        formal_a_runtime_binding_path=(
            None
            if args.formal_a_runtime_binding is None
            else Path(args.formal_a_runtime_binding)
        ),
        decoding_search_roots=tuple(
            Path(item) for item in args.decoding_search_root
        ),
        training_config_root=(
            None
            if args.training_config_root is None
            else Path(args.training_config_root)
        ),
        training_dataset_manifest_path=(
            None
            if args.training_dataset_manifest is None
            else Path(args.training_dataset_manifest)
        ),
        reference_evaluation_manifest_path=(
            None
            if args.reference_evaluation_manifest is None
            else Path(args.reference_evaluation_manifest)
        ),
        output_json=Path(args.output_json),
        output_text=Path(args.output_text),
    )
    print("PI1_IDENTITY_SLOT_REVIEW_V1_PASS")
    print("REVIEW_SHA256=" + str(review["review_sha256"]))
    print(
        "ALL_REQUIRED_SLOTS_UNIQUE="
        + str(review["all_required_slots_unique"])
    )
    print("OUTPUT_JSON=" + str(Path(args.output_json).resolve()))
    print("OUTPUT_TEXT=" + str(Path(args.output_text).resolve()))


if __name__ == "__main__":
    main()
