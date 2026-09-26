from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
def rebind_memory_reader(function,reader_factory):
    """Retain the registered budget wrapper and replace its native reader only."""
    import types
    namespace=dict(function.__globals__);closure=function.__closure__
    if '_read' in function.__code__.co_names:
        namespace['_read']=reader_factory(namespace['_read'])
    else:
        names=function.__code__.co_freevars
        if 'native' not in names:raise ValueError('MEMORY_REGISTERED_NATIVE_WRAPPER_REQUIRED')
        cells=list(closure);index=names.index('native')
        rebound=rebind_memory_reader(cells[index].cell_contents,reader_factory)
        cells[index]=(lambda value:lambda:value)(rebound).__closure__[0];closure=tuple(cells)
    result=types.FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,closure)
    result.__kwdefaults__=function.__kwdefaults__
    return result

@contextmanager
def memory_reuse_context(module,authority,candidate_universe_ref):
    import one_validation as native
    native._source_inputs(authority)
    root=native._path(authority['source_analyzer_root'])
    lookup={root/relative:authority['source_files'][role] for role,relative in native.SOURCE_FILES.items()}
    lookup[root/native.SOURCE_FILES['universe']]=candidate_universe_ref
    native.read_ref(candidate_universe_ref)
    def factory(original):
        def read(path):
            path=native._path(path)
            return native.read_ref(lookup[path]) if path in lookup else original(path)
        return read
    producer=rebind_memory_reader(module.materialize_round_memory,factory)
    def reused(**kw):return producer(**{**kw,'analyzer_output_root':root})
    with patch.object(module,'materialize_round_memory',reused):yield

