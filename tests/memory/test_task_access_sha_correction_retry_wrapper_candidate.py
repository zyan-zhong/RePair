"""RED-only tests for the Task 4 correction-aware retry wrapper candidate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

WRAPPER_PATH = (
    REPO_ROOT
    / "scripts/memory/"
    "build_task_access_sha_correction_retry_wrapper_candidate_v1.py"
)

TASK3_HEAD = "ba0a344fcda079e112c84fcbe312121dcf5efb60"
TASK1_COMMIT = "08aa577a299012aa59b03d75a4a0654ae0d74d69"
EXPECTED_BRANCH = (
    "implementation/"
    "failure-memory-task-access-sha-authority-correction-v1"
)

OLD_V1_STAGING = "failure_memory_foundation_v1_71ce8a4"
OLD_V2_STAGING = "failure_memory_foundation_v1_1a0feee"

FROZEN_NEW_STAGING = (
    "failure_memory_foundation_v1_"
    "sha_authority_correction_v1_ba0a344"
)

HISTORICAL_SHA = (
    "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
)

EXACT_SHA = (
    "260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea"
)


def _wrapper():
    if not WRAPPER_PATH.is_file():
        pytest.fail(
            "TASK4_RED_MISSING_RETRY_WRAPPER",
            pytrace=False,
        )

    name = "pchsi_task_access_sha_retry_wrapper_candidate_test_target"
    spec = importlib.util.spec_from_file_location(
        name,
        WRAPPER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _error(module):
    assert hasattr(module, "RetryWrapperCandidateError")
    return module.RetryWrapperCandidateError


def _valid_evidence() -> dict[str, object]:
    reproduction_ids = (
        "CURRENT_PRODUCTION_IN_MEMORY",
        "HISTORICAL_PURE_CORE",
        "STANDALONE_CANONICAL_SERIALIZER",
    )

    return {
        "schema": "TASK_ACCESS_SHA_AUTHORITY_CORRECTION_EVIDENCE_V1",
        "correction_base_commit": (
            "1a0feeef8085ba124fa79e72c38fea90b812d9f9"
        ),
        "correction_design_commit": TASK1_COMMIT,
        "access_policy_id": "MEMORY_TASK_ACCESS_V2_1",
        "historical_design_candidate_sha256": HISTORICAL_SHA,
        "historical_candidate_role": (
            "PRESERVED_HISTORICAL_DESIGN_CANDIDATE"
        ),
        "historical_candidate_execution_authority": False,
        "proposed_exact_contract_protected_sha256": EXACT_SHA,
        "dataset_source_fingerprint": (
            "d657703df1033a9797e7e9a18b3eb989"
            "e49dd3391a468d1a65f6edff3e609e24"
        ),
        "record_count": 3827,
        "role_counts": {
            "TRAIN_MEMORY_SOURCE": 2367,
            "TRAIN_RETRIEVAL_DEV": 1186,
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
            (
                "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_"
                "HISTORICALLY_EXPOSED"
            ): 134,
        },
        "reproductions": [
            {
                "reproduction_id": reproduction_id,
                "implementation_identity": (
                    f"SYNTHETIC_{reproduction_id}"
                ),
                "implementation_sha256": "1" * 64,
                "source_fingerprint": (
                    "d657703df1033a9797e7e9a18b3eb989"
                    "e49dd3391a468d1a65f6edff3e609e24"
                ),
                "record_count": 3827,
                "role_counts": {
                    "TRAIN_MEMORY_SOURCE": 2367,
                    "TRAIN_RETRIEVAL_DEV": 1186,
                    "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
                    (
                        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_"
                        "HISTORICALLY_EXPOSED"
                    ): 134,
                },
                "canonical_output_artifact_sha256": EXACT_SHA,
                "canonical_output_byte_count": 3527458,
                "observed_protected_sha256": EXACT_SHA,
            }
            for reproduction_id in reproduction_ids
        ],
        "production_vs_historical_bytes_equal": True,
        "production_vs_standalone_bytes_equal": True,
        "all_three_sha256_equal": True,
        "three_way_observed_protected_sha256": EXACT_SHA,
        "three_way_sha_matches_proposed_authority": True,
        "incident_evidence": [
            {
                "artifact_id": "V2_MATERIALIZATION_STOP",
                "sha256": (
                    "de08da19fe8ac43e7ed91ad47e6411cb"
                    "151665f1ee41008db187a983a9b58866"
                ),
                "byte_count": 1,
            },
            {
                "artifact_id": "V2_SOURCE_INTEGRITY_PRE",
                "sha256": (
                    "b03649bcf252d07bf8c4095aaf396a7"
                    "ed70e9f8c1d032646dbe38cb44780ab92"
                ),
                "byte_count": 1,
            },
            {
                "artifact_id": "V2_TASK_MATERIALIZER_STDERR",
                "sha256": (
                    "d6c1b9dc4d4362eba1c82e243c124906"
                    "44439816d22997a6429ed8e07a76f6c6"
                ),
                "byte_count": 1,
            },
            {
                "artifact_id": "V2_TASK_MATERIALIZER_STDOUT",
                "sha256": (
                    "e3b0c44298fc1c149afbf4c8996fb924"
                    "27ae41e4649b934ca495991b7852b855"
                ),
                "byte_count": 0,
            },
        ],
        "conclusion": (
            "THREE_WAY_CANONICAL_BYTES_AGREE_"
            "AND_MATCH_PROPOSED_AUTHORITY"
        ),
    }


def _valid_authority_config() -> dict[str, object]:
    return {
        "schema": "TASK_ACCESS_REGENERATION_CONFIG_V2",
        "access_policy_id": "MEMORY_TASK_ACCESS_V2_1",
        "disclosure_policy_id": (
            "HELDOUT_IDENTITY_DISCLOSURE_POLICY_V1"
        ),
        "original_failure_memory_design_commit": (
            "b3cb816e2e727600f79f1947a77c73ce87d4a97c"
        ),
        "sha_authority_correction_design_commit": TASK1_COMMIT,
        "historical_design_candidate_sha256": HISTORICAL_SHA,
        "approved_exact_contract_protected_sha256": EXACT_SHA,
        "expected_populations": {
            "TRAIN_MEMORY_SOURCE": 2367,
            "TRAIN_RETRIEVAL_DEV": 1186,
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
            (
                "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_"
                "HISTORICALLY_EXPOSED"
            ): 134,
        },
    }


def _valid_snapshot(
    module,
    *,
    staging_identity: str = FROZEN_NEW_STAGING,
    staging_exists: bool = False,
    staging_is_symlink: bool = False,
    branch: str = EXPECTED_BRANCH,
    head: str = TASK3_HEAD,
    clean: bool = True,
    correction_evidence: dict[str, object] | None = None,
    authority_config: dict[str, object] | None = None,
):
    snapshot_type = getattr(
        module,
        "RetryWrapperCandidateSnapshotV1",
    )

    return snapshot_type(
        branch=branch,
        head=head,
        worktree_clean=clean,
        requested_staging_identity=staging_identity,
        requested_staging_exists=staging_exists,
        requested_staging_is_symlink=staging_is_symlink,
        correction_evidence=(
            _valid_evidence()
            if correction_evidence is None
            else correction_evidence
        ),
        authority_config=(
            _valid_authority_config()
            if authority_config is None
            else authority_config
        ),
    )


def _validate(module, snapshot):
    assert hasattr(
        module,
        "validate_retry_wrapper_candidate_snapshot",
    )
    return module.validate_retry_wrapper_candidate_snapshot(
        snapshot
    )


def test_retry_wrapper_freezes_task3_head_and_new_staging_identity() -> None:
    module = _wrapper()

    assert module.FROZEN_CORRECTION_CODE_HEAD == TASK3_HEAD
    assert module.FROZEN_NEW_STAGING_IDENTITY == FROZEN_NEW_STAGING

    assert (
        module.FROZEN_NEW_STAGING_IDENTITY
        == module.derive_head_bound_staging_identity(
            TASK3_HEAD
        )
    )


@pytest.mark.parametrize(
    "old_identity",
    [
        OLD_V1_STAGING,
        OLD_V2_STAGING,
    ],
)
def test_retry_wrapper_rejects_old_failure_staging_identity(
    old_identity: str,
) -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(
        module,
        staging_identity=old_identity,
    )

    with pytest.raises(
        _error(module),
        match="OLD_FAILURE_STAGING_IDENTITY_FORBIDDEN",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_rejects_old_v1_failure_staging_identity() -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(
        module,
        staging_identity=OLD_V1_STAGING,
    )

    with pytest.raises(
        _error(module),
        match="OLD_FAILURE_STAGING_IDENTITY_FORBIDDEN",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_rejects_old_v2_failure_staging_identity() -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(
        module,
        staging_identity=OLD_V2_STAGING,
    )

    with pytest.raises(
        _error(module),
        match="OLD_FAILURE_STAGING_IDENTITY_FORBIDDEN",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_requires_new_head_bound_staging_identity() -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(
        module,
        staging_identity=(
            "failure_memory_foundation_v1_"
            "sha_authority_correction_v1_deadbee"
        ),
    )

    with pytest.raises(
        _error(module),
        match="NEW_STAGING_IDENTITY_MISMATCH",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_rejects_preexisting_new_staging_root() -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(
        module,
        staging_exists=True,
    )

    with pytest.raises(
        _error(module),
        match="NEW_STAGING_ROOT_ALREADY_EXISTS",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_rejects_symlink_staging_root() -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(
        module,
        staging_is_symlink=True,
    )

    with pytest.raises(
        _error(module),
        match="NEW_STAGING_ROOT_SYMLINK_FORBIDDEN",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_requires_correction_evidence() -> None:
    module = _wrapper()
    snapshot_type = getattr(
        module,
        "RetryWrapperCandidateSnapshotV1",
    )

    snapshot = snapshot_type(
        branch=EXPECTED_BRANCH,
        head=TASK3_HEAD,
        worktree_clean=True,
        requested_staging_identity=FROZEN_NEW_STAGING,
        requested_staging_exists=False,
        requested_staging_is_symlink=False,
        correction_evidence=None,
        authority_config=_valid_authority_config(),
    )

    with pytest.raises(
        _error(module),
        match="CORRECTION_EVIDENCE_REQUIRED",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_rejects_non_equal_correction_evidence() -> None:
    module = _wrapper()
    evidence = _valid_evidence()
    evidence["production_vs_historical_bytes_equal"] = False

    snapshot = _valid_snapshot(
        module,
        correction_evidence=evidence,
    )

    with pytest.raises(
        _error(module),
        match="CORRECTION_EVIDENCE_THREE_WAY_EQUALITY_REQUIRED",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_rejects_v1_authority_config() -> None:
    module = _wrapper()

    v1 = {
        "schema": "TASK_ACCESS_REGENERATION_CONFIG_V1",
        "access_policy_id": "MEMORY_TASK_ACCESS_V2_1",
    }

    snapshot = _valid_snapshot(
        module,
        authority_config=v1,
    )

    with pytest.raises(
        _error(module),
        match="AUTHORITY_CONFIG_V1_REJECTED",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_requires_task1_bound_v2_authority_config() -> None:
    module = _wrapper()
    config = _valid_authority_config()
    config["sha_authority_correction_design_commit"] = "0" * 40

    snapshot = _valid_snapshot(
        module,
        authority_config=config,
    )

    with pytest.raises(
        _error(module),
        match="AUTHORITY_CONFIG_TASK1_BINDING_MISMATCH",
    ):
        _validate(module, snapshot)


def test_retry_wrapper_requires_exact_260766_authority() -> None:
    module = _wrapper()
    config = _valid_authority_config()
    config["approved_exact_contract_protected_sha256"] = "0" * 64

    snapshot = _valid_snapshot(
        module,
        authority_config=config,
    )

    with pytest.raises(
        _error(module),
        match="AUTHORITY_CONFIG_EXACT_SHA_MISMATCH",
    ):
        _validate(module, snapshot)


@pytest.mark.parametrize(
    ("branch", "head", "clean", "expected_code"),
    [
        (
            "wrong/branch",
            TASK3_HEAD,
            True,
            "BRANCH_MISMATCH",
        ),
        (
            EXPECTED_BRANCH,
            "0" * 40,
            True,
            "HEAD_MISMATCH",
        ),
        (
            EXPECTED_BRANCH,
            TASK3_HEAD,
            False,
            "WORKTREE_NOT_CLEAN",
        ),
    ],
)
def test_retry_wrapper_requires_clean_fixed_head(
    branch: str,
    head: str,
    clean: bool,
    expected_code: str,
) -> None:
    module = _wrapper()

    snapshot = _valid_snapshot(
        module,
        branch=branch,
        head=head,
        clean=clean,
    )

    with pytest.raises(
        _error(module),
        match=expected_code,
    ):
        _validate(module, snapshot)


def test_retry_wrapper_valid_snapshot_is_candidate_only() -> None:
    module = _wrapper()
    snapshot = _valid_snapshot(module)

    result = _validate(module, snapshot)

    assert result["candidate_valid"] is True
    assert result["real_materialization_authorized"] is False
    assert result["create_staging_root"] is False
    assert result["staging_identity"] == FROZEN_NEW_STAGING


def test_retry_wrapper_candidate_does_not_execute_real_materialization() -> None:
    module = _wrapper()

    source = WRAPPER_PATH.read_text(
        encoding="utf-8"
    )

    forbidden = (
        "materialize_task_access(",
        "materialize_primary_policy_contract(",
        "os.mkdir(",
        "os.makedirs(",
        ".mkdir(",
        "shutil.copy",
        "copy2(",
        "copyfile(",
    )
    for token in forbidden:
        assert token not in source

    assert getattr(
        module,
        "REAL_MATERIALIZATION_APPROVED",
        None,
    ) is False


def test_retry_wrapper_cli_is_dry_run_only(
    tmp_path: Path,
) -> None:
    _wrapper()

    request = {
        "branch": EXPECTED_BRANCH,
        "head": TASK3_HEAD,
        "worktree_clean": True,
        "requested_staging_identity": FROZEN_NEW_STAGING,
        "requested_staging_exists": False,
        "requested_staging_is_symlink": False,
        "correction_evidence": _valid_evidence(),
        "authority_config": _valid_authority_config(),
    }

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(request),
        encoding="utf-8",
    )

    sentinel = tmp_path / FROZEN_NEW_STAGING
    assert not sentinel.exists()

    result = subprocess.run(
        [
            sys.executable,
            str(WRAPPER_PATH),
            "--snapshot-json",
            str(request_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, (
        result.stdout + result.stderr
    )
    assert (
        "TASK_ACCESS_SHA_CORRECTION_RETRY_CANDIDATE_PASS"
        in result.stdout
    )
    assert not sentinel.exists()
