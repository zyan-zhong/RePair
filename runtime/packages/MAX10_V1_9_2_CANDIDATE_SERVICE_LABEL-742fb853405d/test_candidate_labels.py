from pathlib import Path
import json,pytest,jsonschema
from candidate_labels import service_label
F=json.loads((Path(__file__).parent/'REGRESSION_FIXTURE.json').read_bytes())

def test_original_real_label_rejected():
    assert len(F['candidate']['logical_condition_id'])==80
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(F['candidate']['logical_condition_id'],F['schema'])

def test_label_meets_actual_native_schema_without_changing_policy():
    value=F['candidate'];original=dict(value)
    label=service_label(value['policy_id'],value['artifact_sha256']);jsonschema.validate(label,F['schema'])
    assert len(label)==64 and value==original
    assert label==service_label(value['policy_id'],value['artifact_sha256'])

def test_no_truncation_collision():
    assert service_label('a'*100+'1','a'*64)!=service_label('a'*100+'2','a'*64)
    assert service_label('same','a'*64)!=service_label('same','b'*64)

@pytest.mark.parametrize('value',[None,'','x'*64,'a'*63,'a'*65])
def test_invalid_artifact_rejected(value):
    with pytest.raises(ValueError):service_label('policy',value)

@pytest.mark.parametrize('parent_kind,child_kind,count', [('BASE_MODEL','LORA_ADAPTER',1),('LORA_ADAPTER','LORA_ADAPTER',2)])
def test_registered_capacity_keeps_frozen_per_batch_limit(parent_kind,child_kind,count):
    from candidate_labels import adapter_capacity
    source={'max_loras':1,'max_cpu_loras':1,'other':'unchanged'}
    result=adapter_capacity(source,{'kind':parent_kind},{'kind':child_kind})
    assert result=={'max_loras':1,'max_cpu_loras':count,'other':'unchanged'}
    assert source['max_cpu_loras']==1

def test_larger_registered_cpu_cache_is_preserved():
    from candidate_labels import adapter_capacity
    source={'max_loras':1,'max_cpu_loras':4}
    assert adapter_capacity(source,{'kind':'LORA_ADAPTER'},{'kind':'LORA_ADAPTER'})==source
