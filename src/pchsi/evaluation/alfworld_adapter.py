"""Spawn-only parent adapter for one exact ALFWorld game attempt."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass,replace
import multiprocessing
from pathlib import Path
import time
from .alfworld_contracts import ResetPublicState,StepPublicState,parse_reset_batch,parse_step_batch
from .alfworld_worker import real_alfworld_worker_main
from .alfworld_worker_protocol import CloseRequest,CreateEnvironmentRequest,EnvironmentCreated,ResetRequest,ResetResult,StepRequest,StepResult,WorkerFailure,WorkerMessage,WorkerTerminalStatus,worker_message_from_bytes
from .canonical_evidence import require_lower_sha256

class WorkerAdapterError(RuntimeError): pass
class WorkerTimeoutError(WorkerAdapterError): pass
class WorkerExitedError(WorkerAdapterError): pass
class WorkerProtocolError(WorkerAdapterError): pass
def _get_spawn_context(): return multiprocessing.get_context("spawn")

def _positive(name:str,value:object)->float:
    if type(value) not in (int,float) or float(value)<=0: raise ValueError(f'{name} must be positive numeric')
    return float(value)
@dataclass(frozen=True,slots=True)
class WorkerTimeouts:
    constructor_seconds:float=120.0; reset_seconds:float=60.0; step_seconds:float=60.0; close_seconds:float=30.0; exit_seconds:float=15.0; terminate_grace_seconds:float=5.0; kill_grace_seconds:float=5.0
    def __post_init__(self):
        for name in ('constructor_seconds','reset_seconds','step_seconds','close_seconds','exit_seconds','terminate_grace_seconds','kill_grace_seconds'): _positive(name,getattr(self,name))

class SpawnedAlfworldAdapter:
    def __init__(self,*,exact_gamefile:str,registration_id:str,runtime_manifest_sha256:str,connection,process,timeouts:WorkerTimeouts):
        self._exact_gamefile=exact_gamefile; self._registration_id=registration_id; self._runtime_manifest_sha256=runtime_manifest_sha256; self._connection=connection; self._process=process; self._timeouts=timeouts; self._closed_status=None; self._close_request_sent=False; self._reset_state=None
    @classmethod
    def start(cls,*,exact_gamefile:Path,registration_id:str,runtime_manifest_sha256:str,timeouts:WorkerTimeouts=WorkerTimeouts(),worker_target:Callable[...,None]|None=None)->'SpawnedAlfworldAdapter':
        exact=str(Path(exact_gamefile).resolve())
        if not isinstance(registration_id,str) or not registration_id: raise ValueError('registration_id must be non-empty')
        require_lower_sha256('runtime_manifest_sha256',runtime_manifest_sha256)
        if not isinstance(timeouts,WorkerTimeouts): raise TypeError('timeouts must be WorkerTimeouts')
        target=real_alfworld_worker_main if worker_target is None else worker_target
        if not callable(target): raise TypeError('worker_target must be callable')
        context=_get_spawn_context(); parent,child=context.Pipe(duplex=True)
        request=CreateEnvironmentRequest(exact_gamefile=exact,registration_id=registration_id,runtime_manifest_sha256=runtime_manifest_sha256)
        process=context.Process(target=target,args=(child,request.to_bytes()),daemon=False); process.start(); child.close()
        adapter=cls(exact_gamefile=exact,registration_id=registration_id,runtime_manifest_sha256=runtime_manifest_sha256,connection=parent,process=process,timeouts=timeouts)
        try:
            message=adapter._receive(timeout=timeouts.constructor_seconds,stage='constructor')
            if isinstance(message,WorkerFailure): raise WorkerProtocolError(f'constructor worker failure: {message.error_code}')
            if not isinstance(message,EnvironmentCreated): raise WorkerProtocolError('constructor returned unexpected message')
            if message.exact_gamefile!=exact or message.registration_id!=registration_id: raise WorkerProtocolError('constructor identity mismatch')
        except BaseException:
            adapter._abort_worker(); raise
        return adapter
    @property
    def exact_gamefile(self)->str: return self._exact_gamefile
    @property
    def process_start_method(self)->str: return 'spawn'
    @property
    def worker_pid(self)->int: return -1 if self._process.pid is None else int(self._process.pid)
    @property
    def worker_alive(self)->bool: return bool(self._process.is_alive())
    @property
    def process_exitcode(self)->int|None: return self._process.exitcode
    @property
    def close_request_sent(self)->bool: return self._close_request_sent
    def _receive(self,*,timeout:float,stage:str)->WorkerMessage:
        deadline=time.monotonic()+timeout
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0: self._abort_worker(); raise WorkerTimeoutError(f'{stage} timed out')
            if self._connection.poll(min(remaining,0.05)):
                try: raw=self._connection.recv_bytes()
                except (EOFError,OSError) as error: self._join_if_exited(); raise WorkerExitedError(f'{stage} worker connection closed') from error
                try: return worker_message_from_bytes(raw)
                except (TypeError,ValueError) as error: self._abort_worker(); raise WorkerProtocolError(f'{stage} returned invalid IPC') from error
            if not self._process.is_alive(): self._join_if_exited(); raise WorkerExitedError(f'{stage} worker exited with code {self._process.exitcode}')
    def _join_if_exited(self):
        try: self._process.join(timeout=0)
        except BaseException: pass
    def _wait_join(self,timeout:float)->bool: self._process.join(timeout=timeout); return not self._process.is_alive()
    def _abort_worker(self):
        if self._process.is_alive():
            self._process.terminate()
            if not self._wait_join(self._timeouts.terminate_grace_seconds): self._process.kill(); self._wait_join(self._timeouts.kill_grace_seconds)
        else: self._join_if_exited()
        try: self._connection.close()
        except BaseException: pass
    def _send(self,message,stage:str):
        try: self._connection.send_bytes(message.to_bytes())
        except (BrokenPipeError,EOFError,OSError) as error:
            self._join_if_exited();
            if self.worker_alive: self._abort_worker()
            raise WorkerExitedError(f'{stage} worker connection closed before request') from error
    def reset(self)->ResetPublicState:
        if self._closed_status is not None: raise WorkerProtocolError('reset after close')
        self._send(ResetRequest(),'reset'); message=self._receive(timeout=self._timeouts.reset_seconds,stage='reset')
        if isinstance(message,WorkerFailure): self._abort_worker(); raise WorkerProtocolError(f'reset worker failure: {message.error_code}')
        if not isinstance(message,ResetResult): self._abort_worker(); raise WorkerProtocolError('reset returned unexpected message')
        public=parse_reset_batch(observations=[message.observation],infos={'admissible_commands':[list(message.admissible_commands)],'extra.gamefile':[message.extra_gamefile]},expected_gamefile=Path(self._exact_gamefile)); self._reset_state=public; return public
    def step(self,action:str)->StepPublicState:
        if self._closed_status is not None: raise WorkerProtocolError('step after close')
        if self._reset_state is None: raise WorkerProtocolError('step before reset')
        if not isinstance(action,str) or not action: raise ValueError('action must be non-empty')
        self._send(StepRequest(action=action),'step'); message=self._receive(timeout=self._timeouts.step_seconds,stage='step')
        if isinstance(message,WorkerFailure): self._abort_worker(); raise WorkerProtocolError(f'step worker failure: {message.error_code}')
        if not isinstance(message,StepResult): self._abort_worker(); raise WorkerProtocolError('step returned unexpected message')
        infos={'won':[message.won],'admissible_commands':[list(message.admissible_commands)]}
        if message.extra_gamefile is not None: infos['extra.gamefile']=[message.extra_gamefile]
        return parse_step_batch(result=([message.observation],[message.score],[message.done],infos),gamefile_latch=self._reset_state.gamefile_latch)
    def close(self)->WorkerTerminalStatus:
        if self._closed_status is not None: return self._closed_status
        if not self._process.is_alive():
            self._join_if_exited(); self._closed_status=WorkerTerminalStatus(status='WORKER_ALREADY_EXITED',detail=None,exit_code=self._process.exitcode); return self._closed_status
        self._close_request_sent=True
        try: self._send(CloseRequest(),'close'); message=self._receive(timeout=self._timeouts.close_seconds,stage='close')
        except WorkerTimeoutError:
            self._closed_status=WorkerTerminalStatus(status='CLOSE_TIMEOUT',detail=None,exit_code=self._process.exitcode); return self._closed_status
        except WorkerExitedError:
            self._closed_status=WorkerTerminalStatus(status='CLOSE_WORKER_EXITED',detail=None,exit_code=self._process.exitcode); return self._closed_status
        if isinstance(message,WorkerFailure): self._abort_worker(); self._closed_status=WorkerTerminalStatus(status='CLOSE_FAILURE',detail=message.error_code,exit_code=self._process.exitcode); return self._closed_status
        if not isinstance(message,WorkerTerminalStatus): self._abort_worker(); self._closed_status=WorkerTerminalStatus(status='CLOSE_PROTOCOL_ERROR',detail=None,exit_code=self._process.exitcode); return self._closed_status
        if not self._wait_join(self._timeouts.exit_seconds): self._abort_worker()
        self._closed_status=replace(message,exit_code=self._process.exitcode)
        try: self._connection.close()
        except BaseException: pass
        return self._closed_status
