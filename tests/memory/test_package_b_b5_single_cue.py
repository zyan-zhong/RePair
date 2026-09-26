from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from pchsi.memory.projection_common import (
    ProjectionBuildDispositionV1,
)
from pchsi.memory.single_cue_failure_summary import (
    SingleCuePolicyViewV1,
    build_single_cue_policy_view_v1,
)


def _helpers():
    path = Path(
        "tests/memory/package_b_direct_test_helpers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_package_b_direct_helpers_b5",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_b5_single_cue_is_exact_first_fm2_failure_pattern_item():
    _, _, _, _, fm2, tokenizer = (
        _helpers().record_experience_fm1_fm2()
    )

    fm2_bytes = fm2.canonical_bytes()
    cue = build_single_cue_policy_view_v1(
        fm2=fm2,
        fm2_artifact_sha256=hashlib.sha256(
            fm2_bytes
        ).hexdigest(),
        tokenizer=tokenizer,
        hard_ceiling=640,
    )

    assert (
        cue.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
    )
    assert cue.failure_pattern_index == 0
    assert cue.cue_text == (
        fm2.policy_visible_payload
        .failure_pattern[0]
        .text
    )
    assert cue.source_fm2_payload_sha256 == (
        fm2.policy_visible_payload_sha256
    )
    assert cue.safety_report.static_status == "PASS"
    assert cue.policy_visible_payload() == {
        "failure_cue": cue.cue_text,
    }

    rebuilt = SingleCuePolicyViewV1.from_json(
        cue.canonical_bytes()
    )
    assert rebuilt == cue


def test_b5_never_searches_for_alternate_cue():
    _, _, _, _, fm2, tokenizer = (
        _helpers().record_experience_fm1_fm2()
    )

    assert len(
        fm2.policy_visible_payload.failure_pattern
    ) == 1

    cue = build_single_cue_policy_view_v1(
        fm2=fm2,
        fm2_artifact_sha256=hashlib.sha256(
            fm2.canonical_bytes()
        ).hexdigest(),
        tokenizer=tokenizer,
        hard_ceiling=640,
    )
    assert cue.failure_pattern_index == 0
