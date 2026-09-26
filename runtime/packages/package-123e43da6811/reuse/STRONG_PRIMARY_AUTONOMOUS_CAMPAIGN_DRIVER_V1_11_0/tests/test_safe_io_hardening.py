import hashlib,json
from pathlib import Path
import pytest
from safe_io import canonical_bytes,domain_hash,load_obj

def test_domain_hash_removes_excluded_field_not_zero_fills():
    v={'schema_id':'X','a':1,'receipt_sha256':'f'*64}
    expected=hashlib.sha256(b'X\0'+canonical_bytes({'schema_id':'X','a':1})).hexdigest()
    assert domain_hash('X',v)==expected

def test_load_obj_rejects_symlink(tmp_path):
    target=tmp_path/'x.json'; target.write_text('{"a":1}',encoding='utf-8')
    link=tmp_path/'link.json'; link.symlink_to(target)
    with pytest.raises(ValueError,match='JSON_REGULAR_FILE_REQUIRED'):
        load_obj(link)
