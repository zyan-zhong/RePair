from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from pchsi.memory.candidate_materialization import (
    audit_candidate_directory_v1,
    materialize_candidate_item_v1,
)
from pchsi.memory.descriptive_eligibility import (
    govern_descriptive_dev_record_v1,
)
from pchsi.memory.dev_descriptive_snapshot import (
    audit_memory_dev_descriptive_snapshot_v1,
    build_memory_dev_descriptive_snapshot_v1,
    publish_memory_dev_descriptive_snapshot_v1,
)
from pchsi.memory.lifecycle_relations import (
    EvaluationContaminationStatusV1,
)
from pchsi.memory.matched_raw_view import (
    FM1MatchedRawEpisodicViewV1,
)
from pchsi.memory.policy_projection import (
    FailureMemoryPolicyProjectionV1,
)
from pchsi.memory.projection_common import (
    ProjectionBuildDispositionV1,
)
from pchsi.memory.source_integrity import (
    audit_memory_source_integrity_v1,
)


class _FM1OverflowFM2FitTokenizer:
    tokenizer_id = "fm1-overflow-fm2-fit"
    tokenizer_revision = "v1"

    def count_tokens(self, text: str) -> int:
        # FM1 payload carries both "relevant_start" and "events".
        # FM2 uses the six-field structured projection and does not.
        if '"relevant_start"' in text and '"events"' in text:
            return 300
        return 1


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        Path(path),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_safe_record_and_experience():
    a5 = _load_module(
        "tests/memory/test_package_a_a5_source_integrity_eligibility.py",
        "_decoupling_a5_helpers",
    )
    h = a5._helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()
    record = a5._safe_record(
        existing,
        builder_module,
        experience,
    )
    return record, experience


def _build_materialization_item(tmp_path: Path):
    a6 = _load_module(
        "tests/memory/test_package_a_a6_candidate_materialization.py",
        "_decoupling_a6_helpers",
    )
    h = a6._helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()
    assembly = a6._safe_assembly(
        existing,
        builder_module,
        experience,
    )
    item = a6._item_from_assembly(
        tmp_path=tmp_path,
        experience=experience,
        assembly=assembly,
    )
    return item


def test_fm1_token_budget_does_not_block_fm2_descriptive_eligibility():
    record, experience = _build_safe_record_and_experience()

    report = audit_memory_source_integrity_v1(
        record=record,
        registered_experiences=(experience,),
    )
    assert report.status == "VERIFIED"

    bundle = govern_descriptive_dev_record_v1(
        record=record,
        source_report=report,
        source_experience=experience,
        tokenizer=_FM1OverflowFM2FitTokenizer(),
        evaluation_contamination_status=(
            EvaluationContaminationStatusV1.CLEAN
        ),
    )

    assert bundle.status == "ELIGIBLE"
    assert bundle.failure_codes == ()
    assert bundle.governed_record is not None
    assert bundle.fm1 is not None
    assert bundle.fm2 is not None

    assert (
        bundle.fm1.build_disposition
        is ProjectionBuildDispositionV1.PROJECTION_INELIGIBLE_TOKEN_BUDGET
    )
    assert bundle.fm1.policy_visible_payload is None
    assert bundle.fm1.token_count is not None
    assert bundle.fm1.token_count.policy_visible_token_count == 300
    assert bundle.fm1.token_count.hard_ceiling == 256
    assert bundle.fm1.safety_report is not None
    assert bundle.fm1.safety_report.static_status == "PASS"
    assert bundle.fm1.safety_report.critical_safety_failure is False
    assert bundle.fm1.safety_report.static_failure_codes == ()

    assert (
        bundle.fm2.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
    )
    assert bundle.fm2.policy_visible_payload is not None


def test_materialization_preserves_unavailable_fm1_artifact_and_eligible_fm2(
    tmp_path: Path,
):
    item = _build_materialization_item(tmp_path)

    output_root = tmp_path / "candidates"
    output_root.mkdir()

    _, source_report, bundle, final = materialize_candidate_item_v1(
        item=item,
        tokenizer=_FM1OverflowFM2FitTokenizer(),
        output_root=output_root,
        execute=True,
    )

    assert source_report.status == "VERIFIED"
    assert bundle is not None
    assert bundle.status == "ELIGIBLE"
    assert bundle.governed_record is not None
    assert final is not None

    audit_candidate_directory_v1(final)

    fm1 = FM1MatchedRawEpisodicViewV1.from_json(
        (final / "fm1.json").read_bytes()
    )
    fm2 = FailureMemoryPolicyProjectionV1.from_json(
        (final / "fm2.json").read_bytes()
    )
    eligibility = json.loads(
        (final / "descriptive_eligibility.json").read_text(
            encoding="utf-8"
        )
    )

    assert (
        fm1.build_disposition
        is ProjectionBuildDispositionV1.PROJECTION_INELIGIBLE_TOKEN_BUDGET
    )
    assert fm1.policy_visible_payload is None
    assert fm1.token_count is not None
    assert fm1.token_count.hard_ceiling == 256
    assert fm1.safety_report is not None
    assert fm1.safety_report.static_status == "PASS"

    assert (
        fm2.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
    )
    assert fm2.policy_visible_payload is not None

    assert eligibility == {
        "failure_codes": [],
        "fm1_build_disposition": (
            "PROJECTION_INELIGIBLE_TOKEN_BUDGET"
        ),
        "fm2_build_disposition": "ELIGIBLE",
        "status": "ELIGIBLE",
    }


def test_dev_descriptive_snapshot_accepts_token_ineligible_fm1_as_artifact(
    tmp_path: Path,
):
    item = _build_materialization_item(tmp_path)

    candidate_root = tmp_path / "candidates"
    candidate_root.mkdir()

    _, _, bundle, final = materialize_candidate_item_v1(
        item=item,
        tokenizer=_FM1OverflowFM2FitTokenizer(),
        output_root=candidate_root,
        execute=True,
    )

    assert bundle is not None
    assert bundle.status == "ELIGIBLE"
    assert final is not None

    snapshot, files = build_memory_dev_descriptive_snapshot_v1(
        candidate_directories=(final,),
        source_materialization_manifest_sha256="a" * 64,
        tokenizer_id="fm1-overflow-fm2-fit",
        tokenizer_revision="v1",
    )

    assert len(snapshot.members) == 1

    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()

    published = publish_memory_dev_descriptive_snapshot_v1(
        output_root=snapshot_root,
        snapshot=snapshot,
        member_files=files,
    )

    rebuilt = audit_memory_dev_descriptive_snapshot_v1(
        snapshot_directory=published,
        expected_snapshot_sha256=snapshot.snapshot_sha256,
    )
    assert rebuilt == snapshot

    member_root = (
        published
        / snapshot.members[0].relative_directory
    )

    fm1 = FM1MatchedRawEpisodicViewV1.from_json(
        (member_root / "fm1.json").read_bytes()
    )
    fm2 = FailureMemoryPolicyProjectionV1.from_json(
        (member_root / "fm2.json").read_bytes()
    )

    assert (
        fm1.build_disposition
        is ProjectionBuildDispositionV1.PROJECTION_INELIGIBLE_TOKEN_BUDGET
    )
    assert (
        fm2.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
    )
    assert not any(
        path.name.startswith("fm3")
        for path in published.rglob("*")
        if path.is_file()
    )
