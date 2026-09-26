"""Fail-closed review of exact π1 identity slots before materialization."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .bundle_reader import validate_attempt_bundle
from .canonical import (
    canonical_json_bytes,
    directory_manifest_sha256,
    domain_hash,
    ensure_directory_no_symlink,
    ensure_regular_no_symlink,
    sha256_file,
    strict_json_loads,
    write_new_json,
    write_new_text,
)


ARTIFACT_SLOTS = (
    "base_model_artifact",
    "adapter_artifact",
    "tokenizer_artifact",
    "chat_template",
    "policy_runtime_manifest",
    "decoding_contract",
    "raw_policy_prompt_protocol",
    "training_config",
    "training_data_manifest",
    "reference_evaluation_manifest",
)

SCALAR_SLOTS = (
    "base_model_id",
    "adapter_id",
    "tokenizer_identity",
    "runtime_core_commit",
    "evaluator_commit",
    "training_seed",
)


def _load_json(path: Path) -> object:
    source = ensure_regular_no_symlink(path, name=path.name)
    return strict_json_loads(source.read_bytes())


def _walk(value: object, *, prefix: str = "$") -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}"
            rows.append((child_prefix, child))
            rows.extend(_walk(child, prefix=child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            rows.append((child_prefix, child))
            rows.extend(_walk(child, prefix=child_prefix))
    return rows


def _is_sha256_text(value: str) -> bool:
    return (
        len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _candidate_id(slot: str, candidate: dict[str, object]) -> str:
    payload = {
        "slot": slot,
        "kind": candidate["kind"],
        "path": candidate.get("path"),
        "sha256": candidate["sha256"],
        "source_authority_path": candidate["source_authority_path"],
        "source_json_path": candidate.get("source_json_path"),
        "manifest_value_field": candidate.get("manifest_value_field"),
        "value": candidate.get("value"),
    }
    return domain_hash("PI1_IDENTITY_SLOT_CANDIDATE_V1", payload)


def _file_candidate(
    *,
    slot: str,
    path: Path,
    source_authority_path: Path,
    source_json_path: str | None,
    reason: str,
) -> dict[str, object]:
    source = ensure_regular_no_symlink(path, name=f"{slot} candidate")
    row = {
        "kind": "FILE",
        "path": str(source),
        "sha256": sha256_file(source),
        "size_bytes": source.stat().st_size,
        "source_authority_path": str(source_authority_path),
        "source_authority_sha256": sha256_file(source_authority_path),
        "source_json_path": source_json_path,
        "reason": reason,
    }
    row["candidate_id"] = _candidate_id(slot, row)
    return row


def _directory_candidate(
    *,
    slot: str,
    path: Path,
    source_authority_path: Path,
    source_json_path: str | None,
    reason: str,
) -> dict[str, object]:
    source = ensure_directory_no_symlink(path, name=f"{slot} candidate")
    row = {
        "kind": "DIRECTORY_MANIFEST",
        "path": str(source),
        "sha256": directory_manifest_sha256(source),
        "size_bytes": None,
        "source_authority_path": str(source_authority_path),
        "source_authority_sha256": sha256_file(source_authority_path),
        "source_json_path": source_json_path,
        "reason": reason,
    }
    row["candidate_id"] = _candidate_id(slot, row)
    return row


def _manifest_value_candidate(
    *,
    slot: str,
    path: Path,
    field_name: str,
    source_authority_path: Path,
    source_json_path: str | None,
    reason: str,
) -> dict[str, object]:
    source = ensure_regular_no_symlink(
        path,
        name=f"{slot} manifest authority",
    )
    payload = _load_json(source)
    if not isinstance(payload, dict):
        raise TypeError(f"{slot} manifest authority must be object")
    value = payload.get(field_name)
    if (
        not isinstance(value, str)
        or not _is_sha256_text(value)
    ):
        raise ValueError(
            f"{slot} manifest field {field_name} is not a SHA-256"
        )
    row = {
        "kind": "MANIFEST_VALUE_SHA256",
        "path": str(source),
        "sha256": value,
        "size_bytes": source.stat().st_size,
        "source_authority_path": str(source_authority_path),
        "source_authority_sha256": sha256_file(source_authority_path),
        "source_json_path": source_json_path,
        "manifest_value_field": field_name,
        "reason": reason,
    }
    row["candidate_id"] = _candidate_id(slot, row)
    return row


def _inline_candidate(
    *,
    slot: str,
    value: str,
    source_authority_path: Path,
    source_json_path: str,
    reason: str,
) -> dict[str, object]:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    row = {
        "kind": "INLINE_TEXT",
        "path": None,
        "sha256": digest,
        "size_bytes": len(value.encode("utf-8")),
        "source_authority_path": str(source_authority_path),
        "source_authority_sha256": sha256_file(source_authority_path),
        "source_json_path": source_json_path,
        "value": value,
        "reason": reason,
    }
    row["candidate_id"] = _candidate_id(slot, row)
    return row


def _dedupe(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for row in rows:
        key = (
            row.get("kind"),
            row.get("path"),
            row.get("sha256"),
            row.get("value"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return sorted(
        result,
        key=lambda item: (
            str(item.get("kind")),
            str(item.get("path")),
            str(item.get("source_authority_path")),
            str(item.get("source_json_path")),
        ),
    )


def _path_candidate_slots(json_path: str) -> tuple[str, ...]:
    key = json_path.lower()
    slots: list[str] = []
    if (
        ("base_model" in key or "model_name_or_path" in key)
        and "adapter" not in key
        and "tokenizer" not in key
    ):
        slots.append("base_model_artifact")
    if "tokenizer" in key:
        slots.append("tokenizer_artifact")
    if "chat_template" in key or "chattemplate" in key:
        slots.append("chat_template")
    if "decoding" in key or "generation_config" in key:
        slots.append("decoding_contract")
    if (
        "raw_policy_prompt" in key
        or "prompt_protocol" in key
        or "raw_protocol" in key
    ):
        slots.append("raw_policy_prompt_protocol")
    if (
        "training_config" in key
        or "execution_spec" in key
        or "train_config" in key
    ):
        slots.append("training_config")
    if (
        "training_data" in key
        or "dataset_manifest" in key
        or "sample_ledger" in key
    ):
        slots.append("training_data_manifest")
    if (
        "reference_evaluation" in key
        or "formal_run_manifest" in key
        or "evaluation_manifest" in key
    ):
        slots.append("reference_evaluation_manifest")
    return tuple(slots)


def _scalar_candidate_slots(json_path: str) -> tuple[str, ...]:
    key = json_path.lower()
    slots: list[str] = []
    if (
        ("base_model_id" in key or "model_id" in key or "model_name" in key)
        and "adapter" not in key
        and "served_model" not in key
    ):
        slots.append("base_model_id")
    if "adapter_id" in key or "lora_name" in key:
        slots.append("adapter_id")
    if (
        "tokenizer_identity" in key
        or "tokenizer_name" in key
        or "tokenizer_id" in key
    ):
        slots.append("tokenizer_identity")
    return tuple(slots)


def _authority_paths_from_census(census: dict[str, object]) -> list[Path]:
    paths: list[Path] = []
    for row in census.get("formal_a_runtime_binding_candidates", []):
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            paths.append(Path(row["path"]))
    for row in census.get("select_runtime_manifest_matches", []):
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            paths.append(Path(row["path"]))
    for row in census.get("frozen_checkpoint_files", []):
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            paths.append(Path(row["path"]))
    return paths


def _scan_authority(
    path: Path,
    artifact_candidates: dict[str, list[dict[str, object]]],
    scalar_candidates: dict[str, set[object]],
) -> None:
    if path.suffix not in {".json", ".jsonl"}:
        return
    if path.suffix == ".jsonl":
        values = []
        for line in path.read_bytes().splitlines():
            if line:
                try:
                    values.append(strict_json_loads(line))
                except Exception:
                    continue
    else:
        try:
            values = [_load_json(path)]
        except Exception:
            return

    for value in values:
        for json_path, child in _walk(value):
            if isinstance(child, str):
                for slot in _scalar_candidate_slots(json_path):
                    if child and "\n" not in child and "\r" not in child:
                        scalar_candidates[slot].add(child)

                for slot in _path_candidate_slots(json_path):
                    candidate_path = Path(child)
                    if candidate_path.is_absolute() and candidate_path.exists():
                        try:
                            if candidate_path.is_dir():
                                row = _directory_candidate(
                                    slot=slot,
                                    path=candidate_path,
                                    source_authority_path=path,
                                    source_json_path=json_path,
                                    reason="ABSOLUTE_PATH_FROM_SEALED_AUTHORITY",
                                )
                            elif candidate_path.is_file():
                                row = _file_candidate(
                                    slot=slot,
                                    path=candidate_path,
                                    source_authority_path=path,
                                    source_json_path=json_path,
                                    reason="ABSOLUTE_PATH_FROM_SEALED_AUTHORITY",
                                )
                            else:
                                continue
                        except ValueError:
                            continue
                        artifact_candidates[slot].append(row)
                    elif (
                        slot == "chat_template"
                        and len(child) >= 16
                        and not _is_sha256_text(child)
                        and "sha256" not in json_path.lower()
                    ):
                        artifact_candidates[slot].append(
                            _inline_candidate(
                                slot=slot,
                                value=child,
                                source_authority_path=path,
                                source_json_path=json_path,
                                reason="INLINE_CHAT_TEMPLATE_FROM_SEALED_AUTHORITY",
                            )
                        )


def _checkpoint_role_candidates(
    census: dict[str, object],
    artifact_candidates: dict[str, list[dict[str, object]]],
) -> None:
    # The checkpoint-set execution spec, training step ledger and formal run
    # manifest are provenance authorities, but they are not the semantic
    # training-config, training-data or reference-evaluation artifacts.
    return

def _adapter_artifact_candidate_from_census(
    census: dict[str, object],
) -> dict[str, object]:
    adapter_dir_value = census.get("seed17_adapter_directory")
    if not isinstance(adapter_dir_value, str):
        raise ValueError("census lacks seed17 adapter directory")
    adapter_dir = ensure_directory_no_symlink(
        Path(adapter_dir_value),
        name="Seed-17 adapter directory",
    )

    adapter_authority = next(
        (
            Path(row["path"])
            for row in census.get("frozen_checkpoint_files", [])
            if isinstance(row, dict)
            and row.get("relative_path")
            == "seed_17/adapter_artifact_manifest.json"
            and isinstance(row.get("path"), str)
        ),
        None,
    )
    if adapter_authority is None:
        raise ValueError("adapter artifact manifest missing from census")

    candidate = _manifest_value_candidate(
        slot="adapter_artifact",
        path=adapter_authority,
        field_name="adapter_bundle_sha256",
        source_authority_path=adapter_authority,
        source_json_path="$.adapter_bundle_sha256",
        reason="FROZEN_ADAPTER_ARTIFACT_MANIFEST_BUNDLE_SHA",
    )

    manifest = _load_json(adapter_authority)
    if not isinstance(manifest, dict):
        raise TypeError("adapter artifact manifest must be object")
    required_files = manifest.get("required_files")
    files = manifest.get("files")
    if not isinstance(required_files, list) or not isinstance(files, dict):
        raise ValueError("adapter artifact manifest file binding is malformed")

    for name in required_files:
        if not isinstance(name, str):
            raise ValueError("adapter required_files must contain strings")
        member = adapter_dir / name
        ensure_regular_no_symlink(
            member,
            name="Seed-17 adapter member " + name,
        )
        metadata = files.get(name)
        if not isinstance(metadata, dict):
            raise ValueError(
                "adapter artifact manifest lacks metadata for " + name
            )
        expected_sha = metadata.get("sha256")
        if not isinstance(expected_sha, str):
            raise ValueError(
                "adapter artifact manifest lacks member SHA for " + name
            )
        if sha256_file(member) != expected_sha:
            raise ValueError(
                "adapter member SHA differs from manifest: " + name
            )

    return candidate


def _historical_training_identity_candidates(
    *,
    training_materialization_root: Path,
    artifact_candidates: dict[str, list[dict[str, object]]],
    scalar_candidates: dict[str, set[object]],
) -> None:
    root = ensure_directory_no_symlink(
        training_materialization_root,
        name="training materialization root",
    )
    final_path = root / "final_materialization_manifest.json"
    model_path = root / "provenance" / "model_artifact_manifest.json"
    chat_path = root / "provenance" / "chat_template.jinja"

    for required in (final_path, model_path, chat_path):
        ensure_regular_no_symlink(required, name=required.name)

    final = _load_json(final_path)
    model = _load_json(model_path)
    if not isinstance(final, dict) or not isinstance(model, dict):
        raise TypeError("training materialization manifests must be objects")

    repository = final.get("base_model_repository")
    revision = final.get("base_model_revision")
    tokenizer_bundle = final.get("tokenizer_bundle_sha256")
    chat_sha = final.get("chat_template_sha256")

    if (
        not isinstance(repository, str)
        or not isinstance(revision, str)
        or not isinstance(tokenizer_bundle, str)
        or not _is_sha256_text(tokenizer_bundle)
        or not isinstance(chat_sha, str)
        or not _is_sha256_text(chat_sha)
    ):
        raise ValueError("training materialization identity fields invalid")

    if model.get("repository_id") != repository:
        raise ValueError("model artifact repository differs from materialization")
    if model.get("snapshot_revision") != revision:
        raise ValueError("model artifact revision differs from materialization")
    if model.get("tokenizer_bundle_sha256") != tokenizer_bundle:
        raise ValueError("tokenizer bundle SHA differs across materialization")
    if sha256_file(chat_path) != chat_sha:
        raise ValueError("chat template file SHA differs from materialization")

    artifact_candidates["base_model_artifact"].append(
        _manifest_value_candidate(
            slot="base_model_artifact",
            path=model_path,
            field_name="weights_bundle_sha256",
            source_authority_path=final_path,
            source_json_path="$.weights_bundle_sha256",
            reason="FROZEN_MODEL_ARTIFACT_MANIFEST_WEIGHTS_BUNDLE_SHA",
        )
    )
    artifact_candidates["tokenizer_artifact"].append(
        _manifest_value_candidate(
            slot="tokenizer_artifact",
            path=model_path,
            field_name="tokenizer_bundle_sha256",
            source_authority_path=final_path,
            source_json_path="$.tokenizer_bundle_sha256",
            reason="FROZEN_MODEL_ARTIFACT_MANIFEST_TOKENIZER_BUNDLE_SHA",
        )
    )
    artifact_candidates["chat_template"].append(
        _file_candidate(
            slot="chat_template",
            path=chat_path,
            source_authority_path=final_path,
            source_json_path="$.chat_template_sha256",
            reason="FROZEN_CHAT_TEMPLATE_FILE_EXACT_SHA",
        )
    )

    scalar_candidates["base_model_id"].add(repository + "@" + revision)
    scalar_candidates["tokenizer_identity"].add(
        repository
        + "@"
        + revision
        + "#tokenizer_bundle_sha256="
        + tokenizer_bundle
    )


def _runtime_adapter_id_candidates(
    *,
    runtime_manifest_path: Path,
    checkpoint_instance_id: str,
    scalar_candidates: dict[str, set[object]],
) -> None:
    value = _load_json(runtime_manifest_path)
    if not isinstance(value, dict):
        raise TypeError("policy runtime manifest must be object")
    for json_path, child in _walk(value):
        if (
            isinstance(child, str)
            and child == checkpoint_instance_id
            and any(
                token in json_path.lower()
                for token in (
                    "checkpoint_instance_id",
                    "policy_condition_id",
                    "served_model_name",
                    "lora",
                    "adapter",
                )
            )
        ):
            scalar_candidates["adapter_id"].add(checkpoint_instance_id)


def _decoding_contract_candidates(
    *,
    formal_a_runtime_binding_path: Path,
    search_roots: tuple[Path, ...],
    artifact_candidates: dict[str, list[dict[str, object]]],
) -> None:
    runtime_path = ensure_regular_no_symlink(
        formal_a_runtime_binding_path,
        name="Formal-A runtime binding",
    )
    runtime = _load_json(runtime_path)
    expected_shas: set[str] = set()
    for json_path, child in _walk(runtime):
        if (
            isinstance(child, str)
            and _is_sha256_text(child)
            and "decoding" in json_path.lower()
            and "sha256" in json_path.lower()
        ):
            expected_shas.add(child)

    if len(expected_shas) != 1:
        return
    expected = next(iter(expected_shas))

    matches: list[Path] = []
    seen: set[Path] = set()
    for root in search_roots:
        if not root.exists():
            continue
        root = ensure_directory_no_symlink(root, name="decoding search root")
        for candidate in root.rglob("*"):
            if candidate.is_symlink() or not candidate.is_file():
                continue
            name = candidate.name.lower()
            if not any(
                token in name
                for token in ("decod", "generation", "runtime", "contract")
            ):
                continue
            try:
                if candidate.stat().st_size > 4 * 1024 * 1024:
                    continue
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if sha256_file(candidate) == expected:
                matches.append(resolved)

    if matches:
        chosen = sorted(
            matches,
            key=lambda item: (
                "/data/run01/" not in str(item),
                str(item),
            ),
        )[0]
        artifact_candidates["decoding_contract"].append(
            _file_candidate(
                slot="decoding_contract",
                path=chosen,
                source_authority_path=runtime_path,
                source_json_path="$.decoding*_sha256",
                reason="EXACT_SHA_MATCH_FROM_FORMAL_A_RUNTIME_BINDING",
            )
        )


def _find_unique_file_by_sha(
    *,
    root: Path,
    expected_sha256: str,
    role_name: str,
) -> Path:
    root = ensure_directory_no_symlink(root, name=role_name + " root")
    matches: list[Path] = []
    for candidate in root.rglob("*"):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        try:
            if candidate.stat().st_size > 16 * 1024 * 1024:
                continue
        except OSError:
            continue
        if sha256_file(candidate) == expected_sha256:
            matches.append(candidate.resolve())
    distinct = sorted(set(matches), key=str)
    if not distinct:
        raise ValueError(
            f"{role_name} exact SHA was not found"
        )
    # Multiple paths with the same expected SHA are byte-identical aliases,
    # not an identity ambiguity. Prefer the shortest deterministic path.
    return sorted(distinct, key=lambda item: (len(str(item)), str(item)))[0]


def _correct_training_and_reference_roles(
    *,
    census: dict[str, object],
    training_config_root: Path,
    training_dataset_manifest_path: Path,
    reference_evaluation_manifest_path: Path,
    artifact_candidates: dict[str, list[dict[str, object]]],
) -> None:
    rows = census.get("frozen_checkpoint_files")
    if not isinstance(rows, list):
        raise TypeError("frozen checkpoint files must be an array")

    seed17_run = next(
        (
            Path(row["path"])
            for row in rows
            if isinstance(row, dict)
            and row.get("relative_path")
            == "seed_17/formal_run_manifest.json"
        ),
        None,
    )
    if seed17_run is None:
        raise ValueError("Seed-17 formal run manifest missing from census")
    run_value = _load_json(seed17_run)
    if not isinstance(run_value, dict):
        raise TypeError("Seed-17 formal run manifest must be object")

    training_config_sha = run_value.get("training_config_sha256")
    dataset_freeze_root_sha = run_value.get("dataset_freeze_root_sha256")
    if (
        not isinstance(training_config_sha, str)
        or not _is_sha256_text(training_config_sha)
        or not isinstance(dataset_freeze_root_sha, str)
        or not _is_sha256_text(dataset_freeze_root_sha)
    ):
        raise ValueError("Seed-17 formal run lacks frozen training identities")

    config_path = _find_unique_file_by_sha(
        root=training_config_root,
        expected_sha256=training_config_sha,
        role_name="training config",
    )
    artifact_candidates["training_config"].append(
        _file_candidate(
            slot="training_config",
            path=config_path,
            source_authority_path=seed17_run,
            source_json_path="$.training_config_sha256",
            reason="EXACT_TRAINING_CONFIG_SHA_FROM_SEED17_FORMAL_RUN",
        )
    )

    dataset_manifest = ensure_regular_no_symlink(
        training_dataset_manifest_path,
        name="training dataset manifest",
    )
    dataset_value = _load_json(dataset_manifest)
    if not isinstance(dataset_value, dict):
        raise TypeError("training dataset manifest must be object")
    if dataset_value.get("dataset_status") != "D_Q2_BAD_V1_FROZEN":
        raise ValueError("training dataset is not frozen D_Q2_BAD_V1")
    package_sha = dataset_manifest.parent / "package_files.sha256"
    if not package_sha.is_file():
        raise ValueError("training dataset package_files.sha256 missing")
    if sha256_file(package_sha) != dataset_freeze_root_sha:
        raise ValueError(
            "training dataset freeze root differs from Seed-17 formal run"
        )
    artifact_candidates["training_data_manifest"].append(
        _file_candidate(
            slot="training_data_manifest",
            path=dataset_manifest,
            source_authority_path=seed17_run,
            source_json_path="$.dataset_freeze_root_sha256",
            reason="FROZEN_D_Q2_BAD_V1_FINAL_DATASET_MANIFEST",
        )
    )

    reference_eval = ensure_regular_no_symlink(
        reference_evaluation_manifest_path,
        name="reference evaluation manifest",
    )
    reference_value = _load_json(reference_eval)
    if not isinstance(reference_value, dict):
        raise TypeError("reference evaluation manifest must be object")
    runtime_rows = census.get("select_runtime_manifest_matches")
    if not isinstance(runtime_rows, list) or len(runtime_rows) != 1:
        raise ValueError("census does not bind one SELECT runtime manifest")
    runtime_sha = runtime_rows[0].get("sha256")
    if reference_value.get("policy_runtime_sha256") != runtime_sha:
        raise ValueError(
            "reference evaluation policy runtime differs from π1 runtime"
        )
    if reference_value.get("condition") not in {
        "r1_train17",
        "P4-R1-Q2-BAD-TRAIN17",
    }:
        raise ValueError("reference evaluation condition is not Train17")
    artifact_candidates["reference_evaluation_manifest"].append(
        _file_candidate(
            slot="reference_evaluation_manifest",
            path=reference_eval,
            source_authority_path=reference_eval,
            source_json_path=None,
            reason="FORMAL_HARNESS_OFF_TRAIN17_REFERENCE_EVALUATION_IDENTITY",
        )
    )


def _repo_sha_matches(repo: Path, expected_sha256s: set[str]) -> dict[str, list[Path]]:
    matches: dict[str, list[Path]] = defaultdict(list)
    if not expected_sha256s:
        return matches
    for base in ("configs", "docs", "scripts", "src"):
        root = repo / base
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                if path.stat().st_size > 8 * 1024 * 1024:
                    continue
                digest = sha256_file(path)
            except OSError:
                continue
            if digest in expected_sha256s:
                matches[digest].append(path.resolve())
    return matches


def build_pi1_identity_slot_review(
    *,
    census_path: Path,
    lineage_bridge_path: Path,
    repository_root: Path,
    training_materialization_root: Path | None = None,
    formal_a_runtime_binding_path: Path | None = None,
    decoding_search_roots: tuple[Path, ...] = (),
    training_config_root: Path | None = None,
    training_dataset_manifest_path: Path | None = None,
    reference_evaluation_manifest_path: Path | None = None,
) -> dict[str, object]:
    census_source = ensure_regular_no_symlink(
        census_path, name="PI1 identity authority census"
    )
    lineage_source = ensure_regular_no_symlink(
        lineage_bridge_path, name="source-collection lineage bridge"
    )
    repo = ensure_directory_no_symlink(
        repository_root, name="repository root"
    )
    census = _load_json(census_source)
    lineage = _load_json(lineage_source)
    if not isinstance(census, dict) or not isinstance(lineage, dict):
        raise TypeError("identity census and lineage bridge must be objects")
    if (
        census.get("readiness_status")
        != "READY_FOR_EXPLICIT_PI1_IDENTITY_REGISTRATION_REVIEW"
    ):
        raise ValueError("π1 identity census is not READY for review")
    if lineage.get("source_bundle_count") != 12:
        raise ValueError("lineage bridge must bind exactly 12 source bundles")

    artifact_candidates: dict[str, list[dict[str, object]]] = {
        slot: [] for slot in ARTIFACT_SLOTS
    }
    scalar_candidates: dict[str, set[object]] = {
        slot: set() for slot in SCALAR_SLOTS
    }

    artifact_candidates["adapter_artifact"].append(
        _adapter_artifact_candidate_from_census(census)
    )

    runtime_matches = census.get("select_runtime_manifest_matches")
    if not isinstance(runtime_matches, list) or len(runtime_matches) != 1:
        raise ValueError("census must contain exactly one SELECT runtime match")
    runtime_path = Path(runtime_matches[0]["path"])
    artifact_candidates["policy_runtime_manifest"].append(
        _file_candidate(
            slot="policy_runtime_manifest",
            path=runtime_path,
            source_authority_path=runtime_path,
            source_json_path=None,
            reason="UNIQUE_SELECT_RUNTIME_SHA_MATCH",
        )
    )

    authority_paths = _authority_paths_from_census(census)
    for authority_path in authority_paths:
        _scan_authority(
            authority_path,
            artifact_candidates,
            scalar_candidates,
        )
    _checkpoint_role_candidates(census, artifact_candidates)

    if training_materialization_root is not None:
        _historical_training_identity_candidates(
            training_materialization_root=training_materialization_root,
            artifact_candidates=artifact_candidates,
            scalar_candidates=scalar_candidates,
        )

    if formal_a_runtime_binding_path is not None:
        _decoding_contract_candidates(
            formal_a_runtime_binding_path=formal_a_runtime_binding_path,
            search_roots=decoding_search_roots,
            artifact_candidates=artifact_candidates,
        )

    if (
        training_config_root is not None
        and training_dataset_manifest_path is not None
        and reference_evaluation_manifest_path is not None
    ):
        _correct_training_and_reference_roles(
            census=census,
            training_config_root=training_config_root,
            training_dataset_manifest_path=training_dataset_manifest_path,
            reference_evaluation_manifest_path=(
                reference_evaluation_manifest_path
            ),
            artifact_candidates=artifact_candidates,
        )

    runtime_rows = census.get("select_runtime_manifest_matches")
    if isinstance(runtime_rows, list) and len(runtime_rows) == 1:
        runtime_path_value = runtime_rows[0].get("path")
        if isinstance(runtime_path_value, str):
            _runtime_adapter_id_candidates(
                runtime_manifest_path=Path(runtime_path_value),
                checkpoint_instance_id=str(census["checkpoint_instance_id"]),
                scalar_candidates=scalar_candidates,
            )

    source_bundle_rows = lineage.get("rows")
    if not isinstance(source_bundle_rows, list):
        raise TypeError("lineage rows must be array")
    raw_protocol_shas: set[str] = set()
    runtime_commits: set[str] = set()
    evaluator_commits: set[str] = set()
    seeds: set[int] = set()
    for row in source_bundle_rows:
        if not isinstance(row, dict):
            continue
        bundle = validate_attempt_bundle(Path(row["source_bundle_path"]))
        raw_protocol = bundle.episode.get("raw_protocol_sha256")
        if isinstance(raw_protocol, str):
            raw_protocol_shas.add(raw_protocol)
        runtime_commit = bundle.episode.get("runtime_core_commit")
        evaluator_commit = bundle.episode.get("evaluator_commit")
        seed = bundle.episode.get("seed")
        if isinstance(runtime_commit, str):
            runtime_commits.add(runtime_commit)
        if isinstance(evaluator_commit, str):
            evaluator_commits.add(evaluator_commit)
        if isinstance(seed, int):
            seeds.add(seed)

    scalar_candidates["runtime_core_commit"].update(runtime_commits)
    scalar_candidates["evaluator_commit"].update(evaluator_commits)
    scalar_candidates["training_seed"].update(seeds)

    repo_matches = _repo_sha_matches(repo, raw_protocol_shas)
    for digest in sorted(raw_protocol_shas):
        for path in repo_matches.get(digest, []):
            artifact_candidates["raw_policy_prompt_protocol"].append(
                _file_candidate(
                    slot="raw_policy_prompt_protocol",
                    path=path,
                    source_authority_path=lineage_source,
                    source_json_path="$.rows[*].source_bundle_path->attempt.raw_protocol_sha256",
                    reason="REPOSITORY_FILE_EXACTLY_MATCHES_SOURCE_EPISODE_RAW_PROTOCOL_SHA",
                )
            )

    # Missing scalar slots remain missing. Do not derive adapter/base/tokenizer
    # labels from checkpoint names or directory names.

    artifact_review = {}
    for slot in ARTIFACT_SLOTS:
        rows = _dedupe(artifact_candidates[slot])
        status = (
            "UNIQUE"
            if len(rows) == 1
            else "MISSING"
            if not rows
            else "AMBIGUOUS"
        )
        artifact_review[slot] = {
            "status": status,
            "candidate_count": len(rows),
            "candidates": rows,
        }

    scalar_review = {}
    for slot in SCALAR_SLOTS:
        values = sorted(
            scalar_candidates[slot],
            key=lambda item: str(item),
        )
        status = (
            "UNIQUE"
            if len(values) == 1
            else "MISSING"
            if not values
            else "AMBIGUOUS"
        )
        scalar_review[slot] = {
            "status": status,
            "candidate_count": len(values),
            "candidates": values,
        }

    all_unique = all(
        item["status"] == "UNIQUE"
        for item in artifact_review.values()
    ) and all(
        item["status"] == "UNIQUE"
        for item in scalar_review.values()
    )

    review = {
        "schema_id": "PI1_IDENTITY_SLOT_REVIEW_V1",
        "schema_version": 1,
        "logical_policy_id": census["logical_policy_id"],
        "checkpoint_instance_id": census["checkpoint_instance_id"],
        "census_path": str(census_source),
        "census_sha256": sha256_file(census_source),
        "lineage_bridge_path": str(lineage_source),
        "lineage_bridge_sha256": lineage["bridge_sha256"],
        "repository_root": str(repo),
        "artifact_slots": artifact_review,
        "scalar_slots": scalar_review,
        "all_required_slots_unique": all_unique,
        "approval_status": "WAITING_FOR_HUMAN_IDENTITY_SLOT_REVIEW",
        "selection_performed": False,
        "identity_materialized": False,
        "review_sha256": "0" * 64,
    }
    review["review_sha256"] = domain_hash(
        "PI1_IDENTITY_SLOT_REVIEW_V1",
        review,
        excluded_field="review_sha256",
    )
    return review


def render_review_text(review: dict[str, object]) -> str:
    lines = [
        "PI1 IDENTITY SLOT REVIEW V1",
        "=" * 78,
        f"logical_policy_id = {review['logical_policy_id']}",
        f"checkpoint_instance_id = {review['checkpoint_instance_id']}",
        f"review_sha256 = {review['review_sha256']}",
        f"all_required_slots_unique = {review['all_required_slots_unique']}",
        "",
        "ARTIFACT SLOTS",
        "-" * 78,
    ]
    for slot, item in review["artifact_slots"].items():
        lines.append(
            f"{slot}: status={item['status']} candidates={item['candidate_count']}"
        )
        for candidate in item["candidates"]:
            lines.append(
                "  - id={candidate_id} kind={kind} sha={sha256}".format(
                    **candidate
                )
            )
            lines.append(f"    path={candidate.get('path')}")
            lines.append(
                f"    source={candidate['source_authority_path']}"
                f" {candidate.get('source_json_path') or ''}"
            )
            lines.append(f"    reason={candidate['reason']}")
    lines.extend(["", "SCALAR SLOTS", "-" * 78])
    for slot, item in review["scalar_slots"].items():
        lines.append(
            f"{slot}: status={item['status']} candidates={item['candidate_count']}"
        )
        for candidate in item["candidates"]:
            lines.append(f"  - {candidate}")
    lines.extend(
        [
            "",
            "HUMAN GATE",
            "-" * 78,
            "No PI1_REFERENCE_IDENTITY_V1 has been created.",
            "No trajectory rebinding or Analyzer Evidence Pack has been materialized.",
            "The next phase requires an approval artifact bound to this review_sha256.",
            "",
        ]
    )
    return "\n".join(lines)


def build_review_files(
    *,
    census_path: Path,
    lineage_bridge_path: Path,
    repository_root: Path,
    output_json: Path,
    output_text: Path,
    training_materialization_root: Path | None = None,
    formal_a_runtime_binding_path: Path | None = None,
    decoding_search_roots: tuple[Path, ...] = (),
    training_config_root: Path | None = None,
    training_dataset_manifest_path: Path | None = None,
    reference_evaluation_manifest_path: Path | None = None,
) -> dict[str, object]:
    review = build_pi1_identity_slot_review(
        census_path=census_path,
        lineage_bridge_path=lineage_bridge_path,
        repository_root=repository_root,
        training_materialization_root=training_materialization_root,
        formal_a_runtime_binding_path=formal_a_runtime_binding_path,
        decoding_search_roots=decoding_search_roots,
        training_config_root=training_config_root,
        training_dataset_manifest_path=training_dataset_manifest_path,
        reference_evaluation_manifest_path=(
            reference_evaluation_manifest_path
        ),
    )
    write_new_json(output_json, review)
    write_new_text(output_text, render_review_text(review))
    return review
