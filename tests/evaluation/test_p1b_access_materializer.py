from pchsi.evaluation.distillation_access import HistoricalAccessAuditRecordV1,HistoricalAccessAuditV1,HistoricalAccessFlag,DistillationAccessClass
from pchsi.evaluation.p1b_split import assign_p1b_access
from pchsi.evaluation.p1b_access_materializer import materialize_task_access_manifest
from pchsi.evaluation.task_manifest import FrozenTaskRecord

def fixtures():
    rs=[]; rows=[]
    for i in range(6):
        tid=f"alfworld_valid_unseen_all134_{i:04d}"; root=f"/d/{tid}"
        r=FrozenTaskRecord(i,tid,"valid_unseen","family",f"{root}/game.tw-pddl",f"{i+1:040x}",root,f"{root}/traj_data.json"); rs.append(r)
        rows.append(HistoricalAccessAuditRecordV1(r.task_id,r.gamefile,r.split,None,(HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,),(f"e:{i}",)))
    audit=HistoricalAccessAuditV1("DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1",1,"audit","json_2.1.1",6,tuple(rows))
    proof=assign_p1b_access(records=tuple(rs),audit=audit,forced_dev_evidence={})
    shas={r.task_id:f"{100+i:064x}" for i,r in enumerate(rs)}
    return tuple(rs),audit,proof,shas

def test_materialized_permissions_exact():
    rs,a,p,s=fixtures(); m=materialize_task_access_manifest(records=rs,audit=a,split_proof=p,gamefile_sha256_by_task_id=s)
    for r in m.records:
        perms=(r.teacher_call_permitted,r.training_permitted,r.select_evaluation_permitted,r.confirmatory_permitted)
        if r.access_class is DistillationAccessClass.DEV_VISIBLE: assert perms==(True,True,False,False)
        else: assert perms==(False,False,True,False)
