from pchsi.memory.ledger_common import make_ledger_entry_v1

def make_memory_effect_entry_v1(
    *,
    effect_status: str,
    effect_evidence_scope: str,
    evidence_ids: tuple[str, ...],
    **kwargs,
):
    if effect_status != "UNTESTED" or effect_evidence_scope != "UNTESTED":
        raise ValueError("Package A effect authority must remain UNTESTED")
    if evidence_ids:
        raise ValueError("UNTESTED effect must not cite effect evidence")
    return make_ledger_entry_v1(
        ledger_kind="MEMORY_RECORD_EFFECT_LEDGER_V1",
        event_type="MEMORY_EFFECT_UNTESTED",
        payload={
            "effect_status": "UNTESTED",
            "effect_evidence_scope": "UNTESTED",
            "evidence_ids": [],
        },
        **kwargs,
    )
