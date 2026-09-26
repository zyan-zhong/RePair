from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).parents[2] / "scripts" / "research_intelligence" / "materialize_reference_round_readiness_v2.py"


def load_script():
    spec = importlib.util.spec_from_file_location("readiness_v2", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path, module, *, omit: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    for asset in module.REQUIRED_ASSETS:
        if asset.asset_id == omit:
            continue
        path = repo / asset.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(asset.asset_id + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixtures"], check=True)
    return repo


def test_inventory_distinguishes_ready_from_query_required(tmp_path: Path) -> None:
    module = load_script()
    ready_repo = make_repo(tmp_path / "ready", module)
    ready = module.inventory_required(ready_repo)
    assert all(row["status"] == "PRESENT" for row in ready)

    missing_repo = make_repo(
        tmp_path / "missing",
        module,
        omit="FORMAL_ANALYZER_RESULT_MANIFEST",
    )
    missing = module.inventory_required(missing_repo)
    row = next(
        item for item in missing if item["asset_id"] == "FORMAL_ANALYZER_RESULT_MANIFEST"
    )
    assert row["status"] == "MISSING_QUERY_REQUIRED"


def test_benchmark_skeleton_keeps_historical_gpt_pending_audit() -> None:
    module = load_script()
    payload = module.benchmark_skeleton(
        round_id="r",
        parent_policy_id="pi1",
        evidence_cutoff_sha256="0" * 64,
        discovered={"TRAINER_AND_EVALUATOR_ASSETS": []},
    )
    strong = next(entry for entry in payload["entries"] if entry["stage"] == "STRONG_MODEL_REFERENCE")
    assert strong["comparability"] == "PENDING_PROTOCOL_AUDIT"
    assert strong["status"] == "HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT"


def test_benchmark_skeleton_separates_shared_protocol_from_model_identity() -> None:
    module = load_script()
    payload = module.benchmark_skeleton(
        round_id="r",
        parent_policy_id="pi1",
        evidence_cutoff_sha256="0" * 64,
        discovered={"TRAINER_AND_EVALUATOR_ASSETS": []},
    )
    shared = payload["shared_evaluation_protocol_required_fields"]
    model = payload["model_execution_profile_required_fields"]
    assert "model/tokenizer/adapter hashes when exposed" not in shared
    assert "model/tokenizer/adapter hashes when exposed" in model
    assert "prompt/history" in shared
