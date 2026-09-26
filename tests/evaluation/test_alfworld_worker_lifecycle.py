
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import queue
import threading
import time
import pytest
import pchsi.evaluation.alfworld_adapter as adapter_module
from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter,WorkerExitedError,WorkerTimeoutError,WorkerTimeouts
from pchsi.evaluation.alfworld_worker_protocol import CloseRequest,CreateEnvironmentRequest,EnvironmentCreated,ResetRequest,ResetResult,StepRequest,StepResult,WorkerTerminalStatus,worker_message_from_bytes

class _Endpoint:
    def __init__(self,incoming,outgoing): self._incoming=incoming; self._outgoing=outgoing; self._closed=False; self._stash=None
    def send_bytes(self,value):
        if self._closed: raise OSError('closed')
        self._outgoing.put(value)
    def poll(self,timeout=0):
        if self._stash is not None: return True
        try: self._stash=self._incoming.get(timeout=timeout); return True
        except queue.Empty: return False
    def recv_bytes(self):
        if self._stash is not None: value=self._stash; self._stash=None; return value
        return self._incoming.get()
    def close(self): pass
class _FakeProcess:
    _pid=60000
    def __init__(self,*,target,args,daemon):
        type(self)._pid+=1; self.pid=type(self)._pid; self.exitcode=None; self._target=target; self._args=args; self._killed=False; self._thread=None; self.error=None
    def _run(self):
        try: self._target(*self._args)
        except SystemExit as e: self.exitcode=e.code if type(e.code) is int else 1
        except BaseException as e: self.error=repr(e); self.exitcode=1
        else: self.exitcode=0
    def start(self): self._thread=threading.Thread(target=self._run,daemon=True); self._thread.start()
    def is_alive(self): return self._thread is not None and self._thread.is_alive() and not self._killed
    def join(self,timeout=None):
        if self._thread is not None: self._thread.join(timeout)
    def terminate(self): self._killed=True; self.exitcode=-15
    def kill(self): self._killed=True; self.exitcode=-9
class _FakeContext:
    def Pipe(self,duplex=True):
        a,b=queue.Queue(),queue.Queue(); return _Endpoint(a,b),_Endpoint(b,a)
    def Process(self,*,target,args,daemon): return _FakeProcess(target=target,args=args,daemon=daemon)
@pytest.fixture(autouse=True)
def _fake_context(monkeypatch): monkeypatch.setattr(adapter_module,'_get_spawn_context',lambda:_FakeContext())
def _send(c,m): c.send_bytes(m.to_bytes())
def _timeouts(): return WorkerTimeouts(constructor_seconds=2,reset_seconds=.15,step_seconds=.15,close_seconds=.15,exit_seconds=.15,terminate_grace_seconds=.05,kill_grace_seconds=.05)
def _game(tmp_path): p=tmp_path/'game.tw-pddl'; p.write_text('{}\n',encoding='utf-8'); return p

def normal_worker(c,raw):
    create=worker_message_from_bytes(raw); _send(c,EnvironmentCreated(create.exact_gamefile,create.registration_id))
    while True:
        msg=worker_message_from_bytes(c.recv_bytes())
        if isinstance(msg,ResetRequest): _send(c,ResetResult('initial',('look','inventory'),create.exact_gamefile))
        elif isinstance(msg,StepRequest): _send(c,StepResult('after:'+msg.action,('inventory',),0,False,False,None))
        elif isinstance(msg,CloseRequest): _send(c,WorkerTerminalStatus('CLOSED',None,None)); return

def ctor_hang(c,raw): time.sleep(10)
def reset_hang(c,raw):
    create=worker_message_from_bytes(raw); _send(c,EnvironmentCreated(create.exact_gamefile,create.registration_id)); assert isinstance(worker_message_from_bytes(c.recv_bytes()),ResetRequest); time.sleep(10)
def step_hang(c,raw):
    create=worker_message_from_bytes(raw); _send(c,EnvironmentCreated(create.exact_gamefile,create.registration_id)); assert isinstance(worker_message_from_bytes(c.recv_bytes()),ResetRequest); _send(c,ResetResult('initial',('look',),create.exact_gamefile)); assert isinstance(worker_message_from_bytes(c.recv_bytes()),StepRequest); time.sleep(10)
def close_hang(c,raw):
    create=worker_message_from_bytes(raw); _send(c,EnvironmentCreated(create.exact_gamefile,create.registration_id)); assert isinstance(worker_message_from_bytes(c.recv_bytes()),CloseRequest); time.sleep(10)
def exits(c,raw):
    create=worker_message_from_bytes(raw); _send(c,EnvironmentCreated(create.exact_gamefile,create.registration_id)); raise SystemExit(7)

def test_constructor_reset_step_close_timeouts_are_classified(tmp_path):
    with pytest.raises(WorkerTimeoutError,match='constructor'): SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='ctor',runtime_manifest_sha256='a'*64,timeouts=replace(_timeouts(),constructor_seconds=.15),worker_target=ctor_hang)
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='reset',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=reset_hang)
    with pytest.raises(WorkerTimeoutError,match='reset'): a.reset()
    assert not a.worker_alive
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='step',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=step_hang); a.reset()
    with pytest.raises(WorkerTimeoutError,match='step'): a.step('look')
    assert not a.worker_alive
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='close',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=close_hang)
    assert a.close().status=='CLOSE_TIMEOUT'; assert not a.worker_alive

def test_unexpected_worker_death_is_classified(tmp_path):
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='exit',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=exits)
    with pytest.raises(WorkerExitedError): a.reset()
    assert not a.worker_alive and a.process_exitcode==7

def test_close_is_sent_at_most_once(tmp_path):
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='close-once',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=normal_worker)
    first=a.close(); second=a.close(); assert first==second and first.status=='CLOSED' and a.close_request_sent and not a.worker_alive

def test_terminate_then_kill_then_join_reaps_worker(tmp_path):
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='reap',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=close_hang)
    assert a.close().status=='CLOSE_TIMEOUT'; assert not a.worker_alive and a.process_exitcode is not None
