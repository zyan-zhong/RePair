#!/usr/bin/env python3
"""Code-approved real Failure Memory live-cell executor.

This executable implements only the mechanical cell contract frozen by
LIVE_CELL_EXECUTOR_CONTRACT_V1. It never computes or writes Q1--Q5
dispositions. Stage 1B delegates the exact registered source-state
continuation to the already audited Formal-A runner and translates its
mechanical evidence. Stage 2/3 run the same frozen pi1/Train17 policy in real
ALFWorld tasks with a pre-frozen Memory arm/snapshot.

Exactly five files are written to --output-dir:
  CELL_SCIENTIFIC_RESULT_V1.json
  CELL_TERMINAL_RECEIPT_V1.json
  POLICY_MEMORY_PACK_V1.json
  ANALYZER_MEMORY_PACK_V1.json
  RESEARCHER_MEMORY_PACK_V1.json
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Mapping

from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.evaluation.policy_client import HttpPolicyTransport, PolicyClient
from pchsi.evaluation.policy_execution_profile import PolicyExecutionProfileV1
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
)
from pchsi.evaluation.rendered_prompt import (
    HuggingFaceTokenizerFactory,
    LocalTokenizerPromptRenderer,
)
from pchsi.evaluation.runtime_core import finalize_environment_result
from pchsi.memory.a0_replay_session import (
    replay_source_decision_state_hold_open_v1,
)
from pchsi.memory.consumer_views import (
    MemoryConsumerQueryV1,
    MemorySourcePartitionBindingV1,
    MemorySourcePartitionV1,
    ResearcherPurposeV1,
    build_analyzer_memory_view_v1,
    build_policy_memory_view_v1,
    build_researcher_memory_view_v1,
)
from pchsi.memory.dev_snapshot_loader import (
    LoadedDevSnapshotV2,
    load_calibrated_dev_snapshot_v2,
)
from pchsi.memory.formal_b_retrieval import FormalBRetrieverConfigV1
from pchsi.memory.memory_runtime_bridge import (
    prepare_memory_policy_attempt_v1,
    process_memory_policy_generation_v1,
)
from pchsi.memory.policy_projection import (
    build_failure_memory_policy_projection_v1,
)
from pchsi.memory.projection_common import ProjectionClassV1
from pchsi.memory.scientific_decision import (
    FM0, FM1, FM2, FM3, ROUND_ACTIVE,
    STAGE_1B, STAGE_2, STAGE_3,
)
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
)

EXECUTION_APPROVAL = "EXECUTION_APPROVED_FAILURE_MEMORY_LIVE_STAGES_V1"
A0_APPROVAL = "PACKAGE_A0_LOCAL_MECHANISM_EXECUTION_APPROVED"
ROLE_FILENAMES = {
    "policy": "POLICY_MEMORY_PACK_V1.json",
    "analyzer": "ANALYZER_MEMORY_PACK_V1.json",
    "researcher": "RESEARCHER_MEMORY_PACK_V1.json",
}
CONDITION_TO_A0 = {FM0: "M0", FM1: "M1", FM2: "M3"}


def _dsha(domain: str, value: Mapping[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return hashlib.sha256(
        domain.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _write_new(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=LIVE_CELL_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _canonical_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=LIVE_CELL_BOUND_OBJECT_INVALID:" + str(path))
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise SystemExit("STOP=LIVE_CELL_BOUND_OBJECT_NOT_CANONICAL:" + str(path))
    return value


def _jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    for number, raw in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        value = strict_json_loads(raw)
        if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
            raise SystemExit(f"STOP=LIVE_CELL_JSONL_NOT_CANONICAL:{path}:{number}")
        rows.append(value)
    if not rows:
        raise SystemExit("STOP=LIVE_CELL_JSONL_EMPTY:" + str(path))
    return rows


def _parse_goal(observation: str) -> str:
    prefix = "Your task is to:"
    for line in observation.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if value:
                return value
    raise ValueError("public task goal parser contract failure")


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _traj_path(gamefile: Path) -> Path:
    for name in ("traj_data.json", "traj_data.jsonl"):
        candidate = gamefile.parent / name
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return gamefile


def _load_repo_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load repository module: " + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _HFTokenCounter:
    def __init__(self, *, model_path: str, revision: str):
        from transformers import AutoTokenizer
        self.tokenizer_id = model_path
        self.tokenizer_revision = revision
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            revision=revision,
            local_files_only=True,
            trust_remote_code=False,
        )

    def count_tokens(self, text: str) -> int:
        values = self._tokenizer.encode(text, add_special_tokens=False)
        return len(values)


def _load_runtime_identity(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    outer = _canonical_object(path)
    if outer.get("schema_id") != "FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1":
        raise SystemExit("STOP=FINAL_RUNTIME_IDENTITY_SCHEMA")
    source_path = Path(str(outer["source_runtime_binding_path"]))
    if sha256_file(source_path) != outer["source_runtime_binding_sha256"]:
        raise SystemExit("STOP=SOURCE_RUNTIME_BINDING_CHANGED")
    source = _canonical_object(source_path)
    if source.get("schema_id") != "FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1":
        raise SystemExit("STOP=SOURCE_RUNTIME_BINDING_SCHEMA")
    if outer["runtime_identity_sha256"] != _dsha(
        "FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1", outer, "runtime_identity_sha256"
    ):
        raise SystemExit("STOP=FINAL_RUNTIME_IDENTITY_SELF_HASH")
    return outer, source


def _load_snapshot(
    *,
    runtime: dict[str, object],
    member_limit: int | None,
) -> LoadedDevSnapshotV2:
    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=Path(str(runtime["active_snapshot_directory"])),
        expected_snapshot_sha256=str(runtime["active_snapshot_sha256"]),
        token_budget_contract_path=Path(str(runtime["token_budget_contract_path"])),
        expected_token_budget_contract_sha256=str(
            runtime["token_budget_contract_sha256"]
        ),
    )
    if member_limit is None:
        return loaded
    if member_limit < 0 or member_limit > len(loaded.members):
        raise SystemExit("STOP=SNAPSHOT_MEMBER_LIMIT_INVALID")
    return LoadedDevSnapshotV2(
        snapshot=loaded.snapshot,
        token_budget_contract=loaded.token_budget_contract,
        members=loaded.members[:member_limit],
        snapshot_directory=loaded.snapshot_directory,
    )


def _snapshot_member_limit(
    *,
    stage: str,
    row: dict[str, object],
    manifest: dict[str, object],
) -> int | None:
    if stage != STAGE_2:
        return None
    registry_path = Path(str(manifest["operational_paths"]["snapshot_registry"]))
    registry = _canonical_object(registry_path)
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("STOP=SNAPSHOT_REGISTRY_ENTRIES")
    matches = [
        item for item in entries
        if isinstance(item, dict)
        and item.get("snapshot_sha256") == row["snapshot_sha256"]
    ]
    if len(matches) != 1:
        raise SystemExit("STOP=CELL_SNAPSHOT_REGISTRY_BINDING")
    limit = matches[0].get("member_limit")
    if type(limit) is not int or limit < 0:
        raise SystemExit("STOP=SNAPSHOT_REGISTRY_MEMBER_LIMIT")
    return limit


def _selected_payload(
    *,
    condition: str,
    query: MemoryConsumerQueryV1,
    snapshot: LoadedDevSnapshotV2,
    config: FormalBRetrieverConfigV1,
    token_counter: _HFTokenCounter,
    hard_ceiling: int,
) -> tuple[
    tuple[dict[str, object], ...],
    str,
    str | None,
    int | None,
    str | None,
    int,
    bool,
    dict[str, object] | None,
]:
    if condition == FM0 or not snapshot.members:
        return (), "M0", None, None, None, 0, False, None

    policy_view = build_policy_memory_view_v1(
        query=query,
        snapshot=snapshot,
        config=config,
    )
    if policy_view.policy_prompt_fragment() is None:
        return (), "M0", None, None, None, 0, False, None

    lineage = policy_view.selected_memory_lineage_id
    members = [
        item for item in snapshot.members
        if item.record.memory_lineage_id == lineage
    ]
    if len(members) != 1:
        raise SystemExit("STOP=SELECTED_MEMORY_MEMBER_NOT_UNIQUE")
    member = members[0]

    if condition == FM1:
        raw = member.fm1
        if raw.policy_visible_payload is None or raw.policy_visible_payload_sha256 is None:
            return (), "M0", None, None, None, 0, False, None
        payload = {
            "activation_cues": [],
            "failure_pattern": [{
                "authority": "SOURCE_BOUND_RAW_EPISODIC",
                "annotation_type": "MATCHED_FAILURE_PROCESS",
                "text": json.dumps(
                    raw.policy_visible_payload.to_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }],
            "revalidate_on": [],
            "release_cues": [],
            "non_applicability_cues": [],
            "recovery_procedure": [],
        }
        count = token_counter.count_tokens(
            canonical_json_bytes(payload).decode("utf-8")
        )
        if count > hard_ceiling:
            return (), "M0", None, None, None, 0, False, None
        return (
            (payload,), "M1", lineage, member.record.record_version,
            raw.policy_visible_payload_sha256, count, True, payload,
        )

    representation = "M2"
    if condition == FM2:
        projection = member.fm2
    else:
        projection = build_failure_memory_policy_projection_v1(
            record=member.record,
            projection_class=ProjectionClassV1.FM3,
            tokenizer=token_counter,
            hard_ceiling=hard_ceiling,
        )
        if projection.policy_visible_payload is not None:
            representation = "M3"
        elif condition == ROUND_ACTIVE:
            # Controlled external-Memory accumulation may use the governed
            # descriptive projection when prescriptive authority is absent.
            projection = member.fm2
            representation = "M2"
        else:
            # A registered FM3 cell must not silently become FM2.
            return (), "M0", None, None, None, 0, False, None

    if projection.policy_visible_payload is None:
        return (), "M0", None, None, None, 0, False, None
    payload = projection.policy_visible_payload.to_dict()
    count = (
        0 if projection.token_count is None
        else projection.token_count.policy_visible_token_count
    )
    return (
        (payload,),
        representation,
        lineage,
        member.record.record_version,
        projection.policy_visible_payload_sha256,
        count,
        True,
        payload,
    )


def _role_views(
    *,
    query: MemoryConsumerQueryV1,
    snapshot: LoadedDevSnapshotV2,
    config: FormalBRetrieverConfigV1,
    policy_payload: dict[str, object] | None,
) -> tuple[object, dict[str, object], dict[str, object]]:
    analyzer = build_analyzer_memory_view_v1(
        query=query,
        snapshot=snapshot,
        top_k=3,
    ).to_dict()
    bindings = {
        item.record.memory_lineage_id: MemorySourcePartitionBindingV1(
            memory_lineage_id=item.record.memory_lineage_id,
            source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
            partition_authority_sha256=snapshot.snapshot.snapshot_sha256,
        )
        for item in snapshot.members
    }
    researcher = build_researcher_memory_view_v1(
        snapshot=snapshot,
        purpose=ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,
        source_partition_by_lineage=bindings,
        round_evidence={
            "live_cell_role_pack_only": True,
            "scientific_outcome_authority": False,
        },
        heldout_aggregate_metrics={},
    ).to_dict()
    return policy_payload, analyzer, researcher


def _pack(
    *,
    role: str,
    cell_id: str,
    execution_manifest_sha256: str,
    payload: object,
) -> dict[str, object]:
    value = {
        "schema_id": "FAILURE_MEMORY_ROLE_PACK_V1",
        "schema_version": 1,
        "role": role.upper(),
        "cell_id": cell_id,
        "execution_manifest_sha256": execution_manifest_sha256,
        "payload": payload,
        "pack_sha256": "0" * 64,
    }
    value["pack_sha256"] = _dsha(
        "FAILURE_MEMORY_ROLE_PACK_V1", value, "pack_sha256"
    )
    return value


def _finalize_five_files(
    *,
    output: Path,
    manifest: dict[str, object],
    row: dict[str, object],
    success: bool,
    memory_exposed: bool,
    correct_memory_exposure: bool,
    wrong_memory_exposure: bool,
    unsafe_memory_exposure: bool,
    harm_observed: bool,
    abstained: bool,
    old_failure_disposition: str,
    model_calls: int,
    environment_steps: int,
    memory_tokens: int,
    prompt_tokens: int,
    latency_ms: int,
    policy_payload: object,
    analyzer_payload: dict[str, object],
    researcher_payload: dict[str, object],
) -> None:
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=LIVE_CELL_FINAL_OUTPUT_EXISTS")
    output.mkdir(parents=True, mode=0o700)

    file_shas: dict[str, str] = {}
    for role, payload in (
        ("policy", policy_payload),
        ("analyzer", analyzer_payload),
        ("researcher", researcher_payload),
    ):
        value = _pack(
            role=role,
            cell_id=str(row["cell_id"]),
            execution_manifest_sha256=str(manifest["manifest_sha256"]),
            payload=payload,
        )
        path = output / ROLE_FILENAMES[role]
        _write_new(path, value)
        file_shas[role] = sha256_file(path)

    result = {
        "schema_id": "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        "schema_version": 1,
        "cell_result_sha256": "0" * 64,
        **row,
        "execution_manifest_sha256": manifest["manifest_sha256"],
        "stage": manifest["stage"],
        "success": success,
        "memory_exposed": memory_exposed,
        "correct_memory_exposure": correct_memory_exposure,
        "wrong_memory_exposure": wrong_memory_exposure,
        "unsafe_memory_exposure": unsafe_memory_exposure,
        "harm_observed": harm_observed,
        "abstained": abstained,
        "old_failure_disposition": old_failure_disposition,
        "model_calls": model_calls,
        "environment_steps": environment_steps,
        "memory_tokens": memory_tokens,
        "prompt_tokens": prompt_tokens,
        "latency_ms": latency_ms,
        "evaluation_writeback_attempted": False,
        "same_round_memory_readback": False,
        "role_pack_sha256s": file_shas,
    }
    result["cell_result_sha256"] = _dsha(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        result,
        "cell_result_sha256",
    )
    _write_new(output / "CELL_SCIENTIFIC_RESULT_V1.json", result)

    receipt = {
        "schema_id": "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1",
        "schema_version": 1,
        "receipt_sha256": "0" * 64,
        "cell_id": row["cell_id"],
        "execution_manifest_sha256": manifest["manifest_sha256"],
        "cell_result_sha256": result["cell_result_sha256"],
        "cell_complete": True,
        "scientific_outcome_produced": True,
        "infrastructure_error": False,
    }
    receipt["receipt_sha256"] = _dsha(
        "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1",
        receipt,
        "receipt_sha256",
    )
    _write_new(output / "CELL_TERMINAL_RECEIPT_V1.json", receipt)

    observed = sorted(item.name for item in output.iterdir())
    expected = sorted([
        "CELL_SCIENTIFIC_RESULT_V1.json",
        "CELL_TERMINAL_RECEIPT_V1.json",
        *ROLE_FILENAMES.values(),
    ])
    if observed != expected:
        raise SystemExit("STOP=LIVE_CELL_ARTIFACT_SET_MISMATCH")


def _stage1b_route_v1(condition: str) -> str:
    if condition in CONDITION_TO_A0:
        return "FORMAL_A"
    if condition == FM3:
        return "LIVE_SOURCE_STATE_FM3"
    raise SystemExit("STOP=STAGE1B_CONDITION_UNSUPPORTED:" + str(condition))


def _stage1b_a0_cell_index_v1(
    *,
    a0_manifest: dict[str, object],
    source_state_id: str,
    condition: str,
) -> int:
    if condition == FM3:
        raise SystemExit("STOP=STAGE1B_FM3_HAS_NO_FORMAL_A_ALIAS")
    desired_arm = CONDITION_TO_A0.get(condition)
    if desired_arm is None:
        raise SystemExit("STOP=STAGE1B_FORMAL_A_CONDITION_UNSUPPORTED")
    cells = a0_manifest.get("cells")
    if not isinstance(cells, list):
        raise SystemExit("STOP=A0_MANIFEST_CELLS_INVALID")
    matches: list[int] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            continue
        arm = cell.get("arm")
        if (
            cell.get("source_state_id") == source_state_id
            and isinstance(arm, dict)
            and arm.get("arm_id") == desired_arm
        ):
            matches.append(index)
    if len(matches) != 1:
        raise SystemExit("STOP=A0_CELL_TRANSLATION_NOT_UNIQUE")
    return matches[0]


def _stage1b_live_fm3_v1(
    *,
    manifest: dict[str, object],
    row: dict[str, object],
    panel_entry: dict[str, object],
    runtime_outer: dict[str, object],
    source_runtime: dict[str, object],
    output: Path,
) -> None:
    a0_binding = _canonical_object(
        Path(str(panel_entry["a0_binding_path"]))
    )
    source_rows = [
        item
        for item in a0_binding.get("sources", [])
        if isinstance(item, dict)
        and item.get("source_state_id") == panel_entry["source_state_id"]
    ]
    if len(source_rows) != 1:
        raise SystemExit("STOP=STAGE1B_SOURCE_BINDING_NOT_UNIQUE")
    source_row = source_rows[0]

    source_path = Path(str(source_row["replay_source_path"]))
    if (
        source_path.is_symlink()
        or not source_path.is_file()
        or sha256_file(source_path) != source_row["replay_source_sha256"]
    ):
        raise SystemExit("STOP=STAGE1B_REPLAY_SOURCE_IDENTITY")
    source_raw = source_path.read_bytes()
    source = RegisteredReplaySourceV1.from_json(source_raw)
    if source.canonical_bytes() != source_raw:
        raise SystemExit("STOP=STAGE1B_REPLAY_SOURCE_NOT_CANONICAL")
    if (
        source.expected_source_fingerprint.fingerprint_sha256
        != panel_entry["source_state_id"]
    ):
        raise SystemExit("STOP=STAGE1B_SOURCE_STATE_IDENTITY")
    if source.source_policy_condition != source_runtime["served_model_name"]:
        raise SystemExit("STOP=STAGE1B_SOURCE_POLICY_IDENTITY")

    snapshot = _load_snapshot(
        runtime=runtime_outer,
        member_limit=None,
    )
    members = [
        item
        for item in snapshot.members
        if (
            item.record.memory_lineage_id
            == source_row["memory_lineage_id"]
            and item.record.record_version
            == source_row["record_version"]
        )
    ]
    if len(members) != 1:
        raise SystemExit("STOP=STAGE1B_FM3_MEMBER_NOT_UNIQUE")
    member = members[0]

    token_counter = _HFTokenCounter(
        model_path=str(source_runtime["base_model_local_path"]),
        revision=str(source_runtime["base_model_revision"]),
    )
    projection = build_failure_memory_policy_projection_v1(
        record=member.record,
        projection_class=ProjectionClassV1.FM3,
        tokenizer=token_counter,
        hard_ceiling=int(
            snapshot.token_budget_contract.single_record_hard_ceiling
        ),
    )
    exposed = projection.policy_visible_payload is not None
    if exposed:
        policy_payload = projection.policy_visible_payload.to_dict()
        payloads = (policy_payload,)
        representation = "M3"
        projection_sha = projection.policy_visible_payload_sha256
        packed_tokens = (
            0
            if projection.token_count is None
            else projection.token_count.policy_visible_token_count
        )
        lineage = member.record.memory_lineage_id
        record_version = member.record.record_version
    else:
        policy_payload = None
        payloads = ()
        representation = "M0"
        projection_sha = None
        packed_tokens = 0
        lineage = None
        record_version = None

    renderer = LocalTokenizerPromptRenderer(
        model_path=str(source_runtime["base_model_local_path"]),
        revision=str(source_runtime["base_model_revision"]),
        chat_template_sha256=str(source_runtime["chat_template_sha256"]),
        tokenizer_factory=HuggingFaceTokenizerFactory(),
    )
    base_url = os.environ.get(
        "FAILURE_MEMORY_POLICY_BASE_URL",
        str(source_runtime.get(
            "policy_base_url", "http://127.0.0.1:8000"
        )),
    )
    client = PolicyClient(
        transport=HttpPolicyTransport(
            base_url=base_url,
            timeout_seconds=float(os.environ.get(
                "FAILURE_MEMORY_POLICY_TIMEOUT_SECONDS", "120"
            )),
        )
    )
    profile = PolicyExecutionProfileV1(
        profile_id="FAILURE_MEMORY_STAGE1B_LIVE_FM3_V1",
        arm_id="FAILURE_MEMORY_STAGE1B_FM3",
        policy_version="PI1_BAD",
        request_kind="R0",
        requires_diagnostic_policy_call_evidence=False,
        requires_current_admissible_commands=False,
        served_model_name=str(source_runtime["served_model_name"]),
    )

    adapter = SpawnedAlfworldAdapter.start(
        exact_gamefile=Path(source.exact_gamefile),
        registration_id=str(source_row["registration_id"]),
        runtime_manifest_sha256=source.runtime_manifest_sha256,
    )
    session = None
    started = time.monotonic()
    total_memory_tokens = 0
    total_prompt_tokens = 0
    cell_model_calls = 0
    environment_steps = 0
    first_query = None

    try:
        session = replay_source_decision_state_hold_open_v1(
            source=source,
            adapter=adapter,
        )
        goal = _parse_goal(session.reset_state.observation)
        history = tuple(
            ExecutedTransition(
                expected.action,
                observed.observation,
            )
            for expected, observed in zip(
                source.transitions,
                session.step_states,
            )
        )
        observation = session.current_observation
        commands = session.current_commands
        budget = source.budget_state
        limits = BudgetLimits()
        feedback = (
            None
            if source.interface_feedback_code is None
            else InterfaceFeedbackCode(source.interface_feedback_code)
        )
        request_index = source.model_call_index
        success = False

        while True:
            query = MemoryConsumerQueryV1(
                observation=observation,
                executed_transitions=history,
                admissible_commands=tuple(commands),
                interface_feedback=feedback,
                public_task_goal=goal,
            )
            if first_query is None:
                first_query = query

            total_memory_tokens += packed_tokens
            prepared = prepare_memory_policy_attempt_v1(
                public_task_goal=goal,
                observation=observation,
                executed_transitions=history,
                memory_payloads=payloads,
                policy_visible_commands=commands,
                harness_visible_commands=commands,
                environment_commands=commands,
                interface_feedback=feedback,
                budget_state=budget,
                snapshot_sha256=str(row["snapshot_sha256"]),
                token_budget_contract_sha256=str(
                    runtime_outer["token_budget_contract_sha256"]
                ),
                retrieval_mode=(
                    "DIRECT_FIXED_RECORD_NO_RETRIEVAL"
                    if exposed
                    else "NO_RETRIEVAL"
                ),
                branch_role=str(manifest["stage"]),
                representation_class=representation,
                memory_lineage_id=lineage,
                record_version=record_version,
                projection_artifact_sha256=projection_sha,
                packed_token_count=packed_tokens,
                budget_limits=limits,
            )
            if not prepared.precondition.should_call_policy:
                success = False
                break
            if prepared.prompt is None:
                raise RuntimeError(
                    "Stage1B FM3 authorized attempt lacks prompt"
                )

            rendered = renderer.render(prompt_text=prepared.prompt)
            total_prompt_tokens += rendered.prompt_token_count
            request = profile.build_request(
                prompt_text=prepared.prompt,
                seed=int(panel_entry["continuation_seed"]),
                request_id=(
                    "fm-stage1b-fm3-"
                    + str(row["cell_id"])[:16]
                    + "-"
                    + str(request_index).zfill(4)
                ),
            )
            call = client.generate_with_evidence(
                request=request,
                expected_prompt=rendered,
            )
            cell_model_calls += 1
            request_index += 1
            decision = process_memory_policy_generation_v1(
                raw_response=call.generation.raw_response_text,
                visible_admissible_commands=commands,
                prepared=prepared,
                budget_limits=limits,
            )
            budget = decision.budget_after

            if not decision.should_call_env:
                feedback = decision.feedback_code
                if decision.termination_reason is not None:
                    success = False
                    break
                continue

            action = decision.candidate_environment_action
            if action is None:
                raise RuntimeError(
                    "Stage1B FM3 environment decision lacks action"
                )
            state = adapter.step(action)
            environment_steps += 1
            decision = finalize_environment_result(
                decision,
                environment_terminated=state.done,
                infrastructure_error=False,
            )
            budget = decision.budget_after
            history = (
                *history,
                ExecutedTransition(action, state.observation),
            )
            observation = state.observation
            commands = state.menu.commands
            feedback = None
            if state.done:
                success = bool(state.won)
                break
            if decision.termination_reason is not None:
                success = False
                break

        if first_query is None:
            raise SystemExit("STOP=STAGE1B_FM3_NO_QUERY")
        b_result = _canonical_object(
            Path(str(runtime_outer["formal_b_result_path"]))
        )
        config = FormalBRetrieverConfigV1(
            threshold_pct=int(b_result["selected_threshold_pct"])
        )
        policy, analyzer, researcher = _role_views(
            query=first_query,
            snapshot=snapshot,
            config=config,
            policy_payload=policy_payload,
        )
        _finalize_five_files(
            output=output,
            manifest=manifest,
            row=row,
            success=success,
            memory_exposed=exposed,
            correct_memory_exposure=exposed,
            wrong_memory_exposure=False,
            unsafe_memory_exposure=False,
            harm_observed=False,
            abstained=not exposed,
            old_failure_disposition="UNCERTAIN",
            model_calls=cell_model_calls,
            environment_steps=environment_steps,
            memory_tokens=total_memory_tokens,
            prompt_tokens=total_prompt_tokens,
            latency_ms=int((time.monotonic() - started) * 1000),
            policy_payload=policy,
            analyzer_payload=analyzer,
            researcher_payload=researcher,
        )
    finally:
        if session is not None:
            session.close()
        else:
            try:
                adapter.close()
            except Exception:
                pass


def _stage1b(
    *,
    repo: Path,
    manifest: dict[str, object],
    row: dict[str, object],
    panel_entry: dict[str, object],
    runtime_outer: dict[str, object],
    source_runtime: dict[str, object],
    output: Path,
) -> None:
    condition = str(row["condition"])
    if _stage1b_route_v1(condition) == "LIVE_SOURCE_STATE_FM3":
        _stage1b_live_fm3_v1(
            manifest=manifest,
            row=row,
            panel_entry=panel_entry,
            runtime_outer=runtime_outer,
            source_runtime=source_runtime,
            output=output,
        )
        return

    a0_manifest_path = Path(str(panel_entry["a0_manifest_path"]))
    a0_binding_path = Path(str(panel_entry["a0_binding_path"]))
    a0_runtime_path = Path(str(runtime_outer["a0_runtime_binding_path"]))
    a0_manifest = _canonical_object(a0_manifest_path)
    desired_arm = CONDITION_TO_A0[condition]
    index = _stage1b_a0_cell_index_v1(
        a0_manifest=a0_manifest,
        source_state_id=str(panel_entry["source_state_id"]),
        condition=condition,
    )

    raw_root = Path(str(runtime_outer["raw_cell_evidence_root"]))
    raw_out = raw_root / str(manifest["manifest_sha256"]) / str(row["cell_id"])
    if raw_out.exists():
        result_path = raw_out / "cell_result.json"
        evidence_path = raw_out / "cell_evidence.json"
        if not result_path.is_file() or not evidence_path.is_file():
            raise SystemExit("STOP=A0_RAW_CELL_PARTIAL")
    else:
        env = dict(os.environ)
        env["PACKAGE_A0_SCIENTIFIC_EXECUTION_APPROVAL"] = A0_APPROVAL
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts/memory/run_formal_a0_cell_v1.py"),
                "--manifest", str(a0_manifest_path),
                "--input-binding", str(a0_binding_path),
                "--runtime-binding", str(a0_runtime_path),
                "--cell-index", str(index),
                "--attempt-index", "0",
                "--output-dir", str(raw_out),
            ],
            check=True,
            env=env,
        )

    a0_result = _canonical_object(raw_out / "cell_result.json")
    evidence = _canonical_object(raw_out / "cell_evidence.json")
    first_policy_call = evidence["calls"][0]["policy_call"]
    query = MemoryConsumerQueryV1(
        observation=str(first_policy_call["observation"]),
        executed_transitions=tuple(
            ExecutedTransition(
                action=str(item["action"]),
                resulting_observation=str(item["resulting_observation"]),
            )
            for item in first_policy_call["executed_history"]
        ),
        admissible_commands=tuple(first_policy_call["admissible_commands"]),
        interface_feedback=(
            None
            if first_policy_call["interface_feedback_before"] is None
            else __import__(
                "pchsi.evaluation.raw_policy_prompt",
                fromlist=["InterfaceFeedbackCode"],
            ).InterfaceFeedbackCode(
                first_policy_call["interface_feedback_before"]
            )
        ),
        public_task_goal=str(first_policy_call["public_task_goal"]),
    )

    runtime_loaded = _load_snapshot(
        runtime=runtime_outer,
        member_limit=None,
    )
    b = _canonical_object(Path(str(runtime_outer["formal_b_result_path"])))
    config = FormalBRetrieverConfigV1(threshold_pct=int(b["selected_threshold_pct"]))
    template_payload = None
    if desired_arm != "M0":
        first_call = evidence["calls"][0]
        exposure = first_call["memory_exposure"]
        template = _canonical_object(
            Path(str(panel_entry["representation_template_path"]))
        )
        arms = [
            item for item in template.get("arms", [])
            if item.get("arm_id") == desired_arm
        ]
        if len(arms) != 1:
            raise SystemExit("STOP=A0_TEMPLATE_ARM_NOT_UNIQUE")
        template_payload = arms[0]["policy_visible_payload"]
    policy, analyzer, researcher = _role_views(
        query=query,
        snapshot=runtime_loaded,
        config=config,
        policy_payload=template_payload,
    )
    calls = evidence.get("calls", [])
    census = evidence.get("prompt_census", [])
    memory_tokens = sum(
        int(item["memory_exposure"]["packed_token_count"])
        for item in calls
    )
    prompt_tokens = sum(int(item["prompt_token_count"]) for item in census)
    _finalize_five_files(
        output=output,
        manifest=manifest,
        row=row,
        success=bool(a0_result["terminal_success"]),
        memory_exposed=desired_arm != "M0",
        correct_memory_exposure=desired_arm != "M0",
        wrong_memory_exposure=False,
        unsafe_memory_exposure=False,
        harm_observed=False,
        abstained=desired_arm == "M0",
        old_failure_disposition="UNCERTAIN",
        model_calls=int(a0_result["policy_call_count"]),
        environment_steps=int(a0_result["environment_step_count_from_source"]),
        memory_tokens=memory_tokens,
        prompt_tokens=prompt_tokens,
        latency_ms=sum(
            int(item["policy_call"]["latency_ms"])
            for item in calls
        ),
        policy_payload=policy,
        analyzer_payload=analyzer,
        researcher_payload=researcher,
    )


def _task_reset(
    *,
    manifest: dict[str, object],
    row: dict[str, object],
    panel_entry: dict[str, object],
    runtime_outer: dict[str, object],
    source_runtime: dict[str, object],
    output: Path,
) -> None:
    gamefile = Path(str(panel_entry["absolute_gamefile"]))
    if gamefile.is_symlink() or not gamefile.is_file():
        raise SystemExit("STOP=LIVE_TASK_GAMEFILE_INVALID")
    if sha256_file(gamefile) != panel_entry["gamefile_sha256"]:
        raise SystemExit("STOP=LIVE_TASK_GAMEFILE_SHA")

    member_limit = _snapshot_member_limit(
        stage=str(manifest["stage"]),
        row=row,
        manifest=manifest,
    )
    snapshot = _load_snapshot(
        runtime=runtime_outer,
        member_limit=member_limit,
    )
    b_result = _canonical_object(Path(str(runtime_outer["formal_b_result_path"])))
    config = FormalBRetrieverConfigV1(
        threshold_pct=int(b_result["selected_threshold_pct"])
    )
    token_counter = _HFTokenCounter(
        model_path=str(source_runtime["base_model_local_path"]),
        revision=str(source_runtime["base_model_revision"]),
    )
    renderer = LocalTokenizerPromptRenderer(
        model_path=str(source_runtime["base_model_local_path"]),
        revision=str(source_runtime["base_model_revision"]),
        chat_template_sha256=str(source_runtime["chat_template_sha256"]),
        tokenizer_factory=HuggingFaceTokenizerFactory(),
    )
    base_url = os.environ.get(
        "FAILURE_MEMORY_POLICY_BASE_URL",
        str(source_runtime.get("policy_base_url", "http://127.0.0.1:8000")),
    )
    client = PolicyClient(
        transport=HttpPolicyTransport(
            base_url=base_url,
            timeout_seconds=float(os.environ.get(
                "FAILURE_MEMORY_POLICY_TIMEOUT_SECONDS", "120"
            )),
        )
    )
    profile = PolicyExecutionProfileV1(
        profile_id="FAILURE_MEMORY_FINAL_LIVE_PI1_R0_V1",
        arm_id="FAILURE_MEMORY_FINAL_" + str(row["condition"]),
        policy_version="PI1_BAD",
        request_kind="R0",
        requires_diagnostic_policy_call_evidence=False,
        requires_current_admissible_commands=False,
        served_model_name=str(source_runtime["served_model_name"]),
    )

    adapter = SpawnedAlfworldAdapter.start(
        exact_gamefile=gamefile,
        registration_id="fm-final-" + str(row["cell_id"])[:24],
        runtime_manifest_sha256=str(
            source_runtime["environment_runtime_manifest_sha256"]
        ),
    )
    started = time.monotonic()
    first_query = None
    first_policy_payload = None
    total_memory_tokens = 0
    total_prompt_tokens = 0
    model_calls = 0
    environment_steps = 0
    memory_exposed_any = False
    correct_exposure_any = False

    try:
        reset = adapter.reset()
        goal = _parse_goal(reset.observation)
        observation = reset.observation
        commands = reset.menu.commands
        history: tuple[ExecutedTransition, ...] = ()
        feedback = None
        budget = BudgetState()
        limits = BudgetLimits()
        success = False

        while True:
            query = MemoryConsumerQueryV1(
                observation=observation,
                executed_transitions=history,
                admissible_commands=tuple(commands),
                interface_feedback=feedback,
                public_task_goal=goal,
            )
            if first_query is None:
                first_query = query

            condition = str(row["condition"])
            effective_condition = (
                FM0
                if condition == ROUND_ACTIVE and member_limit == 0
                else condition
            )
            (
                payloads,
                representation,
                lineage,
                record_version,
                projection_sha,
                packed_tokens,
                exposed,
                policy_payload,
            ) = _selected_payload(
                condition=effective_condition,
                query=query,
                snapshot=snapshot,
                config=config,
                token_counter=token_counter,
                hard_ceiling=int(
                    snapshot.token_budget_contract.single_record_hard_ceiling
                ),
            )
            if exposed and first_policy_payload is None:
                first_policy_payload = policy_payload
            memory_exposed_any = memory_exposed_any or exposed
            correct_exposure_any = correct_exposure_any or exposed
            total_memory_tokens += packed_tokens

            prepared = prepare_memory_policy_attempt_v1(
                public_task_goal=goal,
                observation=observation,
                executed_transitions=history,
                memory_payloads=payloads,
                policy_visible_commands=commands,
                harness_visible_commands=commands,
                environment_commands=commands,
                interface_feedback=feedback,
                budget_state=budget,
                snapshot_sha256=str(row["snapshot_sha256"]),
                token_budget_contract_sha256=str(
                    runtime_outer["token_budget_contract_sha256"]
                ),
                retrieval_mode=(
                    "NO_RETRIEVAL"
                    if representation == "M0"
                    else "FROZEN_JACCARD_POLICY_GATE_V1"
                ),
                branch_role=str(manifest["stage"]),
                representation_class=representation,
                memory_lineage_id=lineage,
                record_version=record_version,
                projection_artifact_sha256=projection_sha,
                packed_token_count=packed_tokens,
                budget_limits=limits,
            )
            if not prepared.precondition.should_call_policy:
                success = False
                break
            assert prepared.prompt is not None
            rendered = renderer.render(prompt_text=prepared.prompt)
            total_prompt_tokens += rendered.prompt_token_count
            request = profile.build_request(
                prompt_text=prepared.prompt,
                seed=int(panel_entry["continuation_seed"]),
                request_id=(
                    "fm-final-" + str(row["cell_id"])[:16]
                    + "-" + str(model_calls).zfill(4)
                ),
            )
            call = client.generate_with_evidence(
                request=request,
                expected_prompt=rendered,
            )
            model_calls += 1
            decision = process_memory_policy_generation_v1(
                raw_response=call.generation.raw_response_text,
                visible_admissible_commands=commands,
                prepared=prepared,
                budget_limits=limits,
            )
            budget = decision.budget_after

            if not decision.should_call_env:
                feedback = decision.feedback_code
                if decision.termination_reason is not None:
                    success = False
                    break
                continue

            action = decision.candidate_environment_action
            if action is None:
                raise RuntimeError("environment-authorized decision lacks action")
            state = adapter.step(action)
            environment_steps += 1
            decision = finalize_environment_result(
                decision,
                environment_terminated=state.done,
                infrastructure_error=False,
            )
            budget = decision.budget_after
            history = (*history, ExecutedTransition(action, state.observation))
            observation = state.observation
            commands = state.menu.commands
            feedback = None
            if state.done:
                success = bool(state.won)
                break
            if decision.termination_reason is not None:
                success = False
                break

        assert first_query is not None
        policy, analyzer, researcher = _role_views(
            query=first_query,
            snapshot=snapshot,
            config=config,
            policy_payload=first_policy_payload,
        )
        latency = int((time.monotonic() - started) * 1000)
        _finalize_five_files(
            output=output,
            manifest=manifest,
            row=row,
            success=success,
            memory_exposed=memory_exposed_any,
            # FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1 requires booleans, but
            # Stage 2/3 have no registered per-task gold exposure labels.
            # These are schema placeholders only. The independent decision
            # engine ignores them for correctness/safety and recomputes harm
            # from paired task-success outcomes.
            correct_memory_exposure=False,
            wrong_memory_exposure=False,
            unsafe_memory_exposure=False,
            harm_observed=False,
            abstained=not memory_exposed_any,
            old_failure_disposition="NOT_APPLICABLE",
            model_calls=model_calls,
            environment_steps=environment_steps,
            memory_tokens=total_memory_tokens,
            prompt_tokens=total_prompt_tokens,
            latency_ms=latency,
            policy_payload=policy,
            analyzer_payload=analyzer,
            researcher_payload=researcher,
        )
    finally:
        adapter.close()


def main() -> None:
    if os.environ.get("FAILURE_MEMORY_LIVE_EXECUTION_APPROVAL") != EXECUTION_APPROVAL:
        raise SystemExit("STOP=LIVE_CELL_EXECUTION_APPROVAL_MISSING")

    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-manifest", required=True)
    parser.add_argument("--cell-manifest", required=True)
    parser.add_argument("--cell-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    manifest = _canonical_object(Path(args.execution_manifest))
    cells = _jsonl(Path(args.cell_manifest))
    if args.cell_index < 0 or args.cell_index >= len(cells):
        raise SystemExit("STOP=LIVE_CELL_INDEX_INVALID")
    row = cells[args.cell_index]
    if row["cell_id"] not in str(Path(args.output_dir).name):
        # The outer runner uses output-dir == cells/<cell_id>.
        raise SystemExit("STOP=LIVE_CELL_OUTPUT_IDENTITY")

    panel = _canonical_object(
        Path(str(manifest["operational_paths"]["panel"]))
    )
    entries = panel.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("STOP=LIVE_PANEL_ENTRIES")
    matches = [
        item for item in entries
        if isinstance(item, dict) and item.get("task_id") == row["task_id"]
    ]
    if len(matches) != 1:
        raise SystemExit("STOP=LIVE_PANEL_TASK_NOT_UNIQUE")
    panel_entry = matches[0]

    runtime_outer, source_runtime = _load_runtime_identity(
        Path(str(manifest["operational_paths"]["runtime_identity"]))
    )
    repo = Path(__file__).resolve().parents[2]
    output = Path(args.output_dir)

    if manifest["stage"] == STAGE_1B:
        _stage1b(
            repo=repo,
            manifest=manifest,
            row=row,
            panel_entry=panel_entry,
            runtime_outer=runtime_outer,
            source_runtime=source_runtime,
            output=output,
        )
    elif manifest["stage"] in {STAGE_2, STAGE_3}:
        _task_reset(
            manifest=manifest,
            row=row,
            panel_entry=panel_entry,
            runtime_outer=runtime_outer,
            source_runtime=source_runtime,
            output=output,
        )
    else:
        raise SystemExit("STOP=LIVE_CELL_STAGE_UNSUPPORTED")

    print("FAILURE_MEMORY_REAL_LIVE_CELL_EXECUTOR_V1_PASS")
    print("CELL_ID=" + str(row["cell_id"]))


if __name__ == "__main__":
    main()
