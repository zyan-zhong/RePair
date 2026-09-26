from __future__ import annotations

from collections.abc import Mapping

from .common import recursive_keys


_PRE_FORBIDDEN = {
    "human_pre_record",
    "human_pre_record_sha256",
    "human_post_record",
    "human_post_record_sha256",
    "current_f0f1_outcomes",
    "environment_result_package",
    "future_pi2_evaluation",
    "sealed_test_trajectory",
    "api_shadow_output",
}
_POST_FORBIDDEN = {
    "human_post_record",
    "human_post_record_sha256",
    "future_pi2_evaluation",
    "sealed_test_trajectory",
}


def _assert_absent(value: object, forbidden: set[str], label: str) -> None:
    hits = sorted(recursive_keys(value) & forbidden)
    if hits:
        raise ValueError(f"{label} contains forbidden keys: {hits}")


def build_strong_pre_projection(
    *,
    round_evidence_package: Mapping[str, object],
    researcher_memory_pack: Mapping[str, object] | None,
) -> dict[str, object]:
    _assert_absent(round_evidence_package, _PRE_FORBIDDEN, "strong PRE input")
    memory_sha = round_evidence_package.get("researcher_memory_pack_sha256")
    projection = {
        "round_evidence_package_sha256": round_evidence_package[
            "round_evidence_package_sha256"
        ],
        "round_evidence_package": dict(round_evidence_package),
        "memory_pack_sha256": memory_sha,
    }
    if researcher_memory_pack is not None:
        projection["memory_pack"] = dict(researcher_memory_pack)
    _assert_absent(projection, _PRE_FORBIDDEN, "strong PRE projection")
    return projection


def build_strong_post_projection(
    *,
    environment_result_package: Mapping[str, object],
    human_pre_record_sha256: str,
    researcher_memory_pack: Mapping[str, object] | None,
) -> dict[str, object]:
    _assert_absent(environment_result_package, _POST_FORBIDDEN, "strong POST input")
    projection = {
        "environment_result_package_sha256": environment_result_package[
            "environment_result_package_sha256"
        ],
        "environment_result_package": dict(environment_result_package),
        "human_pre_record_sha256": human_pre_record_sha256,
        "memory_pack_sha256": None,
    }
    if researcher_memory_pack is not None:
        for field in ("memory_pack_sha256", "pack_sha256", "snapshot_sha256"):
            value = researcher_memory_pack.get(field)
            if isinstance(value, str) and len(value) == 64:
                projection["memory_pack_sha256"] = value
                break
        projection["memory_pack"] = dict(researcher_memory_pack)
    _assert_absent(projection, _POST_FORBIDDEN, "strong POST projection")
    return projection
