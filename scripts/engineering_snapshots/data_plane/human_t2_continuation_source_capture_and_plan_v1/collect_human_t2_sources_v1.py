#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

PYTHON = Path(sys.executable)

PARENT_RUNNER_ROOT = Path(
    "/data/run01/scwb204/pchsi/p2/"
    "p4_r1_q2_bad_training_runner_v1_frozen"
)
PARENT_CONFIG = Path(
    "/data/run01/scwb204/pchsi/p2/"
    "p4_r1_q2_bad_training_config_v1/"
    "training_config.json"
)
PARENT_CHECKPOINT_ROOT = Path(
    "/data/run01/scwb204/pchsi/p2/"
    "p4_r1_q2_bad_checkpoint_set_v1_frozen"
)
CURRENT_PACKAGE_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2"
)
ROUND_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1"
)
CURRENT_OUTPUT_ROOT = ROUND_ROOT / (
    "qwen25_3b_schema_aware_renderer_adapter_"
    "and_trainer_native_preflight_v1_7_2"
)
OUTPUT_ROOT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "human_t2_continuation_source_capture_v1_output"
)

EXPECTED_FORMAL_TRAIN_SHA = (
    "4709c32d34b437d2884fa83d4967f4d898e4cd17d5a56ce0b9e72a250f0ad9e7"
)
EXPECTED_TRAIN_CONFIG_SHA = (
    "a860a77890e34e4cfcb38dff0acdf35db0a3605d0a494c100f2b74b9f5228f9c"
)
EXPECTED_PARENT_ADAPTER_BUNDLE_SHA = (
    "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"
)

TEXT_SUFFIXES = {".py", ".json", ".jsonl", ".md", ".txt", ".sh", ".jinja"}
MAX_CAPTURE_SIZE = 8 * 1024 * 1024


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise Stop(f"{label}_MISSING:{path}")


def safe_copy(source: Path, destination: Path) -> dict:
    require_file(source, "SOURCE_FILE")
    if source.stat().st_size > MAX_CAPTURE_SIZE:
        raise Stop(f"SOURCE_FILE_TOO_LARGE:{source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "source_path": str(source),
        "bundle_path": str(destination.relative_to(OUTPUT_ROOT)),
        "size": source.stat().st_size,
        "sha256": sha256_file(source),
    }


def formal_train_symbol_census(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    functions = []
    classes = []
    constants = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", None),
                    "arguments": [arg.arg for arg in node.args.args],
                }
            )
        elif isinstance(node, ast.ClassDef):
            classes.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", None),
                }
            )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    constants.append(
                        {
                            "name": target.id,
                            "line": node.lineno,
                        }
                    )

    keywords = [
        "get_peft_model",
        "PeftModel",
        "resume_from_checkpoint",
        "get_linear_schedule_with_warmup",
        "save_pretrained",
        "training_step_ledger",
        "formal_run_manifest",
        "adapter_artifact_manifest",
        "hash_trainable_parameters",
        "gradient_accumulation",
        "input_ids",
        "labels",
    ]
    occurrences = {
        keyword: [
            index
            for index, line in enumerate(text.splitlines(), start=1)
            if keyword in line
        ]
        for keyword in keywords
    }

    return {
        "source_path": str(path),
        "source_sha256": sha256_file(path),
        "functions": functions,
        "classes": classes,
        "constants": constants,
        "keyword_occurrences": occurrences,
    }


def collect_text_tree(root: Path, bundle_prefix: Path, manifest: list[dict]) -> None:
    if not root.is_dir():
        raise Stop(f"CAPTURE_ROOT_MISSING:{root}")
    for source in sorted(root.rglob("*")):
        if not source.is_file():
            continue
        if source.name == "adapter_model.safetensors":
            continue
        if source.suffix not in TEXT_SUFFIXES:
            continue
        if source.stat().st_size > MAX_CAPTURE_SIZE:
            continue
        rel = source.relative_to(root)
        manifest.append(
            safe_copy(
                source,
                OUTPUT_ROOT / bundle_prefix / rel,
            )
        )


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise Stop(f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}")

    require_file(PARENT_CONFIG, "PARENT_CONFIG")
    formal_train = PARENT_RUNNER_ROOT / "formal_train.py"
    require_file(formal_train, "FORMAL_TRAIN")

    if sha256_file(PARENT_CONFIG) != EXPECTED_TRAIN_CONFIG_SHA:
        raise Stop("PARENT_TRAIN_CONFIG_SHA_CHANGED")
    if sha256_file(formal_train) != EXPECTED_FORMAL_TRAIN_SHA:
        raise Stop("FORMAL_TRAIN_SHA_CHANGED")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    source_manifest: list[dict] = []

    collect_text_tree(
        PARENT_RUNNER_ROOT,
        Path("sources/parent_runner"),
        source_manifest,
    )

    source_manifest.append(
        safe_copy(
            PARENT_CONFIG,
            OUTPUT_ROOT / "sources/parent_config/training_config.json",
        )
    )

    capture_files = [
        (
            PARENT_CHECKPOINT_ROOT / "provenance/execution_spec.json",
            "sources/parent_checkpoint/provenance/execution_spec.json",
        ),
        (
            PARENT_CHECKPOINT_ROOT / "provenance/runner_manifest.json",
            "sources/parent_checkpoint/provenance/runner_manifest.json",
        ),
        (
            PARENT_CHECKPOINT_ROOT / "checkpoint_set_manifest.json",
            "sources/parent_checkpoint/checkpoint_set_manifest.json",
        ),
        (
            PARENT_CHECKPOINT_ROOT / "seed_17/adapter/adapter_config.json",
            "sources/parent_checkpoint/seed_17/adapter_config.json",
        ),
        (
            PARENT_CHECKPOINT_ROOT / "seed_17/adapter_artifact_manifest.json",
            "sources/parent_checkpoint/seed_17/adapter_artifact_manifest.json",
        ),
        (
            PARENT_CHECKPOINT_ROOT / "seed_17/formal_run_manifest.json",
            "sources/parent_checkpoint/seed_17/formal_run_manifest.json",
        ),
        (
            PARENT_CHECKPOINT_ROOT / "seed_17/training_step_ledger.jsonl",
            "sources/parent_checkpoint/seed_17/training_step_ledger.jsonl",
        ),
        (
            CURRENT_PACKAGE_ROOT / "PACKAGE_METADATA.json",
            "sources/current_package/PACKAGE_METADATA.json",
        ),
        (
            CURRENT_PACKAGE_ROOT / "tools/materialize_current_t2_trainer_native.py",
            "sources/current_package/materialize_current_t2_trainer_native.py",
        ),
        (
            CURRENT_OUTPUT_ROOT / "trainer_preflight/TRAINER_EXECUTION_PREFLIGHT_V5.json",
            "sources/current_output/TRAINER_EXECUTION_PREFLIGHT_V5.json",
        ),
        (
            CURRENT_OUTPUT_ROOT / "review/REVIEW_MANIFEST_V1.json",
            "sources/current_output/REVIEW_MANIFEST_V1.json",
        ),
        (
            CURRENT_OUTPUT_ROOT / "trainer_native_dataset/POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json",
            "sources/current_output/POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json",
        ),
        (
            CURRENT_OUTPUT_ROOT / "trainer_native_dataset/POLICY_T2_TRAINER_NATIVE_V1.jsonl",
            "sources/current_output/POLICY_T2_TRAINER_NATIVE_V1.jsonl",
        ),
    ]

    for source, rel in capture_files:
        source_manifest.append(
            safe_copy(
                source,
                OUTPUT_ROOT / rel,
            )
        )

    adapter_model = (
        PARENT_CHECKPOINT_ROOT
        / "seed_17/adapter/adapter_model.safetensors"
    )
    require_file(adapter_model, "PARENT_ADAPTER_MODEL")
    adapter_identity = {
        "adapter_model_path": str(adapter_model),
        "adapter_model_size": adapter_model.stat().st_size,
        "adapter_model_sha256": sha256_file(adapter_model),
        "adapter_config": load_json(
            PARENT_CHECKPOINT_ROOT
            / "seed_17/adapter/adapter_config.json"
        ),
        "expected_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER_BUNDLE_SHA,
        "checkpoint_set_manifest": load_json(
            PARENT_CHECKPOINT_ROOT / "checkpoint_set_manifest.json"
        ),
    }

    current_preflight = load_json(
        CURRENT_OUTPUT_ROOT
        / "trainer_preflight/TRAINER_EXECUTION_PREFLIGHT_V5.json"
    )
    current_dataset = load_json(
        CURRENT_OUTPUT_ROOT
        / "trainer_native_dataset/POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json"
    )
    parent_config = load_json(PARENT_CONFIG)

    contract_summary = {
        "parent_training_config_sha256": sha256_file(PARENT_CONFIG),
        "parent_formal_train_sha256": sha256_file(formal_train),
        "current_preflight": current_preflight,
        "current_dataset_manifest": current_dataset,
        "parent_optimization": parent_config.get("optimization"),
        "parent_peft": parent_config.get("peft"),
        "parent_execution": parent_config.get("execution"),
        "parent_objective": parent_config.get("objective"),
        "parent_training_budget": parent_config.get("training_budget"),
        "current_round_expected": {
            "rows": 12,
            "epochs": 1,
            "sequence_lengths": [
                774, 654, 568, 327, 570, 343,
                436, 333, 491, 314, 274, 425,
            ],
            "sequence_max": 774,
            "one_pass_target_loss_tokens": 151,
            "micro_batch": 1,
            "gradient_accumulation": 4,
            "effective_batch": 4,
            "optimizer_steps": 3,
            "warmup_steps": 0,
            "training_seed": 17,
            "data_seed": 17,
            "resume_from_checkpoint": False,
            "load_parent_adapter_as_trainable": True,
        },
    }

    candidate_patterns = [
        "*human*pre*.json",
        "*human*post*.json",
        "*strong*pre*.json",
        "*strong*post*.json",
        "*adjudication*.json",
        "*training*plan*.json",
        "*f0f1*.json",
        "*result*audit*.json",
    ]
    handoff_candidates = []
    for pattern in candidate_patterns:
        for path in sorted(ROUND_ROOT.rglob(pattern)):
            if not path.is_file():
                continue
            if path.stat().st_size > MAX_CAPTURE_SIZE:
                continue
            handoff_candidates.append(
                {
                    "pattern": pattern,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )

    reports = OUTPUT_ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "SOURCE_CAPTURE_MANIFEST_V1.json").write_text(
        json.dumps(
            {
                "schema_id": "HUMAN_T2_SOURCE_CAPTURE_MANIFEST_V1",
                "files": source_manifest,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (reports / "FORMAL_TRAIN_SYMBOL_CENSUS_V1.json").write_text(
        json.dumps(
            formal_train_symbol_census(formal_train),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (reports / "CURRENT_T2_CONTRACT_SUMMARY_V1.json").write_text(
        json.dumps(
            contract_summary,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (reports / "PARENT_TRAIN17_IDENTITY_V1.json").write_text(
        json.dumps(
            adapter_identity,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (reports / "HUMAN_T2_EXISTING_HANDOFF_CANDIDATES_V1.json").write_text(
        json.dumps(
            {
                "schema_id": "HUMAN_T2_EXISTING_HANDOFF_CANDIDATES_V1",
                "candidates": handoff_candidates,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = OUTPUT_ROOT.parent / (
        "HUMAN_T2_CONTINUATION_SOURCE_REVIEW_BUNDLE_V1.zip"
    )
    if bundle.exists():
        raise Stop(f"BUNDLE_ALREADY_EXISTS:{bundle}")

    with zipfile.ZipFile(
        bundle,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(OUTPUT_ROOT).as_posix(),
                )

    print("HUMAN_T2_SOURCE_CAPTURE_PASS")
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")
    print(f"BUNDLE={bundle}")
    print(f"BUNDLE_SHA256={sha256_file(bundle)}")
    print("REPOSITORY_MUTATION=false")
    print("MODEL_EXECUTION=false")
    print("ENVIRONMENT_EXECUTION=false")
    print("TRAINING_EXECUTION=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stop as exc:
        raise SystemExit("STOP=" + str(exc))
