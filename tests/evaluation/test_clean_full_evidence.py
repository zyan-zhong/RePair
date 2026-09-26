from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.evaluation.clean_full_evidence import (
    LocalComputeSidecarV1,
    prepare_full_evidence_campaign,
    write_local_compute_sidecar,
)
from pchsi.evaluation.run_schedule import ScheduledCell
from pchsi.round_control.clean_execution_binding import CleanScheduledEpisodeV1


def _cell(split: str, index: int) -> CleanScheduledEpisodeV1:
    runtime = f"e1-t{index:04d}-s0000000017"
    return CleanScheduledEpisodeV1(
        scientific_cell_id=f"pi0-clean-{split.replace('_','-')}-t{index:04d}-s0000000017",
        split=split,
        cell=ScheduledCell(
            scheduled_cell_id=runtime,
            task_index=index,
            task_id=f"{split}-{index}",
            seed=17,
        ),
        execution_attempt_id=runtime + "-a000",
        attempt_ordinal=0,
    )


def test_official_full_evidence_prepare_requires_exact_140_plus_134(tmp_path: Path) -> None:
    cells = tuple(_cell("valid_seen", i) for i in range(140)) + tuple(
        _cell("valid_unseen", i) for i in range(134)
    )
    value = prepare_full_evidence_campaign(
        campaign_root=tmp_path / "campaign",
        campaign_id="PI0-CLEAN-OFFICIAL-BENCHMARK-V1",
        campaign_sha256="a" * 64,
        pi0_artifact_sha256="b" * 64,
        cells=cells,
        product_domain="OFFICIAL_BENCHMARK",
        result_visibility="SEALED",
    )
    assert value["expected_cell_count"] == 274
    assert value["expected_split_counts"] == {"valid_seen": 140, "valid_unseen": 134}
    assert value["scientific_execution_authorized"] is False


def test_official_full_evidence_rejects_train_select_or_unsealed(tmp_path: Path) -> None:
    cells = (_cell("train", 0),)
    with pytest.raises(ValueError, match="valid_seen"):
        prepare_full_evidence_campaign(
            campaign_root=tmp_path / "bad",
            campaign_id="bad",
            campaign_sha256="a" * 64,
            pi0_artifact_sha256="b" * 64,
            cells=cells,
            product_domain="OFFICIAL_BENCHMARK",
            result_visibility="SEALED",
        )


def test_local_compute_sidecar_never_fabricates_api_cost(tmp_path: Path) -> None:
    path = tmp_path / "sidecar.json"
    sidecar = LocalComputeSidecarV1(
        scientific_cell_id="cell",
        execution_attempt_id="attempt",
        provider_kind="LOCAL_VLLM",
        gpu_model="NVIDIA A800-SXM4-80GB",
        gpu_count=1,
        wall_clock_seconds=1.25,
        peak_gpu_memory_bytes=123,
        vllm_version="0.11.0",
    )
    write_local_compute_sidecar(path, sidecar)
    assert path.is_file()
    with pytest.raises(FileExistsError):
        write_local_compute_sidecar(path, sidecar)
