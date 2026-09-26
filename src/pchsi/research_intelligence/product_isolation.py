from __future__ import annotations
from collections.abc import Mapping, Sequence
from pathlib import Path
import json

HUMAN = "HUMAN_REFERENCE_ROUND"
BENCHMARK = "STRONG_MODEL_BENCHMARK"

_FORBIDDEN = {
    HUMAN: {
        "STRONG_MODEL_REFERENCE_CELL_RESULT_V1",
        "STRONG_MODEL_PROVIDER_SIDECAR_MANIFEST_V1",
        "STRONG_MODEL_REFERENCE_COLLECTION_SEAL_V1",
    },
    BENCHMARK: {
        "HUMAN_RESEARCHER_PRE_V1",
        "HUMAN_RESEARCHER_POST_V1",
        "RESEARCH_REPAIR_PORTFOLIO_V1",
        "VERIFIED_TRAINING_EVIDENCE_V1",
    },
}


def _walk(value: object):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _walk(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _walk(child)
    elif isinstance(value, str):
        yield value


def assert_separate_roots(human_root: Path, benchmark_root: Path) -> None:
    human = human_root.resolve()
    benchmark = benchmark_root.resolve()
    if human == benchmark or human in benchmark.parents or benchmark in human.parents:
        raise ValueError("Human and benchmark scientific roots must be disjoint")


def assert_artifact_domain(payload: Mapping[str, object], domain: str) -> None:
    if domain not in _FORBIDDEN:
        raise ValueError(f"unknown product domain: {domain}")
    observed = set(_walk(payload))
    collisions = sorted(observed & _FORBIDDEN[domain])
    if collisions:
        raise ValueError(f"cross-product scientific result leakage: {collisions}")


def load_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact must be a JSON object")
    return value
