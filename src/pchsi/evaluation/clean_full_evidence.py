from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
from pchsi.evaluation.policy_call_evidence import PolicyCallEvidenceV1
from pchsi.evaluation.schema_models import (
    AttemptReceiptV1,
    EpisodeArtifactV1,
    ScientificCellLockV1,
)
from pchsi.round_control.clean_execution_binding import CleanScheduledEpisodeV1


_OFFICIAL_SPLITS = {"valid_seen": 140, "valid_unseen": 134}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{name} must be non-empty NUL-free str")
    return value


def _mkdir(path: Path) -> None:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("campaign directory must not be symlink: " + str(path))
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("campaign directory invalid: " + str(path))


def _write_bytes_once(path: Path, payload: bytes) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json_once(path: Path, value: object) -> None:
    _write_bytes_once(
        path,
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        ),
    )


def _write_jsonl_once(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    payload = b"".join(
        (
            json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        for row in rows
    )
    _write_bytes_once(path, payload)


def _load_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("required regular JSON missing: " + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object: " + str(path))
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("required regular JSONL missing: " + str(path))
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line:
            raise ValueError(f"blank JSONL line {index}: {path}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {index} not object: {path}")
        rows.append(value)
    return rows


def _bundle_identity(attempt_dir: Path) -> str:
    attempt_dir = Path(attempt_dir)
    names = (
        "attempt.json",
        "action_traces.jsonl",
        "policy_calls.jsonl",
        "public_transitions.jsonl",
        "SHA256SUMS",
    )
    rows: list[dict[str, str]] = []
    for name in names:
        path = attempt_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("complete policy-evidence attempt file missing: " + str(path))
        rows.append({"filename": name, "sha256": _sha256_file(path)})
    return sha256_bytes(canonical_json_bytes(rows))


@dataclass(frozen=True, slots=True)
class LocalComputeSidecarV1:
    scientific_cell_id: str
    execution_attempt_id: str
    provider_kind: str
    gpu_model: str
    gpu_count: int
    wall_clock_seconds: float
    peak_gpu_memory_bytes: int | None
    vllm_version: str
    observed_api_cost_usd: None = None
    nominal_api_cost_status: str = "NOT_APPLICABLE_LOCAL_COMPUTE"

    def to_dict(self) -> dict[str, object]:
        if self.provider_kind != "LOCAL_VLLM":
            raise ValueError("local compute sidecar provider must be LOCAL_VLLM")
        _require_text(self.scientific_cell_id, "scientific_cell_id")
        _require_text(self.execution_attempt_id, "execution_attempt_id")
        _require_text(self.gpu_model, "gpu_model")
        _require_text(self.vllm_version, "vllm_version")
        if type(self.gpu_count) is not int or self.gpu_count <= 0:
            raise ValueError("gpu_count must be positive int")
        if type(self.wall_clock_seconds) not in (int, float) or self.wall_clock_seconds < 0:
            raise ValueError("wall_clock_seconds must be non-negative numeric")
        if self.peak_gpu_memory_bytes is not None and (
            type(self.peak_gpu_memory_bytes) is not int or self.peak_gpu_memory_bytes < 0
        ):
            raise ValueError("peak_gpu_memory_bytes invalid")
        if self.observed_api_cost_usd is not None:
            raise ValueError("local compute must not fabricate API cost")
        if self.nominal_api_cost_status != "NOT_APPLICABLE_LOCAL_COMPUTE":
            raise ValueError("local compute cost status invalid")
        return {
            "schema_id": "LOCAL_VLLM_COMPUTE_SIDECAR_V1",
            "schema_version": 1,
            "scientific_cell_id": self.scientific_cell_id,
            "execution_attempt_id": self.execution_attempt_id,
            "provider_kind": self.provider_kind,
            "gpu_model": self.gpu_model,
            "gpu_count": self.gpu_count,
            "wall_clock_seconds": float(self.wall_clock_seconds),
            "peak_gpu_memory_bytes": self.peak_gpu_memory_bytes,
            "vllm_version": self.vllm_version,
            "observed_api_cost_usd": None,
            "nominal_api_cost_status": self.nominal_api_cost_status,
        }


def write_local_compute_sidecar(path: Path, sidecar: LocalComputeSidecarV1) -> None:
    if not isinstance(sidecar, LocalComputeSidecarV1):
        raise TypeError("sidecar must be LocalComputeSidecarV1")
    _write_json_once(path, sidecar.to_dict())


def _campaign_cells(
    cells: Sequence[CleanScheduledEpisodeV1], *, product_domain: str
) -> tuple[CleanScheduledEpisodeV1, ...]:
    frozen = tuple(cells)
    if not frozen:
        raise ValueError("campaign cells must be non-empty")
    if any(not isinstance(cell, CleanScheduledEpisodeV1) for cell in frozen):
        raise TypeError("campaign cells must contain CleanScheduledEpisodeV1")
    scientific_ids = [cell.scientific_cell_id for cell in frozen]
    if len(scientific_ids) != len(set(scientific_ids)):
        raise ValueError("scientific cell ids must be globally unique")
    if product_domain == "OFFICIAL_BENCHMARK":
        counts = Counter(cell.split for cell in frozen)
        if counts != Counter(_OFFICIAL_SPLITS):
            raise ValueError("official campaign must be exact valid_seen 140 + valid_unseen 134")
    elif product_domain == "TRAIN_UPDATE":
        if any(cell.split != "train" for cell in frozen):
            raise ValueError("TRAIN_UPDATE campaign must be train-only")
    else:
        raise ValueError("unsupported full-evidence product domain")
    return frozen


def prepare_full_evidence_campaign(
    *,
    campaign_root: Path,
    campaign_id: str,
    campaign_sha256: str,
    pi0_artifact_sha256: str,
    cells: Sequence[CleanScheduledEpisodeV1],
    product_domain: str,
    result_visibility: str,
) -> dict[str, object]:
    campaign_root = Path(campaign_root)
    if campaign_root.exists() or campaign_root.is_symlink():
        raise FileExistsError(str(campaign_root))
    _require_text(campaign_id, "campaign_id")
    _require_sha256(campaign_sha256, "campaign_sha256")
    _require_sha256(pi0_artifact_sha256, "pi0_artifact_sha256")
    frozen = _campaign_cells(cells, product_domain=product_domain)
    if product_domain == "OFFICIAL_BENCHMARK" and result_visibility != "SEALED":
        raise ValueError("official benchmark full evidence must remain SEALED")
    if product_domain == "TRAIN_UPDATE" and result_visibility != "ADAPTIVE_AFTER_ROUND_GATE":
        raise ValueError("TRAIN_UPDATE visibility contract mismatch")

    _mkdir(campaign_root)
    for split in sorted({cell.split for cell in frozen}):
        for relative in (
            f"{split}/artifacts",
            f"{split}/artifacts/provider_sidecars",
            f"{split}/artifacts/cell_results",
            f"{split}/provider_ledger",
            f"{split}/local_transport",
            f"{split}/bindings",
            f"{split}/preflight",
        ):
            _mkdir(campaign_root / relative)
    for relative in (
        "metadata/snapshots/schemas",
        "logs",
        "reports/per_task/full",
        "reports/grouped",
        "reports/decoded_provider_calls",
        "reports/indices",
        "reports/integrity",
    ):
        _mkdir(campaign_root / relative)

    prepared = {
        "schema_id": "CLEAN_FULL_EVIDENCE_CAMPAIGN_PREPARED_V1",
        "schema_version": 1,
        "campaign_id": campaign_id,
        "campaign_sha256": campaign_sha256,
        "pi0_artifact_sha256": pi0_artifact_sha256,
        "product_domain": product_domain,
        "result_visibility": result_visibility,
        "expected_cell_count": len(frozen),
        "expected_split_counts": dict(sorted(Counter(cell.split for cell in frozen).items())),
        "scientific_execution_authorized": False,
        "collection_complete": False,
    }
    _write_json_once(campaign_root / "PREPARED.json", prepared)
    return prepared


def _safe_average(values: Sequence[int | float]) -> float | None:
    return None if not values else float(mean(values))


def _write_csv_once(path: Path, rows: Sequence[Mapping[str, object]], fields: Sequence[str]) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _group_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    total = len(rows)
    successes = sum(row.get("success") is True for row in rows)
    return {
        "task_count": total,
        "success_count": successes,
        "failure_count": total - successes,
        "success_rate": None if total == 0 else successes / total,
        "mean_policy_attempts": _safe_average(
            [int(row["policy_attempt_count"]) for row in rows]
        ),
        "mean_environment_steps": _safe_average(
            [int(row["environment_step_count"]) for row in rows]
        ),
        "input_tokens_total": sum(int(row["input_tokens"]) for row in rows),
        "output_tokens_total": sum(int(row["output_tokens"]) for row in rows),
        "latency_ms_total": sum(int(row["provider_latency_ms"]) for row in rows),
    }


def _nested_group(rows: Sequence[Mapping[str, object]], keys: Sequence[str]) -> dict[str, object]:
    groups: dict[tuple[str, ...], list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row[key]) for key in keys)].append(row)
    return {
        "|".join(key): _group_summary(values)
        for key, values in sorted(groups.items())
    }


def finalize_full_evidence_campaign(
    *,
    campaign_root: Path,
    cells: Sequence[CleanScheduledEpisodeV1],
    product_domain: str,
    campaign_sha256: str,
    result_visibility: str,
) -> dict[str, object]:
    campaign_root = Path(campaign_root).resolve()
    _require_sha256(campaign_sha256, "campaign_sha256")
    frozen = _campaign_cells(cells, product_domain=product_domain)
    prepared = _load_json(campaign_root / "PREPARED.json")
    if prepared.get("campaign_sha256") != campaign_sha256:
        raise ValueError("campaign PREPARED identity mismatch")
    if prepared.get("product_domain") != product_domain:
        raise ValueError("campaign PREPARED product domain mismatch")
    if prepared.get("result_visibility") != result_visibility:
        raise ValueError("campaign PREPARED visibility mismatch")
    if product_domain == "OFFICIAL_BENCHMARK" and result_visibility != "SEALED":
        raise ValueError("official benchmark cannot be finalized unsealed")

    per_task: list[dict[str, object]] = []
    evidence_index: list[dict[str, object]] = []
    trajectory_index: list[dict[str, object]] = []
    provider_call_index: list[dict[str, object]] = []
    all_policy_calls: list[PolicyCallEvidenceV1] = []
    termination = Counter()
    scientific = Counter()
    operational = Counter()
    failure_codes = Counter()
    feedback_codes = Counter()
    admissibility = Counter()

    for cell in frozen:
        split_root = campaign_root / cell.split
        artifacts = split_root / "artifacts"
        attempt_dir = artifacts / "attempts" / cell.execution_attempt_id
        terminal_path = artifacts / "attempt_ledger" / (
            cell.execution_attempt_id + ".terminal.json"
        )
        cell_lock_path = artifacts / "cell_locks" / (cell.cell.scheduled_cell_id + ".json")
        sidecar_path = artifacts / "provider_sidecars" / (
            cell.execution_attempt_id + ".local_compute.json"
        )
        for path in (attempt_dir,):
            if path.is_symlink() or not path.is_dir():
                raise ValueError("expected completed attempt directory missing: " + str(path))
        terminal = AttemptReceiptV1.from_json(terminal_path.read_bytes())
        lock = ScientificCellLockV1.from_json(cell_lock_path.read_bytes())
        sidecar = _load_json(sidecar_path)
        if terminal.receipt_kind != "TERMINAL":
            raise ValueError("attempt terminal receipt kind mismatch")
        if terminal.execution_attempt_id != cell.execution_attempt_id:
            raise ValueError("terminal attempt identity mismatch")
        if lock.execution_attempt_id != cell.execution_attempt_id:
            raise ValueError("cell lock attempt identity mismatch")
        bundle_sha = _bundle_identity(attempt_dir)
        if terminal.attempt_bundle_sha256 != bundle_sha or lock.attempt_bundle_sha256 != bundle_sha:
            raise ValueError("attempt bundle identity mismatch")
        if sidecar.get("schema_id") != "LOCAL_VLLM_COMPUTE_SIDECAR_V1":
            raise ValueError("local compute sidecar schema mismatch")
        if sidecar.get("scientific_cell_id") != cell.scientific_cell_id:
            raise ValueError("local compute scientific cell mismatch")
        if sidecar.get("execution_attempt_id") != cell.execution_attempt_id:
            raise ValueError("local compute attempt identity mismatch")
        if sidecar.get("observed_api_cost_usd") is not None:
            raise ValueError("local compute sidecar fabricated API cost")

        episode = EpisodeArtifactV1.from_json((attempt_dir / "attempt.json").read_bytes())
        if episode.execution_attempt_id != cell.execution_attempt_id:
            raise ValueError("episode attempt identity mismatch")
        if episode.task_id != cell.cell.task_id or episode.seed != cell.cell.seed:
            raise ValueError("episode scheduled task identity mismatch")

        trace_rows = _load_jsonl(attempt_dir / "action_traces.jsonl")
        transition_rows = _load_jsonl(attempt_dir / "public_transitions.jsonl")
        policy_rows = _load_jsonl(attempt_dir / "policy_calls.jsonl")
        policy_calls = [PolicyCallEvidenceV1.from_dict(row) for row in policy_rows]
        all_policy_calls.extend(policy_calls)
        input_tokens = sum(call.prompt_tokens for call in policy_calls)
        output_tokens = sum(call.completion_tokens for call in policy_calls)
        provider_latency = sum(call.latency_ms for call in policy_calls)

        for trace in trace_rows:
            feedback = trace.get("interface_feedback")
            if feedback is not None:
                feedback_codes[str(feedback)] += 1
            status = trace.get("execution_status")
            if status is not None:
                admissibility[str(status)] += 1

        termination[episode.termination_reason] += 1
        scientific[episode.scientific_outcome_status] += 1
        operational[episode.operational_finalization_status] += 1
        if terminal.error_code is not None:
            failure_codes[terminal.error_code] += 1

        row: dict[str, object] = {
            "scientific_cell_id": cell.scientific_cell_id,
            "split": cell.split,
            "execution_attempt_id": cell.execution_attempt_id,
            "task_index": episode.task_index,
            "task_id": episode.task_id,
            "task_type": episode.task_type,
            "seed": episode.seed,
            "success": episode.success,
            "termination_reason": episode.termination_reason,
            "scientific_outcome_status": episode.scientific_outcome_status,
            "operational_finalization_status": episode.operational_finalization_status,
            "policy_attempt_count": episode.final_budget.policy_attempt_count,
            "environment_step_count": episode.final_budget.environment_step_count,
            "protocol_failure_count": episode.final_budget.protocol_failure_count,
            "inadmissible_action_count": episode.final_budget.inadmissible_action_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": None,
            "provider_latency_ms": provider_latency,
            "attempt_bundle_sha256": bundle_sha,
            "episode_semantic_sha256": episode.episode_semantic_sha256,
            "local_wall_clock_seconds": sidecar.get("wall_clock_seconds"),
            "peak_gpu_memory_bytes": sidecar.get("peak_gpu_memory_bytes"),
            "nominal_api_cost_status": "NOT_APPLICABLE_LOCAL_COMPUTE",
        }
        per_task.append(row)

        full_view = {
            "schema_id": "CLEAN_FULL_EVIDENCE_PER_TASK_VIEW_V1",
            "schema_version": 1,
            "scientific_cell_id": cell.scientific_cell_id,
            "summary": row,
            "attempt": episode.to_dict(),
            "action_traces": trace_rows,
            "policy_calls": policy_rows,
            "public_transitions": transition_rows,
            "local_compute_sidecar": sidecar,
        }
        full_path = campaign_root / "reports/per_task/full" / (
            cell.scientific_cell_id + ".json"
        )
        _write_json_once(full_path, full_view)

        provider_ledger_path = split_root / "provider_ledger" / (
            cell.execution_attempt_id + ".jsonl"
        )
        _write_jsonl_once(provider_ledger_path, policy_rows)

        for call in policy_calls:
            decoded_request = json.loads(call.request_wire_bytes.decode("utf-8"))
            decoded_response = json.loads(call.raw_response_body.decode("utf-8"))
            decoded_path = campaign_root / "reports/decoded_provider_calls" / (
                cell.scientific_cell_id + f"-call{call.model_call_index:04d}.json"
            )
            _write_json_once(
                decoded_path,
                {
                    "schema_id": "LOCAL_VLLM_DECODED_PROVIDER_CALL_V1",
                    "schema_version": 1,
                    "scientific_cell_id": cell.scientific_cell_id,
                    "execution_attempt_id": cell.execution_attempt_id,
                    "model_call_index": call.model_call_index,
                    "client_request_id": call.client_request_id,
                    "provider_request_id": call.provider_request_id,
                    "request_wire_sha256": call.request_wire_sha256,
                    "raw_response_body_sha256": call.raw_response_body_sha256,
                    "decoded_request": decoded_request,
                    "decoded_response": decoded_response,
                },
            )
            provider_call_index.append(
                {
                    "scientific_cell_id": cell.scientific_cell_id,
                    "execution_attempt_id": cell.execution_attempt_id,
                    "model_call_index": call.model_call_index,
                    "client_request_id": call.client_request_id,
                    "provider_request_id": call.provider_request_id,
                    "request_wire_sha256": call.request_wire_sha256,
                    "raw_response_body_sha256": call.raw_response_body_sha256,
                    "decoded_provider_call_path": str(decoded_path.relative_to(campaign_root)),
                }
            )

        result_path = artifacts / "cell_results" / (cell.scientific_cell_id + ".json")
        _write_json_once(
            result_path,
            {
                "schema_id": "CLEAN_FULL_EVIDENCE_CELL_RESULT_V1",
                "schema_version": 1,
                **row,
            },
        )
        evidence_index.append(
            {
                "scientific_cell_id": cell.scientific_cell_id,
                "split": cell.split,
                "execution_attempt_id": cell.execution_attempt_id,
                "attempt_bundle_sha256": bundle_sha,
                "attempt_path": str(attempt_dir.relative_to(campaign_root)),
                "terminal_receipt_path": str(terminal_path.relative_to(campaign_root)),
                "cell_lock_path": str(cell_lock_path.relative_to(campaign_root)),
                "local_compute_sidecar_path": str(sidecar_path.relative_to(campaign_root)),
            }
        )
        trajectory_index.append(
            {
                "scientific_cell_id": cell.scientific_cell_id,
                "execution_attempt_id": cell.execution_attempt_id,
                "action_trace_path": str((attempt_dir / "action_traces.jsonl").relative_to(campaign_root)),
                "public_transition_path": str((attempt_dir / "public_transitions.jsonl").relative_to(campaign_root)),
                "trace_count": episode.trace_count,
                "public_transition_count": episode.public_transition_count,
            }
        )

    per_task = sorted(per_task, key=lambda row: (str(row["split"]), int(row["task_index"])))
    evidence_index = sorted(evidence_index, key=lambda row: str(row["scientific_cell_id"]))
    trajectory_index = sorted(trajectory_index, key=lambda row: str(row["scientific_cell_id"]))
    provider_call_index = sorted(
        provider_call_index,
        key=lambda row: (str(row["scientific_cell_id"]), int(row["model_call_index"])),
    )

    _write_jsonl_once(campaign_root / "reports/per_task/per_task_results.jsonl", per_task)
    _write_csv_once(
        campaign_root / "reports/per_task/per_task_results.csv",
        per_task,
        (
            "scientific_cell_id",
            "split",
            "execution_attempt_id",
            "task_index",
            "task_id",
            "task_type",
            "seed",
            "success",
            "termination_reason",
            "scientific_outcome_status",
            "operational_finalization_status",
            "policy_attempt_count",
            "environment_step_count",
            "protocol_failure_count",
            "inadmissible_action_count",
            "input_tokens",
            "output_tokens",
            "provider_latency_ms",
            "local_wall_clock_seconds",
            "peak_gpu_memory_bytes",
        ),
    )
    _write_jsonl_once(campaign_root / "reports/indices/evidence_index.jsonl", evidence_index)
    _write_jsonl_once(campaign_root / "reports/indices/trajectory_index.jsonl", trajectory_index)
    _write_jsonl_once(campaign_root / "reports/indices/provider_call_index.jsonl", provider_call_index)

    overall = _group_summary(per_task)
    by_split = _nested_group(per_task, ("split",))
    by_task_type = _nested_group(per_task, ("task_type",))
    by_split_task = _nested_group(per_task, ("split", "task_type"))
    for path, value in (
        ("reports/grouped/overall.json", overall),
        ("reports/grouped/by_split.json", by_split),
        ("reports/grouped/by_task_type.json", by_task_type),
        ("reports/grouped/by_split_and_task_type.json", by_split_task),
        ("reports/grouped/termination_reason_distribution.json", dict(sorted(termination.items()))),
        ("reports/grouped/scientific_outcome_distribution.json", dict(sorted(scientific.items()))),
        ("reports/grouped/execution_status_distribution.json", dict(sorted(operational.items()))),
        ("reports/grouped/failure_code_distribution.json", dict(sorted(failure_codes.items()))),
        ("reports/grouped/feedback_code_distribution.json", dict(sorted(feedback_codes.items()))),
        ("reports/grouped/admissibility_status_distribution.json", dict(sorted(admissibility.items()))),
    ):
        _write_json_once(campaign_root / path, value)

    _write_json_once(
        campaign_root / "reports/grouped/attempt_outcome_distribution.json",
        {
            "success": sum(row["success"] is True for row in per_task),
            "failure_or_not_produced": sum(row["success"] is not True for row in per_task),
        },
    )
    _write_json_once(
        campaign_root / "reports/grouped/efficiency_statistics.json",
        {
            "task_count": len(per_task),
            "environment_steps_total": sum(int(row["environment_step_count"]) for row in per_task),
            "policy_attempts_total": sum(int(row["policy_attempt_count"]) for row in per_task),
            "mean_environment_steps": _safe_average([int(row["environment_step_count"]) for row in per_task]),
            "mean_policy_attempts": _safe_average([int(row["policy_attempt_count"]) for row in per_task]),
        },
    )
    _write_json_once(
        campaign_root / "reports/grouped/provider_usage_statistics.json",
        {
            "provider_kind": "LOCAL_VLLM",
            "provider_call_count": len(all_policy_calls),
            "input_tokens_total": sum(call.prompt_tokens for call in all_policy_calls),
            "output_tokens_total": sum(call.completion_tokens for call in all_policy_calls),
            "reasoning_tokens_total": None,
            "latency_ms_total": sum(call.latency_ms for call in all_policy_calls),
        },
    )
    sidecars = [_load_json(Path(row["local_compute_sidecar_path"]) if Path(str(row["local_compute_sidecar_path"])).is_absolute() else campaign_root / str(row["local_compute_sidecar_path"])) for row in evidence_index]
    _write_json_once(
        campaign_root / "reports/grouped/local_compute_usage.json",
        {
            "provider_kind": "LOCAL_VLLM",
            "attempt_count": len(sidecars),
            "wall_clock_seconds_total": sum(float(row["wall_clock_seconds"]) for row in sidecars),
            "peak_gpu_memory_bytes_max": max(
                (int(row["peak_gpu_memory_bytes"]) for row in sidecars if row.get("peak_gpu_memory_bytes") is not None),
                default=None,
            ),
            "gpu_models": sorted({str(row["gpu_model"]) for row in sidecars}),
        },
    )
    _write_json_once(
        campaign_root / "reports/grouped/nominal_api_cost.json",
        {
            "status": "NOT_APPLICABLE_LOCAL_COMPUTE",
            "observed_api_cost_usd": None,
            "note": "Local GPU compute is reported separately and must not be represented as zero API cost.",
        },
    )

    full_report = {
        "schema_id": "CLEAN_FULL_BENCHMARK_REPORT_V1" if product_domain == "OFFICIAL_BENCHMARK" else "CLEAN_TRAIN_UPDATE_FULL_EVIDENCE_REPORT_V1",
        "schema_version": 1,
        "product_domain": product_domain,
        "campaign_sha256": campaign_sha256,
        "result_visibility": result_visibility,
        "overall": overall,
        "by_split": by_split,
        "by_task_type": by_task_type,
        "by_split_and_task_type": by_split_task,
        "task_count": len(per_task),
        "provider_kind": "LOCAL_VLLM",
        "benchmark_feedback_authorized": False if product_domain == "OFFICIAL_BENCHMARK" else None,
    }
    _write_json_once(campaign_root / "reports/FULL_BENCHMARK_REPORT.json", full_report)
    _write_bytes_once(
        campaign_root / "reports/SUMMARY.md",
        (
            "# Full Evidence Summary\n\n"
            f"Product domain: `{product_domain}`\n\n"
            f"Task count: `{len(per_task)}`\n\n"
            f"Result visibility: `{result_visibility}`\n"
        ).encode("utf-8"),
    )
    _write_bytes_once(
        campaign_root / "reports/PAPER_TABLES.md",
        b"# Paper Tables\n\nGenerated from reports/per_task/per_task_results.jsonl.\n",
    )

    collection_complete = {
        "schema_id": "CLEAN_FULL_EVIDENCE_COLLECTION_COMPLETE_V1",
        "schema_version": 1,
        "campaign_sha256": campaign_sha256,
        "product_domain": product_domain,
        "expected_cell_count": len(frozen),
        "observed_complete_cell_count": len(per_task),
        "all_expected_cells_complete": True,
        "result_visibility": result_visibility,
    }
    _write_json_once(campaign_root / "COLLECTION_COMPLETE.json", collection_complete)

    completeness = {
        "schema_id": "CLEAN_FULL_EVIDENCE_COMPLETENESS_AUDIT_V1",
        "schema_version": 1,
        "campaign_sha256": campaign_sha256,
        "expected_cell_count": len(frozen),
        "complete_attempt_bundle_count": len(per_task),
        "terminal_receipt_count": len(per_task),
        "cell_lock_count": len(per_task),
        "local_compute_sidecar_count": len(per_task),
        "provider_call_count": len(provider_call_index),
        "per_task_full_view_count": len(per_task),
        "missing_cell_count": 0,
        "conflicting_cell_count": 0,
        "pass": True,
    }
    _write_json_once(campaign_root / "reports/integrity/COMPLETENESS_AUDIT.json", completeness)

    inventory_rows: list[dict[str, object]] = []
    excluded = {
        "reports/integrity/ASSET_INVENTORY.json",
        "reports/integrity/SHA256SUMS_ALL.txt",
        "FULL_EVIDENCE_REPORT_COMPLETE.json",
    }
    for path in sorted(campaign_root.rglob("*"), key=lambda value: str(value.relative_to(campaign_root))):
        if path.is_symlink():
            raise ValueError("campaign symlink forbidden: " + str(path.relative_to(campaign_root)))
        if not path.is_file():
            continue
        relative = str(path.relative_to(campaign_root))
        if relative in excluded:
            continue
        inventory_rows.append(
            {"path": relative, "sha256": _sha256_file(path), "size_bytes": path.stat().st_size}
        )
    inventory = {
        "schema_id": "CLEAN_FULL_EVIDENCE_ASSET_INVENTORY_V1",
        "schema_version": 1,
        "campaign_sha256": campaign_sha256,
        "asset_count": len(inventory_rows),
        "assets": inventory_rows,
    }
    _write_json_once(campaign_root / "reports/integrity/ASSET_INVENTORY.json", inventory)

    checksum_paths = [
        path
        for path in sorted(campaign_root.rglob("*"), key=lambda value: str(value.relative_to(campaign_root)))
        if path.is_file()
        and not path.is_symlink()
        and str(path.relative_to(campaign_root))
        not in {"reports/integrity/SHA256SUMS_ALL.txt", "FULL_EVIDENCE_REPORT_COMPLETE.json"}
    ]
    checksum_text = "".join(
        f"{_sha256_file(path)}  {path.relative_to(campaign_root)}\n" for path in checksum_paths
    )
    _write_bytes_once(campaign_root / "reports/integrity/SHA256SUMS_ALL.txt", checksum_text.encode("utf-8"))
    checksums_sha = _sha256_file(campaign_root / "reports/integrity/SHA256SUMS_ALL.txt")

    report_complete = {
        "schema_id": "CLEAN_FULL_EVIDENCE_REPORT_COMPLETE_V1",
        "schema_version": 1,
        "campaign_sha256": campaign_sha256,
        "product_domain": product_domain,
        "result_visibility": result_visibility,
        "full_report_sha256": _sha256_file(campaign_root / "reports/FULL_BENCHMARK_REPORT.json"),
        "completeness_audit_sha256": _sha256_file(campaign_root / "reports/integrity/COMPLETENESS_AUDIT.json"),
        "asset_inventory_sha256": _sha256_file(campaign_root / "reports/integrity/ASSET_INVENTORY.json"),
        "sha256sums_all_sha256": checksums_sha,
        "terminal_marker_intentionally_excluded_from_sha256sums_all": True,
        "benchmark_feedback_authorized": False if product_domain == "OFFICIAL_BENCHMARK" else None,
    }
    _write_json_once(campaign_root / "FULL_EVIDENCE_REPORT_COMPLETE.json", report_complete)
    return report_complete
