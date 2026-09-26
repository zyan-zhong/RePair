import json,hashlib
from pathlib import Path
import pytest
from post_recovery import resolve,target,INDEX

def ref(p):return {'path':str(p),'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def fixture(tmp_path):
    old=tmp_path/'current';old.mkdir();source=tmp_path/'source';source.mkdir()
    a={'post_original_run_root':str(old),'post_recovery_round_id':'r2'}
    (source/'AUTHORITY.json').write_text(json.dumps(a));ar=ref(source/'AUTHORITY.json')
    (source/'PACKAGE_FILES.sha256').write_text(ar['file_sha256']+'  AUTHORITY.json\n');mr=ref(source/'PACKAGE_FILES.sha256')
    new=target(a,mr['file_sha256'])
    index={'schema_id':'REGISTERED_POST_CONTRACT_EXECUTION_INDEX_V1','source_authority':ar,'source_manifest':mr,
        'original_run_root':str(old),'execution_run_root':str(new),'round_id':'r2'}
    (old/INDEX).write_text(json.dumps(index));return old,new,index

def test_resolves_exact_registration(tmp_path):
    old,new,_=fixture(tmp_path);assert resolve(old)==new

def test_next_round_no_index_uses_same_native_root(tmp_path):assert resolve(tmp_path)==tmp_path

@pytest.mark.parametrize('key,value',[('execution_run_root','/wrong'),('round_id','r3'),('schema_id','wrong'),('original_run_root','/other')])
def test_rejects_wrong_identity(tmp_path,key,value):
    old,new,index=fixture(tmp_path);index[key]=value;(old/INDEX).write_text(json.dumps(index))
    with pytest.raises(ValueError):resolve(old)

def test_changed_authority_rejected(tmp_path):
    old,new,index=fixture(tmp_path);Path(index['source_authority']['path']).write_text('{}')
    with pytest.raises(ValueError,match='REFERENCE_SHA'):resolve(old)
