"""Exact native executor overlay: replace only parent execution by audited reuse."""
from contextlib import contextmanager
from unittest.mock import patch
from pathlib import Path
import inspect,types

def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('REGISTERED_REUSE_OVERLAY_ANCHOR_CHANGED')
    return text.replace(old,new)

def executor_source(text):
    # All original candidate execution, budget, server, integrity and arithmetic remain.
    text=text.replace('    live, audit, aggregate, server, types, loader = native.runners()',
        '    cache = cache_for(binding_ref, context)\n    live, audit, aggregate, server, types, loader = native.runners()')
    text=replace_once(text,'        live, audit, aggregate, _, _, loader = native.runners()',
        '        cache = cache_for(binding_ref, context)\n        live, audit, aggregate, _, _, loader = native.runners()')
    text=text.replace('live.load_receipts(', 'cache_receipts(cache, live, ')
    text=replace_once(text,"        for label, bundle in context['bundles'].items():\n            for ordinal in ordinals:",
        "        for label, bundle in context['bundles'].items():\n            if cache is not None and label == 'parent':continue\n            for ordinal in ordinals:")
    text=replace_once(text,"                for label in ('parent', 'candidate'):\n                    need(process.poll() is None, 'OWNED_OFFOFF_SERVER_EXITED')",
        "                for label in ('parent', 'candidate'):\n                    if cache is not None and label == 'parent':\n                        row, metadata = cache.adopt(ordinal, execution)\n                        audits.append({'label':label,'ordinal':ordinal,**metadata})\n                        continue\n                    need(process.poll() is None, 'OWNED_OFFOFF_SERVER_EXITED')")
    old="""                loaded = loader.load_attempt_directory_v1(evaluator / 'attempts' / row['execution_attempt_id'])
                metadata = _audit_one(audit=audit,native_audit=audit_native,loaded=loaded,row=row,
                    expected=expected_map[(label,cell.condition_cell_id)],bundle=bundle,
                    protocol=context['protocol'],infra=context['infra'],access=context['access'],root=evaluator)"""
    new="""                if cache is not None and label == 'parent':
                    row, metadata = cache.audit_adopted(ordinal, root)
                else:
                    loaded = loader.load_attempt_directory_v1(evaluator / 'attempts' / row['execution_attempt_id'])
                    metadata = _audit_one(audit=audit,native_audit=audit_native,loaded=loaded,row=row,
                        expected=expected_map[(label,cell.condition_cell_id)],bundle=bundle,
                        protocol=context['protocol'],infra=context['infra'],access=context['access'],root=evaluator)"""
    text=replace_once(text,old,new)
    text=text.replace("'schema_id': 'CURRENT_OFFOFF_IDENTITY_AUDIT_V1', 'binding_ref': binding_ref,",
        "'schema_id': 'CURRENT_OFFOFF_IDENTITY_AUDIT_V2' if cache else 'CURRENT_OFFOFF_IDENTITY_AUDIT_V1', 'binding_ref': binding_ref,")
    text=text.replace("audit.get('schema_id') == 'CURRENT_OFFOFF_IDENTITY_AUDIT_V1'", "audit.get('schema_id') in ('CURRENT_OFFOFF_IDENTITY_AUDIT_V1','CURRENT_OFFOFF_IDENTITY_AUDIT_V2')")
    return text

@contextmanager
def installed():
    import offoff_binding.execute as execution
    import offoff_binding.parallel as parallel
    from parent_cache import cache_for,receipts
    # Reuse the registered source file. No copied fork of the native evaluator.
    source=Path(execution.__file__).read_text();namespace=dict(vars(execution))
    exec(compile(executor_source(source),execution.__file__,'exec'),namespace)
    # Keep already installed goal collector/write/decider wrappers.
    for key in ('write_once','freeze_registered_promotion','_registered_decider','_audit_one','prepare','materialize'):
        namespace[key]=getattr(execution,key)
    namespace.update(cache_for=cache_for,cache_receipts=receipts)
    with patch.object(execution,'execute_binding',namespace['execute_binding']),patch.object(execution,'finalize_binding',namespace['finalize_binding']),patch.object(execution,'validate_completed_offoff_terminal',namespace['validate_completed_offoff_terminal']),patch.object(parallel,'execute_binding',namespace['execute_binding']),patch.object(parallel,'finalize_binding',namespace['finalize_binding']):yield
