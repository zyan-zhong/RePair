from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from pchsi.memory.dev_snapshot_loader import (
    FM1AvailabilityV1,
    FM2AvailabilityV1,
    LoadedDevSnapshotMemberV2,
)
from pchsi.memory.matched_raw_view import (
    build_fm1_matched_raw_episodic_view_v1,
)
from pchsi.memory.representation_ablation import (
    build_matched_representation_template_v1,
)
from pchsi.memory.single_cue_failure_summary import (
    build_single_cue_policy_view_v1,
)


def _helpers():
    path = Path(
        "tests/memory/package_b_direct_test_helpers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_package_b_direct_helpers_b7",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_b7_same_record_m1_m2_m3_ready_when_all_are_eligible(tmp_path):
    final, snapshot, contract, contract_path, tokenizer = (
        _helpers().published_snapshot(tmp_path)
    )

    from pchsi.memory.dev_snapshot_loader import (
        load_calibrated_dev_snapshot_v2,
    )

    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=final,
        expected_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=contract.contract_sha256,
    )
    member = loaded.members[0]

    cue = build_single_cue_policy_view_v1(
        fm2=member.fm2,
        fm2_artifact_sha256=hashlib.sha256(
            (member.member_directory / "fm2.json").read_bytes()
        ).hexdigest(),
        tokenizer=tokenizer,
        hard_ceiling=contract.single_record_hard_ceiling,
    )

    template = build_matched_representation_template_v1(
        snapshot_sha256=snapshot.snapshot_sha256,
        member=member,
        single_cue=cue,
    )

    assert template.core_matched_ready is True
    assert tuple(
        arm.arm_id
        for arm in template.arms
    ) == (
        "M0",
        "M1",
        "M2",
        "M3",
        "NEG",
        "D1",
        "D2",
    )
    assert all(
        next(
            arm for arm in template.arms
            if arm.arm_id == arm_id
        ).availability == "AVAILABLE"
        for arm_id in ("M1", "M2", "M3")
    )


class _OverflowTokenizer:
    tokenizer_id = "overflow"
    tokenizer_revision = "v1"

    def count_tokens(self, text: str) -> int:
        return 700


def test_b7_fm1_unavailable_is_not_rewritten_or_treated_as_m0(tmp_path):
    record, experience, key, _, fm2, tokenizer = (
        _helpers().record_experience_fm1_fm2()
    )

    fm1 = build_fm1_matched_raw_episodic_view_v1(
        record=record,
        experience=experience,
        tokenizer=_OverflowTokenizer(),
        hard_ceiling=640,
    )
    assert (
        fm1.build_disposition.value
        == "PROJECTION_INELIGIBLE_TOKEN_BUDGET"
    )

    member_dir = tmp_path / "member"
    member_dir.mkdir()
    (member_dir / "fm2.json").write_bytes(
        fm2.canonical_bytes()
    )

    member = LoadedDevSnapshotMemberV2(
        record=record,
        retrieval_key=key,
        fm1=fm1,
        fm2=fm2,
        fm1_availability=(
            FM1AvailabilityV1.FM1_UNAVAILABLE_TOKEN_BUDGET
        ),
        fm2_availability=(
            FM2AvailabilityV1.FM2_ELIGIBLE
        ),
        member_directory=member_dir,
    )

    cue = build_single_cue_policy_view_v1(
        fm2=fm2,
        fm2_artifact_sha256=hashlib.sha256(
            fm2.canonical_bytes()
        ).hexdigest(),
        tokenizer=tokenizer,
        hard_ceiling=640,
    )

    template = build_matched_representation_template_v1(
        snapshot_sha256="1" * 64,
        member=member,
        single_cue=cue,
    )

    m0 = next(arm for arm in template.arms if arm.arm_id == "M0")
    m1 = next(arm for arm in template.arms if arm.arm_id == "M1")

    assert m0.availability == "AVAILABLE"
    assert m0.policy_visible_payload == []
    assert m1.availability == "UNAVAILABLE"
    assert m1.policy_visible_payload is None
    assert (
        m1.reason
        == "PROJECTION_INELIGIBLE_TOKEN_BUDGET"
    )
    assert template.core_matched_ready is False
