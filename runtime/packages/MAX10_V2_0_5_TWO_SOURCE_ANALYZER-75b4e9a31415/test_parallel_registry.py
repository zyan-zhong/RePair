from pathlib import Path
from types import SimpleNamespace
import ast,json,hashlib,os
import pytest

pytestmark=pytest.mark.skipif(os.name!='posix',reason='server-native fork integration required')

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v))

def fixture(tmp_path,source):
    units=[]
    for sid in ['a','b','c']:
        for name,value in [('id',{'scientific_unit_id':sid,'identity_sha256':digest(sid)}),('projection',{'evidence_pack_sha256':sid}),('access',{})]:write(tmp_path/(sid+'_'+name+'.json'),value)
        for stage in ['L-A0','L-A1']:units.append({'source_unit_id':sid,'stage_id':stage,'condition_id':stage[-2:],
            'scientific_unit_identity_path':sid+'_id.json','input_projection_path':sid+'_projection.json',
            'task_access_record_path':sid+'_access.json','expected_common_evidence_sha256':sid})
    reg={'registry_sha256':'r','round_id':'round','policy_version':'parent','units':units};path=tmp_path/'registry.json';write(path,reg)
    rr=SimpleNamespace(_obj=lambda p:json.loads(p.read_bytes()),validate_artifact=lambda *x:None,
        QUARANTINE_SOURCE_CONTINUE_UNRELATED='QUARANTINE',GLOBAL_INFRASTRUCTURE_FAIL_CLOSED='GLOBAL',write_new_json=write)
    rr._logical_id=lambda **kw:digest([kw['identity']['identity_sha256'],kw['unit']['stage_id'],kw['projection']])
    def execute(**kw):
        cid=rr._logical_id(identity=kw['unit_identity'],unit=kw,registry=reg,projection=kw['projection'])
        call=kw['output_root']/cid;call.mkdir()
        (call/'sent').write_text('once')
        ambiguous=kw['unit_identity']['scientific_unit_id']=='a' and kw['stage_id']=='L-A0'
        result={'logical_call_id':cid,'call_dir':str(call),'status':'AMBIGUOUS_POST_SEND' if ambiguous else 'ACCEPTED',
            'hard_stop':ambiguous,'validated_artifact_sha256':None if ambiguous else cid}
        write(call/'result.json',result);return result
    rr.execute_one=execute
    rr._adopt_terminal=lambda call:{**json.loads((call/'result.json').read_bytes()),'reused_terminal':True,'same_logical_call_resend_authorized':False}
    rr.classify_hard_stop=lambda **kw:{'route':'QUARANTINE'}
    tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_registry')
    # Execute the exact historical function against a deterministic transport fixture.
    ns={**vars(rr),'Path':Path,'CampaignStartupAuthorityV1':object}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'native_registry','exec'),ns)
    return rr,ns['run_registry'],path

def test_native_rows_hashes_quarantine_and_order_match(tmp_path):
    from parallel_registry import run_registry
    source=Path(__file__).with_name('NATIVE_REGISTRY_SOURCE.py').read_text()
    rr,native,reg=fixture(tmp_path,source)
    left=native(registry_path=reg,output_root=tmp_path/'serial')[0]
    right=run_registry(rr,native,workers=2,observe=None,registry_path=reg,output_root=tmp_path/'parallel')[0]
    def normalized(v):return json.loads(json.dumps(v).replace(str(tmp_path/'serial'),'OUT').replace(str(tmp_path/'parallel'),'OUT'))
    assert normalized(left)==normalized(right)
    assert right['quarantined_source_ids']==['a'] and right['rows'][1]['status']=='QUARANTINED_SOURCE_SKIPPED'
    before={str(p):p.read_bytes() for p in (tmp_path/'parallel').glob('*/sent')}
    result=run_registry(rr,native,workers=2,observe=None,registry_path=reg,output_root=tmp_path/'parallel')
    assert result[0]==right and before=={str(p):p.read_bytes() for p in (tmp_path/'parallel').glob('*/sent')}

def test_partial_recovery_adopts_without_resending(tmp_path):
    from parallel_registry import run_registry
    source=Path(__file__).with_name('NATIVE_REGISTRY_SOURCE.py').read_text();rr,native,reg=fixture(tmp_path,source)
    native(registry_path=reg,output_root=tmp_path/'parallel')
    (tmp_path/'parallel/execution_manifest.json').unlink()
    rr.execute_one=lambda **kw:pytest.fail('terminal must be adopted, never re-sent')
    result,rc=run_registry(rr,native,workers=2,observe=None,registry_path=reg,output_root=tmp_path/'parallel')
    assert rc==0 and all(r.get('reused_terminal') for r in result['rows'] if r['logical_call_id'])

def test_binding_mismatch_prevents_all_sends(tmp_path):
    from parallel_registry import run_registry
    source=Path(__file__).with_name('NATIVE_REGISTRY_SOURCE.py').read_text();rr,native,reg=fixture(tmp_path,source)
    write(tmp_path/'c_projection.json',{'evidence_pack_sha256':'bad'})
    with pytest.raises(ValueError,match='binding mismatch'):
        run_registry(rr,native,workers=2,observe=None,registry_path=reg,output_root=tmp_path/'parallel')
    assert not list((tmp_path/'parallel').glob('*/sent'))

def test_global_hard_stop_keeps_native_terminal_manifest(tmp_path):
    from parallel_registry import run_registry
    source=Path(__file__).with_name('NATIVE_REGISTRY_SOURCE.py').read_text();rr,native,reg=fixture(tmp_path,source)
    rr.classify_hard_stop=lambda **kw:{'route':'GLOBAL'}
    result,rc=run_registry(rr,native,workers=2,observe=None,registry_path=reg,output_root=tmp_path/'parallel')
    assert rc==20 and result['terminal_route']=='GLOBAL'
    assert json.loads((tmp_path/'parallel/execution_manifest.json').read_bytes())==result
    assert any(r['hard_stop'] for r in result['rows'])

def test_duplicate_logical_directory_cannot_have_two_writers(tmp_path):
    from parallel_registry import run_registry
    source=Path(__file__).with_name('NATIVE_REGISTRY_SOURCE.py').read_text();rr,native,reg=fixture(tmp_path,source)
    value=json.loads(reg.read_bytes())
    for unit in value['units'][4:]:
        unit.update(scientific_unit_identity_path='b_id.json',input_projection_path='b_projection.json',expected_common_evidence_sha256='b')
    write(reg,value)
    with pytest.raises(ValueError,match='DUPLICATE_LOGICAL'):
        run_registry(rr,native,workers=2,observe=None,registry_path=reg,output_root=tmp_path/'parallel')
    assert not list((tmp_path/'parallel').glob('*/sent'))
