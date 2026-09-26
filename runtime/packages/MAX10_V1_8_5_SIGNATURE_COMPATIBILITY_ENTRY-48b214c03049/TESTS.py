import tempfile,inspect
from pathlib import Path
from signature_entry import load,signature_compatibility
a,base,identity=load();prepared=base.prepare();authority,values,*_=prepared
from reuse import load_cores
from pchsi.cognitive_runtime import orchestrator
import repair
native=orchestrator.execute_one
with tempfile.TemporaryDirectory(prefix='signature_regression_no_send_') as tmp:
    with repair.install_repair(authority,values,Path(tmp)/'negative',values['repair_plans']):
        try:load_cores(values['analyzer_binding'])
        except RuntimeError as error:assert str(error)=='FIXED_HEAD_CALLABLE_SIGNATURE_DRIFT:execute_one'
        else:raise AssertionError('ORIGINAL_SIGNATURE_DEFECT_NOT_REPRODUCED')
    with signature_compatibility(),repair.install_repair(authority,values,Path(tmp)/'positive',values['repair_plans']):
        assert inspect.signature(orchestrator.execute_one)==inspect.signature(native)
        core=load_cores(values['analyzer_binding'])
        assert core.orch.execute_one is orchestrator.execute_one
        print('NEGATIVE_REPRODUCTION_AND_NATIVE_API_REUSE_PASS=2')
print('PROVIDER_SEND_COUNT=0')
