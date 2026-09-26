import json
from pathlib import Path
from copy import deepcopy
from trajectory_facts import project, expand_branch

FIXTURES=json.loads(Path(__file__).with_name('TRAJECTORY_FIXTURES.json').read_bytes())

def test_all_branches_covered_without_changing_effects():
    for f in FIXTURES:
        before=deepcopy(f['verifier']);value=project(before)
        assert before==f['verifier']
        assert value['branch_count']==len(before['branch_records'])
        assert {b['branch_key_sha256'] for b in value['branches']}=={b['branch_key_sha256'] for b in before['branch_records']}
        for b in before['branch_records']:
            got=expand_branch(value,b['branch_key_sha256'])
            assert [x['action'] for x in got['transitions']]==[x['action'] for x in b['environment_transitions_from_source']]
            assert [x['resulting_observation'] for x in got['transitions']]==[x['resulting_observation'] for x in b['environment_transitions_from_source']]
            assert got['terminal_success']==b['terminal_success']

def test_r3_repeated_cooling_and_inadmissible_cd_are_distinct():
    v=project(FIXTURES[2]['verifier'])
    rows=[expand_branch(v,b['branch_key_sha256']) for b in v['branches'] if b['arm']=='F1']
    cooling=[r for r in rows if any(t['action']=='cool egg 2 with fridge 1' for t in r['transitions'])]
    assert len(cooling)==5
    assert all(sum(t['action']=='cool egg 2 with fridge 1' for t in r['transitions'])==25 for r in cooling)
    cds=[r for r in rows if r not in cooling]
    assert len(cds)==5
    assert all(r['parsed_actions_absent_from_live_menu']==3 for r in cds)
    assert all(any('cd 1' in t['resulting_observation'] for t in r['transitions']) for r in cds)

def test_r4_local_action_success_does_not_become_benefit():
    v=project(FIXTURES[3]['verifier'])
    rows=[expand_branch(v,b['branch_key_sha256']) for b in v['branches'] if b['arm']=='F1']
    assert len(rows)==5
    assert all(r['intervention_steps']==1 and r['continuation_environment_steps']==28 for r in rows)
    assert all(r['terminal_success'] is False for r in rows)
    assert v['causal_effect_assignment_authorized'] is False
    assert v['training_supervision_authorized'] is False

def test_no_private_policy_payload_or_task_specific_rules():
    text=json.dumps(project(FIXTURES[3]['verifier']))
    for key in ['raw_response_body_base64','prompt_token_ids','request_wire_bytes_base64']:
        assert key not in text
    source=Path(__file__).with_name('trajectory_facts.py').read_text()
    for task in ['egg','desklamp','creditcard','alfworld_train']:
        assert task not in source

def test_incomplete_branches_remain_unknown_and_cleanup_invalid_not_scientific():
    from trajectory_facts import researcher_summary,history_summary
    v=deepcopy(FIXTURES[3]['verifier']);b=v['branch_records'][0]
    for key in ('environment_transitions_from_source','policy_calls','intervention_sequence','final_budget','terminal_success','terminal_reason','typed_option_stop_reason'):
        b.pop(key)
    b['evidence_complete']=False;b['scientific_outcome_produced']=False
    other=v['branch_records'][1];other['terminal_success']=True;other['evidence_complete']=False;other['scientific_outcome_produced']=False
    facts=project(v);summary=researcher_summary(facts);history=history_summary(facts)
    unknown=facts['patterns'][facts['branches'][0]['pattern_id']]
    assert unknown['terminal_success'] is None and unknown['intervention_steps'] is None
    assert sum(r['trajectory_unavailable_branches'] for r in history['state_arm_aggregates'])==1
    assert sum(r['successful_valid_branches'] for r in history['state_arm_aggregates'])==0
    assert len(summary['branches'])==len(v['branch_records'])
    from trajectory_facts import canonical
    canonical(history)
    assert sum(r['terminal_reason_unknown_branches'] for r in history['state_arm_aggregates'])==1

def test_completely_missing_branch_has_explicit_denominator():
    from trajectory_facts import history_summary
    v=deepcopy(FIXTURES[3]['verifier']);v['planned_branch_count']=len(v['branch_records']);v['branch_records'].pop()
    facts=project(v);history=history_summary(facts)
    assert facts['missing_branch_record_count']==history['missing_branch_record_count']==1
    assert history['planned_branch_count']==10 and history['branch_count']==9
