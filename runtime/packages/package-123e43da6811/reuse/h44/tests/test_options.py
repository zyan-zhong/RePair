"""Regression tests for the two frozen public search-termination forms.

No entity, selected count or candidate identity is part of production dispatch.
"""
import importlib
import pytest


def mod():
    try:
        return importlib.import_module('option_adapter')
    except ImportError:
        pytest.fail('Typed option compiler and exact public predicates are not implemented')


def candidate(term, actions=None):
    from copy import deepcopy
    return {'candidate_sha256':'a'*64,'source_state_sha256':'b'*64,
            'option_actions':actions or ['go to desk 1','go to shelf 2'],
            'termination_condition':term,'candidate_status':'EXECUTABLE_SHORT_OPTION'}


def form1(noun='mug'):
    return (f'Stop the search options when the {noun} becomes visible or carried, '
            'when the current admissible menu changes such that the next option is unavailable, '
            'or when the episode terminates; after each executed action, re-read the resulting observation and current menu.')


def form2(noun='key'):
    return (f'Re-evaluate after each executed action and stop this search sequence as soon as the {noun} '
            f'or an exact admissible {noun}-taking command appears, the task completes, '
            'or the next listed action is no longer an exact member of the current menu.')


def test_compile_preserves_all_actions_and_candidate_identity():
    c=candidate(form1());r=mod().compile_option(c)
    assert r['status']=='COMPILED'
    assert r['contract']['option_actions']==c['option_actions']
    assert r['contract']['source_candidate_sha256']==c['candidate_sha256']
    assert r['contract']['target_object_type']=='mug'
    assert r['contract']['dispatch_mode']=='ORDERED_SEQUENCE'
    assert r['contract']['legacy_free_text_semantic_coverage']=='FULL'


def test_unknown_semantics_are_missingness_not_default_intervention():
    r=mod().compile_option(candidate('Try the best route until enough progress has happened.'))
    assert r['status']=='PROTOCOL_MISSINGNESS'
    assert r['contract'] is None


def test_each_clause_must_match_no_silent_dropping():
    assert mod().compile_option(candidate(form1()+' Ignore the live menu.'))['status']=='PROTOCOL_MISSINGNESS'


def test_pen_is_not_pencil_or_open():
    c=mod().compile_option(candidate(form2('pen')))['contract']
    r=mod().decide(c,executed_actions=[],observation='On the shelf 2, you see a pencil 2.',
      menu=['go to desk 1','take pencil 2 from shelf 2','open drawer 1'],environment_done=False)
    assert r['decision']=='EXECUTE' and r['action']=='go to desk 1'


def test_goal_mention_is_not_visibility():
    c=mod().compile_option(candidate(form2('pen')))['contract']
    r=mod().decide(c,executed_actions=[],observation='Your task is to: put a pen in desk.\nYou see a pencil 2.',
       menu=['go to desk 1'],environment_done=False)
    assert r['decision']=='EXECUTE'


def test_positive_visible_instance_stops_before_next_step():
    c=mod().compile_option(candidate(form2('pen')))['contract']
    r=mod().decide(c,executed_actions=['go to desk 1'],observation='On the desk 1, you see a pen 2 and a pencil 2.',
       menu=['go to shelf 2'],environment_done=False)
    assert r['decision']=='STOP' and r['reason']=='TARGET_VISIBLE'


def test_take_command_requires_exact_object_type_and_instance():
    c=mod().compile_option(candidate(form2('key')))['contract']
    r=mod().decide(c,executed_actions=[],observation='Nothing happens.',
      menu=['go to desk 1','take key 4 from shelf 1'],environment_done=False)
    assert r['decision']=='STOP' and r['reason']=='TARGET_TAKE_ADMISSIBLE'


def test_carried_object_is_public_put_action_not_goal_text():
    c=mod().compile_option(candidate(form1('mug')))['contract']
    r=mod().decide(c,executed_actions=[],observation='You arrive at the desk 1.',
       menu=['go to desk 1','put mug 1 in/on desk 1'],environment_done=False)
    assert r['decision']=='STOP' and r['reason']=='TARGET_CARRIED'


def test_missing_next_action_does_not_skip_to_later_action():
    c=mod().compile_option(candidate(form1()))['contract']
    r=mod().decide(c,executed_actions=[],observation='Nothing happens.',
       menu=['go to shelf 2'],environment_done=False)
    assert r['decision']=='STOP' and r['reason']=='NEXT_REGISTERED_ACTION_NOT_ADMISSIBLE'


def test_environment_done_has_precedence():
    c=mod().compile_option(candidate(form1()))['contract']
    assert mod().decide(c,executed_actions=[],observation='',menu=[],environment_done=True)['reason']=='ENVIRONMENT_DONE'


def test_out_of_order_prefix_is_rejected():
    c=mod().compile_option(candidate(form1()))['contract']
    with pytest.raises(ValueError,match='prefix'):
        mod().decide(c,executed_actions=['go to shelf 2'],observation='',menu=['go to shelf 2'],environment_done=False)


def test_contract_tampering_rejected():
    c=mod().compile_option(candidate(form1()))['contract'];c['target_object_type']='different'
    with pytest.raises(ValueError,match='hash'):
        mod().decide(c,executed_actions=[],observation='',menu=[],environment_done=False)


def test_negation_or_absence_is_not_visible():
    c=mod().compile_option(candidate(form2('pen')))['contract']
    for obs in ['You do not see a pen 1.','No pen 1 is visible.','You see no pen 1 here.']:
        assert mod().decide(c,executed_actions=[],observation=obs,menu=['go to desk 1'],environment_done=False)['decision']=='EXECUTE'
