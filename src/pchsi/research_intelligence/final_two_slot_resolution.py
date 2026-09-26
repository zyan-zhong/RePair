"""Targeted resolution for the final two Strong-Researcher evidence slots.

This module does NOT broaden generic hydration authority. It resolves only:

1. policy_scorecard.policy_config_sha256
2. policy_scorecard.task_set_manifest_sha256

The first slot is known to be semantically bound by the sealed policy-lineage
artifact to ``policy_condition_manifest_sha256``. The alias is accepted only
when the current sealed lineage and a dedicated historical policy-condition
manifest agree on the exact SHA and policy-condition identity.

The second slot never substitutes task-access manifests, split-access
manifests, SCIENTIFIC_UNIT_IDENTITY records, or chat/history knowledge.
It accepts an exact readable task-set artifact, or a dedicated task-set
manifest whose own registered identity equals the bound SHA.

No current F0/F1 outcome, Human PRE decision, or future policy result is used.
"""

from __future__ import annotations

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
from pchsi.research_intelligence.strong_researcher_evidence_hydration import (
    build_reference_trace_v3,
    build_strong_blind_pre_input_v2,
    validate_hydrated_blind_input_v2,
)


POLICY_SLOT = "policy_scorecard.policy_config_sha256"
TASK_SET_SLOT = "policy_scorecard.task_set_manifest_sha256"

TEXT_SUFFIXES = frozenset(
    {
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".txt",
        ".md",
        ".cfg",
        ".ini",
    }
)
PRUNE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "node_modules",
        "raw_responses",
        "rendered_requests",
    }
)
MAX_FILE_BYTES = 32 * 1024 * 1024

FORBIDDEN_TASK_SET_SCHEMA_IDS = frozenset(
    {
        "SCIENTIFIC_UNIT_IDENTITY_V1",
    }
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _require_sha(value: object, name: str) -> str:
    if not _valid_sha(value):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return str(value)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_json_documents(path: Path):
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
        value = _load_json(path)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    yield "$", value


def _walk(value: object, path: str):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _walk(child, path + "/" + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, path + "/" + str(index))


def _name_affinity(text: str, tokens: Sequence[str]) -> bool:
    lower = text.lower().replace("-", "_")
    return all(token in lower for token in tokens)


def _readable_file(path: Path, data: bytes) -> tuple[str, object] | None:
    suffix = path.suffix.lower()
    if suffix in {".json", ".jsonl"}:
        docs = list(_iter_json_documents(path))
        if len(docs) == 1:
            return "FULL_JSON_DOCUMENT", docs[0][1]
        if docs:
            return "FULL_JSONL_DOCUMENTS", [value for _, value in docs]
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return "FULL_TEXT", text


def _policy_manifest_like(
    *,
    path: Path,
    obj: Mapping[str, object],
) -> bool:
    schema = obj.get("schema_id")
    searchable = path.name + " " + (schema if isinstance(schema, str) else "")
    return _name_affinity(
        searchable,
        ("policy", "condition", "manifest"),
    )


def _task_set_manifest_like(
    *,
    path: Path,
    obj: Mapping[str, object],
) -> bool:
    schema = obj.get("schema_id")
    if schema in FORBIDDEN_TASK_SET_SCHEMA_IDS:
        return False
    searchable = path.name + " " + (schema if isinstance(schema, str) else "")
    return _name_affinity(
        searchable,
        ("task", "set", "manifest"),
    )


@dataclass(frozen=True, slots=True)
class CandidateMatchV1:
    resolution_mode: str
    source_path: str
    source_file_sha256: str
    json_path: str | None
    schema_id: str | None
    object_sha256: str | None
    score: int
    content: object
    evidence_notes: tuple[str, ...]

    def content_identity(self) -> str:
        if self.object_sha256 is not None:
            return self.object_sha256
        if isinstance(self.content, str):
            return _sha256(self.content.encode("utf-8"))
        return _sha256(canonical_json_bytes(self.content))

    def to_dict(self) -> dict[str, object]:
        return {
            "resolution_mode": self.resolution_mode,
            "source_path": self.source_path,
            "source_file_sha256": self.source_file_sha256,
            "json_path": self.json_path,
            "schema_id": self.schema_id,
            "object_sha256": self.object_sha256,
            "score": self.score,
            "evidence_notes": list(self.evidence_notes),
        }


def _scan_policy_manifest_candidates(
    *,
    roots: Sequence[Path],
    target_sha: str,
    expected_policy_condition_id: str,
) -> tuple[list[CandidateMatchV1], list[dict[str, object]], dict[str, int]]:
    matches: list[CandidateMatchV1] = []
    occurrences: list[dict[str, object]] = []
    scanned = parsed = 0
    seen: set[tuple[int, int]] = set()
    target_bytes = target_sha.encode("ascii")

    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name for name in dirnames if name not in PRUNE_DIRS
            ]
            directory = Path(dirpath)
            for filename in filenames:
                path = directory / filename
                if path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    stat = path.stat()
                except OSError:
                    continue
                identity = (stat.st_dev, stat.st_ino)
                if identity in seen:
                    continue
                seen.add(identity)
                if stat.st_size > MAX_FILE_BYTES:
                    continue

                scanned += 1
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                file_sha = _sha256(data)

                if file_sha == target_sha:
                    readable = _readable_file(path, data)
                    if readable is not None:
                        kind, content = readable
                        if isinstance(content, dict):
                            condition = (
                                content.get("policy_condition_id")
                                or content.get("checkpoint_instance_id")
                                or content.get("policy_version")
                            )
                            if (
                                condition is not None
                                and condition != expected_policy_condition_id
                            ):
                                continue
                        matches.append(
                            CandidateMatchV1(
                                resolution_mode=(
                                    "SEMANTIC_ALIAS_EXACT_FILE_SHA256"
                                ),
                                source_path=str(path.resolve()),
                                source_file_sha256=file_sha,
                                json_path=None,
                                schema_id=(
                                    str(content.get("schema_id"))
                                    if isinstance(content, dict)
                                    and isinstance(
                                        content.get("schema_id"), str
                                    )
                                    else None
                                ),
                                object_sha256=(
                                    _sha256(canonical_json_bytes(content))
                                    if isinstance(content, dict)
                                    else None
                                ),
                                score=10000,
                                content=content,
                                evidence_notes=(
                                    "file SHA equals bound policy-config reference",
                                    "sealed policy lineage independently binds this SHA as policy_condition_manifest_sha256",
                                ),
                            )
                        )

                if target_bytes not in data:
                    continue
                if path.suffix.lower() not in {".json", ".jsonl"}:
                    continue
                parsed += 1

                for root_path, document in _iter_json_documents(path):
                    for json_path, obj in _walk(document, root_path):
                        if not isinstance(obj, dict):
                            continue
                        if obj.get(
                            "policy_condition_manifest_sha256"
                        ) != target_sha:
                            continue

                        condition = (
                            obj.get("policy_condition_id")
                            or obj.get("checkpoint_instance_id")
                            or obj.get("policy_version")
                        )
                        occurrence = {
                            "source_path": str(path.resolve()),
                            "json_path": json_path,
                            "schema_id": obj.get("schema_id"),
                            "condition_identity": condition,
                            "dedicated_manifest_like": _policy_manifest_like(
                                path=path,
                                obj=obj,
                            ),
                            "top_level_keys": sorted(str(k) for k in obj),
                        }
                        occurrences.append(occurrence)

                        if not _policy_manifest_like(path=path, obj=obj):
                            continue
                        if condition != expected_policy_condition_id:
                            continue

                        object_sha = _sha256(canonical_json_bytes(obj))
                        score = 8000
                        if "policy_condition_manifest_sha256" in obj:
                            score += 500
                        if isinstance(obj.get("schema_id"), str):
                            score += 500

                        matches.append(
                            CandidateMatchV1(
                                resolution_mode=(
                                    "SEMANTIC_ALIAS_POLICY_CONDITION_MANIFEST"
                                ),
                                source_path=str(path.resolve()),
                                source_file_sha256=file_sha,
                                json_path=json_path,
                                schema_id=(
                                    str(obj.get("schema_id"))
                                    if isinstance(obj.get("schema_id"), str)
                                    else None
                                ),
                                object_sha256=object_sha,
                                score=score,
                                content=obj,
                                evidence_notes=(
                                    "object registers policy_condition_manifest_sha256 equal to bound policy-config reference",
                                    "policy-condition identity equals sealed policy version",
                                ),
                            )
                        )

    return matches, occurrences, {
        "scanned_file_count": scanned,
        "parsed_target_file_count": parsed,
    }


def _scan_task_set_candidates(
    *,
    roots: Sequence[Path],
    target_sha: str,
) -> tuple[
    list[CandidateMatchV1],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, int],
]:
    matches: list[CandidateMatchV1] = []
    references: list[dict[str, object]] = []
    builder_hits: list[dict[str, object]] = []
    scanned = parsed = 0
    seen: set[tuple[int, int]] = set()
    target_bytes = target_sha.encode("ascii")

    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name for name in dirnames if name not in PRUNE_DIRS
            ]
            directory = Path(dirpath)
            for filename in filenames:
                path = directory / filename
                suffix = path.suffix.lower()
                if suffix not in TEXT_SUFFIXES and suffix != ".py":
                    continue
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    stat = path.stat()
                except OSError:
                    continue
                identity = (stat.st_dev, stat.st_ino)
                if identity in seen:
                    continue
                seen.add(identity)
                if stat.st_size > MAX_FILE_BYTES:
                    continue

                scanned += 1
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                file_sha = _sha256(data)

                if suffix == ".py":
                    if (
                        b"task_set_manifest_sha256" in data
                        and (
                            b"def " in data
                            or b"class " in data
                            or b"domain_hash" in data
                            or b"sha256" in data
                        )
                    ):
                        builder_hits.append(
                            {
                                "source_path": str(path.resolve()),
                                "file_sha256": file_sha,
                            }
                        )
                    continue

                if file_sha == target_sha:
                    readable = _readable_file(path, data)
                    if readable is not None:
                        kind, content = readable
                        if (
                            isinstance(content, dict)
                            and content.get("schema_id")
                            in FORBIDDEN_TASK_SET_SCHEMA_IDS
                        ):
                            pass
                        else:
                            matches.append(
                                CandidateMatchV1(
                                    resolution_mode=(
                                        "TASK_SET_EXACT_FILE_SHA256"
                                    ),
                                    source_path=str(path.resolve()),
                                    source_file_sha256=file_sha,
                                    json_path=None,
                                    schema_id=(
                                        str(content.get("schema_id"))
                                        if isinstance(content, dict)
                                        and isinstance(
                                            content.get("schema_id"), str
                                        )
                                        else None
                                    ),
                                    object_sha256=(
                                        _sha256(
                                            canonical_json_bytes(content)
                                        )
                                        if isinstance(content, dict)
                                        else None
                                    ),
                                    score=10000,
                                    content=content,
                                    evidence_notes=(
                                        "file SHA exactly equals bound task_set_manifest_sha256",
                                    ),
                                )
                            )

                if target_bytes not in data:
                    continue
                if suffix not in {".json", ".jsonl"}:
                    continue
                parsed += 1

                for root_path, document in _iter_json_documents(path):
                    for json_path, obj in _walk(document, root_path):
                        if not isinstance(obj, dict):
                            continue
                        if obj.get("task_set_manifest_sha256") != target_sha:
                            continue

                        schema = obj.get("schema_id")
                        task_set_like = _task_set_manifest_like(
                            path=path,
                            obj=obj,
                        )
                        references.append(
                            {
                                "source_path": str(path.resolve()),
                                "json_path": json_path,
                                "schema_id": schema,
                                "dedicated_task_set_manifest_like": (
                                    task_set_like
                                ),
                                "top_level_keys": sorted(str(k) for k in obj),
                            }
                        )

                        if not task_set_like:
                            continue

                        object_sha = _sha256(canonical_json_bytes(obj))
                        matches.append(
                            CandidateMatchV1(
                                resolution_mode=(
                                    "TASK_SET_REGISTERED_MANIFEST_IDENTITY"
                                ),
                                source_path=str(path.resolve()),
                                source_file_sha256=file_sha,
                                json_path=json_path,
                                schema_id=(
                                    str(schema)
                                    if isinstance(schema, str)
                                    else None
                                ),
                                object_sha256=object_sha,
                                score=8500,
                                content=obj,
                                evidence_notes=(
                                    "dedicated task-set manifest registers exact bound task_set_manifest_sha256",
                                ),
                            )
                        )

    return matches, references, builder_hits, {
        "scanned_file_count": scanned,
        "parsed_target_file_count": parsed,
    }


def _choose_unique(
    matches: Sequence[CandidateMatchV1],
) -> tuple[str, CandidateMatchV1 | None, list[dict[str, object]]]:
    ordered = sorted(
        matches,
        key=lambda row: (
            -row.score,
            row.source_path,
            row.json_path or "",
        ),
    )
    if not ordered:
        return "QUERY_REQUIRED_MISSING", None, []

    best_score = ordered[0].score
    best = [row for row in ordered if row.score == best_score]
    content_ids = {row.content_identity() for row in best}
    if len(content_ids) != 1:
        return (
            "QUERY_REQUIRED_AMBIGUOUS",
            None,
            [row.to_dict() for row in ordered[:200]],
        )

    selected = min(
        best,
        key=lambda row: (
            row.source_path,
            row.json_path or "",
        ),
    )
    return (
        "RESOLVED_READABLE",
        selected,
        [row.to_dict() for row in ordered[:200]],
    )


def _readable_view(
    *,
    selected: CandidateMatchV1,
    slot_id: str,
    target_sha: str,
    alias_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    content = selected.content
    if isinstance(content, str):
        projection = {
            "projection_kind": "FULL_TEXT",
            "content": content,
        }
    else:
        projection = {
            "projection_kind": "FULL_JSON_OBJECT",
            "content": content,
        }

    return {
        "projection_kind": "BOUND_SEMANTIC_RESOLUTION_V1",
        "slot_id": slot_id,
        "reference_sha256": target_sha,
        "resolution_mode": selected.resolution_mode,
        "authority": selected.to_dict(),
        "alias_metadata": (
            dict(alias_metadata)
            if alias_metadata is not None
            else None
        ),
        "artifact_view": projection,
    }


def resolve_policy_config_slot_v1(
    *,
    hydration_manifest: Mapping[str, object],
    roots: Sequence[Path],
) -> dict[str, object]:
    slots = {
        str(row["slot_id"]): row
        for row in hydration_manifest["slots"]
    }
    target = _require_sha(
        slots[POLICY_SLOT]["reference_sha256"],
        POLICY_SLOT,
    )

    lineage_lane = hydration_manifest["lane_views"][
        "policy_scorecard"
    ]["policy_lineage_sha256"]
    lineage_view = lineage_lane.get("readable_view")
    if not isinstance(lineage_view, dict):
        raise ValueError("policy lineage is not readable")
    lineage_content = lineage_view.get("content")
    if lineage_content is None:
        # Generic hydration wraps content directly; final-two-slot wrappers do
        # not apply to the already-resolved lineage slot.
        lineage_content = lineage_view.get("artifact_view", {}).get(
            "content"
        )
    if not isinstance(lineage_content, dict):
        raise ValueError("policy lineage content missing")

    lineage_bound = _require_sha(
        lineage_content.get("policy_condition_manifest_sha256"),
        "policy_lineage.policy_condition_manifest_sha256",
    )
    if lineage_bound != target:
        raise ValueError(
            "policy-config target is not the sealed policy-condition manifest"
        )
    expected_condition = str(lineage_content.get("policy_version") or "")
    if not expected_condition:
        raise ValueError("sealed policy lineage lacks policy_version")

    matches, occurrences, stats = _scan_policy_manifest_candidates(
        roots=roots,
        target_sha=target,
        expected_policy_condition_id=expected_condition,
    )
    status, selected, all_matches = _choose_unique(matches)

    slot = copy.deepcopy(slots[POLICY_SLOT])
    slot["status"] = status
    slot["all_matches"] = all_matches
    slot["selected_match"] = (
        None if selected is None else selected.to_dict()
    )
    slot["readable_view"] = (
        None
        if selected is None
        else _readable_view(
            selected=selected,
            slot_id=POLICY_SLOT,
            target_sha=target,
            alias_metadata={
                "source_reference_field": "policy_config_sha256",
                "resolved_semantics": "policy_condition_manifest",
                "sealed_policy_lineage_sha256": lineage_content.get(
                    "policy_lineage_sha256"
                ),
                "expected_policy_condition_id": expected_condition,
            },
        )
    )

    return {
        "slot": slot,
        "status": status,
        "target_sha256": target,
        "sealed_policy_lineage_binding": {
            "policy_lineage_sha256": lineage_content.get(
                "policy_lineage_sha256"
            ),
            "policy_condition_manifest_sha256": lineage_bound,
            "policy_version": expected_condition,
        },
        "candidate_occurrences": occurrences[:500],
        "candidate_occurrence_count": len(occurrences),
        "scan_statistics": stats,
    }


def resolve_task_set_slot_v1(
    *,
    hydration_manifest: Mapping[str, object],
    roots: Sequence[Path],
) -> dict[str, object]:
    slots = {
        str(row["slot_id"]): row
        for row in hydration_manifest["slots"]
    }
    target = _require_sha(
        slots[TASK_SET_SLOT]["reference_sha256"],
        TASK_SET_SLOT,
    )

    matches, references, builder_hits, stats = _scan_task_set_candidates(
        roots=roots,
        target_sha=target,
    )
    status, selected, all_matches = _choose_unique(matches)

    slot = copy.deepcopy(slots[TASK_SET_SLOT])
    slot["status"] = status
    slot["all_matches"] = all_matches
    slot["selected_match"] = (
        None if selected is None else selected.to_dict()
    )
    slot["readable_view"] = (
        None
        if selected is None
        else _readable_view(
            selected=selected,
            slot_id=TASK_SET_SLOT,
            target_sha=target,
        )
    )

    return {
        "slot": slot,
        "status": status,
        "target_sha256": target,
        "reference_occurrences": references[:1000],
        "reference_occurrence_count": len(references),
        "builder_source_candidates": builder_hits[:200],
        "builder_source_candidate_count": len(builder_hits),
        "deterministic_reconstruction_attempted": False,
        "deterministic_reconstruction_reason": (
            "No reconstruction is authorized without locating and separately "
            "reviewing the project's exact registered task-set hash builder."
        ),
        "scan_statistics": stats,
    }


def stitch_final_hydration_manifest_v1(
    *,
    base_manifest: Mapping[str, object],
    policy_resolution: Mapping[str, object],
    task_set_resolution: Mapping[str, object],
) -> dict[str, object]:
    if base_manifest.get("schema_id") != (
        "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1"
    ):
        raise ValueError("base hydration manifest schema mismatch")

    base_slots = copy.deepcopy(list(base_manifest["slots"]))
    base_by_id = {
        str(row["slot_id"]): row for row in base_slots
    }
    original_other = {
        slot_id: canonical_json_bytes(row)
        for slot_id, row in base_by_id.items()
        if slot_id not in {POLICY_SLOT, TASK_SET_SLOT}
    }

    for resolution, expected_slot in (
        (policy_resolution, POLICY_SLOT),
        (task_set_resolution, TASK_SET_SLOT),
    ):
        row = copy.deepcopy(resolution["slot"])
        if row.get("slot_id") != expected_slot:
            raise ValueError("resolution slot mismatch")
        base_by_id[expected_slot] = row

    stitched_slots = [
        base_by_id[str(row["slot_id"])]
        for row in base_slots
    ]

    # No previously resolved slot may change at this stage.
    for slot_id, expected_bytes in original_other.items():
        if canonical_json_bytes(base_by_id[slot_id]) != expected_bytes:
            raise ValueError(
                "final-two-slot resolver changed a pre-resolved slot: "
                + slot_id
            )

    lane_views = copy.deepcopy(base_manifest["lane_views"])
    for slot_id in (POLICY_SLOT, TASK_SET_SLOT):
        lane, field = slot_id.split(".", 1)
        row = base_by_id[slot_id]
        lane_views[lane][field] = {
            "reference_sha256": row["reference_sha256"],
            "status": row["status"],
            "readable_view": row["readable_view"],
        }

    required_bound = [
        row
        for row in stitched_slots
        if row["required_readable"]
        and row["reference_sha256"] is not None
    ]
    unresolved = [
        str(row["slot_id"])
        for row in required_bound
        if row["status"] != "RESOLVED_READABLE"
    ]

    result = copy.deepcopy(dict(base_manifest))
    result["slots"] = stitched_slots
    result["lane_views"] = lane_views
    result["required_bound_slot_count"] = len(required_bound)
    result["resolved_required_slot_count"] = (
        len(required_bound) - len(unresolved)
    )
    result["unresolved_required_slot_ids"] = unresolved
    result["hydration_ready"] = not unresolved
    result["final_two_slot_resolution"] = {
        "policy_config_status": policy_resolution["status"],
        "task_set_status": task_set_resolution["status"],
        "policy_config_resolution_semantics": (
            "policy_condition_manifest"
        ),
        "task_access_manifest_substitution_allowed": False,
        "scientific_unit_identity_substitution_allowed": False,
        "chat_history_backfill_allowed": False,
        "deterministic_task_set_reconstruction_performed": False,
    }
    result["hydration_manifest_sha256"] = "0" * 64
    result["hydration_manifest_sha256"] = domain_hash(
        "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1",
        result,
        excluded_field="hydration_manifest_sha256",
    )
    return result


def build_final_two_slot_artifacts_v1(
    *,
    blind_input_v1: Mapping[str, object],
    reference_trace_v2: Mapping[str, object],
    base_manifest: Mapping[str, object],
    policy_roots: Sequence[Path],
    task_set_roots: Sequence[Path],
) -> dict[str, object]:
    unresolved_before = set(
        base_manifest.get("unresolved_required_slot_ids", [])
    )
    if unresolved_before != {POLICY_SLOT, TASK_SET_SLOT}:
        raise ValueError(
            "expected exactly policy_config and task_set unresolved"
        )
    if blind_input_v1.get("blind_input_sha256") != (
        base_manifest.get("source_blind_input_v1_sha256")
    ):
        raise ValueError("base hydration/blind V1 identity mismatch")

    policy = resolve_policy_config_slot_v1(
        hydration_manifest=base_manifest,
        roots=policy_roots,
    )
    task_set = resolve_task_set_slot_v1(
        hydration_manifest=base_manifest,
        roots=task_set_roots,
    )
    manifest = stitch_final_hydration_manifest_v1(
        base_manifest=base_manifest,
        policy_resolution=policy,
        task_set_resolution=task_set,
    )

    blind_v2 = trace_v3 = None
    if manifest["hydration_ready"]:
        blind_v2 = build_strong_blind_pre_input_v2(
            blind_input_v1=blind_input_v1,
            hydration_manifest=manifest,
        )
        validate_hydrated_blind_input_v2(
            blind_input_v2=blind_v2,
            hydration_manifest=manifest,
        )
        trace_v3 = build_reference_trace_v3(
            reference_trace_v2=reference_trace_v2,
            hydration_manifest=manifest,
            blind_input_v2=blind_v2,
        )

    return {
        "policy_resolution": policy,
        "task_set_resolution": task_set,
        "hydration_manifest": manifest,
        "blind_input_v2": blind_v2,
        "reference_trace_v3": trace_v3,
    }
