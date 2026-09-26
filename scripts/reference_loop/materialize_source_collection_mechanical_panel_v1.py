#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
from pchsi.reference_loop.canonical import (
    domain_hash,
    write_new_json,
)
from pchsi.reference_loop.mechanical import (
    extract_mechanical_episode_evidence,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lineage-bridge", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    bridge_path = Path(args.lineage_bridge).resolve()
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    if bridge.get("schema_id") != "SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_V1":
        raise SystemExit("STOP=LINEAGE_BRIDGE_SCHEMA")
    output = Path(args.output_dir).resolve()
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=MECHANICAL_PANEL_OUTPUT_EXISTS")
    output.mkdir(parents=True)

    rows = []
    for index, source_row in enumerate(bridge["rows"]):
        bundle = validate_attempt_bundle(
            Path(source_row["source_bundle_path"])
        )
        if (
            bundle.attempt_bundle_sha256
            != source_row["attempt_bundle_sha256"]
        ):
            raise SystemExit("STOP=BRIDGE_BUNDLE_SHA_DRIFT")
        facts = extract_mechanical_episode_evidence(bundle)
        name = (
            f"{index:02d}_"
            + str(source_row["source_attempt_id"])
            + ".json"
        )
        path = output / name
        write_new_json(path, facts)
        rows.append(
            {
                "source_attempt_id": source_row["source_attempt_id"],
                "attempt_bundle_sha256": bundle.attempt_bundle_sha256,
                "task_id": bundle.task_id,
                "gamefile_sha256": bundle.gamefile_sha256,
                "task_access_row_sha256": source_row[
                    "task_access_row_sha256"
                ],
                "human_registered_case_authority": source_row[
                    "human_registered_case_authority"
                ],
                "mechanical_evidence_path": str(path),
                "mechanical_evidence_sha256": facts["evidence_sha256"],
            }
        )

    panel = {
        "schema_id": "SOURCE_COLLECTION_MECHANICAL_EVIDENCE_PANEL_V1",
        "schema_version": 1,
        "lineage_bridge_path": str(bridge_path),
        "lineage_bridge_sha256": bridge["bridge_sha256"],
        "row_count": len(rows),
        "rows": rows,
        "authority": "DETERMINISTIC_FACTS_ONLY",
        "analyzer_model_called": False,
        "environment_execution_performed": False,
        "scientific_outcome_created": False,
        "panel_sha256": "0" * 64,
    }
    panel["panel_sha256"] = domain_hash(
        "SOURCE_COLLECTION_MECHANICAL_EVIDENCE_PANEL_V1",
        panel,
        excluded_field="panel_sha256",
    )
    write_new_json(output / "PANEL_V1.json", panel)

    print("SOURCE_COLLECTION_MECHANICAL_EVIDENCE_PANEL_V1_PASS")
    print("ROW_COUNT=" + str(len(rows)))
    print("PANEL_SHA256=" + str(panel["panel_sha256"]))
    print("OUTPUT_DIR=" + str(output))


if __name__ == "__main__":
    main()
