"""Canonical Researcher view over the sealed Formal Analyzer candidate pool.

The Formal pool contains wrappers, proposals, cross-check sidecars, summaries,
and final repair candidates. A recursive "candidate-like object" search can
therefore overcount. This adapter selects only validated
ANALYZER_REPAIR_CANDIDATE_V1 objects, preserves A2/A3 condition identity, and
joins proposal/group/cross-check lineage without changing Analyzer semantics.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pchsi.reference_loop.canonical import domain_hash


EXECUTABLE_STATUSES = frozenset(
    {
        "EXECUTABLE_EXACT_ACTION",
        "EXECUTABLE_SHORT_OPTION",
    }
)
NONEXECUTABLE_STATUSES = frozenset(
    {
        "ABSTAIN",
        "REJECTED_SOURCE_BINDING",
        "REJECTED_CROSSCHECK",
    }
)
ALL_STATUSES = EXECUTABLE_STATUSES | NONEXECUTABLE_STATUSES

_CONDITION_FIELDS = (
    "condition_id",
    "condition",
    "analyzer_condition",
    "method_condition",
    "stage_id",
)


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
        or upper == "G-A2"
        or upper.startswith("A2_")
        or "HIERARCHICAL_NO_HISTORY" in upper
    ):
        return "A2"
    if (
        upper == "A3"
        or upper == "G-A3"
        or upper.startswith("A3_")
        or "HIERARCHICAL_WITH_HISTORY" in upper
    ):
        return "A3"
    return None


def _condition_from_object(
    value: Mapping[str, object],
    inherited: str | None,
) -> str | None:
    for field in _CONDITION_FIELDS:
        condition = _normalize_condition(value.get(field))
        if condition is not None:
            return condition
    return inherited


def _walk_objects(
    value: object,
    *,
    path: tuple[str, ...] = (),
    condition: str | None = None,
):
    if isinstance(value, dict):
        current = _condition_from_object(value, condition)
        yield path, current, value
        for key, child in value.items():
            yield from _walk_objects(
                child,
                path=path + (str(key),),
                condition=current,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_objects(
                child,
                path=path + (str(index),),
                condition=condition,
            )


def _sha_values_under_candidate_keys(
    value: Mapping[str, object],
) -> set[str]:
    found: set[str] = set()

    def walk(item: object, parent_key: str = "") -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                lower = str(key).lower()
                if (
                    isinstance(child, str)
                    and len(child) == 64
                    and all(
                        ch in "0123456789abcdef"
                        for ch in child
                    )
                    and (
                        "candidate" in lower
                        or lower == "candidate_sha256"
                    )
                ):
                    found.add(child)
                walk(child, lower)
        elif isinstance(item, list):
            for child in item:
                walk(child, parent_key)

    walk(value)
    return found


def _sha_values_under_proposal_keys(
    value: Mapping[str, object],
) -> set[str]:
    found: set[str] = set()

    def walk(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                lower = str(key).lower()
                if (
                    isinstance(child, str)
                    and len(child) == 64
                    and all(
                        ch in "0123456789abcdef"
                        for ch in child
                    )
                    and (
                        "proposal" in lower
                        or lower == "source_proposal_sha256"
                    )
                ):
                    found.add(child)
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return found


def _candidate_required_keyset() -> set[str]:
    return {
        "schema_id",
        "schema_version",
        "candidate_kind",
        "source_state_sha256",
        "menu_sha256",
        "source_proposal_sha256",
        "candidate_status",
        "exact_action",
        "option_actions",
        "termination_condition",
        "requires_environment_verification",
        "candidate_sha256",
        "live_menu_revalidation_required",
        "all_intervention_actions_count_against_environment_budget",
    }


@dataclass(frozen=True, slots=True)
class CanonicalRepairCandidateV1:
    condition_id: str
    candidate_sha256: str
    source_state_sha256: str
    menu_sha256: str
    source_proposal_sha256: str
    candidate_status: str
    exact_action: str | None
    option_actions: tuple[str, ...]
    termination_condition: str | None
    proposal: dict[str, object] | None
    group_manifest: dict[str, object] | None
    crosschecks: tuple[dict[str, object], ...]
    source_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.condition_id not in {"A2", "A3"}:
            raise ValueError("condition_id must be A2 or A3")
        for name in (
            "candidate_sha256",
            "source_state_sha256",
            "menu_sha256",
            "source_proposal_sha256",
        ):
            _require_sha(getattr(self, name), name)
        if self.candidate_status not in ALL_STATUSES:
            raise ValueError("candidate_status not registered")
        if self.candidate_status == "EXECUTABLE_EXACT_ACTION":
            if not isinstance(self.exact_action, str) or not self.exact_action:
                raise ValueError("exact-action candidate missing exact_action")
            if self.option_actions:
                raise ValueError("exact-action candidate has option_actions")
        if self.candidate_status == "EXECUTABLE_SHORT_OPTION":
            if self.exact_action is not None:
                raise ValueError("short-option candidate has exact_action")
            if not (1 <= len(self.option_actions) <= 4):
                raise ValueError("short option must contain 1-4 actions")

    @property
    def executable(self) -> bool:
        return self.candidate_status in EXECUTABLE_STATUSES

    @property
    def repair_kind(self) -> str:
        if self.candidate_status == "EXECUTABLE_EXACT_ACTION":
            return "EXACT_ACTION"
        if self.candidate_status == "EXECUTABLE_SHORT_OPTION":
            return "SHORT_OPTION"
        return self.candidate_status

    @property
    def task_family(self) -> str | None:
        if isinstance(self.group_manifest, dict):
            raw = self.group_manifest.get("task_family")
            if isinstance(raw, str):
                return raw
        return None

    @property
    def group_id(self) -> str | None:
        if isinstance(self.group_manifest, dict):
            raw = self.group_manifest.get("group_id")
            if isinstance(raw, str):
                return raw
        return None

    @property
    def supporting_evidence_sha256s(self) -> tuple[str, ...]:
        rows: set[str] = set()
        if isinstance(self.proposal, dict):
            raw = self.proposal.get("supporting_evidence_sha256s")
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, str):
                        rows.add(_require_sha(item, "supporting evidence"))
        for crosscheck in self.crosschecks:
            for field in (
                "supporting_evidence_sha256s",
                "contradiction_evidence_sha256s",
                "current_evidence_sha256s",
                "historical_evidence_sha256s",
            ):
                raw = crosscheck.get(field)
                if isinstance(raw, list):
                    for item in raw:
                        if isinstance(item, str):
                            rows.add(_require_sha(item, field))
        return tuple(sorted(rows))

    def to_dict(self) -> dict[str, object]:
        return {
            "condition_id": self.condition_id,
            "candidate_sha256": self.candidate_sha256,
            "source_state_sha256": self.source_state_sha256,
            "menu_sha256": self.menu_sha256,
            "source_proposal_sha256": self.source_proposal_sha256,
            "candidate_status": self.candidate_status,
            "executable": self.executable,
            "repair_kind": self.repair_kind,
            "exact_action": self.exact_action,
            "option_actions": list(self.option_actions),
            "termination_condition": self.termination_condition,
            "task_family": self.task_family,
            "group_id": self.group_id,
            "supporting_evidence_sha256s": list(
                self.supporting_evidence_sha256s
            ),
            "proposal": self.proposal,
            "group_manifest": self.group_manifest,
            "crosschecks": list(self.crosschecks),
            "source_paths": list(self.source_paths),
        }


@dataclass(frozen=True, slots=True)
class CanonicalCandidatePoolV1:
    pool_file_sha256: str
    selected_candidates: tuple[CanonicalRepairCandidateV1, ...]
    nonselected_candidates: tuple[CanonicalRepairCandidateV1, ...]
    schema_object_census: dict[str, int]
    canonical_pool_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha(self.pool_file_sha256, "pool_file_sha256")
        selected = self.selected_candidates
        if len(selected) != 60:
            raise ValueError(
                f"expected 60 executable selected candidates, got {len(selected)}"
            )
        conditions = Counter(row.condition_id for row in selected)
        if conditions != Counter({"A2": 30, "A3": 30}):
            raise ValueError(
                "expected A2=30/A3=30, got " + repr(dict(conditions))
            )
        states = defaultdict(set)
        for row in selected:
            states[row.source_state_sha256].add(row.condition_id)
        if len(states) != 30:
            raise ValueError(
                f"expected 30 source states, got {len(states)}"
            )
        incomplete = {
            state: sorted(conditions)
            for state, conditions in states.items()
            if conditions != {"A2", "A3"}
        }
        if incomplete:
            raise ValueError(
                "A2/A3 state-pair incompleteness: " + repr(incomplete)
            )

        identity_rows = [
            (
                row.condition_id,
                row.candidate_sha256,
            )
            for row in selected
        ]
        if len(set(identity_rows)) != len(identity_rows):
            raise ValueError("duplicate condition/candidate identity")

        expected = domain_hash(
            "CANONICAL_FORMAL_CANDIDATE_POOL_V1",
            self._without_sha(),
        )
        if self.canonical_pool_sha256 is None:
            object.__setattr__(
                self,
                "canonical_pool_sha256",
                expected,
            )
        elif self.canonical_pool_sha256 != expected:
            raise ValueError("canonical candidate pool SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "CANONICAL_FORMAL_CANDIDATE_POOL_V1",
            "schema_version": 1,
            "pool_file_sha256": self.pool_file_sha256,
            "selected_candidates": [
                row.to_dict() for row in self.selected_candidates
            ],
            "nonselected_candidates": [
                row.to_dict() for row in self.nonselected_candidates
            ],
            "schema_object_census": self.schema_object_census,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._without_sha(),
            "canonical_pool_sha256": self.canonical_pool_sha256,
        }

    def state_pairs(self) -> dict[str, dict[str, dict[str, object]]]:
        pairs: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
        for row in self.selected_candidates:
            pairs[row.source_state_sha256][row.condition_id] = row.to_dict()
        return {
            state: dict(sorted(rows.items()))
            for state, rows in sorted(pairs.items())
        }


def build_canonical_candidate_pool_v1(
    *,
    pool: Mapping[str, object],
    pool_file_sha256: str,
) -> CanonicalCandidatePoolV1:
    if pool.get("schema_id") != "FORMAL_ANALYZER_CANDIDATE_POOL_V1":
        raise ValueError("Formal candidate pool schema mismatch")

    objects = list(_walk_objects(dict(pool)))
    census = Counter(
        str(value.get("schema_id"))
        for _, _, value in objects
        if isinstance(value.get("schema_id"), str)
    )

    condition_refs: dict[str, set[str]] = defaultdict(set)
    proposal_condition_refs: dict[str, set[str]] = defaultdict(set)
    for _, condition, value in objects:
        if condition is None:
            continue
        for candidate_sha in _sha_values_under_candidate_keys(value):
            condition_refs[candidate_sha].add(condition)
        for proposal_sha in _sha_values_under_proposal_keys(value):
            proposal_condition_refs[proposal_sha].add(condition)

    proposals: dict[str, dict[str, object]] = {}
    groups: dict[str, dict[str, object]] = {}
    crosschecks_by_target: dict[str, list[dict[str, object]]] = defaultdict(list)

    for _, _, value in objects:
        schema_id = value.get("schema_id")
        if schema_id == "ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1":
            sha = _require_sha(
                value.get("source_proposal_sha256"),
                "source_proposal_sha256",
            )
            proposals.setdefault(sha, dict(value))
        elif schema_id == "ANALYZER_GROUP_MANIFEST_V1":
            sha = _require_sha(
                value.get("group_manifest_sha256"),
                "group_manifest_sha256",
            )
            groups.setdefault(sha, dict(value))
        elif schema_id == "ANALYZER_CROSSCHECK_RESULT_V1":
            target = _require_sha(
                value.get("target_artifact_sha256"),
                "target_artifact_sha256",
            )
            crosschecks_by_target[target].append(dict(value))

    # Index every repair-candidate object by its semantic candidate SHA.
    # Presence/executability alone is not enough for the scientific selected
    # denominator: the authoritative selector is the final
    # state_condition_outcomes ledger.
    candidate_objects: dict[str, list[dict[str, object]]] = defaultdict(list)
    candidate_paths: dict[str, list[str]] = defaultdict(list)

    for path, _, value in objects:
        if value.get("schema_id") != "ANALYZER_REPAIR_CANDIDATE_V1":
            continue
        if set(value) != _candidate_required_keyset():
            raise ValueError(
                "ANALYZER_REPAIR_CANDIDATE_V1 keyset mismatch at "
                + "/".join(path)
            )
        candidate_sha = _require_sha(
            value.get("candidate_sha256"),
            "candidate_sha256",
        )
        candidate_objects[candidate_sha].append(dict(value))
        candidate_paths[candidate_sha].append("/".join(path))

    outcome_rows = pool.get("state_condition_outcomes")
    if not isinstance(outcome_rows, list):
        raise ValueError(
            "FORMAL_ANALYZER_CANDIDATE_POOL_V1 must expose "
            "state_condition_outcomes as final selection authority"
        )
    if len(outcome_rows) != 60:
        raise ValueError(
            "expected 60 state_condition_outcomes, got "
            + str(len(outcome_rows))
        )

    def _selected_candidate_sha(
        row: Mapping[str, object],
    ) -> str:
        for key in (
            "selected_candidate_sha256",
            "selected_candidate_id",
        ):
            raw = row.get(key)
            if (
                isinstance(raw, str)
                and len(raw) == 64
                and all(ch in "0123456789abcdef" for ch in raw)
            ):
                return raw

        selected = row.get("selected_candidate")
        if isinstance(selected, dict):
            raw = selected.get("candidate_sha256")
            if isinstance(raw, str):
                return _require_sha(
                    raw,
                    "selected_candidate.candidate_sha256",
                )

        raw = row.get("candidate_sha256")
        if isinstance(raw, str):
            return _require_sha(
                raw,
                "state_condition_outcome.candidate_sha256",
            )

        raise ValueError(
            "state_condition_outcome lacks explicit selected candidate SHA"
        )

    def _outcome_condition(
        row: Mapping[str, object],
    ) -> str:
        condition = _condition_from_object(row, None)
        if condition is None:
            raise ValueError(
                "state_condition_outcome lacks registered A2/A3 condition"
            )
        return condition

    def _resolve_candidate(
        candidate_sha: str,
    ) -> dict[str, object]:
        rows = candidate_objects.get(candidate_sha, [])
        if not rows:
            raise ValueError(
                "selected candidate not found as "
                "ANALYZER_REPAIR_CANDIDATE_V1: "
                + candidate_sha
            )
        first = rows[0]
        for other in rows[1:]:
            if other != first:
                raise ValueError(
                    "same candidate SHA maps to non-identical objects"
                )
        return first

    def _build_row(
        *,
        condition: str,
        candidate_sha: str,
        candidate: Mapping[str, object],
        source_state_sha: str | None = None,
    ) -> CanonicalRepairCandidateV1:
        status = str(candidate["candidate_status"])
        if status not in ALL_STATUSES:
            raise ValueError("unregistered candidate status: " + status)

        candidate_state = _require_sha(
            candidate["source_state_sha256"],
            "source_state_sha256",
        )
        if source_state_sha is not None and source_state_sha != candidate_state:
            raise ValueError(
                "state-condition ledger state differs from candidate"
            )

        proposal_sha = _require_sha(
            candidate["source_proposal_sha256"],
            "source_proposal_sha256",
        )
        proposal = proposals.get(proposal_sha)
        group_manifest = None
        crosschecks: list[dict[str, object]] = []

        if proposal is not None:
            group_sha = _require_sha(
                proposal.get("group_manifest_sha256"),
                "group_manifest_sha256",
            )
            group_manifest = groups.get(group_sha)
            crosschecks.extend(
                crosschecks_by_target.get(proposal_sha, [])
            )
            crosschecks.extend(
                crosschecks_by_target.get(group_sha, [])
            )
        crosschecks.extend(
            crosschecks_by_target.get(candidate_sha, [])
        )

        exact_action = candidate["exact_action"]
        if exact_action is not None and not isinstance(exact_action, str):
            raise TypeError("exact_action must be string or null")

        option_raw = candidate["option_actions"]
        if not isinstance(option_raw, list):
            raise TypeError("option_actions must be array")
        option_actions = tuple(str(item) for item in option_raw)

        termination = candidate["termination_condition"]
        if termination is not None and not isinstance(termination, str):
            raise TypeError(
                "termination_condition must be string or null"
            )

        return CanonicalRepairCandidateV1(
            condition_id=condition,
            candidate_sha256=candidate_sha,
            source_state_sha256=candidate_state,
            menu_sha256=_require_sha(
                candidate["menu_sha256"],
                "menu_sha256",
            ),
            source_proposal_sha256=proposal_sha,
            candidate_status=status,
            exact_action=exact_action,
            option_actions=option_actions,
            termination_condition=termination,
            proposal=proposal,
            group_manifest=group_manifest,
            crosschecks=tuple(
                sorted(
                    crosschecks,
                    key=lambda item: str(
                        item.get("crosscheck_sha256")
                    ),
                )
            ),
            source_paths=tuple(
                sorted(candidate_paths[candidate_sha])
            ),
        )

    selected_rows: list[CanonicalRepairCandidateV1] = []
    selected_identities: set[tuple[str, str]] = set()

    for index, raw in enumerate(outcome_rows):
        if not isinstance(raw, dict):
            raise TypeError(
                f"state_condition_outcomes[{index}] must be object"
            )
        condition = _outcome_condition(raw)
        candidate_sha = _selected_candidate_sha(raw)
        candidate = _resolve_candidate(candidate_sha)

        ledger_state = None
        for key in (
            "source_state_sha256",
            "state_sha256",
            "decision_state_sha256",
        ):
            raw_state = raw.get(key)
            if isinstance(raw_state, str):
                ledger_state = _require_sha(raw_state, key)
                break

        row = _build_row(
            condition=condition,
            candidate_sha=candidate_sha,
            candidate=candidate,
            source_state_sha=ledger_state,
        )
        if not row.executable:
            raise ValueError(
                "final selected state-condition outcome is non-executable: "
                + candidate_sha
            )

        identity = (condition, candidate_sha)
        if identity in selected_identities:
            raise ValueError(
                "duplicate selected condition/candidate identity: "
                + repr(identity)
            )
        selected_identities.add(identity)
        selected_rows.append(row)

    # Preserve every extra candidate object in an audit side-channel. The key
    # invariant is that executable-but-unselected objects never alter the
    # registered 60 state-condition denominator.
    audit_rows: list[CanonicalRepairCandidateV1] = []
    audit_identities: set[tuple[str, str]] = set()

    for candidate_sha, candidate_rows in candidate_objects.items():
        candidate = _resolve_candidate(candidate_sha)
        proposal_sha = _require_sha(
            candidate["source_proposal_sha256"],
            "source_proposal_sha256",
        )

        possible_conditions = set(
            condition_refs.get(candidate_sha, set())
        )
        possible_conditions.update(
            proposal_condition_refs.get(proposal_sha, set())
        )

        for condition in sorted(possible_conditions):
            identity = (condition, candidate_sha)
            if (
                identity in selected_identities
                or identity in audit_identities
            ):
                continue
            audit_identities.add(identity)
            audit_rows.append(
                _build_row(
                    condition=condition,
                    candidate_sha=candidate_sha,
                    candidate=candidate,
                )
            )

    return CanonicalCandidatePoolV1(
        pool_file_sha256=pool_file_sha256,
        selected_candidates=tuple(
            sorted(
                selected_rows,
                key=lambda row: (
                    row.source_state_sha256,
                    row.condition_id,
                    row.candidate_sha256,
                ),
            )
        ),
        nonselected_candidates=tuple(
            sorted(
                audit_rows,
                key=lambda row: (
                    row.source_state_sha256,
                    row.condition_id,
                    row.candidate_sha256,
                ),
            )
        ),
        schema_object_census=dict(sorted(census.items())),
    )
