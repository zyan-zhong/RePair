import json,hashlib
from pathlib import Path
import pytest
from runtime_contract import load_trained_runtime

def fixture():return json.loads(Path(__file__).with_name('CURRENT_FIXTURE.json').read_bytes())['runtime']['value']
def write(tmp,value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode();p=tmp/'runtime.json';p.write_bytes(raw)
    return p,hashlib.sha256(raw).hexdigest()

def test_accept_trained_without_rewriting_its_schema_or_bytes(tmp_path):
    value=fixture();p,digest=write(tmp_path,value);before=p.read_bytes()
    result=load_trained_runtime(p,expected_file_sha256=digest,expected_model=value['served_model_name'],validate_native_contract=lambda v:None,validate_artifacts=lambda v:None)
    assert result==value and p.read_bytes()==before

@pytest.mark.parametrize('mutation',['schema','version','model','extra','self_authorize','sha','contract','artifact'])
def test_invalid_trained_binding_rejected(tmp_path,mutation):
    v=fixture();expected=v['served_model_name'];validator=lambda v:None;artifacts=lambda v:None
    if mutation=='schema':v['schema_id']='UNKNOWN'
    if mutation=='version':v['schema_version']=2
    if mutation=='model':v['served_model_name']='wrong'
    if mutation=='extra':v['undeclared_field']=1
    if mutation=='self_authorize':v['scientific_execution_authorized']=True
    if mutation=='contract':validator=lambda v:(_ for _ in ()).throw(ValueError('native contract'))
    if mutation=='artifact':artifacts=lambda v:(_ for _ in ()).throw(ValueError('native artifact'))
    p,digest=write(tmp_path,v)
    if mutation=='sha':digest='0'*64
    with pytest.raises(ValueError):load_trained_runtime(p,expected_file_sha256=digest,expected_model=expected,validate_native_contract=validator,validate_artifacts=artifacts)
