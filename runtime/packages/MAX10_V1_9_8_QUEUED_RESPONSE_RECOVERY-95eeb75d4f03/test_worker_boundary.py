from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import hashlib,json,sys

def test_fresh_post_worker_persists_adoption_before_native_main(tmp_path,monkeypatch):
    import transport_worker as worker
    owner=tmp_path/'owner';run=owner/'new_attempt'/'causal';prior=tmp_path/'registered_worker.py'
    prior.write_text('# registered fixture\n')
    authority={'owner_root':str(owner),'scientific_repo_root':str(tmp_path/'repo'),
        'post_worker_ref':{'path':str(prior),'sha256':hashlib.sha256(prior.read_bytes()).hexdigest()}}
    (tmp_path/'AUTHORITY.json').write_text(json.dumps(authority))
    request=tmp_path/'request.json'
    request.write_text(json.dumps({'scientific_repo_root':authority['scientific_repo_root'],'run_root':str(run)}))
    observed=[]
    def native_main():
        receipt=json.loads((run/'REGISTERED_DURABLE_TRANSPORT_WORKER.json').read_bytes())
        assert receipt['prior_worker_ref']==authority['post_worker_ref']
        observed.append(True);return 0
    @contextmanager
    def install(*args):yield
    monkeypatch.setattr(worker,'ROOT',tmp_path);monkeypatch.setattr(worker,'verify',lambda:'a'*64)
    monkeypatch.setattr(worker,'installed_transport',install)
    spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:setattr(module,'main',native_main)))
    monkeypatch.setattr(worker.importlib.util,'spec_from_file_location',lambda *args:spec)
    monkeypatch.setattr(worker.importlib.util,'module_from_spec',lambda value:SimpleNamespace())
    monkeypatch.setattr(sys,'argv',['transport_worker.py','--request',str(request)])
    monkeypatch.setattr(sys,'path',list(sys.path))
    assert not run.exists()
    assert worker.main()==0 and observed==[True]
