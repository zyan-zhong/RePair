import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from io_utils import canonical,sha
from deployment import resolve_memory,resolve_gamefiles

def test_memory_requires_exact_current_file_and_snapshot(tmp_path,monkeypatch):
    value={'schema_id':'FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1','active_snapshot_sha256':'a'*64,'token_budget_contract_sha256':'b'*64}
    p=tmp_path/'m.json';p.write_bytes(canonical(value));monkeypatch.setenv('TEST_MEMORY',str(p))
    req={'round_memory_runtime_authority_sha256':sha(p.read_bytes()),'round_start_memory_snapshot_sha256':'a'*64,'token_budget_contract_sha256':'b'*64}
    loc={'memory_runtime_environment_variable':'TEST_MEMORY','scripts_root':str(tmp_path),'bootstrap_memory_relative_glob':'none'}
    assert resolve_memory(request=req,locators=loc)['file_sha256']==req['round_memory_runtime_authority_sha256']
    req['round_start_memory_snapshot_sha256']='c'*64
    with pytest.raises(ValueError,match='current authority'):resolve_memory(request=req,locators=loc)

def test_memory_does_not_choose_latest_or_different_hash(tmp_path,monkeypatch):
    monkeypatch.delenv('TEST_MEMORY',raising=False)
    loc={'memory_runtime_environment_variable':'TEST_MEMORY','scripts_root':str(tmp_path),'bootstrap_memory_relative_glob':'*.json'}
    (tmp_path/'later.json').write_text('{}')
    with pytest.raises(ValueError,match='UNRESOLVED'):
        resolve_memory(request={'round_memory_runtime_authority_sha256':'0'*64},locators=loc)

def test_exact_train_manifest_selected_assets_only(tmp_path):
    root=tmp_path/'train';root.mkdir();taskroot=root/'game';taskroot.mkdir()
    vals={}
    for rel,field in [('gamefile','gamefile_sha256'),('traj_file','traj_sha256'),('initial_state','initial_state_sha256')]:
        f=taskroot/(rel+'.json');f.write_text(rel);vals[rel+'_relpath']=str(f.relative_to(root));vals[field]=sha(f.read_bytes())
    task={'schema_id':'ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1','split':'train','train_pool':'TRAIN_UPDATE','id':'task-a','index':7,**vals}
    manifest=tmp_path/'m.jsonl';manifest.write_bytes(canonical(task))
    req={'train_update_manifest_sha256':sha(manifest.read_bytes())}
    source=SimpleNamespace(source_task_id='task-a',source_gamefile_sha256=task['gamefile_sha256'])
    rows=[{'fingerprint':source,'bundle':SimpleNamespace(episode_artifact=SimpleNamespace(task_index=7))}]
    loc={'train_update_manifest_path':str(manifest),'train_root':str(root)}
    assert resolve_gamefiles(request=req,source_rows=rows,locators=loc)['task-a']['gamefile']==str(taskroot/'gamefile.json')
    task['split']='valid_unseen';manifest.write_bytes(canonical(task));req['train_update_manifest_sha256']=sha(manifest.read_bytes())
    with pytest.raises(ValueError,match='untrusted'):resolve_gamefiles(request=req,source_rows=rows,locators=loc)
