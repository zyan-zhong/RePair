from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    REPO_ROOT
    / "scripts/evaluation/audit_e1_evaluator_candidate.py"
)
SPEC = importlib.util.spec_from_file_location(
    "e1_candidate_audit_module",
    AUDIT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CandidateAuditError = MODULE.CandidateAuditError
CandidateAuditPhase = MODULE.CandidateAuditPhase
audit_candidate = MODULE.audit_candidate


SUBJECTS = (
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
)
DESIGN_PATH = (
    "docs/superpowers/specs/"
    "2026-08-06-e1-alfworld-evaluator-v1-design.md"
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
SCHEMA_IDS = (
    "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1",
    "E1_ATTEMPT_RECEIPT_V1",
    "E1_EPISODE_ARTIFACT_V1",
    "E1_GAMEFILE_SHA256_PREFLIGHT_V1",
    "E1_POLICY_RUNTIME_MANIFEST_V1",
    "E1_PUBLIC_TRANSITION_RECORD_V1",
    "E1_RUN_SCHEDULE_V1",
    "E1_SCIENTIFIC_CELL_LOCK_V1",
)
REQUIREMENTS = tuple(
    [f"D{index:02d}" for index in range(1, 25)]
    + ["AR01", "NC01", "NC02", "NC03"]
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _matrix(
    *,
    shas: tuple[str, ...],
    missing: str | None = None,
    symbolic_sha: bool = False,
    bad_symbol: bool = False,
) -> str:
    lines = [
        "# Synthetic Requirement Matrix",
        "",
        "| requirement_id | design_section | source_path | symbol | test_path | test_name | verification_command | task_number | task_commit_sha |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for index, requirement in enumerate(REQUIREMENTS, start=1):
        if requirement == missing:
            continue
        task = ((index - 1) % 13) + 1
        symbol = "missing_symbol" if bad_symbol and index == 1 else f"symbol_{task:02d}"
        sha = "HEAD" if symbolic_sha and index == 1 else shas[task - 1]
        test_name = f"test_task_{task:02d}"
        row = (
            requirement,
            f"section {index}",
            f"src/pchsi/evaluation/task{task:02d}.py",
            symbol,
            f"tests/evaluation/test_task{task:02d}.py",
            test_name,
            (
                "python -m pytest -q "
                f"tests/evaluation/test_task{task:02d}.py::"
                f"{test_name}"
            ),
            str(task),
            sha,
        )
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _make_repo(
    tmp_path: Path,
    *,
    postcommit: bool = False,
    missing_requirement: str | None = None,
    symbolic_sha: bool = False,
    bad_symbol: bool = False,
    bad_runtime_test: bool = False,
    skipped_test: bool = False,
):
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "fixture@example.test")

    _write(root, DESIGN_PATH, "frozen evaluator design\n")
    for path in FROZEN_PATHS:
        _write(root, path, "# frozen\n")
    for index, schema_id in enumerate(SCHEMA_IDS):
        _write(
            root,
            f"configs/evaluation/schemas/schema-{index:02d}.json",
            '{"$id":"' + schema_id + '"}\n',
        )
    _write(
        root,
        "src/pchsi/evaluation/alfworld_worker.py",
        (
            "def real_alfworld_worker_main():\n"
            "    try:\n"
            "        import textworld\n"
            "        return textworld\n"
            "    except ImportError:\n"
            "        return None\n"
        ),
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "synthetic plan merge")
    base = _git(root, "rev-parse", "HEAD")
    design_blob = _git(root, "rev-parse", f"HEAD:{DESIGN_PATH}")

    task_shas: list[str] = []
    for task in range(1, 14):
        source = (
            f"def symbol_{task:02d}():\n"
            f"    return {task}\n"
        )
        test_source = (
            f"def test_task_{task:02d}():\n"
            "    assert True\n"
        )
        if task == 13 and bad_runtime_test:
            test_source = (
                "import " + "torch\n"
                + f"def test_task_{task:02d}():\n"
                + "    assert " + "torch." + "cuda.is_available() is False\n"
            )
        if task == 13 and skipped_test:
            test_source = (
                "import pytest\n"
                + "@pytest.mark." + "skip(reason='forbidden')\n"
                + f"def test_task_{task:02d}():\n"
                + "    assert True\n"
            )
        _write(
            root,
            f"src/pchsi/evaluation/task{task:02d}.py",
            source,
        )
        _write(
            root,
            f"tests/evaluation/test_task{task:02d}.py",
            test_source,
        )
        _git(root, "add", ".")
        _git(root, "commit", "-m", SUBJECTS[task - 1])
        task_shas.append(_git(root, "rev-parse", "HEAD"))

    _write(
        root,
        "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md",
        _matrix(
            shas=tuple(task_shas),
            missing=missing_requirement,
            symbolic_sha=symbolic_sha,
            bad_symbol=bad_symbol,
        ),
    )
    _write(
        root,
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "def main():\n    return 0\n",
    )
    _write(
        root,
        "tests/evaluation/test_evaluator_candidate_audit.py",
        "def test_candidate_audit_fixture():\n    assert True\n",
    )
    _git(
        root,
        "add",
        "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md",
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "tests/evaluation/test_evaluator_candidate_audit.py",
    )

    if postcommit:
        _git(root, "commit", "-m", SUBJECTS[13])

    return root, base, design_blob, tuple(task_shas)


def _audit(root: Path, base: str, design_blob: str, *, post: bool = False):
    return audit_candidate(
        repository_root=root,
        implementation_base=base,
        expected_design_blob=design_blob,
        expected_design_merge_commit=base,
        phase=(
            CandidateAuditPhase.POSTCOMMIT_TASK14
            if post
            else CandidateAuditPhase.PRECOMMIT_TASK14
        ),
    )


def test_candidate_audit_binds_design_blob_and_merge_commit(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path)
    assert _audit(root, base, blob).valid is True
    with pytest.raises(CandidateAuditError):
        _audit(root, base, "0" * 40)
    with pytest.raises(CandidateAuditError):
        audit_candidate(
            repository_root=root,
            implementation_base=base,
            expected_design_blob=blob,
            expected_design_merge_commit="0" * 40,
            phase=CandidateAuditPhase.PRECOMMIT_TASK14,
        )


def test_precommit_audit_requires_thirteen_prior_commits_and_exact_task14_staged_paths(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path)
    report = _audit(root, base, blob)
    assert report.commit_count == 13
    assert report.changed_paths == tuple(sorted((
        "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md",
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "tests/evaluation/test_evaluator_candidate_audit.py",
    )))
    _git(root, "restore", "--staged", "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md")
    with pytest.raises(CandidateAuditError):
        _audit(root, base, blob)


def test_postcommit_audit_requires_fourteen_ordered_task_commits(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, postcommit=True)
    report = _audit(root, base, blob, post=True)
    assert report.commit_count == 14
    assert report.task_subjects == SUBJECTS


def test_postcommit_report_records_task14_head_sha(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, postcommit=True)
    report = _audit(root, base, blob, post=True)
    assert report.task14_head_sha == _git(root, "rev-parse", "HEAD")


def test_candidate_audit_rejects_changed_frozen_runtime_or_manifest_paths(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path)
    _write(root, FROZEN_PATHS[0], "# changed\n")
    _git(root, "add", FROZEN_PATHS[0])
    with pytest.raises(CandidateAuditError, match="FROZEN"):
        _audit(root, base, blob)


def test_candidate_audit_rejects_real_execution_in_tests(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, bad_runtime_test=True)
    with pytest.raises(CandidateAuditError, match="REAL_EXECUTION"):
        _audit(root, base, blob)


def test_candidate_audit_requires_every_design_requirement_mapping(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, missing_requirement="D24")
    with pytest.raises(CandidateAuditError, match="INCOMPLETE"):
        _audit(root, base, blob)


def test_requirement_matrix_uses_only_resolved_task1_to_task13_shas(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, symbolic_sha=True)
    with pytest.raises(CandidateAuditError, match="SYMBOLIC"):
        _audit(root, base, blob)


def test_requirement_matrix_references_existing_symbols_and_tests(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, bad_symbol=True)
    with pytest.raises(CandidateAuditError, match="SYMBOL"):
        _audit(root, base, blob)


def test_candidate_audit_reports_exact_changed_paths_and_tree_hash(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path)
    report = _audit(root, base, blob)
    assert len(report.candidate_tree_sha256) == 64
    assert report.requirement_count == 28
    assert report.schema_ids == tuple(sorted(SCHEMA_IDS))
    assert report.full_test_command == "python -m pytest -q"


def test_candidate_audit_rejects_skips_xfails_and_relaxed_assertions_in_security_critical_tests(tmp_path: Path) -> None:
    root, base, blob, _ = _make_repo(tmp_path, skipped_test=True)
    with pytest.raises(CandidateAuditError, match="SKIP_OR_XFAIL"):
        _audit(root, base, blob)



# ---------------------------------------------------------------------------
# Fixed-head source-review correction audit (Commit 16)
# ---------------------------------------------------------------------------

CORRECTION15_SUBJECT = (
    "Correct evaluator close-failure evidence integration"
)
CORRECTION16_SUBJECT = (
    "Refresh cumulative E1 evaluator audit after close-evidence correction"
)


def _make_correction16_repo(
    tmp_path: Path,
    *,
    postcommit: bool = False,
    missing_nc04: bool = False,
):
    case_root = tmp_path / "correction16-fixture"
    case_root.mkdir()

    root, base, blob, task1_to_13 = _make_repo(
        case_root,
        postcommit=True,
    )
    task14_sha = _git(root, "rev-parse", "HEAD")

    _write(
        root,
        "src/pchsi/evaluation/close_fix.py",
        (
            "class CloseFailureEvidenceCode:\n"
            "    pass\n"
        ),
    )
    _write(
        root,
        "tests/evaluation/test_close_fix.py",
        (
            "def test_close_failure_reaped_worker_records_formal_audit_code():\n"
            "    assert True\n"
        ),
    )
    _git(
        root,
        "add",
        "src/pchsi/evaluation/close_fix.py",
        "tests/evaluation/test_close_fix.py",
    )
    _git(root, "commit", "-m", CORRECTION15_SUBJECT)
    task15_sha = _git(root, "rev-parse", "HEAD")

    matrix = _matrix(shas=task1_to_13)
    if missing_nc04:
        matrix += (
            "\n<!-- correction16 fixture intentionally missing NC04 -->\n"
        )
    else:
        matrix += (
            "| NC04 | close failure evidence integration | "
            "src/pchsi/evaluation/close_fix.py | "
            "CloseFailureEvidenceCode | "
            "tests/evaluation/test_close_fix.py | "
            "test_close_failure_reaped_worker_records_formal_audit_code | "
            "python -m pytest -q "
            "tests/evaluation/test_close_fix.py::"
            "test_close_failure_reaped_worker_records_formal_audit_code | "
            f"15 | {task15_sha} |\n"
        )

    _write(
        root,
        "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md",
        matrix,
    )
    for relative in (
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "tests/evaluation/test_evaluator_candidate_audit.py",
    ):
        path = root / relative
        path.write_text(
            path.read_text(encoding="utf-8")
            + "# correction16 staged fixture\n",
            encoding="utf-8",
        )
    _git(
        root,
        "add",
        "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md",
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "tests/evaluation/test_evaluator_candidate_audit.py",
    )

    if postcommit:
        _git(root, "commit", "-m", CORRECTION16_SUBJECT)

    return (
        root,
        base,
        blob,
        (*task1_to_13, task14_sha, task15_sha),
    )


def test_correction16_precommit_requires_fifteen_prior_commits(
    tmp_path: Path,
) -> None:
    root, base, blob, sequence = _make_correction16_repo(
        tmp_path
    )
    phase = getattr(
        CandidateAuditPhase,
        "PRECOMMIT_CORRECTION16",
    )
    report = audit_candidate(
        repository_root=root,
        implementation_base=base,
        expected_design_blob=blob,
        expected_design_merge_commit=base,
        phase=phase,
    )
    assert report.valid is True
    assert report.commit_count == 15
    assert report.requirement_count == 29
    assert report.task14_head_sha == sequence[13]


def test_correction16_postcommit_requires_sixteen_ordered_commits(
    tmp_path: Path,
) -> None:
    root, base, blob, sequence = _make_correction16_repo(
        tmp_path,
        postcommit=True,
    )
    phase = getattr(
        CandidateAuditPhase,
        "POSTCOMMIT_CORRECTION16",
    )
    report = audit_candidate(
        repository_root=root,
        implementation_base=base,
        expected_design_blob=blob,
        expected_design_merge_commit=base,
        phase=phase,
    )
    assert report.valid is True
    assert report.commit_count == 16
    assert report.task_subjects[-2:] == (
        CORRECTION15_SUBJECT,
        CORRECTION16_SUBJECT,
    )
    assert report.task14_head_sha == sequence[13]
    assert report.candidate_head_sha == _git(
        root,
        "rev-parse",
        "HEAD",
    )


def test_correction16_requires_nc04_bound_to_task15(
    tmp_path: Path,
) -> None:
    root, base, blob, _ = _make_correction16_repo(
        tmp_path,
        missing_nc04=True,
    )
    phase = getattr(
        CandidateAuditPhase,
        "PRECOMMIT_CORRECTION16",
    )
    with pytest.raises(
        CandidateAuditError,
        match="INCOMPLETE",
    ):
        audit_candidate(
            repository_root=root,
            implementation_base=base,
            expected_design_blob=blob,
            expected_design_merge_commit=base,
            phase=phase,
        )



# ---------------------------------------------------------------------------
# Fixed-head source-review correction audit (Commit 18)
# ---------------------------------------------------------------------------

CORRECTION17_SUBJECT = (
    "Fix evaluator started-receipt close cleanup"
)
CORRECTION18_SUBJECT = (
    "Refresh cumulative E1 evaluator audit after started-receipt correction"
)


def _make_correction18_repo(
    tmp_path: Path,
    *,
    postcommit: bool = False,
    missing_nc05: bool = False,
):
    case_root = tmp_path / "correction18-fixture"
    case_root.mkdir()

    root, base, blob, sequence15 = _make_correction16_repo(
        case_root,
        postcommit=True,
    )
    task16_sha = _git(root, "rev-parse", "HEAD")

    _write(
        root,
        "src/pchsi/evaluation/started_receipt_cleanup.py",
        (
            "def close_after_started_receipt_failure():\n"
            "    return None\n"
        ),
    )
    _write(
        root,
        "tests/evaluation/test_started_receipt_cleanup.py",
        (
            "def test_started_receipt_failure_closes_environment_without_name_error():\n"
            "    assert True\n"
        ),
    )
    _git(
        root,
        "add",
        "src/pchsi/evaluation/started_receipt_cleanup.py",
        "tests/evaluation/test_started_receipt_cleanup.py",
    )
    _git(root, "commit", "-m", CORRECTION17_SUBJECT)
    task17_sha = _git(root, "rev-parse", "HEAD")

    matrix_path = (
        root / "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md"
    )
    matrix = matrix_path.read_text(encoding="utf-8")
    if missing_nc05:
        matrix += (
            "\n<!-- correction18 fixture intentionally missing NC05 -->\n"
        )
    else:
        matrix += (
            "| NC05 | started receipt failure cleanup | "
            "src/pchsi/evaluation/started_receipt_cleanup.py | "
            "close_after_started_receipt_failure | "
            "tests/evaluation/test_started_receipt_cleanup.py | "
            "test_started_receipt_failure_closes_environment_without_name_error | "
            "python -m pytest -q "
            "tests/evaluation/test_started_receipt_cleanup.py::"
            "test_started_receipt_failure_closes_environment_without_name_error | "
            f"17 | {task17_sha} |\n"
        )
    matrix_path.write_text(matrix, encoding="utf-8")

    for relative in (
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "tests/evaluation/test_evaluator_candidate_audit.py",
    ):
        path = root / relative
        path.write_text(
            path.read_text(encoding="utf-8")
            + "# correction18 staged fixture\n",
            encoding="utf-8",
        )

    _git(
        root,
        "add",
        "docs/evaluation/E1_EVALUATOR_REQUIREMENT_MATRIX.md",
        "scripts/evaluation/audit_e1_evaluator_candidate.py",
        "tests/evaluation/test_evaluator_candidate_audit.py",
    )

    if postcommit:
        _git(root, "commit", "-m", CORRECTION18_SUBJECT)

    return (
        root,
        base,
        blob,
        (*sequence15, task16_sha, task17_sha),
    )


def test_correction18_precommit_requires_seventeen_prior_commits(
    tmp_path: Path,
) -> None:
    root, base, blob, sequence = _make_correction18_repo(
        tmp_path
    )
    phase = getattr(
        CandidateAuditPhase,
        "PRECOMMIT_CORRECTION18",
    )
    report = audit_candidate(
        repository_root=root,
        implementation_base=base,
        expected_design_blob=blob,
        expected_design_merge_commit=base,
        phase=phase,
    )
    assert report.valid is True
    assert report.commit_count == 17
    assert report.requirement_count == 30
    assert report.task14_head_sha == sequence[13]


def test_correction18_postcommit_requires_eighteen_ordered_commits(
    tmp_path: Path,
) -> None:
    root, base, blob, sequence = _make_correction18_repo(
        tmp_path,
        postcommit=True,
    )
    phase = getattr(
        CandidateAuditPhase,
        "POSTCOMMIT_CORRECTION18",
    )
    report = audit_candidate(
        repository_root=root,
        implementation_base=base,
        expected_design_blob=blob,
        expected_design_merge_commit=base,
        phase=phase,
    )
    assert report.valid is True
    assert report.commit_count == 18
    assert report.task_subjects[-2:] == (
        CORRECTION17_SUBJECT,
        CORRECTION18_SUBJECT,
    )
    assert report.task14_head_sha == sequence[13]
    assert report.candidate_head_sha == _git(
        root,
        "rev-parse",
        "HEAD",
    )


def test_correction18_requires_nc05_bound_to_task17(
    tmp_path: Path,
) -> None:
    root, base, blob, _ = _make_correction18_repo(
        tmp_path,
        missing_nc05=True,
    )
    phase = getattr(
        CandidateAuditPhase,
        "PRECOMMIT_CORRECTION18",
    )
    with pytest.raises(
        CandidateAuditError,
        match="INCOMPLETE",
    ):
        audit_candidate(
            repository_root=root,
            implementation_base=base,
            expected_design_blob=blob,
            expected_design_merge_commit=base,
            phase=phase,
        )
