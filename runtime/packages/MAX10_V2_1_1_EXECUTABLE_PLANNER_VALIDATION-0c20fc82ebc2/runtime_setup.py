"""Reuse registered child/bootstrap and credential transport scopes."""
from pathlib import Path
from contextlib import contextmanager
import json,sys

def child_bootstrap(a):
    from entry_v208 import checked,digest,load_module
    root=Path(a['native_entry_root'])
    if digest(root/'PACKAGE_FILES.sha256')!=a['native_entry_manifest_sha256']:raise ValueError('NATIVE_CHILD_ENTRY_CHANGED')
    sys.path.insert(0,str(root));sys.path.insert(0,str(root/'live_adapter'))
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(checked(a['source_binding_ref'])['scientific_repo_root'])
    reader=a['trained_reader'];reader_root=Path(reader['root']);sys.path.insert(0,str(reader_root))
    profile=load_module('_registered_trained_reader_entry',reader_root/'profile_entry.py')
    if profile.verify()!=reader['manifest_sha256']:raise ValueError('TRAINED_READER_CHANGED')
    from runtime_overlay import configure
    configure(json.loads((reader_root/'AUTHORITY.json').read_bytes()),reader_root,reader['manifest_sha256'])

@contextmanager
def cognitive(binding,a):
    from entry_v208 import checked,load_module,digest
    import transport_entry
    from transport_scope import bound_scope,install_executor,retry_pacing
    from pacing import registered_transport
    from pchsi.cognitive_runtime import orchestrator
    environment_ref=a['environment_module_ref'];checked(environment_ref,as_bytes=True)
    environment=load_module('_registered_validation_environment',Path(environment_ref['path']))
    initialization=checked(a['environment_authority_ref'])['environment_initialization']
    if digest(transport_entry.ROOT/'PACKAGE_FILES.sha256')!=a['transport_manifest_sha256']:raise ValueError('TRANSPORT_SOURCE_CHANGED')
    transport=json.loads((transport_entry.ROOT/'AUTHORITY.json').read_bytes())
    scope=bound_scope(binding,binding['campaign_startup_authority'])
    with environment.environment_scope(initialization),install_executor(scope),retry_pacing(orchestrator,registered_transport()),\
         transport_entry.installed_transport(transport,a['transport_manifest_sha256']):yield

@contextmanager
def post_representation(a):
    from entry_v208 import checked,digest
    from unittest.mock import patch
    from pchsi.reference_loop.canonical import domain_hash
    from lossless_context import encode_bundle
    from exact_bindings import immutable_json,file_ref
    feedback=json.loads((Path(a['feedback_worker_ref']['path']).parent/'AUTHORITY.json').read_bytes())
    registration=feedback['repair_sources']['planner_context'];root=Path(registration['root'])
    if digest(root/'PACKAGE_FILES.sha256')!=registration['manifest_sha256']:raise ValueError('POST_CONTEXT_SOURCE_CHANGED')
    sys.path.insert(0,str(root));import post_context
    original=post_context.renderer
    def renderer(native,**kw):
        proof=[None];record=kw['record']
        def render(**args):
            bundle=native(**args)
            if args['stage_id']=='R-POST-PRIMARY-V1':bundle,proof[0]=encode_bundle(bundle,kw['policy']['max_provider_request_body_bytes'],domain_hash)
            return bundle
        def registered(bundle,view,size):
            request=checked(file_ref(Path(sys.argv[sys.argv.index('--request')+1])))
            immutable_json(Path(request['run_root'])/'post/REGISTERED_LOSSLESS_CONTEXT_BINDING.json',{
                'proof':proof[0],'request_body_sha256':bundle['request_body_sha256'],'body_bytes':size})
            return record(bundle,view,size)
        return original(render,**{**kw,'record':registered})
    with patch.object(post_context,'renderer',renderer):yield
