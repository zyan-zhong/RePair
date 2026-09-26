import json
from pathlib import Path
import pytest
from execution_index import assert_unsubmitted,resolve_run

def test_pre_submission_gate_checks_unbound_population(tmp_path):
    plan={'handoff':{'branch_plan':[{'branch_key_sha256':'unbound'}]}}
    assert_unsubmitted(tmp_path,plan)
    p=tmp_path/'branches/unbound/BRANCH_INTENT.json';p.parent.mkdir(parents=True);p.write_text('{}')
    with pytest.raises(ValueError):assert_unsubmitted(tmp_path,plan)

def test_submission_intent_blocks_materialization_recovery(tmp_path):
    (tmp_path/'SBATCH_SUBMISSION_INTENT.json').write_text('{}')
    with pytest.raises(ValueError):assert_unsubmitted(tmp_path,{'handoff':{'branch_plan':[]}})

def test_no_index_returns_original_exact_root(tmp_path):assert resolve_run(tmp_path/'run')==tmp_path/'run'

def test_undeclared_index_root_is_rejected(tmp_path):
    (tmp_path/'REGISTERED_H44_EXECUTION_INDEX.json').write_text(json.dumps({'schema_id':'wrong','original_run_root':str(tmp_path/'run')}))
    with pytest.raises(ValueError):resolve_run(tmp_path/'run')
