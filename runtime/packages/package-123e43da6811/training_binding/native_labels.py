"""Call the registered Stage6AN renderer/masker; never generate strategy text."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from .materializer import _read_ref, _sha


@dataclass(frozen=True)
class NativeLabels:
    tools_root: Path
    source_sha256s: dict[str, str]
    common: Any
    adapter: Any

    @classmethod
    def load(cls, tools_root: Path, source_sha256s: dict[str, str]):
        root = Path(tools_root).resolve()
        names = ("common", "renderer_adapter_core", "strategy_dual_view_adapter")
        previous = {name: sys.modules.get(name) for name in names}
        modules = {}
        try:
            for name in names:
                path = root / (name + ".py")
                _read_ref({"path": str(path), "sha256": source_sha256s.get(path.name)})
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                modules[name] = module
        finally:
            for name in names:
                if previous[name] is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous[name]
        return cls(root, dict(source_sha256s), modules["common"], modules["strategy_dual_view_adapter"])

    def materialize(self, *, verified_rows: list[dict], tokenizer: Any, output_root: Path,
                    verifier_result_sha256: str, verified_benefit_state_sha256s: list[str]) -> dict:
        """The caller supplies verified strategies preserving repair identity.

        All native content validation, strategy hashing, I1 rendering, masking
        and pair census are performed by the original Stage6AN functions.
        The native contract does not require the JSON file to predate F0/F1.
        Its content must preserve the verified repair; this adapter cannot
        establish a missing source mapping or invent a short-option target.
        """
        for name, expected in self.source_sha256s.items():
            _read_ref({"path": str(self.tools_root / name), "sha256": expected})
        _sha(verifier_result_sha256, "VERIFIER")
        eligible = {_sha(value, "BENEFIT_STATE") for value in verified_benefit_state_sha256s}
        if not verified_rows:
            raise ValueError("VERIFIED_STRATEGY_INPUT_EMPTY")
        seen, pairs, native_rows, materialized = set(), [], [], []
        for index, row in enumerate(verified_rows):
            state = row["source_state_sha256"]
            if state not in eligible or state in seen:
                raise ValueError("NON_CURRENT_OR_DUPLICATE_VERIFIED_STRATEGY_STATE")
            seen.add(state)
            if row["verification"]["verification_receipt_sha256"] != verifier_result_sha256:
                raise ValueError("STRATEGY_CURRENT_VERIFIER_BINDING_MISMATCH")
            pair = self.adapter.build_strategy_dual_view_pair(row, index)
            result = self.adapter.materialize_dual_view_native_pair(pair=pair, tokenizer=tokenizer, ordinal_base=index * 2)
            pairs.append(pair)
            native_rows.extend((result["execution_native_row"], result["strategy_native_row"]))
            materialized.append(result)
        census = self.adapter.summarize_native_label_census(materialized)
        root = Path(output_root).resolve()
        input_path = root / "VERIFIED_POLICY_STRATEGY_MATERIALIZATION_INPUT_V1.jsonl"
        source_path = root / "POLICY_STRATEGY_DUAL_VIEW_SOURCE_V1.jsonl"
        native_path = root / "POLICY_STRATEGY_DUAL_VIEW_NATIVE_V1.jsonl"
        census_path = root / "STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1.json"
        cb = self.common.canonical_json_bytes
        input_bytes = b"".join(cb(row) for row in verified_rows)
        source_bytes = b"".join(cb(row) for row in pairs)
        native_bytes = b"".join(cb(row) for row in native_rows)
        sha = lambda raw: hashlib.sha256(raw).hexdigest()
        census_authority = self.common.finalize("STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1", "census_sha256", {
            "schema_id": "STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1", "schema_version": 1, **census,
            "source_input_path": str(input_path), "source_input_sha256": sha(input_bytes),
            "source_pair_path": str(source_path), "source_pair_sha256": sha(source_bytes),
            "native_dataset_path": str(native_path), "native_dataset_sha256": sha(native_bytes),
            "native_example_count": len(native_rows), "views_per_strategy_row": 2,
            "execution_view_semantics": "EXACT_I1_ACTION_ONLY",
            "strategy_view_semantics": "TRAINING_ONLY_COMPACT_STRATEGY_WITH_ACTION",
            "deployment_i1_parser_changed": False, "future_outcome_visible_to_policy": False,
            "training_token_fairness_required_for_ablation": True,
            "task_policy_optimizer_execution_authorized": False, "training_execution_count": 0,
        })
        outputs = {input_path: input_bytes, source_path: source_bytes, native_path: native_bytes, census_path: cb(census_authority)}
        for path, raw in outputs.items():
            if path.exists() and (path.is_symlink() or path.read_bytes() != raw):
                raise ValueError("NATIVE_LABEL_EXISTING_OUTPUT_CONFLICT:" + str(path))
        root.mkdir(parents=True, exist_ok=True)
        for path, raw in outputs.items():
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(raw)
        return {"dataset_ref": {"path": str(native_path), "sha256": sha(native_bytes)},
                "dataset_manifest_ref": {"path": str(census_path), "sha256": sha(outputs[census_path])},
                "manifest_domain_sha_field": "census_sha256", "census": census_authority,
                "recipe_context": {"dataset_sha256": sha(native_bytes), "row_count": len(native_rows)},
                "training_execution_count": 0}
