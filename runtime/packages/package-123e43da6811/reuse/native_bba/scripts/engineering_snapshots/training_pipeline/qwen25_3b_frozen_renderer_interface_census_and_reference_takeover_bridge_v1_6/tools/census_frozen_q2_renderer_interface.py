#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import (
    ContractError,
    finalize,
    load_json_object,
    load_jsonl,
    sha256_file,
    write_new_json,
    write_new_text,
)


SENSITIVE_HINTS = (
    "prompt",
    "input",
    "target",
    "action",
    "message",
    "system",
    "user",
    "assistant",
    "completion",
    "student",
    "teacher",
    "repair",
    "visible",
)


def require_sha(path: Path, expected: str, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"{label}_NOT_REGULAR_FILE:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ContractError(
            f"{label}_SHA_CHANGED:{observed}:{expected}"
        )


def scalar_preview(value: Any, limit: int = 240) -> dict[str, Any]:
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return {
            "type": "str",
            "length": len(value),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "preview": value[:limit],
            "truncated": len(value) > limit,
        }
    if value is None or isinstance(value, (bool, int, float)):
        return {"type": type(value).__name__, "value": value}
    if isinstance(value, list):
        return {"type": "list", "length": len(value)}
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": sorted(value),
            "length": len(value),
        }
    return {"type": type(value).__name__}


def flatten_shape(
    value: Any,
    *,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = 5,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if depth > max_depth:
        return rows
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else key
            child = value[key]
            rows.append(
                {
                    "path": path,
                    "type": type(child).__name__,
                    "length": (
                        len(child)
                        if isinstance(child, (str, list, dict))
                        else None
                    ),
                }
            )
            if isinstance(child, (dict, list)):
                rows.extend(
                    flatten_shape(
                        child,
                        prefix=path,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                )
    elif isinstance(value, list):
        # Shape only the first element to avoid multiplying identical schemas.
        if value:
            path = f"{prefix}[]"
            rows.append(
                {
                    "path": path,
                    "type": type(value[0]).__name__,
                    "length": (
                        len(value[0])
                        if isinstance(value[0], (str, list, dict))
                        else None
                    ),
                }
            )
            if isinstance(value[0], (dict, list)):
                rows.extend(
                    flatten_shape(
                        value[0],
                        prefix=path,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                )
    return rows


def interesting_previews(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    stack: list[tuple[str, Any]] = [("", row)]
    while stack:
        prefix, value = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else key
                if any(hint in key.lower() for hint in SENSITIVE_HINTS):
                    out[path] = scalar_preview(child)
                if isinstance(child, (dict, list)):
                    stack.append((path, child))
        elif isinstance(value, list):
            for idx, child in enumerate(value[:2]):
                if isinstance(child, (dict, list)):
                    stack.append((f"{prefix}[{idx}]", child))
    return dict(sorted(out.items()))


def expr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = expr_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


class MaterializerVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[dict[str, Any]] = []
        self.subscript_keys: list[dict[str, Any]] = []
        self.get_keys: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.string_literals: Counter[str] = Counter()
        self._function_stack: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.functions.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", node.lineno),
                "args": [arg.arg for arg in node.args.args],
            }
        )
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        key = None
        if isinstance(node.slice, ast.Constant) and isinstance(
            node.slice.value, str
        ):
            key = node.slice.value
        if key is not None:
            self.subscript_keys.append(
                {
                    "receiver": expr_name(node.value),
                    "key": key,
                    "lineno": node.lineno,
                    "function": (
                        self._function_stack[-1]
                        if self._function_stack
                        else None
                    ),
                }
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        name = expr_name(node.func)
        self.calls.append(
            {
                "call": name,
                "lineno": node.lineno,
                "function": (
                    self._function_stack[-1]
                    if self._function_stack
                    else None
                ),
            }
        )
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            self.get_keys.append(
                {
                    "receiver": expr_name(node.func.value),
                    "key": node.args[0].value,
                    "lineno": node.lineno,
                    "function": (
                        self._function_stack[-1]
                        if self._function_stack
                        else None
                    ),
                }
            )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, str):
            self.string_literals[node.value] += 1


def relevant_function_names(
    tree: ast.AST,
    source_lines: list[str],
) -> list[str]:
    needles = (
        "apply_chat_template",
        "input_ids",
        "labels",
        "prompt_prefix",
        "tokenizer",
        "messages",
        "assistant",
    )
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        text = "\n".join(source_lines[start:end])
        if any(needle in text for needle in needles):
            names.append(node.name)
    return sorted(set(names))


def source_excerpt(
    tree: ast.AST,
    source_lines: list[str],
    function_names: set[str],
) -> str:
    blocks = []
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in function_names
        ):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)
            blocks.append(
                f"===== FUNCTION {node.name} L{start}-L{end} =====\n"
                + "\n".join(
                    f"{idx:04d}: {source_lines[idx-1]}"
                    for idx in range(start, end + 1)
                )
            )
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    source_path = Path(os.environ["PI1_SOURCE_TRAINING_EXAMPLES_PATH"])
    native_path = Path(
        os.environ["PI1_REFERENCE_MATERIALIZED_EXAMPLES_PATH"]
    )
    materializer_path = Path(os.environ["PI1_ROW_RENDERER_PATH"])
    manifest_path = Path(
        os.environ["PI1_FINAL_MATERIALIZATION_MANIFEST_PATH"]
    )

    require_sha(
        source_path,
        os.environ["EXPECTED_PI1_SOURCE_TRAINING_EXAMPLES_SHA256"],
        "PI1_SOURCE_TRAINING_EXAMPLES",
    )
    require_sha(
        native_path,
        os.environ[
            "EXPECTED_PI1_REFERENCE_MATERIALIZED_EXAMPLES_FILE_SHA256"
        ],
        "PI1_REFERENCE_MATERIALIZED_EXAMPLES",
    )
    require_sha(
        materializer_path,
        os.environ["EXPECTED_PI1_ROW_RENDERER_FILE_SHA256"],
        "PI1_ROW_RENDERER",
    )
    require_sha(
        manifest_path,
        os.environ["EXPECTED_PI1_FINAL_MATERIALIZATION_MANIFEST_SHA256"],
        "PI1_FINAL_MATERIALIZATION_MANIFEST",
    )

    source_rows = load_jsonl(source_path)
    native_rows = load_jsonl(native_path)
    manifest = load_json_object(manifest_path)

    if len(source_rows) != 84 or len(native_rows) != 84:
        raise ContractError(
            f"FROZEN_ORACLE_POPULATION_CHANGED:"
            f"{len(source_rows)}:{len(native_rows)}"
        )

    common_keys = sorted(
        set.intersection(*(set(row) for row in source_rows))
    )
    union_keys = sorted(
        set.union(*(set(row) for row in source_rows))
    )
    schema_counts = Counter(
        str(row.get("schema_id")) for row in source_rows
    )
    if schema_counts != Counter(
        {"D_Q2_BAD_V1_TRAINING_EXAMPLE": 84}
    ):
        raise ContractError(
            "FROZEN_Q2_SCHEMA_DISTRIBUTION_CHANGED:"
            + repr(dict(schema_counts))
        )

    native_common_keys = sorted(
        set.intersection(*(set(row) for row in native_rows))
    )
    native_union_keys = sorted(
        set.union(*(set(row) for row in native_rows))
    )

    source = materializer_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ContractError(
            f"MATERIALIZER_AST_PARSE_FAILED:{exc.lineno}"
        ) from exc
    visitor = MaterializerVisitor()
    visitor.visit(tree)
    lines = source.splitlines()
    relevant_names = relevant_function_names(tree, lines)
    excerpt = source_excerpt(tree, lines, set(relevant_names))

    # Receiver->key summaries are useful to distinguish source schema from
    # intermediate message objects without executing the old materializer.
    get_by_receiver: dict[str, set[str]] = defaultdict(set)
    sub_by_receiver: dict[str, set[str]] = defaultdict(set)
    for row in visitor.get_keys:
        get_by_receiver[row["receiver"]].add(row["key"])
    for row in visitor.subscript_keys:
        sub_by_receiver[row["receiver"]].add(row["key"])

    first_source_shape = flatten_shape(source_rows[0])
    first_native_shape = flatten_shape(native_rows[0])

    census = finalize(
        "FROZEN_Q2_RENDERER_INTERFACE_CENSUS_V1",
        "renderer_interface_census_sha256",
        {
            "schema_id": "FROZEN_Q2_RENDERER_INTERFACE_CENSUS_V1",
            "schema_version": 1,
            "source_training_examples_path": str(source_path.resolve()),
            "source_training_examples_file_sha256": sha256_file(
                source_path
            ),
            "source_training_example_count": len(source_rows),
            "source_schema_id_counts": dict(sorted(schema_counts.items())),
            "source_common_top_level_keys": common_keys,
            "source_union_top_level_keys": union_keys,
            "source_has_top_level_messages": "messages" in common_keys,
            "source_first_three_shapes": [
                flatten_shape(row) for row in source_rows[:3]
            ],
            "source_first_three_interesting_previews": [
                interesting_previews(row) for row in source_rows[:3]
            ],
            "native_materialized_examples_path": str(native_path.resolve()),
            "native_materialized_examples_file_sha256": sha256_file(
                native_path
            ),
            "native_materialized_example_count": len(native_rows),
            "native_common_top_level_keys": native_common_keys,
            "native_union_top_level_keys": native_union_keys,
            "native_first_row_shape": first_native_shape,
            "native_first_three_interesting_previews": [
                interesting_previews(row) for row in native_rows[:3]
            ],
            "final_materialization_manifest_path": str(
                manifest_path.resolve()
            ),
            "final_materialization_manifest_file_sha256": sha256_file(
                manifest_path
            ),
            "final_materialization_manifest_hot": {
                key: manifest.get(key)
                for key in (
                    "sample_count",
                    "sequence_token_count_min",
                    "sequence_token_count_max",
                    "completion_loss_token_count_min",
                    "completion_loss_token_count_max",
                    "one_pass_target_loss_token_count",
                    "recommended_no_truncation_sequence_ceiling",
                    "loss_definition",
                    "prompt_label_value",
                    "packing_applied",
                    "truncation_applied",
                    "base_model_repository",
                    "base_model_revision",
                    "tokenizer_bundle_sha256",
                    "chat_template_sha256",
                    "render_reproduction",
                )
            },
            "materializer_path": str(materializer_path.resolve()),
            "materializer_file_sha256": sha256_file(materializer_path),
            "materializer_function_inventory": visitor.functions,
            "materializer_relevant_function_names": relevant_names,
            "materializer_get_key_accesses": visitor.get_keys,
            "materializer_subscript_key_accesses": visitor.subscript_keys,
            "materializer_get_keys_by_receiver": {
                receiver: sorted(keys)
                for receiver, keys in sorted(get_by_receiver.items())
            },
            "materializer_subscript_keys_by_receiver": {
                receiver: sorted(keys)
                for receiver, keys in sorted(sub_by_receiver.items())
            },
            "materializer_relevant_calls": [
                row
                for row in visitor.calls
                if any(
                    needle in row["call"]
                    for needle in (
                        "apply_chat_template",
                        "encode",
                        "tokenizer",
                        "json.dumps",
                        "json.loads",
                    )
                )
            ],
            "materializer_contains_messages_literal": (
                "messages" in visitor.string_literals
            ),
            "materializer_source_executed": False,
            "model_execution_count": 0,
            "environment_execution_count": 0,
            "training_execution_count": 0,
            "adapter_implementation_ready": False,
            "next_gate": (
                "BUILD_EXACT_SCHEMA_AWARE_RENDERER_ADAPTER_FROM_CENSUS"
            ),
        },
    )

    out = Path(os.environ["CENSUS_ROOT"])
    out.mkdir(parents=True, exist_ok=False)
    write_new_json(
        out / "FROZEN_Q2_RENDERER_INTERFACE_CENSUS_V1.json",
        census,
    )
    write_new_text(
        out / "MATERIALIZER_RELEVANT_SOURCE_EXCERPTS_V1.txt",
        excerpt,
    )

    print("FROZEN_Q2_RENDERER_INTERFACE_CENSUS_PASS")
    print(
        "RENDERER_INTERFACE_CENSUS_SHA256="
        + census["renderer_interface_census_sha256"]
    )
    print("SOURCE_TRAINING_EXAMPLE_COUNT=84")
    print(
        "SOURCE_SCHEMA_ID_COUNTS="
        + repr(dict(sorted(schema_counts.items())))
    )
    print(
        "SOURCE_TOP_LEVEL_KEYS="
        + repr(common_keys)
    )
    print(
        "SOURCE_HAS_TOP_LEVEL_MESSAGES="
        + str("messages" in common_keys).lower()
    )
    print(
        "NATIVE_TOP_LEVEL_KEYS="
        + repr(native_common_keys)
    )
    print(
        "MATERIALIZER_FUNCTIONS="
        + repr([row["name"] for row in visitor.functions])
    )
    print(
        "MATERIALIZER_RELEVANT_FUNCTIONS="
        + repr(relevant_names)
    )
    print(
        "MATERIALIZER_GET_KEYS_BY_RECEIVER="
        + repr(
            {
                receiver: sorted(keys)
                for receiver, keys in sorted(get_by_receiver.items())
            }
        )
    )
    print(
        "MATERIALIZER_SUBSCRIPT_KEYS_BY_RECEIVER="
        + repr(
            {
                receiver: sorted(keys)
                for receiver, keys in sorted(sub_by_receiver.items())
            }
        )
    )
    print(
        "MATERIALIZER_RELEVANT_CALLS="
        + repr(
            [
                (row["call"], row["lineno"], row["function"])
                for row in census["materializer_relevant_calls"]
            ]
        )
    )
    for idx, previews in enumerate(
        census["source_first_three_interesting_previews"]
    ):
        print(
            f"SOURCE_ROW_{idx}_INTERESTING_PREVIEWS="
            + json.dumps(
                previews,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    print(
        "MATERIALIZER_EXCERPT_PATH="
        + str(
            (
                out
                / "MATERIALIZER_RELEVANT_SOURCE_EXCERPTS_V1.txt"
            ).resolve()
        )
    )
    print("MATERIALIZER_SOURCE_EXECUTED=false")
    print("ADAPTER_IMPLEMENTATION_READY=false")
    print(
        "NEXT_GATE="
        "BUILD_EXACT_SCHEMA_AWARE_RENDERER_ADAPTER_FROM_CENSUS"
    )
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
