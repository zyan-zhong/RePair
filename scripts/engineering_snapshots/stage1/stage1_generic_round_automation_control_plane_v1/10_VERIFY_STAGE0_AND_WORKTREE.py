from __future__ import annotations

from pathlib import Path
import json
import zipfile

from stage1_pkg.common import Stage1PackageError, load_json, sha256_file, write_new_json
from stage1_pkg.constants import (
    OUTPUT_ROOT,
    PREEXISTING_CHANGED_PATHS,
    STAGE0_CLOSEOUT_SHA256,
    STAGE0_CLOSEOUT_ZIP,
    STAGE0_CLOSEOUT_ZIP_SHA256,
    STAGE0_GENERIC_PATCH_FREEZE_ROOT_SHA256,
    STAGE0_GENERIC_PATCH_RECEIPT,
    STAGE0_HANDOFF_SHA256,
)
from stage1_pkg.worktree import status_paths, verify_head_and_detached


def main() -> int:
    if sha256_file(STAGE0_CLOSEOUT_ZIP) != STAGE0_CLOSEOUT_ZIP_SHA256:
        raise Stage1PackageError("Stage0 closeout ZIP SHA changed")
    if not zipfile.is_zipfile(STAGE0_CLOSEOUT_ZIP):
        raise Stage1PackageError("Stage0 closeout is not a ZIP")

    with zipfile.ZipFile(STAGE0_CLOSEOUT_ZIP) as archive:
        if archive.testzip() is not None:
            raise Stage1PackageError("Stage0 closeout ZIP CRC failed")
        closeout = json.loads(
            archive.read("PILOT_ENGINEERING_ROUND_CLOSEOUT_V1.json")
        )
        handoff = json.loads(
            archive.read("STAGE1_AUTOMATION_HANDOFF_V1.json")
        )
        result = json.loads(
            archive.read("HUMAN_PILOT_STAGE0_PAIRED_RESULTS_V1.json")
        )

    if closeout.get("closeout_sha256") != STAGE0_CLOSEOUT_SHA256:
        raise Stage1PackageError("Stage0 closeout domain SHA changed")
    if closeout.get("round_status") != "CLOSED":
        raise Stage1PackageError("Stage0 is not closed")
    if closeout.get("paper_efficacy_evidence") is not False:
        raise Stage1PackageError("Stage0 paper boundary changed")
    if closeout.get("promotion_eligible") is not False:
        raise Stage1PackageError("Stage0 promotion boundary changed")
    if handoff.get("stage1_handoff_sha256") != STAGE0_HANDOFF_SHA256:
        raise Stage1PackageError("Stage1 handoff SHA changed")
    if handoff.get("status") != "READY_FOR_STAGE1_AUTOMATION_DESIGN":
        raise Stage1PackageError("Stage1 handoff status changed")
    if result.get("paired_cell_count") != 85:
        raise Stage1PackageError("Stage0 paired cell count changed")
    if result.get("total_condition_cell_count") != 170:
        raise Stage1PackageError("Stage0 total cell count changed")

    patch = load_json(STAGE0_GENERIC_PATCH_RECEIPT)
    if patch.get("generic_select_artifact_patch_freeze_root_sha256") != (
        STAGE0_GENERIC_PATCH_FREEZE_ROOT_SHA256
    ):
        raise Stage1PackageError("Stage0 Generic SELECT patch changed")

    verify_head_and_detached()
    observed = status_paths()
    if observed != set(PREEXISTING_CHANGED_PATHS):
        raise Stage1PackageError(
            "Stage1 worktree prestate changed: " + repr(sorted(observed))
        )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_id": "STAGE1_PRECONDITION_RECEIPT_V1",
        "schema_version": 1,
        "status": "PASS",
        "stage0_closeout_zip_sha256": STAGE0_CLOSEOUT_ZIP_SHA256,
        "stage0_closeout_sha256": STAGE0_CLOSEOUT_SHA256,
        "stage0_handoff_sha256": STAGE0_HANDOFF_SHA256,
        "stage0_parent_success_cells": result.get("parent_success_cells"),
        "stage0_candidate_success_cells": result.get("candidate_success_cells"),
        "stage0_mean_task_success_rate_delta": result.get(
            "mean_task_success_rate_delta"
        ),
        "stage0_generic_select_patch_freeze_root_sha256": (
            STAGE0_GENERIC_PATCH_FREEZE_ROOT_SHA256
        ),
        "worktree_prestate_paths": sorted(observed),
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
    }
    write_new_json(OUTPUT_ROOT / "STAGE1_PRECONDITION_RECEIPT_V1.json", receipt)
    print("STAGE1_PRECONDITION_PASS")
    print("MODEL_EXECUTION_COUNT=0")
    print("ENVIRONMENT_EXECUTION_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
