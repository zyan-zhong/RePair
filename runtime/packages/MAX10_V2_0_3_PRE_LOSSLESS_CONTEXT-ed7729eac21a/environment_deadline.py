"""Keep the native secret-safe loader; source-bind its startup deadline."""
from pathlib import Path
import hashlib,ast

def loader(authority, module):
    ref=authority['environment_loader_source_ref'];raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256'] or Path(module.__file__)!=Path(ref['path']):
        raise ValueError('ENVIRONMENT_LOADER_SOURCE_CHANGED')
    timeout=authority['environment_policy']['initialization_timeout_seconds']
    if type(timeout) not in (int,float) or not 0<timeout<=authority['environment_policy']['maximum_initialization_timeout_seconds']:
        raise ValueError('ENVIRONMENT_DEADLINE_POLICY_INVALID')
    source=raw.decode();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='load_environment')
    function=ast.get_source_segment(source,node);anchor='time.monotonic()+60'
    if function.count(anchor)!=1:raise ValueError('ENVIRONMENT_DEADLINE_SOURCE_ANCHOR')
    namespace={**module.__dict__,'_registered_initialization_timeout':timeout}
    exec(compile(function.replace(anchor,'time.monotonic()+_registered_initialization_timeout'),ref['path'],'exec'),namespace)
    return namespace['load_environment']
