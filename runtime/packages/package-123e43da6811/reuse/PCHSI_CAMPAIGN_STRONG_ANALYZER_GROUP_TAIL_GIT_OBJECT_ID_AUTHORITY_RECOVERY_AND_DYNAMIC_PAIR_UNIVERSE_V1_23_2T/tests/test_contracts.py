from __future__ import annotations
import ast
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'v1232t_driver.py').read_text()

def load_eq():
    spec=importlib.util.spec_from_file_location('eq',ROOT/'source_context_equivalence.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_no_current_round_literals_or_legacy_fixed_cardinality():
    forbidden=['166443','e5cb2f3d15d63e31c7ab9ba61502df10a590740d067ea2dc749e3a8cac6012ea','34072dedc0234050307459c77f24a9763fe2a470ae74e0078eceaa87ef417b49','2843','==30','== 30','==12','== 12']
    for value in forbidden: assert value not in SRC

def test_reuses_existing_analyzer_tail_assets():
    for value in ['group_projection_v3','crosscheck_projection_v2','build_analyzer_memory_view_v1','execute_one','aggregate_capability_profile','build_policy_behavior_profile','project_candidate','materialize_state_condition_k1']:
        assert value in SRC

def test_no_environment_training_slurm_paths():
    for value in ['sbatch','srun','ALFWorld','training_execution(', 'optimizer.step(', 'subprocess.Popen']:
        assert value not in SRC

def test_no_retry_or_replacement_execution():
    assert "automatic_retry_count':0" in SRC
    assert "same_logical_call_resend_count':0" in SRC
    assert "replacement_group_count':0" in SRC
    assert "top_up_group_count':0" in SRC

def test_execution_context_equivalence_provenance_only():
    m=load_eq(); s='a'*64; menu='b'*64
    rows=[{'source_state_sha256':s,'menu_sha256':menu,'admissible_commands':['x'],'local_result_sha256':'c'*64},{'source_state_sha256':s,'menu_sha256':menu,'admissible_commands':['x'],'local_result_sha256':'d'*64}]
    idx=m.index_source_contexts(rows); assert len(idx)==1; assert idx[s]['execution_context_conflict'] is False; assert len(idx[s]['provenance_variants'])==2

def test_execution_context_conflict_fails():
    m=load_eq(); s='a'*64; menu='b'*64
    try: m.index_source_contexts([{'source_state_sha256':s,'menu_sha256':menu,'admissible_commands':['x']},{'source_state_sha256':s,'menu_sha256':menu,'admissible_commands':['y']}])
    except ValueError as e: assert 'EXECUTION_CONTEXT_CONFLICT' in str(e)
    else: raise AssertionError('conflict must fail')

def test_operator_shell_no_strict_mode():
    run=(ROOT/'RUN_V1232T.sh').read_text()
    for x in ['set -e','set -u','set -o pipefail','set -euo pipefail']: assert x not in run

def test_status_is_read_only():
    status=(ROOT/'STATUS_V1232T.sh').read_text()
    for x in ['sbatch','scontrol','scancel','OPENAI_API_KEY','RUN_V1232T']: assert x not in status


def load_driver():
    spec=importlib.util.spec_from_file_location('drv',ROOT/'v1232t_driver.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_git_oid_domain_is_object_format_aware():
    m=load_driver()
    assert m.git_object_id('a'*40,'sha1','HEAD')=='a'*40
    assert m.git_object_id('b'*64,'sha256','HEAD')=='b'*64
    for value,fmt in [('a'*64,'sha1'),('b'*40,'sha256')]:
        try: m.git_object_id(value,fmt,'HEAD')
        except RuntimeError as e: assert 'INVALID_GIT_OBJECT_ID' in str(e)
        else: raise AssertionError('cross-domain Git OID must fail')

def test_tracked_repo_identity_uses_git_object_format_and_commit_type(tmp_path):
    import subprocess
    m=load_driver()
    repo=tmp_path/'repo'; repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.email','t@example.com'],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.name','T'],check=True)
    (repo/'x').write_text('x\n')
    subprocess.run(['git','-C',str(repo),'add','x'],check=True)
    subprocess.run(['git','-C',str(repo),'commit','-q','-m','x'],check=True)
    ident=m.tracked_repo_identity(repo)
    assert ident['object_format'] in {'sha1','sha256'}
    assert len(ident['head_oid'])==__import__('hashlib').new(ident['object_format']).digest_size*2
    assert subprocess.run(['git','-C',str(repo),'cat-file','-t',ident['head_oid']],capture_output=True,text=True,check=True).stdout.strip()=='commit'

def test_no_sha64_repo_head_conflation():
    assert "sha64(head,'REPO_HEAD')" not in SRC
    for token in ["--show-object-format=storage","HEAD^{commit}","cat-file","fixed_repo_head_oid","fixed_repo_object_format"]:
        assert token in SRC
