from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .common import hashed_payload, require_sha256, require_text


class BenchmarkSplitV1(str, Enum):
    VALID_SEEN = "VALID_SEEN"
    VALID_UNSEEN = "VALID_UNSEEN"


@dataclass(frozen=True)
class BenchmarkResultSealV1:
    benchmark_split: BenchmarkSplitV1
    checkpoint_id: str
    shared_protocol_sha256: str
    result_artifact_sha256: str
    revealed: bool
    benchmark_feedback_authorized: bool
    seal_sha256: str

    @classmethod
    def create(
        cls,
        *,
        benchmark_split: BenchmarkSplitV1,
        checkpoint_id: str,
        shared_protocol_sha256: str,
        result_artifact_sha256: str,
    ) -> "BenchmarkResultSealV1":
        require_text("checkpoint_id", checkpoint_id)
        require_sha256("shared_protocol_sha256", shared_protocol_sha256)
        require_sha256("result_artifact_sha256", result_artifact_sha256)
        payload = {
            "schema_id": "BENCHMARK_RESULT_SEAL_V1",
            "schema_version": 1,
            "benchmark_split": benchmark_split.value,
            "checkpoint_id": checkpoint_id,
            "shared_protocol_sha256": shared_protocol_sha256,
            "result_artifact_sha256": result_artifact_sha256,
            "revealed": False,
            "benchmark_feedback_authorized": False,
        }
        hashed = hashed_payload(
            domain="BENCHMARK_RESULT_SEAL_V1",
            hash_field="seal_sha256",
            payload=payload,
        )
        return cls(
            benchmark_split=benchmark_split,
            checkpoint_id=checkpoint_id,
            shared_protocol_sha256=shared_protocol_sha256,
            result_artifact_sha256=result_artifact_sha256,
            revealed=False,
            benchmark_feedback_authorized=False,
            seal_sha256=hashed["seal_sha256"],
        )

    def reveal(
        self,
        *,
        all_comparison_models_frozen: bool,
    ) -> "BenchmarkResultSealV1":
        if all_comparison_models_frozen is not True:
            raise ValueError("all comparison models must be frozen before reveal")
        payload = {
            "schema_id": "BENCHMARK_RESULT_SEAL_V1",
            "schema_version": 1,
            "benchmark_split": self.benchmark_split.value,
            "checkpoint_id": self.checkpoint_id,
            "shared_protocol_sha256": self.shared_protocol_sha256,
            "result_artifact_sha256": self.result_artifact_sha256,
            "revealed": True,
            "benchmark_feedback_authorized": False,
        }
        hashed = hashed_payload(
            domain="BENCHMARK_RESULT_SEAL_V1",
            hash_field="seal_sha256",
            payload=payload,
        )
        return replace(
            self,
            revealed=True,
            benchmark_feedback_authorized=False,
            seal_sha256=hashed["seal_sha256"],
        )
