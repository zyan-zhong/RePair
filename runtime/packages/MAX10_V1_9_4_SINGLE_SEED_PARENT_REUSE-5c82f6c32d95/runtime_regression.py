"""Isolated synthetic regression of the real finalizer/decision/recovery path."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import tempfile,json

def run(deployment,future,a):
    from continuity_binding.api import read_ref,write_once
    from promotion_entry import ROOT,source_refs,install
    from goal_runtime import installed
    from goal_capture import spec_for,canonical,sha
    from goal_metric import METRIC_ID,completion
    import offoff_binding.execute as execution
    from offoff_binding.native import Native
    import pchsi.evaluation.select_result_audit as result_audit
    from entry.driver import ExistingComponentRoundDriver as Driver
    from entry import offoff_job
    # Production Native/auditor behavior has its own unchanged suite. Here the
    # deterministic fixture substitutes upstream cells only, then executes the
    # real finalizer, hashes, new collector verification, decision, and replay.
    task=read_ref(future['offoff_source_registration']['assets']['task_access'])['records'][0]
    spec=spec_for(task['gamefile'],task['gamefile_sha256']);refs=source_refs()
    with tempfile.TemporaryDirectory(prefix='goal-native-finalizer-',dir=ROOT/'validation') as temp:
        root=Path(temp);sink=root/'binding';sink.mkdir();executed=root/'execution';loader_rows={};receipts={};bundles={}
        env_sha='d'*64
        for label in ('parent','candidate'):
            cells=[];rows=[]
            for ordinal in range(2):
                cell_id=f'fixture-{label}-{ordinal}';attempt=cell_id+'-a000';bundle_sha=sha(attempt.encode())
                cell=NS(condition_cell_id=cell_id,to_dict=lambda:{})
                row={'condition_cell_id':cell_id,'execution_attempt_id':attempt,'attempt_bundle_sha256':bundle_sha,'success':False}
                episode=NS(condition_cell_id=cell_id,gamefile_sha256=task['gamefile_sha256'],environment_runtime_manifest_sha256=env_sha,
                    final_budget={'environment_step_count':0},final_observation_sha256='e'*64,success=False)
                loader_rows[str(executed/label/'evaluator_run/attempts'/attempt)]=NS(episode_artifact=episode)
                facts=[]
                if label=='candidate':
                    p,args,negative=spec['groups'][0]['alternatives'][0][0]
                    assert negative is False
                    facts=[(p,args)]
                n,d=completion(spec,{(p,tuple(args)) for p,args in facts});assert n<d
                metric_root=executed/label/'restricted_goal_progress'/cell_id
                capture=write_once(metric_root/'TERMINAL_CAPTURE.json',{'metric_id':METRIC_ID,'source_refs':refs,'identity':{'condition_cell_id':cell_id,'gamefile':task['gamefile'],'gamefile_sha256':task['gamefile_sha256'],'environment_runtime_manifest_sha256':env_sha},
                    'environment_step_count':0,'final_observation_sha256':'e'*64,'goal_spec_sha256':sha(canonical(spec)),'facts':facts,'numerator':n,'denominator':d,'native_won':False})
                write_once(metric_root/'BOUND_GOAL_METRIC.json',{'condition_cell_id':cell_id,'execution_attempt_id':attempt,'attempt_bundle_sha256':bundle_sha,'capture_ref':capture})
                cells.append(cell);rows.append(row)
            receipts[str(executed/label/'cell_receipts.jsonl')]=rows
            bundles[label]=(NS(policy_condition_id=label),None,NS(cells=cells),'a'*64,'b'*64,'c'*64)
        rule=read_ref(future['promotion_rule_ref']);rule={**rule,'expected_task_count':2,'replicate_seeds':[7]}
        rule_ref=write_once(root/'fixture_rule.json',rule)
        protocol_ref=write_once(root/'fixture_protocol.json',{'promotion_rule_ref':rule_ref,'replicate_seeds':[7]})
        binding={'schema_id':'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1','native_repo_root':str(root/'native'),'source_refs':list(future['offoff_source_registration']['source_refs']),
            'execution_root':str(executed),'paired_cell_count':2,'input_refs':{'protocol_ref':protocol_ref}}
        binding_ref=write_once(sink/'BINDING.json',binding)
        context={'protocol':read_ref(protocol_ref),'bundles':bundles,'infra':{},'access':NS(records=[None,None]),
            'start':{'round_id':'SYNTHETIC-ONLY','request_sha256':'a'*64},'parent':{'policy_id':'fixture-parent','artifact_sha256':'b'*64},'candidate':{'policy_id':'fixture-candidate','artifact_sha256':'c'*64}}
        paired={'unique_task_count':2,'replicate_seeds':[7],'paired_cell_count':2,'total_condition_cell_count':4,'parent_success_cells':0,'candidate_success_cells':0,
            'both_success_cells':0,'both_failure_cells':2,'parent_only_success_cells':0,'candidate_only_success_cells':0,'mean_task_success_rate_delta':0}
        runner=(NS(load_receipts=lambda path:receipts[str(path)],_recover_or_execute_cell=lambda **kw:None),NS(load_native=lambda root:None,check_receipt_grid=lambda *args,**kwargs:None),
            lambda **kw:paired,None,{},NS(load_attempt_directory_v1=lambda path:loader_rows[str(path)]))
        native=NS(root=root,sources={r['path']:r for r in binding['source_refs']})
        native.runners=lambda:Native.runners(native)
        expected=[NS(schedule_name=arm,condition_cell_id=c.condition_cell_id) for arm,b in bundles.items() for c in b[2].cells]
        with patch.object(Native,'load',return_value=native),patch.object(Native,'runners',lambda self:runner),patch.object(execution,'prepare',return_value=context),patch.object(execution,'materialize',return_value=binding_ref),patch.object(execution,'_audit_one',return_value={}),patch.object(result_audit,'derive_expected_select_cells_from_master_schedules',return_value=expected),installed():
            terminal_ref=execution.finalize_binding(binding_ref)
            terminal=read_ref(terminal_ref);assert terminal['outcome']=='PROMOTED'
            assert 'goal_progress_ref' in read_ref(terminal['summary_ref'])
            assert execution.validate_completed_offoff_terminal(terminal_ref) is True
            # A changed restricted capture cannot be accepted on recovery.
            path=executed/'candidate/restricted_goal_progress/fixture-candidate-0/TERMINAL_CAPTURE.json';path.write_bytes(path.read_bytes()+b' ')
            try:execution.validate_completed_offoff_terminal(terminal_ref)
            except ValueError:pass
            else:raise AssertionError('TAMPERED_GOAL_CAPTURE_ACCEPTED')
        # Test prospective activation and preservation of already started rounds.
        calls=[];driver=NS(deployment=deployment,_binding=lambda start:{'round_index':a['promotion_activation_after_round_index']+1},_binding_path=lambda start:root/'requests'/start['request_sha256'])
        def original(self,start,path):calls.append(self.deployment['promotion_rule_ref']);return 'native'
        start={'request_sha256':'f'*64,'round_id':'SYNTHETIC-FUTURE'}
        from parent_cache import index_path
        write_once(index_path(driver,start),{'fixture_only':True})
        with patch.object(Driver,'execute_round',original),install(a,'f'*64):
            fresh=root/'fresh';fresh.mkdir();Driver.execute_round(driver,start,fresh)
            assert calls[-1]!=deployment['promotion_rule_ref'] and (fresh/'FROZEN_ACCEPTANCE_AMENDMENT.json').exists()
            Driver.execute_round(driver,start,fresh);assert calls[-1]!=deployment['promotion_rule_ref']
            existing=root/'existing';(existing/'rollout').mkdir(parents=True);Driver.execute_round(driver,start,existing)
            assert calls[-1]==deployment['promotion_rule_ref'] and not (existing/'FROZEN_ACCEPTANCE_AMENDMENT.json').exists()
            driver._binding=lambda start:{'round_index':a['promotion_activation_after_round_index']}
            current=root/'current';current.mkdir();Driver.execute_round(driver,start,current)
            assert calls[-1]==deployment['promotion_rule_ref'] and not (current/'FROZEN_ACCEPTANCE_AMENDMENT.json').exists()
    print('NATIVE_FINALIZER_PROMOTE_REPLAY_TAMPER_AND_ACTIVATION_REGRESSION_PASS',flush=True)
