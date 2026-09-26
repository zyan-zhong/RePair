from pchsi.memory.ledger_common import make_ledger_entry_v1

def make_memory_exposure_entry_v1(*, exposure_status: str, **kwargs):
    if exposure_status != "NOT_EXPOSED_PACKAGE_A":
        raise ValueError("Package A forbids Policy Memory exposure")
    return make_ledger_entry_v1(
        ledger_kind="MEMORY_EXPOSURE_LEDGER_V1",
        event_type="NOT_EXPOSED_PACKAGE_A",
        payload={"exposure_status": exposure_status, "projection_ids": []},
        **kwargs,
    )
