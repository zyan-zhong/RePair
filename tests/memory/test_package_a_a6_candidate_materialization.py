from dataclasses import replace
import importlib.util
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import sha256_bytes
from pchsi.memory.candidate_materialization import (
    CandidateMaterializationItemV1,
    audit_candidate_directory_v1,
    candidate_id_for_item_v1,
    materialize_candidate_item_v1,
)
from pchsi.memory.lifecycle_relations import (
    EvaluationContaminationStatusV1,
)


def _helpers():
    path = Path("tests/memory/package_a_test_helpers.py")
    spec = importlib.util.spec_from_file_location(
        "_pa_helpers_a6",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_assembly(existing, builder_module, experience):
    assembly = existing._assembly_input(
        builder_module,
        (experience,),
    )
    applicability = assembly.applicability
    safe_applicability = replace(
        applicability,
        activation=tuple(
            replace(
                clause,
                condition_text="activation condition is satisfied",
            )
            for clause in applicability.activation
        ),
        release=tuple(
            replace(
                clause,
                condition_text="release condition becomes satisfied",
            )
            for clause in applicability.release
        ),
    )
    return replace(
        assembly,
        applicability=safe_applicability,
    )


def _item_from_assembly(
    *,
    tmp_path,
    experience,
    assembly,
):
    ep = (tmp_path / "experience.json").resolve()
    ap = (tmp_path / "assembly.json").resolve()

    ep.write_bytes(experience.canonical_bytes())
    ap.write_bytes(assembly.canonical_bytes())

    esha = sha256_bytes(ep.read_bytes())
    asha = sha256_bytes(ap.read_bytes())
    status = EvaluationContaminationStatusV1.CLEAN

    cid = candidate_id_for_item_v1(
        source_experience_sha256s=(esha,),
        assembly_registration_sha256=asha,
        previous_record_sha256=None,
        evaluation_contamination_status=status,
    )

    item = CandidateMaterializationItemV1(
        candidate_id=cid,
        source_experience_paths=(str(ep),),
        source_experience_sha256s=(esha,),
        assembly_registration_path=str(ap),
        assembly_registration_sha256=asha,
        previous_record_path=None,
        previous_record_sha256=None,
        evaluation_contamination_status=status,
    )
    return item


def test_staging_materialization_is_content_bound_and_no_clobber(
    tmp_path,
):
    h = _helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()

    assembly = _safe_assembly(
        existing,
        builder_module,
        experience,
    )
    item = _item_from_assembly(
        tmp_path=tmp_path,
        experience=experience,
        assembly=assembly,
    )

    out = tmp_path / "out"
    out.mkdir()

    _, source_report, bundle, final = (
        materialize_candidate_item_v1(
            item=item,
            tokenizer=h.TinyTokenizer(),
            output_root=out,
            execute=True,
        )
    )

    assert source_report.status == "VERIFIED"
    assert bundle is not None
    assert bundle.status == "ELIGIBLE"
    assert bundle.failure_codes == ()
    assert bundle.governed_record is not None
    assert final is not None

    audit_candidate_directory_v1(final)

    assert (final / "initial_record.json").is_file()
    assert (final / "source_integrity_report.json").is_file()
    assert (final / "governed_record.json").is_file()
    assert (final / "retrieval_key.json").is_file()
    assert (final / "fm1.json").is_file()
    assert (final / "fm2.json").is_file()
    assert (
        final / "fm3_empty_recovery_integrity.json"
    ).is_file()

    with pytest.raises(FileExistsError):
        materialize_candidate_item_v1(
            item=item,
            tokenizer=h.TinyTokenizer(),
            output_root=out,
            execute=True,
        )


def test_identity_leaking_candidate_remains_descriptively_ineligible(
    tmp_path,
):
    h = _helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()

    unsafe_assembly = existing._assembly_input(
        builder_module,
        (experience,),
    )

    assert any(
        clause.registration_id in clause.condition_text
        for clause in (
            *unsafe_assembly.applicability.activation,
            *unsafe_assembly.applicability.release,
        )
    )

    item = _item_from_assembly(
        tmp_path=tmp_path,
        experience=experience,
        assembly=unsafe_assembly,
    )

    out = tmp_path / "unsafe-out"
    out.mkdir()

    _, source_report, bundle, final = (
        materialize_candidate_item_v1(
            item=item,
            tokenizer=h.TinyTokenizer(),
            output_root=out,
            execute=True,
        )
    )

    assert source_report.status == "VERIFIED"
    assert bundle is not None
    assert bundle.status == "INELIGIBLE"
    assert bundle.failure_codes == ("FM2_NOT_ELIGIBLE",)
    assert bundle.governed_record is None
    assert final is not None

    audit_candidate_directory_v1(final)

    assert (final / "initial_record.json").is_file()
    assert (final / "source_integrity_report.json").is_file()
    assert not (final / "governed_record.json").exists()
    assert not (final / "fm2.json").exists()
