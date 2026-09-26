from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

from auditlib.common import (
    AuditError,
    domain_sha256,
    load_json,
    require_file_sha,
    sha256_file,
    write_json_create_once,
)


ROUND_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1"
)
RECOVERED_ZIP = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "ROUND_HUMAN_T2_FORMAL_TRAINING_REVIEW_V1_RECOVERED.zip"
)
TRAIN_ROOT = (
    ROUND_ROOT
    / "human_t2_train17_continuation_v1"
    / "human-t2-train17-continuation-v1-a000"
)
ATTEMPT_ROOT = (
    ROUND_ROOT
    / "human_t2_train17_continuation_stage_attempts_v1"
    / "human-t2-train17-continuation-v1-a000"
)

REPO_CANDIDATES = (
    Path(
        "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
        "pchsi-wt-human-reference-round-pi1-pi2-v1"
    ),
    Path(
        "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
        "phase-critical-harness-guided-self-improvement"
    ),
)

OUTPUT_PARENT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts"
)
OUTPUT_ROOT = (
    OUTPUT_PARENT
    / "human_t2_training_result_audit_offoff_reuse_census_v1_output"
)
OUTPUT_ZIP = (
    OUTPUT_PARENT
    / "HUMAN_T2_TRAINING_RESULT_AUDIT_OFFOFF_REUSE_CENSUS_V1.zip"
)

EXPECTED_PARENT_ADAPTER = (
    "b296f2254b1fa1f2e141dffd3f6b5af"
    "903f839df4790ffcb245fd8dd57773ace"
)
EXPECTED_PARENT_PARAMETER = (
    "1801dc72946471ac3ada1ab61967c86d"
    "03874b209d9342db94b0054cccdb3dac"
)
EXPECTED_CANDIDATE_ADAPTER = (
    "908acf081e80008800284653c3340c39"
    "7353eef0de08ee044f06810cab2a251e"
)
EXPECTED_AUTHORIZATION = (
    "fb735be69f6bc345b45ba37423b2043b"
    "3fe1cfe416714c60f76f6efeb25f990b"
)
EXPECTED_DATASET_SHA = (
    "ae5fa948fe75a56c287e0a0907021124"
    "2a0a933bc0a1011486b186bba824ea39"
)
EXPECTED_PLAN_DOMAIN = (
    "282fe712c85641c47f9c29f2b942c6b"
    "94528d22a942345d4ac57553ab95697d2"
)

REQUIRED_ZIP_MEMBERS = (
    "REVIEW_MANIFEST_V1.json",
    "authority/approval_witness.json",
    "authority/approved_authorization.json",
    "evidence/adapter_artifact_manifest.json",
    "evidence/formal_run_manifest.json",
    "evidence/input_artifact_index.json",
    "evidence/output_artifact_index.json",
    "evidence/slurm_runtime_context.json",
    "evidence/started_stage_receipt.json",
    "evidence/terminal_stage_receipt.json",
    "evidence/training_step_ledger.jsonl",
)

SEARCH_RE = re.compile(
    r"(off.?off|harness.?off|memory.?off|"
    r"run_e1_evaluator|episode_evaluator|"
    r"policy_runtime_manifest|policy_client|"
    r"adapter|lora|checkpoint|valid_unseen|"
    r"evaluation_binding|promotion|rollback)",
    re.IGNORECASE,
)

FILENAME_RE = re.compile(
    r"(eval|evaluator|episode|policy|runtime|benchmark|"
    r"off|harness|adapter|checkpoint|schedule)",
    re.IGNORECASE,
)

SCAN_SUFFIXES = {".py", ".json", ".md", ".txt", ".sh"}
MAX_FILE_BYTES = 3 * 1024 * 1024
MAX_MATCHES_PER_FILE = 30


def zip_json(
    archive: zipfile.ZipFile,
    name: str,
) -> dict:
    try:
        value = json.loads(
            archive.read(name).decode("utf-8")
        )
    except Exception as exc:
        raise AuditError(
            f"ZIP_JSON_INVALID:{name}:{exc}"
        ) from exc
    if not isinstance(value, dict):
        raise AuditError(f"ZIP_JSON_OBJECT_REQUIRED:{name}")
    return value


def audit_recovered_zip() -> dict:
    if not RECOVERED_ZIP.is_file():
        raise AuditError(
            f"RECOVERED_ZIP_MISSING:{RECOVERED_ZIP}"
        )
    if RECOVERED_ZIP.stat().st_size <= 0:
        raise AuditError("RECOVERED_ZIP_EMPTY")
    if not zipfile.is_zipfile(RECOVERED_ZIP):
        raise AuditError("RECOVERED_ZIP_MAGIC_INVALID")

    with zipfile.ZipFile(RECOVERED_ZIP, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise AuditError(
                f"RECOVERED_ZIP_CRC_FAILED:{bad}"
            )
        names = tuple(sorted(archive.namelist()))
        if names != tuple(sorted(REQUIRED_ZIP_MEMBERS)):
            raise AuditError(
                "RECOVERED_ZIP_MEMBER_SET_CHANGED:"
                + repr(names)
            )

        review = zip_json(
            archive,
            "REVIEW_MANIFEST_V1.json",
        )
        run = zip_json(
            archive,
            "evidence/formal_run_manifest.json",
        )
        adapter = zip_json(
            archive,
            "evidence/adapter_artifact_manifest.json",
        )
        started = zip_json(
            archive,
            "evidence/started_stage_receipt.json",
        )
        terminal = zip_json(
            archive,
            "evidence/terminal_stage_receipt.json",
        )
        output_index = zip_json(
            archive,
            "evidence/output_artifact_index.json",
        )
        authorization = zip_json(
            archive,
            "authority/approved_authorization.json",
        )

        ledger = [
            json.loads(line)
            for line in archive.read(
                "evidence/training_step_ledger.jsonl"
            ).decode("utf-8").splitlines()
            if line.strip()
        ]

    expected_run = {
        "run_status": "FORMAL_TRAINING_COMPLETED",
        "diagnostic_only": True,
        "promotion_eligible": False,
        "formal_training_seed": 17,
        "data_seed": 17,
        "parent_policy_id": "PILOT_DISTILLED_PI1",
        "parent_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER,
        "parent_final_trainable_parameter_sha256": (
            EXPECTED_PARENT_PARAMETER
        ),
        "trainer_native_dataset_sha256": EXPECTED_DATASET_SHA,
        "research_planner_training_plan_domain_sha256": (
            EXPECTED_PLAN_DOMAIN
        ),
        "optimizer_step_count": 3,
        "dataset_pass_count": 1,
        "target_loss_token_count": 151,
        "all_losses_finite": True,
        "all_grad_norms_finite": True,
        "checkpoint_rule": "FINAL_STEP_ONLY",
        "resume_from_checkpoint_used": False,
        "early_stopping_used": False,
        "within_training_evaluation_used": False,
        "intermediate_scientific_checkpoint_used": False,
    }
    observed_run = {
        key: run.get(key)
        for key in expected_run
    }
    if observed_run != expected_run:
        raise AuditError(
            "FORMAL_RUN_CONTRACT_CHANGED:"
            + repr(observed_run)
            + ":"
            + repr(expected_run)
        )

    expected_terminal = {
        "terminal_status": "ACCEPTED",
        "model_training_executed": True,
        "model_training_execution_status": "COMPLETED",
        "authorization_sha256": EXPECTED_AUTHORIZATION,
    }
    observed_terminal = {
        key: terminal.get(key)
        for key in expected_terminal
    }
    if observed_terminal != expected_terminal:
        raise AuditError(
            "TERMINAL_RECEIPT_CONTRACT_CHANGED:"
            + repr(observed_terminal)
        )
    if terminal.get("started_from_receipt_sha256") != (
        started.get("stage_receipt_sha256")
    ):
        raise AuditError(
            "TRAINING_RECEIPT_CHAIN_BROKEN"
        )
    if terminal.get("output_artifact_index_sha256") != (
        output_index.get("artifact_index_sha256")
    ):
        raise AuditError(
            "TRAINING_OUTPUT_INDEX_BINDING_BROKEN"
        )

    if len(ledger) != 3:
        raise AuditError(
            f"TRAINING_LEDGER_ROW_COUNT_CHANGED:{len(ledger)}"
        )
    expected_groups = (
        ([8, 6, 9, 7], 43),
        ([5, 1, 0, 10], 53),
        ([2, 4, 3, 11], 55),
    )
    for row, (indices, tokens) in zip(
        ledger,
        expected_groups,
        strict=True,
    ):
        if row.get("example_indices") != indices:
            raise AuditError(
                "TRAINING_LEDGER_EXAMPLE_GROUP_CHANGED"
            )
        if row.get("target_loss_tokens") != tokens:
            raise AuditError(
                "TRAINING_LEDGER_TOKEN_GROUP_CHANGED"
            )
        if row.get("loss_is_finite") is not True:
            raise AuditError("TRAINING_LEDGER_NONFINITE_LOSS")
        if row.get("grad_norm_is_finite") is not True:
            raise AuditError("TRAINING_LEDGER_NONFINITE_GRAD")

    candidate = adapter.get("adapter_bundle_sha256")
    if candidate != EXPECTED_CANDIDATE_ADAPTER:
        raise AuditError(
            f"CANDIDATE_ADAPTER_SHA_CHANGED:{candidate}"
        )
    if candidate == EXPECTED_PARENT_ADAPTER:
        raise AuditError("CANDIDATE_EQUALS_PARENT")

    if review.get("review_status") != (
        "READY_FOR_FORMAL_TRAINING_RESULT_AUDIT"
    ):
        raise AuditError(
            f"REVIEW_STATUS_CHANGED:{review.get('review_status')}"
        )
    if review.get("candidate_adapter_bundle_sha256") != (
        EXPECTED_CANDIDATE_ADAPTER
    ):
        raise AuditError(
            "REVIEW_CANDIDATE_ADAPTER_BINDING_CHANGED"
        )
    if review.get("evaluation_executed") is not False:
        raise AuditError("REVIEW_CLAIMS_EVALUATION_EXECUTED")
    if review.get("promotion_decision_executed") is not False:
        raise AuditError("REVIEW_CLAIMS_PROMOTION_EXECUTED")

    adapter_file = (
        TRAIN_ROOT
        / "adapter"
        / "adapter_model.safetensors"
    )
    if not adapter_file.is_file() or adapter_file.stat().st_size <= 0:
        raise AuditError("CANDIDATE_ADAPTER_FILE_INVALID")

    return {
        "recovered_zip_path": str(RECOVERED_ZIP),
        "recovered_zip_sha256": sha256_file(
            RECOVERED_ZIP
        ),
        "recovered_zip_size_bytes": (
            RECOVERED_ZIP.stat().st_size
        ),
        "recovered_zip_member_count": len(
            REQUIRED_ZIP_MEMBERS
        ),
        "candidate_adapter_bundle_sha256": candidate,
        "candidate_adapter_file_path": str(
            adapter_file
        ),
        "candidate_adapter_file_sha256": sha256_file(
            adapter_file
        ),
        "candidate_adapter_file_size_bytes": (
            adapter_file.stat().st_size
        ),
        "training_ledger_rows": ledger,
        "formal_run_manifest": run,
        "terminal_stage_receipt": terminal,
        "review_manifest": review,
    }


def git_info(root: Path) -> dict:
    def run(*args: str) -> tuple[int, str, str]:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
        )
        return (
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )

    rc, head, err = run("rev-parse", "HEAD")
    if rc != 0:
        return {
            "root": str(root),
            "git_error": err,
        }
    _, branch, _ = run(
        "branch",
        "--show-current",
    )
    _, status, _ = run(
        "status",
        "--short",
        "--untracked-files=no",
    )
    return {
        "root": str(root),
        "head": head,
        "branch": branch,
        "tracked_status_short": status,
    }


def function_index(path: Path) -> list[dict]:
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return []
    rows = []
    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            rows.append(
                {
                    "name": node.name,
                    "kind": (
                        "class"
                        if isinstance(node, ast.ClassDef)
                        else "function"
                    ),
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        None,
                    ),
                }
            )
    return rows


def scan_repo(root: Path) -> dict:
    matches = []
    if not root.is_dir():
        return {
            "root": str(root),
            "exists": False,
            "matches": [],
        }

    for dirname in (
        "src",
        "scripts",
        "configs",
        "docs",
        "tests",
    ):
        scan_root = root / dirname
        if not scan_root.is_dir():
            continue

        for path in sorted(scan_root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                continue

            rel = path.relative_to(root).as_posix()
            filename_hit = bool(
                FILENAME_RE.search(path.name)
            )

            try:
                text = path.read_text(
                    encoding="utf-8"
                )
            except Exception:
                continue

            line_hits = []
            for number, line in enumerate(
                text.splitlines(),
                start=1,
            ):
                if SEARCH_RE.search(line):
                    line_hits.append(
                        {
                            "line": number,
                            "text": line[:500],
                        }
                    )
                    if (
                        len(line_hits)
                        >= MAX_MATCHES_PER_FILE
                    ):
                        break

            if filename_hit or line_hits:
                matches.append(
                    {
                        "path": rel,
                        "sha256": sha256_file(path),
                        "size_bytes": path.stat().st_size,
                        "filename_hit": filename_hit,
                        "line_hits": line_hits,
                        "symbols": function_index(path),
                    }
                )

    return {
        "root": str(root),
        "exists": True,
        "git": git_info(root),
        "match_count": len(matches),
        "matches": matches,
    }


def classify_evaluator_candidates(
    repo_scans: list[dict],
) -> list[dict]:
    candidates = []
    for scan in repo_scans:
        if not scan.get("exists"):
            continue
        for row in scan["matches"]:
            path = row["path"].lower()
            combined = (
                row["path"]
                + "\n"
                + "\n".join(
                    hit["text"]
                    for hit in row["line_hits"]
                )
            ).lower()

            score = 0
            reasons = []

            rules = (
                (r"run_e1_evaluator", 5, "E1_RUNNER"),
                (r"episode_evaluator", 5, "EPISODE_EVALUATOR"),
                (r"harness.?off", 3, "HARNESS_OFF"),
                (r"memory.?off", 3, "MEMORY_OFF"),
                (r"policy_runtime_manifest", 2, "POLICY_RUNTIME_IDENTITY"),
                (r"policy_client", 2, "POLICY_CLIENT"),
                (r"run.?schedule", 2, "RUN_SCHEDULE"),
                (r"adapter", 1, "ADAPTER_SUPPORT"),
                (r"checkpoint", 1, "CHECKPOINT_SUPPORT"),
                (r"valid_unseen", 1, "VALID_UNSEEN"),
            )
            for pattern, weight, label in rules:
                if re.search(pattern, combined):
                    score += weight
                    reasons.append(label)

            if score >= 4:
                candidates.append(
                    {
                        "repo_root": scan["root"],
                        "path": row["path"],
                        "sha256": row["sha256"],
                        "score": score,
                        "reasons": sorted(set(reasons)),
                        "symbols": row["symbols"],
                        "selected_for_reuse_review": False,
                    }
                )

    candidates.sort(
        key=lambda row: (
            -row["score"],
            row["repo_root"],
            row["path"],
        )
    )
    return candidates[:100]


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise AuditError(
            f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}"
        )
    if OUTPUT_ZIP.exists():
        raise AuditError(
            f"OUTPUT_ZIP_ALREADY_EXISTS:{OUTPUT_ZIP}"
        )

    training = audit_recovered_zip()

    repo_scans = [
        scan_repo(root)
        for root in REPO_CANDIDATES
    ]
    evaluator_candidates = (
        classify_evaluator_candidates(
            repo_scans
        )
    )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)

    formal_audit = {
        "schema_id": "HUMAN_T2_FORMAL_TRAINING_RESULT_AUDIT_V1",
        "schema_version": 1,
        "audit_status": "PASS",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "profile_id": (
            "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC_PROFILE_V1"
        ),
        "scientific_role": "DIAGNOSTIC_T2_CONTINUATION",
        "parent_policy_id": "PILOT_DISTILLED_PI1",
        "parent_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER,
        "parent_final_trainable_parameter_sha256": (
            EXPECTED_PARENT_PARAMETER
        ),
        "candidate_adapter_bundle_sha256": (
            EXPECTED_CANDIDATE_ADAPTER
        ),
        "candidate_adapter_file_sha256": training[
            "candidate_adapter_file_sha256"
        ],
        "candidate_adapter_file_size_bytes": training[
            "candidate_adapter_file_size_bytes"
        ],
        "recovered_training_review_zip_sha256": training[
            "recovered_zip_sha256"
        ],
        "optimizer_step_count": 3,
        "target_loss_token_count": 151,
        "training_seed": 17,
        "data_seed": 17,
        "diagnostic_only": True,
        "promotion_eligible": False,
        "evaluation_executed": False,
        "promotion_decision_executed": False,
        "audit_sha256": "",
    }
    formal_audit["audit_sha256"] = domain_sha256(
        formal_audit["schema_id"],
        formal_audit,
        sha_field="audit_sha256",
    )

    candidate_policy = {
        "schema_id": "POLICY_ARTIFACT_NODE_CANDIDATE_V1",
        "schema_version": 1,
        "policy_id": "PI2_HUMAN_T2_DIAGNOSTIC_CANDIDATE",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "parent_policy_id": "PILOT_DISTILLED_PI1",
        "parent_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER,
        "adapter_bundle_sha256": EXPECTED_CANDIDATE_ADAPTER,
        "adapter_file_path": training[
            "candidate_adapter_file_path"
        ],
        "adapter_file_sha256": training[
            "candidate_adapter_file_sha256"
        ],
        "adapter_file_size_bytes": training[
            "candidate_adapter_file_size_bytes"
        ],
        "training_result_audit_sha256": formal_audit[
            "audit_sha256"
        ],
        "diagnostic_only": True,
        "promotion_eligible": False,
        "off_off_evaluation_status": "NOT_EXECUTED",
        "disposition_status": "UNASSIGNED_PENDING_EVALUATION",
        "policy_artifact_candidate_sha256": "",
    }
    candidate_policy[
        "policy_artifact_candidate_sha256"
    ] = domain_sha256(
        candidate_policy["schema_id"],
        candidate_policy,
        sha_field="policy_artifact_candidate_sha256",
    )

    census = {
        "schema_id": "OFF_OFF_EVALUATOR_REUSE_CENSUS_V1",
        "schema_version": 1,
        "status": "CANDIDATES_DISCOVERED_REVIEW_REQUIRED",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "repo_scans": repo_scans,
        "evaluator_candidates": evaluator_candidates,
        "candidate_count": len(evaluator_candidates),
        "automatic_reuse_decision": False,
        "alworld_execution_count": 0,
        "model_execution_count": 0,
        "evaluation_execution_count": 0,
    }

    handoff = {
        "schema_id": "OFF_OFF_EVALUATION_HANDOFF_DRAFT_V1",
        "schema_version": 1,
        "status": "PENDING_EVALUATOR_BINDING_REVIEW",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "parent_policy_id": "PILOT_DISTILLED_PI1",
        "candidate_policy_id": candidate_policy[
            "policy_id"
        ],
        "parent_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER,
        "candidate_adapter_bundle_sha256": EXPECTED_CANDIDATE_ADAPTER,
        "training_result_audit_sha256": formal_audit[
            "audit_sha256"
        ],
        "candidate_policy_artifact_sha256": candidate_policy[
            "policy_artifact_candidate_sha256"
        ],
        "required_conditions": {
            "parent_memory": "OFF",
            "parent_harness": "OFF",
            "candidate_memory": "OFF",
            "candidate_harness": "OFF",
            "same_task_manifest_required": True,
            "same_task_order_required": True,
            "same_budget_required": True,
            "same_parser_required": True,
            "same_environment_runtime_required": True,
            "same_success_definition_required": True,
            "model_identity_may_differ": True,
        },
        "evaluation_execution_authorized": False,
        "selected_evaluator_binding": None,
        "next_gate": "OFF_OFF_EVALUATOR_REUSE_BINDING_REVIEW",
    }

    write_json_create_once(
        OUTPUT_ROOT
        / "HUMAN_T2_FORMAL_TRAINING_RESULT_AUDIT_V1.json",
        formal_audit,
    )
    write_json_create_once(
        OUTPUT_ROOT
        / "POLICY_ARTIFACT_NODE_CANDIDATE_V1.json",
        candidate_policy,
    )
    write_json_create_once(
        OUTPUT_ROOT
        / "OFF_OFF_EVALUATOR_REUSE_CENSUS_V1.json",
        census,
    )
    write_json_create_once(
        OUTPUT_ROOT
        / "OFF_OFF_EVALUATION_HANDOFF_DRAFT_V1.json",
        handoff,
    )

    review_manifest = {
        "schema_id": (
            "HUMAN_T2_TRAINING_RESULT_AUDIT_OFFOFF_REUSE_"
            "CENSUS_REVIEW_MANIFEST_V1"
        ),
        "schema_version": 1,
        "review_status": (
            "READY_FOR_OFF_OFF_EVALUATOR_REUSE_BINDING_REVIEW"
        ),
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "training_result_audit_sha256": formal_audit[
            "audit_sha256"
        ],
        "candidate_policy_artifact_sha256": candidate_policy[
            "policy_artifact_candidate_sha256"
        ],
        "candidate_adapter_bundle_sha256": EXPECTED_CANDIDATE_ADAPTER,
        "evaluator_candidate_count": len(
            evaluator_candidates
        ),
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
        "files": [],
    }

    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            {
                "path": str(
                    path.relative_to(OUTPUT_ROOT)
                ),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    review_manifest["files"] = files

    write_json_create_once(
        OUTPUT_ROOT / "REVIEW_MANIFEST_V1.json",
        review_manifest,
    )

    with zipfile.ZipFile(
        OUTPUT_ZIP,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(
            OUTPUT_ROOT.rglob("*")
        ):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(
                        OUTPUT_ROOT
                    ).as_posix(),
                )

    if not zipfile.is_zipfile(OUTPUT_ZIP):
        raise AuditError("OUTPUT_ZIP_MAGIC_INVALID")
    with zipfile.ZipFile(
        OUTPUT_ZIP,
        "r",
    ) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise AuditError(
                f"OUTPUT_ZIP_CRC_FAILED:{bad}"
            )

    print("HUMAN_T2_FORMAL_TRAINING_RESULT_AUDIT_PASS")
    print(
        "CANDIDATE_ADAPTER_BUNDLE_SHA256="
        + EXPECTED_CANDIDATE_ADAPTER
    )
    print(
        "CANDIDATE_POLICY_ARTIFACT_SHA256="
        + candidate_policy[
            "policy_artifact_candidate_sha256"
        ]
    )
    print(
        "OFF_OFF_EVALUATOR_CANDIDATE_COUNT="
        + str(len(evaluator_candidates))
    )
    print("EVALUATION_EXECUTION_AUTHORIZED=false")
    print("EVALUATION_EXECUTION_COUNT=0")
    print("REVIEW_ZIP=" + str(OUTPUT_ZIP))
    print(
        "REVIEW_ZIP_SHA256="
        + sha256_file(OUTPUT_ZIP)
    )
    print(
        "NEXT_GATE=OFF_OFF_EVALUATOR_REUSE_BINDING_REVIEW"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
