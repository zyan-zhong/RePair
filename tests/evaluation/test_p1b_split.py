import pytest
from pchsi.evaluation.distillation_access import HistoricalAccessAuditRecordV1,HistoricalAccessAuditV1,HistoricalAccessFlag,DistillationAccessClass
from pchsi.evaluation.p1b_split import P1_B_SPLIT_SALT,P1BSplitInfeasibleError,assign_p1b_access,select_target,split_key_sha256
from pchsi.evaluation.canonical_evidence import canonical_json_bytes,sha256_bytes
from pchsi.evaluation.task_manifest import FrozenTaskRecord

def records(n=6):
    out=[]
    for i in range(n):
        tid=f"alfworld_valid_unseen_all134_{i:04d}"; root=f"/d/{tid}"
        out.append(FrozenTaskRecord(i,tid,"valid_unseen","family",f"{root}/game.tw-pddl",f"{i+1:040x}",root,f"{root}/traj_data.json"))
    return tuple(out)

def audit(rs, forced=()):
    rows=[]
    for r in rs:
        flags=(HistoricalAccessFlag.USED_FOR_METHOD_DESIGN,) if r.index in forced else (HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,)
        rows.append(HistoricalAccessAuditRecordV1(r.task_id,r.gamefile,r.split,None,flags,(f"e:{r.index}",)))
    return HistoricalAccessAuditV1("DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1",1,"audit","json_2.1.1",len(rows),tuple(rows))

def test_split_key_matches_formula():
    r=records()[3]
    expected=sha256_bytes(canonical_json_bytes({"schema_id":"P1_B_TASK_SPLIT_KEY_V1","salt":P1_B_SPLIT_SALT,"task_type":r.task_type,"task_id":r.task_id,"gamefile_sha1":r.gamefile_sha1}))
    assert split_key_sha256(r)==expected

def test_select_target():
    assert select_target(2)==1 and select_target(3)==1 and select_target(8)==2 and select_target(12)==4

def test_forced_dev_requires_evidence_and_is_dev():
    rs=records(); a=audit(rs,forced=(2,))
    with pytest.raises(ValueError,match="forced DEV evidence"):
        assign_p1b_access(records=rs,audit=a,forced_dev_evidence={})
    proof=assign_p1b_access(records=rs,audit=a,forced_dev_evidence={rs[2].task_id:("e:2",)})
    row=proof.assignment_for(2)
    assert row.forced_dev and row.final_access_class is DistillationAccessClass.DEV_VISIBLE
    assert row.forced_dev_evidence_sources==("e:2",)

def test_split_infeasible_when_all_forced():
    rs=records(3); a=audit(rs,forced=(0,1,2)); ev={r.task_id:(f"e:{r.index}",) for r in rs}
    with pytest.raises(P1BSplitInfeasibleError): assign_p1b_access(records=rs,audit=a,forced_dev_evidence=ev)
def test_select_quota_uses_eligible_pool_after_forced_dev():
    rs = records(24)
    forced = tuple(range(18))
    a = audit(rs, forced=forced)
    ev = {
        r.task_id: (f"e:{r.index}",)
        for r in rs
        if r.index in forced
    }

    proof = assign_p1b_access(
        records=rs,
        audit=a,
        forced_dev_evidence=ev,
    )

    select_rows = [
        row
        for row in proof.records
        if row.final_access_class
        is DistillationAccessClass.SELECT_SUMMARY_ONLY
    ]

    assert len(select_rows) == 2
    assert {
        row.family_select_target
        for row in proof.records
    } == {2}


def test_single_eligible_task_gets_one_select():
    rs = records(17)
    forced = tuple(range(16))
    a = audit(rs, forced=forced)
    ev = {
        r.task_id: (f"e:{r.index}",)
        for r in rs
        if r.index in forced
    }

    proof = assign_p1b_access(
        records=rs,
        audit=a,
        forced_dev_evidence=ev,
    )

    select_rows = [
        row
        for row in proof.records
        if row.final_access_class
        is DistillationAccessClass.SELECT_SUMMARY_ONLY
    ]

    assert len(select_rows) == 1
    assert select_rows[0].family_select_target == 1


def test_all_forced_uses_specific_no_eligible_error():
    rs = records(3)
    forced = tuple(range(3))
    a = audit(rs, forced=forced)
    ev = {
        r.task_id: (f"e:{r.index}",)
        for r in rs
    }

    with pytest.raises(
        P1BSplitInfeasibleError,
        match=(
            "P1_B_SPLIT_INFEASIBLE_NO_ELIGIBLE_SELECT"
        ),
    ):
        assign_p1b_access(
            records=rs,
            audit=a,
            forced_dev_evidence=ev,
        )


def test_split_contract_uses_eligible_pool_rule():
    from pchsi.evaluation.p1b_split import (
        P1BSplitContractV1,
    )

    assert (
        P1BSplitContractV1().family_rule
        ==
        "E_f=N_f-F_f; require E_f>0; "
        "SELECT_TARGET=max(1,floor(E_f/3))"
    )
