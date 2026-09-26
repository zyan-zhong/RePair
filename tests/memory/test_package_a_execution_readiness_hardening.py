from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import (
    sha256_bytes,
)
from pchsi.memory import ledger_common
from pchsi.memory.dev_descriptive_snapshot import (
    MemoryDevDescriptiveSnapshotMemberV1,
    MemoryDevDescriptiveSnapshotV1,
    publish_memory_dev_descriptive_snapshot_v1,
)
from pchsi.memory.memory_execution_identity import (
    MemoryBoundReplayPairV1,
    build_memory_bound_replay_pair_v1,
)
from pchsi.memory.source_state_contracts import (
    build_source_decision_state_fingerprint_v1,
)


def _load_script(
    path: str,
    name: str,
):
    spec = importlib.util.spec_from_file_location(
        name,
        Path(path),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(
    path: Path,
    payload: object,
) -> str:
    raw = (
        __import__("json")
        .dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        .encode("utf-8")
    )
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_ledger_partial_write_is_fully_drained(
    tmp_path,
    monkeypatch,
):
    original_write = ledger_common.os.write
    call_count = 0

    def partial_write(fd, data):
        nonlocal call_count
        call_count += 1
        chunk = bytes(data[:7])
        return original_write(fd, chunk)

    monkeypatch.setattr(
        ledger_common.os,
        "write",
        partial_write,
    )

    entry = ledger_common.make_ledger_entry_v1(
        ledger_id="ledger",
        ledger_kind="MEMORY_EVENT_LEDGER_V1",
        entry_id="entry",
        event_type="AUDIT",
        memory_lineage_id="a" * 64,
        record_version=1,
        event_time_utc="2026-08-18T00:00:00Z",
        repository_commit="b" * 40,
        payload={"audit": True},
        previous_entry_sha256=None,
    )

    path = tmp_path / "ledger.jsonl"
    ledger_common.append_ledger_entry_v1(
        path,
        entry,
    )

    assert call_count > 1
    assert ledger_common.read_ledger_v1(
        path
    ) == (entry,)


def test_paired_execution_identity_round_trips():
    fingerprint = (
        build_source_decision_state_fingerprint_v1(
            source_task_id="task",
            source_gamefile_sha256="a" * 64,
            source_bundle_sha256="b" * 64,
            source_policy_condition="condition",
            executed_prefix_sha256="c" * 64,
            observation_sha256="d" * 64,
            menu_sequence_sha256="e" * 64,
            memory_m0_sha256="f" * 64,
            interface_feedback_code=None,
            budget_state=BudgetState(
                policy_attempt_count=1,
                environment_step_count=1,
            ),
            model_call_index=1,
            base_policy_input_sha256="1" * 64,
        )
    )

    pair = build_memory_bound_replay_pair_v1(
        source_fingerprint=fingerprint,
        policy_checkpoint_id="policy-1",
        memory_snapshot_id="2" * 64,
        memory_on_projection_sha256s=(
            "3" * 64,
        ),
        continuation_seed=17,
    )

    raw = pair.canonical_bytes()
    rebuilt = MemoryBoundReplayPairV1.from_json(
        raw
    )

    assert rebuilt == pair
    assert rebuilt.canonical_bytes() == raw


def test_materialize_cli_rejects_wrong_authority_before_tokenizer(
    tmp_path,
    monkeypatch,
):
    module = _load_script(
        "scripts/memory/materialize_failure_memory_candidates_v1.py",
        "_hardening_materialize_cli",
    )

    manifest = tmp_path / "manifest.json"
    manifest_sha = _write_json(
        manifest,
        {
            "authority_commit": "0" * 40,
            "tokenizer_id": "unused",
            "tokenizer_revision": "unused",
            "tokenizer_local_path": str(
                tmp_path / "missing-tokenizer"
            ),
            "items": [],
        },
    )

    class ForbiddenTokenizer:
        def __init__(self, *args, **kwargs):
            raise AssertionError(
                "tokenizer loaded before authority check"
            )

    monkeypatch.setattr(
        module,
        "LocalTokenizerCounter",
        ForbiddenTokenizer,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "materialize",
            "--manifest",
            str(manifest),
            "--manifest-sha256",
            manifest_sha,
        ],
    )

    with pytest.raises(
        SystemExit,
        match=(
            "STOP=MATERIALIZATION_"
            "AUTHORITY_COMMIT_MISMATCH"
        ),
    ):
        module.main()


def test_replay_cli_rejects_wrong_authority(
    tmp_path,
    monkeypatch,
):
    module = _load_script(
        "scripts/memory/qualify_source_state_replay_v1.py",
        "_hardening_replay_cli",
    )

    manifest = tmp_path / "manifest.json"
    manifest_sha = _write_json(
        manifest,
        {
            "authority_commit": "0" * 40,
            "cases": [],
        },
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "replay",
            "--manifest",
            str(manifest),
            "--manifest-sha256",
            manifest_sha,
        ],
    )

    with pytest.raises(
        SystemExit,
        match=(
            "STOP=REPLAY_"
            "AUTHORITY_COMMIT_MISMATCH"
        ),
    ):
        module.main()


def test_snapshot_cli_rejects_wrong_authority(
    tmp_path,
    monkeypatch,
):
    module = _load_script(
        "scripts/memory/build_failure_memory_dev_snapshot_v1.py",
        "_hardening_snapshot_cli",
    )

    manifest = tmp_path / "manifest.json"
    manifest_sha = _write_json(
        manifest,
        {
            "authority_commit": "0" * 40,
            "tokenizer_id": "unused",
            "tokenizer_revision": "unused",
            "items": [],
        },
    )

    candidate_root = tmp_path / "candidates"
    snapshot_root = tmp_path / "snapshots"
    candidate_root.mkdir()
    snapshot_root.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "snapshot",
            "--manifest",
            str(manifest),
            "--manifest-sha256",
            manifest_sha,
            "--candidate-root",
            str(candidate_root),
            "--snapshot-root",
            str(snapshot_root),
        ],
    )

    with pytest.raises(
        SystemExit,
        match=(
            "STOP=SNAPSHOT_"
            "AUTHORITY_COMMIT_MISMATCH"
        ),
    ):
        module.main()


def _fake_snapshot():
    files = {
        "governed_record.json": b"governed\n",
        "retrieval_key.json": b"key\n",
        "fm1.json": b"fm1\n",
        "fm2.json": b"fm2\n",
    }
    member = (
        MemoryDevDescriptiveSnapshotMemberV1(
            memory_lineage_id="a" * 64,
            record_version=2,
            governed_record_sha256=sha256_bytes(
                files["governed_record.json"]
            ),
            retrieval_key_sha256=sha256_bytes(
                files["retrieval_key.json"]
            ),
            fm1_sha256=sha256_bytes(
                files["fm1.json"]
            ),
            fm2_sha256=sha256_bytes(
                files["fm2.json"]
            ),
            relative_directory=(
                "members/"
                + "a" * 64
                + ".v2"
            ),
        )
    )
    snapshot = MemoryDevDescriptiveSnapshotV1(
        source_materialization_manifest_sha256=(
            "b" * 64
        ),
        tokenizer_id="tokenizer",
        tokenizer_revision="revision",
        members=(member,),
    )
    return snapshot, {
        member.relative_directory: files
    }


def test_snapshot_publication_has_rehash_audit(
    tmp_path,
):
    module = importlib.import_module(
        "pchsi.memory.dev_descriptive_snapshot"
    )
    auditor = getattr(
        module,
        "audit_memory_dev_descriptive_snapshot_v1",
        None,
    )
    assert callable(auditor)

    snapshot, member_files = _fake_snapshot()
    root = tmp_path / "snapshots"
    root.mkdir()

    final = publish_memory_dev_descriptive_snapshot_v1(
        output_root=root,
        snapshot=snapshot,
        member_files=member_files,
    )

    assert (
        final / "snapshot_files.json"
    ).is_file()
    assert (
        final / "snapshot_files.sha256"
    ).is_file()

    rebuilt = auditor(
        snapshot_directory=final,
        expected_snapshot_sha256=(
            snapshot.snapshot_sha256
        ),
    )
    assert rebuilt == snapshot

    fm2 = (
        final
        / snapshot.members[0].relative_directory
        / "fm2.json"
    )
    fm2.write_bytes(b"tampered\n")

    with pytest.raises(
        ValueError,
        match="SHA mismatch",
    ):
        auditor(
            snapshot_directory=final,
            expected_snapshot_sha256=(
                snapshot.snapshot_sha256
            ),
        )


def test_package_a_materialization_ledger_set_is_complete(
    tmp_path,
):
    try:
        execution_ledgers = (
            importlib.import_module(
                "pchsi.memory.package_a_execution_ledgers"
            )
        )
    except ModuleNotFoundError:
        pytest.fail(
            "PACKAGE_A_EXECUTION_LEDGERS_MISSING"
        )

    a6 = _load_script(
        "tests/memory/test_package_a_a6_candidate_materialization.py",
        "_hardening_a6_helpers",
    )
    helpers = a6._helpers()
    existing = helpers.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()

    assembly = a6._safe_assembly(
        existing,
        builder_module,
        experience,
    )
    item = a6._item_from_assembly(
        tmp_path=tmp_path,
        experience=experience,
        assembly=assembly,
    )

    candidate_root = tmp_path / "candidates"
    candidate_root.mkdir()

    (
        initial_record,
        source_report,
        bundle,
        _,
    ) = (
        __import__(
            "pchsi.memory.candidate_materialization",
            fromlist=["materialize_candidate_item_v1"],
        )
        .materialize_candidate_item_v1(
            item=item,
            tokenizer=helpers.TinyTokenizer(),
            output_root=candidate_root,
            execute=True,
        )
    )

    ledger_root = tmp_path / "ledgers"
    ledger_root.mkdir()

    final = (
        execution_ledgers
        .write_package_a_materialization_ledgers_v1(
            ledger_root=ledger_root,
            candidate_id=item.candidate_id,
            initial_record=initial_record,
            source_report=source_report,
            eligibility_bundle=bundle,
            event_time_utc=(
                "2026-08-18T00:00:00Z"
            ),
            repository_commit="b" * 40,
        )
    )

    expected = {
        "memory_event_ledger.jsonl",
        "memory_record_effect_ledger.jsonl",
        "memory_promotion_ledger.jsonl",
        "memory_exposure_ledger.jsonl",
        "ledger_set.json",
        "ledger_set.sha256",
    }
    observed = {
        path.name
        for path in final.iterdir()
        if path.is_file()
    }
    assert observed == expected

    for name in (
        "memory_event_ledger.jsonl",
        "memory_record_effect_ledger.jsonl",
        "memory_promotion_ledger.jsonl",
        "memory_exposure_ledger.jsonl",
    ):
        assert len(
            ledger_common.read_ledger_v1(
                final / name
            )
        ) == 1


def test_materialization_cli_wires_all_four_ledgers():
    text = Path(
        "scripts/memory/"
        "materialize_failure_memory_candidates_v1.py"
    ).read_text(encoding="utf-8")

    assert (
        "write_package_a_materialization_ledgers_v1"
        in text
    )

    for marker in (
        "MEMORY_EVENT_LEDGER_V1",
        "MEMORY_RECORD_EFFECT_LEDGER_V1",
        "MEMORY_PROMOTION_LEDGER_V1",
        "MEMORY_EXPOSURE_LEDGER_V1",
    ):
        assert marker in text
