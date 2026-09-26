"""Fresh-process ALFWorld worker with lazy real-runtime imports."""
from __future__ import annotations
from pathlib import Path
from .alfworld_contracts import GamefileIdentityLatch,parse_reset_batch,parse_step_batch
from .alfworld_worker_protocol import CloseRequest,CreateEnvironmentRequest,EnvironmentCreated,ResetRequest,ResetResult,StepRequest,StepResult,WorkerFailure,WorkerTerminalStatus,worker_message_from_bytes

def _send(connection,message)->None: connection.send_bytes(message.to_bytes())
def _failure(stage:str,error:BaseException)->WorkerFailure:
    message=str(error)[:512]
    return WorkerFailure(stage=stage,error_code=f'{stage.upper()}_FAILED',exception_type=type(error).__name__,message=message)

def real_alfworld_worker_main(connection,create_request_bytes:bytes)->None:
    env=None; stage='constructor'; latch:GamefileIdentityLatch|None=None
    try:
        create=worker_message_from_bytes(create_request_bytes)
        if not isinstance(create,CreateEnvironmentRequest): raise TypeError('initial message must be CreateEnvironmentRequest')
        import textworld
        import textworld.gym
        from alfworld.agents.environment.alfred_tw_env import AlfredDemangler,AlfredInfos
        request_infos=textworld.EnvInfos(won=True,admissible_commands=True,extras=['gamefile'])
        env_id=textworld.gym.register_games([create.exact_gamefile],request_infos,batch_size=1,asynchronous=False,auto_reset=False,max_episode_steps=31,wrappers=[AlfredDemangler(shuffle=False),AlfredInfos],name=create.registration_id)
        env=textworld.gym.make(env_id)
        _send(connection,EnvironmentCreated(exact_gamefile=create.exact_gamefile,registration_id=create.registration_id))
        while True:
            message=worker_message_from_bytes(connection.recv_bytes())
            if isinstance(message,ResetRequest):
                stage='reset'; observations,infos=env.reset(); public=parse_reset_batch(observations=observations,infos=infos,expected_gamefile=Path(create.exact_gamefile)); latch=public.gamefile_latch
                _send(connection,ResetResult(observation=public.observation,admissible_commands=public.menu.commands,extra_gamefile=latch.resolved_gamefile)); continue
            if isinstance(message,StepRequest):
                stage='step'
                if latch is None: raise RuntimeError('step requested before reset')
                public=parse_step_batch(result=env.step([message.action]),gamefile_latch=latch)
                _send(connection,StepResult(observation=public.observation,admissible_commands=public.menu.commands,score=public.score,done=public.done,won=public.won,extra_gamefile=None)); continue
            if isinstance(message,CloseRequest):
                stage='close'
                if env is not None: env.close(); env=None
                _send(connection,WorkerTerminalStatus(status='CLOSED',detail=None,exit_code=None)); return
            raise TypeError('unexpected worker message')
    except BaseException as error:
        try: _send(connection,_failure(stage,error))
        except BaseException: pass
        if env is not None:
            try: env.close()
            except BaseException: pass
    finally:
        try: connection.close()
        except BaseException: pass
