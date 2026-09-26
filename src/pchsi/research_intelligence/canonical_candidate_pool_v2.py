"""Build the canonical selected repair pool from an explicit selection authority."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from pchsi.reference_loop.canonical import domain_hash

from .selected_candidate_authority import (
    SelectedCandidateAuthorityV1,
)


EXECUTABLE_STATUSES = {
    "EXECUTABLE_EXACT_ACTION",
    "EXECUTABLE_SHORT_OPTION",
}


def _require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _walk(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _index_unique(
    pool: Mapping[str, object],
    *,
    schema_id: str,
    sha_field: str,
) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for value in _walk(dict(pool)):
        if value.get("schema_id") != schema_id:
            continue
        sha = _require_sha(value.get(sha_field), sha_field)
        previous = out.get(sha)
        if previous is None:
            out[sha] = dict(value)
        elif previous != dict(value):
            raise ValueError(
                f"{schema_id} SHA maps to non-identical objects: {sha}"
            )
    return out


def _crosschecks(
    pool: Mapping[str, object],
) -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = defaultdict(list)
    seen: set[str] = set()
    for value in _walk(dict(pool)):
        if value.get("schema_id") != "ANALYZER_CROSSCHECK_RESULT_V1":
            continue
        cross_sha = _require_sha(
            value.get("crosscheck_sha256"),
            "crosscheck_sha256",
        )
        if cross_sha in seen:
            continue
        seen.add(cross_sha)
        target = _require_sha(
            value.get("target_artifact_sha256"),
            "target_artifact_sha256",
        )
        out[target].append(dict(value))
    return out


def _evidence_shas(value: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()

    def walk(item: object, key: str = "") -> None:
        if isinstance(item, dict):
            for child_key, child in item.items():
                lower = str(child_key).lower()
                if (
                    isinstance(child, str)
                    and len(child) == 64
                    and all(ch in "0123456789abcdef" for ch in child)
                    and "evidence" in lower
                ):
                    found.add(child)
                walk(child, lower)
        elif isinstance(item, list):
            for child in item:
                walk(child, key)

    walk(value)
    return tuple(sorted(found))


def build_canonical_selected_pool_v2(
    *,
    pool: Mapping[str, object],
    pool_file_sha256: str,
    authority: SelectedCandidateAuthorityV1,
) -> dict[str, object]:
    _require_sha(pool_file_sha256, "pool_file_sha256")

    candidates = _index_unique(
        pool,
        schema_id="ANALYZER_REPAIR_CANDIDATE_V1",
        sha_field="candidate_sha256",
    )
    proposals = _index_unique(
        pool,
        schema_id="ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",
        sha_field="source_proposal_sha256",
    )
    groups = _index_unique(
        pool,
        schema_id="ANALYZER_GROUP_MANIFEST_V1",
        sha_field="group_manifest_sha256",
    )
    crosschecks = _crosschecks(pool)

    selected_ids = {
        row.candidate_sha256 for row in authority.selected_rows
    }
    selected_rows: list[dict[str, object]] = []

    for authority_row in authority.selected_rows:
        candidate = candidates.get(authority_row.candidate_sha256)
        if candidate is None:
            raise ValueError(
                "authority candidate missing from pool: "
                + authority_row.candidate_sha256
            )
        if candidate.get("candidate_status") not in EXECUTABLE_STATUSES:
            raise ValueError(
                "authority candidate is not executable: "
                + authority_row.candidate_sha256
            )
        state_sha = _require_sha(
            candidate.get("source_state_sha256"),
            "source_state_sha256",
        )
        if state_sha != authority_row.source_state_sha256:
            raise ValueError(
                "authority/candidate source-state mismatch"
            )
        proposal_sha = _require_sha(
            candidate.get("source_proposal_sha256"),
            "source_proposal_sha256",
        )
        proposal = proposals.get(proposal_sha)
        group = None
        related_crosschecks: list[dict[str, object]] = []

        if proposal is not None:
            group_sha = _require_sha(
                proposal.get("group_manifest_sha256"),
                "group_manifest_sha256",
            )
            group = groups.get(group_sha)
            related_crosschecks.extend(
                crosschecks.get(proposal_sha, [])
            )
            related_crosschecks.extend(
                crosschecks.get(group_sha, [])
            )
        related_crosschecks.extend(
            crosschecks.get(authority_row.candidate_sha256, [])
        )

        exact_action = candidate.get("exact_action")
        option_actions = candidate.get("option_actions")
        if option_actions is None:
            option_actions = []
        if not isinstance(option_actions, list):
            raise TypeError("candidate option_actions must be array")

        selected_rows.append(
            {
                "condition_id": authority_row.condition_id,
                "candidate_sha256": authority_row.candidate_sha256,
                "source_state_sha256": state_sha,
                "menu_sha256": _require_sha(
                    candidate.get("menu_sha256"),
                    "menu_sha256",
                ),
                "source_proposal_sha256": proposal_sha,
                "candidate_status": candidate["candidate_status"],
                "repair_kind": (
                    "EXACT_ACTION"
                    if candidate["candidate_status"]
                    == "EXECUTABLE_EXACT_ACTION"
                    else "SHORT_OPTION"
                ),
                "exact_action": exact_action,
                "option_actions": list(option_actions),
                "termination_condition": candidate.get(
                    "termination_condition"
                ),
                "proposal": proposal,
                "group_manifest": group,
                "crosschecks": sorted(
                    related_crosschecks,
                    key=lambda row: str(
                        row.get("crosscheck_sha256")
                    ),
                ),
                "supporting_evidence_sha256s": sorted(
                    set(_evidence_shas(candidate))
                    | (
                        set(_evidence_shas(proposal))
                        if isinstance(proposal, dict)
                        else set()
                    )
                    | {
                        sha
                        for row in related_crosschecks
                        for sha in _evidence_shas(row)
                    }
                ),
            }
        )

    selected_rows = sorted(
        selected_rows,
        key=lambda row: (
            row["source_state_sha256"],
            row["condition_id"],
            row["candidate_sha256"],
        ),
    )

    state_pairs: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in selected_rows:
        state_pairs[str(row["source_state_sha256"])][
            str(row["condition_id"])
        ] = row

    extra_audit: list[dict[str, object]] = []
    for candidate_sha, candidate in sorted(candidates.items()):
        if candidate_sha in selected_ids:
            continue
        extra_audit.append(
            {
                "candidate_sha256": candidate_sha,
                "candidate_status": candidate.get("candidate_status"),
                "executable": candidate.get("candidate_status")
                in EXECUTABLE_STATUSES,
                "source_state_sha256": candidate.get(
                    "source_state_sha256"
                ),
                "source_proposal_sha256": candidate.get(
                    "source_proposal_sha256"
                ),
                "exact_action": candidate.get("exact_action"),
                "option_actions": candidate.get("option_actions"),
                "termination_condition": candidate.get(
                    "termination_condition"
                ),
                "audit_reason": (
                    "NOT_REFERENCED_BY_SELECTED_CANDIDATE_AUTHORITY"
                ),
            }
        )

    result = {
        "schema_id": "CANONICAL_FORMAL_CANDIDATE_POOL_V2",
        "schema_version": 2,
        "pool_file_sha256": pool_file_sha256,
        "selection_authority_sha256": (
            authority.selection_authority_sha256
        ),
        "selected_candidate_count": len(selected_rows),
        "selected_source_state_count": len(state_pairs),
        "selected_candidates": selected_rows,
        "state_pairs": {
            state: dict(sorted(rows.items()))
            for state, rows in sorted(state_pairs.items())
        },
        "extra_candidate_audit": extra_audit,
        "extra_candidate_count": len(extra_audit),
        "extra_executable_candidate_count": sum(
            1 for row in extra_audit if row["executable"]
        ),
        "canonical_pool_sha256": "0" * 64,
    }
    result["canonical_pool_sha256"] = domain_hash(
        "CANONICAL_FORMAL_CANDIDATE_POOL_V2",
        result,
        excluded_field="canonical_pool_sha256",
    )
    return result
