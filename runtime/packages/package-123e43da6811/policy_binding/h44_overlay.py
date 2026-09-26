"""Exact H4.4 vendor launch adapter, inherited by the existing GPU job."""
import hashlib
import importlib.abc
import importlib.util
import os
from pathlib import Path
import sys

BASE_SHA256='b72888cd5d323a8acd657cd77e1938235a8ed5bdf395a6e6261ffea5baa44a4d'
H44_ENV='PCHSI_CURRENT_H44_REGISTERED_ROOT'
_installed=None


class _Loader(importlib.abc.Loader):
    def __init__(self,path,raw): self.path,self.raw=path,raw
    def create_module(self,spec): return None
    def exec_module(self,module):
        exec(compile(self.raw,str(self.path),'exec'),module.__dict__)
        original=module.build_current_runtime_service_launch_contract
        from policy_binding.launch import extend_lora_launch
        def build_current_runtime_service_launch_contract(runtime,profile,*,python_executable):
            return extend_lora_launch(original(runtime,profile,python_executable=python_executable),runtime)
        module.build_current_runtime_service_launch_contract=build_current_runtime_service_launch_contract
        module.__current_lora_source_sha256__=BASE_SHA256


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self,path,raw): self.path,self.raw=path,raw
    def find_spec(self,fullname,path=None,target=None):
        if fullname!='policy_runtime_engine_profile': return None
        return importlib.util.spec_from_file_location(fullname,self.path,loader=_Loader(self.path,self.raw))


def configure_h44_workers(root):
    global _installed
    root=Path(root).absolute()
    path=root/'vendor/policy_runtime_engine_profile.py'
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA256:
        raise ValueError('H44_LORA_SOURCE_IDENTITY')
    if _installed is not None:
        if _installed.path!=path: raise ValueError('H44_LORA_SOURCE_ROOT_CONFLICT')
    else:
        if 'policy_runtime_engine_profile' in sys.modules:
            raise ValueError('H44_LORA_INSTALL_BEFORE_VENDOR_IMPORT')
        _installed=_Finder(path,raw);sys.meta_path.insert(0,_installed)
    os.environ[H44_ENV]=str(root)
    return {'native_source_path':str(path),'native_source_sha256':BASE_SHA256,
            'base_files_modified':False,'provider_calls_added':0}
