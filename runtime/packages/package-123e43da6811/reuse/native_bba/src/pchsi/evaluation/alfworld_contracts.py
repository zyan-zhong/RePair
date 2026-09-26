"""Strict public-state contracts for singleton ALFWorld/TextWorld batches."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
from typing import cast
from pchsi.evaluation.action_trace import sha256_string_sequence

@dataclass(frozen=True, slots=True)
class MenuSnapshot:
    commands: tuple[str, ...]
    sequence_sha256: str

@dataclass(frozen=True, slots=True)
class GamefileIdentityLatch:
    resolved_gamefile: str
    def __post_init__(self) -> None:
        if not isinstance(self.resolved_gamefile,str) or not self.resolved_gamefile: raise ValueError('resolved_gamefile must be non-empty')
        if not Path(self.resolved_gamefile).is_absolute(): raise ValueError('resolved_gamefile must be absolute')

@dataclass(frozen=True, slots=True)
class ResetPublicState:
    observation: str
    menu: MenuSnapshot
    gamefile_latch: GamefileIdentityLatch

@dataclass(frozen=True, slots=True)
class StepPublicState:
    observation: str
    menu: MenuSnapshot
    score: int | float
    done: bool
    won: bool

def _require_mapping(*,name:str,value:object)->Mapping[str,object]:
    if not isinstance(value,Mapping): raise TypeError(f'{name} must be a mapping')
    return cast(Mapping[str,object],value)

def _require_stable_sequence(*,name:str,value:object)->Sequence[object]:
    if isinstance(value,(str,bytes,bytearray,Mapping)): raise TypeError(f'{name} must be a stable sequence, not string-like or mapping')
    if not isinstance(value,Sequence): raise TypeError(f'{name} must be a stable sequence')
    return cast(Sequence[object],value)

def _require_singleton(*,name:str,value:object)->object:
    seq=_require_stable_sequence(name=name,value=value)
    if len(seq)!=1: raise ValueError(f'{name} must contain exactly one item')
    return seq[0]

def snapshot_menu(*,infos:Mapping[str,object],done:bool)->MenuSnapshot:
    if type(done) is not bool: raise TypeError('done must be bool')
    mapping=_require_mapping(name='infos',value=infos)
    if 'admissible_commands' not in mapping: raise ValueError('infos is missing admissible_commands')
    inner=_require_singleton(name='admissible_commands outer batch',value=mapping['admissible_commands'])
    seq=_require_stable_sequence(name='admissible_commands inner menu',value=inner)
    if not done and len(seq)==0: raise ValueError('non-terminal admissible_commands menu must not be empty')
    frozen=tuple(seq)
    if any(not isinstance(item,str) for item in frozen): raise TypeError('admissible_commands items must be str')
    return MenuSnapshot(commands=cast(tuple[str,...],frozen),sequence_sha256=sha256_string_sequence(cast(Sequence[str],frozen)))

def _resolve_gamefile(*,name:str,value:object)->str:
    if not isinstance(value,str) or not value: raise TypeError(f'{name} must be a non-empty string')
    return str(Path(value).resolve())

def parse_reset_batch(*,observations:object,infos:object,expected_gamefile:Path)->ResetPublicState:
    observation=_require_singleton(name='reset observations',value=observations)
    if not isinstance(observation,str): raise TypeError('reset observation must be str')
    mapping=_require_mapping(name='reset infos',value=infos)
    menu=snapshot_menu(infos=mapping,done=False)
    if 'extra.gamefile' not in mapping: raise ValueError('reset infos is missing extra.gamefile')
    raw=_require_singleton(name='reset extra.gamefile batch',value=mapping['extra.gamefile'])
    observed=_resolve_gamefile(name='reset extra.gamefile',value=raw); expected=str(Path(expected_gamefile).resolve())
    if observed!=expected: raise ValueError('reset extra.gamefile does not match expected gamefile')
    latch=GamefileIdentityLatch(resolved_gamefile=expected)
    return ResetPublicState(observation=observation,menu=menu,gamefile_latch=latch)

def _validate_optional_step_gamefile(*,infos:Mapping[str,object],latch:GamefileIdentityLatch)->None:
    if 'extra.gamefile' not in infos or infos['extra.gamefile'] is None: return
    inner=_require_singleton(name='step extra.gamefile batch',value=infos['extra.gamefile'])
    if inner is None: return
    observed=_resolve_gamefile(name='step extra.gamefile',value=inner)
    if observed!=latch.resolved_gamefile: raise ValueError('step extra.gamefile does not match reset gamefile latch')

def parse_step_batch(*,result:object,gamefile_latch:GamefileIdentityLatch)->StepPublicState:
    if not isinstance(gamefile_latch,GamefileIdentityLatch): raise TypeError('gamefile_latch must be GamefileIdentityLatch')
    outer=_require_stable_sequence(name='step result',value=result)
    if len(outer)!=4: raise ValueError('step result must contain exactly four items')
    observations,scores,dones,infos=outer
    observation=_require_singleton(name='step observations',value=observations)
    if not isinstance(observation,str): raise TypeError('step observation must be str')
    score=_require_singleton(name='step scores',value=scores)
    if type(score) not in (int,float): raise TypeError('step score must be int or float and not bool')
    if isinstance(score,float) and not math.isfinite(score): raise ValueError('step score must be finite')
    done=_require_singleton(name='step dones',value=dones)
    if type(done) is not bool: raise TypeError('step done must be bool')
    mapping=_require_mapping(name='step infos',value=infos)
    if 'won' not in mapping: raise ValueError('step infos is missing won')
    won=_require_singleton(name='step won batch',value=mapping['won'])
    if type(won) is not bool: raise TypeError('step won must be bool')
    _validate_optional_step_gamefile(infos=mapping,latch=gamefile_latch)
    menu=snapshot_menu(infos=mapping,done=done)
    if won and not done: raise ValueError('won=true with done=false violates environment contract')
    return StepPublicState(observation=observation,menu=menu,score=cast(int|float,score),done=done,won=won)
