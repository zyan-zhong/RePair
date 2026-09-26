#!/usr/bin/env python3
"""Pure two-phase cumulative audit for the E1 evaluator candidate."""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


DESIGN_PATH = (
    "docs/superpowers/specs/"
    "2026-08-06-e1-alfworld-evaluator-v1-design.md"
)
MATRIX_PATH = "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md"
TASK14_PATHS = (
    MATRIX_PATH,
    "scripts/evaluation/audit_e1_evaluator_candidate.py",
    "tests/evaluation/test_evaluator_candidate_audit.py",
)
FROZEN_PATHS = (
    "src/pchsi/evaluation/runtime_core.py",
    "src/pchsi/evaluation/raw_policy_parser.py",
    "src/pchsi/evaluation/raw_policy_prompt.py",
    "src/pchsi/evaluation/budget.py",
    "src/pchsi/evaluation/action_trace.py",
    "data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl",
    "configs/protocols/split_and_access_v1.json",
)
TASK_SUBJECTS = (
    "Implement canonical evaluator evidence contracts",
    "Implement frozen E1 task and gamefile identity",
    "Implement evaluator environment runtime identity",
    "Implement strict ALFWorld data contracts",
    "Implement spawned ALFWorld worker adapter",
    "Implement frozen E1 policy transport",
    "Implement E1 run schedule and resolution",
    "Implement public transitions and trace assembly",
    "Implement episode trace sequence validation",
    "Implement crash-consistent evaluator artifacts",
    "Implement single-episode E1 evaluator",
    "Implement E1 result audit",
    "Add evaluator candidate execution gate",
    "Add cumulative E1 evaluator candidate audit",
    "Correct evaluator close-failure evidence integration",
    "Refresh cumulative E1 evaluator audit after close-evidence correction",
    "Fix evaluator started-receipt close cleanup",
    "Refresh cumulative E1 evaluator audit after started-receipt correction",
)
BASE_REQUIRED_REQUIREMENT_IDS = tuple(
    [f"D{index:02d}" for index in range(1, 25)]
    + ["AR01", "NC01", "NC02", "NC03"]
)
CORRECTED_REQUIRED_REQUIREMENT_IDS = (
    *BASE_REQUIRED_REQUIREMENT_IDS,
    "NC04",
)
CORRECTED18_REQUIRED_REQUIREMENT_IDS = (
    *CORRECTED_REQUIRED_REQUIREMENT_IDS,
    "NC05",
)
MATRIX_COLUMNS = (
    "requirement_id",
    "design_section",
    "source_path",
    "symbol",
    "test_path",
    "test_name",
    "verification_command",
    "task_number",
    "task_commit_sha",
)
EXPECTED_SCHEMA_IDS = (
    "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1",
    "E1_ATTEMPT_RECEIPT_V1",
    "E1_EPISODE_ARTIFACT_V1",
    "E1_GAMEFILE_SHA256_PREFLIGHT_V1",
    "E1_POLICY_RUNTIME_MANIFEST_V1",
    "E1_PUBLIC_TRANSITION_RECORD_V1",
    "E1_RUN_SCHEDULE_V1",
    "E1_SCIENTIFIC_CELL_LOCK_V1",
)
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CandidateAuditPhase(str, Enum):
    PRECOMMIT_TASK14 = "PRECOMMIT_TASK14"
    POSTCOMMIT_TASK14 = "POSTCOMMIT_TASK14"
    PRECOMMIT_CORRECTION16 = "PRECOMMIT_CORRECTION16"
    POSTCOMMIT_CORRECTION16 = "POSTCOMMIT_CORRECTION16"
    PRECOMMIT_CORRECTION18 = "PRECOMMIT_CORRECTION18"
    POSTCOMMIT_CORRECTION18 = "POSTCOMMIT_CORRECTION18"


class CandidateAuditError(ValueError):
    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not code:
            raise ValueError("CandidateAuditError code must be non-empty")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class CandidateAuditReport:
    phase: str
    commit_count: int
    task_subjects: tuple[str, ...]
    changed_paths: tuple[str, ...]
    schema_ids: tuple[str, ...]
    requirement_count: int
    candidate_tree_sha256: str
    task14_head_sha: str | None
    candidate_head_sha: str | None
    full_test_command: str
    valid: bool

    def to_json(self) -> str:
        return json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"


def _fail(code: str) -> None:
    raise CandidateAuditError(code)


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
    text: bool = True,
):
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=text,
    )
    if check and result.returncode != 0:
        _fail("GIT_COMMAND_FAILED:" + " ".join(arguments))
    return result


def _lines(value: str) -> tuple[str, ...]:
    return tuple(line for line in value.splitlines() if line)


def _require_repo(root: Path) -> Path:
    repository = Path(root).resolve()
    if not repository.is_dir() or repository.is_symlink():
        _fail("REPOSITORY_ROOT_INVALID")
    _git(repository, "rev-parse", "--git-dir")
    return repository


def _commit_sequence(
    root: Path,
    implementation_base: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    shas = _lines(
        _git(
            root,
            "rev-list",
            "--reverse",
            f"{implementation_base}..HEAD",
        ).stdout
    )
    subjects = _lines(
        _git(
            root,
            "log",
            "--reverse",
            "--format=%s",
            f"{implementation_base}..HEAD",
        ).stdout
    )
    if len(shas) != len(subjects):
        _fail("COMMIT_SUBJECT_COUNT_MISMATCH")
    return shas, subjects


def _verify_design_binding(
    root: Path,
    *,
    implementation_base: str,
    expected_design_blob: str,
    expected_design_merge_commit: str,
) -> None:
    if not _HEX40.fullmatch(expected_design_blob):
        _fail("EXPECTED_DESIGN_BLOB_INVALID")
    if not _HEX40.fullmatch(expected_design_merge_commit):
        _fail("EXPECTED_DESIGN_MERGE_INVALID")
    if not _HEX40.fullmatch(implementation_base):
        _fail("IMPLEMENTATION_BASE_INVALID")

    _git(root, "cat-file", "-e", f"{implementation_base}^{{commit}}")
    _git(
        root,
        "merge-base",
        "--is-ancestor",
        expected_design_merge_commit,
        implementation_base,
    )
    design_blob = _git(
        root,
        "rev-parse",
        f"HEAD:{DESIGN_PATH}",
    ).stdout.strip()
    if design_blob != expected_design_blob:
        _fail("DESIGN_BLOB_MISMATCH")
    merge_blob = _git(
        root,
        "rev-parse",
        f"{expected_design_merge_commit}:{DESIGN_PATH}",
    ).stdout.strip()
    if merge_blob != expected_design_blob:
        _fail("DESIGN_MERGE_BLOB_MISMATCH")


def _verify_frozen_paths(root: Path, implementation_base: str) -> None:
    result = _git(
        root,
        "diff",
        "--quiet",
        implementation_base,
        "HEAD",
        "--",
        *FROZEN_PATHS,
        check=False,
    )
    if result.returncode != 0:
        _fail("FROZEN_PATH_CHANGED")
    worktree = _git(
        root,
        "diff",
        "--name-only",
        "--",
        *FROZEN_PATHS,
    ).stdout
    staged = _git(
        root,
        "diff",
        "--cached",
        "--name-only",
        "--",
        *FROZEN_PATHS,
    ).stdout
    if worktree.strip() or staged.strip():
        _fail("FROZEN_PATH_CHANGED")


def _phase_paths(
    root: Path,
    phase: CandidateAuditPhase,
) -> tuple[str, ...]:
    staged = _lines(
        _git(root, "diff", "--cached", "--name-only").stdout
    )
    unstaged = _lines(
        _git(root, "diff", "--name-only").stdout
    )
    untracked = _lines(
        _git(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
        ).stdout
    )

    if phase in {
        CandidateAuditPhase.PRECOMMIT_TASK14,
        CandidateAuditPhase.PRECOMMIT_CORRECTION16,
        CandidateAuditPhase.PRECOMMIT_CORRECTION18,
    }:
        if tuple(sorted(staged)) != tuple(sorted(TASK14_PATHS)):
            _fail("CUMULATIVE_AUDIT_STAGED_PATHS_MISMATCH")
        if unstaged:
            _fail("PRECOMMIT_UNSTAGED_PATHS_PRESENT")
        if untracked:
            _fail("PRECOMMIT_UNTRACKED_PATHS_PRESENT")
        return tuple(sorted(staged))

    if staged or unstaged or untracked:
        _fail("POSTCOMMIT_WORKTREE_NOT_CLEAN")
    changed = _lines(
        _git(
            root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
        ).stdout
    )
    if tuple(sorted(changed)) != tuple(sorted(TASK14_PATHS)):
        _fail("CUMULATIVE_AUDIT_COMMIT_PATHS_MISMATCH")
    return tuple(sorted(changed))


def _candidate_tree_sha256(
    root: Path,
    phase: CandidateAuditPhase,
) -> str:
    if phase in {
        CandidateAuditPhase.PRECOMMIT_TASK14,
        CandidateAuditPhase.PRECOMMIT_CORRECTION16,
        CandidateAuditPhase.PRECOMMIT_CORRECTION18,
    }:
        tree = _git(root, "write-tree").stdout.strip()
    else:
        tree = _git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    payload = _git(
        root,
        "ls-tree",
        "-r",
        "-z",
        tree,
        text=False,
    ).stdout
    return hashlib.sha256(payload).hexdigest()


def _parse_matrix(path: Path) -> tuple[dict[str, str], ...]:
    if path.is_symlink() or not path.is_file():
        _fail("REQUIREMENT_MATRIX_MISSING")
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("|")
    ]
    if len(lines) < 3:
        _fail("REQUIREMENT_MATRIX_TABLE_MISSING")

    def cells(line: str) -> tuple[str, ...]:
        return tuple(part.strip() for part in line.strip("|").split("|"))

    header = cells(lines[0])
    if header != MATRIX_COLUMNS:
        _fail("REQUIREMENT_MATRIX_COLUMNS_MISMATCH")
    separator = cells(lines[1])
    if len(separator) != len(MATRIX_COLUMNS) or any(
        not cell or set(cell) - {"-", ":"}
        for cell in separator
    ):
        _fail("REQUIREMENT_MATRIX_SEPARATOR_INVALID")

    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = cells(line)
        if len(values) != len(MATRIX_COLUMNS):
            _fail("REQUIREMENT_MATRIX_ROW_WIDTH")
        row = dict(zip(MATRIX_COLUMNS, values, strict=True))
        if any(not value for value in row.values()):
            _fail("REQUIREMENT_MATRIX_EMPTY_VALUE")
        rows.append(row)
    return tuple(rows)


def _top_level_symbols(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise CandidateAuditError("MATRIX_SOURCE_PARSE_FAILED") from error
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _verify_matrix(
    root: Path,
    rows: tuple[dict[str, str], ...],
    task_shas: tuple[str, ...],
    required_requirement_ids: tuple[str, ...],
) -> None:
    observed_ids = tuple(row["requirement_id"] for row in rows)
    if len(set(observed_ids)) != len(observed_ids):
        _fail("REQUIREMENT_MATRIX_DUPLICATE_ID")
    if set(observed_ids) != set(required_requirement_ids):
        _fail("REQUIREMENT_MATRIX_INCOMPLETE")

    for row in rows:
        joined = " ".join(row.values())
        if re.search(r"covered\s*=\s*true", joined, flags=re.IGNORECASE):
            _fail("REQUIREMENT_MATRIX_GENERIC_COVERAGE")
        if re.search(r"\b(?:HEAD|PENDING|TBD|TODO)\b", joined):
            _fail("REQUIREMENT_MATRIX_SYMBOLIC_SHA")
        try:
            task_number = int(row["task_number"])
        except ValueError as error:
            raise CandidateAuditError("REQUIREMENT_MATRIX_TASK_INVALID") from error
        if not 1 <= task_number <= len(task_shas):
            _fail("REQUIREMENT_MATRIX_TASK_OUT_OF_RANGE")
        commit_sha = row["task_commit_sha"]
        if not _HEX40.fullmatch(commit_sha):
            _fail("REQUIREMENT_MATRIX_SHA_INVALID")
        if commit_sha != task_shas[task_number - 1]:
            _fail("REQUIREMENT_MATRIX_SHA_MISMATCH")

        source = root / row["source_path"]
        test = root / row["test_path"]
        if source.is_symlink() or not source.is_file():
            _fail("REQUIREMENT_MATRIX_SOURCE_MISSING")
        if test.is_symlink() or not test.is_file():
            _fail("REQUIREMENT_MATRIX_TEST_MISSING")
        if row["symbol"] not in _top_level_symbols(source):
            _fail("REQUIREMENT_MATRIX_SYMBOL_MISSING")
        if row["test_name"] not in _top_level_symbols(test):
            _fail("REQUIREMENT_MATRIX_TEST_NAME_MISSING")


def _schema_inventory(root: Path) -> tuple[str, ...]:
    schema_root = root / "configs/evaluation/schemas"
    if schema_root.is_symlink() or not schema_root.is_dir():
        _fail("SCHEMA_DIRECTORY_MISSING")
    identifiers: list[str] = []
    for path in sorted(schema_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CandidateAuditError("SCHEMA_INVALID_JSON") from error
        identifier = payload.get("$id") if isinstance(payload, dict) else None
        if not isinstance(identifier, str) or not identifier:
            _fail("SCHEMA_ID_MISSING")
        identifiers.append(identifier)
    observed = tuple(sorted(identifiers))
    if observed != tuple(sorted(EXPECTED_SCHEMA_IDS)):
        _fail("SCHEMA_INVENTORY_MISMATCH")
    return observed


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _decorator_name(node.value) + "." + node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _scan_tests(root: Path) -> None:
    forbidden_imports = {
        "alfworld",
        "textworld",
        "gym",
        "vllm",
        "torch",
        "requests",
        "httpx",
    }
    for path in sorted((root / "tests/evaluation").glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            raise CandidateAuditError("TEST_SOURCE_PARSE_FAILED") from error
        if _import_roots(tree) & forbidden_imports:
            _fail("REAL_EXECUTION_IMPORT_IN_TEST")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    name = _decorator_name(decorator).casefold()
                    if "skip" in name or "xfail" in name:
                        _fail("SKIP_OR_XFAIL_IN_EVALUATION_TEST")
            if isinstance(node, ast.Call):
                name = _decorator_name(node.func).casefold()
                if name in {"pytest.skip", "pytest.xfail", "unittest.skip"}:
                    _fail("SKIP_OR_XFAIL_IN_EVALUATION_TEST")
                if name.endswith(".step") and name.startswith("env."):
                    _fail("REAL_ENV_STEP_IN_TEST")


def _scan_production(root: Path) -> None:
    forbidden_roots = {
        "alfworld",
        "textworld",
        "gym",
        "vllm",
        "torch",
    }
    for path in sorted((root / "src/pchsi/evaluation").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parent_map: dict[ast.AST, ast.AST] = {}
        for candidate in ast.walk(tree):
            for child in ast.iter_child_nodes(candidate):
                parent_map[child] = candidate

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(
                    (node, alias.name.split(".", 1)[0])
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(
                    (node, node.module.split(".", 1)[0])
                )
        for node, root_name in imports:
            if root_name not in forbidden_roots:
                continue
            if path.name != "alfworld_worker.py":
                _fail("REAL_RUNTIME_IMPORT_OUTSIDE_WORKER")
            ancestor = parent_map.get(node)
            found_entrypoint = False
            while ancestor is not None:
                if (
                    isinstance(
                        ancestor,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    )
                    and ancestor.name
                    == "real_alfworld_worker_main"
                ):
                    found_entrypoint = True
                    break
                ancestor = parent_map.get(ancestor)
            if not found_entrypoint:
                _fail("REAL_RUNTIME_IMPORT_NOT_LAZY")


def audit_candidate(
    *,
    repository_root: Path,
    implementation_base: str,
    expected_design_blob: str,
    expected_design_merge_commit: str,
    phase: CandidateAuditPhase,
) -> CandidateAuditReport:
    if not isinstance(phase, CandidateAuditPhase):
        raise TypeError("phase must be CandidateAuditPhase")
    root = _require_repo(repository_root)
    _verify_design_binding(
        root,
        implementation_base=implementation_base,
        expected_design_blob=expected_design_blob,
        expected_design_merge_commit=expected_design_merge_commit,
    )
    _verify_frozen_paths(root, implementation_base)

    task_shas, subjects = _commit_sequence(root, implementation_base)

    phase_settings = {
        CandidateAuditPhase.PRECOMMIT_TASK14: (
            13,
            13,
            BASE_REQUIRED_REQUIREMENT_IDS,
            True,
        ),
        CandidateAuditPhase.POSTCOMMIT_TASK14: (
            14,
            13,
            BASE_REQUIRED_REQUIREMENT_IDS,
            False,
        ),
        CandidateAuditPhase.PRECOMMIT_CORRECTION16: (
            15,
            15,
            CORRECTED_REQUIRED_REQUIREMENT_IDS,
            True,
        ),
        CandidateAuditPhase.POSTCOMMIT_CORRECTION16: (
            16,
            15,
            CORRECTED_REQUIRED_REQUIREMENT_IDS,
            False,
        ),
        CandidateAuditPhase.PRECOMMIT_CORRECTION18: (
            17,
            17,
            CORRECTED18_REQUIRED_REQUIREMENT_IDS,
            True,
        ),
        CandidateAuditPhase.POSTCOMMIT_CORRECTION18: (
            18,
            17,
            CORRECTED18_REQUIRED_REQUIREMENT_IDS,
            False,
        ),
    }
    (
        expected_count,
        matrix_commit_count,
        required_requirement_ids,
        precommit,
    ) = phase_settings[phase]

    if len(task_shas) != expected_count:
        _fail("TASK_COMMIT_COUNT_MISMATCH")
    if subjects != TASK_SUBJECTS[:expected_count]:
        _fail("TASK_COMMIT_SUBJECT_MISMATCH")

    if precommit:
        if (
            _git(root, "rev-parse", "HEAD").stdout.strip()
            != task_shas[-1]
        ):
            _fail("PRECOMMIT_HEAD_MISMATCH")
    else:
        if (
            _git(root, "log", "-1", "--format=%s").stdout.strip()
            != TASK_SUBJECTS[expected_count - 1]
        ):
            _fail("POSTCOMMIT_HEAD_SUBJECT_MISMATCH")

    changed_paths = _phase_paths(root, phase)
    matrix_rows = _parse_matrix(root / MATRIX_PATH)
    _verify_matrix(
        root,
        matrix_rows,
        task_shas[:matrix_commit_count],
        required_requirement_ids,
    )
    schema_ids = _schema_inventory(root)
    _scan_tests(root)
    _scan_production(root)
    candidate_tree = _candidate_tree_sha256(root, phase)
    if not _HEX64.fullmatch(candidate_tree):
        _fail("CANDIDATE_TREE_SHA256_INVALID")

    task14_head_sha = (
        task_shas[13]
        if len(task_shas) >= 14
        else None
    )
    candidate_head_sha = (
        None
        if precommit
        else _git(root, "rev-parse", "HEAD").stdout.strip()
    )

    return CandidateAuditReport(
        phase=phase.value,
        commit_count=expected_count,
        task_subjects=subjects,
        changed_paths=changed_paths,
        schema_ids=schema_ids,
        requirement_count=len(matrix_rows),
        candidate_tree_sha256=candidate_tree,
        task14_head_sha=task14_head_sha,
        candidate_head_sha=candidate_head_sha,
        full_test_command="python -m pytest -q",
        valid=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--implementation-base", required=True)
    parser.add_argument("--expected-design-blob", required=True)
    parser.add_argument("--expected-design-merge-commit", required=True)
    parser.add_argument(
        "--phase",
        choices=tuple(item.value for item in CandidateAuditPhase),
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_candidate(
            repository_root=args.repository_root,
            implementation_base=args.implementation_base,
            expected_design_blob=args.expected_design_blob,
            expected_design_merge_commit=args.expected_design_merge_commit,
            phase=CandidateAuditPhase(args.phase),
        )
    except CandidateAuditError as error:
        sys.stderr.write(error.code + "\n")
        return 1
    sys.stdout.write(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
