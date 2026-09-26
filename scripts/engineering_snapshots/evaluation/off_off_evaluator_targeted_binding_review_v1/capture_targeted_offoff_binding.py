from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


HUMAN_WT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
    "pchsi-wt-human-reference-round-pi1-pi2-v1"
)
ROUND_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1"
)
PCHSI_ROOT = Path("/data/run01/scwb204/pchsi")
EVIDENCE_ROOTS = (
    Path("/data/home/scwb204/pchsi_evidence"),
    Path("/data/run01/scwb204/pchsi_evidence"),
    ROUND_ROOT,
    PCHSI_ROOT,
)

OUTPUT_PARENT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts"
)
OUTPUT_ROOT = OUTPUT_PARENT / (
    "off_off_evaluator_targeted_binding_review_v1_output"
)
OUTPUT_ZIP = OUTPUT_PARENT / (
    "OFF_OFF_EVALUATOR_TARGETED_BINDING_REVIEW_V1.zip"
)

SOURCE_PATHS = (
    "scripts/evaluation/run_e1_evaluator.py",
    "scripts/evaluation/build_policy_runtime_manifest.py",
    "scripts/evaluation/validate_e1_vllm_readiness.py",
    "src/pchsi/evaluation/episode_evaluator.py",
    "src/pchsi/evaluation/result_audit.py",
    "src/pchsi/evaluation/run_schedule.py",
    "src/pchsi/evaluation/run_resolution.py",
    "src/pchsi/evaluation/task_manifest.py",
    "src/pchsi/evaluation/policy_client.py",
    "src/pchsi/evaluation/policy_runtime_manifest.py",
    "src/pchsi/evaluation/policy_execution_profile.py",
    "src/pchsi/evaluation/condition_execution_binding.py",
    "src/pchsi/evaluation/condition_run_schedule.py",
    "src/pchsi/evaluation/select_execution_identity.py",
    "src/pchsi/evaluation/select_policy_runtime.py",
    "src/pchsi/evaluation/select_result_audit.py",
    "src/pchsi/evaluation/artifact_publisher.py",
    "src/pchsi/evaluation/attempt_state.py",
    "src/pchsi/evaluation/episode_artifact.py",
    "data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl",
    "configs/protocols/split_and_access_v1.json",
)

TEST_PATHS = (
    "tests/evaluation/test_episode_evaluator.py",
    "tests/evaluation/test_result_audit.py",
    "tests/evaluation/test_run_schedule.py",
    "tests/evaluation/test_policy_runtime_manifest.py",
    "tests/evaluation/test_policy_execution_profile.py",
    "tests/evaluation/test_condition_execution_binding.py",
    "tests/evaluation/test_condition_run_schedule.py",
    "tests/evaluation/test_p4_select_execution_compat_v1.py",
)

ARTIFACT_NAME_PATTERNS = (
    "e1_policy_runtime_manifest",
    "policy_runtime_manifest",
    "select_policy_runtime",
    "select_server_runtime",
    "condition_run_schedule",
    "run_schedule",
    "task_access_manifest",
    "policy_condition_manifest",
    "checkpoint_set_manifest",
    "adapter_artifact_manifest",
    "formal_run_manifest",
    "readiness_summary",
)

MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_ARTIFACT_MATCHES = 300


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(HUMAN_WT), *args],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise Stop(
            "GIT_FAILED:"
            + " ".join(args)
            + ":"
            + result.stderr.strip()
        )
    return result.stdout.strip()


def copy_file(source: Path, destination: Path) -> dict:
    if not source.is_file() or source.is_symlink():
        raise Stop(f"SOURCE_INVALID:{source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "source_path": str(source),
        "bundle_path": str(destination.relative_to(OUTPUT_ROOT)),
        "sha256": sha256_file(source),
        "size_bytes": source.stat().st_size,
    }


def symbol_index(path: Path) -> list[dict]:
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
                    "end_line": getattr(node, "end_lineno", None),
                }
            )
    return rows


def source_capture() -> tuple[list[dict], list[dict]]:
    files = []
    symbols = []

    for rel in SOURCE_PATHS:
        source = HUMAN_WT / rel
        if not source.is_file():
            files.append(
                {
                    "source_path": str(source),
                    "bundle_path": None,
                    "missing": True,
                }
            )
            continue
        destination = OUTPUT_ROOT / "sources" / rel
        row = copy_file(source, destination)
        files.append(row)
        symbols.append(
            {
                "path": rel,
                "sha256": row["sha256"],
                "symbols": symbol_index(source),
            }
        )

    for rel in TEST_PATHS:
        source = HUMAN_WT / rel
        if not source.is_file():
            files.append(
                {
                    "source_path": str(source),
                    "bundle_path": None,
                    "missing": True,
                }
            )
            continue
        destination = OUTPUT_ROOT / "tests" / rel
        files.append(copy_file(source, destination))

    return files, symbols


def find_materialized_artifacts() -> list[dict]:
    rows = []
    seen = set()

    for root in EVIDENCE_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*"):
            if len(rows) >= MAX_ARTIFACT_MATCHES:
                return rows
            if not path.is_file() or path.is_symlink():
                continue
            if path.stat().st_size > MAX_ARTIFACT_BYTES:
                continue

            name = path.name.lower()
            if not any(
                pattern in name
                for pattern in ARTIFACT_NAME_PATTERNS
            ):
                continue

            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)

            entry = {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }

            if path.suffix == ".json":
                try:
                    value = json.loads(
                        path.read_text(encoding="utf-8")
                    )
                except Exception as exc:
                    entry["json_error"] = repr(exc)
                else:
                    if isinstance(value, dict):
                        interesting = {}
                        wanted = {
                            "schema_id",
                            "policy_id",
                            "policy_condition_id",
                            "served_model_name",
                            "model_repository",
                            "model_revision",
                            "tokenizer_revision",
                            "adapter_sha256",
                            "adapter_bundle_sha256",
                            "checkpoint_set_sha256",
                            "task_manifest_sha256",
                            "task_access_manifest_sha256",
                            "condition_run_schedule_sha256",
                            "policy_runtime_manifest_sha256",
                            "server_runtime_manifest_sha256",
                            "seed",
                            "replicate_seeds",
                            "cell_count",
                            "task_count",
                        }

                        def walk(obj, prefix="$"):
                            if isinstance(obj, dict):
                                for key, child in obj.items():
                                    child_prefix = (
                                        prefix + "." + str(key)
                                    )
                                    if key in wanted and isinstance(
                                        child,
                                        (
                                            str,
                                            int,
                                            float,
                                            bool,
                                            type(None),
                                            list,
                                        ),
                                    ):
                                        interesting[
                                            child_prefix
                                        ] = child
                                    walk(child, child_prefix)
                            elif isinstance(obj, list):
                                for index, child in enumerate(obj):
                                    walk(
                                        child,
                                        f"{prefix}[{index}]",
                                    )

                        walk(value)
                        entry["interesting_fields"] = interesting

            rows.append(entry)

    return rows


def exact_keyword_context() -> list[dict]:
    terms = (
        "PILOT_DISTILLED_PI1",
        "E1_POLICY_RUNTIME_MANIFEST_V1",
        "SELECT_POLICY_RUNTIME",
        "select_policy_runtime",
        "adapter_bundle_sha256",
        "checkpoint",
        "Memory OFF",
        "Harness OFF",
        "670",
        "17, 31, 47, 73, 101",
    )
    rows = []

    for rel in SOURCE_PATHS + TEST_PATHS:
        path = HUMAN_WT / rel
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        hits = []
        for number, line in enumerate(lines, start=1):
            if any(term.lower() in line.lower() for term in terms):
                hits.append(
                    {
                        "line": number,
                        "text": line[:600],
                    }
                )
                if len(hits) >= 80:
                    break

        if hits:
            rows.append(
                {
                    "path": rel,
                    "sha256": sha256_file(path),
                    "hits": hits,
                }
            )

    return rows


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise Stop(f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}")
    if OUTPUT_ZIP.exists():
        raise Stop(f"OUTPUT_ZIP_ALREADY_EXISTS:{OUTPUT_ZIP}")
    if not HUMAN_WT.is_dir():
        raise Stop(f"HUMAN_WT_MISSING:{HUMAN_WT}")

    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    status = git("status", "--short", "--untracked-files=no")
    if status:
        raise Stop("HUMAN_WT_TRACKED_DIRTY:" + repr(status))

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)

    files, symbols = source_capture()
    artifacts = find_materialized_artifacts()
    contexts = exact_keyword_context()

    repo = {
        "schema_id": "OFF_OFF_EVALUATOR_TARGETED_REPO_IDENTITY_V1",
        "schema_version": 1,
        "root": str(HUMAN_WT),
        "branch": branch,
        "head": head,
        "tracked_status_short": status,
    }

    conclusion = {
        "schema_id": "OFF_OFF_EVALUATOR_BINDING_REVIEW_INPUT_V1",
        "schema_version": 1,
        "status": "READY_FOR_SOURCE_LEVEL_BINDING_REVIEW",
        "canonical_evaluator_core_candidate": (
            "src/pchsi/evaluation/episode_evaluator.py"
        ),
        "canonical_cli_candidate": (
            "scripts/evaluation/run_e1_evaluator.py"
        ),
        "canonical_result_audit_candidate": (
            "src/pchsi/evaluation/result_audit.py"
        ),
        "canonical_schedule_candidate": (
            "src/pchsi/evaluation/run_schedule.py"
        ),
        "policy_binding_candidates": [
            "src/pchsi/evaluation/policy_runtime_manifest.py",
            "src/pchsi/evaluation/policy_execution_profile.py",
            "src/pchsi/evaluation/condition_execution_binding.py",
            "src/pchsi/evaluation/condition_run_schedule.py",
            "src/pchsi/evaluation/select_execution_identity.py",
            "src/pchsi/evaluation/select_policy_runtime.py",
            "src/pchsi/evaluation/select_result_audit.py",
        ],
        "task_manifest_candidate": (
            "data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl"
        ),
        "candidate_adapter_bundle_sha256": (
            "908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e"
        ),
        "parent_adapter_bundle_sha256": (
            "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"
        ),
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
    }

    for name, value in (
        ("REPOSITORY_IDENTITY_V1.json", repo),
        ("SOURCE_CAPTURE_MANIFEST_V1.json", {
            "schema_id": "OFF_OFF_EVALUATOR_SOURCE_CAPTURE_MANIFEST_V1",
            "schema_version": 1,
            "files": files,
        }),
        ("SYMBOL_INDEX_V1.json", {
            "schema_id": "OFF_OFF_EVALUATOR_SYMBOL_INDEX_V1",
            "schema_version": 1,
            "symbols": symbols,
        }),
        ("MATERIALIZED_ARTIFACT_CANDIDATES_V1.json", {
            "schema_id": "OFF_OFF_MATERIALIZED_ARTIFACT_CANDIDATES_V1",
            "schema_version": 1,
            "artifacts": artifacts,
            "artifact_count": len(artifacts),
        }),
        ("KEYWORD_CONTEXT_V1.json", {
            "schema_id": "OFF_OFF_EVALUATOR_KEYWORD_CONTEXT_V1",
            "schema_version": 1,
            "contexts": contexts,
        }),
        ("BINDING_REVIEW_INPUT_V1.json", conclusion),
    ):
        (OUTPUT_ROOT / name).write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    with zipfile.ZipFile(
        OUTPUT_ZIP,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(OUTPUT_ROOT).as_posix(),
                )

    if not zipfile.is_zipfile(OUTPUT_ZIP):
        raise Stop("OUTPUT_ZIP_INVALID")
    with zipfile.ZipFile(OUTPUT_ZIP, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stop(f"OUTPUT_ZIP_BAD_MEMBER:{bad}")

    print("OFF_OFF_EVALUATOR_TARGETED_BINDING_CAPTURE_PASS")
    print("REPOSITORY_HEAD=" + head)
    print("REPOSITORY_BRANCH=" + branch)
    print("SOURCE_FILE_COUNT=" + str(len(files)))
    print(
        "MATERIALIZED_ARTIFACT_CANDIDATE_COUNT="
        + str(len(artifacts))
    )
    print("EVALUATION_EXECUTION_AUTHORIZED=false")
    print("EVALUATION_EXECUTION_COUNT=0")
    print("REVIEW_ZIP=" + str(OUTPUT_ZIP))
    print("REVIEW_ZIP_SHA256=" + sha256_file(OUTPUT_ZIP))
    print("NEXT_GATE=OFF_OFF_EVALUATOR_SOURCE_LEVEL_BINDING_REVIEW")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stop as exc:
        raise SystemExit("STOP=" + str(exc))
