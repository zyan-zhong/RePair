"""Use the original strategy-receipt SHA dialect at its existing boundary."""
import types
from runtime_overlay import checked

def registered_index_function(source_ref):
    source=checked(source_ref).decode()
    needle="        raw=native_read(receipt['accepted_raw_response_ref'],as_bytes=True)"
    if source.count(needle)!=1:raise ValueError('STRATEGY_REFERENCE_SOURCE_DRIFT')
    source=source.replace(needle,"        raw=_strategy_read(receipt['accepted_raw_response_ref'])")
    from training_binding.materializer import _read_ref
    module=types.ModuleType('_registered_strategy_reference');module.__file__=source_ref['path'];module._strategy_read=_read_ref
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    return module.register
