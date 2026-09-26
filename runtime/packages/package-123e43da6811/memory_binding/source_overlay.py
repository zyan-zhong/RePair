"""Auditable in-memory edits to exact bba400 sources; base files stay immutable."""
import ast
import hashlib
import importlib.abc
import importlib.util
from pathlib import Path
import sys

BASE_SHA256 = {
 'pchsi.memory.round_maintenance':'65c860667587869533f0a570b694c5b14bb28eb4dc33bb03f9ab99fcf61ecd6e',
 'pchsi.memory.sequence_failure_experience':'b949b83c10ecbb0bf521431fec5d32b363c46847c9bb487fb47514097f3dad58',
 'pchsi.memory.matched_raw_view':'a3caecd9e3b551a3ab64e8319a47a6118b92b47891b42080451979d9213b03b8',
 'pchsi.memory.consumer_views':'78bc0275984fa369d22934d829bc74c47b9bfca2bfb765e23680f8652000777a',
 'pchsi.memory.component_ports':'fef4f74e4098dc2847e59617cabe84595af37118db23bf8099b758d906bdfa57',
 'pchsi.cognitive_runtime.request_renderer':'27eb63847ab827b98290ce102d02850650cefc0dc2b3ae74681a5d51645125b9',
 'pchsi.cognitive_runtime.output_validation':'0b468a3401fcd2c5ff2a90884200a01d76de88029124a91429e9c6b3b37d7f22',
}
_installed = None


def adapt_source(name, raw):
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA256[name]:
        raise ValueError('NATIVE_MEMORY_SOURCE_DRIFT:' + name)
    source=raw.decode('utf8')
    def replace(old,new,count=1):
        nonlocal source
        if source.count(old)!=count:
            raise ValueError('MEMORY_OVERLAY_ANCHOR:' + name + ':' + old[:70])
        source=source.replace(old,new)
    if name.endswith('sequence_failure_experience'):
        replace('from typing import ClassVar', 'from typing import ClassVar\nfrom memory_binding.current_source import SequenceSourceTaskAccessBindingV2, validate_current_source_record')
        replace('isinstance(self.task_access_binding, SequenceSourceTaskAccessBindingV1)',
                'isinstance(self.task_access_binding, (SequenceSourceTaskAccessBindingV1, SequenceSourceTaskAccessBindingV2))')
        replace('isinstance(task_access_binding, SequenceSourceTaskAccessBindingV1)',
                'isinstance(task_access_binding, (SequenceSourceTaskAccessBindingV1, SequenceSourceTaskAccessBindingV2))')
        replace('task_access_binding=SequenceSourceTaskAccessBindingV1.from_dict(\n                value["task_access_binding"]\n            )',
                'task_access_binding=(SequenceSourceTaskAccessBindingV2 if value["task_access_binding"].get("schema_id") == "SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V2" else SequenceSourceTaskAccessBindingV1).from_dict(value["task_access_binding"])')
        replace('    if source.task_access_record_line_index != binding.task_access_record_line_index:',
                '    if isinstance(binding, SequenceSourceTaskAccessBindingV2):\n        return validate_current_source_record(source, binding)\n    if source.task_access_record_line_index != binding.task_access_record_line_index:')
    elif name.endswith('round_maintenance'):
        replace('    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"',
                '    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"\n    TRAIN_UPDATE = "TRAIN_UPDATE"')
    elif name.endswith('matched_raw_view'):
        replace('        access.task_access_protected_manifest_sha256,',
                '        (access.task_manifest_sha256 if hasattr(access, "task_manifest_sha256") else access.task_access_protected_manifest_sha256),')
    elif name.endswith('consumer_views'):
        replace('    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"',
                '    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"\n    TRAIN_UPDATE = "TRAIN_UPDATE"')
        replace('        if row.get("source_partition") != (\n            MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE.value\n        ):',
                '        if row.get("source_partition") not in {MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE.value, MemorySourcePartitionV1.TRAIN_UPDATE.value}:')
        replace('        if binding.source_partition is not (\n            MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE\n        ):',
                '        if binding.source_partition not in {MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE, MemorySourcePartitionV1.TRAIN_UPDATE}:')
        replace('        fields = (\n            self.source_collection_manifest_sha256,',
                '        if self.source_partition is MemorySourcePartitionV1.TRAIN_UPDATE and self.authority_scope is not MemoryPartitionAuthorityScopeV1.FULL_TRAIN_SOURCE_PROVENANCE:\n            raise ValueError("TRAIN_UPDATE requires verified full current source provenance")\n        fields = (\n            self.source_collection_manifest_sha256,')
    elif name.endswith('component_ports'):
        replace('    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"',
                '    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"\n    TRAIN_UPDATE = "TRAIN_UPDATE"')
        replace('self.source_partition is MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE',
                'self.source_partition in {MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE, MemorySourcePartitionV1.TRAIN_UPDATE}')
        replace('source_partition is MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE',
                'source_partition in {MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE, MemorySourcePartitionV1.TRAIN_UPDATE}')
    elif name.endswith('request_renderer'):
        replace('        schema = _specialize_local_selector_enums(schema, selectors)',
                '        schema = _specialize_local_selector_enums(schema, selectors)\n        from memory_binding.same_call import extend_local_schema, extend_local_prompt\n        schema = extend_local_schema(schema)\n        prompt = extend_local_prompt(prompt)')
    elif name.endswith('output_validation'):
        replace('  value["raw_response_sha256"]=raw_response_sha256\n  value=finalize_local_result(value)\n  return validate_local_result(value,evidence_pack=projection["evidence_pack"])',
                '  from memory_binding.same_call import validate_boundaries\n  boundary_rows=value.pop("memory_boundary_registrations")\n  value["raw_response_sha256"]=raw_response_sha256\n  value=finalize_local_result(value)\n  value=validate_local_result(value,evidence_pack=projection["evidence_pack"])\n  validate_boundaries(boundary_rows,value)\n  return value')
    ast.parse(source)
    return source


class _Loader(importlib.abc.Loader):
    def __init__(self,name,path,source): self.name,self.path,self.source=name,path,source
    def create_module(self,spec): return None
    def exec_module(self,module):
        module.__memory_overlay_sha256__=hashlib.sha256(self.source.encode()).hexdigest()
        exec(compile(self.source,str(self.path),'exec'),module.__dict__)


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self,repo,sources): self.repo,self.sources=repo,sources
    def find_spec(self,fullname,path=None,target=None):
        if fullname not in self.sources: return None
        base=self.repo/'src'/(fullname.replace('.','/')+'.py')
        return importlib.util.spec_from_file_location(fullname,base,loader=_Loader(fullname,base,self.sources[fullname]))


def install_memory_overlay(repo):
    global _installed
    repo=Path(repo).absolute()
    if _installed is not None:
        if _installed.repo!=repo: raise ValueError('MEMORY_OVERLAY_REPO_CONFLICT')
        return overlay_receipt()
    if any(name in sys.modules for name in BASE_SHA256):
        raise ValueError('INSTALL_MEMORY_OVERLAY_BEFORE_NATIVE_IMPORTS')
    sources={name:adapt_source(name,(repo/'src'/(name.replace('.','/')+'.py')).read_bytes()) for name in BASE_SHA256}
    _installed=_Finder(repo,sources)
    sys.meta_path.insert(0,_installed)
    sys.path.insert(0,str(repo/'src'))
    return overlay_receipt()


def adapted_sources():
    if _installed is None: raise ValueError('MEMORY_OVERLAY_NOT_INSTALLED')
    return dict(_installed.sources)


def overlay_receipt():
    return {'schema_id':'CURRENT_TRAIN_UPDATE_MEMORY_SOURCE_OVERLAY_V1',
        'native_repo':str(_installed.repo),'base_source_sha256':BASE_SHA256,
        'adapted_source_sha256':{name:hashlib.sha256(source.encode()).hexdigest() for name,source in _installed.sources.items()},
        'provider_calls_added':0,'base_files_modified':False,'v1_source_constraints_changed':False}
