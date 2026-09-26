"""RED-only tests for Task 1 SHA-authority correction evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "src/pchsi/memory/task_access_sha_authority_correction.py"
SCHEMA_PATH = REPO_ROOT / "configs/memory/schemas/task_access_sha_authority_correction_evidence_v1.json"
BUILDER_PATH = REPO_ROOT / "scripts/memory/build_task_access_sha_authority_correction_evidence_v1.py"

HISTORICAL_SHA = "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
EXACT_SHA = "260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea"
SOURCE_FINGERPRINT = "d657703df1033a9797e7e9a18b3eb989e49dd3391a468d1a65f6edff3e609e24"
CORRECTION_BASE = "1a0feeef8085ba124fa79e72c38fea90b812d9f9"
CORRECTION_DESIGN_COMMIT = "a" * 40
ROLE_COUNTS = (
    ("TRAIN_MEMORY_SOURCE", 4),
    ("TRAIN_RETRIEVAL_DEV", 2),
    ("VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED", 1),
    ("VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED", 1),
)
REPRO_IDS = (
    "CURRENT_PRODUCTION_IN_MEMORY",
    "HISTORICAL_PURE_CORE",
    "STANDALONE_CANONICAL_SERIALIZER",
)


def _target():
    if not MODULE_PATH.is_file():
        pytest.fail("TASK1_RED_MISSING_CORRECTION_MODULE", pytrace=False)
    name = "pchsi_task_access_sha_authority_correction_test_target"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec is not None, "TASK1_RED_MODULE_SPEC_UNAVAILABLE"
    assert spec.loader is not None, "TASK1_RED_MODULE_LOADER_UNAVAILABLE"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _api(module, name: str):
    assert hasattr(module, name), f"TASK1_RED_MISSING_API={name}"
    return getattr(module, name)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fixture(
    tmp_path: Path,
    *,
    historical_bytes: bytes | None = None,
    standalone_bytes: bytes | None = None,
    declared_override: dict[str, str] | None = None,
    reproduction_ids: tuple[str, ...] = REPRO_IDS,
    historical_sha: str = HISTORICAL_SHA,
    exact_sha: str | None = None,
    role_counts: tuple[tuple[str, int], ...] = ROLE_COUNTS,
):
    module = _target()
    ReproductionInputV1 = _api(module, "ReproductionInputV1")
    IncidentEvidenceInputV1 = _api(module, "IncidentEvidenceInputV1")
    CorrectionEvidenceRequestV1 = _api(module, "CorrectionEvidenceRequestV1")

    production = b'{"record":"synthetic-protected"}\n'
    if exact_sha is None:
        exact_sha = _sha(production)
    historical = production if historical_bytes is None else historical_bytes
    standalone = production if standalone_bytes is None else standalone_bytes
    payloads = {
        "CURRENT_PRODUCTION_IN_MEMORY": production,
        "HISTORICAL_PURE_CORE": historical,
        "STANDALONE_CANONICAL_SERIALIZER": standalone,
    }
    declared_override = declared_override or {}
    reproductions = []
    for index, reproduction_id in enumerate(reproduction_ids, 1):
        implementation = tmp_path / f"implementation_{index}.py"
        implementation.write_text(f"# {reproduction_id}\n", encoding="utf-8")
        output = tmp_path / f"canonical_{index}.jsonl"
        payload = payloads.get(reproduction_id, b'{"record":"unknown"}\n')
        output.write_bytes(payload)
        reproductions.append(
            ReproductionInputV1(
                reproduction_id=reproduction_id,
                implementation_identity=f"SYNTHETIC_{reproduction_id}",
                implementation_path=implementation,
                canonical_output_path=output,
                declared_observed_protected_sha256=declared_override.get(
                    reproduction_id, _sha(payload)
                ),
                source_fingerprint=SOURCE_FINGERPRINT,
                record_count=8,
                role_counts=role_counts,
            )
        )

    incidents = []
    for artifact_id, payload in (
        ("V2_MATERIALIZATION_STOP", b'{"stop_code":"TASK_ACCESS_MATERIALIZER_RETURN_CODE_2"}\n'),
        ("V2_SOURCE_INTEGRITY_PRE", b'{"schema":"FAILURE_MEMORY_SOURCE_STATE_V1"}\n'),
        ("V2_TASK_MATERIALIZER_STDERR", b"TASK_ACCESS_MATERIALIZATION_STOP=PROTECTED_REGENERATION_SHA256_MISMATCH\n"),
        ("V2_TASK_MATERIALIZER_STDOUT", b""),
    ):
        path = tmp_path / f"{artifact_id}.bin"
        path.write_bytes(payload)
        incidents.append(
            IncidentEvidenceInputV1(
                artifact_id=artifact_id,
                path=path,
                expected_sha256=_sha(payload),
            )
        )

    request = CorrectionEvidenceRequestV1(
        correction_base_commit=CORRECTION_BASE,
        correction_design_commit=CORRECTION_DESIGN_COMMIT,
        access_policy_id="MEMORY_TASK_ACCESS_V2_1",
        historical_design_candidate_sha256=historical_sha,
        proposed_exact_contract_protected_sha256=exact_sha,
        dataset_source_fingerprint=SOURCE_FINGERPRINT,
        record_count=8,
        role_counts=role_counts,
        reproductions=tuple(reproductions),
        incident_evidence=tuple(incidents),
    )
    return module, request


def _build(module, request):
    return _api(module, "build_correction_evidence")(request)


def _error(module):
    return _api(module, "TaskAccessShaAuthorityCorrectionError")


def test_correction_evidence_schema_file_is_registered() -> None:
    assert SCHEMA_PATH.is_file(), "TASK1_RED_MISSING_EVIDENCE_SCHEMA"
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert payload.get("$id") == "TASK_ACCESS_SHA_AUTHORITY_CORRECTION_EVIDENCE_V1"
    required = set(payload.get("required", ()))
    assert {
        "schema", "correction_base_commit", "correction_design_commit",
        "historical_design_candidate_sha256",
        "proposed_exact_contract_protected_sha256", "reproductions",
        "production_vs_historical_bytes_equal",
        "production_vs_standalone_bytes_equal", "all_three_sha256_equal",
        "three_way_sha_matches_proposed_authority",
        "incident_evidence", "conclusion",
    } <= required
    assert payload["properties"]["three_way_sha_matches_proposed_authority"] == {
        "const": True
    }, "TASK1_HARDENING_RED_SCHEMA_AUTHORITY_MATCH_NOT_CONST_TRUE"


def test_correction_evidence_builder_cli_is_registered() -> None:
    assert BUILDER_PATH.is_file(), "TASK1_RED_MISSING_EVIDENCE_BUILDER"


def test_correction_evidence_requires_three_registered_reproductions(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path, reproduction_ids=REPRO_IDS[:2])
    with pytest.raises(_error(module), match="REPRODUCTION_SET_INVALID"):
        _build(module, request)


def test_correction_evidence_computes_sha_from_canonical_bytes(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path)
    result = _build(module, request)
    payload = result.payload
    expected = _sha(b'{"record":"synthetic-protected"}\n')
    assert payload["all_three_sha256_equal"] is True
    assert payload["production_vs_historical_bytes_equal"] is True
    assert payload["production_vs_standalone_bytes_equal"] is True
    for item in payload["reproductions"]:
        assert item["observed_protected_sha256"] == expected
        assert item["canonical_output_artifact_sha256"] == expected
        assert item["canonical_output_byte_count"] == len(b'{"record":"synthetic-protected"}\n')
        assert len(item["implementation_sha256"]) == 64


def test_correction_evidence_rejects_declared_sha_that_disagrees_with_bytes(tmp_path: Path) -> None:
    module, request = _fixture(
        tmp_path,
        declared_override={"CURRENT_PRODUCTION_IN_MEMORY": "0" * 64},
    )
    with pytest.raises(_error(module), match="DECLARED_PROTECTED_SHA256_MISMATCH"):
        _build(module, request)


def test_correction_evidence_requires_production_historical_byte_equality(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path, historical_bytes=b'{"record":"different-historical"}\n')
    with pytest.raises(_error(module), match="PRODUCTION_HISTORICAL_BYTES_MISMATCH"):
        _build(module, request)


def test_correction_evidence_requires_production_standalone_byte_equality(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path, standalone_bytes=b'{"record":"different-standalone"}\n')
    with pytest.raises(_error(module), match="PRODUCTION_STANDALONE_BYTES_MISMATCH"):
        _build(module, request)


def test_correction_evidence_binds_role_counts_and_record_count(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path)
    result = _build(module, request)
    assert result.payload["record_count"] == 8
    assert result.payload["role_counts"] == dict(ROLE_COUNTS)
    for item in result.payload["reproductions"]:
        assert item["record_count"] == 8
        assert item["role_counts"] == dict(ROLE_COUNTS)
        assert item["source_fingerprint"] == SOURCE_FINGERPRINT


def test_correction_evidence_binds_incident_artifact_hashes(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path)
    result = _build(module, request)
    observed = {item["artifact_id"]: item for item in result.payload["incident_evidence"]}
    assert set(observed) == {
        "V2_MATERIALIZATION_STOP", "V2_SOURCE_INTEGRITY_PRE",
        "V2_TASK_MATERIALIZER_STDERR", "V2_TASK_MATERIALIZER_STDOUT",
    }
    for artifact_id, item in observed.items():
        assert len(item["sha256"]) == 64
        if artifact_id == "V2_TASK_MATERIALIZER_STDOUT":
            assert item["byte_count"] == 0
        else:
            assert item["byte_count"] > 0


def test_correction_evidence_preserves_historical_candidate_role(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path)
    payload = _build(module, request).payload
    assert payload["historical_design_candidate_sha256"] == HISTORICAL_SHA
    assert payload["proposed_exact_contract_protected_sha256"] == _sha(
        b'{"record":"synthetic-protected"}\n'
    )
    assert payload["historical_candidate_role"] == "PRESERVED_HISTORICAL_DESIGN_CANDIDATE"
    assert payload["historical_candidate_execution_authority"] is False


def test_correction_v1_instance_requires_6dcd_not_equal_260766(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path, historical_sha=EXACT_SHA, exact_sha=EXACT_SHA)
    with pytest.raises(_error(module), match="CORRECTION_V1_DIGESTS_MUST_DIFFER"):
        _build(module, request)


def test_correction_evidence_no_clobber(tmp_path: Path) -> None:
    module, request = _fixture(tmp_path)
    write = _api(module, "write_correction_evidence")
    output = tmp_path / "evidence.json"
    first = write(request, output)
    first_bytes = output.read_bytes()
    assert first.canonical_bytes == first_bytes
    assert first_bytes.endswith(b"\n")
    with pytest.raises(_error(module), match="OUTPUT_ALREADY_EXISTS"):
        write(request, output)
    assert output.read_bytes() == first_bytes


def test_correction_evidence_rejects_three_way_sha_not_matching_proposed_authority(
    tmp_path: Path,
) -> None:
    module, request = _fixture(tmp_path, exact_sha="f" * 64)
    try:
        _build(module, request)
    except _error(module) as exc:
        assert str(exc) == "THREE_WAY_SHA_DOES_NOT_MATCH_PROPOSED_AUTHORITY"
        return
    pytest.fail(
        "TASK1_HARDENING_RED_MISSING="
        "THREE_WAY_SHA_DOES_NOT_MATCH_PROPOSED_AUTHORITY"
    )


def test_correction_evidence_requires_role_counts_sum_to_record_count(
    tmp_path: Path,
) -> None:
    bad_counts = (
        ("TRAIN_MEMORY_SOURCE", 5),
        ("TRAIN_RETRIEVAL_DEV", 2),
        ("VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED", 1),
        ("VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED", 1),
    )
    module, request = _fixture(tmp_path, role_counts=bad_counts)
    try:
        _build(module, request)
    except _error(module) as exc:
        assert str(exc) == "ROLE_COUNTS_RECORD_COUNT_MISMATCH"
        return
    pytest.fail("TASK1_HARDENING_RED_MISSING=ROLE_COUNTS_RECORD_COUNT_MISMATCH")


def test_correction_evidence_requires_exact_registered_role_keys(
    tmp_path: Path,
) -> None:
    wrong_keys = (
        ("TRAIN_MEMORY_SOURCE", 4),
        ("TRAIN_RETRIEVAL_DEV", 2),
        ("VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED", 1),
        ("WRONG_OOD_ROLE", 1),
    )
    module, request = _fixture(tmp_path, role_counts=wrong_keys)
    try:
        _build(module, request)
    except _error(module) as exc:
        assert str(exc) == "ROLE_COUNTS_KEYS_INVALID"
        return
    pytest.fail("TASK1_HARDENING_RED_MISSING=ROLE_COUNTS_KEYS_INVALID")


def test_correction_evidence_requires_four_registered_incident_artifacts(
    tmp_path: Path,
) -> None:
    module, request = _fixture(tmp_path)
    request_type = type(request)
    incomplete = request_type(
        correction_base_commit=request.correction_base_commit,
        correction_design_commit=request.correction_design_commit,
        access_policy_id=request.access_policy_id,
        historical_design_candidate_sha256=request.historical_design_candidate_sha256,
        proposed_exact_contract_protected_sha256=request.proposed_exact_contract_protected_sha256,
        dataset_source_fingerprint=request.dataset_source_fingerprint,
        record_count=request.record_count,
        role_counts=request.role_counts,
        reproductions=request.reproductions,
        incident_evidence=request.incident_evidence[:-1],
    )
    try:
        _build(module, incomplete)
    except _error(module) as exc:
        assert str(exc) == "INCIDENT_EVIDENCE_SET_INVALID"
        return
    pytest.fail("TASK1_HARDENING_RED_MISSING=INCIDENT_EVIDENCE_SET_INVALID")
