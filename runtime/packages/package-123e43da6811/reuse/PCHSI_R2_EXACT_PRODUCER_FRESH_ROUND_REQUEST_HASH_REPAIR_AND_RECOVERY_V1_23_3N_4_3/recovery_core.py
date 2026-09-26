"""Control helpers. All scientific identifiers/paths are read from receipts."""
from __future__ import annotations
import ast,hashlib,json,os,re,shlex,subprocess,zipfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'producer'))
from safe_io import canonical_bytes,load_json,sha_file,write_new_bytes,write_new_json

def equal_or_new(path:Path,value)->None:
    data=canonical_bytes(value)
    try:write_new_bytes(path,data)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes()!=data:raise ValueError('IMMUTABLE_CONFLICT:'+str(path))

def require_file(path:Path,expected:str|None=None)->Path:
    if path.is_symlink() or not path.is_file():raise ValueError('REQUIRED_REGULAR_FILE:'+str(path))
    if expected is not None and sha_file(path)!=expected:raise ValueError('INPUT_SHA_CHANGED:'+str(path))
    return path

def cmd(argv,*,timeout=120,cwd=None):
    try:
        cp=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            shell=False,check=False,timeout=timeout,cwd=cwd)
        return {'argv':list(map(str,argv)),'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}
    except subprocess.TimeoutExpired as exc:
        return {'argv':list(map(str,argv)),'returncode':124,'stdout':str(exc.stdout or ''),'stderr':'TIMEOUT:'+str(exc.stderr or '')}

def checked(argv,*,timeout=120,cwd=None):
    r=cmd(argv,timeout=timeout,cwd=cwd)
    if r['returncode']!=0:raise ValueError('COMMAND_FAILED:'+json.dumps(r,ensure_ascii=False)[-4000:])
    return r['stdout'].strip()

def checked_timeout_retry(argv,*,initial_timeout:int,retry_timeout:int,cwd=None):
    if type(initial_timeout) is not int or initial_timeout<=0 or type(retry_timeout) is not int or retry_timeout<=initial_timeout:
        raise ValueError('TIMEOUT_RETRY_POLICY_INVALID')
    frozen_argv=list(map(str,argv))
    first=cmd(frozen_argv,timeout=initial_timeout,cwd=cwd)
    timed_out=(first['returncode']==124 and str(first.get('stderr','')).startswith('TIMEOUT:'))
    if not timed_out:
        if first['returncode']!=0:raise ValueError('COMMAND_FAILED:'+json.dumps(first,ensure_ascii=False)[-4000:])
        return first['stdout'].strip()
    second=cmd(frozen_argv,timeout=retry_timeout,cwd=cwd)
    if second['returncode']!=0:raise ValueError('COMMAND_FAILED:'+json.dumps(second,ensure_ascii=False)[-4000:])
    return second['stdout'].strip()

def parse_runner(path:Path):
    lines=[s.strip() for s in require_file(path).read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if len(lines)!=1 or not lines[0].startswith('exec '):raise ValueError('RUNNER_NOT_SINGLE_EXEC')
    tokens=shlex.split(lines[0][5:])
    if len(tokens)<3 or tokens[1]!='-B' or Path(tokens[2]).name!='shard_worker.py':raise ValueError('RUNNER_EXECUTABLE_SHAPE')
    result={'python':tokens[0],'worker':tokens[2]}
    wanted={'--state-root','--v1230-output-root','--capsule','--shard-plan','--shard-id'}
    rest=tokens[3:]
    if len(rest)!=len(wanted)*2:raise ValueError('RUNNER_UNKNOWN_ARGUMENTS')
    for key,value in zip(rest[::2],rest[1::2]):
        if key not in wanted or key in result:raise ValueError('RUNNER_DUPLICATE_OR_UNKNOWN_FLAG')
        result[key]=value
    if result['--shard-id']!='${SLURM_ARRAY_TASK_ID}':raise ValueError('RUNNER_SHARD_NOT_ALLOCATION_DERIVED')
    for k,v in result.items():
        if k!='--shard-id' and not Path(v).is_absolute():raise ValueError('RUNNER_PATH_NOT_ABSOLUTE:'+k)
    return result

def validate_capsule_missing_fatal(fatal:dict,missing:Path)->str:
    if fatal.get('error_type')!='FileNotFoundError' or fatal.get('assigned_global_ordinals') is not None or fatal.get('scientific_environment_execution_finished') is not False:
        raise ValueError('FATAL_NOT_PRE_SCHEDULE_MISSING_CAPSULE')
    trace=str(fatal.get('traceback',''))
    if 'safe_extract_zip' not in trace:raise ValueError('FATAL_NOT_CAPSULE_EXTRACTION')
    msg=str(fatal.get('error_message',''))
    m=re.fullmatch(r'\[Errno 2\] No such file or directory: (.+)',msg)
    if m is None:raise ValueError('FATAL_FILENAME_NOT_RECOVERABLE:'+msg)
    try:name=ast.literal_eval(m.group(1))
    except (ValueError,SyntaxError) as e:raise ValueError('FATAL_FILENAME_ENCODING') from e
    if not isinstance(name,str) or Path(name)!=missing:raise ValueError('FATAL_MISSING_PATH_NOT_REGISTERED_CAPSULE:'+str(name))
    return name

def check_capsule_inventory(path:Path,inventory:dict)->None:
    expected={r['name']:(r['bytes'],r['crc']) for r in inventory['members']}
    with zipfile.ZipFile(require_file(path)) as z:
        members=z.infolist(); names=[x.filename for x in members]
        if len(names)!=len(set(names)):raise ValueError('CAPSULE_DUPLICATE_MEMBER')
        for row in members:
            p=Path(row.filename)
            if p.is_absolute() or '..' in p.parts or ((row.external_attr>>16)&0o170000)==0o120000:
                raise ValueError('CAPSULE_PATH_ESCAPE_OR_SYMLINK')
            if {'cell_terminals','attempts','results','training_outputs'} & set(p.parts):raise ValueError('CAPSULE_CONTAINS_OUTPUTS')
        observed={x.filename:(x.file_size,x.CRC) for x in members}
        if observed!=expected:raise ValueError('CAPSULE_REVIEWED_INVENTORY_CHANGED')
        if z.testzip() is not None:raise ValueError('CAPSULE_CRC_FAILURE')

def queue_state(rc:int,stdout:str,stderr:str='')->str:
    if rc==0:return 'ACTIVE' if stdout.strip() else 'EMPTY'
    if not stdout.strip() and 'Invalid job id specified' in stderr:return 'NOT_IN_QUEUE'
    return 'UNKNOWN'

def assert_old_array_inactive(job:str,gate:dict,shard_count:int,gate_id:int):
    if not job.isdigit():raise ValueError('ARRAY_ID_INVALID')
    q=cmd(['squeue','--noheader','--jobs',job,'--format','%i|%T'])
    state=queue_state(q['returncode'],q['stdout'],q['stderr'])
    if state not in {'EMPTY','NOT_IN_QUEUE'}:raise ValueError('OLD_ARRAY_NOT_PROVEN_INACTIVE:'+json.dumps(q))
    rows=gate.get('held_sibling_cancellation_results')
    expected={job+'_'+str(i) for i in range(shard_count) if i!=gate_id}
    if not isinstance(rows,list) or len(rows)!=len(expected) or {r.get('target') for r in rows}!=expected or any(r.get('returncode')!=0 for r in rows):
        raise ValueError('HELD_SIBLING_CANCELLATION_PROOF_INCOMPLETE')
    # No assumption that never-started siblings get individual accounting rows.
    a=cmd(['sacct','--noheader','--parsable2','--jobs',job+'_'+str(gate_id),'--format','JobID%100,State%40,ExitCode'])
    if a['returncode']!=0:raise ValueError('GATE_ACCOUNTING_UNAVAILABLE:'+a['stderr'])
    matches=[s.split('|') for s in a['stdout'].splitlines() if s.split('|')[0].strip()==job+'_'+str(gate_id)]
    if len(matches)!=1 or matches[0][1].strip().split()[0].rstrip('+')!='COMPLETED' or matches[0][2].strip()!='0:0':
        raise ValueError('GATE_NOT_ACCOUNTING_TERMINAL')
    return {'queue':q,'gate_accounting':a,'sibling_terminality_authority':'EXACT_GATE_CANCELLATION_RECEIPT_PLUS_NO_ACTIVE_ARRAY'}


def verify_source_identity(package:Path,identity:dict)->None:
    if identity.get('schema_id')!='NATIVE_PRODUCER_PATCH_SOURCE_IDENTITY_V1' or not isinstance(identity.get('files'),dict):
        raise ValueError('PATCH_SOURCE_IDENTITY_SCHEMA')
    for relative,digest in identity['files'].items():
        rel=Path(relative)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('PATCH_SOURCE_PATH_ESCAPE')
        require_file(package/rel,digest)
