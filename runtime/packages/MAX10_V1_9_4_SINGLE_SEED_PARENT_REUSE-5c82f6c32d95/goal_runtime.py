"""Small extension at native worker, audit, and decision registration boundaries."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import json
from goal_capture import install_cell_capture,validate_capture,sha
from goal_metric import METRIC_ID
from promotion_v2 import validate_rule

def rule_from_binding(binding):
    from continuity_binding.api import read_ref
    protocol=read_ref(binding['input_refs']['protocol_ref'])
    rule=read_ref(protocol['promotion_rule_ref'])
    return rule if rule.get('schema_id')=='FROZEN_TRAIN_SELECT_PROMOTION_RULE_V2' else None

@contextmanager
def installed():
    import offoff_binding.execute as execution
    import offoff_binding.parallel as parallel_module
    from offoff_binding.native import Native
    from continuity_binding.api import read_ref
    native_runners=Native.runners;native_decider=execution._registered_decider;native_write=execution.write_once
    native_components=parallel_module._parallel_components
    def components(binding_ref):
        binding,native,config_ref,policy,assignments=native_components(binding_ref)
        rule=rule_from_binding(binding)
        if rule is None:return binding,native,config_ref,policy,assignments
        resource=read_ref(rule['select_parallel_resource_ref'])
        cap=resource['max_concurrent_shards'];count=resource['shard_count']
        if type(cap) is not int or type(count) is not int or min(cap,count)<=0:raise ValueError('SELECT_PARALLEL_RESOURCE_AUTHORITY_INVALID')
        count=min(cap,count,binding['paired_cell_count'])
        policy={**policy,'shards':count,'max_concurrent_jobs':count,'registered_select_parallel_amendment_ref':rule['select_parallel_resource_ref']}
        assignments=native.parallel().partition_ordinals(range(binding['paired_cell_count']),shard_count=count)
        return binding,native,config_ref,policy,assignments
    def decider(native,rule):
        if rule.get('schema_id')=='FROZEN_TRAIN_SELECT_PROMOTION_RULE_V2':validate_rule(rule)
        return native_decider(native,rule)
    def runners(native):
        result=native_runners(native)
        # Only V2 bindings register this collector. Existing V1 native sources
        # and execution are byte-for-byte unchanged during R2 recovery.
        registered=native.sources.get(str(Path(__file__).with_name('goal_capture.py')))
        if registered:
            refs=[native.sources[str(Path(__file__).with_name(name))] for name in ('goal_metric.py','goal_capture.py','goal_runtime.py','promotion_v2.py')]
            install_cell_capture(result[0],refs)
        return result
    def write(path,value):
        if Path(path).name!='TRAIN_SELECT_AGGREGATE.json':return native_write(path,value)
        audit=read_ref(value['identity_audit_ref']);binding=read_ref(audit['binding_ref']);rule=rule_from_binding(binding)
        if rule is None:return native_write(path,value)
        validate_rule(rule);native=Native.load(binding['native_repo_root'],binding['source_refs']);loader=native_runners(native)[-1]
        rows=[];roots=audit['execution_roots_by_ordinal']
        for row in audit['rows']:
            if 'parent_reuse' in row:
                if row['label']!='parent':raise ValueError('ONLY_PARENT_CACHE_ALLOWED')
                metric=read_ref(row['parent_reuse']['metric_ref'])
                if any(metric[k]!=row[k] for k in ('execution_attempt_id','attempt_bundle_sha256')):raise ValueError('REUSED_GOAL_ATTEMPT_CHANGED')
                rows.append({**row,**{k:metric[k] for k in ('condition_cell_id','numerator','denominator','bound_metric_ref')}})
                continue
            root=Path(roots[row['ordinal']])/row['label'];episode=loader.load_attempt_directory_v1(root/'evaluator_run/attempts'/row['execution_attempt_id']).episode_artifact
            metric_root=root/'restricted_goal_progress'/episode.condition_cell_id
            bound_path=metric_root/'BOUND_GOAL_METRIC.json';bound=json.loads(bound_path.read_bytes())
            for k in ('execution_attempt_id','attempt_bundle_sha256'):
                if bound[k]!=row[k]:raise ValueError('GOAL_BOUND_ATTEMPT_CHANGED')
            if bound['condition_cell_id']!=episode.condition_cell_id:raise ValueError('GOAL_BOUND_CELL_CHANGED')
            capture=metric_root/'TERMINAL_CAPTURE.json'
            if bound['capture_ref']!={'path':str(capture),'sha256':sha(capture.read_bytes())}:raise ValueError('GOAL_CAPTURE_REF_CHANGED')
            n,d=validate_capture(capture,episode,{'condition_cell_id':episode.condition_cell_id,'success':episode.success},rule['goal_source_refs'])
            rows.append({**row,'condition_cell_id':episode.condition_cell_id,'numerator':n,'denominator':d,
                'bound_metric_ref':{'path':str(bound_path),'sha256':sha(bound_path.read_bytes())}})
        metric={'schema_id':'RESTRICTED_COMPLETE_GOAL_PROGRESS_V1','metric_id':METRIC_ID,'request_sha256':value['request_sha256'],
            'source_refs':rule['goal_source_refs'],'binding_ref':audit['binding_ref'],'rows':rows}
        ref=native_write(Path(path).parent/'restricted/GOAL_PROGRESS.json',metric)
        reused=sum('parent_reuse' in row for row in audit['rows'])
        return native_write(path,{**value,'goal_progress_ref':ref,'parent_reused_cell_count':reused,
            'fresh_model_episode_count':value['total_condition_cell_count']-reused,'historical_parent_observations_reused':bool(reused)})
    # The finalizer passes its local summary object to the native freeze call;
    # load the exact augmented bytes here instead of altering native aggregation.
    native_freeze=execution.freeze_registered_promotion
    def freeze(**kwargs):
        kwargs['aggregate']=read_ref(kwargs['summary_ref'])
        return native_freeze(**kwargs)
    with patch.object(Native,'runners',runners),patch.object(execution,'_registered_decider',decider),patch.object(execution,'write_once',write),patch.object(execution,'freeze_registered_promotion',freeze),patch.object(parallel_module,'_parallel_components',components):yield
