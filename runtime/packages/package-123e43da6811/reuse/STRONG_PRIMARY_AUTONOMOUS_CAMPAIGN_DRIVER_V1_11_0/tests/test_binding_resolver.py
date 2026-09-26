from pathlib import Path
import json, pytest
from binding_resolver import unique_json_by_schema

def test_unique_schema_resolves(tmp_path:Path):
    p=tmp_path/'a.json'; p.write_text(json.dumps({'schema_id':'A','x':1}))
    assert unique_json_by_schema(tmp_path,'A')['path']==str(p)

def test_multiple_schema_is_ambiguous(tmp_path:Path):
    for n in ('a','b'): (tmp_path/f'{n}.json').write_text(json.dumps({'schema_id':'A'}))
    with pytest.raises(ValueError,match='AMBIGUOUS'):
        unique_json_by_schema(tmp_path,'A')
