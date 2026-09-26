from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess

import pytest

from pchsi.security.canonical import (
    canonical_json_bytes,
    strict_json_loadb,
)
from pchsi.security.contracts import (
    BootstrapContract,
    BootstrapState,
    LandlockPathRule,
    LandlockPolicy,
    LocalProbeDiagnostic,
    ProbeEvidence,
    ProbeProfileManifest,
    RuntimeManifest,
    SealedSourceManifest,
    SeccompFilterManifest,
    SemanticProbeResult,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "canonical_vectors.json"
)
SCHEMA_ROOT = (
    REPO_ROOT
    / "configs"
    / "security"
    / "schemas"
)
NATIVE_ROOT = (
    REPO_ROOT
    / "native"
    / "s1_backend_probe"
)


@pytest.fixture(scope="session")
def c_json_validator(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    output = (
        tmp_path_factory.mktemp("strict-json-c")
        / "strict-json-validator"
    )

    result = subprocess.run(
        [
            "/usr/bin/cc",
            "-D_GNU_SOURCE",
            f"-I{NATIVE_ROOT / 'include'}",
            "-std=c17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wpedantic",
            "-Wconversion",
            "-Wshadow",
            str(NATIVE_ROOT / "src" / "strict_json.c"),
            str(
                NATIVE_ROOT
                / "tests"
                / "test_strict_json.c"
            ),
            "-o",
            str(output),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    return output


def _vectors() -> list[dict[str, object]]:
    payload = json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    return list(payload["vectors"])


@pytest.mark.parametrize(
    "vector",
    _vectors(),
    ids=lambda vector: str(vector["id"]),
)
def test_c_validator_matches_shared_vectors(
    c_json_validator: Path,
    vector: dict[str, object],
) -> None:
    payload = bytes.fromhex(
        str(vector["input_hex"])
    )

    result = subprocess.run(
        [str(c_json_validator)],
        input=payload,
        check=False,
        capture_output=True,
    )

    first_token = (
        result.stdout.decode("ascii").split()[0]
    )

    assert first_token == vector["c_status"]
    assert (result.returncode == 0) is bool(
        vector["accepted"]
    )


def _sha(character: str) -> str:
    return character * 64


def _semantic_result(
    probe_id: str = "P1",
) -> SemanticProbeResult:
    return SemanticProbeResult(
        probe_id=probe_id,
        payload_sha256=_sha("1"),
        expected_outcome="SUCCESS",
        observed_outcome="SUCCESS",
        status="PASS",
    )


def _local_diagnostic(
    probe_id: str = "P1",
) -> LocalProbeDiagnostic:
    return LocalProbeDiagnostic(
        probe_id=probe_id,
        raw_errno=None,
        raw_signal=None,
        duration_microseconds=10,
        log_sha256=_sha("2"),
    )


def test_runtime_manifest_is_frozen_and_serializable() -> None:
    manifest = RuntimeManifest(
        schema_version="runtime_manifest_v1",
        python_binary_sha256=_sha("1"),
        stdlib_tree_semantics_sha256=_sha("2"),
        dynamic_linker_sha256=_sha("3"),
        shared_library_manifest_sha256=_sha("4"),
    )

    with pytest.raises(FrozenInstanceError):
        manifest.schema_version = "changed"  # type: ignore[misc]

    assert strict_json_loadb(
        canonical_json_bytes(manifest.to_dict())
    ) == manifest.to_dict()


def test_all_manifest_contracts_accept_valid_hashes() -> None:
    sealed = SealedSourceManifest(
        schema_version="sealed_source_manifest_v1",
        bootstrap_source_sha256=_sha("1"),
        collector_source_sha256=_sha("2"),
        source_copy_contract_sha256=_sha("3"),
    )
    seccomp = SeccompFilterManifest(
        schema_version="seccomp_filter_manifest_v1",
        architecture="x86_64",
        policy_sha256=_sha("4"),
        program_sha256=_sha("5"),
    )
    profile = ProbeProfileManifest(
        schema_version="probe_profile_manifest_v1",
        profile_id="production",
        contract_sha256=_sha("6"),
        seccomp_filter_sha256=_sha("7"),
    )

    assert sealed.to_dict()["collector_source_sha256"] == _sha("2")
    assert seccomp.to_dict()["architecture"] == "x86_64"
    assert profile.to_dict()["profile_id"] == "production"


@pytest.mark.parametrize(
    "bad_hash",
    [
        "",
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
    ],
)
def test_manifest_contracts_reject_invalid_sha256(
    bad_hash: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        RuntimeManifest(
            schema_version="runtime_manifest_v1",
            python_binary_sha256=bad_hash,
            stdlib_tree_semantics_sha256=_sha("2"),
            dynamic_linker_sha256=_sha("3"),
            shared_library_manifest_sha256=_sha("4"),
        )


def test_probe_evidence_requires_matching_unique_ids() -> None:
    with pytest.raises(
        ValueError,
        match="sets must match",
    ):
        ProbeEvidence(
            schema_version="probe_evidence_v1",
            semantic_evidence_sha256=_sha("3"),
            semantic_results=(
                _semantic_result("P1"),
            ),
            local_diagnostics=(
                _local_diagnostic("P2"),
            ),
        )


def test_probe_evidence_uses_tuples_and_is_serializable() -> None:
    evidence = ProbeEvidence(
        schema_version="probe_evidence_v1",
        semantic_evidence_sha256=_sha("3"),
        semantic_results=(
            _semantic_result(),
        ),
        local_diagnostics=(
            _local_diagnostic(),
        ),
    )

    assert isinstance(
        evidence.semantic_results,
        tuple,
    )
    assert isinstance(
        evidence.local_diagnostics,
        tuple,
    )
    assert strict_json_loadb(
        canonical_json_bytes(evidence.to_dict())
    ) == evidence.to_dict()


def test_probe_evidence_rejects_mutable_sequences() -> None:
    with pytest.raises(
        ValueError,
        match="semantic_results must be a tuple",
    ):
        ProbeEvidence(
            schema_version="probe_evidence_v1",
            semantic_evidence_sha256=_sha("3"),
            semantic_results=[  # type: ignore[arg-type]
                _semantic_result(),
            ],
            local_diagnostics=(
                _local_diagnostic(),
            ),
        )


def test_schema_files_are_strict_json_and_closed() -> None:
    expected = {
        "backend_probe_contract_v1.json",
        "backend_probe_execution_decision_v1.json",
        "runtime_manifest_v1.json",
        "sealed_source_manifest_v1.json",
        "seccomp_filter_manifest_v1.json",
        "probe_profile_manifest_v1.json",
        "probe_evidence_v1.json",
    }

    observed = {
        path.name
        for path in SCHEMA_ROOT.glob("*.json")
    }

    assert observed == expected

    for path in sorted(SCHEMA_ROOT.glob("*.json")):
        schema = strict_json_loadb(path.read_bytes())

        assert isinstance(schema, dict)
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["schema_version"] == 1
def test_bootstrap_contracts_are_frozen_and_serializable() -> None:
    rule = LandlockPathRule(
        path="/landlock/allowed",
        access_fs=1,
    )
    policy = LandlockPolicy(
        profile_id="S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1",
        minimum_abi=1,
        handled_access_fs=3,
        rules=(rule,),
        profile_sha256=_sha("8"),
    )
    state = BootstrapState(
        runtime_manifest_sha256=_sha("1"),
        bootstrap_filter_sha256=_sha("2"),
        collector_filter_sha256=_sha("3"),
        landlock_abi=3,
        landlock_enforced=True,
        mount_contract_verified=True,
        procfs_contract_verified=True,
        capability_contract_verified=True,
        fd_contract_verified=True,
        environment_contract_verified=True,
        inherited_fds=(0, 1, 2),
    )
    contract = BootstrapContract(
        runtime_manifest_sha256=_sha("1"),
        bootstrap_filter_sha256=_sha("2"),
        collector_filter_sha256=_sha("3"),
        minimum_landlock_abi=1,
        require_landlock_when_supported=True,
        allowed_fds=(0, 1, 2),
    )

    with pytest.raises(FrozenInstanceError):
        rule.path = "/changed"  # type: ignore[misc]

    assert strict_json_loadb(
        canonical_json_bytes(policy.to_dict())
    ) == policy.to_dict()
    assert state.inherited_fds == (0, 1, 2)
    assert strict_json_loadb(
        canonical_json_bytes(contract.to_dict())
    ) == contract.to_dict()


def test_landlock_policy_rejects_duplicate_rule_paths() -> None:
    rule = LandlockPathRule(
        path="/landlock/allowed",
        access_fs=1,
    )

    with pytest.raises(ValueError, match="duplicate"):
        LandlockPolicy(
            profile_id="S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1",
            minimum_abi=1,
            handled_access_fs=3,
            rules=(rule, rule),
            profile_sha256=_sha("8"),
        )


def test_bootstrap_contract_rejects_noncanonical_fd_set() -> None:
    with pytest.raises(ValueError, match="sorted"):
        BootstrapContract(
            runtime_manifest_sha256=_sha("1"),
            bootstrap_filter_sha256=_sha("2"),
            collector_filter_sha256=_sha("3"),
            minimum_landlock_abi=1,
            require_landlock_when_supported=True,
            allowed_fds=(0, 2, 1),
        )
