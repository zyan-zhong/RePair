import importlib,sys,types
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def test_preflight_reuses_original_q_contract_without_provider(tmp_path,monkeypatch):
    try:m=importlib.import_module('analyzer_preflight')
    except ImportError:pytest.fail('Analyzer native contract preflight missing')
    repo=tmp_path/'repo';repo.mkdir();calls=[]
    def discover(root):calls.append('discover');return repo,{'schema_id':'test_roles'}
    q=types.SimpleNamespace(discover_strong_repo=discover,import_repo=lambda p:calls.append('import'),
        assert_fixed_head_api_contract=lambda p:{'test_symbol':lambda:None})
    monkeypatch.setattr(m,'checked',lambda argv,**kw:'test-head' if argv[-1]=='HEAD' else '')
    monkeypatch.setattr(m,'validate_runtime_surface',lambda repo,capsule,authority:{'status':'PASS','scope':'fixture'})
    result=m.run(tmp_path,tmp_path/'output.json',q=q)
    assert result['provider_calls']==0
    assert result['entire_hierarchical_analyzer_proven'] is False
    assert calls==['discover','import']
    assert result['repo_path']==str(repo)
    assert result['runtime_surface_preflight']['status']=='PASS'
