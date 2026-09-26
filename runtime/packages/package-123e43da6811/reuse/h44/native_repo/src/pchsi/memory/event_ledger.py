from pchsi.memory.ledger_common import make_ledger_entry_v1

def make_memory_event_entry_v1(**kwargs):
    details = kwargs.pop("details")
    return make_ledger_entry_v1(
        ledger_kind="MEMORY_EVENT_LEDGER_V1",
        payload={"details": details},
        **kwargs,
    )
