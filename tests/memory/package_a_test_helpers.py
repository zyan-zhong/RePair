from __future__ import annotations

import importlib.util
from pathlib import Path


def load_existing_helpers():
    path = Path("tests/memory/test_procedural_memory_builder.py")
    spec = importlib.util.spec_from_file_location("_package_a_existing_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TinyTokenizer:
    tokenizer_id = "tiny"
    tokenizer_revision = "v1"

    def count_tokens(self, text: str) -> int:
        return 1
