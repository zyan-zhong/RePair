from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.descriptive_eligibility import govern_descriptive_dev_record_v1
from pchsi.memory.lifecycle_relations import EvaluationContaminationStatusV1
from pchsi.memory.policy_projection import build_failure_memory_policy_projection_v1
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
    ProceduralMemoryAssemblyInputV1,
    build_procedural_failure_memory_record_v1,
)
from pchsi.memory.procedural_record import AssemblyRegistrationBindingV1, MemoryEvidenceRefV1
from pchsi.memory.projection_common import PolicyTokenizerCounterV1, ProjectionClassV1
from pchsi.memory.retrieval_key import build_memory_retrieval_key_v1
from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1
from pchsi.memory.source_integrity import audit_memory_source_integrity_v1


def _regular(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be regular non-symlink file")
    return path


def _dir(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} must be existing non-symlink directory")
    return path


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("os.write made no progress")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


@dataclass(frozen=True, slots=True)
class CandidateMaterializationItemV1:
    candidate_id: str
    source_experience_paths: tuple[str, ...]
    source_experience_sha256s: tuple[str, ...]
    assembly_registration_path: str
    assembly_registration_sha256: str
    previous_record_path: str | None
    previous_record_sha256: str | None
    evaluation_contamination_status: EvaluationContaminationStatusV1

    def __post_init__(self) -> None:
        require_lower_sha256("candidate_id", self.candidate_id)
        if len(self.source_experience_paths) != len(self.source_experience_sha256s):
            raise ValueError("source path/SHA count mismatch")
        if not self.source_experience_paths:
            raise ValueError("source experiences required")
        for raw, sha in zip(self.source_experience_paths, self.source_experience_sha256s):
            if not Path(raw).is_absolute():
                raise ValueError("source experience paths must be absolute")
            require_lower_sha256("source experience SHA", sha)
        if not Path(self.assembly_registration_path).is_absolute():
            raise ValueError("assembly registration path must be absolute")
        require_lower_sha256("assembly_registration_sha256", self.assembly_registration_sha256)
        if self.previous_record_path is None:
            if self.previous_record_sha256 is not None:
                raise ValueError("previous SHA requires previous path")
        else:
            if not Path(self.previous_record_path).is_absolute():
                raise ValueError("previous record path must be absolute")
            require_lower_sha256("previous_record_sha256", self.previous_record_sha256)
        expected = candidate_id_for_item_v1(
            source_experience_sha256s=self.source_experience_sha256s,
            assembly_registration_sha256=self.assembly_registration_sha256,
            previous_record_sha256=self.previous_record_sha256,
            evaluation_contamination_status=self.evaluation_contamination_status,
        )
        if self.candidate_id != expected:
            raise ValueError("candidate_id mismatch")


def candidate_id_for_item_v1(
    *,
    source_experience_sha256s: tuple[str, ...],
    assembly_registration_sha256: str,
    previous_record_sha256: str | None,
    evaluation_contamination_status: EvaluationContaminationStatusV1,
) -> str:
    return sha256_bytes(
        b"FAILURE_MEMORY_MATERIALIZATION_ITEM_V1\0"
        + canonical_json_bytes({
            "source_experience_sha256s": list(source_experience_sha256s),
            "assembly_registration_sha256": assembly_registration_sha256,
            "previous_record_sha256": previous_record_sha256,
            "evaluation_contamination_status": evaluation_contamination_status.value,
        })
    )


def _load_canonical(path: Path, parser, expected_sha: str, label: str):
    path = _regular(path, label)
    data = path.read_bytes()
    if sha256_bytes(data) != expected_sha:
        raise ValueError(f"{label} SHA mismatch")
    value = parser(data)
    if value.canonical_bytes() != data:
        raise ValueError(f"{label} must be canonical bytes")
    return value


def materialize_candidate_item_v1(
    *,
    item: CandidateMaterializationItemV1,
    tokenizer: PolicyTokenizerCounterV1,
    output_root: Path | None,
    execute: bool,
):
    assembly = _load_canonical(
        Path(item.assembly_registration_path),
        ProceduralMemoryAssemblyInputV1.from_json,
        item.assembly_registration_sha256,
        "assembly registration",
    )
    experiences = tuple(
        _load_canonical(
            Path(path),
            SequenceFailureExperienceV1.from_json,
            sha,
            "source experience",
        )
        for path, sha in zip(
            item.source_experience_paths,
            item.source_experience_sha256s,
            strict=True,
        )
    )
    registration_binding = AssemblyRegistrationBindingV1(
        schema_id="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        registration_id=assembly.registration_id,
        assembly_registration_sha256=item.assembly_registration_sha256,
        lineage_registration_ref=MemoryEvidenceRefV1(
            source_kind="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
            source_id=assembly.registration_id,
            source_sha256=item.assembly_registration_sha256,
        ),
    )
    previous = None
    if item.previous_record_path is not None:
        previous = _load_canonical(
            Path(item.previous_record_path),
            ProceduralFailureMemoryRecordV1.from_json,
            item.previous_record_sha256,
            "previous record",
        )

    record = build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=registration_binding,
        source_experiences=experiences,
        previous_record=previous,
    )
    source_report = audit_memory_source_integrity_v1(
        record=record,
        registered_experiences=experiences,
    )
    bundle = None
    retrieval_key = None
    fm3 = None
    if len(experiences) == 1:
        bundle = govern_descriptive_dev_record_v1(
            record=record,
            source_report=source_report,
            source_experience=experiences[0],
            tokenizer=tokenizer,
            evaluation_contamination_status=item.evaluation_contamination_status,
        )
        if bundle.governed_record is not None:
            retrieval_key = build_memory_retrieval_key_v1(bundle.governed_record)
            fm3 = build_failure_memory_policy_projection_v1(
                record=bundle.governed_record,
                projection_class=ProjectionClassV1.FM3,
                tokenizer=tokenizer,
                hard_ceiling=256,
            )
            if (
                fm3.policy_visible_payload is not None
                and fm3.policy_visible_payload.recovery_procedure
            ):
                raise ValueError("Package A FM3 must not expose recovery")

    files = {
        "initial_record.json": record.canonical_bytes(),
        "source_integrity_report.json": source_report.canonical_bytes(),
    }
    if bundle is not None:
        files["descriptive_eligibility.json"] = canonical_json_bytes({
            "status": bundle.status,
            "failure_codes": list(bundle.failure_codes),
            "fm1_build_disposition": (
                None
                if bundle.fm1 is None
                else bundle.fm1.build_disposition.value
            ),
            "fm2_build_disposition": (
                None
                if bundle.fm2 is None
                else bundle.fm2.build_disposition.value
            ),
        })
        if bundle.governed_record is not None:
            files.update({
                "governed_record.json": bundle.governed_record.canonical_bytes(),
                "retrieval_key.json": retrieval_key.canonical_bytes(),
                "fm1.json": bundle.fm1.canonical_bytes(),
                "fm2.json": bundle.fm2.canonical_bytes(),
                "fm3_empty_recovery_integrity.json": fm3.canonical_bytes(),
            })

    final = None
    if execute:
        if output_root is None:
            raise ValueError("execute requires output_root")
        root = _dir(output_root, "output root")
        final = root / item.candidate_id
        if final.exists() or final.is_symlink():
            raise FileExistsError(str(final))
        final.mkdir(mode=0o700)
        for name, data in sorted(files.items()):
            _write_once(final / name, data)
        manifest = canonical_json_bytes({
            "schema_id": "FAILURE_MEMORY_STAGING_CANDIDATE_ARTIFACTS_V1",
            "schema_version": 1,
            "candidate_id": item.candidate_id,
            "files": [
                {"name": name, "sha256": sha256_bytes(data), "size": len(data)}
                for name, data in sorted(files.items())
            ],
        })
        _write_once(final / "artifact_manifest.json", manifest)
        _write_once(
            final / "artifact_manifest.sha256",
            (sha256_bytes(manifest) + "\n").encode("ascii"),
        )
    return record, source_report, bundle, final


def audit_candidate_directory_v1(path: Path) -> None:
    path = _dir(path, "candidate directory")
    manifest_path = _regular(path / "artifact_manifest.json", "artifact manifest")
    sidecar = _regular(path / "artifact_manifest.sha256", "artifact manifest SHA")
    manifest_bytes = manifest_path.read_bytes()
    if sha256_bytes(manifest_bytes) != sidecar.read_text(encoding="ascii").strip():
        raise ValueError("artifact manifest sidecar mismatch")
    p = strict_json_loads(manifest_bytes)
    if not isinstance(p, dict) or p.get("schema_id") != "FAILURE_MEMORY_STAGING_CANDIDATE_ARTIFACTS_V1":
        raise ValueError("artifact manifest invalid")
    expected = {"artifact_manifest.json", "artifact_manifest.sha256"}
    for item in p["files"]:
        name = item["name"]
        expected.add(name)
        file_path = _regular(path / name, "candidate artifact")
        if sha256_file(file_path) != item["sha256"] or file_path.stat().st_size != item["size"]:
            raise ValueError(f"candidate artifact mismatch: {name}")
    observed = {x.name for x in path.iterdir()}
    if observed != expected:
        raise ValueError("candidate artifact census mismatch")
