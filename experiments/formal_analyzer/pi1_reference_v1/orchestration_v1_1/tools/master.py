#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping

EXPECTED_HEAD = "0529efa4b4c896f3855a4634c7daa3a3559e3a89"
EXPECTED_POLICY_VERSION = "P4-R1-Q2-BAD-TRAIN17"
EXPECTED_POLICY_CONDITION_SHA256 = "457f4f58cd6733f863fa690e45c962f3fda3b2cf511d9961eb715b7a52c07e0b"
EXPECTED_POLICY_RUNTIME_SHA256 = "215bbe3981668181c8b2eb51c4568af944512f7c20c4504ad75faa012cc83faa"
EXPECTED_POLICY_CHECKPOINT_SHA256 = "2d232e19acb99e6ba026cf92ebcb94d8c785aec52f327261d2b872aa3c8ebd8c"
EXPECTED_PI1_IDENTITY_REVIEW_SHA256 = "9017612ab3bd5c37517037c25d5a1427718ab1fb7bbee66024de2b18343f880c"

DEFAULT_REPO = Path(
    "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
    "pchsi-wt-formal-act3-canonical-pack-hardening-v1"
)
DEFAULT_LOCAL_REGISTRY = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "formal_analyzer_selected42_evidence_a0a1_preparation_v1/"
    "_run_state/formal_selected42_prepared/main/"
    "runtime_registry_formal_main_a0a1.json"
)
DEFAULT_MAIN_IMPORT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "formal_batch_transport_v2_round_continuation_v1/"
    "_run_state/main_batch_import"
)
DEFAULT_POSTMAIN_FREEZE = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "formal_postlocal_group_x_human_researcher_bridge_v1/"
    "_run_state/FORMAL_MAIN_POSTLOCAL_INPUT_FREEZE_V1.json"
)
DEFAULT_CLOSURE = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "formal_act3_registration_hardening_and_source_materialization_v1/"
    "_run_state/corrected_source_closure"
)
DEFAULT_MEMORY_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "formal_main_a3_group_memory_semantics_restore_v1_results/"
    "fixed_0944e3c5a172f3b30431d142a4b53a9c113bd0a1f9a473c35a38bcfbad16e057"
)
DEFAULT_A2A3_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "formal_main_a2a3_offline_materialization_v1"
)
DEFAULT_STATE_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "formal_analyzer_to_human_researcher_pre_boundary_v1_1_state"
)
DEFAULT_PI1_ADAPTER_ROOT = Path(
    "/data/run01/scwb204/pchsi/p2/"
    "p4_r1_q2_bad_checkpoint_set_v1_frozen/seed_17/adapter"
)
DEFAULT_PI1_REVIEW = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "reference_loop_pi1_identity_review_v1/"
    "fixed_42c676b2f17698b9837064283310f7fcec347fe2/"
    "PI1_IDENTITY_SLOT_REVIEW_V1.json"
)

PAIR_RE = re.compile(r"^FORMAL_PI1_MAIN_L_A([01])_(.+)$")
TERMINAL_BATCH = frozenset({"completed", "failed", "expired", "cancelled"})


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require_object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be object")
    return value


def require_array(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be array")
    return value


def ensure_bytes(path: Path, raw: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"existing path is not regular file: {path}")
        if path.read_bytes() != raw:
            raise ValueError(f"existing file bytes differ: {path}")
        return False
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("write made no progress")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def ensure_json(path: Path, value: Mapping[str, object]) -> bool:
    return ensure_bytes(path, canonical_json_bytes(dict(value)))


def ensure_jsonl(path: Path, rows: list[Mapping[str, object]]) -> bool:
    raw = b"".join(canonical_json_bytes(dict(row)) for row in rows)
    return ensure_bytes(path, raw)


def read_jsonl_with_raw(path: Path) -> list[tuple[bytes, dict[str, Any]]]:
    out = []
    with path.open("rb") as f:
        for raw in f:
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row must be object: {path}")
            out.append((raw, value))
    return out


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def pair_suffix(source_unit_id: str) -> tuple[str, str]:
    match = PAIR_RE.match(source_unit_id)
    if match is None:
        raise ValueError(f"unexpected Main local source_unit_id: {source_unit_id}")
    return match.group(1), match.group(2)


def paired_local_id(suffix: str) -> str:
    return f"FORMAL_PI1_MAIN_LOCAL_{suffix}"


def validate_analyzer_member_access(
    api: object,
    access: Mapping[str, object],
    membership: Mapping[str, object],
    *,
    group_manifest_sha256: str,
    local_result_sha256: str,
) -> None:
    # The repository's authoritative live-call gate is
    # teacher_call_permitted=True. confirmatory_permitted is a data-use
    # classification field, not an Analyzer teacher-call authorization bit.
    api.validate_task_access(access, live_call=True)
    if access.get("task_id") != membership.get("task_id"):
        raise SystemExit(
            f"STOP=GROUP_MEMBER_TASK_ACCESS_TASK_DRIFT:"
            f"{group_manifest_sha256}:{local_result_sha256}"
        )
    if access.get("gamefile_sha256") != membership.get("gamefile_sha256"):
        raise SystemExit(
            f"STOP=GROUP_MEMBER_TASK_ACCESS_GAMEFILE_DRIFT:"
            f"{group_manifest_sha256}:{local_result_sha256}"
        )


def execution_semantics(candidate: Mapping[str, object]) -> tuple[object, ...] | None:
    status = candidate.get("candidate_status")
    state = candidate.get("source_state_sha256")
    if status == "EXECUTABLE_EXACT_ACTION":
        return (state, "EXACT", candidate.get("exact_action"))
    if status == "EXECUTABLE_SHORT_OPTION":
        options = candidate.get("option_actions")
        if not isinstance(options, list):
            return None
        return (
            state,
            "OPTION",
            tuple(options),
            candidate.get("termination_condition"),
        )
    return None


def model_dump(value: object) -> dict[str, object]:
    fn = getattr(value, "model_dump", None)
    if callable(fn):
        return dict(fn(mode="json"))
    if isinstance(value, dict):
        return dict(value)
    result = {}
    for name in (
        "id",
        "status",
        "input_file_id",
        "output_file_id",
        "error_file_id",
        "created_at",
        "completed_at",
        "expires_at",
        "request_counts",
        "errors",
    ):
        if hasattr(value, name):
            child = getattr(value, name)
            dump = getattr(child, "model_dump", None)
            result[name] = dump(mode="json") if callable(dump) else child
    return result


def file_content_bytes(client: object, file_id: str) -> bytes:
    content = client.files.content(file_id)
    read = getattr(content, "read", None)
    if callable(read):
        raw = read()
        if isinstance(raw, str):
            return raw.encode("utf-8")
        return bytes(raw)
    raw_content = getattr(content, "content", None)
    if isinstance(raw_content, bytes):
        return raw_content
    text = getattr(content, "text", None)
    if callable(text):
        text = text()
    if isinstance(text, str):
        return text.encode("utf-8")
    raise RuntimeError("unable to read OpenAI file content")


class RepoAPI:
    def __init__(self, repo: Path):
        sys.path.insert(0, str(repo / "src"))
        from pchsi.reference_loop.canonical import (  # type: ignore
            canonical_json_bytes as repo_canonical_json_bytes,
            directory_manifest_sha256,
            domain_hash,
        )
        from pchsi.cognitive_runtime.access import validate_task_access  # type: ignore
        from pchsi.cognitive_runtime.formal_registry_v2 import validate_formal_dag_v2  # type: ignore
        from pchsi.cognitive_runtime.identity import build_scientific_unit_identity  # type: ignore
        from pchsi.cognitive_runtime.projections import crosscheck_projection_v2  # type: ignore
        from pchsi.cognitive_runtime.request_renderer import render_stage_request  # type: ignore
        from pchsi.cognitive_runtime.output_validation import validate_stage_output  # type: ignore
        from pchsi.cognitive_runtime.response import (  # type: ignore
            ProviderResponseError,
            extract_output_text,
            parse_provider_response,
            usage_summary,
        )
        from pchsi.cognitive_runtime.schema_registry import validate_artifact  # type: ignore
        from pchsi.cognitive_runtime.round_evidence import freeze_round_evidence_package  # type: ignore
        from pchsi.analyzer.candidate_projector import project_candidate  # type: ignore

        self.canonical_json_bytes = repo_canonical_json_bytes
        self.directory_manifest_sha256 = directory_manifest_sha256
        self.domain_hash = domain_hash
        self.validate_task_access = validate_task_access
        self.validate_formal_dag_v2 = validate_formal_dag_v2
        self.build_scientific_unit_identity = build_scientific_unit_identity
        self.crosscheck_projection_v2 = crosscheck_projection_v2
        self.render_stage_request = render_stage_request
        self.validate_stage_output = validate_stage_output
        self.ProviderResponseError = ProviderResponseError
        self.extract_output_text = extract_output_text
        self.parse_provider_response = parse_provider_response
        self.usage_summary = usage_summary
        self.validate_artifact = validate_artifact
        self.freeze_round_evidence_package = freeze_round_evidence_package
        self.project_candidate = project_candidate


class Config:
    def __init__(self, args: argparse.Namespace):
        self.repo = Path(args.repo).resolve()
        self.local_registry = Path(args.local_registry).resolve()
        self.main_import = Path(args.main_import).resolve()
        self.postmain_freeze = Path(args.postmain_freeze).resolve()
        self.closure = Path(args.closure).resolve()
        self.memory_root = Path(args.memory_root).resolve()
        self.a2a3_root = Path(args.a2a3_root).resolve()
        self.state_root = Path(args.state_root).resolve()
        self.pi1_adapter_root = Path(args.pi1_adapter_root).resolve()
        self.pi1_review = Path(args.pi1_review).resolve()
        self.round_id = args.round_id
        self.poll_seconds = args.poll_seconds


def support_artifact(
    api: RepoAPI,
    *,
    schema_id: str,
    hash_field: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    out = {
        "schema_id": schema_id,
        "schema_version": 1,
        **dict(payload),
        hash_field: "0" * 64,
    }
    out[hash_field] = api.domain_hash(
        schema_id,
        out,
        excluded_field=hash_field,
    )
    return out


def verify_repo(cfg: Config) -> RepoAPI:
    if not cfg.repo.is_dir():
        raise SystemExit(f"STOP=REPO_MISSING:{cfg.repo}")
    head = git(cfg.repo, "rev-parse", "HEAD")
    print(f"REPO_HEAD={head}")
    if head != EXPECTED_HEAD:
        raise SystemExit("STOP=FORMAL_REPO_HEAD_CHANGED")
    status = git(
        cfg.repo,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status:
        raise SystemExit("STOP=FORMAL_REPO_NOT_CLEAN")
    return RepoAPI(cfg.repo)


def resolve_local_authorities(
    cfg: Config,
    api: RepoAPI,
) -> dict[str, object]:
    registry = require_object(load_json(cfg.local_registry), "local registry")
    api.validate_artifact("RUNTIME_INPUT_REGISTRY_V1", registry)
    units = require_array(registry.get("units"), "local registry units")
    if len(units) != 60:
        raise SystemExit(f"STOP=LOCAL_REGISTRY_UNIT_COUNT:{len(units)}")

    normalized_path = cfg.main_import / "normalized_execution_manifest.json"
    normalized = require_object(load_json(normalized_path), "normalized manifest")
    rows = require_array(normalized.get("rows"), "normalized rows")
    if len(rows) != 60:
        raise SystemExit("STOP=MAIN_NORMALIZED_ROW_COUNT_NOT_60")
    if Counter(str(r.get("status")) for r in rows) != Counter({"ACCEPTED": 60}):
        raise SystemExit("STOP=MAIN_LOCAL_NOT_ALL_ACCEPTED")

    outcome_by_source = {}
    for row in rows:
        source = str(row.get("source_unit_id"))
        if source in outcome_by_source:
            raise SystemExit(f"STOP=DUPLICATE_NORMALIZED_SOURCE:{source}")
        outcome_by_source[source] = row

    registry_base = cfg.local_registry.parent
    pairs: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    local_source_records: dict[str, dict[str, object]] = {}

    for raw_unit in units:
        unit = require_object(raw_unit, "local registry unit")
        source = str(unit.get("source_unit_id"))
        arm, suffix = pair_suffix(source)
        if arm in pairs[suffix]:
            raise SystemExit(f"STOP=DUPLICATE_LOCAL_ARM:{suffix}:{arm}")
        if source not in outcome_by_source:
            raise SystemExit(f"STOP=LOCAL_REGISTRY_NOT_IN_NORMALIZED:{source}")

        def relative_file(key: str) -> Path:
            raw = unit.get(key)
            if not isinstance(raw, str) or not raw:
                raise SystemExit(f"STOP=LOCAL_UNIT_PATH:{source}:{key}")
            path = (registry_base / raw).resolve()
            if not path.is_file() or path.is_symlink():
                raise SystemExit(f"STOP=LOCAL_UNIT_FILE_INVALID:{path}")
            return path

        ident_path = relative_file("scientific_unit_identity_path")
        proj_path = relative_file("input_projection_path")
        access_path = relative_file("task_access_record_path")
        ident = require_object(load_json(ident_path), "scientific identity")
        projection = require_object(load_json(proj_path), "local projection")
        access = require_object(load_json(access_path), "task access")
        api.validate_artifact("SCIENTIFIC_UNIT_IDENTITY_V1", ident)
        api.validate_task_access(access, live_call=True)

        row = outcome_by_source[source]
        validated_path = Path(str(row["result_root"])).resolve() / "validated_artifact.json"
        if not validated_path.is_file() or validated_path.is_symlink():
            raise SystemExit(f"STOP=LOCAL_VALIDATED_ARTIFACT_MISSING:{validated_path}")
        validated = require_object(load_json(validated_path), "local validated artifact")

        record = {
            "source_unit_id": source,
            "stage_id": unit.get("stage_id"),
            "condition_id": unit.get("condition_id"),
            "unit": unit,
            "identity": ident,
            "identity_path": str(ident_path),
            "projection": projection,
            "projection_path": str(proj_path),
            "task_access": access,
            "task_access_path": str(access_path),
            "task_access_file_sha256": sha256_file(access_path),
            "normalized_row": row,
            "validated_artifact": validated,
            "validated_artifact_path": str(validated_path),
        }
        pairs[suffix][arm] = record
        local_source_records[source] = record

    if len(pairs) != 30 or any(set(v) != {"0", "1"} for v in pairs.values()):
        raise SystemExit("STOP=LOCAL_A0_A1_PAIRING_INVALID")

    pair_rows = []
    local_condition_rows = []
    a1_local_sha_to_pair = {}
    task_set_values = set()

    for suffix in sorted(pairs):
        a0 = pairs[suffix]["0"]
        a1 = pairs[suffix]["1"]
        pair_id = paired_local_id(suffix)

        for field in ("task_id", "gamefile_sha256", "task_set_manifest_sha256"):
            if a0["identity"].get(field) != a1["identity"].get(field):
                raise SystemExit(f"STOP=A0_A1_IDENTITY_DRIFT:{suffix}:{field}")

        task_set = a1["identity"].get("task_set_manifest_sha256")
        if not isinstance(task_set, str) or len(task_set) != 64:
            raise SystemExit(f"STOP=TASK_SET_IDENTITY_INVALID:{suffix}")
        task_set_values.add(task_set)

        a0_evidence = a0["projection"].get("evidence_pack_sha256")
        a1_evidence = a1["projection"].get("evidence_pack_sha256")
        if a0_evidence != a1_evidence or not isinstance(a0_evidence, str):
            raise SystemExit(f"STOP=A0_A1_COMMON_EVIDENCE_DRIFT:{suffix}")
        if a0["projection"].get("memory_pack_sha256") is not None:
            raise SystemExit(f"STOP=A0_MEMORY_EXPOSURE:{suffix}")
        if a1["projection"].get("memory_pack_sha256") is not None:
            raise SystemExit(f"STOP=A1_MEMORY_EXPOSURE:{suffix}")

        local_sha = a1["validated_artifact"].get("local_result_sha256")
        if not isinstance(local_sha, str) or len(local_sha) != 64:
            raise SystemExit(f"STOP=A1_LOCAL_RESULT_ID_INVALID:{suffix}")
        if local_sha in a1_local_sha_to_pair:
            raise SystemExit(f"STOP=DUPLICATE_A1_LOCAL_RESULT:{local_sha}")
        a1_local_sha_to_pair[local_sha] = {
            "pair_id": pair_id,
            "suffix": suffix,
            "a1_source_unit_id": a1["source_unit_id"],
            "a1_identity": a1["identity"],
            "a1_access": a1["task_access"],
            "a1_access_path": a1["task_access_path"],
            "a1_access_file_sha256": a1["task_access_file_sha256"],
        }

        pair_rows.append(
            {
                "paired_local_unit_id": pair_id,
                "original_a0_source_unit_id": a0["source_unit_id"],
                "original_a1_source_unit_id": a1["source_unit_id"],
                "a0_scientific_unit_identity_sha256": a0["identity"]["identity_sha256"],
                "a1_scientific_unit_identity_sha256": a1["identity"]["identity_sha256"],
                "task_id": a1["identity"].get("task_id"),
                "gamefile_sha256": a1["identity"].get("gamefile_sha256"),
                "task_set_manifest_sha256": task_set,
                "common_evidence_pack_sha256": a0_evidence,
                "a1_local_result_sha256": local_sha,
            }
        )

        local_condition_rows.extend(
            [
                {
                    "source_unit_id": pair_id,
                    "condition_id": "A0",
                    "common_evidence_pack_sha256": a0_evidence,
                    "a1_local_result_sha256": None,
                    "memory_pack_sha256": None,
                    "candidate_budget": 1,
                    "abstain_permitted": True,
                },
                {
                    "source_unit_id": pair_id,
                    "condition_id": "A1",
                    "common_evidence_pack_sha256": a0_evidence,
                    "a1_local_result_sha256": local_sha,
                    "memory_pack_sha256": None,
                    "candidate_budget": 1,
                    "abstain_permitted": True,
                },
            ]
        )

    if len(task_set_values) != 1:
        raise SystemExit("STOP=LOCAL_TASK_SET_MANIFEST_NOT_COMMON")
    if len(a1_local_sha_to_pair) != 30:
        raise SystemExit("STOP=A1_LOCAL_SHA_PAIR_MAP_NOT_30")

    return {
        "registry": registry,
        "normalized": normalized,
        "normalized_path": str(normalized_path),
        "pairs": pairs,
        "pair_rows": pair_rows,
        "local_condition_rows": local_condition_rows,
        "registered_local_unit_ids": sorted(row["paired_local_unit_id"] for row in pair_rows),
        "a1_local_sha_to_pair": a1_local_sha_to_pair,
        "task_set_manifest_sha256": next(iter(task_set_values)),
    }


def stage_offline(cfg: Config, api: RepoAPI) -> dict[str, object]:
    offline = cfg.state_root / "01_offline_registry_dag"
    dag_path = offline / "FORMAL_ANALYZER_DAG_REGISTRY_V2.json"
    group_registry_path = offline / "group_registry_bundle" / "runtime_registry_formal_main_a2a3.json"

    local = resolve_local_authorities(cfg, api)

    group_file = cfg.closure / "ANALYZER_SOURCE_CLOSED_GROUPS_V1.json"
    groups_obj = require_object(load_json(group_file), "source-closed groups")
    groups = require_array(groups_obj.get("groups"), "source-closed group rows")
    if len(groups) != 30:
        raise SystemExit("STOP=FORMAL_GROUP_COUNT_NOT_30")

    a2_dir = cfg.a2a3_root / "a2_projections"
    a3_dir = cfg.a2a3_root / "a3_projections"
    if len(list(a2_dir.glob("*.json"))) != 30 or len(list(a3_dir.glob("*.json"))) != 30:
        raise SystemExit("STOP=A2A3_PROJECTION_FILE_COUNT")

    registry_root = group_registry_path.parent
    registry_root.mkdir(parents=True, exist_ok=True)
    witness_root = registry_root / "task_access_witnesses"
    identity_root = registry_root / "scientific_identities"
    projection_root = registry_root / "projections"
    witness_root.mkdir(exist_ok=True)
    identity_root.mkdir(exist_ok=True)
    projection_root.mkdir(exist_ok=True)

    group_condition_rows = []
    registry_units = []
    witness_rows = []
    group_manifest_shas = []
    task_set_sha = str(local["task_set_manifest_sha256"])

    for index, group in enumerate(sorted(groups, key=lambda x: str(x["group_manifest_sha256"]))):
        gsha = str(group["group_manifest_sha256"])
        group_manifest_shas.append(gsha)
        members = require_array(group.get("membership_records"), f"group members {gsha}")
        member_bindings = []
        access_members = []

        for membership in members:
            membership = require_object(membership, "group membership")
            local_sha = str(membership["local_result_sha256"])
            bind = local["a1_local_sha_to_pair"].get(local_sha)
            if not isinstance(bind, dict):
                raise SystemExit(f"STOP=GROUP_MEMBER_A1_PAIR_MISSING:{gsha}:{local_sha}")
            access = require_object(bind["a1_access"], "member task access")
            validate_analyzer_member_access(
                api,
                access,
                membership,
                group_manifest_sha256=gsha,
                local_result_sha256=local_sha,
            )

            member_bindings.append(
                {
                    "source_unit_id": bind["pair_id"],
                    "a1_local_result_sha256": local_sha,
                    "error_instance_id": membership["error_instance_id"],
                }
            )
            access_members.append(
                {
                    "paired_local_unit_id": bind["pair_id"],
                    "original_a1_source_unit_id": bind["a1_source_unit_id"],
                    "local_result_sha256": local_sha,
                    "error_instance_id": membership["error_instance_id"],
                    "task_id": membership["task_id"],
                    "gamefile_sha256": membership["gamefile_sha256"],
                    "task_access_file_sha256": bind["a1_access_file_sha256"],
                    "access_class": access.get("access_class"),
                    "dataset_split": access.get("dataset_split"),
                    "teacher_call_permitted": access.get("teacher_call_permitted"),
                    "training_permitted": access.get("training_permitted"),
                    "select_evaluation_permitted": access.get("select_evaluation_permitted"),
                    "confirmatory_permitted": access.get("confirmatory_permitted"),
                    "task_access_record": access,
                }
            )

        witness = support_artifact(
            api,
            schema_id="GROUP_MEMBERWISE_TASK_ACCESS_WITNESS_V1",
            hash_field="witness_sha256",
            payload={
                "group_manifest_sha256": gsha,
                "member_count": len(access_members),
                "analyzer_live_authorization_field": "teacher_call_permitted",
                "all_members_teacher_call_permitted": True,
                "confirmatory_permission_required_for_analyzer_live": False,
                "confirmatory_permission_values": sorted(
                    {bool(row["confirmatory_permitted"]) for row in access_members}
                ),
                "access_classes": sorted(
                    {str(row["access_class"]) for row in access_members}
                ),
                "members": access_members,
            },
        )
        witness_path = witness_root / f"{gsha}.json"
        ensure_json(witness_path, witness)
        witness_rows.append(
            {
                "group_manifest_sha256": gsha,
                "witness_sha256": witness["witness_sha256"],
                "witness_path": str(witness_path),
            }
        )

        identity = api.build_scientific_unit_identity(
            scientific_unit_type="GROUP",
            scientific_unit_id=f"FORMAL_PI1_MAIN_GROUP_{gsha[:24]}",
            source_unit_manifest_sha256=gsha,
            task_set_manifest_sha256=task_set_sha,
            task_id=None,
            gamefile_sha256=None,
            group_manifest_sha256=gsha,
            round_evidence_package_sha256=None,
        )
        identity_path = identity_root / f"{gsha}.json"
        ensure_json(identity_path, identity)

        a2_path = a2_dir / f"{gsha}.json"
        a3_path = a3_dir / f"{gsha}.json"
        a2 = require_object(load_json(a2_path), "A2 projection")
        a3 = require_object(load_json(a3_path), "A3 projection")
        for field in (
            "group_id",
            "group_manifest_sha256",
            "a1_local_result_sha256s",
            "current_evidence_sha256s",
        ):
            if a2.get(field) != a3.get(field):
                raise SystemExit(f"STOP=A2_A3_DRIFT:{gsha}:{field}")
        if a2.get("memory_pack_sha256") is not None:
            raise SystemExit(f"STOP=A2_MEMORY_EXPOSURE:{gsha}")
        if not isinstance(a3.get("memory_pack_sha256"), str):
            raise SystemExit(f"STOP=A3_MEMORY_MISSING:{gsha}")

        expected_a1 = sorted({row["a1_local_result_sha256"] for row in member_bindings})
        if a2.get("a1_local_result_sha256s") != expected_a1:
            raise SystemExit(f"STOP=GROUP_MEMBER_A1_SET_DRIFT:{gsha}")

        for stage, condition, projection, source_path in (
            ("G-A2", "A2", a2, a2_path),
            ("G-A3", "A3", a3, a3_path),
        ):
            safe_stage = stage.replace("-", "_")
            unit_name = f"{index:02d}_{safe_stage}_{gsha[:16]}"
            copied_projection = projection_root / f"{unit_name}.json"
            ensure_json(copied_projection, projection)

            registry_units.append(
                {
                    "source_unit_id": unit_name,
                    "scientific_unit_identity_path": os.path.relpath(identity_path, registry_root),
                    "stage_id": stage,
                    "condition_id": condition,
                    "input_projection_path": os.path.relpath(copied_projection, registry_root),
                    "task_access_record_path": os.path.relpath(witness_path, registry_root),
                    "expected_common_evidence_sha256": None,
                    "expected_a1_local_result_sha256": None,
                    "expected_memory_pack_sha256": projection.get("memory_pack_sha256"),
                }
            )

            group_condition_rows.append(
                {
                    "group_id": projection["group_id"],
                    "group_manifest_sha256": gsha,
                    "condition_id": condition,
                    "member_bindings": member_bindings,
                    "a1_local_result_sha256s": projection["a1_local_result_sha256s"],
                    "current_evidence_sha256s": projection["current_evidence_sha256s"],
                    "memory_pack_sha256": projection.get("memory_pack_sha256"),
                    "candidate_budget": 1,
                    "abstain_permitted": True,
                }
            )

    access_manifest = support_artifact(
        api,
        schema_id="GROUP_TASK_ACCESS_WITNESS_MANIFEST_V1",
        hash_field="task_access_manifest_sha256",
        payload={"group_count": 30, "rows": witness_rows},
    )
    ensure_json(registry_root / "GROUP_TASK_ACCESS_WITNESS_MANIFEST_V1.json", access_manifest)

    group_registry = {
        "schema_id": "RUNTIME_INPUT_REGISTRY_V1",
        "schema_version": 1,
        "registry_role": "FORMAL_A0_A3",
        "round_id": cfg.round_id,
        "policy_version": EXPECTED_POLICY_VERSION,
        "task_access_manifest_sha256": access_manifest["task_access_manifest_sha256"],
        "units": registry_units,
        "registry_sha256": "0" * 64,
    }
    group_registry["registry_sha256"] = api.domain_hash(
        "RUNTIME_INPUT_REGISTRY_V1",
        group_registry,
        excluded_field="registry_sha256",
    )
    api.validate_artifact("RUNTIME_INPUT_REGISTRY_V1", group_registry)
    ensure_json(group_registry_path, group_registry)

    universe = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_PAIRED_LOCAL_UNIVERSE_V1",
        hash_field="registered_universe_sha256",
        payload={
            "local_runtime_registry_sha256": local["registry"]["registry_sha256"],
            "registered_local_unit_ids": local["registered_local_unit_ids"],
            "pair_rows": local["pair_rows"],
        },
    )
    ensure_json(offline / "FORMAL_ANALYZER_PAIRED_LOCAL_UNIVERSE_V1.json", universe)

    local_pair_binding = support_artifact(
        api,
        schema_id="FORMAL_MAIN_LOCAL_PAIR_BINDINGS_V1",
        hash_field="binding_manifest_sha256",
        payload={"pair_count": 30, "rows": local["pair_rows"]},
    )
    ensure_json(offline / "FORMAL_MAIN_LOCAL_PAIR_BINDINGS_V1.json", local_pair_binding)

    dag = {
        "schema_id": "FORMAL_ANALYZER_DAG_REGISTRY_V2",
        "schema_version": 2,
        "round_id": cfg.round_id,
        "registered_universe_sha256": universe["registered_universe_sha256"],
        "registered_local_unit_ids": local["registered_local_unit_ids"],
        "local_condition_rows": local["local_condition_rows"],
        "registered_group_manifest_sha256s": sorted(group_manifest_shas),
        "group_condition_rows": group_condition_rows,
        "local_runtime_input_registry_sha256": local["registry"]["registry_sha256"],
        "group_runtime_input_registry_sha256": group_registry["registry_sha256"],
        "formal_dag_sha256": "0" * 64,
    }
    dag["formal_dag_sha256"] = api.domain_hash(
        "FORMAL_ANALYZER_DAG_REGISTRY_V2",
        dag,
        excluded_field="formal_dag_sha256",
    )
    api.validate_formal_dag_v2(dag)
    ensure_json(dag_path, dag)

    summary = support_artifact(
        api,
        schema_id="FORMAL_MAIN_GROUP_REGISTRY_DAG_V2_AUDIT_V1",
        hash_field="audit_sha256",
        payload={
            "registered_local_unit_count": 30,
            "local_condition_row_count": 60,
            "registered_group_count": 30,
            "group_condition_row_count": 60,
            "multi_source_group_runtime_representation": "MEMBERWISE_TEACHER_ACCESS_WITNESS_PLUS_GROUP_IDENTITY",
            "confirmatory_permission_used_as_analyzer_live_gate": False,
            "fake_single_task_group_identity_used": False,
            "formal_dag_sha256": dag["formal_dag_sha256"],
            "group_registry_sha256": group_registry["registry_sha256"],
            "provider_call_performed": False,
            "environment_call_performed": False,
        },
    )
    ensure_json(offline / "FORMAL_MAIN_GROUP_REGISTRY_DAG_V2_AUDIT_V1.json", summary)
    print("FORMAL_MAIN_GROUP_RUNTIME_REGISTRY_AND_DAG_V2_PASS")
    print("REGISTERED_LOCAL_UNIT_COUNT=30")
    print("GROUP_RUNTIME_UNIT_COUNT=60")
    print("FORMAL_DAG_V2_SHA256=" + str(dag["formal_dag_sha256"]))
    return {
        "local": local,
        "group_registry": group_registry,
        "group_registry_path": str(group_registry_path),
        "dag": dag,
        "dag_path": str(dag_path),
        "offline": str(offline),
    }


def build_batch_input_from_registry(
    cfg: Config,
    api: RepoAPI,
    *,
    registry_path: Path,
    batch_dir: Path,
    label: str,
) -> tuple[Path, dict[str, dict[str, object]]]:
    registry = require_object(load_json(registry_path), "runtime registry")
    api.validate_artifact("RUNTIME_INPUT_REGISTRY_V1", registry)
    base = registry_path.parent
    rows = []
    metadata = {}
    for unit in require_array(registry["units"], "registry units"):
        unit = require_object(unit, "registry unit")
        custom_id = str(unit["source_unit_id"])
        if custom_id in metadata:
            raise SystemExit(f"STOP=DUPLICATE_BATCH_CUSTOM_ID:{custom_id}")
        projection_path = (base / str(unit["input_projection_path"])).resolve()
        projection = require_object(load_json(projection_path), "registry projection")
        rendered = api.render_stage_request(stage_id=str(unit["stage_id"]), projection=projection)

        # Re-bind to the already-frozen offline render for G.
        if str(unit["stage_id"]) in {"G-A2", "G-A3"}:
            gsha = str(projection["group_manifest_sha256"])
            frozen = cfg.a2a3_root / "rendered_requests" / gsha / f"{unit['stage_id']}.json"
            frozen_bundle = require_object(load_json(frozen), "frozen rendered request")
            if rendered["request_body_sha256"] != frozen_bundle["request_body_sha256"]:
                raise SystemExit(f"STOP=G_REQUEST_RENDER_DRIFT:{custom_id}")
            if api.canonical_json_bytes(rendered["provider_request"]) != api.canonical_json_bytes(
                frozen_bundle["provider_request"]
            ):
                raise SystemExit(f"STOP=G_REQUEST_BODY_BYTES_DRIFT:{custom_id}")

        line = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/responses",
            "body": rendered["provider_request"],
        }
        rows.append(line)
        metadata[custom_id] = {
            "custom_id": custom_id,
            "stage_id": unit["stage_id"],
            "condition_id": unit.get("condition_id"),
            "projection_path": str(projection_path),
            "input_projection_sha256": rendered["input_projection_sha256"],
            "request_body_sha256": rendered["request_body_sha256"],
            "expected_memory_pack_sha256": unit.get("expected_memory_pack_sha256"),
            "scientific_unit_identity_path": str(
                (base / str(unit["scientific_unit_identity_path"])).resolve()
            ),
            "task_access_witness_path": str(
                (base / str(unit["task_access_record_path"])).resolve()
            ),
        }

    batch_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = batch_dir / f"{label}_batch_input.jsonl"
    ensure_jsonl(jsonl_path, rows)
    manifest = support_artifact(
        api,
        schema_id="FORMAL_BATCH_INPUT_MANIFEST_V1",
        hash_field="batch_input_manifest_sha256",
        payload={
            "label": label,
            "request_count": len(rows),
            "input_jsonl_sha256": sha256_file(jsonl_path),
            "rows": [metadata[key] for key in sorted(metadata)],
            "provider_call_performed": False,
        },
    )
    ensure_json(batch_dir / f"{label}_BATCH_INPUT_MANIFEST_V1.json", manifest)
    return jsonl_path, metadata


def make_openai_client():
    try:
        from openai import OpenAI
    except Exception as error:
        raise SystemExit(f"STOP=OPENAI_SDK_IMPORT:{error}") from error
    return OpenAI(max_retries=0)


def ensure_live_authorized() -> None:
    if os.environ.get("PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE") != "YES":
        raise SystemExit(
            "STOP=LIVE_NOT_AUTHORIZED: set PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE=YES "
            "for the formal G/X Batch calls"
        )
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("STOP=OPENAI_API_KEY_NOT_LOADED")


def ensure_batch_terminal(
    *,
    client: object,
    batch_dir: Path,
    jsonl_path: Path,
    label: str,
    poll_seconds: int,
    recovery_env: str,
) -> dict[str, object]:
    receipt_path = batch_dir / "batch_receipt.json"
    intent_path = batch_dir / "submission_intent.json"

    if receipt_path.is_file():
        receipt = require_object(load_json(receipt_path), "batch receipt")
        batch_id = str(receipt["batch_id"])
    else:
        ensure_live_authorized()
        upload_receipt_path = batch_dir / "upload_receipt.json"
        if upload_receipt_path.is_file():
            upload = require_object(load_json(upload_receipt_path), "upload receipt")
            input_file_id = str(upload["input_file_id"])
        else:
            try:
                with jsonl_path.open("rb") as handle:
                    uploaded = client.files.create(file=handle, purpose="batch")
            except Exception as error:
                raise SystemExit(f"STOP={label}_INPUT_UPLOAD_FAILED:{type(error).__name__}:{error}")
            input_file_id = str(uploaded.id)
            ensure_json(
                upload_receipt_path,
                {
                    "schema_id": "FORMAL_BATCH_UPLOAD_RECEIPT_V1",
                    "label": label,
                    "input_jsonl_sha256": sha256_file(jsonl_path),
                    "input_file_id": input_file_id,
                },
            )

        intent = {
            "schema_id": "FORMAL_BATCH_SUBMISSION_INTENT_V1",
            "label": label,
            "input_jsonl_sha256": sha256_file(jsonl_path),
            "input_file_id": input_file_id,
            "endpoint": "/v1/responses",
            "completion_window": "24h",
        }
        intent_created = ensure_json(intent_path, intent)

        if not intent_created:
            recovery_id = os.environ.get(recovery_env)
            if not recovery_id:
                raise SystemExit(
                    f"STOP={label}_SUBMISSION_INTENT_WITHOUT_RECEIPT:"
                    f"do not resubmit; set {recovery_env}=<existing_batch_id> only if "
                    "you have independently recovered the exact Batch ID"
                )
            batch = client.batches.retrieve(recovery_id)
            recovered = model_dump(batch)
            if str(recovered.get("input_file_id")) != input_file_id:
                raise SystemExit(f"STOP={label}_RECOVERED_BATCH_INPUT_FILE_MISMATCH")
            batch_id = str(recovered["id"])
        else:
            try:
                batch = client.batches.create(
                    input_file_id=input_file_id,
                    endpoint="/v1/responses",
                    completion_window="24h",
                )
            except Exception as error:
                ensure_bytes(
                    batch_dir / "SUBMISSION_AMBIGUOUS.txt",
                    (
                        f"{type(error).__name__}: {error}\n"
                        "No automatic resubmission is permitted.\n"
                    ).encode("utf-8"),
                )
                raise SystemExit(
                    f"STOP={label}_BATCH_SUBMISSION_AMBIGUOUS:"
                    "submission intent is frozen; do not retry automatically"
                )
            recovered = model_dump(batch)
            batch_id = str(recovered["id"])

        ensure_json(
            receipt_path,
            {
                "schema_id": "FORMAL_BATCH_SUBMISSION_RECEIPT_V1",
                "label": label,
                "batch_id": batch_id,
                "input_file_id": input_file_id,
                "input_jsonl_sha256": sha256_file(jsonl_path),
            },
        )

    while True:
        try:
            batch = client.batches.retrieve(batch_id)
            state = model_dump(batch)
        except Exception as error:
            print(
                f"{label}_BATCH_STATUS_RETRIEVE_RETRY="
                f"{type(error).__name__}:{error}",
                flush=True,
            )
            time.sleep(poll_seconds)
            continue

        status = str(state.get("status"))
        counts = state.get("request_counts")
        print(
            f"{label}_BATCH_ID={batch_id} STATUS={status} REQUEST_COUNTS={counts}",
            flush=True,
        )
        if status in TERMINAL_BATCH:
            ensure_json(
                batch_dir / "batch_terminal_receipt.json",
                {
                    "schema_id": "FORMAL_BATCH_TERMINAL_RECEIPT_V1",
                    "label": label,
                    "batch": state,
                },
            )
            return state
        time.sleep(poll_seconds)


def download_batch_files(
    *,
    client: object,
    batch_dir: Path,
    terminal: Mapping[str, object],
) -> tuple[Path | None, Path | None]:
    output_path = batch_dir / "batch_output.jsonl"
    error_path = batch_dir / "batch_error.jsonl"

    output_id = terminal.get("output_file_id")
    error_id = terminal.get("error_file_id")

    if isinstance(output_id, str) and output_id:
        raw = file_content_bytes(client, output_id)
        ensure_bytes(output_path, raw)
    if isinstance(error_id, str) and error_id:
        raw = file_content_bytes(client, error_id)
        ensure_bytes(error_path, raw)

    return (
        output_path if output_path.is_file() else None,
        error_path if error_path.is_file() else None,
    )


def import_batch_results(
    cfg: Config,
    api: RepoAPI,
    *,
    batch_dir: Path,
    metadata: Mapping[str, Mapping[str, object]],
    label: str,
) -> dict[str, object]:
    import_manifest_path = batch_dir / "IMPORT_MANIFEST_V1.json"
    if import_manifest_path.is_file():
        return require_object(load_json(import_manifest_path), "batch import manifest")

    terminal = require_object(load_json(batch_dir / "batch_terminal_receipt.json"), "terminal")[
        "batch"
    ]
    terminal = require_object(terminal, "terminal batch object")

    output_path = batch_dir / "batch_output.jsonl"
    error_path = batch_dir / "batch_error.jsonl"
    output_rows = {}
    error_rows = {}

    if output_path.is_file():
        for raw, row in read_jsonl_with_raw(output_path):
            custom = row.get("custom_id")
            if not isinstance(custom, str):
                raise SystemExit(f"STOP={label}_OUTPUT_CUSTOM_ID_MISSING")
            if custom in output_rows:
                raise SystemExit(f"STOP={label}_DUPLICATE_OUTPUT_CUSTOM_ID:{custom}")
            output_rows[custom] = (raw, row)

    if error_path.is_file():
        for raw, row in read_jsonl_with_raw(error_path):
            custom = row.get("custom_id")
            if not isinstance(custom, str):
                continue
            if custom in error_rows:
                raise SystemExit(f"STOP={label}_DUPLICATE_ERROR_CUSTOM_ID:{custom}")
            error_rows[custom] = (raw, row)

    unexpected = (set(output_rows) | set(error_rows)) - set(metadata)
    if unexpected:
        raise SystemExit(f"STOP={label}_UNEXPECTED_CUSTOM_IDS:{sorted(unexpected)}")

    result_root = batch_dir / "imported_results"
    result_root.mkdir(parents=True, exist_ok=True)
    rows = []

    for custom_id in sorted(metadata):
        meta = dict(metadata[custom_id])
        unit_root = result_root / custom_id
        unit_root.mkdir(exist_ok=True)
        status = None
        failure_class = None
        validated_path = None
        validated_semantic_sha = None
        validated_artifact_file_sha256 = None
        batch_output_row_sha256 = None
        provider_response_body_sha256 = None
        usage = None
        provider_response_id = None

        if custom_id in output_rows:
            raw_line, batch_row = output_rows[custom_id]
            batch_output_row_sha256 = sha256_bytes(raw_line)
            ensure_bytes(unit_root / "batch_output_row.jsonl", raw_line)
            response = batch_row.get("response")
            if not isinstance(response, dict):
                status = "BATCH_OUTPUT_RESPONSE_MALFORMED"
            else:
                status_code = response.get("status_code")
                body = response.get("body")
                if status_code != 200 or not isinstance(body, dict):
                    status = "BATCH_REQUEST_ERROR"
                    failure_class = f"HTTP_{status_code}"
                else:
                    body_raw = api.canonical_json_bytes(body)
                    body_sha = sha256_bytes(body_raw)
                    provider_response_body_sha256 = body_sha
                    ensure_bytes(unit_root / "provider_response_body.json", body_raw)
                    try:
                        parsed = api.parse_provider_response(body_raw)
                        provider_response_id = parsed.get("id")
                        output_text = api.extract_output_text(parsed)
                        projection = require_object(
                            load_json(Path(str(meta["projection_path"]))),
                            "input projection",
                        )
                        validated = api.validate_stage_output(
                            stage_id=str(meta["stage_id"]),
                            text=output_text,
                            raw_response_sha256=body_sha,
                            projection=projection,
                        )
                        validated_path = unit_root / "validated_artifact.json"
                        ensure_json(validated_path, validated)
                        validated_artifact_file_sha256 = sha256_file(validated_path)
                        for key in (
                            "group_result_sha256",
                            "crosscheck_sha256",
                            "component_attribution_sha256",
                            "local_result_sha256",
                        ):
                            if isinstance(validated.get(key), str):
                                validated_semantic_sha = validated[key]
                                break
                        usage = api.usage_summary(parsed)
                        status = "VALIDATED"
                    except api.ProviderResponseError as error:
                        status = error.logical_method_status
                        failure_class = error.failure_class
                    except Exception as error:
                        status = "VALIDATION_FAILED"
                        failure_class = f"{type(error).__name__}:{error}"

        elif custom_id in error_rows:
            raw_line, row = error_rows[custom_id]
            ensure_bytes(unit_root / "batch_error_row.jsonl", raw_line)
            status = "BATCH_ERROR_FILE"
            failure_class = json.dumps(row.get("error"), ensure_ascii=False, sort_keys=True)
        else:
            status = "BATCH_TERMINAL_MISSING_OUTPUT"
            failure_class = f"BATCH_STATUS_{terminal.get('status')}"

        result_status = {
            "schema_id": "FORMAL_BATCH_UNIT_RESULT_V1",
            "custom_id": custom_id,
            "stage_id": meta["stage_id"],
            "condition_id": meta.get("condition_id"),
            "status": status,
            "failure_class": failure_class,
            "validated_artifact_path": None if validated_path is None else str(validated_path),
            "validated_semantic_sha256": validated_semantic_sha,
            "validated_artifact_file_sha256": validated_artifact_file_sha256,
            "batch_output_row_sha256": batch_output_row_sha256,
            "provider_response_body_sha256": provider_response_body_sha256,
            "provider_response_id": provider_response_id,
            "usage": usage,
            "group_manifest_sha256": meta.get("group_manifest_sha256"),
            "target_custom_id": meta.get("target_custom_id"),
        }
        ensure_json(unit_root / "result_status.json", result_status)
        rows.append(result_status)

    manifest = support_artifact(
        api,
        schema_id="FORMAL_BATCH_IMPORT_MANIFEST_V1",
        hash_field="import_manifest_sha256",
        payload={
            "label": label,
            "batch_status": terminal.get("status"),
            "expected_request_count": len(metadata),
            "output_row_count": len(output_rows),
            "error_row_count": len(error_rows),
            "status_counts": dict(sorted(Counter(str(r["status"]) for r in rows).items())),
            "rows": rows,
            "automatic_scientific_retry_performed": False,
        },
    )
    ensure_json(import_manifest_path, manifest)
    return manifest


def run_g_batch(cfg: Config, api: RepoAPI, offline: Mapping[str, object]) -> dict[str, object]:
    batch_dir = cfg.state_root / "02_formal_g_batch"
    jsonl_path, metadata = build_batch_input_from_registry(
        cfg,
        api,
        registry_path=Path(str(offline["group_registry_path"])),
        batch_dir=batch_dir,
        label="FORMAL_G_A2_A3",
    )
    for custom, meta in metadata.items():
        projection = require_object(load_json(Path(str(meta["projection_path"]))), "G projection")
        meta["group_manifest_sha256"] = projection["group_manifest_sha256"]

    client = make_openai_client()
    terminal = ensure_batch_terminal(
        client=client,
        batch_dir=batch_dir,
        jsonl_path=jsonl_path,
        label="FORMAL_G_A2_A3",
        poll_seconds=cfg.poll_seconds,
        recovery_env="PCHSI_RECOVER_G_BATCH_ID",
    )
    download_batch_files(client=client, batch_dir=batch_dir, terminal=terminal)
    imported = import_batch_results(
        cfg,
        api,
        batch_dir=batch_dir,
        metadata=metadata,
        label="FORMAL_G_A2_A3",
    )
    print("FORMAL_G_A2_A3_BATCH_IMPORT_COMPLETE")
    print("FORMAL_G_STATUS_COUNTS=" + json.dumps(imported["status_counts"], sort_keys=True))
    return {
        "batch_dir": str(batch_dir),
        "input_jsonl": str(jsonl_path),
        "metadata": metadata,
        "import_manifest": imported,
        "import_manifest_path": str(batch_dir / "IMPORT_MANIFEST_V1.json"),
    }


def prepare_x_registry(
    cfg: Config,
    api: RepoAPI,
    g: Mapping[str, object],
    offline: Mapping[str, object],
) -> tuple[Path, dict[str, dict[str, object]]]:
    x_root = cfg.state_root / "03_formal_x_batch"
    registry_root = x_root / "registry_bundle"
    registry_path = registry_root / "runtime_registry_formal_main_x.json"
    if registry_path.is_file():
        registry = require_object(load_json(registry_path), "X registry")
        base = registry_path.parent
        binding_manifest = require_object(
            load_json(x_root / "X_TARGET_BINDING_MANIFEST_V1.json"),
            "X target binding manifest",
        )
        frozen_meta = {
            str(row["custom_id"]): require_object(row, "X binding row")
            for row in require_array(binding_manifest["rows"], "X binding rows")
        }
        metadata = {}
        for unit_raw in require_array(registry["units"], "X units"):
            unit = require_object(unit_raw, "X unit")
            custom = str(unit["source_unit_id"])
            projection_path = (base / str(unit["input_projection_path"])).resolve()
            if custom not in frozen_meta:
                raise SystemExit(f"STOP=X_RESUME_BINDING_MISSING:{custom}")
            row = dict(frozen_meta[custom])
            row.update(
                {
                    "custom_id": custom,
                    "stage_id": "X",
                    "condition_id": unit.get("condition_id"),
                    "projection_path": str(projection_path),
                    "expected_memory_pack_sha256": unit.get(
                        "expected_memory_pack_sha256"
                    ),
                    "scientific_unit_identity_path": str(
                        (base / str(unit["scientific_unit_identity_path"])).resolve()
                    ),
                    "task_access_witness_path": str(
                        (base / str(unit["task_access_record_path"])).resolve()
                    ),
                }
            )
            metadata[custom] = row
        return registry_path, metadata

    registry_root.mkdir(parents=True, exist_ok=True)
    identity_root = registry_root / "scientific_identities"
    projection_root = registry_root / "projections"
    witness_root = Path(str(offline["group_registry_path"])).parent / "task_access_witnesses"
    identity_root.mkdir(exist_ok=True)
    projection_root.mkdir(exist_ok=True)

    g_rows = require_array(g["import_manifest"]["rows"], "G import rows")
    group_registry = require_object(load_json(Path(str(offline["group_registry_path"]))), "G registry")
    group_unit_by_custom = {
        str(u["source_unit_id"]): require_object(u, "G registry unit")
        for u in require_array(group_registry["units"], "G registry units")
    }
    task_set_sha = str(offline["local"]["task_set_manifest_sha256"])

    units = []
    metadata = {}
    x_count = 0

    for g_row_raw in g_rows:
        g_row = require_object(g_row_raw, "G result row")
        if g_row.get("status") != "VALIDATED":
            continue
        target_custom = str(g_row["custom_id"])
        g_meta = require_object(g["metadata"][target_custom], "G metadata")
        target_stage = str(g_meta["stage_id"])
        condition = str(g_meta["condition_id"])
        projection = require_object(load_json(Path(str(g_meta["projection_path"]))), "G projection")
        gsha = str(projection["group_manifest_sha256"])
        target_path = Path(str(g_row["validated_artifact_path"]))
        common_a2 = cfg.a2a3_root / "a2_projections" / f"{gsha}.json"
        group_manifest = cfg.a2a3_root / "group_manifests" / f"{gsha}.json"
        memory_path = (
            None
            if target_stage == "G-A2"
            else cfg.memory_root / "memory_packs" / f"{gsha}.json"
        )

        x_projection = api.crosscheck_projection_v2(
            target_path=target_path,
            target_stage_id=target_stage,
            group_manifest_path=group_manifest,
            common_group_projection_path=common_a2,
            memory_pack_path=memory_path,
        )
        # Internal provenance field must not enter provider projection.
        custom = f"X_{condition}_{x_count:02d}_{gsha[:12]}"
        x_count += 1
        projection_path = projection_root / f"{custom}.json"
        ensure_json(projection_path, x_projection)

        identity = api.build_scientific_unit_identity(
            scientific_unit_type="CROSSCHECK_TARGET",
            scientific_unit_id=f"FORMAL_PI1_MAIN_X_{condition}_{gsha[:20]}",
            source_unit_manifest_sha256=gsha,
            task_set_manifest_sha256=task_set_sha,
            task_id=None,
            gamefile_sha256=None,
            group_manifest_sha256=gsha,
            round_evidence_package_sha256=None,
        )
        identity_path = identity_root / f"{custom}.json"
        ensure_json(identity_path, identity)
        witness_path = witness_root / f"{gsha}.json"
        witness = require_object(load_json(witness_path), "X access witness")
        for member in require_array(witness["members"], "X access members"):
            api.validate_task_access(
                require_object(member["task_access_record"], "X member access"),
                live_call=True,
            )

        rendered = api.render_stage_request(stage_id="X", projection=x_projection)
        metadata[custom] = {
            "custom_id": custom,
            "stage_id": "X",
            "condition_id": condition,
            "projection_path": str(projection_path),
            "expected_memory_pack_sha256": x_projection.get("memory_pack_sha256"),
            "scientific_unit_identity_path": str(identity_path),
            "task_access_witness_path": str(witness_path),
            "target_custom_id": target_custom,
            "group_manifest_sha256": gsha,
            "request_body_sha256": rendered["request_body_sha256"],
        }
        units.append(
            {
                "source_unit_id": custom,
                "scientific_unit_identity_path": os.path.relpath(identity_path, registry_root),
                "stage_id": "X",
                "condition_id": condition,
                "input_projection_path": os.path.relpath(projection_path, registry_root),
                "task_access_record_path": os.path.relpath(witness_path, registry_root),
                "expected_common_evidence_sha256": None,
                "expected_a1_local_result_sha256": None,
                "expected_memory_pack_sha256": x_projection.get("memory_pack_sha256"),
            }
        )

    witness_manifest = require_object(
        load_json(Path(str(offline["group_registry_path"])).parent / "GROUP_TASK_ACCESS_WITNESS_MANIFEST_V1.json"),
        "group witness manifest",
    )
    registry = {
        "schema_id": "RUNTIME_INPUT_REGISTRY_V1",
        "schema_version": 1,
        "registry_role": "FORMAL_A0_A3",
        "round_id": cfg.round_id,
        "policy_version": EXPECTED_POLICY_VERSION,
        "task_access_manifest_sha256": witness_manifest["task_access_manifest_sha256"],
        "units": units,
        "registry_sha256": "0" * 64,
    }
    registry["registry_sha256"] = api.domain_hash(
        "RUNTIME_INPUT_REGISTRY_V1",
        registry,
        excluded_field="registry_sha256",
    )
    if units:
        api.validate_artifact("RUNTIME_INPUT_REGISTRY_V1", registry)
    ensure_json(registry_path, registry)
    ensure_json(
        x_root / "X_TARGET_BINDING_MANIFEST_V1.json",
        support_artifact(
            api,
            schema_id="X_TARGET_BINDING_MANIFEST_V1",
            hash_field="binding_manifest_sha256",
            payload={
                "eligible_validated_g_target_count": len(units),
                "rows": [metadata[k] for k in sorted(metadata)],
                "g_targets_without_validated_artifact": 60 - len(units),
            },
        ),
    )
    return registry_path, metadata


def run_x_batch(
    cfg: Config,
    api: RepoAPI,
    g: Mapping[str, object],
    offline: Mapping[str, object],
) -> dict[str, object]:
    batch_dir = cfg.state_root / "03_formal_x_batch"
    registry_path, x_meta = prepare_x_registry(cfg, api, g, offline)
    if not x_meta:
        empty = support_artifact(
            api,
            schema_id="FORMAL_BATCH_IMPORT_MANIFEST_V1",
            hash_field="import_manifest_sha256",
            payload={
                "label": "FORMAL_X",
                "batch_status": "NOT_RUN_NO_VALID_G_TARGETS",
                "expected_request_count": 0,
                "output_row_count": 0,
                "error_row_count": 0,
                "status_counts": {},
                "rows": [],
                "automatic_scientific_retry_performed": False,
            },
        )
        ensure_json(batch_dir / "IMPORT_MANIFEST_V1.json", empty)
        return {
            "batch_dir": str(batch_dir),
            "metadata": {},
            "import_manifest": empty,
            "import_manifest_path": str(batch_dir / "IMPORT_MANIFEST_V1.json"),
        }

    jsonl_path, generated_meta = build_batch_input_from_registry(
        cfg,
        api,
        registry_path=registry_path,
        batch_dir=batch_dir,
        label="FORMAL_X",
    )
    # Restore target/group metadata not carried by the generic registry fields.
    for custom in generated_meta:
        generated_meta[custom].update(
            {
                "target_custom_id": x_meta[custom]["target_custom_id"],
                "group_manifest_sha256": x_meta[custom]["group_manifest_sha256"],
            }
        )

    client = make_openai_client()
    terminal = ensure_batch_terminal(
        client=client,
        batch_dir=batch_dir,
        jsonl_path=jsonl_path,
        label="FORMAL_X",
        poll_seconds=cfg.poll_seconds,
        recovery_env="PCHSI_RECOVER_X_BATCH_ID",
    )
    download_batch_files(client=client, batch_dir=batch_dir, terminal=terminal)
    imported = import_batch_results(
        cfg,
        api,
        batch_dir=batch_dir,
        metadata=generated_meta,
        label="FORMAL_X",
    )
    print("FORMAL_X_BATCH_IMPORT_COMPLETE")
    print("FORMAL_X_STATUS_COUNTS=" + json.dumps(imported["status_counts"], sort_keys=True))
    return {
        "batch_dir": str(batch_dir),
        "metadata": generated_meta,
        "import_manifest": imported,
        "import_manifest_path": str(batch_dir / "IMPORT_MANIFEST_V1.json"),
    }


def stage_candidates(
    cfg: Config,
    api: RepoAPI,
    g: Mapping[str, object],
    x: Mapping[str, object],
) -> dict[str, object]:
    out_root = cfg.state_root / "04_candidate_projector"
    ledger_path = out_root / "FORMAL_ANALYZER_CANDIDATE_POOL_V1.json"
    if ledger_path.is_file():
        return require_object(load_json(ledger_path), "candidate pool")

    out_root.mkdir(parents=True, exist_ok=True)
    g_rows = {
        str(r["custom_id"]): require_object(r, "G result row")
        for r in require_array(g["import_manifest"]["rows"], "G rows")
    }
    x_rows = {
        str(r["custom_id"]): require_object(r, "X result row")
        for r in require_array(x["import_manifest"]["rows"], "X rows")
    }
    x_meta = x.get("metadata", {})
    x_custom_by_target = {
        str(meta["target_custom_id"]): custom
        for custom, meta in x_meta.items()
        if isinstance(meta, Mapping) and meta.get("target_custom_id")
    }

    state_by_sha = {}
    for path in sorted((cfg.a2a3_root / "a2_projections").glob("*.json")):
        projection = require_object(load_json(path), "A2 projection")
        for context_raw in require_array(projection["source_contexts"], "source contexts"):
            context = require_object(context_raw, "source context")
            state_sha = str(context["source_state_sha256"])
            existing = state_by_sha.get(state_sha)
            if existing is None:
                state_by_sha[state_sha] = context
            else:
                for field in ("menu_sha256", "admissible_commands"):
                    if existing.get(field) != context.get(field):
                        raise SystemExit(f"STOP=SOURCE_STATE_CONTEXT_DRIFT:{state_sha}:{field}")

    if len(state_by_sha) != 30:
        raise SystemExit(f"STOP=FORMAL_SOURCE_STATE_COUNT_NOT_30:{len(state_by_sha)}")

    projected_rows = []
    by_condition_state: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    x_dispositions = Counter()

    for custom_id, g_row in sorted(g_rows.items()):
        meta = require_object(g["metadata"][custom_id], "G metadata")
        condition = str(meta["condition_id"])
        if g_row.get("status") != "VALIDATED":
            continue
        g_artifact = require_object(
            load_json(Path(str(g_row["validated_artifact_path"]))),
            "G validated artifact",
        )
        x_custom = x_custom_by_target.get(custom_id)
        x_row = x_rows.get(x_custom) if x_custom is not None else None
        x_valid = isinstance(x_row, dict) and x_row.get("status") == "VALIDATED"
        disposition = None
        if x_valid:
            x_artifact = require_object(
                load_json(Path(str(x_row["validated_artifact_path"]))),
                "X validated artifact",
            )
            disposition = str(x_artifact["disposition"])
            x_dispositions[disposition] += 1

        repairs = require_array(g_artifact.get("source_conditioned_proposals"), "G source proposals")
        for proposal_index, proposal_raw in enumerate(repairs):
            proposal = require_object(proposal_raw, "source proposal")
            state_sha = str(proposal.get("source_state_sha256"))
            state = state_by_sha.get(state_sha)
            base = {
                "g_custom_id": custom_id,
                "x_custom_id": x_custom,
                "group_manifest_sha256": meta.get("group_manifest_sha256"),
                "condition_id": condition,
                "proposal_index": proposal_index,
                "source_state_sha256": state_sha,
                "source_proposal_sha256": proposal.get("source_proposal_sha256"),
                "x_available_and_valid": bool(x_valid),
                "x_disposition": disposition,
            }
            if state is None:
                base["projection_status"] = "SOURCE_STATE_NOT_IN_FORMAL_UNIVERSE"
                projected_rows.append(base)
                continue
            if not x_valid:
                base["projection_status"] = "X_UNAVAILABLE_OR_INVALID"
                projected_rows.append(base)
                continue
            candidate = api.project_candidate(
                proposal,
                state,
                candidate_kind="FAILURE_REPAIR",
                crosscheck_disposition=str(disposition),
            )
            base["projection_status"] = "PROJECTED"
            base["candidate"] = candidate
            projected_rows.append(base)
            semantics = execution_semantics(candidate)
            if semantics is not None:
                by_condition_state[(condition, state_sha)].append(
                    {
                        "candidate": candidate,
                        "execution_semantics": list(semantics),
                        "group_manifest_sha256": meta.get("group_manifest_sha256"),
                        "source_proposal_sha256": proposal.get("source_proposal_sha256"),
                        "x_disposition": disposition,
                    }
                )

    state_condition_rows = []
    collision_count = 0
    selected_count = Counter()

    for condition in ("A2", "A3"):
        for state_sha in sorted(state_by_sha):
            candidates = by_condition_state.get((condition, state_sha), [])
            by_semantics: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
            for row in candidates:
                candidate = require_object(row["candidate"], "projected candidate")
                semantics = execution_semantics(candidate)
                if semantics is None:
                    continue
                by_semantics[semantics].append(row)

            if not by_semantics:
                outcome = "NO_EXECUTABLE_CANDIDATE"
                selected = None
            elif len(by_semantics) == 1:
                outcome = "K1_EXECUTABLE_CANDIDATE"
                only = next(iter(by_semantics.values()))
                selected = min(
                    only,
                    key=lambda r: str(require_object(r["candidate"], "candidate")["candidate_sha256"]),
                )
                selected_count[condition] += 1
            else:
                outcome = "METHOD_INVALID_K1_STATE_BUDGET_COLLISION"
                selected = None
                collision_count += 1

            state_condition_rows.append(
                {
                    "condition_id": condition,
                    "source_state_sha256": state_sha,
                    "distinct_execution_semantics_count": len(by_semantics),
                    "outcome": outcome,
                    "selected_candidate_sha256": (
                        None
                        if selected is None
                        else require_object(selected["candidate"], "candidate")["candidate_sha256"]
                    ),
                    "execution_semantics": [
                        list(key) for key in sorted(by_semantics, key=lambda x: repr(x))
                    ],
                }
            )

    if len(state_condition_rows) != 60:
        raise SystemExit("STOP=STATE_CONDITION_OUTCOME_COUNT_NOT_60")

    ledger = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_CANDIDATE_POOL_V1",
        hash_field="candidate_pool_sha256",
        payload={
            "source_state_count": 30,
            "condition_count": 2,
            "state_condition_outcome_count": 60,
            "projected_candidate_rows": projected_rows,
            "state_condition_rows": state_condition_rows,
            "x_disposition_counts": dict(sorted(x_dispositions.items())),
            "selected_candidate_counts": dict(sorted(selected_count.items())),
            "k1_collision_count": collision_count,
            "candidate_budget_per_condition_source_state": 1,
            "collision_policy": "NO_WINNER_METHOD_INVALID",
            "environment_verification_performed": False,
            "benefit_harm_labels_assigned": False,
        },
    )
    ensure_json(ledger_path, ledger)
    print("FORMAL_ANALYZER_CANDIDATE_POOL_PASS")
    print("FORMAL_SOURCE_STATE_COUNT=30")
    print("K1_COLLISION_COUNT=" + str(collision_count))
    print("SELECTED_CANDIDATE_COUNTS=" + json.dumps(dict(selected_count), sort_keys=True))
    return ledger


def sum_usage(rows: list[Mapping[str, object]]) -> dict[str, int]:
    total = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    for row in rows:
        usage = row.get("usage")
        if not isinstance(usage, Mapping):
            continue
        for key in total:
            value = usage.get(key)
            if isinstance(value, int):
                total[key] += value
    return total


def create_support_manifests(
    cfg: Config,
    api: RepoAPI,
    offline: Mapping[str, object],
    g: Mapping[str, object],
    x: Mapping[str, object],
    candidates: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    seal_root = cfg.state_root / "05_round_evidence_seal"
    support_root = seal_root / "support"
    support_root.mkdir(parents=True, exist_ok=True)

    local = offline["local"]
    normalized = require_object(local["normalized"], "normalized local manifest")
    normalized_rows = require_array(normalized["rows"], "normalized local rows")
    closure_summary = require_object(
        load_json(cfg.closure / "FORMAL_ACT3_REGISTRATION_CLOSURE_V2.json"),
        "closure summary",
    )
    groups = require_array(
        require_object(
            load_json(cfg.closure / "ANALYZER_SOURCE_CLOSED_GROUPS_V1.json"),
            "source-closed groups",
        )["groups"],
        "source-closed groups rows",
    )

    group_size_counts = Counter(len(require_array(gp["membership_records"], "group memberships")) for gp in groups)

    rollout = support_artifact(
        api,
        schema_id="FORMAL_PI1_ROLLOUT_CENSUS_V1",
        hash_field="rollout_census_sha256",
        payload={
            "formal_main_local_request_count": 60,
            "formal_main_a0_count": 30,
            "formal_main_a1_count": 30,
            "formal_main_local_status_counts": dict(
                sorted(Counter(str(row["status"]) for row in normalized_rows).items())
            ),
            "a1_error_instance_count": closure_summary.get("error_instance_count"),
            "full_deterministic_group_count": closure_summary.get("full_group_count"),
            "source_closed_group_count": closure_summary.get("source_closed_group_count"),
            "source_closed_membership_count": sum(
                len(require_array(gp["membership_records"], "members")) for gp in groups
            ),
            "group_size_census": {str(k): v for k, v in sorted(group_size_counts.items())},
        },
    )
    ensure_json(support_root / "FORMAL_PI1_ROLLOUT_CENSUS_V1.json", rollout)

    mechanical = support_artifact(
        api,
        schema_id="FORMAL_PI1_MECHANICAL_FAILURE_CENSUS_V1",
        hash_field="mechanical_failure_census_sha256",
        payload={
            "source_call_selection_counts": closure_summary.get("source_call_selection_counts"),
            "mechanical_signature_pass_count": closure_summary.get("mechanical_signature_pass_count"),
            "mechanical_signature_failure_counts": closure_summary.get(
                "mechanical_signature_failure_counts"
            ),
            "formal_source_binding_eligible_count": closure_summary.get(
                "formal_source_binding_eligible_count"
            ),
            "exact_source_registration_pass_count": closure_summary.get(
                "exact_source_registration_pass_count"
            ),
            "partial_source_group_count": closure_summary.get("partial_source_group_count"),
            "no_source_group_count": closure_summary.get("no_source_group_count"),
            "all_error_groups_preserved": closure_summary.get("all_error_groups_preserved"),
        },
    )
    ensure_json(support_root / "FORMAL_PI1_MECHANICAL_FAILURE_CENSUS_V1.json", mechanical)

    g_rows = [require_object(r, "G import row") for r in require_array(g["import_manifest"]["rows"], "G rows")]
    x_rows = [require_object(r, "X import row") for r in require_array(x["import_manifest"]["rows"], "X rows")]
    g_status_by_condition = defaultdict(Counter)
    for row in g_rows:
        g_status_by_condition[str(row.get("condition_id"))][str(row.get("status"))] += 1

    x_dispositions = Counter()
    for row in x_rows:
        if row.get("status") != "VALIDATED":
            continue
        artifact = require_object(load_json(Path(str(row["validated_artifact_path"]))), "X artifact")
        x_dispositions[str(artifact.get("disposition"))] += 1

    metric = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_PREVERIFICATION_METRIC_REPORT_V1",
        hash_field="analyzer_metric_report_sha256",
        payload={
            "metric_scope": "PRE_ENVIRONMENT_VERIFICATION",
            "local_a0_a1_accepted_count": 60,
            "group_status_counts_by_condition": {
                key: dict(sorted(value.items())) for key, value in sorted(g_status_by_condition.items())
            },
            "x_request_count": len(x_rows),
            "x_status_counts": dict(
                sorted(Counter(str(row.get("status")) for row in x_rows).items())
            ),
            "x_disposition_counts": dict(sorted(x_dispositions.items())),
            "candidate_source_state_count": candidates["source_state_count"],
            "candidate_state_condition_outcome_count": candidates[
                "state_condition_outcome_count"
            ],
            "candidate_selected_counts": candidates["selected_candidate_counts"],
            "k1_collision_count": candidates["k1_collision_count"],
            "benefit_harm_metrics_present": False,
            "environment_effect_labels_present": False,
        },
    )
    ensure_json(support_root / "FORMAL_ANALYZER_PREVERIFICATION_METRIC_REPORT_V1.json", metric)

    formal_result = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_RESULT_MANIFEST_V1",
        hash_field="analyzer_formal_result_manifest_sha256",
        payload={
            "round_id": cfg.round_id,
            "policy_version": EXPECTED_POLICY_VERSION,
            "formal_dag_sha256": offline["dag"]["formal_dag_sha256"],
            "local_runtime_registry_sha256": local["registry"]["registry_sha256"],
            "local_normalized_execution_manifest_file_sha256": sha256_file(
                Path(str(local["normalized_path"]))
            ),
            "a2a3_pair_audit_file_sha256": sha256_file(
                cfg.a2a3_root / "A2_A3_PAIR_AUDIT.json"
            ),
            "a3_memory_restore_summary_file_sha256": sha256_file(
                cfg.memory_root / "RESTORE_SUMMARY_V1.json"
            ),
            "g_batch_import_manifest_sha256": g["import_manifest"]["import_manifest_sha256"],
            "x_batch_import_manifest_sha256": x["import_manifest"]["import_manifest_sha256"],
            "candidate_pool_sha256": candidates["candidate_pool_sha256"],
            "formal_groups_registered": 30,
            "formal_g_requests_registered": 60,
            "formal_x_requests_registered": len(x_rows),
            "automatic_scientific_retry_performed": False,
            "environment_execution_performed": False,
            "f0f1_performed": False,
        },
    )
    ensure_json(support_root / "FORMAL_ANALYZER_RESULT_MANIFEST_V1.json", formal_result)

    resource = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_RESOURCE_BUDGET_MANIFEST_V1",
        hash_field="resource_budget_manifest_sha256",
        payload={
            "local_a0a1_request_count": 60,
            "local_a0a1_usage": sum_usage(normalized_rows),
            "g_registered_request_count": 60,
            "g_usage": sum_usage(g_rows),
            "x_registered_request_count": len(x_rows),
            "x_usage": sum_usage(x_rows),
            "a2a3_max_rendered_request_size_bytes": require_object(
                load_json(cfg.a2a3_root / "REQUEST_PREFLIGHT.json"),
                "A2A3 preflight",
            ).get("max_request_size_bytes"),
            "environment_call_count": 0,
            "f0f1_call_count": 0,
        },
    )
    ensure_json(support_root / "FORMAL_ANALYZER_RESOURCE_BUDGET_MANIFEST_V1.json", resource)

    relevant_paths = [
        "src/pchsi/analyzer/grouping.py",
        "src/pchsi/analyzer/candidate_projector.py",
        "src/pchsi/cognitive_runtime/projections.py",
        "src/pchsi/cognitive_runtime/request_renderer.py",
        "src/pchsi/cognitive_runtime/output_validation.py",
        "src/pchsi/cognitive_runtime/formal_registry_v2.py",
        "src/pchsi/cognitive_runtime/round_evidence.py",
        "configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json",
    ]
    code_rows = []
    for rel in relevant_paths:
        path = cfg.repo / rel
        if not path.is_file():
            raise SystemExit(f"STOP=CODE_CONFIG_BOUND_FILE_MISSING:{rel}")
        code_rows.append({"path": rel, "sha256": sha256_file(path)})

    code_diff = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_CODE_CONFIG_DIFF_MANIFEST_V1",
        hash_field="code_config_diff_manifest_sha256",
        payload={
            "formal_repo_head": EXPECTED_HEAD,
            "formal_repo_clean": True,
            "bound_files": code_rows,
            "new_scientific_algorithm_introduced_by_boundary_package": False,
            "boundary_package_role": "ORCHESTRATION_AND_CONTENT_ADDRESSED_GLUE_ONLY",
        },
    )
    ensure_json(support_root / "FORMAL_ANALYZER_CODE_CONFIG_DIFF_MANIFEST_V1.json", code_diff)

    return {
        "rollout": rollout,
        "mechanical": mechanical,
        "metric": metric,
        "formal_result": formal_result,
        "resource": resource,
        "code_diff": code_diff,
    }


def verify_policy_identity(
    cfg: Config,
    api: RepoAPI,
    local: Mapping[str, object],
) -> dict[str, object]:
    mode = None
    adapter_observed = None
    if cfg.pi1_adapter_root.is_dir() and not cfg.pi1_adapter_root.is_symlink():
        adapter_observed = api.directory_manifest_sha256(cfg.pi1_adapter_root)
        if adapter_observed != EXPECTED_POLICY_CHECKPOINT_SHA256:
            raise SystemExit(
                "STOP=PI1_CHECKPOINT_DIRECTORY_MANIFEST_DRIFT:"
                f"{adapter_observed}"
            )
        mode = "DIRECTORY_MANIFEST_VERIFIED"
    elif cfg.pi1_review.is_file() and not cfg.pi1_review.is_symlink():
        review = require_object(load_json(cfg.pi1_review), "PI1 identity review")
        raw = json.dumps(review, sort_keys=True)
        if EXPECTED_POLICY_CHECKPOINT_SHA256 not in raw:
            raise SystemExit("STOP=PI1_IDENTITY_REVIEW_DOES_NOT_BIND_CHECKPOINT")
        mode = "REGISTERED_IDENTITY_REVIEW_VERIFIED"
    else:
        raise SystemExit("STOP=NO_PI1_CHECKPOINT_OR_IDENTITY_REVIEW_AUTHORITY")

    condition_hits = 0
    runtime_hits = 0
    for pair in local["pairs"].values():
        a1 = pair["1"]
        artifact = require_object(a1["validated_artifact"], "A1 artifact")

        def walk(value: object):
            nonlocal condition_hits, runtime_hits
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "policy_condition_manifest_sha256":
                        condition_hits += 1
                        if child != EXPECTED_POLICY_CONDITION_SHA256:
                            raise SystemExit("STOP=POLICY_CONDITION_SHA_DRIFT_IN_A1")
                    if key == "policy_runtime_manifest_sha256":
                        runtime_hits += 1
                        if child != EXPECTED_POLICY_RUNTIME_SHA256:
                            raise SystemExit("STOP=POLICY_RUNTIME_SHA_DRIFT_IN_A1")
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(artifact)

    payload = {
        "policy_version": EXPECTED_POLICY_VERSION,
        "policy_checkpoint_sha256": EXPECTED_POLICY_CHECKPOINT_SHA256,
        "policy_condition_manifest_sha256": EXPECTED_POLICY_CONDITION_SHA256,
        "policy_runtime_manifest_sha256": EXPECTED_POLICY_RUNTIME_SHA256,
        "verification_mode": mode,
        "adapter_directory_manifest_sha256_observed": adapter_observed,
        "registered_identity_review_expected_sha256": EXPECTED_PI1_IDENTITY_REVIEW_SHA256,
        "a1_policy_condition_binding_hit_count": condition_hits,
        "a1_policy_runtime_binding_hit_count": runtime_hits,
    }
    lineage = support_artifact(
        api,
        schema_id="FORMAL_PI1_POLICY_LINEAGE_BINDING_V1",
        hash_field="policy_lineage_sha256",
        payload=payload,
    )
    return lineage


def stage_round_evidence(
    cfg: Config,
    api: RepoAPI,
    offline: Mapping[str, object],
    g: Mapping[str, object],
    x: Mapping[str, object],
    candidates: Mapping[str, object],
) -> dict[str, object]:
    seal_root = cfg.state_root / "05_round_evidence_seal"
    round_path = seal_root / "ROUND_EVIDENCE_PACKAGE_V1.json"
    final_path = seal_root / "FORMAL_ANALYZER_PRE_HUMAN_BOUNDARY_V1.json"

    if round_path.is_file() and final_path.is_file():
        round_pkg = require_object(load_json(round_path), "round evidence package")
        api.validate_artifact("ROUND_EVIDENCE_PACKAGE_V1", round_pkg)
        return round_pkg

    support = create_support_manifests(cfg, api, offline, g, x, candidates)
    policy_lineage = verify_policy_identity(cfg, api, offline["local"])
    support_root = seal_root / "support"
    ensure_json(support_root / "FORMAL_PI1_POLICY_LINEAGE_BINDING_V1.json", policy_lineage)

    round_value = {
        "round_id": cfg.round_id,
        "policy_lineage_sha256": policy_lineage["policy_lineage_sha256"],
        "policy_checkpoint_sha256": EXPECTED_POLICY_CHECKPOINT_SHA256,
        "policy_config_sha256": EXPECTED_POLICY_CONDITION_SHA256,
        "task_set_manifest_sha256": offline["local"]["task_set_manifest_sha256"],
        "rollout_census_sha256": support["rollout"]["rollout_census_sha256"],
        "mechanical_failure_census_sha256": support["mechanical"][
            "mechanical_failure_census_sha256"
        ],
        "analyzer_formal_result_manifest_sha256": support["formal_result"][
            "analyzer_formal_result_manifest_sha256"
        ],
        "analyzer_metric_report_sha256": support["metric"]["analyzer_metric_report_sha256"],
        "researcher_memory_pack_sha256": None,
        "historical_f0f1_summary_sha256": None,
        "historical_go_nogo_ledger_sha256": None,
        "previous_researcher_decisions_sha256": None,
        "training_history_sha256": None,
        "resource_budget_manifest_sha256": support["resource"][
            "resource_budget_manifest_sha256"
        ],
        "code_config_diff_manifest_sha256": support["code_diff"][
            "code_config_diff_manifest_sha256"
        ],
    }
    seal_root.mkdir(parents=True, exist_ok=True)
    if round_path.exists():
        round_pkg = require_object(load_json(round_path), "round evidence package")
    else:
        round_pkg = api.freeze_round_evidence_package(round_value, round_path)

    api.validate_artifact("ROUND_EVIDENCE_PACKAGE_V1", round_pkg)

    boundary = support_artifact(
        api,
        schema_id="FORMAL_ANALYZER_PRE_HUMAN_BOUNDARY_V1",
        hash_field="boundary_sha256",
        payload={
            "formal_dag_sha256": offline["dag"]["formal_dag_sha256"],
            "g_batch_import_manifest_sha256": g["import_manifest"]["import_manifest_sha256"],
            "x_batch_import_manifest_sha256": x["import_manifest"]["import_manifest_sha256"],
            "candidate_pool_sha256": candidates["candidate_pool_sha256"],
            "round_evidence_package_sha256": round_pkg["round_evidence_package_sha256"],
            "human_researcher_pre_created": False,
            "api_researcher_pre_shadow_created": False,
            "environment_call_performed": False,
            "f0f1_performed": False,
            "next_gate": "HUMAN_TRAINING_RESEARCHER_PRE",
        },
    )
    ensure_json(final_path, boundary)
    return round_pkg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("FORMAL_MAIN_REPO", str(DEFAULT_REPO)))
    parser.add_argument(
        "--local-registry",
        default=os.environ.get("FORMAL_MAIN_LOCAL_REGISTRY", str(DEFAULT_LOCAL_REGISTRY)),
    )
    parser.add_argument(
        "--main-import",
        default=os.environ.get("FORMAL_MAIN_IMPORT_ROOT", str(DEFAULT_MAIN_IMPORT)),
    )
    parser.add_argument(
        "--postmain-freeze",
        default=os.environ.get("FORMAL_MAIN_POSTLOCAL_FREEZE", str(DEFAULT_POSTMAIN_FREEZE)),
    )
    parser.add_argument(
        "--closure",
        default=os.environ.get("FORMAL_ACT3_CLOSURE", str(DEFAULT_CLOSURE)),
    )
    parser.add_argument(
        "--memory-root",
        default=os.environ.get("FORMAL_MAIN_A3_MEMORY_ROOT", str(DEFAULT_MEMORY_ROOT)),
    )
    parser.add_argument(
        "--a2a3-root",
        default=os.environ.get("FORMAL_MAIN_A2A3_ROOT", str(DEFAULT_A2A3_ROOT)),
    )
    parser.add_argument(
        "--state-root",
        default=os.environ.get("FORMAL_ANALYZER_BOUNDARY_STATE_ROOT", str(DEFAULT_STATE_ROOT)),
    )
    parser.add_argument(
        "--pi1-adapter-root",
        default=os.environ.get("PCHSI_PI1_ADAPTER_ROOT", str(DEFAULT_PI1_ADAPTER_ROOT)),
    )
    parser.add_argument(
        "--pi1-review",
        default=os.environ.get("PCHSI_PI1_IDENTITY_REVIEW", str(DEFAULT_PI1_REVIEW)),
    )
    parser.add_argument(
        "--round-id",
        default=os.environ.get("PCHSI_FORMAL_ROUND_ID", "FORMAL_ANALYZER_PI1_REFERENCE_V1"),
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=int(os.environ.get("PCHSI_BATCH_POLL_SECONDS", "60")),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = Config(args)
    cfg.state_root.mkdir(parents=True, exist_ok=True)

    api = verify_repo(cfg)

    required = [
        cfg.local_registry,
        cfg.main_import / "normalized_execution_manifest.json",
        cfg.postmain_freeze,
        cfg.closure / "ANALYZER_SOURCE_CLOSED_GROUPS_V1.json",
        cfg.closure / "FORMAL_SOURCE_CONTEXTS_V1.json",
        cfg.memory_root / "RESTORE_SUMMARY_V1.json",
        cfg.a2a3_root / "A2_A3_PAIR_AUDIT.json",
        cfg.a2a3_root / "REQUEST_PREFLIGHT.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("STOP=REQUIRED_INPUT_MISSING:" + repr(missing))

    postmain = require_object(load_json(cfg.postmain_freeze), "postmain freeze")
    if postmain.get("schema_id") != "FORMAL_MAIN_POSTLOCAL_INPUT_FREEZE_V1":
        raise SystemExit("STOP=POSTMAIN_FREEZE_SCHEMA")
    if postmain.get("a1_result_count") != 30:
        raise SystemExit("STOP=POSTMAIN_FREEZE_A1_COUNT")

    print("========== STAGE 1: OFFLINE GROUP REGISTRY + DAG V2 ==========")
    offline = stage_offline(cfg, api)

    print("========== STAGE 2: FORMAL G-A2/A3 BATCH ==========")
    g = run_g_batch(cfg, api, offline)

    print("========== STAGE 3: FORMAL X BATCH ==========")
    x = run_x_batch(cfg, api, g, offline)

    print("========== STAGE 4: DETERMINISTIC CANDIDATE PROJECTOR + K1 ==========")
    candidates = stage_candidates(cfg, api, g, x)

    print("========== STAGE 5: ROUND EVIDENCE SEAL ==========")
    round_pkg = stage_round_evidence(cfg, api, offline, g, x, candidates)

    print("FORMAL_ANALYZER_TO_HUMAN_PRE_BOUNDARY_PASS")
    print("ROUND_EVIDENCE_PACKAGE_V1=" + str(
        cfg.state_root / "05_round_evidence_seal" / "ROUND_EVIDENCE_PACKAGE_V1.json"
    ))
    print("ROUND_EVIDENCE_PACKAGE_SHA256=" + str(round_pkg["round_evidence_package_sha256"]))
    print("HUMAN_RESEARCHER_PRE_CREATED=false")
    print("API_RESEARCHER_PRE_SHADOW_CREATED=false")
    print("ENVIRONMENT_CALL_PERFORMED=false")
    print("F0F1_PERFORMED=false")
    print("AUTOMATIC_SCIENTIFIC_RETRY_PERFORMED=false")
    print("NEXT_GATE=HUMAN_TRAINING_RESEARCHER_PRE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
