from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROW_SCHEMA = "LOCAL_ANALYZER_BOOTSTRAP_TRAINER_NATIVE_ROW_V1"
MANIFEST_SCHEMA = "LOCAL_ANALYZER_BOOTSTRAP_TRAINER_NATIVE_MANIFEST_V1"


class AdapterContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdapterContractError(f"object required: {path}")
    return value


def load_native_records(
    *,
    dataset_path: Path,
    manifest_path: Path,
) -> tuple[dict[str, Any], ...]:
    """Validate Local-Analyzer native rows without policy-state assumptions.

    Identity is source_example_sha256 + role + stage + scientific unit.
    Multiple Analyzer stages may legitimately originate from the same task/state,
    so the historical task-policy adapter's one-unique-source-state rule is not
    imported here.
    """
    manifest = load_json(manifest_path)
    if manifest.get("schema_id") != MANIFEST_SCHEMA:
        raise AdapterContractError("manifest schema mismatch")
    if manifest.get("row_count") != 144:
        raise AdapterContractError("Analyzer denominator drift")
    if manifest.get("trained_region") != "ASSISTANT_COMPLETION_SUFFIX_ONLY":
        raise AdapterContractError("trained-region drift")
    if manifest.get("prompt_label_value") != -100:
        raise AdapterContractError("prompt label drift")
    if manifest.get("packing") is not False:
        raise AdapterContractError("packing escalated")
    if manifest.get("truncation") is not False:
        raise AdapterContractError("truncation escalated")
    if manifest.get("dataset_sha256") != sha256_file(dataset_path):
        raise AdapterContractError("dataset SHA mismatch")

    rows = []
    seen_examples: set[str] = set()
    response_total = 0

    for ordinal, line in enumerate(
        dataset_path.read_text(encoding="utf-8").splitlines()
    ):
        if not line:
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise AdapterContractError("native row must be object")
        if row.get("schema_id") != ROW_SCHEMA:
            raise AdapterContractError(f"row schema drift:{ordinal}")
        if row.get("ordinal") != ordinal:
            raise AdapterContractError(f"ordinal drift:{ordinal}")

        identity = row.get("source_identity")
        tokenization = row.get("tokenization")
        if not isinstance(identity, dict) or not isinstance(tokenization, dict):
            raise AdapterContractError(f"row sections missing:{ordinal}")

        source_example = identity.get("source_example_sha256")
        if not isinstance(source_example, str) or len(source_example) != 64:
            raise AdapterContractError(f"source example invalid:{ordinal}")
        if source_example in seen_examples:
            raise AdapterContractError(f"duplicate source example:{source_example}")
        seen_examples.add(source_example)

        if identity.get("role") != "ANALYZER":
            raise AdapterContractError(f"non-Analyzer row:{ordinal}")
        stage = identity.get("stage_id")
        if not isinstance(stage, str) or not stage:
            raise AdapterContractError(f"stage missing:{ordinal}")

        input_ids = tokenization.get("input_ids")
        labels = tokenization.get("labels")
        if not isinstance(input_ids, list) or not isinstance(labels, list):
            raise AdapterContractError(f"token arrays invalid:{ordinal}")
        if len(input_ids) != len(labels):
            raise AdapterContractError(f"input/label length mismatch:{ordinal}")

        sequence_count = tokenization.get("sequence_token_count")
        prompt_count = tokenization.get("prompt_token_count")
        response_count = tokenization.get("response_loss_token_count")
        if sequence_count != len(input_ids):
            raise AdapterContractError(f"sequence count mismatch:{ordinal}")
        if type(prompt_count) is not int or prompt_count <= 0:
            raise AdapterContractError(f"prompt count invalid:{ordinal}")
        if type(response_count) is not int or response_count <= 0:
            raise AdapterContractError(f"response count invalid:{ordinal}")

        if labels[:prompt_count] != [-100] * prompt_count:
            raise AdapterContractError(f"prompt mask violation:{ordinal}")
        if labels[prompt_count:] != input_ids[prompt_count:]:
            raise AdapterContractError(f"assistant suffix violation:{ordinal}")
        if sum(value != -100 for value in labels) != response_count:
            raise AdapterContractError(f"response loss census mismatch:{ordinal}")

        rows.append(
            {
                "case_id": source_example,
                "ordinal": ordinal,
                "source_example_sha256": source_example,
                "stage_id": stage,
                "scientific_unit_id": identity.get("scientific_unit_id"),
                "tokenization": tokenization,
            }
        )
        response_total += response_count

    if len(rows) != 144 or len(seen_examples) != 144:
        raise AdapterContractError("Analyzer native population drift")
    if response_total != manifest.get("response_loss_token_count_total"):
        raise AdapterContractError("response token total drift")
    return tuple(rows)


def select_longest_record(
    records: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    if not records:
        raise AdapterContractError("empty record set")
    return max(
        records,
        key=lambda row: (
            int(row["tokenization"]["sequence_token_count"]),
            str(row["case_id"]),
        ),
    )
