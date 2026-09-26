import importlib,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def api():return importlib.import_module('dashboard')

def test_unknown_and_empty_population_do_not_fake_completion():
    d=api()
    assert '100%' not in d.progress_bar(0,None)
    assert '100%' not in d.progress_bar(0,0)
    assert '50%' in d.progress_bar(5,10)
    assert 'INVALID' in d.progress_bar(11,10)

def test_error_and_queue_are_not_reported_as_success():
    d=api()
    assert d.stage_state(10,10,failed=True)=='ERROR'
    assert d.stage_state(0,10,active=True,waiting=True)=='WAIT'
    assert d.stage_state(10,10,active=True,verified=False)=='CHECK'
    assert d.stage_state(10,10,verified=True)=='DONE'

def test_colors_are_backgrounds_and_plain_output_has_no_escape():
    d=api();s={'title':'Validation','round_id':'r1','state':'RUN','resident':'alive','rows':[
        d.row('Rollout',5,10,state='RUN'),d.row('PRE',0,1,state='WAIT'),d.row('POST',0,1,state='ERROR')]}
    colored=d.render(s,color=True,width=100)
    assert '\x1b[42;' in colored and '\x1b[43;' in colored and '\x1b[41;' in colored
    assert '\x1b' not in d.render(s,color=False,width=80)

def test_controls_from_evidence_cannot_inject_terminal_commands():
    d=api();s={'title':'x','round_id':'r','state':'ERROR','resident':'dead','rows':[],
        'notes':['remote\x1b[2J\rforged\x07']}
    out=d.render(s,color=False,width=80)
    assert '\x1b' not in out and '\r' not in out and '\x07' not in out

def test_published_eval_and_final_receipts_are_separate():
    d=api();rows=d.lifecycle_rows({'training':{'planned_steps':8,'published_steps':8,'state':'TRAINING_RESULT_PUBLISHED'},
        'offoff':{'total_pairs':1775,'published_parent':300,'published_candidate':250,'parent':0,'candidate':0,'closed_shards':0,'shards':4}},active='TRAIN_SELECT')
    by={r['name']:r for r in rows}
    assert by['Training']['state']=='DONE'
    assert by['Eval parent']['done']==300 and by['Eval candidate']['total']==1775
    assert by['Acceptance']['done']==0

def test_completed_process_exit_is_not_error_but_unexpected_exit_is():
    d=api()
    assert d.overall_state('COMPLETED',False,terminal=True)=='DONE'
    assert d.overall_state('TRAIN_SELECT',False)=='ERROR'
    assert d.overall_state('TRAIN_SELECT',True)=='RUN'

def test_non_tty_color_and_refresh_controls():
    d=api()
    assert d.use_color('auto',False,{}) is False
    assert d.use_color('auto',True,{'NO_COLOR':'1'}) is False
    assert d.use_color('auto',True,{'TERM':'dumb'}) is False
    assert d.use_color('always',False,{}) is True

def test_long_lines_wrap_without_losing_error_details():
    d=api();reason='reason='+('abcdefghijklmnop '*20)
    out=d.render({'title':'x','round_id':'r','state':'ERROR','resident':'dead','rows':[],'notes':[reason]},color=False,width=80)
    assert all(len(line)<=80 for line in out.splitlines())
    assert ' '.join(reason.split()) in ' '.join(out.split())

def test_queued_evaluation_is_yellow_wait_not_running():
    d=api();rows=d.lifecycle_rows({'offoff':{'total_pairs':10,'published_parent':0,'published_candidate':0},
        'queue':{'returncode':0,'stdout':'17|PENDING|Resources\n'}},active='TRAIN_SELECT')
    assert next(r for r in rows if r['name']=='Eval candidate')['state']=='WAIT'

def test_next_registered_formal_round_wins_over_closed_validation():
    from collector import choose_scope,current_progress
    assert choose_scope('auto',{'source_attempt_root':'/owner/old'},
        {'stage':'COMPLETED','attempt_root':'/owner/new'},True)=='formal'
    assert choose_scope('auto',{'source_attempt_root':'/owner/old'},
        {'stage':'COMPLETED','attempt_root':'/owner/old'},True)=='validation'
    assert current_progress({'round_id':'previous','completed_local_calls':60},'current')=={}

def test_queue_outage_is_explicit_in_running_evaluation():
    d=api();rows=d.lifecycle_rows({'offoff':{'total_pairs':10,'published_parent':1,'published_candidate':1},
        'queue':{'returncode':1,'stdout':''}},active='TRAIN_SELECT')
    assert next(r for r in rows if r['name']=='Eval candidate')['state']=='UNKNOWN'
