from pchsi.memory.ledger_common import make_ledger_entry_v1

def make_memory_promotion_entry_v1(
    *,
    decision: str,
    access_scope: str,
    referenced_report_ids: tuple[str, ...],
    **kwargs,
):
    if decision not in {"DESCRIPTIVE_DEV_ALLOWED", "DESCRIPTIVE_DEV_DENIED"}:
        raise ValueError("Package A promotion is descriptive DEV only")
    if access_scope not in {"STAGING_ONLY", "SAME_TASK_DEV_ALLOWED"}:
        raise ValueError("Package A access_scope invalid")
    return make_ledger_entry_v1(
        ledger_kind="MEMORY_PROMOTION_LEDGER_V1",
        event_type=decision,
        payload={
            "decision": decision,
            "access_scope": access_scope,
            "referenced_report_ids": list(referenced_report_ids),
        },
        **kwargs,
    )
