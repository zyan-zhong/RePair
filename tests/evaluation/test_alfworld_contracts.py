from __future__ import annotations
from collections import UserDict
from pathlib import Path
import pytest
from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.alfworld_contracts import GamefileIdentityLatch, parse_reset_batch, parse_step_batch, snapshot_menu

def _infos(menu: object) -> dict[str, object]:
    return {"admissible_commands": menu}

@pytest.mark.parametrize("value", ["look", b"look", bytearray(b"look")])
def test_menu_outer_and_inner_string_like_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError): snapshot_menu(infos=_infos(value), done=False)
    with pytest.raises(TypeError): snapshot_menu(infos=_infos([value]), done=False)

@pytest.mark.parametrize("value", [{"x": 1}, UserDict({"x": 1}), iter(["look"])])
def test_menu_mapping_and_iterator_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError): snapshot_menu(infos=_infos(value), done=False)
    with pytest.raises(TypeError): snapshot_menu(infos=_infos([value]), done=False)

def test_menu_duplicate_commands_and_order_are_preserved() -> None:
    commands=["look","inventory","look"]
    snapshot=snapshot_menu(infos=_infos([commands]),done=False)
    assert snapshot.commands==tuple(commands)
    assert snapshot.sequence_sha256==sha256_string_sequence(commands)

def test_nonterminal_empty_menu_is_rejected_and_terminal_empty_menu_allowed() -> None:
    with pytest.raises(ValueError,match="empty"): snapshot_menu(infos=_infos([[]]),done=False)
    assert snapshot_menu(infos=_infos([[]]),done=True).commands==()

def test_reset_requires_exact_single_gamefile_and_latches_identity(tmp_path: Path) -> None:
    gamefile=tmp_path/'game.tw-pddl'; gamefile.write_text('{}\n',encoding='utf-8')
    state=parse_reset_batch(observations=['initial'],infos={'admissible_commands':[['look','inventory']], 'extra.gamefile':[str(gamefile)]},expected_gamefile=gamefile)
    assert state.observation=='initial'
    assert state.menu.commands==('look','inventory')
    assert state.gamefile_latch.resolved_gamefile==str(gamefile.resolve())
    with pytest.raises(ValueError,match='gamefile'):
        parse_reset_batch(observations=['initial'],infos={'admissible_commands':[['look']], 'extra.gamefile':[str(tmp_path/'other')]},expected_gamefile=gamefile)

@pytest.mark.parametrize('step_gamefile',[...,None,[None]])
def test_step_gamefile_missing_none_and_single_none_are_accepted(tmp_path: Path, step_gamefile: object) -> None:
    gamefile=tmp_path/'game.tw-pddl'; latch=GamefileIdentityLatch(resolved_gamefile=str(gamefile.resolve()))
    infos={'won':[False],'admissible_commands':[['look']]}
    if step_gamefile is not ...: infos['extra.gamefile']=step_gamefile
    state=parse_step_batch(result=(['after'],[0],[False],infos),gamefile_latch=latch)
    assert state.observation=='after' and state.done is False and state.won is False

def test_step_nonnull_gamefile_must_match_reset_latch(tmp_path: Path) -> None:
    latch=GamefileIdentityLatch(resolved_gamefile=str((tmp_path/'game.tw-pddl').resolve()))
    with pytest.raises(ValueError,match='gamefile'):
        parse_step_batch(result=(['after'],[0],[False],{'won':[False],'admissible_commands':[['look']], 'extra.gamefile':[str(tmp_path/'other.tw-pddl')]}),gamefile_latch=latch)

@pytest.mark.parametrize('result', [(['obs'],[0],[False]), ('obs',[0],[False],{'won':[False],'admissible_commands':[['look']]}), (['obs'],0,[False],{'won':[False],'admissible_commands':[['look']]}), (['obs'],[0],False,{'won':[False],'admissible_commands':[['look']]}), (['obs','extra'],[0],[False],{'won':[False],'admissible_commands':[['look']]})])
def test_step_requires_exact_four_item_singleton_batches(tmp_path: Path, result: object) -> None:
    latch=GamefileIdentityLatch(resolved_gamefile=str((tmp_path/'game.tw-pddl').resolve()))
    with pytest.raises((TypeError,ValueError)): parse_step_batch(result=result,gamefile_latch=latch)

@pytest.mark.parametrize(('done','won'),[(1,False),(False,1),('false',False),(False,'false')])
def test_done_and_won_require_type_bool(tmp_path: Path, done: object, won: object) -> None:
    latch=GamefileIdentityLatch(resolved_gamefile=str((tmp_path/'game.tw-pddl').resolve()))
    with pytest.raises(TypeError): parse_step_batch(result=(['after'],[0],[done],{'won':[won],'admissible_commands':[['look']]}),gamefile_latch=latch)

@pytest.mark.parametrize('score',[True,float('nan'),float('inf'),-float('inf'),'0'])
def test_score_is_finite_numeric_and_not_bool(tmp_path: Path, score: object) -> None:
    latch=GamefileIdentityLatch(resolved_gamefile=str((tmp_path/'game.tw-pddl').resolve()))
    with pytest.raises((TypeError,ValueError)): parse_step_batch(result=(['after'],[score],[False],{'won':[False],'admissible_commands':[['look']]}),gamefile_latch=latch)

def test_won_true_done_false_is_rejected(tmp_path: Path) -> None:
    latch=GamefileIdentityLatch(resolved_gamefile=str((tmp_path/'game.tw-pddl').resolve()))
    with pytest.raises(ValueError,match='won'): parse_step_batch(result=(['after'],[1],[False],{'won':[True],'admissible_commands':[['look']]}),gamefile_latch=latch)
