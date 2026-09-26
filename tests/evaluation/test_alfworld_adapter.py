
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

def public_worker(c,raw):
    create=worker_message_from_bytes(raw); _send(c,EnvironmentCreated(create.exact_gamefile,create.registration_id))
    while True:
        msg=worker_message_from_bytes(c.recv_bytes())
        if isinstance(msg,ResetRequest): _send(c,ResetResult('reset observation',('look','look','inventory'),create.exact_gamefile))
        elif isinstance(msg,StepRequest): _send(c,StepResult('step observation',('inventory','go north'),1,True,True,None))
        elif isinstance(msg,CloseRequest): _send(c,WorkerTerminalStatus('CLOSED',None,None)); return

def test_adapter_uses_spawn_context_and_rejects_fork_fallback(tmp_path):
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='spawn',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=public_worker)
    assert a.process_start_method=='spawn'
    source=Path(adapter_module.__file__).read_text(encoding='utf-8'); assert ("multiprocessing.get_context('spawn')" in source or 'multiprocessing.get_context("spawn")' in source); assert "get_context('fork')" not in source and 'get_context("fork")' not in source
    a.close()
def test_one_worker_handles_one_exact_gamefile(tmp_path):
    game=_game(tmp_path); a=SpawnedAlfworldAdapter.start(exact_gamefile=game,registration_id='one',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=public_worker); assert a.exact_gamefile==str(game.resolve()) and a.worker_pid>0; a.close()
def test_reset_and_step_return_only_public_fields(tmp_path):
    a=SpawnedAlfworldAdapter.start(exact_gamefile=_game(tmp_path),registration_id='public',runtime_manifest_sha256='a'*64,timeouts=_timeouts(),worker_target=public_worker)
    reset=a.reset(); assert reset.menu.commands==('look','look','inventory')
    step=a.step('look'); assert step.observation=='step observation' and step.done and step.won
    assert a.close().status=='CLOSED'
def test_real_environment_import_is_lazy_and_not_reached_by_tests():
    import subprocess,sys,os
    code="import sys; import pchsi.evaluation.alfworld_worker; import pchsi.evaluation.alfworld_adapter; assert all(x not in sys.modules for x in ('alfworld','textworld','gym')); print('TASK5_LAZY_IMPORT_OK')"
    env=os.environ.copy(); env['PYTHONPATH']=str(Path(__file__).resolve().parents[2]/'src')
    result=subprocess.run([sys.executable,'-S','-c',code],text=True,capture_output=True,env=env)
    assert result.returncode==0,result.stderr; assert 'TASK5_LAZY_IMPORT_OK' in result.stdout
