from pathlib import Path
from types import SimpleNamespace
import hashlib
import pytest
from environment_deadline import loader

def setup(tmp_path):
    path=tmp_path/'environment.py';path.write_text('def load_environment(authority):\n return time.monotonic()+60\n')
    module=SimpleNamespace(__file__=str(path),time=SimpleNamespace(monotonic=lambda:10))
    authority={'environment_loader_source_ref':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},
        'environment_policy':{'initialization_timeout_seconds':300,'maximum_initialization_timeout_seconds':300}}
    return authority,module

def test_registered_deadline_replaces_only_native_literal(tmp_path):
    a,m=setup(tmp_path);assert loader(a,m)({})==310

@pytest.mark.parametrize('value',[0,-1,True,301,float('nan')])
def test_invalid_budget_rejected(tmp_path,value):
    a,m=setup(tmp_path);a['environment_policy']['initialization_timeout_seconds']=value
    with pytest.raises(ValueError,match='POLICY_INVALID'):loader(a,m)

def test_loader_source_drift_rejected(tmp_path):
    a,m=setup(tmp_path);Path(m.__file__).write_text('changed')
    with pytest.raises(ValueError,match='SOURCE_CHANGED'):loader(a,m)
