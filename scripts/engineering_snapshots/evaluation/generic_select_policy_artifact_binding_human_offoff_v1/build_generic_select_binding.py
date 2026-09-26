from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

EXPECTED_HEAD = "daef26b9cde45182ada534d96335da3ea451f12f"
SOURCE_WT = Path("/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-human-reference-round-pi1-pi2-v1")
TARGET_WT = Path("/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-generic-select-policy-binding-human-offoff-v1")
PACKAGE_ROOT = Path(__file__).resolve().parent
PYTHON = Path("/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python")
OUTPUT_PARENT = Path("/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts")
OUTPUT_ROOT = OUTPUT_PARENT / "generic_select_policy_artifact_binding_human_offoff_v1_review"
OUTPUT_ZIP = OUTPUT_PARENT / "GENERIC_SELECT_POLICY_ARTIFACT_BINDING_HUMAN_OFFOFF_REVIEW_V1.zip"
TASK_ACCESS = Path("/data/home/scwb204/pchsi_evidence/p1b_materialized_access_v1/task_access_manifest.json")
EXPECTED_TASK_ACCESS_SHA256 = "5b8859a50478601cc054423af88fb57f5c31d95b96aeb67ab528987274eb9718"
PARENT_ADAPTER = "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"
CANDIDATE_ADAPTER = "908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e"
CANDIDATE_LOGICAL = "P4-R2-HUMAN-T2-DIAGNOSTIC"


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, log: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("$ " + " ".join(args) + "\n\n" + result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    return result


def git(*args: str, cwd: Path = SOURCE_WT) -> str:
    result = run(["git", *args], cwd=cwd)
    if result.returncode != 0:
        raise Stop("GIT_FAILED:" + " ".join(args) + ":" + result.stderr.strip())
    return result.stdout.strip()


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise Stop(f"PATCH_ANCHOR_COUNT:{label}:{count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def create_isolated_worktree() -> None:
    if not SOURCE_WT.is_dir():
        raise Stop(f"SOURCE_WT_MISSING:{SOURCE_WT}")
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    status = git("status", "--short", "--untracked-files=no")
    if head != EXPECTED_HEAD:
        raise Stop(f"SOURCE_HEAD_CHANGED:{head}:{EXPECTED_HEAD}")
    if branch != "implementation/human-reference-round-pi1-pi2-v1":
        raise Stop(f"SOURCE_BRANCH_CHANGED:{branch}")
    if status:
        raise Stop("SOURCE_TRACKED_DIRTY:" + repr(status))
    if TARGET_WT.exists():
        raise Stop(f"TARGET_WT_ALREADY_EXISTS:{TARGET_WT}")
    result = run(
        ["git", "-C", str(SOURCE_WT), "worktree", "add", "--detach", str(TARGET_WT), EXPECTED_HEAD],
        cwd=SOURCE_WT,
    )
    if result.returncode != 0:
        raise Stop("WORKTREE_ADD_FAILED:" + result.stderr.strip())
    if git("rev-parse", "HEAD", cwd=TARGET_WT) != EXPECTED_HEAD:
        raise Stop("TARGET_HEAD_CHANGED")


def write_red_test() -> None:
    source = PACKAGE_ROOT / "payload/test_generic_select_policy_artifact_binding_v1.py"
    destination = TARGET_WT / "tests/evaluation/test_generic_select_policy_artifact_binding_v1.py"
    if destination.exists():
        raise Stop(f"RED_TEST_ALREADY_EXISTS:{destination}")
    shutil.copy2(source, destination)


def pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(TARGET_WT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_red() -> None:
    result = run(
        [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/evaluation/test_generic_select_policy_artifact_binding_v1.py"],
        cwd=TARGET_WT,
        env=pytest_env(),
        log=OUTPUT_ROOT / "logs/10_red.log",
    )
    if result.returncode == 0:
        raise Stop("TDD_RED_UNEXPECTEDLY_PASSED")
    combined = result.stdout + "\n" + result.stderr
    expected = (
        "LoRA registration logical condition mismatch",
        "exactly three frozen pi1 LoRAs are required",
        "unknown SELECT logical condition",
    )
    if not any(x in combined for x in expected):
        raise Stop("TDD_RED_FAILED_FOR_UNEXPECTED_REASON")


def patch_schema_files() -> None:
    server_path = TARGET_WT / "configs/evaluation/schemas/select_server_runtime_manifest_v1.json"
    policy_path = TARGET_WT / "configs/evaluation/schemas/select_policy_runtime_manifest_v1.json"

    server = json.loads(server_path.read_text(encoding="utf-8"))
    registry = server["properties"]["static_lora_registry"]
    logical = registry["items"]["properties"]["logical_condition_id"]
    if logical.get("const") != "P4-R1-Q2-BAD":
        raise Stop("SERVER_SCHEMA_LOGICAL_CONST_CHANGED")
    logical.pop("const")
    logical["minLength"] = 1
    logical["pattern"] = "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    if registry.get("minItems") != 3 or registry.get("maxItems") != 3:
        raise Stop("SERVER_SCHEMA_REGISTRY_CARDINALITY_CHANGED")
    registry["minItems"] = 1
    registry.pop("maxItems")
    server_path.write_text(json.dumps(server, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    logical = policy["properties"]["logical_condition_id"]
    if logical.get("enum") != ["P4-R0-PI0", "P4-R1-Q2-BAD"]:
        raise Stop("POLICY_SCHEMA_LOGICAL_ENUM_CHANGED")
    logical.pop("enum")
    logical["minLength"] = 1
    logical["pattern"] = "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def patch_select_policy_runtime() -> None:
    path = TARGET_WT / "src/pchsi/evaluation/select_policy_runtime.py"
    replace_once(
        path,
        """        if (\n            self.logical_condition_id\n            != PI1_LOGICAL_CONDITION_ID\n        ):\n            raise ValueError(\n                \"LoRA registration logical condition mismatch\"\n            )\n""",
        """        _text(\n            \"logical_condition_id\",\n            self.logical_condition_id,\n        )\n\n        if (\n            self.logical_condition_id\n            == PI0_CONDITION_ID\n        ):\n            raise ValueError(\n                \"LoRA registration may not use pi0 logical condition\"\n            )\n""",
        "registration_logical_condition",
    )
    replace_once(
        path,
        """        if (\n            len(\n                self.static_lora_registry\n            )\n            != 3\n        ):\n            raise ValueError(\n                \"exactly three frozen pi1 LoRAs are required\"\n            )\n""",
        """        if (\n            not self.static_lora_registry\n        ):\n            raise ValueError(\n                \"static_lora_registry must not be empty\"\n            )\n\n        if (\n            self.max_cpu_loras\n            < len(\n                self.static_lora_registry\n            )\n        ):\n            raise ValueError(\n                \"max_cpu_loras must cover the static LoRA registry\"\n            )\n""",
        "server_registry_cardinality",
    )
    replace_once(
        path,
        """        seeds = tuple(\n            item.training_seed\n            for item\n            in self.static_lora_registry\n        )\n\n        checkpoints = tuple(\n""",
        """        logical_seed_pairs = tuple(\n            (\n                item.logical_condition_id,\n                item.training_seed,\n            )\n            for item\n            in self.static_lora_registry\n        )\n\n        checkpoints = tuple(\n""",
        "seed_tuple_to_logical_seed_pairs",
    )
    replace_once(
        path,
        """        if (\n            len(set(seeds))\n            != len(seeds)\n        ):\n            raise ValueError(\n                \"duplicate training seed identity\"\n            )\n""",
        """        if (\n            len(set(logical_seed_pairs))\n            != len(logical_seed_pairs)\n        ):\n            raise ValueError(\n                \"duplicate logical-condition/training-seed identity\"\n            )\n""",
        "seed_uniqueness",
    )
    replace_once(
        path,
        """        elif (\n            self.logical_condition_id\n            == PI1_LOGICAL_CONDITION_ID\n        ):\n""",
        """        else:\n""",
        "policy_runtime_trained_branch",
    )
    replace_once(
        path,
        """        else:\n            raise ValueError(\n                \"unknown SELECT logical condition\"\n            )\n\n        _optional_text(\n""",
        """        _optional_text(\n""",
        "policy_runtime_unknown_branch",
    )


def patch_select_execution_identity() -> None:
    path = TARGET_WT / "src/pchsi/evaluation/select_execution_identity.py"
    replace_once(
        path,
        """        elif (\n            self.logical_condition_id\n            == PI1_LOGICAL_CONDITION_ID\n        ):\n""",
        """        else:\n""",
        "identity_trained_branch",
    )
    replace_once(
        path,
        """        else:\n            raise ValueError(\n                \"unknown SELECT logical condition\"\n            )\n\n\n@dataclass(\n""",
        """\n\n@dataclass(\n""",
        "identity_unknown_branch",
    )
    replace_once(
        path,
        """        if (\n            policy_runtime.logical_condition_id\n            != PI1_LOGICAL_CONDITION_ID\n        ):\n            raise ValueError(\n                \"pi1 logical identity mismatch\"\n            )\n""",
        """        if (\n            policy_runtime.logical_condition_id\n            == PI0_CONDITION_ID\n        ):\n            raise ValueError(\n                \"trained SELECT logical identity may not be pi0\"\n            )\n""",
        "bind_trained_logical_identity",
    )
    replace_once(
        path,
        """    policy_version = (\n        \"pi0\"\n        if identity.logical_condition_id\n        == PI0_CONDITION_ID\n        else \"PI1_BAD\"\n    )\n""",
        """    policy_version = (\n        \"pi0\"\n        if identity.logical_condition_id\n        == PI0_CONDITION_ID\n        else (\n            \"PI1_BAD\"\n            if identity.logical_condition_id\n            == PI1_LOGICAL_CONDITION_ID\n            else identity.logical_condition_id\n        )\n    )\n""",
        "profile_policy_version",
    )


def patch_select_result_audit() -> None:
    path = TARGET_WT / "src/pchsi/evaluation/select_result_audit.py"
    replace_once(
        path,
        """        if (\n            policy_runtime.logical_condition_id\n            != PI1_LOGICAL_CONDITION_ID\n        ):\n            raise ValueError(\n                \"SELECT pi1 logical identity mismatch\"\n            )\n""",
        """        if (\n            policy_runtime.logical_condition_id\n            == PI0_CONDITION_ID\n        ):\n            raise ValueError(\n                \"SELECT trained LoRA may not use pi0 logical identity\"\n            )\n""",
        "result_audit_trained_logical_identity",
    )


def apply_green_patch() -> None:
    patch_schema_files()
    patch_select_policy_runtime()
    patch_select_execution_identity()
    patch_select_result_audit()


def run_green_and_regression() -> None:
    commands = [
        ("20_green_focused.log", [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/evaluation/test_generic_select_policy_artifact_binding_v1.py"]),
        ("30_legacy_select_regression.log", [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/evaluation/test_p4_select_execution_compat_v1.py"]),
        ("40_evaluation_suite.log", [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/evaluation"]),
    ]
    for filename, args in commands:
        result = run(args, cwd=TARGET_WT, env=pytest_env(), log=OUTPUT_ROOT / "logs" / filename)
        if result.returncode != 0:
            raise Stop("GREEN_OR_REGRESSION_FAILED:" + filename)


def task_access_census() -> dict:
    if not TASK_ACCESS.is_file() or TASK_ACCESS.is_symlink():
        raise Stop(f"TASK_ACCESS_INVALID:{TASK_ACCESS}")
    observed_sha = sha256_file(TASK_ACCESS)
    if observed_sha != EXPECTED_TASK_ACCESS_SHA256:
        raise Stop("TASK_ACCESS_SHA_CHANGED:" + observed_sha)
    value = json.loads(TASK_ACCESS.read_text(encoding="utf-8"))
    records = value.get("records")
    if not isinstance(records, list):
        raise Stop("TASK_ACCESS_RECORDS_INVALID")
    counts = Counter()
    permission_counts = Counter()
    for row in records:
        if not isinstance(row, dict):
            raise Stop("TASK_ACCESS_ROW_INVALID")
        access = row.get("access_class")
        if not isinstance(access, str):
            raise Stop("TASK_ACCESS_CLASS_INVALID")
        counts[access] += 1
        if row.get("select_evaluation_permitted") is True:
            permission_counts["select_evaluation_permitted"] += 1
        if row.get("confirmatory_permitted") is True:
            permission_counts["confirmatory_permitted"] += 1
        if row.get("training_permitted") is True:
            permission_counts["training_permitted"] += 1
    sys.path.insert(0, str(TARGET_WT / "src"))
    from pchsi.evaluation.run_schedule import REPLICATE_SEEDS
    select_count = counts.get("SELECT_SUMMARY_ONLY", 0)
    return {
        "schema_id": "HUMAN_OFFOFF_TASK_ACCESS_CLASS_CENSUS_V1",
        "schema_version": 1,
        "task_access_manifest_path": str(TASK_ACCESS),
        "task_access_manifest_sha256": observed_sha,
        "record_count": len(records),
        "access_class_counts": dict(sorted(counts.items())),
        "permission_counts": dict(sorted(permission_counts.items())),
        "frozen_e1_replicate_seeds": list(REPLICATE_SEEDS),
        "select_summary_only_task_count": select_count,
        "draft_select_5seed_cell_count": select_count * len(REPLICATE_SEEDS),
        "schedule_materialized": False,
        "evaluation_executed": False,
    }


def build_review() -> None:
    census = task_access_census()
    diff = run(["git", "diff", "--binary"], cwd=TARGET_WT)
    if diff.returncode != 0:
        raise Stop("GIT_DIFF_FAILED:" + diff.stderr.strip())
    status = git("status", "--short", cwd=TARGET_WT)
    if not status:
        raise Stop("TARGET_WORKTREE_HAS_NO_CHANGES")
    (OUTPUT_ROOT / "diff").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "diff/git_diff.patch").write_text(diff.stdout, encoding="utf-8")
    census_path = OUTPUT_ROOT / "TASK_ACCESS_CLASS_CENSUS_V1.json"
    census_path.write_text(json.dumps(census, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    fixed = {
        "schema_id": "GENERIC_SELECT_POLICY_ARTIFACT_BINDING_FIXED_HEAD_REVIEW_V1",
        "schema_version": 1,
        "source_worktree": str(SOURCE_WT),
        "target_worktree": str(TARGET_WT),
        "source_branch": "implementation/human-reference-round-pi1-pi2-v1",
        "source_head": EXPECTED_HEAD,
        "target_head": git("rev-parse", "HEAD", cwd=TARGET_WT),
        "target_detached": git("branch", "--show-current", cwd=TARGET_WT) == "",
        "target_status_short": status,
        "parent_adapter_bundle_sha256": PARENT_ADAPTER,
        "candidate_adapter_bundle_sha256": CANDIDATE_ADAPTER,
        "candidate_logical_condition_id": CANDIDATE_LOGICAL,
        "schema_ids_changed": False,
        "wire_fields_changed": False,
        "episode_evaluator_changed": False,
        "runtime_core_changed": False,
        "policy_client_changed": False,
        "condition_schedule_core_changed": False,
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
        "repository_commit_created": False,
        "repository_push_executed": False,
        "next_gate": "GENERIC_SELECT_BINDING_FIXED_HEAD_REVIEW_AND_TWIN_OFFOFF_BINDING_BUILD",
    }
    (OUTPUT_ROOT / "FIXED_HEAD_REVIEW_V1.json").write_text(json.dumps(fixed, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(PACKAGE_ROOT / "docs/DESIGN_V1.md", OUTPUT_ROOT / "DESIGN_V1.md")
    shutil.copy2(PACKAGE_ROOT / "docs/IMPLEMENTATION_PLAN_V1.md", OUTPUT_ROOT / "IMPLEMENTATION_PLAN_V1.md")
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(OUTPUT_ROOT)), "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    manifest = {
        "schema_id": "GENERIC_SELECT_POLICY_ARTIFACT_BINDING_HUMAN_OFFOFF_REVIEW_MANIFEST_V1",
        "schema_version": 1,
        "review_status": "READY_FOR_GENERIC_SELECT_BINDING_FIXED_HEAD_REVIEW",
        "source_head": EXPECTED_HEAD,
        "parent_adapter_bundle_sha256": PARENT_ADAPTER,
        "candidate_adapter_bundle_sha256": CANDIDATE_ADAPTER,
        "candidate_logical_condition_id": CANDIDATE_LOGICAL,
        "task_access_class_census_sha256": sha256_file(census_path),
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
        "repository_commit_created": False,
        "repository_push_executed": False,
        "files": files,
        "next_gate": "GENERIC_SELECT_BINDING_FIXED_HEAD_REVIEW_AND_TWIN_OFFOFF_BINDING_BUILD",
    }
    (OUTPUT_ROOT / "REVIEW_MANIFEST_V1.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if OUTPUT_ZIP.exists():
        raise Stop(f"OUTPUT_ZIP_ALREADY_EXISTS:{OUTPUT_ZIP}")
    with zipfile.ZipFile(OUTPUT_ZIP, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OUTPUT_ROOT).as_posix())
    if not zipfile.is_zipfile(OUTPUT_ZIP):
        raise Stop("OUTPUT_REVIEW_ZIP_INVALID")
    with zipfile.ZipFile(OUTPUT_ZIP, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stop(f"OUTPUT_REVIEW_ZIP_BAD_MEMBER:{bad}")
    print("GENERIC_SELECT_POLICY_ARTIFACT_BINDING_FIXED_HEAD_BUILD_PASS")
    print("TARGET_WORKTREE=" + str(TARGET_WT))
    print("TARGET_HEAD=" + EXPECTED_HEAD)
    print("TASK_ACCESS_RECORD_COUNT=" + str(census["record_count"]))
    for key, value in sorted(census["access_class_counts"].items()):
        print("TASK_ACCESS_CLASS_" + key + "=" + str(value))
    print("FROZEN_E1_REPLICATE_SEEDS=" + repr(census["frozen_e1_replicate_seeds"]))
    print("DRAFT_SELECT_5SEED_CELL_COUNT=" + str(census["draft_select_5seed_cell_count"]))
    print("EVALUATION_EXECUTION_AUTHORIZED=false")
    print("EVALUATION_EXECUTION_COUNT=0")
    print("REPOSITORY_COMMIT_CREATED=false")
    print("REPOSITORY_PUSH_EXECUTED=false")
    print("REVIEW_ZIP=" + str(OUTPUT_ZIP))
    print("REVIEW_ZIP_SHA256=" + sha256_file(OUTPUT_ZIP))
    print("NEXT_GATE=GENERIC_SELECT_BINDING_FIXED_HEAD_REVIEW_AND_TWIN_OFFOFF_BINDING_BUILD")


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise Stop(f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    create_isolated_worktree()
    write_red_test()
    run_red()
    apply_green_patch()
    run_green_and_regression()
    build_review()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stop as exc:
        raise SystemExit("STOP=" + str(exc))
