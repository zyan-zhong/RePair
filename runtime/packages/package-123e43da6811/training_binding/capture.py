"""Read the original accepted PRE receipt through exact captured-file aliases.

The original receipt and its domain identity are never rewritten or re-sealed.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath

from .materializer import _read_ref, _verify_seal

RECEIPT_MEMBER = "pre_root/PRE_STRATEGY_RECEIPT.json"
BINDING_MEMBER = "pre_root/PRE_STRATEGY_CAPTURE_BINDING.json"
REF_KEYS = ("accepted_raw_response_ref", "accepted_raw_request_ref", "accepted_pre_ref", "accepted_logical_ref", "accepted_attempt_ref")


def _member(root, value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts or "\\" in value or ":" in value or str(p) != value:
        raise ValueError("PRE_CAPTURE_MEMBER_ESCAPE")
    path = Path(root).resolve() / Path(*p.parts)
    if not path.is_file() or any(x.is_symlink() for x in (path, *path.parents)):
        raise ValueError("PRE_CAPTURE_MEMBER_NOT_REGULAR:" + value)
    return path


@dataclass(frozen=True)
class CapturedPreStrategyReceipt:
    receipt: dict
    aliases: dict
    original_receipt_ref: dict
    binding_ref: dict
    index_ref: dict

    def validate(self):
        _read_ref(self.index_ref); _read_ref(self.binding_ref)
        if json.loads(_read_ref(self.original_receipt_ref)) != self.receipt:
            raise ValueError("PRE_CAPTURE_ORIGINAL_RECEIPT_CHANGED")
        _verify_seal(self.receipt, "pre_strategy_receipt_sha256")
        for key in REF_KEYS: self.read_ref(self.receipt[key])

    def read_ref(self, ref):
        alias = self.aliases.get(ref["path"])
        if alias is None or alias["sha256"] != ref["sha256"]:
            raise ValueError("PRE_CAPTURE_REFERENCE_NOT_BOUND")
        return _read_ref(alias)


def load_captured_pre_strategy_receipt(capture_root):
    root = Path(capture_root).resolve()
    index_path = _member(root, "CAPTURE_INDEX.json")
    index_raw = index_path.read_bytes(); index = json.loads(index_raw)
    if index["schema_id"] != "EXACT_CURRENT_H44_CAPTURE_INDEX_V1_6":
        raise ValueError("PRE_CAPTURE_INDEX_SCHEMA")
    rows = index["files"]; by_name = {row["member"]: row for row in rows}
    if len(by_name) != len(rows): raise ValueError("PRE_CAPTURE_INDEX_DUPLICATE_MEMBER")
    def indexed(name):
        row = by_name[name]; path = _member(root, name)
        raw = _read_ref({"path": str(path), "sha256": row["sha256"]})
        if len(raw) != row["bytes"]: raise ValueError("PRE_CAPTURE_INDEX_SIZE_MISMATCH")
        return raw, {"path": str(path), "sha256": row["sha256"]}
    binding_raw, binding_ref = indexed(BINDING_MEMBER); binding = json.loads(binding_raw)
    if binding["schema_id"] != "CURRENT_PRE_STRATEGY_CAPTURE_BINDING_V1":
        raise ValueError("PRE_CAPTURE_BINDING_SCHEMA")
    receipt_raw, receipt_ref = indexed(RECEIPT_MEMBER)
    if binding["receipt_member"] != RECEIPT_MEMBER or hashlib.sha256(receipt_raw).hexdigest() != binding["receipt_file_sha256"]:
        raise ValueError("PRE_CAPTURE_RECEIPT_FILE_IDENTITY")
    receipt = json.loads(receipt_raw); _verify_seal(receipt, "pre_strategy_receipt_sha256")
    if receipt["pre_strategy_receipt_sha256"] != binding["pre_strategy_receipt_sha256"]:
        raise ValueError("PRE_CAPTURE_RECEIPT_DOMAIN_IDENTITY")
    aliases = {}
    if set(binding["ref_members"]) != set(REF_KEYS): raise ValueError("PRE_CAPTURE_REFERENCE_SET")
    for key in REF_KEYS:
        ref = receipt[key]; mapped = binding["ref_members"][key]
        if mapped["original_path"] != ref["path"] or mapped["sha256"] != ref["sha256"]:
            raise ValueError("PRE_CAPTURE_REFERENCE_IDENTITY")
        _, actual = indexed(mapped["member"])
        if actual["sha256"] != ref["sha256"]: raise ValueError("PRE_CAPTURE_ORIGINAL_BYTES_MISMATCH")
        aliases[ref["path"]] = actual
    _, source_ref = indexed(binding["native_labels_source_seal_member"])
    if source_ref["sha256"] != binding["native_labels_source_seal_sha256"]:
        raise ValueError("PRE_CAPTURE_LABEL_SOURCE_SEAL_IDENTITY")
    result = CapturedPreStrategyReceipt(receipt, aliases, receipt_ref, binding_ref,
        {"path": str(index_path), "sha256": hashlib.sha256(index_raw).hexdigest()})
    result.validate()
    return result
