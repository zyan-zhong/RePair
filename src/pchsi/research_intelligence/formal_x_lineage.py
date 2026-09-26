"""Bind selected repair candidates to Formal G/X and A3 Analyzer Memory.

The selected repair candidate is a source-state-level proposal. Formal X is a
*group-condition-level* cross-check whose target is the validated Formal G
artifact, not the candidate or source proposal.  This module follows the
registered identifiers instead of trying to join X through candidate/proposal
SHA fields directly.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Any

from pchsi.reference_loop.canonical import domain_hash


SHA_LENGTH = 64
REGISTERED_X_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "target_artifact_sha256",
        "disposition",
        "supporting_evidence_sha256s",
        "contradiction_evidence_sha256s",
        "residual_case_ids",
        "current_evidence_sha256s",
        "historical_evidence_sha256s",
        "crosscheck_sha256",
    }
)
REGISTERED_X_DISPOSITIONS = frozenset(
    {
        "ACCEPT",
        "DOWNGRADE_SCOPE",
        "REQUIRE_ABSTENTION",
        "REJECT",
    }
)
EXECUTABLE_CANDIDATE_STATUSES = frozenset(
    {"EXECUTABLE_EXACT_ACTION", "EXECUTABLE_SHORT_OPTION"}
)


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != SHA_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def load_json_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def walk_objects(value: object, path: str = "$"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from walk_objects(child, path + "/" + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_objects(child, path + "/" + str(index))


def iter_json_documents(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        if path.stat().st_size > 64 * 1024 * 1024:
            continue
        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield path, f"$line:{line_number}", value
        else:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            yield path, "$", value


def normalized_condition(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    upper = value.upper()
    if upper == "A2" or upper.startswith("A2_") or upper.startswith("G-A2"):
        return "A2"
    if upper == "A3" or upper.startswith("A3_") or upper.startswith("G-A3"):
        return "A3"
    return None


def resolve_registered_path(
    raw_path: object,
    *,
    allowed_roots: Sequence[Path],
    expected_file_sha256: str | None = None,
) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("registered artifact path must be non-empty string")
    source = Path(raw_path)
    candidates: list[Path] = []
    if source.is_absolute():
        candidates.append(source)
        # /data/home and /data/run01 are aliases on the target cluster.  Try
        # the same relative tail under every registered root as a safe legacy
        # compatibility path, but never search outside allowed roots.
        for root in allowed_roots:
            try:
                relative = source.relative_to(root)
            except ValueError:
                continue
            candidates.append(root / relative)
    else:
        candidates.extend(root / source for root in allowed_roots)

    observed: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.is_file() or resolved.is_symlink():
            continue
        if not any(resolved.is_relative_to(root.resolve()) for root in allowed_roots):
            continue
        observed.append(resolved)

    unique = {path: None for path in observed}
    if len(unique) != 1:
        raise ValueError(
            "registered path did not resolve to exactly one allowed file: "
            + raw_path
            + " -> "
            + repr([str(path) for path in unique])
        )
    path = next(iter(unique))
    if expected_file_sha256 is not None:
        expected = require_sha(expected_file_sha256, "expected file SHA")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"registered artifact file SHA mismatch: {path}: {actual} != {expected}"
            )
    return path


def _object_identity(value: Mapping[str, object]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(value)))


def _insert_unique(
    mapping: dict[str, tuple[dict[str, Any], list[str]]],
    key: str,
    value: Mapping[str, object],
    source: str,
) -> None:
    """Strict whole-object uniqueness for authorities that require it.

    Formal batch-result objects remain byte/field-identical for one custom_id.
    X registry descriptions use a separate representation-aware insert path.
    """
    current = mapping.get(key)
    row = dict(value)
    if current is None:
        mapping[key] = (row, [source])
        return
    if current[0] != row:
        raise ValueError(f"identity {key} maps to non-identical objects")
    current[1].append(source)


X_REGISTRY_REQUIRED_SCIENTIFIC_FIELDS = (
    "stage_id",
    "custom_id",
    "condition_id",
    "target_custom_id",
    "group_manifest_sha256",
    "expected_memory_pack_sha256",
)

# When two representations both assert one of these fields, disagreement is a
# scientific conflict.  Absence in one representation is not a conflict:
# registry/schedule/preflight containers legitimately expose different subsets.
X_REGISTRY_OPTIONAL_SCIENTIFIC_FIELDS = (
    "source_unit_id",
    "scientific_unit_id",
    "round_id",
    "policy_version",
    "task_id",
    "gamefile_sha256",
    "expected_common_evidence_sha256",
    "expected_a1_local_result_sha256",
    "input_projection_sha256",
    "request_body_sha256",
    "prompt_template_id",
    "prompt_sha256",
)


def _normalize_x_registry_claim(field: str, value: object) -> object:
    if field == "stage_id":
        if value != "X":
            raise ValueError("X registry stage_id must be X")
        return "X"
    if field == "custom_id":
        if not isinstance(value, str) or not value:
            raise ValueError("X registry custom_id must be non-empty")
        return value
    if field == "condition_id":
        condition = normalized_condition(value)
        if condition is None:
            raise ValueError("X registry condition must be A2/A3")
        return condition
    if field in {"target_custom_id", "source_unit_id", "scientific_unit_id",
                 "round_id", "policy_version", "task_id", "prompt_template_id"}:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise ValueError(f"X registry {field} must be non-empty when present")
        return value
    if field in {
        "group_manifest_sha256",
        "gamefile_sha256",
        "expected_common_evidence_sha256",
        "expected_a1_local_result_sha256",
        "input_projection_sha256",
        "request_body_sha256",
        "prompt_sha256",
    }:
        if value is None:
            return None
        return require_sha(value, field)
    if field == "expected_memory_pack_sha256":
        if value is None:
            return None
        return require_sha(value, field)
    return value


def _x_registry_scientific_claims(
    value: Mapping[str, object],
    *,
    require_complete: bool,
) -> dict[str, object]:
    claims: dict[str, object] = {}
    for field in (
        *X_REGISTRY_REQUIRED_SCIENTIFIC_FIELDS,
        *X_REGISTRY_OPTIONAL_SCIENTIFIC_FIELDS,
    ):
        if field not in value:
            if require_complete and field in X_REGISTRY_REQUIRED_SCIENTIFIC_FIELDS:
                raise ValueError(f"X registry missing required scientific field: {field}")
            continue
        claims[field] = _normalize_x_registry_claim(field, value.get(field))

    # Required fields may legitimately use null only for A2 Memory.
    if require_complete:
        condition = claims["condition_id"]
        if claims["target_custom_id"] is None:
            raise ValueError("X registry target_custom_id cannot be null")
        require_sha(claims["group_manifest_sha256"], "group_manifest_sha256")
        memory = claims["expected_memory_pack_sha256"]
        if condition == "A2" and memory is not None:
            raise ValueError("A2 X registry cannot claim Analyzer Memory")
        if condition == "A3" and memory is None:
            raise ValueError("A3 X registry must claim Analyzer Memory")
    return claims


def _merge_x_registry_scientific_claims(
    *,
    key: str,
    left: Mapping[str, object],
    right: Mapping[str, object],
) -> dict[str, object]:
    merged = dict(left)
    for field, value in right.items():
        if field not in merged or merged[field] is None:
            merged[field] = value
            continue
        if value is None:
            continue
        if merged[field] != value:
            raise ValueError(
                f"X registry scientific identity conflict for {key}: "
                f"{field}: {merged[field]!r} != {value!r}"
            )
    return merged


def _representation_record(
    *,
    value: Mapping[str, object],
    source: str,
) -> dict[str, object]:
    row = dict(value)
    return {
        "source": source,
        "object_sha256": _object_identity(row),
        "keys": sorted(row),
        "projection_path": row.get("projection_path"),
        "scientific_claims": _x_registry_scientific_claims(
            row,
            require_complete=False,
        ),
    }


def _insert_x_registry_representation(
    mapping: dict[str, tuple[dict[str, Any], list[str]]],
    representations: dict[str, list[dict[str, object]]],
    key: str,
    value: Mapping[str, object],
    source: str,
) -> None:
    """Merge compatible descriptions of one X scientific unit.

    A custom_id may appear in registry, schedule, preflight, or copied-review
    containers with different provenance/path metadata.  Those descriptions are
    preserved, while overlapping scientific claims must agree exactly.
    """
    row = dict(value)
    if str(row.get("custom_id")) != key:
        raise ValueError("X registry custom_id/key mismatch")
    claims = _x_registry_scientific_claims(row, require_complete=False)
    rep = _representation_record(value=row, source=source)
    representations.setdefault(key, []).append(rep)

    current = mapping.get(key)
    if current is None:
        mapping[key] = (row, [source])
        return

    current_row, sources = current
    current_claims = _x_registry_scientific_claims(
        current_row,
        require_complete=False,
    )
    merged_claims = _merge_x_registry_scientific_claims(
        key=key,
        left=current_claims,
        right=claims,
    )

    # Pick the richest representation deterministically for non-scientific
    # wrapper metadata, then overlay the merged scientific claims.  This avoids
    # scan-order authority while retaining a usable projection_path.
    candidates = [current_row, row]
    representative = min(
        candidates,
        key=lambda item: (
            -sum(value is not None for value in item.values()),
            _object_identity(item),
        ),
    )
    merged_row = dict(representative)
    merged_row.update(merged_claims)

    # projection_path is a registered location, not scientific identity. If
    # several compatible copies exist, choose deterministically and preserve all
    # of them in the representation audit.
    paths = sorted(
        {
            str(item.get("projection_path"))
            for item in candidates
            if isinstance(item.get("projection_path"), str)
            and item.get("projection_path")
        }
    )
    if paths:
        merged_row["projection_path"] = paths[0]

    mapping[key] = (merged_row, sources + [source])


def x_registry_representation_audit_v1(
    indexes: "FormalXIndexesV1",
) -> dict[str, object]:
    rows = []
    duplicate_count = 0
    representation_count = 0
    for custom_id in sorted(indexes.x_registry_representations):
        reps = indexes.x_registry_representations[custom_id]
        representation_count += len(reps)
        if len(reps) > 1:
            duplicate_count += 1
        merged = indexes.x_registry_rows[custom_id][0]
        scientific_claims = _x_registry_scientific_claims(
            merged,
            require_complete=True,
        )
        rows.append(
            {
                "custom_id": custom_id,
                "representation_count": len(reps),
                "representation_object_sha256s": sorted(
                    str(rep["object_sha256"]) for rep in reps
                ),
                "source_records": sorted(
                    str(rep["source"]) for rep in reps
                ),
                "projection_paths": sorted(
                    {
                        str(rep["projection_path"])
                        for rep in reps
                        if isinstance(rep.get("projection_path"), str)
                        and rep.get("projection_path")
                    }
                ),
                "canonical_scientific_claims": scientific_claims,
                "canonical_scientific_identity_sha256": sha256_bytes(
                    canonical_json_bytes(scientific_claims)
                ),
            }
        )
    return {
        "schema_id": "FORMAL_X_REGISTRY_REPRESENTATION_AUDIT_V1",
        "schema_version": 1,
        "recognized_representation_count": representation_count,
        "unique_custom_id_count": len(rows),
        "duplicate_custom_id_count": duplicate_count,
        "rows": rows,
    }


@dataclass(frozen=True, slots=True)
class FormalXIndexesV1:
    candidate_wrappers: dict[
        tuple[str, str, str], tuple[dict[str, Any], list[str]]
    ]
    batch_results: dict[str, tuple[dict[str, Any], list[str]]]
    x_registry_rows: dict[str, tuple[dict[str, Any], list[str]]]
    x_registry_representations: dict[str, list[dict[str, object]]]
    scan_file_count: int
    scan_object_count: int


def build_formal_x_indexes_v1(root: Path) -> FormalXIndexesV1:
    wrappers: dict[
        tuple[str, str, str], tuple[dict[str, Any], list[str]]
    ] = {}
    batch: dict[str, tuple[dict[str, Any], list[str]]] = {}
    registry: dict[str, tuple[dict[str, Any], list[str]]] = {}
    registry_representations: dict[str, list[dict[str, object]]] = {}
    file_count = object_count = 0

    for source_file, document_path, document in iter_json_documents(root):
        file_count += 1
        for json_path, obj in walk_objects(document, document_path):
            if not isinstance(obj, dict):
                continue
            object_count += 1
            source = f"{source_file.resolve()}#{json_path}"

            candidate = obj.get("candidate")
            if (
                isinstance(candidate, dict)
                and candidate.get("schema_id") == "ANALYZER_REPAIR_CANDIDATE_V1"
                and isinstance(obj.get("g_custom_id"), str)
                and isinstance(obj.get("x_custom_id"), str)
            ):
                condition = normalized_condition(obj.get("condition_id"))
                if condition is None:
                    raise ValueError("candidate projector wrapper lacks A2/A3 condition")
                candidate_sha = require_sha(
                    candidate.get("candidate_sha256"), "candidate_sha256"
                )
                state_sha = require_sha(
                    candidate.get("source_state_sha256"), "source_state_sha256"
                )
                key = (condition, candidate_sha, state_sha)
                current = wrappers.get(key)
                if current is None:
                    wrappers[key] = (dict(obj), [source])
                elif current[0] != dict(obj):
                    raise ValueError(
                        "candidate projector identity maps to non-identical wrappers"
                    )
                else:
                    current[1].append(source)

            if obj.get("schema_id") == "FORMAL_BATCH_UNIT_RESULT_V1":
                custom_id = obj.get("custom_id")
                if isinstance(custom_id, str):
                    _insert_unique(batch, custom_id, obj, source)

            if (
                obj.get("stage_id") == "X"
                and isinstance(obj.get("custom_id"), str)
                and isinstance(obj.get("projection_path"), str)
                and "expected_memory_pack_sha256" in obj
            ):
                _insert_x_registry_representation(
                    registry,
                    registry_representations,
                    str(obj["custom_id"]),
                    obj,
                    source,
                )

    return FormalXIndexesV1(
        candidate_wrappers=wrappers,
        batch_results=batch,
        x_registry_rows=registry,
        x_registry_representations=registry_representations,
        scan_file_count=file_count,
        scan_object_count=object_count,
    )


def _require_batch_result(
    indexes: FormalXIndexesV1,
    custom_id: str,
    *,
    expected_stage: str,
    expected_condition: str,
    expected_group_manifest_sha256: str,
    expected_target_custom_id: str | None = None,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    record = indexes.batch_results.get(custom_id)
    if record is None:
        raise ValueError(f"missing Formal batch result for {custom_id}")
    value, sources = record
    if value.get("status") != "VALIDATED":
        raise ValueError(f"Formal batch result is not VALIDATED: {custom_id}")
    if str(value.get("stage_id")) != expected_stage:
        raise ValueError(f"Formal batch stage mismatch: {custom_id}")
    if normalized_condition(value.get("condition_id")) != expected_condition:
        raise ValueError(f"Formal batch condition mismatch: {custom_id}")
    if require_sha(
        value.get("group_manifest_sha256"), "group_manifest_sha256"
    ) != expected_group_manifest_sha256:
        raise ValueError(f"Formal batch group mismatch: {custom_id}")
    if expected_target_custom_id is not None:
        if value.get("target_custom_id") != expected_target_custom_id:
            raise ValueError(f"Formal X target custom-id mismatch: {custom_id}")
    return value, tuple(sorted(set(sources)))


def _load_validated_artifact(
    batch: Mapping[str, object],
    *,
    allowed_roots: Sequence[Path],
) -> tuple[dict[str, Any], Path]:
    path = resolve_registered_path(
        batch.get("validated_artifact_path"),
        allowed_roots=allowed_roots,
        expected_file_sha256=require_sha(
            batch.get("validated_artifact_file_sha256"),
            "validated_artifact_file_sha256",
        ),
    )
    return load_json_object(path), path


def _validate_group_result(
    value: Mapping[str, object],
    *,
    expected_group_manifest_sha256: str,
    expected_semantic_sha256: str,
) -> str:
    schema = value.get("schema_id")
    if schema not in {"ANALYZER_GROUP_RESULT_V1", "ANALYZER_GROUP_RESULT_V2"}:
        raise ValueError("validated G artifact has wrong schema")
    if require_sha(
        value.get("group_manifest_sha256"), "group_manifest_sha256"
    ) != expected_group_manifest_sha256:
        raise ValueError("validated G artifact group mismatch")
    group_result_sha = require_sha(
        value.get("group_result_sha256"), "group_result_sha256"
    )
    if group_result_sha != require_sha(
        expected_semantic_sha256, "G validated_semantic_sha256"
    ):
        raise ValueError("validated G semantic SHA mismatch")
    return group_result_sha


def validate_crosscheck_result_v1(
    value: Mapping[str, object],
    *,
    expected_target_artifact_sha256: str,
    expected_disposition: str,
    expected_semantic_sha256: str,
) -> dict[str, Any]:
    if set(value) != REGISTERED_X_FIELDS:
        raise ValueError(
            "ANALYZER_CROSSCHECK_RESULT_V1 keyset mismatch: "
            + repr(sorted(set(value) ^ REGISTERED_X_FIELDS))
        )
    if value.get("schema_id") != "ANALYZER_CROSSCHECK_RESULT_V1":
        raise ValueError("validated X artifact has wrong schema")
    if value.get("schema_version") != 1:
        raise ValueError("validated X artifact has wrong schema version")
    disposition = str(value.get("disposition"))
    if disposition not in REGISTERED_X_DISPOSITIONS:
        raise ValueError("unregistered X disposition")
    if disposition != expected_disposition:
        raise ValueError("candidate projector/X disposition mismatch")
    if require_sha(
        value.get("target_artifact_sha256"), "target_artifact_sha256"
    ) != expected_target_artifact_sha256:
        raise ValueError("X target artifact does not equal validated G result")
    crosscheck_sha = require_sha(value.get("crosscheck_sha256"), "crosscheck_sha256")
    if crosscheck_sha != require_sha(
        expected_semantic_sha256, "X validated_semantic_sha256"
    ):
        raise ValueError("validated X semantic SHA mismatch")
    for field in (
        "supporting_evidence_sha256s",
        "contradiction_evidence_sha256s",
        "current_evidence_sha256s",
        "historical_evidence_sha256s",
    ):
        raw = value.get(field)
        if not isinstance(raw, list):
            raise ValueError(f"{field} must be array")
        for item in raw:
            require_sha(item, field)
    residual = value.get("residual_case_ids")
    if not isinstance(residual, list) or not all(
        isinstance(item, str) and item for item in residual
    ):
        raise ValueError("residual_case_ids must be non-empty strings")
    if disposition == "ACCEPT" and not value["current_evidence_sha256s"]:
        raise ValueError("historical-only crosscheck cannot independently ACCEPT")
    expected_hash = domain_hash(
        "ANALYZER_CROSSCHECK_RESULT_V1",
        dict(value),
        excluded_field="crosscheck_sha256",
    )
    if crosscheck_sha != expected_hash:
        raise ValueError("crosscheck domain hash mismatch")
    return dict(value)


def _analyzer_role_packs(value: object) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for _, obj in walk_objects(value):
        if (
            obj.get("schema_id") == "FAILURE_MEMORY_ROLE_PACK_V1"
            and obj.get("role") == "ANALYZER"
        ):
            pack_sha = require_sha(obj.get("pack_sha256"), "pack_sha256")
            previous = found.get(pack_sha)
            if previous is None:
                found[pack_sha] = dict(obj)
            elif previous != dict(obj):
                raise ValueError("same Analyzer Memory pack SHA has different bytes")
    return [found[key] for key in sorted(found)]


def validate_analyzer_memory_binding_v1(
    *,
    condition: str,
    registry_row: Mapping[str, object],
    projection: Mapping[str, object],
) -> dict[str, Any] | None:
    expected = registry_row.get("expected_memory_pack_sha256")
    packs = _analyzer_role_packs(projection)
    if condition == "A2":
        if expected is not None or packs:
            raise ValueError("A2 must contain no Analyzer Memory pack")
        return None
    if condition != "A3":
        raise ValueError("condition must be A2/A3")
    expected_sha = require_sha(expected, "expected_memory_pack_sha256")
    if len(packs) != 1:
        raise ValueError("A3 projection must contain exactly one Analyzer Memory pack")
    pack = packs[0]
    if require_sha(pack.get("pack_sha256"), "pack_sha256") != expected_sha:
        raise ValueError("A3 expected Memory pack SHA mismatch")
    computed = domain_hash(
        "FAILURE_MEMORY_ROLE_PACK_V1",
        pack,
        excluded_field="pack_sha256",
    )
    if computed != expected_sha:
        raise ValueError("Analyzer Memory role-pack domain hash mismatch")
    return pack


def _compact_memory_pack(pack: Mapping[str, object] | None) -> dict[str, object] | None:
    if pack is None:
        return None
    payload = pack.get("payload")
    payload_schema = payload.get("schema_id") if isinstance(payload, dict) else None
    snapshot_shas = sorted(set(_collect_named_shas(payload, "snapshot")))
    candidate_count = 0
    if isinstance(payload, dict):
        for key in ("candidates", "records", "member_views"):
            child = payload.get(key)
            if isinstance(child, list):
                candidate_count += len(child)
    return {
        "schema_id": pack.get("schema_id"),
        "schema_version": pack.get("schema_version"),
        "role": pack.get("role"),
        "cell_id": pack.get("cell_id"),
        "execution_manifest_sha256": pack.get("execution_manifest_sha256"),
        "pack_sha256": pack.get("pack_sha256"),
        "payload_schema_id": payload_schema,
        "snapshot_sha256s": snapshot_shas,
        "top_level_candidate_like_count": candidate_count,
    }


def _collect_named_shas(value: object, token: str) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if token in str(key).lower() and isinstance(child, str):
                try:
                    yield require_sha(child, str(key))
                except ValueError:
                    pass
            yield from _collect_named_shas(child, token)
    elif isinstance(value, list):
        for child in value:
            yield from _collect_named_shas(child, token)


def bind_selected_candidates_to_formal_x_v1(
    *,
    selected_candidates: Sequence[Mapping[str, object]],
    indexes: FormalXIndexesV1,
    allowed_artifact_roots: Sequence[Path],
) -> dict[str, object]:
    candidate_bindings: list[dict[str, object]] = []
    x_unit_candidates: dict[str, list[str]] = defaultdict(list)
    bound_artifacts: dict[str, dict[str, object]] = {}

    for candidate in selected_candidates:
        condition = normalized_condition(candidate.get("condition_id"))
        if condition is None:
            raise ValueError("selected candidate lacks A2/A3 condition")
        candidate_sha = require_sha(candidate.get("candidate_sha256"), "candidate_sha256")
        state_sha = require_sha(candidate.get("source_state_sha256"), "source_state_sha256")
        key = (condition, candidate_sha, state_sha)
        wrapper_record = indexes.candidate_wrappers.get(key)
        if wrapper_record is None:
            raise ValueError("selected candidate lacks exact projector wrapper: " + repr(key))
        wrapper, wrapper_sources = wrapper_record
        if wrapper.get("x_available_and_valid") is not True:
            raise ValueError("selected candidate does not have valid X authority")
        wrapper_candidate = wrapper.get("candidate")
        if not isinstance(wrapper_candidate, dict):
            raise ValueError("projector wrapper candidate is missing")
        if require_sha(
            wrapper_candidate.get("candidate_sha256"), "wrapper candidate SHA"
        ) != candidate_sha:
            raise ValueError("wrapper candidate identity mismatch")
        if wrapper_candidate.get("candidate_status") not in EXECUTABLE_CANDIDATE_STATUSES:
            raise ValueError("selected candidate is not executable")
        proposal_sha = require_sha(
            candidate.get("source_proposal_sha256"), "source_proposal_sha256"
        )
        if require_sha(
            wrapper.get("source_proposal_sha256"), "wrapper source proposal SHA"
        ) != proposal_sha:
            raise ValueError("candidate/wrapper source proposal mismatch")
        group_sha = require_sha(
            wrapper.get("group_manifest_sha256"), "group_manifest_sha256"
        )
        g_custom_id = str(wrapper.get("g_custom_id"))
        x_custom_id = str(wrapper.get("x_custom_id"))
        expected_disposition = str(wrapper.get("x_disposition"))

        g_batch, g_batch_sources = _require_batch_result(
            indexes,
            g_custom_id,
            expected_stage="G-" + condition,
            expected_condition=condition,
            expected_group_manifest_sha256=group_sha,
        )
        g_artifact, g_path = _load_validated_artifact(
            g_batch, allowed_roots=allowed_artifact_roots
        )
        group_result_sha = _validate_group_result(
            g_artifact,
            expected_group_manifest_sha256=group_sha,
            expected_semantic_sha256=str(g_batch["validated_semantic_sha256"]),
        )

        x_batch, x_batch_sources = _require_batch_result(
            indexes,
            x_custom_id,
            expected_stage="X",
            expected_condition=condition,
            expected_group_manifest_sha256=group_sha,
            expected_target_custom_id=g_custom_id,
        )
        x_artifact, x_path = _load_validated_artifact(
            x_batch, allowed_roots=allowed_artifact_roots
        )
        crosscheck = validate_crosscheck_result_v1(
            x_artifact,
            expected_target_artifact_sha256=group_result_sha,
            expected_disposition=expected_disposition,
            expected_semantic_sha256=str(x_batch["validated_semantic_sha256"]),
        )

        registry_record = indexes.x_registry_rows.get(x_custom_id)
        if registry_record is None:
            raise ValueError("missing X registry row: " + x_custom_id)
        registry, registry_sources = registry_record
        if normalized_condition(registry.get("condition_id")) != condition:
            raise ValueError("X registry condition mismatch")
        if registry.get("target_custom_id") != g_custom_id:
            raise ValueError("X registry target custom-id mismatch")
        if require_sha(
            registry.get("group_manifest_sha256"), "X registry group SHA"
        ) != group_sha:
            raise ValueError("X registry group mismatch")
        representation_rows = indexes.x_registry_representations.get(
            x_custom_id, []
        )
        registered_projection_paths = sorted(
            {
                str(rep["projection_path"])
                for rep in representation_rows
                if isinstance(rep.get("projection_path"), str)
                and rep.get("projection_path")
            }
        )
        resolved_projection_candidates: dict[Path, dict[str, Any]] = {}
        projection_resolution_errors: list[str] = []
        for raw_projection_path in registered_projection_paths:
            try:
                resolved = resolve_registered_path(
                    raw_projection_path,
                    allowed_roots=allowed_artifact_roots,
                )
            except ValueError as error:
                projection_resolution_errors.append(
                    raw_projection_path + ": " + str(error)
                )
                continue
            resolved_projection_candidates[resolved] = load_json_object(resolved)

        if not resolved_projection_candidates:
            raise ValueError(
                "no registered X projection representation resolved inside "
                "allowed roots: " + repr(projection_resolution_errors)
            )

        projection_identities = {
            sha256_bytes(canonical_json_bytes(value))
            for value in resolved_projection_candidates.values()
        }
        if len(projection_identities) != 1:
            raise ValueError(
                "compatible X registry descriptions resolve to "
                "non-identical projection artifacts"
            )
        projection_path = sorted(
            resolved_projection_candidates,
            key=lambda value: str(value),
        )[0]
        projection = resolved_projection_candidates[projection_path]
        memory_pack = validate_analyzer_memory_binding_v1(
            condition=condition,
            registry_row=registry,
            projection=projection,
        )

        for artifact in (g_artifact, x_artifact, projection):
            bound_artifacts.setdefault(
                sha256_bytes(canonical_json_bytes(artifact)), artifact
            )
        if memory_pack is not None:
            bound_artifacts.setdefault(str(memory_pack["pack_sha256"]), memory_pack)

        x_unit_candidates[x_custom_id].append(candidate_sha)
        candidate_bindings.append(
            {
                "condition_id": condition,
                "candidate_sha256": candidate_sha,
                "source_state_sha256": state_sha,
                "source_proposal_sha256": proposal_sha,
                "group_manifest_sha256": group_sha,
                "g_custom_id": g_custom_id,
                "x_custom_id": x_custom_id,
                "projector_x_disposition": expected_disposition,
                "group_result_sha256": group_result_sha,
                "group_mechanism_hypotheses": list(
                    g_artifact.get("mechanism_hypotheses", [])
                    if isinstance(g_artifact.get("mechanism_hypotheses"), list)
                    else []
                ),
                "source_conditioned_proposals": [
                    dict(proposal)
                    for proposal in (
                        g_artifact.get("source_conditioned_proposals", [])
                        if isinstance(
                            g_artifact.get("source_conditioned_proposals"), list
                        )
                        else []
                    )
                    if isinstance(proposal, dict)
                    and proposal.get("source_proposal_sha256") == proposal_sha
                ],
                "crosscheck_sha256": crosscheck["crosscheck_sha256"],
                "crosscheck": crosscheck,
                "a3_analyzer_memory_pack_sha256": (
                    memory_pack["pack_sha256"] if memory_pack else None
                ),
                "a3_analyzer_memory_summary": _compact_memory_pack(memory_pack),
                "registered_projection_path": str(projection_path),
                "validated_g_artifact_path": str(g_path),
                "validated_x_artifact_path": str(x_path),
                "wrapper_source_records": sorted(set(wrapper_sources)),
                "g_batch_source_records": list(g_batch_sources),
                "x_batch_source_records": list(x_batch_sources),
                "x_registry_source_records": sorted(set(registry_sources)),
                "x_registry_representation_count": len(
                    indexes.x_registry_representations.get(x_custom_id, [])
                ),
            }
        )

    if len(candidate_bindings) != 60:
        raise ValueError(f"expected 60 candidate/X bindings, got {len(candidate_bindings)}")
    condition_counts = Counter(row["condition_id"] for row in candidate_bindings)
    if condition_counts != Counter({"A2": 30, "A3": 30}):
        raise ValueError("candidate/X condition counts are not A2=30/A3=30")
    a2_memory = sum(
        row["a3_analyzer_memory_pack_sha256"] is not None
        for row in candidate_bindings
        if row["condition_id"] == "A2"
    )
    a3_memory = sum(
        row["a3_analyzer_memory_pack_sha256"] is not None
        for row in candidate_bindings
        if row["condition_id"] == "A3"
    )
    if a2_memory != 0 or a3_memory != 30:
        raise ValueError(
            f"A2/A3 Memory exposure mismatch: A2={a2_memory}, A3={a3_memory}"
        )

    multiplicity = Counter(len(values) for values in x_unit_candidates.values())
    unique_a3_memory_pack_count = len(
        {
            str(row["a3_analyzer_memory_pack_sha256"])
            for row in candidate_bindings
            if row["condition_id"] == "A3"
            and row["a3_analyzer_memory_pack_sha256"] is not None
        }
    )
    result = {
        "schema_id": "FORMAL_X_CROSSCHECK_BINDING_AUTHORITY_V1",
        "schema_version": 1,
        "candidate_binding_count": len(candidate_bindings),
        "condition_counts": dict(sorted(condition_counts.items())),
        "unique_x_scientific_unit_count": len(x_unit_candidates),
        "x_candidate_multiplicity_distribution": {
            str(key): value for key, value in sorted(multiplicity.items())
        },
        "candidate_disposition_counts": dict(
            sorted(Counter(row["projector_x_disposition"] for row in candidate_bindings).items())
        ),
        "a2_candidate_memory_binding_count": a2_memory,
        "a3_candidate_memory_binding_count": a3_memory,
        "unique_a3_analyzer_memory_pack_count": unique_a3_memory_pack_count,
        "x_registry_representation_audit": x_registry_representation_audit_v1(
            indexes
        ),
        "candidate_bindings": sorted(
            candidate_bindings,
            key=lambda row: (
                str(row["source_state_sha256"]),
                str(row["condition_id"]),
                str(row["candidate_sha256"]),
            ),
        ),
        "authority_sha256": "0" * 64,
    }
    result["authority_sha256"] = domain_hash(
        "FORMAL_X_CROSSCHECK_BINDING_AUTHORITY_V1",
        result,
        excluded_field="authority_sha256",
    )
    return {"authority": result, "bound_artifacts": bound_artifacts}
