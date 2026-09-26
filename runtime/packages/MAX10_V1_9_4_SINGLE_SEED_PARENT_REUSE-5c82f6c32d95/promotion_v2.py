"""Predeclared lexicographic acceptance, retaining all original integrity checks."""
import importlib.util,json,hashlib
from pathlib import Path
from goal_metric import METRIC_ID,compare

def read(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('PROMOTION_REF_CHANGED')
    return raw

def integrity(rule):
    ref=rule['integrity_producer_ref'];read(ref)
    spec=importlib.util.spec_from_file_location('_goal_v1_integrity',ref['path']);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    shadow={**rule,'schema_id':'FROZEN_TRAIN_SELECT_PROMOTION_RULE_V1','comparison':'strictly_greater','secondary_metrics_role':'explanation_only'}
    mod.validate_rule(shadow)
    return mod,shadow

def validate_rule(rule):
    for key,value in {'schema_id':'FROZEN_TRAIN_SELECT_PROMOTION_RULE_V2','comparison':'success_then_terminal_goal_fraction',
        'secondary_metrics_role':'goal_fraction_tie_break_only','goal_metric_id':METRIC_ID,'frozen_before_outcomes':True,
        'memory_state':'OFF','harness_state':'OFF','benchmark_feedback_used':False}.items():
        if rule.get(key)!=value:raise ValueError('FROZEN_GOAL_RULE_INVALID:'+key)
    for ref in rule['goal_source_refs']+rule['environment_source_refs']:read(ref)
    integrity(rule)

def decide(*,frozen_rule,aggregate):
    validate_rule(frozen_rule);mod,shadow=integrity(frozen_rule)
    result=mod.decide(frozen_rule=shadow,aggregate=aggregate)
    metric=json.loads(read(aggregate['goal_progress_ref']))
    if metric['request_sha256']!=aggregate['request_sha256'] or metric['metric_id']!=METRIC_ID or metric['source_refs']!=frozen_rule['goal_source_refs']:raise ValueError('GOAL_SUMMARY_IDENTITY')
    rows=metric['rows'];pairs=aggregate['paired_cell_count'];progress={}
    for label in ('parent','candidate'):
        cells=[r for r in rows if r['label']==label]
        if sorted(r['ordinal'] for r in cells)!=list(range(pairs)):raise ValueError('GOAL_COMPLETE_GRID_REQUIRED')
        progress[label]=[(r['numerator'],r['denominator']) for r in cells]
    result['decision']=compare(aggregate['parent_success_cells'],aggregate['candidate_success_cells'],progress['parent'],progress['candidate'])
    return result
