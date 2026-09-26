"""Real historical cell audits and action replay; no new policy requests or jobs."""
from pathlib import Path
from types import SimpleNamespace as NS
import json,tempfile,copy

def run(deployment,future,a):
    from continuity_binding.api import read_ref,write_once
    from promotion_entry import ROOT
    from parent_cache import Cache,contract,equivalent
    from offoff_binding.native import Native
    from offoff_binding.materialize import prepare
    from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
    plan=json.loads((ROOT/'REGISTERED_DIAGNOSTIC_PARALLEL.json').read_bytes())
    binding=read_ref(plan['binding_ref']);native=Native.load(binding['native_repo_root'],binding['source_refs'])
    context=prepare(native=native,**binding['input_refs']);contract_before=contract(context,'parent');after=copy.deepcopy(contract_before);after['seeds']=after['seeds'][:1];equivalent(contract_before,after)
    live,audit,_,_,_,loader=native.runners();audit_native=audit.load_native(native.root)
    expected=derive_expected_select_cells_from_master_schedules(schedules={k:b[2] for k,b in context['bundles'].items()},authorized_schedule_sha256={k:b[5] for k,b in context['bundles'].items()})
    expected={c.condition_cell_id:c for c in expected if c.schedule_name=='parent'}
    examples=[]
    # Finite exact registered shard zero rows, stop after a zero-action and a nonzero-action example.
    root=Path(plan['shards'][0]['execution_root'])/'parent'
    for row in live.load_receipts(root/'cell_receipts.jsonl'):
        if row['seed']!=context['protocol']['replicate_seeds'][0]:continue
        loaded=loader.load_attempt_directory_v1(root/'evaluator_run/attempts'/row['execution_attempt_id'])
        kind=bool(loaded.public_transitions)
        if not examples or kind!=examples[0][0] or len(examples)==1:examples.append((kind,row,loaded))
        if len(examples)==2:break
    assert len(examples)==2
    with tempfile.TemporaryDirectory(prefix='parent-reuse-diagnostic-',dir=ROOT/'validation') as temp:
        dest=Path(temp);certificate=write_once(dest/'DIAGNOSTIC_ONLY_NOT_CLOSED_SCIENCE.json',{'diagnostic':True,'production_cache_authority_conferred':False,'binding_ref':plan['binding_ref']})
        cache=Cache.__new__(Cache);cache.read=read_ref;cache.current=context;cache.binding_ref=plan['binding_ref'];cache.authority_ref=certificate
        cache.origin={'source_terminal_ref':certificate};cache.arm='parent';cache.source=context;cache.native=native;cache.live=live;cache.audit=audit;cache.audit_native=audit_native;cache.loader=loader;cache.summary={};cache.receipts={}
        cells=context['bundles']['parent'][2].cells;cache.ordinal={c.condition_cell_id:n for n,c in enumerate(cells)};cache.expected=expected
        roots=['']*len(cells);cache.closed_rows={}
        for _,row,_ in examples:
            n=cache.ordinal[row['condition_cell_id']];roots[n]=str(root.parent);cache.closed_rows[('parent',n)]=row
        cache.source_audit={'execution_roots_by_ordinal':roots}
        for kind,row,loaded in examples:
            ordinal=cache.ordinal[row['condition_cell_id']]
            adopted,metadata=cache.adopt(ordinal,dest/'current');assert adopted==row
            assert cache.audit_adopted(ordinal,dest/'current')==(adopted,metadata)
            assert metadata['parent_reuse']['fresh_model_episode'] is False
            assert not (dest/'current/parent/evaluator_run').exists()
        assert len(cache.rows(dest/'current'))==2
        changed=cache.record_path(dest/'current',cache.ordinal[examples[0][1]['condition_cell_id']]);value=json.loads(changed.read_bytes());value['original_receipt']['success']=not value['original_receipt']['success'];changed.write_text(json.dumps(value))
        try:cache.audit_adopted(cache.ordinal[examples[0][1]['condition_cell_id']],dest/'current')
        except ValueError:pass
        else:raise AssertionError('TAMPERED_REUSE_RECORD_ACCEPTED')
    print('REAL_PARENT_NATIVE_AUDIT_ACTION_REPLAY_ADOPTION_RECOVERY_TAMPER_PASS policy_calls=0 action_counts='+str([len(v[2].public_transitions) for v in examples]),flush=True)
    mixed_finalizer(deployment,future,a)
    prospective_parent_bindings(context,native,binding,future)

def prospective_parent_bindings(source,native,source_binding,future):
    """Prepare actual native condition/runtime/schedule objects for both next-parent roles.

    Only the not-yet-trained NEXT candidate bytes and diagnostic request signature
    are fixtures. The retained parent's real weights and all evaluation inputs are verified.
    """
    from unittest.mock import patch
    import offoff_binding.materialize as module
    from continuity_binding.api import write_once,read_ref
    from promotion_entry import ROOT
    from parent_cache import contract,equivalent,Cache
    from offoff_binding.native import Native
    with tempfile.TemporaryDirectory(prefix='next-parent-contract-',dir=ROOT/'validation') as temp:
        root=Path(temp)
        for arm in ('parent','candidate'):
            parent=source[arm];start={**source['start'],'round_id':'DIAGNOSTIC-NEXT-'+arm,'request_sha256':'a'*64,
                'execution_attempt_id':'b'*64,'parent_policy_id':parent['policy_id'],'parent_policy_artifact_sha256':parent['artifact_sha256']}
            candidate={**source['candidate'],'round_id':start['round_id'],'request_sha256':start['request_sha256'],'execution_attempt_id':start['execution_attempt_id'],
                'parent_policy_id':parent['policy_id'],'parent_policy_artifact_sha256':parent['artifact_sha256'],
                'policy_id':'DIAGNOSTIC-NOT-TRAINED','artifact_sha256':'c'*64,'logical_condition_id':'d'*64,'checkpoint_instance_id':'d'*64}
            infra=copy.deepcopy(source['infra']);infra['server_runtime_parameters']['manifest_id']='DIAGNOSTIC-NEXT-'+arm
            infra['server_runtime_parameters']['max_cpu_loras']=2 if parent['kind']=='LORA_ADAPTER' else 1
            protocol={**source['protocol'],'round_id':start['round_id'],'request_sha256':start['request_sha256'],
                'replicate_seeds':read_ref(future['promotion_rule_ref'])['replicate_seeds'],'promotion_rule_ref':future['promotion_rule_ref']}
            values={'request_ref':start,'parent_ref':parent,'candidate_ref':candidate,'protocol_ref':protocol,'infrastructure_ref':infra}
            refs={k:write_once(root/arm/(k+'.json'),v) for k,v in values.items()}
            artifact=module._artifact
            def verify_artifact(policy):return {} if policy['policy_id']=='DIAGNOSTIC-NOT-TRAINED' else artifact(policy)
            with patch.object(module,'native_request',lambda value:NS(**value)),patch.object(module,'_artifact',verify_artifact):
                observed=module.prepare(native=native,**refs)
                binding_ref=module.materialize(native=native,**refs,sink=root/arm/'binding')
            equivalent(contract(source,arm),contract(observed,'parent'))
            # Constructor regression uses a clearly labeled closed-source fixture;
            # real per-cell evidence validation is separately exercised above.
            count=source_binding['paired_cell_count'];audit_ref=write_once(root/arm/'fixture_audit.json',{'schema_id':'CURRENT_OFFOFF_IDENTITY_AUDIT_V1',
                'binding_ref':{'path':str(root/arm/'fixture_source_binding.json'),'sha256':'unused'},'execution_roots_by_ordinal':['DIAGNOSTIC']*count,
                'rows':[{'label':label,'ordinal':n} for label in ('parent','candidate') for n in range(count)]})
            source_ref=write_once(root/arm/'fixture_source_binding.json',source_binding)
            audit=json.loads(Path(audit_ref['path']).read_bytes());audit['binding_ref']=source_ref
            audit_ref=write_once(root/arm/'fixture_audit_bound.json',audit)
            summary_ref=write_once(root/arm/'fixture_summary.json',{'identity_audit_ref':audit_ref})
            terminal_ref=write_once(root/arm/'fixture_terminal.json',{'fixture_only':True,'outcome':'PROMOTED' if arm=='candidate' else 'ROLLED_BACK','binding_ref':source_ref,'summary_ref':summary_ref})
            cache_ref=write_once(root/arm/'fixture_cache.json',{'schema_id':'REGISTERED_RETAINED_PARENT_SELECT_CACHE_V1','request_sha256':start['request_sha256'],
                'parent_policy_id':parent['policy_id'],'parent_policy_artifact_sha256':parent['artifact_sha256'],
                'origin':{'source_terminal_ref':terminal_ref,'source_arm':arm},'source_binding_ref':source_ref,'source_summary_ref':summary_ref})
            observed['protocol']={**observed['protocol'],'parent_select_cache_ref':cache_ref}
            cache=Cache(binding_ref,observed)
            assert len(observed['bundles']['parent'][2].cells)==len(source['access'].records)
            assert cache.arm==arm
    print('NATIVE_FUTURE_RETAINED_AND_PROMOTED_PARENT_BINDINGS_CACHE_CONSTRUCTOR_PASS',flush=True)

def mixed_finalizer(deployment,future,a):
    """Run the existing real finalizer regression through the mixed-parent adapter."""
    import runtime_regression,inspect
    from reuse_runtime import installed
    # Exercise the installed overlay in the same deterministic upstream fixture.
    # Cache cell/source-audit behavior was checked against real cells above.
    text=inspect.getsource(runtime_regression.run)
    text=text.replace("        with patch.object(Native,'load',return_value=native)",'''        import parent_cache
        class FixtureCache:
            def rows(self,root):return receipts[str(executed/'parent/cell_receipts.jsonl')]
            def audit_adopted(self,ordinal,root):
                row=receipts[str(executed/'parent/cell_receipts.jsonl')][ordinal]
                cell=row['condition_cell_id'];bound=executed/'parent/restricted_goal_progress'/cell/'BOUND_GOAL_METRIC.json'
                capture=read_ref(read_ref({'path':str(bound),'sha256':sha(bound.read_bytes())})['capture_ref'])
                metric_ref=write_once(executed/'reuse_metrics'/cell/'METRIC.json',{'condition_cell_id':cell,
                    'execution_attempt_id':row['execution_attempt_id'],'attempt_bundle_sha256':row['attempt_bundle_sha256'],
                    'numerator':capture['numerator'],'denominator':capture['denominator'],
                    'bound_metric_ref':{'path':str(bound),'sha256':sha(bound.read_bytes())}})
                return row,{'parent_reuse':{'metric_ref':metric_ref,'fresh_model_episode':False}}
        for key in list(loader_rows):
            if '/parent/evaluator_run/' in key:del loader_rows[key]
        with patch.object(parent_cache,'cache_for',lambda binding_ref,context:FixtureCache()),patch.object(Native,'load',return_value=native)''')
    # Keep original fixture patches visible to the cloned executor before entering it.
    text=text.replace('installed():\n            terminal_ref', 'installed(),reuse_installed():\n            terminal_ref')
    text=text.replace("            assert 'goal_progress_ref' in read_ref(terminal['summary_ref'])", "            assert read_ref(terminal['summary_ref'])['parent_reused_cell_count']==2\n            assert read_ref(terminal['summary_ref'])['fresh_model_episode_count']==2")
    namespace=dict(vars(runtime_regression));namespace['reuse_installed']=installed
    exec(compile(text,'mixed_finalizer_regression','exec'),namespace)
    namespace['run'](deployment,future,a)
    print('REUSE_OVERLAY_NATIVE_FINALIZER_RECOVERY_REGRESSION_PASS',flush=True)
