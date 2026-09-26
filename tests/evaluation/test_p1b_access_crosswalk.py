from pchsi.evaluation.p1b_access_crosswalk import (
    LegacyMatchStatus, LegacyTaskIdentityV1, match_legacy_to_current,
)
from pchsi.evaluation.task_manifest import FrozenTaskRecord


def current(index=0, sha1="a"*40):
    task_id=f"alfworld_valid_unseen_all134_{index:04d}"
    root=f"/data/{task_id}"
    return FrozenTaskRecord(index,task_id,"valid_unseen","pick_and_place_simple",f"{root}/game.tw-pddl",sha1,root,f"{root}/traj_data.json")


def test_exact_sha1_match_is_high_confidence():
    record=match_legacy_to_current(legacy=LegacyTaskIdentityV1("legacy","old","/legacy/game.tw-pddl","a"*40,"legacy:0"),current=current())
    assert record.match_status is LegacyMatchStatus.EXACT_GAMEFILE_SHA1_MATCH
    assert record.confidence_class=="HIGH"


def test_exact_path_requires_manual_confirmation():
    c=current()
    record=match_legacy_to_current(legacy=LegacyTaskIdentityV1("legacy",c.task_id,c.gamefile,None,"legacy:0",False),current=c)
    assert record.match_status is LegacyMatchStatus.TASK_ID_ONLY_INSUFFICIENT


def test_exact_path_with_manual_confirmation_is_high_confidence():
    c=current()
    record=match_legacy_to_current(legacy=LegacyTaskIdentityV1("legacy",c.task_id,c.gamefile,None,"legacy:0",True),current=c)
    assert record.match_status is LegacyMatchStatus.EXACT_TASK_ID_AND_PATH_MATCH
    assert record.confidence_class=="HIGH"
