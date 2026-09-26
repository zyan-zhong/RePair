from __future__ import annotations
from pathlib import Path
from collections.abc import Mapping
import time
from pchsi.reference_loop.canonical import write_new_json, write_new_text, sha256_bytes


def create_call_directory(root: Path, logical_call_id: str) -> Path:
    path=root/logical_call_id
    path.mkdir(parents=True,exist_ok=False)
    return path


def record_rendered_request(call_dir: Path, bundle: Mapping[str,object]) -> None:
    write_new_json(call_dir/"rendered_request.json",dict(bundle))


def record_raw_request(call_dir: Path, raw: bytes) -> str:
    path=call_dir/"raw_request.json"
    if path.exists(): raise FileExistsError(path)
    path.write_bytes(raw)
    return sha256_bytes(raw)


def record_raw_response(call_dir: Path, raw: bytes) -> str:
    path=call_dir/"raw_response.json"
    if path.exists(): raise FileExistsError(path)
    path.write_bytes(raw)
    return sha256_bytes(raw)


def monotonic_ms() -> float:
    return time.monotonic_ns()/1_000_000
