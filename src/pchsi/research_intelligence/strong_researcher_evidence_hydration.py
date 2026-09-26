"""Content-addressed evidence hydration for blind Researcher PRE.

The Round Evidence and Researcher input packages intentionally carry immutable
SHA references. Those identities are sufficient for audit, but a model cannot
reason from an opaque hash alone. This module resolves already-frozen artifacts
from approved evidence roots, validates their identities, and constructs a
readable pre-outcome view without importing Human PRE decisions or future
outcomes.

No scientific authority is added:

- hydration may expose evidence already bound by Round Evidence;
- it may not invent missing historical evidence;
- it may not assign Benefit/Harm/Neutral/Uncertain;
- it may not expose Human selection/rationale;
- it may not expose strong-model benchmark per-task results.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import copy
import hashlib
import json
import os
from typing import Any

from pchsi.reference_loop.canonical import (
    canonical_json_bytes,
    domain_hash,
)


FORBIDDEN_PRE_KEYS = frozenset(
    {
        "current_f0f1_outcomes",
        "current_selected_f0f1_outcomes",
        "future_pi2_evaluation",
        "future_policy_evaluation",
        "current_human_pre",
        "human_pre_record",
        "human_selection",
        "human_selection_rationale",
        "strong_model_benchmark_per_task_results",
        "benchmark_per_task_results",
        "sealed_test_trajectory",
    }
)

REFERENCE_CONTAINER_SCHEMA_PREFIXES = (
    "ROUND_EVIDENCE_PACKAGE_",
    "RESEARCHER_ROUND_INPUT_PACKAGE_",
    "SHARED_RESEARCHER_PRE_PROJECTION_",
    "STRONG_RESEARCHER_BLIND_PRE_INPUT_",
    "RESEARCH_PLANNER_SHARED_PRE_INPUT_",
    "HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION_",
    "HUMAN_RESEARCHER_PRE_",
    "HUMAN_REFERENCE_EVIDENCE_BINDING_",
    "RESEARCH_PLANNER_REFERENCE_TRACE_",
    "HUMAN_PLANNER_ADJUDICATION_BUILD_REPORT_",
    "HUMAN_PRE_PREREQUISITE_REPORT_",
)


IDENTITY_CARRIER_SCHEMAS = frozenset(
    {
        "SCIENTIFIC_UNIT_IDENTITY_V1",
    }
)

REFERENCE_ONLY_METADATA_KEYS = frozenset(
    {
        "repair_effect_authority",
        "effect_authority",
        "budget_interpretation_status",
        "status",
        "forbidden_future_outcomes_absent",
        "sealed_test_details_absent",
    }
)

MAX_SCAN_FILE_BYTES = 32 * 1024 * 1024
MAX_EMBED_BYTES = 128 * 1024
SCAN_SUFFIXES = frozenset({
    ".json", ".jsonl", ".md", ".txt", ".yaml", ".yml",
    ".toml", ".cfg", ".ini",
})

PRUNE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "raw_responses",
        "rendered_requests",
        "node_modules",
        ".venv",
    }
)

COMPACT_KEY_TOKENS = (
    "schema",
    "round",
    "policy",
    "checkpoint",
    "config",
    "task",
    "family",
    "rollout",
    "success",
    "failure",
    "error",
    "mechanism",
    "count",
    "rate",
    "metric",
    "status",
    "result",
    "budget",
    "cost",
    "gpu",
    "api",
    "environment",
    "token",
    "call",
    "step",
    "training",
    "regression",
    "go_nogo",
    "nogo",
    "commit",
    "diff",
    "version",
    "seed",
    "lineage",
    "manifest",
    "aggregate",
    "latency",
    "throughput",
    "resource",
)


@dataclass(frozen=True, slots=True)
class EvidenceSlotSpecV1:
    lane: str
    field: str
    required_readable: bool
    identity_only_allowed: bool
    name_tokens: tuple[str, ...]

    @property
    def slot_id(self) -> str:
        return f"{self.lane}.{self.field}"

    def to_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane,
            "field": self.field,
            "slot_id": self.slot_id,
            "required_readable": self.required_readable,
            "identity_only_allowed": self.identity_only_allowed,
            "name_tokens": list(self.name_tokens),
        }


SLOT_SPECS: tuple[EvidenceSlotSpecV1, ...] = (
    EvidenceSlotSpecV1(
        "policy_scorecard",
        "policy_lineage_sha256",
        True,
        False,
        ("policy", "lineage"),
    ),
    EvidenceSlotSpecV1(
        "policy_scorecard",
        "policy_checkpoint_sha256",
        False,
        True,
        ("policy", "checkpoint"),
    ),
    EvidenceSlotSpecV1(
        "policy_scorecard",
        "policy_config_sha256",
        True,
        False,
        ("policy", "config"),
    ),
    EvidenceSlotSpecV1(
        "policy_scorecard",
        "task_set_manifest_sha256",
        True,
        False,
        ("task", "set", "manifest"),
    ),
    EvidenceSlotSpecV1(
        "policy_scorecard",
        "rollout_census_sha256",
        True,
        False,
        ("rollout", "census"),
    ),
    EvidenceSlotSpecV1(
        "policy_scorecard",
        "mechanical_failure_census_sha256",
        True,
        False,
        ("mechanical", "failure", "census"),
    ),
    EvidenceSlotSpecV1(
        "analyzer_evidence",
        "formal_result_manifest_sha256",
        True,
        False,
        ("formal", "result", "manifest"),
    ),
    EvidenceSlotSpecV1(
        "analyzer_evidence",
        "metric_report_sha256",
        True,
        False,
        ("metric", "report"),
    ),
    EvidenceSlotSpecV1(
        "experiment_history",
        "historical_f0f1_summary_sha256",
        True,
        False,
        ("f0f1", "summary"),
    ),
    EvidenceSlotSpecV1(
        "experiment_history",
        "historical_go_nogo_ledger_sha256",
        True,
        False,
        ("go", "nogo", "ledger"),
    ),
    EvidenceSlotSpecV1(
        "experiment_history",
        "previous_researcher_decisions_sha256",
        True,
        False,
        ("researcher", "decision"),
    ),
    EvidenceSlotSpecV1(
        "experiment_history",
        "training_history_sha256",
        True,
        False,
        ("training", "history"),
    ),
    EvidenceSlotSpecV1(
        "experiment_history",
        "code_config_diff_manifest_sha256",
        True,
        False,
        ("code", "config", "diff"),
    ),
    EvidenceSlotSpecV1(
        "resource_and_cost",
        "resource_budget_manifest_sha256",
        True,
        False,
        ("resource", "budget", "manifest"),
    ),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _assert_pre_outcome_safe(value: object, *, name: str) -> None:
    forbidden = FORBIDDEN_PRE_KEYS.intersection(_walk_keys(value))
    if forbidden:
        raise ValueError(
            f"{name} leaks forbidden pre-outcome keys: "
            + repr(sorted(forbidden))
        )


def _reference_container(schema_id: object) -> bool:
    if not isinstance(schema_id, str):
        return False
    return schema_id.startswith(REFERENCE_CONTAINER_SCHEMA_PREFIXES)


def _identity_carrier(schema_id: object) -> bool:
    return (
        isinstance(schema_id, str)
        and schema_id in IDENTITY_CARRIER_SCHEMAS
    )


def _reference_only_object(obj: Mapping[str, object]) -> bool:
    """Return True for schema-less maps that only point at other artifacts.

    This is a structural classifier, not an authority validator. Historical
    reference maps may contain sentinel text such as ``MISSING`` or
    ``NOT_BOUND`` in fields whose names end with ``_sha256``. Those values are
    not candidate evidence identities and must not abort a scan.

    Strict SHA validation remains at the actual bound-reference boundary
    (`build_hydration_manifest_v1`) and on selected authority identities.
    """
    if obj.get("schema_id") is not None:
        return False

    saw_sha_reference = False
    for key, value in obj.items():
        name = str(key)
        if name.endswith("_sha256"):
            # Classification is deliberately total/non-throwing. Any
            # schema-less map composed only of reference-shaped fields stays a
            # provenance/reference container even if one non-authoritative
            # field contains a sentinel or malformed historical value.
            saw_sha_reference = True
            continue
        if (
            name in REFERENCE_ONLY_METADATA_KEYS
            and (
                isinstance(value, (str, bool, int, float))
                or value is None
            )
        ):
            continue
        return False
    return saw_sha_reference


def _artifact_name_affinity(
    *,
    path: Path,
    schema_id: object,
    tokens: Sequence[str],
) -> int:
    searchable = (
        path.name
        + " "
        + (schema_id if isinstance(schema_id, str) else "")
    )
    return _token_score(searchable, tokens)


def _sealed_support_path(path: Path) -> bool:
    parts = set(path.parts)
    return (
        "05_round_evidence_seal" in parts
        and "support" in parts
    )


def _load_json_records(path: Path):
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield f"$line:{line_number}", value
        return
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    yield "$", value


def _walk_objects(value: object, path: str):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _walk_objects(child, path + "/" + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_objects(child, path + "/" + str(index))


def _token_score(text: str, tokens: Sequence[str]) -> int:
    lower = text.lower().replace("-", "_")
    return sum(1 for token in tokens if token in lower)


def _matching_identity_fields(
    obj: Mapping[str, object],
    target_sha: str,
) -> tuple[str, ...]:
    fields = []
    for key, value in obj.items():
        if (
            isinstance(value, str)
            and value == target_sha
            and (
                str(key).endswith("_sha256")
                or str(key) in {
                    "sha256",
                    "semantic_sha256",
                    "manifest_sha256",
                    "artifact_sha256",
                }
            )
        ):
            fields.append(str(key))
    return tuple(sorted(fields))


def _compact_projection(value: object) -> object:
    """Deterministic readable projection for a large JSON artifact."""
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, child in value.items():
            lower = str(key).lower()
            keep = any(token in lower for token in COMPACT_KEY_TOKENS)
            if keep:
                if isinstance(child, (str, int, float, bool)) or child is None:
                    text = child
                    if isinstance(text, str) and len(text) > 4000:
                        text = text[:4000] + "...[TRUNCATED]"
                    out[str(key)] = text
                elif isinstance(child, list):
                    if len(child) <= 50:
                        out[str(key)] = _compact_projection(child)
                    else:
                        out[str(key)] = {
                            "item_count": len(child),
                            "sample": _compact_projection(child[:10]),
                        }
                elif isinstance(child, dict):
                    out[str(key)] = _compact_projection(child)
            else:
                nested = _compact_projection(child)
                if isinstance(nested, dict) and nested:
                    out[str(key)] = nested
        return out
    if isinstance(value, list):
        return [_compact_projection(child) for child in value[:50]]
    return value


@dataclass(frozen=True, slots=True)
class ArtifactMatchV1:
    slot_id: str
    target_sha256: str
    source_path: str
    source_file_sha256: str
    match_type: str
    score: int
    json_path: str | None
    schema_id: str | None
    identity_fields: tuple[str, ...]
    object_sha256: str | None
    readable_value: object | None

    def scientific_identity(self) -> tuple[object, ...]:
        return (
            self.match_type,
            self.object_sha256
            if self.object_sha256 is not None
            else self.source_file_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "target_sha256": self.target_sha256,
            "source_path": self.source_path,
            "source_file_sha256": self.source_file_sha256,
            "match_type": self.match_type,
            "score": self.score,
            "json_path": self.json_path,
            "schema_id": self.schema_id,
            "identity_fields": list(self.identity_fields),
            "object_sha256": self.object_sha256,
        }


def _scan_artifact_matches(
    *,
    roots: Sequence[Path],
    targets: Mapping[str, tuple[EvidenceSlotSpecV1, str]],
) -> tuple[dict[str, list[ArtifactMatchV1]], dict[str, object]]:
    sha_to_slots: dict[str, list[EvidenceSlotSpecV1]] = defaultdict(list)
    for _, (spec, sha) in targets.items():
        sha_to_slots[sha].append(spec)
    target_bytes = {
        sha: sha.encode("ascii") for sha in sha_to_slots
    }

    matches: dict[str, list[ArtifactMatchV1]] = defaultdict(list)
    scanned_files = parsed_files = 0
    seen_files: set[tuple[int, int]] = set()

    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name for name in dirnames if name not in PRUNE_DIRS
            ]
            directory = Path(dirpath)
            for name in filenames:
                path = directory / name
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    stat = path.stat()
                except OSError:
                    continue
                identity = (stat.st_dev, stat.st_ino)
                if identity in seen_files:
                    continue
                seen_files.add(identity)
                if stat.st_size > MAX_SCAN_FILE_BYTES:
                    continue
                if path.suffix.lower() not in SCAN_SUFFIXES:
                    continue
                scanned_files += 1

                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                file_sha = _sha256_bytes(data)

                # Exact file-SHA matches are strongest. Small UTF-8 text
                # configs are readable evidence too; binary checkpoints remain
                # identity-only via their slot contract.
                for slot_id, (spec, target_sha) in targets.items():
                    if file_sha == target_sha:
                        readable = None
                        schema_id = None
                        json_path = None
                        object_sha = None
                        if path.suffix.lower() in {".json", ".jsonl"}:
                            records = list(_load_json_records(path))
                            if len(records) == 1 and isinstance(records[0][1], dict):
                                candidate = records[0][1]
                                candidate_schema = candidate.get("schema_id")
                                if not (
                                    _reference_container(candidate_schema)
                                    or _identity_carrier(candidate_schema)
                                    or _reference_only_object(candidate)
                                ):
                                    readable = candidate
                                    schema_id = candidate_schema
                                    json_path = records[0][0]
                                    object_sha = _sha256_bytes(
                                        canonical_json_bytes(readable)
                                    )
                        elif path.suffix.lower() in SCAN_SUFFIXES:
                            try:
                                readable = data.decode("utf-8")
                            except UnicodeDecodeError:
                                readable = None

                        matches[slot_id].append(
                            ArtifactMatchV1(
                                slot_id=slot_id,
                                target_sha256=target_sha,
                                source_path=str(path.resolve()),
                                source_file_sha256=file_sha,
                                match_type="EXACT_FILE_SHA256",
                                score=10000,
                                json_path=json_path,
                                schema_id=(
                                    str(schema_id)
                                    if isinstance(schema_id, str)
                                    else None
                                ),
                                identity_fields=(),
                                object_sha256=object_sha,
                                readable_value=readable,
                            )
                        )

                if path.suffix.lower() not in {".json", ".jsonl"}:
                    continue
                candidate_shas = [
                    sha for sha, needle in target_bytes.items()
                    if needle in data
                ]
                if not candidate_shas:
                    continue
                parsed_files += 1

                for root_path, document in _load_json_records(path):
                    for json_path, obj in _walk_objects(document, root_path):
                        if not isinstance(obj, dict):
                            continue
                        schema_id = obj.get("schema_id")
                        if (
                            _reference_container(schema_id)
                            or _identity_carrier(schema_id)
                            or _reference_only_object(obj)
                        ):
                            continue
                        for target_sha in candidate_shas:
                            identity_fields = _matching_identity_fields(
                                obj,
                                target_sha,
                            )
                            if not identity_fields:
                                continue
                            object_sha = _sha256_bytes(
                                canonical_json_bytes(obj)
                            )
                            for spec in sha_to_slots[target_sha]:
                                affinity = _artifact_name_affinity(
                                    path=path,
                                    schema_id=schema_id,
                                    tokens=spec.name_tokens,
                                )
                                # Identity-field references inside unrelated
                                # artifacts are provenance, not the artifact
                                # content requested by this slot.
                                if affinity < len(spec.name_tokens):
                                    continue
                                score = 5000
                                if spec.field in identity_fields:
                                    score += 1000
                                if isinstance(schema_id, str):
                                    score += 500
                                score += 300 * affinity
                                if _sealed_support_path(path):
                                    score += 500
                                matches[spec.slot_id].append(
                                    ArtifactMatchV1(
                                        slot_id=spec.slot_id,
                                        target_sha256=target_sha,
                                        source_path=str(path.resolve()),
                                        source_file_sha256=file_sha,
                                        match_type="IDENTITY_FIELD",
                                        score=score,
                                        json_path=json_path,
                                        schema_id=(
                                            str(schema_id)
                                            if isinstance(schema_id, str)
                                            else None
                                        ),
                                        identity_fields=identity_fields,
                                        object_sha256=object_sha,
                                        readable_value=obj,
                                    )
                                )

    return matches, {
        "scanned_file_count": scanned_files,
        "parsed_file_count": parsed_files,
        "unique_files_by_inode": len(seen_files),
    }


def _resolve_slot(
    *,
    spec: EvidenceSlotSpecV1,
    target_sha: str | None,
    matches: Sequence[ArtifactMatchV1],
) -> dict[str, object]:
    if target_sha is None:
        return {
            "slot_id": spec.slot_id,
            "lane": spec.lane,
            "field": spec.field,
            "reference_sha256": None,
            "status": "ABSENT_NOT_BOUND",
            "required_readable": spec.required_readable,
            "identity_only_allowed": spec.identity_only_allowed,
            "selected_match": None,
            "all_matches": [],
            "readable_view": None,
        }

    _require_sha(target_sha, spec.slot_id)

    # Policy checkpoint bytes are intentionally identity-only. Resolving large
    # binary weights adds no Researcher evidence and wastes the prompt budget.
    if spec.identity_only_allowed:
        return {
            "slot_id": spec.slot_id,
            "lane": spec.lane,
            "field": spec.field,
            "reference_sha256": target_sha,
            "status": "IDENTITY_ONLY",
            "required_readable": False,
            "identity_only_allowed": True,
            "selected_match": None,
            "all_matches": [
                match.to_dict()
                for match in sorted(
                    matches,
                    key=lambda row: (-row.score, row.source_path),
                )[:20]
            ],
            "readable_view": {
                "identity_sha256": target_sha,
                "interpretation": (
                    "Frozen checkpoint identity only; model weights are not "
                    "Researcher-readable evidence."
                ),
            },
        }

    if not matches:
        return {
            "slot_id": spec.slot_id,
            "lane": spec.lane,
            "field": spec.field,
            "reference_sha256": target_sha,
            "status": "QUERY_REQUIRED_MISSING",
            "required_readable": spec.required_readable,
            "identity_only_allowed": False,
            "selected_match": None,
            "all_matches": [],
            "readable_view": None,
        }

    best_score = max(match.score for match in matches)
    best = [
        match for match in matches if match.score == best_score
    ]

    # Multiple copied files or review-bundle copies are acceptable if their
    # scientific content identity is identical.
    identities = {
        match.scientific_identity() for match in best
    }
    if len(identities) != 1:
        return {
            "slot_id": spec.slot_id,
            "lane": spec.lane,
            "field": spec.field,
            "reference_sha256": target_sha,
            "status": "QUERY_REQUIRED_AMBIGUOUS",
            "required_readable": spec.required_readable,
            "identity_only_allowed": False,
            "selected_match": None,
            "all_matches": [
                match.to_dict()
                for match in sorted(
                    matches,
                    key=lambda row: (-row.score, row.source_path),
                )[:200]
            ],
            "readable_view": None,
        }

    selected = min(
        best,
        key=lambda row: (
            row.source_path,
            row.json_path or "",
        ),
    )
    value = selected.readable_value
    if value is None:
        return {
            "slot_id": spec.slot_id,
            "lane": spec.lane,
            "field": spec.field,
            "reference_sha256": target_sha,
            "status": "QUERY_REQUIRED_NOT_READABLE",
            "required_readable": spec.required_readable,
            "identity_only_allowed": False,
            "selected_match": selected.to_dict(),
            "all_matches": [
                match.to_dict()
                for match in sorted(
                    matches,
                    key=lambda row: (-row.score, row.source_path),
                )[:200]
            ],
            "readable_view": None,
        }

    _assert_pre_outcome_safe(value, name=spec.slot_id)
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        if len(encoded) <= MAX_EMBED_BYTES:
            readable_view = {
                "projection_kind": "FULL_TEXT",
                "content": value,
            }
        else:
            readable_view = {
                "projection_kind": "DETERMINISTIC_COMPACT_TEXT",
                "source_text_bytes": len(encoded),
                "content": value[:MAX_EMBED_BYTES],
            }
    else:
        raw_bytes = canonical_json_bytes(value)
        if len(raw_bytes) <= MAX_EMBED_BYTES:
            readable_view = {
                "projection_kind": "FULL_JSON_OBJECT",
                "content": value,
            }
        else:
            compact = _compact_projection(value)
            _assert_pre_outcome_safe(
                compact,
                name=spec.slot_id + ".compact",
            )
            readable_view = {
                "projection_kind": "DETERMINISTIC_COMPACT_JSON",
                "source_canonical_json_bytes": len(raw_bytes),
                "content": compact,
            }

    return {
        "slot_id": spec.slot_id,
        "lane": spec.lane,
        "field": spec.field,
        "reference_sha256": target_sha,
        "status": "RESOLVED_READABLE",
        "required_readable": spec.required_readable,
        "identity_only_allowed": False,
        "selected_match": selected.to_dict(),
        "all_matches": [
            match.to_dict()
            for match in sorted(
                matches,
                key=lambda row: (-row.score, row.source_path),
            )[:200]
        ],
        "readable_view": readable_view,
    }


def build_hydration_manifest_v1(
    *,
    blind_input_v1: Mapping[str, object],
    roots: Sequence[Path],
) -> dict[str, object]:
    if blind_input_v1.get("schema_id") != (
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1"
    ):
        raise ValueError("blind V1 schema mismatch")
    _assert_pre_outcome_safe(blind_input_v1, name="blind_input_v1")

    targets: dict[str, tuple[EvidenceSlotSpecV1, str]] = {}
    raw_references: dict[str, str | None] = {}
    for spec in SLOT_SPECS:
        lane = blind_input_v1.get(spec.lane)
        if not isinstance(lane, dict):
            raise ValueError(f"blind V1 lacks lane {spec.lane}")
        value = lane.get(spec.field)
        if value is not None:
            value = _require_sha(value, spec.slot_id)
            targets[spec.slot_id] = (spec, value)
        raw_references[spec.slot_id] = value

    matches, scan_stats = _scan_artifact_matches(
        roots=roots,
        targets=targets,
    )

    slots = []
    for spec in SLOT_SPECS:
        slots.append(
            _resolve_slot(
                spec=spec,
                target_sha=raw_references[spec.slot_id],
                matches=matches.get(spec.slot_id, []),
            )
        )

    required_bound = [
        slot for slot in slots
        if slot["required_readable"]
        and slot["reference_sha256"] is not None
    ]
    unresolved_required = [
        slot["slot_id"]
        for slot in required_bound
        if slot["status"] != "RESOLVED_READABLE"
    ]

    lane_views: dict[str, dict[str, object]] = defaultdict(dict)
    for slot in slots:
        lane_views[str(slot["lane"])][str(slot["field"])] = {
            "reference_sha256": slot["reference_sha256"],
            "status": slot["status"],
            "readable_view": slot["readable_view"],
        }

    root_records = []
    seen_roots: set[tuple[int, int]] = set()
    for root in roots:
        resolved = root.resolve()
        if not resolved.is_dir():
            continue
        stat = resolved.stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity in seen_roots:
            continue
        seen_roots.add(identity)
        root_records.append(
            {
                "path": str(resolved),
                "device": stat.st_dev,
                "inode": stat.st_ino,
            }
        )

    result = {
        "schema_id": (
            "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1"
        ),
        "schema_version": 1,
        "source_blind_input_v1_sha256": blind_input_v1[
            "blind_input_sha256"
        ],
        "slot_count": len(slots),
        "required_bound_slot_count": len(required_bound),
        "resolved_required_slot_count": (
            len(required_bound) - len(unresolved_required)
        ),
        "unresolved_required_slot_ids": unresolved_required,
        "hydration_ready": not unresolved_required,
        "slots": slots,
        "lane_views": {
            lane: dict(values)
            for lane, values in sorted(lane_views.items())
        },
        "scan_roots": root_records,
        "scan_statistics": scan_stats,
        "future_outcomes_visible": False,
        "human_decision_visible": False,
        "benchmark_per_task_results_visible": False,
        "success_trajectory_optimization_active": False,
        "hydration_manifest_sha256": "0" * 64,
    }
    result["hydration_manifest_sha256"] = domain_hash(
        "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1",
        result,
        excluded_field="hydration_manifest_sha256",
    )
    return result


def build_strong_blind_pre_input_v2(
    *,
    blind_input_v1: Mapping[str, object],
    hydration_manifest: Mapping[str, object],
) -> dict[str, object]:
    if hydration_manifest.get("schema_id") != (
        "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1"
    ):
        raise ValueError("hydration manifest schema mismatch")
    if hydration_manifest.get("hydration_ready") is not True:
        raise ValueError(
            "cannot build blind V2 with unresolved required evidence"
        )
    if hydration_manifest.get(
        "source_blind_input_v1_sha256"
    ) != blind_input_v1.get("blind_input_sha256"):
        raise ValueError("hydration/blind V1 identity mismatch")

    result = dict(blind_input_v1)
    result["schema_id"] = "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2"
    result["schema_version"] = 2
    result["source_blind_input_v1_sha256"] = (
        blind_input_v1["blind_input_sha256"]
    )
    result["evidence_hydration_manifest_sha256"] = (
        hydration_manifest["hydration_manifest_sha256"]
    )
    # Do not share mutable nested objects with the hydration manifest.
    # A reviewed manifest and the model-facing blind input must remain
    # independently content-addressed artifacts.
    result["readable_evidence_views"] = copy.deepcopy(
        hydration_manifest["lane_views"]
    )
    result["evidence_hydration_contract"] = {
        "all_non_null_required_references_resolved": True,
        "null_historical_references_remain_absent": True,
        "policy_checkpoint_is_identity_only": True,
        "artifacts_are_read_only": True,
        "human_decision_visible": False,
        "current_f0f1_outcomes_visible": False,
        "benchmark_per_task_results_visible": False,
        "success_trajectory_optimization_active": False,
    }
    result["blind_input_sha256"] = "0" * 64

    # Preserve the same visibility boundary and strengthen it.
    visibility = result.get("visibility_boundary")
    if not isinstance(visibility, dict):
        raise ValueError("blind input lacks visibility boundary")
    for field in (
        "human_pre_visible",
        "human_pre_hash_visible",
        "human_selection_visible",
        "human_rationale_visible",
        "current_f0f1_outcomes_visible",
        "future_policy_evaluation_visible",
        "strong_model_benchmark_per_task_results_visible",
        "success_trajectory_optimization_active",
    ):
        if visibility.get(field) is not False:
            raise ValueError(
                "blind V2 visibility boundary violated: " + field
            )

    _assert_pre_outcome_safe(result, name="blind_input_v2")
    result["blind_input_sha256"] = domain_hash(
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2",
        result,
        excluded_field="blind_input_sha256",
    )
    return result


def build_reference_trace_v3(
    *,
    reference_trace_v2: Mapping[str, object],
    hydration_manifest: Mapping[str, object],
    blind_input_v2: Mapping[str, object],
) -> dict[str, object]:
    if reference_trace_v2.get("schema_id") != (
        "RESEARCH_PLANNER_REFERENCE_TRACE_V2"
    ):
        raise ValueError("reference trace V2 schema mismatch")
    if blind_input_v2.get("schema_id") != (
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2"
    ):
        raise ValueError("blind input V2 schema mismatch")
    if hydration_manifest.get("hydration_ready") is not True:
        raise ValueError("reference trace V3 requires ready hydration")

    trace = dict(reference_trace_v2)
    trace["schema_id"] = "RESEARCH_PLANNER_REFERENCE_TRACE_V3"
    trace["schema_version"] = 3
    trace["source_reference_trace_v2_sha256"] = (
        reference_trace_v2["trace_sha256"]
    )
    trace["evidence_hydration_manifest_sha256"] = (
        hydration_manifest["hydration_manifest_sha256"]
    )
    pre = dict(trace["pre_decision"])
    pre["source_strong_blind_input_v1_sha256"] = pre.get(
        "strong_blind_input_sha256"
    )
    pre["strong_blind_input_sha256"] = blind_input_v2[
        "blind_input_sha256"
    ]
    trace["pre_decision"] = pre
    trace["trace_sha256"] = "0" * 64
    trace["trace_sha256"] = domain_hash(
        "RESEARCH_PLANNER_REFERENCE_TRACE_V3",
        trace,
        excluded_field="trace_sha256",
    )
    return trace


def validate_hydrated_blind_input_v2(
    *,
    blind_input_v2: Mapping[str, object],
    hydration_manifest: Mapping[str, object],
) -> None:
    if blind_input_v2.get("schema_id") != (
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2"
    ):
        raise ValueError("blind V2 schema mismatch")
    if hydration_manifest.get("schema_id") != (
        "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1"
    ):
        raise ValueError("hydration manifest schema mismatch")
    if hydration_manifest.get("hydration_ready") is not True:
        raise ValueError("hydration manifest is not ready")

    expected_manifest_sha = domain_hash(
        "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1",
        dict(hydration_manifest),
        excluded_field="hydration_manifest_sha256",
    )
    if hydration_manifest.get(
        "hydration_manifest_sha256"
    ) != expected_manifest_sha:
        raise ValueError("hydration manifest SHA mismatch")

    if blind_input_v2.get(
        "evidence_hydration_manifest_sha256"
    ) != expected_manifest_sha:
        raise ValueError("blind V2 hydration manifest mismatch")
    if blind_input_v2.get(
        "source_blind_input_v1_sha256"
    ) != hydration_manifest.get(
        "source_blind_input_v1_sha256"
    ):
        raise ValueError("blind V2 source V1 identity mismatch")

    expected_blind_sha = domain_hash(
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2",
        dict(blind_input_v2),
        excluded_field="blind_input_sha256",
    )
    if blind_input_v2.get("blind_input_sha256") != expected_blind_sha:
        raise ValueError("blind V2 SHA mismatch")

    _assert_pre_outcome_safe(
        blind_input_v2,
        name="blind_input_v2",
    )
    visibility = blind_input_v2.get("visibility_boundary")
    if not isinstance(visibility, dict):
        raise ValueError("blind V2 visibility boundary missing")
    for field in (
        "human_pre_visible",
        "human_pre_hash_visible",
        "human_selection_visible",
        "human_rationale_visible",
        "current_f0f1_outcomes_visible",
        "future_policy_evaluation_visible",
        "strong_model_benchmark_per_task_results_visible",
        "success_trajectory_optimization_active",
    ):
        if visibility.get(field) is not False:
            raise ValueError(
                "blind V2 visibility boundary violated: " + field
            )
