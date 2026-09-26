#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

REPO_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
    "phase-critical-harness-guided-self-improvement"
)
ROUND_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1"
)
OUTPUT_ROOT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "round_data_plane_reuse_census_strong_trace_v1_output"
)
PATTERNS_PATH = Path(__file__).resolve().with_name(
    "SEMANTIC_ROLE_PATTERNS_V1.json"
)

SCAN_DIRS = ["src", "scripts", "configs", "docs", "tests"]
MAX_TEXT_FILE = 12 * 1024 * 1024
MAX_MATCHES_PER_ROLE_PER_REF = 500


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise Stop(
            "GIT_COMMAND_FAILED:"
            + " ".join(args)
            + ":"
            + result.stderr.strip()
        )
    return result


def existing_refs() -> list[dict]:
    result = git(
        "for-each-ref",
        "--format=%(refname:short)\t%(objectname)\t%(objecttype)",
        "refs/heads",
        "refs/remotes",
    )
    refs = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        refs.append(
            {
                "ref": parts[0],
                "object": parts[1],
                "object_type": parts[2],
            }
        )
    head = git("rev-parse", "HEAD").stdout.strip()
    branch = git("branch", "--show-current").stdout.strip()
    return [
        {
            "ref": "WORKTREE_HEAD",
            "object": head,
            "object_type": "commit",
            "branch": branch,
        },
        *refs,
    ]


def target_refs(ref_index: list[dict]) -> list[str]:
    available = {row["ref"] for row in ref_index}
    preferred = [
        "main",
        "origin/main",
        "implementation/research-planner-bootstrap-teacher-local-v1",
        "design/generic-self-improvement-loop-v1",
    ]
    selected = ["WORKTREE"]
    for ref in preferred:
        if ref in available:
            selected.append(ref)
    return selected


def grep_worktree(pattern: str) -> list[dict]:
    regex = re.compile(pattern, re.IGNORECASE)
    rows = []
    for dirname in SCAN_DIRS:
        root = REPO_ROOT / dirname
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.stat().st_size > MAX_TEXT_FILE:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    rows.append(
                        {
                            "ref": "WORKTREE",
                            "path": str(path.relative_to(REPO_ROOT)),
                            "line": line_number,
                            "text": line[:500],
                        }
                    )
                    if len(rows) >= MAX_MATCHES_PER_ROLE_PER_REF:
                        return rows
    return rows


def grep_ref(ref: str, pattern: str) -> list[dict]:
    args = ["grep", "-n", "-I", "-E", pattern, ref, "--", *SCAN_DIRS]
    result = git(*args, check=False)
    if result.returncode not in (0, 1):
        return [
            {
                "ref": ref,
                "error": result.stderr.strip(),
            }
        ]
    rows = []
    for line in result.stdout.splitlines():
        match = re.match(r"^([^:]+):([^:]+):(\d+):(.*)$", line)
        if match:
            _, path, line_number, text = match.groups()
        else:
            match = re.match(r"^([^:]+):(\d+):(.*)$", line)
            if not match:
                continue
            path, line_number, text = match.groups()
        rows.append(
            {
                "ref": ref,
                "path": path,
                "line": int(line_number),
                "text": text[:500],
            }
        )
        if len(rows) >= MAX_MATCHES_PER_ROLE_PER_REF:
            break
    return rows


def build_role_map(patterns: dict, refs: list[str]) -> dict:
    output = {}
    for role, terms in patterns.items():
        escaped = [re.escape(term) for term in terms]
        pattern = "(" + "|".join(escaped) + ")"
        by_ref = {"WORKTREE": grep_worktree(pattern)}
        for ref in refs:
            if ref == "WORKTREE":
                continue
            by_ref[ref] = grep_ref(ref, pattern)

        worktree_count = len(
            [row for row in by_ref["WORKTREE"] if "path" in row]
        )
        history_count = sum(
            len([row for row in rows if "path" in row])
            for ref, rows in by_ref.items()
            if ref != "WORKTREE"
        )
        if worktree_count:
            status = "CANDIDATE_FOUND_CURRENT_HEAD"
        elif history_count:
            status = "CANDIDATE_FOUND_HISTORY_ONLY"
        else:
            status = "NOT_FOUND"
        output[role] = {
            "terms": terms,
            "status": status,
            "worktree_match_count": worktree_count,
            "history_match_count": history_count,
            "matches_by_ref": by_ref,
            "reuse_decision": "REVIEW_REQUIRED",
        }
    return output


def strong_artifact_index() -> list[dict]:
    tokens = (
        "strong",
        "analyzer",
        "researcher",
        "planner",
        "adjudication",
        "request",
        "response",
        "transport",
        "logical_call",
        "provider",
        "shadow",
        "pre",
        "post",
    )
    rows = []
    if not ROUND_ROOT.is_dir():
        return rows
    for path in sorted(ROUND_ROOT.rglob("*")):
        if not path.is_file():
            continue
        lower = path.name.lower()
        if not any(token in lower for token in tokens):
            continue
        if path.stat().st_size > MAX_TEXT_FILE:
            continue
        entry = {
            "path": str(path),
            "relative_path": str(path.relative_to(ROUND_ROOT)),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "suffix": path.suffix,
        }
        if path.suffix == ".json":
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                entry["json_error"] = repr(exc)
            else:
                interesting = {}
                wanted = {
                    "schema_id",
                    "provider",
                    "model",
                    "requested_model",
                    "returned_model",
                    "logical_call_id",
                    "transport_attempt_id",
                    "status",
                    "condition",
                    "role",
                    "evidence_cutoff_sha256",
                    "input_projection_sha256",
                    "raw_request_sha256",
                    "raw_response_sha256",
                    "tokens",
                    "latency",
                    "cost",
                    "selected",
                    "rejected",
                    "deferred",
                    "distillation_status",
                }

                def walk(value, prefix="$"):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            child_path = prefix + "." + str(key)
                            if str(key) in wanted and isinstance(
                                child,
                                (str, int, float, bool, type(None), list),
                            ):
                                interesting[child_path] = child
                            walk(child, child_path)
                    elif isinstance(value, list):
                        for index, child in enumerate(value):
                            walk(child, f"{prefix}[{index}]")

                walk(obj)
                entry["interesting_fields"] = interesting
        rows.append(entry)
    return rows


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise Stop(f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}")
    if not (REPO_ROOT / ".git").exists() and not git("rev-parse", "--git-dir", check=False).returncode == 0:
        raise Stop(f"REPO_ROOT_NOT_GIT:{REPO_ROOT}")
    if not PATTERNS_PATH.is_file():
        raise Stop(f"PATTERNS_MISSING:{PATTERNS_PATH}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    patterns = json.loads(PATTERNS_PATH.read_text(encoding="utf-8"))
    refs = existing_refs()
    selected_refs = target_refs(refs)
    role_map = build_role_map(patterns, selected_refs)
    strong_index = strong_artifact_index()

    asset_rows = []
    for role, details in role_map.items():
        for ref, matches in details["matches_by_ref"].items():
            for match in matches:
                if "path" not in match:
                    continue
                asset_rows.append(
                    {
                        "semantic_role": role,
                        "ref": ref,
                        "path": match["path"],
                        "line": match["line"],
                        "evidence_text": match["text"],
                    }
                )

    gap_matrix = {}
    for role, details in role_map.items():
        gap_matrix[role] = {
            "status": details["status"],
            "current_head_candidates": details["worktree_match_count"],
            "history_candidates": details["history_match_count"],
            "recommended_next_action": (
                "REVIEW_CURRENT_CANDIDATES"
                if details["worktree_match_count"]
                else "REVIEW_HISTORY_CANDIDATES"
                if details["history_match_count"]
                else "CONFIRM_MISSING_BEFORE_DESIGN"
            ),
        }

    duplicate_risks = [
        {
            "semantic_role": role,
            "risk": "HIGH" if details["status"] != "NOT_FOUND" else "LOW",
            "reason": (
                "Candidate implementation or schema names already exist; "
                "do not create a new equivalent until reviewed."
                if details["status"] != "NOT_FOUND"
                else "No name/content candidate found in scanned refs; still review experiment artifacts."
            ),
        }
        for role, details in role_map.items()
    ]

    reports = {
        "REPOSITORY_REF_INDEX_V1.json": {
            "schema_id": "REPOSITORY_REF_INDEX_V1",
            "repo_root": str(REPO_ROOT),
            "refs": refs,
            "selected_scan_refs": selected_refs,
        },
        "EXISTING_ASSET_INDEX_V1.json": {
            "schema_id": "EXISTING_ASSET_INDEX_V1",
            "assets": asset_rows,
        },
        "SEMANTIC_ROLE_TO_ARTIFACT_MAP_V1.json": {
            "schema_id": "SEMANTIC_ROLE_TO_ARTIFACT_MAP_V1",
            "roles": role_map,
        },
        "STRONG_ROLE_TRACE_CANDIDATE_INDEX_V1.json": {
            "schema_id": "STRONG_ROLE_TRACE_CANDIDATE_INDEX_V1",
            "round_root": str(ROUND_ROOT),
            "artifacts": strong_index,
        },
        "REUSE_GAP_MATRIX_V1.json": {
            "schema_id": "REUSE_GAP_MATRIX_V1",
            "matrix": gap_matrix,
        },
        "DUPLICATE_IMPLEMENTATION_RISK_REPORT_V1.json": {
            "schema_id": "DUPLICATE_IMPLEMENTATION_RISK_REPORT_V1",
            "risks": duplicate_risks,
        },
    }

    for name, obj in reports.items():
        (OUTPUT_ROOT / name).write_text(
            json.dumps(
                obj,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    summary_lines = [
        "# Read-only reuse census summary",
        "",
        f"- Repository: `{REPO_ROOT}`",
        f"- Current round root: `{ROUND_ROOT}`",
        f"- Scanned refs: `{selected_refs}`",
        f"- Strong-trace candidate artifacts: `{len(strong_index)}`",
        "",
        "## Semantic-role status",
        "",
    ]
    for role, row in gap_matrix.items():
        summary_lines.append(
            f"- `{role}`: `{row['status']}` "
            f"(current={row['current_head_candidates']}, "
            f"history={row['history_candidates']})"
        )
    summary_lines.extend(
        [
            "",
            "No reuse decision is automatic. Every candidate remains REVIEW_REQUIRED.",
            "",
        ]
    )
    (OUTPUT_ROOT / "CENSUS_SUMMARY_V1.md").write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    bundle = OUTPUT_ROOT.parent / (
        "ROUND_DATA_PLANE_REUSE_CENSUS_STRONG_TRACE_REPORT_BUNDLE_V1.zip"
    )
    if bundle.exists():
        raise Stop(f"BUNDLE_ALREADY_EXISTS:{bundle}")

    with zipfile.ZipFile(
        bundle,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(OUTPUT_ROOT).as_posix(),
                )

    print("ROUND_DATA_PLANE_READ_ONLY_CENSUS_PASS")
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")
    print(f"BUNDLE={bundle}")
    print(f"BUNDLE_SHA256={sha256_file(bundle)}")
    print("REPOSITORY_MUTATION=false")
    print("MODEL_EXECUTION=false")
    print("ENVIRONMENT_EXECUTION=false")
    print("TRAINING_EXECUTION=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stop as exc:
        raise SystemExit("STOP=" + str(exc))
