#!/usr/bin/env python3
"""Validate one raw Analyzer JSON output and publish immutable receipts."""

from __future__ import annotations
import argparse, hashlib
from pathlib import Path

from pchsi.analyzer.local_results import finalize_local_result, validate_local_result
from pchsi.reference_loop.canonical import strict_json_loads, write_new_json


def _object(path: Path) -> dict[str, object]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict): raise ValueError(f"input must be object: {path}")
    return value


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--raw-response",required=True)
    parser.add_argument("--evidence-pack",required=True)
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    raw_path=Path(args.raw_response).resolve()
    out=Path(args.output_dir).resolve()
    out.mkdir(parents=True,exist_ok=False)
    raw=raw_path.read_bytes(); raw_sha=hashlib.sha256(raw).hexdigest()
    write_new_json(out/"raw_response.json",{
        "schema_id":"ANALYZER_RAW_RESPONSE_EVIDENCE_V1",
        "raw_response_sha256":raw_sha,
        "raw_response_utf8":raw.decode("utf-8",errors="strict"),
    })
    try:
        payload=strict_json_loads(raw)
        if not isinstance(payload,dict): raise ValueError("response must be object")
        embedded=payload.get("raw_response_sha256")
        if embedded not in (None,"0"*64,raw_sha):
            raise ValueError("raw response SHA binding mismatch")
        payload["raw_response_sha256"]=raw_sha
        value=validate_local_result(
            finalize_local_result(payload),
            evidence_pack=_object(Path(args.evidence_pack)),
        )
    except Exception as error:
        write_new_json(out/"validation_receipt.json",{
            "schema_id":"ANALYZER_VALIDATION_RECEIPT_V1","accepted":False,
            "raw_response_sha256":raw_sha,"error_type":type(error).__name__,
            "error_message":str(error),
        })
        return 2
    write_new_json(out/"validation_receipt.json",{
        "schema_id":"ANALYZER_VALIDATION_RECEIPT_V1","accepted":True,
        "raw_response_sha256":raw_sha,
        "validated_result_sha256":value["validated_result_sha256"],
        "local_result_sha256":value["local_result_sha256"],
    })
    write_new_json(out/"validated_result.json",value)
    return 0


if __name__=="__main__": raise SystemExit(main())
