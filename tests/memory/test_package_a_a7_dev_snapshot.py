from dataclasses import replace
import importlib.util
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import sha256_bytes
from pchsi.memory.candidate_materialization import (
    CandidateMaterializationItemV1,
    candidate_id_for_item_v1,
    materialize_candidate_item_v1,
)
from pchsi.memory.dev_descriptive_snapshot import (
    build_memory_dev_descriptive_snapshot_v1,
    publish_memory_dev_descriptive_snapshot_v1,
)
from pchsi.memory.lifecycle_relations import (
    EvaluationContaminationStatusV1,
)


def _helpers():
    path = Path("tests/memory/package_a_test_helpers.py")
    spec = importlib.util.spec_from_file_location(
        "_pa_helpers_a7",
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
    return replace(
        assembly,
        applicability=replace(
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
        ),
    )


def _candidate(tmp_path):
    h = _helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()

    assembly = _safe_assembly(
        existing,
        builder_module,
        experience,
    )

    ep = (tmp_path / "e.json").resolve()
    ap = (tmp_path / "a.json").resolve()
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
        cid,
        (str(ep),),
        (esha,),
        str(ap),
        asha,
        None,
        None,
        status,
    )

    candidates = tmp_path / "candidates"
    candidates.mkdir()

    _, _, bundle, final = materialize_candidate_item_v1(
        item=item,
        tokenizer=h.TinyTokenizer(),
        output_root=candidates,
        execute=True,
    )

    assert bundle is not None
    assert bundle.status == "ELIGIBLE"
    assert final is not None

    return final


def test_dev_snapshot_excludes_fm3_and_is_immutable(
    tmp_path,
):
    candidate = _candidate(tmp_path)

    snapshot, files = (
        build_memory_dev_descriptive_snapshot_v1(
            candidate_directories=(candidate,),
            source_materialization_manifest_sha256="a" * 64,
            tokenizer_id="tiny",
            tokenizer_revision="v1",
        )
    )

    root = tmp_path / "snapshots"
    root.mkdir()

    published = publish_memory_dev_descriptive_snapshot_v1(
        output_root=root,
        snapshot=snapshot,
        member_files=files,
    )

    member_dir = (
        published
        / snapshot.members[0].relative_directory
    )

    assert (member_dir / "fm2.json").is_file()
    assert not (member_dir / "fm3.json").exists()

    with pytest.raises(FileExistsError):
        publish_memory_dev_descriptive_snapshot_v1(
            output_root=root,
            snapshot=snapshot,
            member_files=files,
        )
