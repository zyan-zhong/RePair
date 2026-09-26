"""Resolve the authoritative selected-candidate ledger in a sealed Formal pool.

This is a legacy-import adapter for the current π1→π2 reference round.

It does not infer scientific selection from "all executable candidate objects".
Instead it searches the sealed pool for a unique container whose candidate
references reproduce the already-frozen Formal Result Manifest invariants:

- total selected state-condition outcomes
- A2 selected count
- A3 selected count
- unique source-state count
- one A2/A3 pair per source state

If multiple structural containers satisfy the invariants, they are accepted
only when they encode the exact same scientific identity set.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pchsi.reference_loop.canonical import domain_hash


def _require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _normalize_condition(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    upper = value.upper()
    if (
        upper == "A2"
        or upper.startswith("A2_")
        or upper.startswith("G-A2")
        or "NO_HISTORY" in upper
    ):
        return "A2"
    if (
        upper == "A3"
        or upper.startswith("A3_")
        or upper.startswith("G-A3")
        or "WITH_HISTORY" in upper
    ):
        return "A3"
    return None


def _candidate_objects(pool: Mapping[str, object]) -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("schema_id") == "ANALYZER_REPAIR_CANDIDATE_V1":
                sha = _require_sha(
                    value.get("candidate_sha256"),
                    "candidate_sha256",
                )
                previous = found.get(sha)
                if previous is None:
                    found[sha] = dict(value)
                elif previous != dict(value):
                    raise ValueError(
                        "same candidate SHA maps to non-identical candidate objects"
                    )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(dict(pool))
    return found


def _candidate_sha_refs(
    value: object,
    *,
    known: set[str],
) -> set[str]:
    refs: set[str] = set()

    def walk(item: object, key_hint: str = "") -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                lower = str(key).lower()
                if (
                    isinstance(child, str)
                    and child in known
                    and "candidate" in lower
                ):
                    refs.add(child)
                elif (
                    key in {"candidate_sha256", "selected_candidate_sha256"}
                    and isinstance(child, str)
                    and child in known
                ):
                    refs.add(child)
                walk(child, lower)
        elif isinstance(item, list):
            for child in item:
                walk(child, key_hint)

    walk(value)
    return refs


def _condition_from_row_or_path(
    row: Mapping[str, object],
    path: tuple[str, ...],
) -> str | None:
    for key in (
        "condition_id",
        "condition",
        "analyzer_condition",
        "method_condition",
        "stage_id",
    ):
        condition = _normalize_condition(row.get(key))
        if condition is not None:
            return condition
    for token in reversed(path):
        condition = _normalize_condition(token)
        if condition is not None:
            return condition
    return None


@dataclass(frozen=True, slots=True)
class SelectionLedgerRowV1:
    condition_id: str
    candidate_sha256: str
    source_state_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "condition_id": self.condition_id,
            "candidate_sha256": self.candidate_sha256,
            "source_state_sha256": self.source_state_sha256,
        }


@dataclass(frozen=True, slots=True)
class SelectedCandidateAuthorityV1:
    expected_total: int
    expected_condition_counts: dict[str, int]
    expected_source_state_count: int
    selected_rows: tuple[SelectionLedgerRowV1, ...]
    structural_container_paths: tuple[str, ...]
    selection_authority_sha256: str | None = None

    def __post_init__(self) -> None:
        if len(self.selected_rows) != self.expected_total:
            raise ValueError("selected row total mismatch")
        counts = Counter(row.condition_id for row in self.selected_rows)
        if dict(counts) != self.expected_condition_counts:
            raise ValueError(
                "condition-count mismatch: " + repr(dict(counts))
            )
        states: dict[str, set[str]] = defaultdict(set)
        for row in self.selected_rows:
            states[row.source_state_sha256].add(row.condition_id)
        if len(states) != self.expected_source_state_count:
            raise ValueError("source-state count mismatch")
        bad = {
            state: sorted(conditions)
            for state, conditions in states.items()
            if conditions != {"A2", "A3"}
        }
        if bad:
            raise ValueError(
                "A2/A3 state-pair incompleteness: " + repr(bad)
            )
        identities = {
            (
                row.condition_id,
                row.candidate_sha256,
                row.source_state_sha256,
            )
            for row in self.selected_rows
        }
        if len(identities) != len(self.selected_rows):
            raise ValueError("duplicate selected scientific identity")

        expected = domain_hash(
            "SELECTED_CANDIDATE_AUTHORITY_V1",
            self._without_sha(),
        )
        if self.selection_authority_sha256 is None:
            object.__setattr__(
                self,
                "selection_authority_sha256",
                expected,
            )
        elif self.selection_authority_sha256 != expected:
            raise ValueError("selection authority SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "SELECTED_CANDIDATE_AUTHORITY_V1",
            "schema_version": 1,
            "expected_total": self.expected_total,
            "expected_condition_counts": self.expected_condition_counts,
            "expected_source_state_count": self.expected_source_state_count,
            "selected_rows": [
                row.to_dict() for row in self.selected_rows
            ],
            "structural_container_paths": list(
                self.structural_container_paths
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._without_sha(),
            "selection_authority_sha256": self.selection_authority_sha256,
        }


def _rows_from_list(
    rows: list[object],
    *,
    path: tuple[str, ...],
    candidates: dict[str, dict[str, object]],
    expected_total: int,
    expected_condition_counts: dict[str, int],
    expected_source_state_count: int,
) -> tuple[SelectionLedgerRowV1, ...] | None:
    if len(rows) != expected_total:
        return None
    known = set(candidates)
    parsed: list[SelectionLedgerRowV1] = []
    for raw in rows:
        if not isinstance(raw, dict):
            return None
        refs = _candidate_sha_refs(raw, known=known)
        if len(refs) != 1:
            return None
        candidate_sha = next(iter(refs))
        condition = _condition_from_row_or_path(raw, path)
        if condition is None:
            return None
        candidate = candidates[candidate_sha]
        status = candidate.get("candidate_status")
        if status not in {
            "EXECUTABLE_EXACT_ACTION",
            "EXECUTABLE_SHORT_OPTION",
        }:
            return None
        state = _require_sha(
            candidate.get("source_state_sha256"),
            "source_state_sha256",
        )
        parsed.append(
            SelectionLedgerRowV1(
                condition_id=condition,
                candidate_sha256=candidate_sha,
                source_state_sha256=state,
            )
        )

    try:
        SelectedCandidateAuthorityV1(
            expected_total=expected_total,
            expected_condition_counts=expected_condition_counts,
            expected_source_state_count=expected_source_state_count,
            selected_rows=tuple(parsed),
            structural_container_paths=("/".join(path),),
        )
    except ValueError:
        return None
    return tuple(parsed)


def _rows_from_a2_a3_dict(
    value: Mapping[str, object],
    *,
    path: tuple[str, ...],
    candidates: dict[str, dict[str, object]],
    expected_condition_counts: dict[str, int],
    expected_source_state_count: int,
) -> tuple[SelectionLedgerRowV1, ...] | None:
    condition_lists: dict[str, list[object]] = {}
    for key, child in value.items():
        condition = _normalize_condition(key)
        if condition is None or not isinstance(child, list):
            continue
        condition_lists[condition] = child

    if set(condition_lists) != {"A2", "A3"}:
        return None
    if any(
        len(condition_lists[condition])
        != expected_condition_counts[condition]
        for condition in ("A2", "A3")
    ):
        return None

    known = set(candidates)
    parsed: list[SelectionLedgerRowV1] = []
    for condition in ("A2", "A3"):
        for raw in condition_lists[condition]:
            refs = _candidate_sha_refs(raw, known=known)
            if not refs and isinstance(raw, str) and raw in known:
                refs = {raw}
            if len(refs) != 1:
                return None
            candidate_sha = next(iter(refs))
            candidate = candidates[candidate_sha]
            if candidate.get("candidate_status") not in {
                "EXECUTABLE_EXACT_ACTION",
                "EXECUTABLE_SHORT_OPTION",
            }:
                return None
            parsed.append(
                SelectionLedgerRowV1(
                    condition_id=condition,
                    candidate_sha256=candidate_sha,
                    source_state_sha256=_require_sha(
                        candidate.get("source_state_sha256"),
                        "source_state_sha256",
                    ),
                )
            )

    try:
        SelectedCandidateAuthorityV1(
            expected_total=sum(expected_condition_counts.values()),
            expected_condition_counts=expected_condition_counts,
            expected_source_state_count=expected_source_state_count,
            selected_rows=tuple(parsed),
            structural_container_paths=("/".join(path),),
        )
    except ValueError:
        return None
    return tuple(parsed)


def discover_selected_candidate_authority_v1(
    *,
    pool: Mapping[str, object],
    expected_total: int,
    expected_condition_counts: Mapping[str, int],
    expected_source_state_count: int,
) -> tuple[SelectedCandidateAuthorityV1, dict[str, object]]:
    candidates = _candidate_objects(pool)
    expected_counts = {
        "A2": int(expected_condition_counts["A2"]),
        "A3": int(expected_condition_counts["A3"]),
    }

    valid_containers: list[
        tuple[str, tuple[SelectionLedgerRowV1, ...]]
    ] = []
    inspected: list[dict[str, object]] = []

    def walk(value: object, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, list):
            parsed = _rows_from_list(
                value,
                path=path,
                candidates=candidates,
                expected_total=expected_total,
                expected_condition_counts=expected_counts,
                expected_source_state_count=expected_source_state_count,
            )
            inspected.append(
                {
                    "path": "/".join(path),
                    "container_type": "list",
                    "length": len(value),
                    "valid_selection_ledger": parsed is not None,
                }
            )
            if parsed is not None:
                valid_containers.append(("/".join(path), parsed))
            for index, child in enumerate(value):
                walk(child, path + (str(index),))
        elif isinstance(value, dict):
            parsed = _rows_from_a2_a3_dict(
                value,
                path=path,
                candidates=candidates,
                expected_condition_counts=expected_counts,
                expected_source_state_count=expected_source_state_count,
            )
            if parsed is not None:
                valid_containers.append(("/".join(path), parsed))
            for key, child in value.items():
                walk(child, path + (str(key),))

    walk(dict(pool))

    if not valid_containers:
        raise ValueError(
            "no structural candidate-selection ledger reproduces "
            "the frozen Formal Result Manifest"
        )

    signatures: dict[
        tuple[tuple[str, str, str], ...],
        list[str],
    ] = defaultdict(list)
    rows_by_signature: dict[
        tuple[tuple[str, str, str], ...],
        tuple[SelectionLedgerRowV1, ...],
    ] = {}

    for path, rows in valid_containers:
        signature = tuple(
            sorted(
                (
                    row.condition_id,
                    row.candidate_sha256,
                    row.source_state_sha256,
                )
                for row in rows
            )
        )
        signatures[signature].append(path)
        rows_by_signature[signature] = rows

    if len(signatures) != 1:
        raise ValueError(
            "multiple structurally valid but scientifically different "
            "selection ledgers found"
        )

    signature = next(iter(signatures))
    authority = SelectedCandidateAuthorityV1(
        expected_total=expected_total,
        expected_condition_counts=expected_counts,
        expected_source_state_count=expected_source_state_count,
        selected_rows=tuple(
            SelectionLedgerRowV1(
                condition_id=condition,
                candidate_sha256=candidate_sha,
                source_state_sha256=state_sha,
            )
            for condition, candidate_sha, state_sha in signature
        ),
        structural_container_paths=tuple(
            sorted(signatures[signature])
        ),
    )

    diagnostics = {
        "schema_id": "SELECTED_CANDIDATE_AUTHORITY_DISCOVERY_DIAGNOSTICS_V1",
        "repair_candidate_object_count": len(candidates),
        "valid_structural_container_count": len(valid_containers),
        "unique_scientific_signature_count": len(signatures),
        "selected_authority_sha256": (
            authority.selection_authority_sha256
        ),
        "selected_structural_container_paths": list(
            authority.structural_container_paths
        ),
        "inspected_list_container_count": len(inspected),
        "inspected_list_containers": inspected,
    }
    return authority, diagnostics
