from pathlib import Path
import pytest
from pchsi.memory.ledger_common import append_ledger_entry_v1, read_ledger_v1
from pchsi.memory.event_ledger import make_memory_event_entry_v1
from pchsi.memory.effect_ledger import make_memory_effect_entry_v1

def _base():
    return dict(
        ledger_id="ledger", entry_id="e1", event_type="EVENT",
        memory_lineage_id="a"*64, record_version=1,
        event_time_utc="2026-08-18T12:00:00Z",
        repository_commit="b"*40, previous_entry_sha256=None,
    )

def test_package_a_effect_closed_and_append_chain(tmp_path):
    base = _base()
    with pytest.raises(ValueError):
        make_memory_effect_entry_v1(
            ledger_id="x", entry_id="x", memory_lineage_id="a"*64,
            record_version=1, event_time_utc="2026-08-18T12:00:00Z",
            repository_commit="b"*40, previous_entry_sha256=None,
            effect_status="POSITIVE", effect_evidence_scope="SOURCE_STATE_PAIRED",
            evidence_ids=("x",),
        )
    first = make_memory_event_entry_v1(details={"x":1}, **base)
    path = tmp_path/"ledger.jsonl"
    append_ledger_entry_v1(path, first)
    assert read_ledger_v1(path) == (first,)
