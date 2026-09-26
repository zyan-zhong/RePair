from pathlib import Path
from types import SimpleNamespace,ModuleType
from contextlib import contextmanager
import copy,json,sys
import pytest
import closed_history as c

@pytest.fixture
def fixture():return json.loads(Path(__file__).with_name('CLOSED_FIXTURE.json').read_bytes())

def reader(fixture):
    def read(ref):
        row=fixture['docs'][ref['path']]
        if row['ref']!=ref:raise ValueError('REF_SHA_CHANGED')
        return copy.deepcopy(row['value'])
    return read

def test_real_closed_exception_preserved(fixture):
    value=c.receipts(fixture['terminal_ref'],reader(fixture))
    assert value['outcome']=='PROMOTED' and value['human_scientific_decision_count']==1

@pytest.mark.parametrize('field,value',[
    ('next_parent_policy_id','WRONG'),('human_scientific_decision_count',0),
    ('automatic_promotion_claimed',True),('outcome','ROLLED_BACK'),('benchmark_feedback_used',True)])
def test_closed_terminal_tamper(fixture,field,value):
    fixture['docs'][fixture['terminal_ref']['path']]['value'][field]=value
    with pytest.raises(ValueError):c.receipts(fixture['terminal_ref'],reader(fixture))

def test_corrupt_reference_rejected(fixture):
    bad={**fixture['terminal_ref'],'sha256':'0'*64}
    with pytest.raises(ValueError,match='REF_SHA_CHANGED'):c.receipts(bad,reader(fixture))

@pytest.mark.parametrize('kind', ['summary','decision','original','audit'])
def test_bound_evidence_tamper(fixture,kind):
    t=fixture['docs'][fixture['terminal_ref']['path']]['value']
    if kind=='summary':fixture['docs'][t['summary_ref']['path']]['value']['candidate_success_cells']+=1
    elif kind=='decision':fixture['docs'][t['promotion_ref']['path']]['value']['evidence_sha256']='0'*64
    elif kind=='original':fixture['docs'][t['original_automatic_terminal_ref']['path']]['value']['outcome']='PROMOTED'
    else:
        s=fixture['docs'][t['summary_ref']['path']]['value']
        fixture['docs'][s['identity_audit_ref']['path']]['value']['binding_ref']={'path':'wrong','sha256':'0'*64}
    with pytest.raises(ValueError):c.receipts(fixture['terminal_ref'],reader(fixture))

@pytest.mark.parametrize('is_closed',[False,True])
def test_only_closed_result_uses_receipts(monkeypatch,tmp_path,is_closed):
    calls=[]
    execution=ModuleType('offoff_binding.execute')
    execution.validate_completed_offoff_terminal=lambda ref:calls.append('native_audit')
    class Driver:
        def validate_result(self,start,result):
            execution.validate_completed_offoff_terminal(result['terminal_ref']);calls.append('other_native_checks')
    driver_module=ModuleType('entry.driver');driver_module.ExistingComponentRoundDriver=Driver
    entry=ModuleType('entry');entry.driver=driver_module
    package=ModuleType('offoff_binding');package.execute=execution
    api=ModuleType('continuity_binding.api');api.read_ref=lambda ref:ref
    continuity=ModuleType('continuity_binding');continuity.api=api
    exact=ModuleType('exact_bindings');exact.immutable_json=lambda p,v:calls.append('proof')
    for k,v in {'entry':entry,'entry.driver':driver_module,'offoff_binding':package,'offoff_binding.execute':execution,
        'continuity_binding':continuity,'continuity_binding.api':api,'exact_bindings':exact}.items():monkeypatch.setitem(sys.modules,k,v)
    monkeypatch.setattr(c,'closed_transition',lambda *args:{'event_sha256':'digest'} if is_closed else None)
    monkeypatch.setattr(c,'receipts',lambda *args:calls.append('closed_receipts'))
    d=Driver();d.owner_root=tmp_path
    with c.installed({'owner_root':str(tmp_path)},'package'):
        d.validate_result({'round_id':'r'},{'outcome':'PROMOTED','attempt_root':str(tmp_path/'attempts/000003'),'terminal_ref':{'path':'exact'}})
    assert calls==(['closed_receipts','other_native_checks','proof'] if is_closed else ['native_audit','other_native_checks'])
    assert execution.validate_completed_offoff_terminal({'path':'anything'}) is None
    assert calls[-1]=='native_audit'

@pytest.mark.parametrize('tamper',[None,'resume','base'])
def test_preparation_cache_uses_original_identities_and_restores(tmp_path,tamper):
    import closure_entry as entry
    modules=[]
    for name in ('resume_entry','continuation'):
        root=tmp_path/name;root.mkdir();(root/'PACKAGE_FILES.sha256').write_text(name)
        module=ModuleType(name);module.ROOT=root;module.__file__=str(root/(name+'.py'))
        module.load=lambda: 'original load';module.prepare=lambda: 'original prepare'
        module.verify=lambda r=root:entry.digest(r/'PACKAGE_FILES.sha256')
        module.verify_package=lambda: None
        modules.append(module)
    resume,base=modules
    base_value=({}, {}, {}, entry.digest(base.ROOT/'PACKAGE_FILES.sha256'),None,None,None)
    value=({},base,None,entry.digest(resume.ROOT/'PACKAGE_FILES.sha256'),base_value,None)
    prepared=(None,None,None,(None,None,None,(None,None,None,(None,resume,None,value))))
    with entry.prepared_once(prepared):
        assert resume.load() is value and base.prepare() is base_value
        if tamper:
            changed=resume if tamper=='resume' else base
            (changed.ROOT/'PACKAGE_FILES.sha256').write_text('CHANGED')
            with pytest.raises(ValueError):
                changed.load() if tamper=='resume' else changed.prepare()
    assert resume.load()=='original load' and base.prepare()=='original prepare'
