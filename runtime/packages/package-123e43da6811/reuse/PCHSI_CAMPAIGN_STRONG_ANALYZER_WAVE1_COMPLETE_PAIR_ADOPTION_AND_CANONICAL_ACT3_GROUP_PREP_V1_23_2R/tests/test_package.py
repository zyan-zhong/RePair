from pathlib import Path
import ast, importlib.util
P=Path(__file__).resolve().parents[1]

def load():
 s=importlib.util.spec_from_file_location('drv',P/'v1232r_driver.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_no_provider_or_rollout_reexecution_path():
 t=(P/'v1232r_driver.py').read_text()
 assert 'run_registry(' not in t
 assert 'execute_one(' not in t
 assert 'sbatch' not in t and 'srun' not in t
 assert "strong_local_logical_call_reexecution_count':0" in t

def test_complete_pair_policy_frozen():
 t=(P/'v1232r_driver.py').read_text()
 for x in ['replacement_source_count','top_up_source_count','resource_budget_expansion','outcome_adaptive_selection_used','automatic_retry_count']:
  assert x in t
 assert 'ONLY_EXISTING_A0_ACCEPTED_PLUS_A1_ACCEPTED_COMPLETE_PAIRS_ENTER_WAVE2' in t

def test_canonical_grouping_symbols_plural():
 t=(P/'v1232r_driver.py').read_text()
 assert 'build_group_synthesis_inputs' in t
 assert 'build_group_synthesis_input(' not in t
 assert "build_group_manifests'](local_results=local_results,mechanical_signatures=mechanical)" in t

def test_source_context_shape_array():
 t=(P/'v1232r_driver.py').read_text()
 assert "write_new_value(gr/'source_contexts.json',members)" in t

def test_no_strict_shell():
 t=(P/'RUN_V1232R.sh').read_text()
 assert 'set -e' not in t and 'set -u' not in t and 'pipefail' not in t
