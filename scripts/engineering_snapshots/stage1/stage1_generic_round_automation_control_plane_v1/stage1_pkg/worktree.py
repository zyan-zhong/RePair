from __future__ import annotations

from pathlib import Path
import subprocess

from .common import Stage1PackageError, sha256_file
from .constants import EXPECTED_SOURCE_HEAD, GENERIC_WORKTREE


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=GENERIC_WORKTREE,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise Stage1PackageError(
            "git command failed: "
            + " ".join(args)
            + ": "
            + result.stderr.strip()
        )
    return result.stdout


def status_paths() -> set[str]:
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
        cwd=GENERIC_WORKTREE,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise Stage1PackageError("git status failed")
    entries = result.stdout.split("\0")
    if entries and entries[-1] == "":
        entries.pop()
    paths: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        if len(entry) < 4 or entry[2] != " ":
            raise Stage1PackageError(f"invalid git status entry: {entry!r}")
        status = entry[:2]
        paths.add(entry[3:])
        if "R" in status or "C" in status:
            index += 1
        index += 1
    return paths


def verify_head_and_detached() -> None:
    if git_text("rev-parse", "HEAD").strip() != EXPECTED_SOURCE_HEAD:
        raise Stage1PackageError("worktree HEAD changed")
    if git_text("branch", "--show-current").strip():
        raise Stage1PackageError("worktree must remain detached")


def file_manifest(paths: set[str]) -> list[dict[str, object]]:
    rows = []
    for relative in sorted(paths):
        path = GENERIC_WORKTREE / relative
        if path.is_symlink() or not path.is_file():
            raise Stage1PackageError(f"changed file invalid: {path}")
        rows.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows
