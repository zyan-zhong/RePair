from pathlib import Path
import hashlib
import json
import zipfile

from stage0.common import (
    atomic_publish_zip,
    canonical_json_bytes,
    domain_sha256,
)


def test_domain_hash_ignores_only_named_hash_field() -> None:
    value = {
        "schema_id": "EXAMPLE_V1",
        "payload": {"x": 1},
        "record_sha256": "",
    }
    observed = domain_sha256(
        value["schema_id"],
        value,
        sha_field="record_sha256",
    )
    assert len(observed) == 64
    value["record_sha256"] = observed
    assert domain_sha256(
        value["schema_id"],
        value,
        sha_field="record_sha256",
    ) == observed


def test_atomic_publish_zip_is_nonempty_crc_valid_and_exact_member_set(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.json").write_bytes(
        canonical_json_bytes({"a": 1})
    )
    (source / "b.txt").write_text("b\n", encoding="utf-8")
    destination = tmp_path / "review.zip"

    result = atomic_publish_zip(
        source_root=source,
        destination=destination,
    )

    assert destination.stat().st_size > 0
    assert result["size_bytes"] == destination.stat().st_size
    assert result["sha256"] == hashlib.sha256(
        destination.read_bytes()
    ).hexdigest()
    assert zipfile.is_zipfile(destination)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert sorted(archive.namelist()) == ["a.json", "b.txt"]
