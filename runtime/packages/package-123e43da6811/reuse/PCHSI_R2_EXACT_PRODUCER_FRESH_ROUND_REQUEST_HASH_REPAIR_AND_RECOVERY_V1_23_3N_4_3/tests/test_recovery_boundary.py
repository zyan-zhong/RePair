import sys,importlib.util,json,zipfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def core():
    assert (ROOT/'recovery_core.py').is_file(),'native recovery boundary missing'
    import recovery_core as c
    return c

def test_batch_is_parsed_as_argv_not_executed(tmp_path):
    c=core();p=tmp_path/'run.sh'
    p.write_text('#!/usr/bin/env bash\nexec "/python" -B "/producer/shard_worker.py" --state-root "/new" --v1230-output-root "/build" --capsule "/old/input.zip" --shard-plan "/new/plan.json" --shard-id "${SLURM_ARRAY_TASK_ID}"\n')
    a=c.parse_runner(p)
    assert a['--capsule']=='/old/input.zip' and a['--state-root']=='/new'

@pytest.mark.parametrize('text',['#!/bin/bash\necho bad\n','#!/bin/bash\nexec python x\ntouch y\n'])
def test_unreviewed_shell_shape_is_rejected(tmp_path,text):
    p=tmp_path/'run.sh';p.write_text(text)
    with pytest.raises(ValueError):core().parse_runner(p)

def test_exact_missing_capsule_from_real_fatal_message(tmp_path):
    c=core();p=tmp_path/'missing.zip'
    fatal={'error_type':'FileNotFoundError','error_message':f"[Errno 2] No such file or directory: '{p}'",'traceback':'in safe_extract_zip\n zipfile.ZipFile(source, "r")','assigned_global_ordinals':None,'scientific_environment_execution_finished':False}
    assert c.validate_capsule_missing_fatal(fatal,p)==str(p)
    with pytest.raises(ValueError):c.validate_capsule_missing_fatal(fatal,tmp_path/'different.zip')

def test_no_blanket_filenotfound_retry(tmp_path):
    c=core()
    with pytest.raises(ValueError):c.validate_capsule_missing_fatal({'error_type':'FileNotFoundError'},tmp_path/'x')

def test_once_write_adopts_equal_bytes_not_different(tmp_path):
    c=core();p=tmp_path/'receipt.json'
    c.equal_or_new(p,{'a':1});before=p.read_bytes();c.equal_or_new(p,{'a':1})
    assert p.read_bytes()==before
    with pytest.raises(ValueError):c.equal_or_new(p,{'a':2})

def test_terminal_states_are_not_inferred_from_missing_rows():
    c=core()
    assert c.queue_state(0,'')=='EMPTY'
    assert c.queue_state(1,'','slurm_load_jobs error: Invalid job id specified')=='NOT_IN_QUEUE'
    assert c.queue_state(1,'','connection error')=='UNKNOWN'
    assert c.queue_state(0,'42_[7%8]|PENDING')=='ACTIVE'

def test_archive_outputs_cannot_become_inputs(tmp_path):
    c=core();p=tmp_path/'capsule.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('cell_terminals/x.json','{}')
    with pytest.raises(ValueError):c.check_capsule_inventory(p,{'members':[]})

def test_zip_path_escape_rejected(tmp_path):
    c=core();p=tmp_path/'capsule.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('../x','bad')
    with pytest.raises(ValueError):c.check_capsule_inventory(p,{'members':[]})

def test_squeue_error_does_not_authorize_retry():
    assert core().queue_state(1,'','Permission denied')=='UNKNOWN'

def test_source_identity_is_validated_before_execution(tmp_path):
    from recovery_core import verify_source_identity,sha_file
    p=tmp_path/'code.py';p.write_text('# fixture\n')
    identity={'schema_id':'NATIVE_PRODUCER_PATCH_SOURCE_IDENTITY_V1','files':{'code.py':sha_file(p)}}
    verify_source_identity(tmp_path,identity)
    p.write_text('# altered\n')
    with pytest.raises(ValueError,match='INPUT_SHA_CHANGED'):
        verify_source_identity(tmp_path,identity)
