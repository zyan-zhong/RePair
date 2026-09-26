from __future__ import annotations
import ast, importlib.util, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'v1232u_driver.py').read_text()

def load_driver():
    spec=importlib.util.spec_from_file_location('drv',ROOT/'v1232u_driver.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def load_eq():
    spec=importlib.util.spec_from_file_location('eq',ROOT/'source_context_equivalence.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_g_recovery_is_terminal_only_no_provider_reexecution():
    assert 'adopt_terminal_call_only' in SRC
    g_block=SRC.split('for ordinal,grow',1)[1].split("complete_g=[x for x in g_records",1)[0]
    assert 'adopt_terminal_call_only(' in g_block
    assert 'execute_or_reuse(' not in g_block
    assert "g_provider_call_reexecution_count':0" in SRC
    assert 'T_G_TERMINAL_CALL_MISSING_NO_REEXECUTION' in SRC

def test_regression_group_record_key_bridge():
    m=load_driver()
    rec={'A2':{'status':'ACCEPTED','call_dir':'a'},'A3':{'status':'ACCEPTED','call_dir':'b'}}
    assert m.formal_group_stage_result(rec,'G-A2')['call_dir']=='a'
    assert m.formal_group_stage_result(rec,'G-A3')['call_dir']=='b'
    assert "res=grec[stage]" not in SRC

def test_recovery_reuses_exact_v1232t_activation_root():
    assert "domain_hash('V1232T_ANALYZER_TAIL_ACTIVATION_V1'" in SRC
    assert "v1232t_strong_analyzer_group_tail_dynamic_pair_universe" in SRC
    assert 'V1232T_RECOVERY_OUTPUT_ROOT_NOT_FOUND' in SRC
    assert 'out.mkdir(parents=True,exist_ok=True)' not in SRC

def test_historical_missingness_governance_preserved():
    for token in ["AMBIGUOUS_POST_SEND","automatic_retry_count':0","replacement_group_count':0","top_up_group_count':0"]:
        assert token in SRC
    assert "elif not unsafe: counters['g_incomplete']+=1" in SRC

def test_existing_analyzer_tail_assets_reused():
    for token in ['group_projection_v3','crosscheck_projection_v2','build_analyzer_memory_view_v1','aggregate_capability_profile','build_policy_behavior_profile','project_candidate','materialize_state_condition_k1']:
        assert token in SRC

def test_no_current_live_cardinality_literals():
    tree=ast.parse(SRC)
    forbidden={28,34,39,69,76,78}
    observed={node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,int)}
    assert not (observed & forbidden)

def test_no_environment_training_slurm_paths():
    for token in ['sbatch','srun','ALFWorld','optimizer.step(', 'training_execution(']:
        assert token not in SRC

def test_operator_shell_no_strict_mode():
    run=(ROOT/'RUN_V1232U.sh').read_text()
    for token in ['set -e','set -u','set -o pipefail','set -euo pipefail']:
        assert token not in run

def test_execution_context_equivalence_still_provenance_only():
    m=load_eq(); s='a'*64; menu='b'*64
    rows=[{'source_state_sha256':s,'menu_sha256':menu,'admissible_commands':['x'],'local_result_sha256':'c'*64},{'source_state_sha256':s,'menu_sha256':menu,'admissible_commands':['x'],'local_result_sha256':'d'*64}]
    idx=m.index_source_contexts(rows); assert len(idx)==1; assert len(idx[s]['provenance_variants'])==2

def test_git_oid_domain_remains_object_format_aware(tmp_path):
    m=load_driver(); repo=tmp_path/'r'; repo.mkdir(); subprocess.run(['git','init','-q',str(repo)],check=True); subprocess.run(['git','-C',str(repo),'config','user.email','u@example.com'],check=True); subprocess.run(['git','-C',str(repo),'config','user.name','U'],check=True); (repo/'x').write_text('x\n'); subprocess.run(['git','-C',str(repo),'add','x'],check=True); subprocess.run(['git','-C',str(repo),'commit','-q','-m','x'],check=True); ident=m.tracked_repo_identity(repo); assert len(ident['head_oid'])==__import__('hashlib').new(ident['object_format']).digest_size*2
