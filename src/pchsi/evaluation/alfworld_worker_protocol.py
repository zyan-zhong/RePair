"""Closed canonical IPC messages for the E1 ALFWorld worker boundary."""
from __future__ import annotations
from dataclasses import dataclass,fields
from pathlib import Path
from typing import ClassVar
from .canonical_evidence import canonical_json_bytes,require_finite_number,require_lower_sha256,require_nonnegative_int,strict_json_loads

def _text(name:str,value:object,*,allow_empty:bool=False)->str:
    if not isinstance(value,str) or (not allow_empty and not value): raise ValueError(f"{name} must be a {'string' if allow_empty else 'non-empty string'}")
    return value

def _abs(name:str,value:object)->str:
    text=_text(name,value)
    if not Path(text).is_absolute(): raise ValueError(f'{name} must be absolute')
    return text

def _commands(value:object)->tuple[str,...]:
    if not isinstance(value,(list,tuple)): raise TypeError('admissible_commands must be an array')
    if any(not isinstance(x,str) for x in value): raise TypeError('admissible_commands items must be strings')
    return tuple(value)

class WorkerMessage:
    MESSAGE_TYPE: ClassVar[str]
    def to_dict(self)->dict[str,object]:
        out={'message_type':self.MESSAGE_TYPE}
        for f in fields(self):
            value=getattr(self,f.name)
            out[f.name]=list(value) if f.name=='admissible_commands' else value
        return out
    def to_bytes(self)->bytes: return canonical_json_bytes(self.to_dict())

@dataclass(frozen=True,slots=True)
class CreateEnvironmentRequest(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='CREATE_ENVIRONMENT_REQUEST'
    exact_gamefile:str; registration_id:str; runtime_manifest_sha256:str
    def __post_init__(self): _abs('exact_gamefile',self.exact_gamefile); _text('registration_id',self.registration_id); require_lower_sha256('runtime_manifest_sha256',self.runtime_manifest_sha256)
@dataclass(frozen=True,slots=True)
class ResetRequest(WorkerMessage): MESSAGE_TYPE: ClassVar[str]='RESET_REQUEST'
@dataclass(frozen=True,slots=True)
class StepRequest(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='STEP_REQUEST'; action:str
    def __post_init__(self): _text('action',self.action)
@dataclass(frozen=True,slots=True)
class CloseRequest(WorkerMessage): MESSAGE_TYPE: ClassVar[str]='CLOSE_REQUEST'
@dataclass(frozen=True,slots=True)
class EnvironmentCreated(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='ENVIRONMENT_CREATED'; exact_gamefile:str; registration_id:str
    def __post_init__(self): _abs('exact_gamefile',self.exact_gamefile); _text('registration_id',self.registration_id)
@dataclass(frozen=True,slots=True)
class ResetResult(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='RESET_RESULT'; observation:str; admissible_commands:tuple[str,...]; extra_gamefile:str
    def __post_init__(self): _text('observation',self.observation,allow_empty=True); _commands(self.admissible_commands); _abs('extra_gamefile',self.extra_gamefile)
@dataclass(frozen=True,slots=True)
class StepResult(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='STEP_RESULT'; observation:str; admissible_commands:tuple[str,...]; score:int|float; done:bool; won:bool; extra_gamefile:str|None
    def __post_init__(self):
        _text('observation',self.observation,allow_empty=True); _commands(self.admissible_commands); require_finite_number('score',self.score)
        if type(self.done) is not bool or type(self.won) is not bool: raise TypeError('done and won must be bool')
        if self.extra_gamefile is not None: _abs('extra_gamefile',self.extra_gamefile)
@dataclass(frozen=True,slots=True)
class WorkerFailure(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='WORKER_FAILURE'; stage:str; error_code:str; exception_type:str; message:str
    def __post_init__(self):
        _text('stage',self.stage); _text('error_code',self.error_code); _text('exception_type',self.exception_type); _text('message',self.message,allow_empty=True)
        if len(self.message)>512: raise ValueError('message exceeds 512 characters')
@dataclass(frozen=True,slots=True)
class WorkerTerminalStatus(WorkerMessage):
    MESSAGE_TYPE: ClassVar[str]='WORKER_TERMINAL_STATUS'; status:str; detail:str|None; exit_code:int|None
    def __post_init__(self):
        _text('status',self.status)
        if self.detail is not None: _text('detail',self.detail)
        if self.exit_code is not None and type(self.exit_code) is not int: raise TypeError('exit_code must be int or None')

_TYPES={c.MESSAGE_TYPE:c for c in (CreateEnvironmentRequest,ResetRequest,StepRequest,CloseRequest,EnvironmentCreated,ResetResult,StepResult,WorkerFailure,WorkerTerminalStatus)}

def worker_message_from_dict(value:object)->WorkerMessage:
    if not isinstance(value,dict) or any(not isinstance(k,str) for k in value): raise TypeError('worker message must be an object with string keys')
    message_type=value.get('message_type')
    if not isinstance(message_type,str) or message_type not in _TYPES: raise ValueError('unknown worker message_type')
    cls=_TYPES[message_type]; expected={'message_type',*(f.name for f in fields(cls))}; observed=set(value)
    missing=sorted(expected-observed); unknown=sorted(observed-expected)
    if missing: raise ValueError(f'missing required fields: {missing}')
    if unknown: raise ValueError(f'unknown fields: {unknown}')
    kwargs={f.name:value[f.name] for f in fields(cls)}
    if 'admissible_commands' in kwargs: kwargs['admissible_commands']=_commands(kwargs['admissible_commands'])
    return cls(**kwargs)

def worker_message_from_bytes(value:bytes)->WorkerMessage:
    if not isinstance(value,bytes): raise TypeError('worker message bytes must be bytes')
    return worker_message_from_dict(strict_json_loads(value))
