"""Narrow outcome-blind compiler for registered public search-option forms.

This is an adapter to the existing ordered-option dispatcher, not a general
natural-language interpreter. Unknown complete sentences are protocol missingness.
Entity values come only from the candidate text; no task-specific defaults exist.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = 'TRAINING_HARNESS_PUBLIC_SEARCH_OPTION_CONTRACT_V2'
COMPILER = 'EXACT_PUBLIC_SEARCH_TERMINATION_FORMS_V1'
_TARGET = r'(?P<target>[a-z][a-z0-9_]*)'
_RULES = (
    ('VISIBLE_OR_CARRIED', re.compile(
        r'Stop the search options when the '+_TARGET+r' becomes visible or carried, '
        r'when the current admissible menu changes such that the next option is unavailable, '
        r'or when the episode terminates; after each executed action, re-read the resulting observation and current menu\.')),
    ('VISIBLE_OR_TAKE_ADMISSIBLE', re.compile(
        r'Re-evaluate after each executed action and stop this search sequence as soon as the '+_TARGET+
        r' or an exact admissible (?P=target)-taking command appears, the task completes, '
        r'or the next listed action is no longer an exact member of the current menu\.')),
)


def _canonical(v: object) -> bytes:
    return (json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def _hash(v: Mapping[str, Any]) -> str:
    return hashlib.sha256(SCHEMA.encode()+b'\0'+_canonical({k:x for k,x in v.items() if k!='contract_sha256'})).hexdigest()


def compile_option(candidate: Mapping[str, Any]) -> dict[str, Any]:
    text=candidate.get('termination_condition')
    actions=candidate.get('option_actions')
    if candidate.get('candidate_status')!='EXECUTABLE_SHORT_OPTION' or not isinstance(text,str):
        return {'status':'PROTOCOL_MISSINGNESS','reason':'NOT_A_REGISTERED_SHORT_OPTION','contract':None}
    if not isinstance(actions,list) or not actions or any(not isinstance(a,str) or not a or '\n' in a or '\x00' in a for a in actions):
        raise ValueError('invalid registered option actions')
    matches=[(kind,regex.fullmatch(text)) for kind,regex in _RULES]
    matches=[(kind,m) for kind,m in matches if m is not None]
    if len(matches)!=1:
        return {'status':'PROTOCOL_MISSINGNESS','reason':'UNSUPPORTED_COMPLETE_TERMINATION_FORM','contract':None,
                'source_candidate_sha256':candidate.get('candidate_sha256'),
                'source_termination_condition_sha256':hashlib.sha256(text.encode()).hexdigest()}
    mode,match=matches[0]
    contract={
        'schema_id':SCHEMA,'schema_version':2,'compiler_id':COMPILER,
        'source_state_sha256':candidate['source_state_sha256'],
        'source_candidate_sha256':candidate['candidate_sha256'],
        'source_termination_condition_sha256':hashlib.sha256(text.encode()).hexdigest(),
        'option_actions':list(actions),'dispatch_mode':'ORDERED_SEQUENCE',
        'max_intervention_steps':len(actions),'target_object_type':match.group('target'),
        'public_stop_mode':mode,'stop_environment_done':True,
        'stop_next_action_not_admissible':True,'stop_actions_exhausted':True,
        'all_intervention_actions_count_against_environment_budget':True,
        'live_menu_revalidation_required_each_step':True,
        'return_control_to_frozen_policy_after_option':True,
        'free_text_runtime_interpretation_allowed':False,
        'legacy_free_text_semantic_coverage':'FULL',
    }
    contract['contract_sha256']=_hash(contract)
    return {'status':'COMPILED','reason':None,'contract':validate_contract(contract)}


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    c=dict(value)
    if c.get('schema_id')!=SCHEMA or c.get('schema_version')!=2 or c.get('compiler_id')!=COMPILER:
        raise ValueError('option contract schema/compiler mismatch')
    if c.get('contract_sha256')!=_hash(c):raise ValueError('option contract hash mismatch')
    if c.get('dispatch_mode')!='ORDERED_SEQUENCE' or c.get('public_stop_mode') not in {x[0] for x in _RULES}:
        raise ValueError('unregistered option operation')
    acts=c.get('option_actions')
    if not isinstance(acts,list) or not acts or any(not isinstance(x,str) or not x for x in acts):
        raise ValueError('option actions invalid')
    if c.get('max_intervention_steps')!=len(acts):raise ValueError('option truncation forbidden')
    target=c.get('target_object_type')
    if not isinstance(target,str) or not re.fullmatch(r'[a-z][a-z0-9_]*',target):raise ValueError('object type invalid')
    for k in ('stop_environment_done','stop_next_action_not_admissible','stop_actions_exhausted',
              'all_intervention_actions_count_against_environment_budget','live_menu_revalidation_required_each_step',
              'return_control_to_frozen_policy_after_option'):
        if c.get(k) is not True:raise ValueError('required option invariant: '+k)
    if c.get('free_text_runtime_interpretation_allowed') is not False:raise ValueError('free-text runtime interpretation forbidden')
    return c


def _positive_visible_object(observation: str, target: str) -> bool:
    # ALFWorld public object enumerations carry numbered object instances.
    # Deliberately do not search goals, arbitrary prose, negation or whole prompt.
    pattern=re.compile(r'\b(?:a|an|the)\s+'+re.escape(target)+r'\s+[0-9]+\b',re.I)
    for line in observation.splitlines():
        if line.lstrip().lower().startswith('your task is to:'):continue
        for match in re.finditer(r'\byou see\s+([^.!?\n]+)',line,re.I):
            if pattern.search(match.group(1)):return True
    return False


def _take_admissible(menu: Sequence[str], target: str) -> bool:
    regex=re.compile(r'take '+re.escape(target)+r' [0-9]+ from .+')
    return any(regex.fullmatch(action) for action in menu)


def _carried(menu: Sequence[str], observation: str, target: str) -> bool:
    # Possession inferred only from public admissible put commands or an explicit
    # current inventory observation. No simulator private facts are accessed.
    regex=re.compile(r'put '+re.escape(target)+r' [0-9]+ in/on .+')
    if any(regex.fullmatch(action) for action in menu):return True
    for m in re.finditer(r'\byou are carrying\s*:?\s*([^.!?\n]+)',observation,re.I):
        if re.search(r'(?<![A-Za-z0-9_])'+re.escape(target)+r' [0-9]+\b',m.group(1),re.I):return True
    return False


def decide(contract: Mapping[str, Any], *, executed_actions: Sequence[str],
           observation: str, menu: Sequence[str], environment_done: bool) -> dict[str, Any]:
    c=validate_contract(contract)
    acts=c['option_actions']; done=list(executed_actions)
    if done!=acts[:len(done)] or len(done)>len(acts):raise ValueError('executed option prefix mismatch')
    if type(environment_done) is not bool:raise TypeError('environment_done must be bool')
    if any(not isinstance(x,str) or not x for x in menu):raise ValueError('public menu invalid')
    def stop(reason):return {'decision':'STOP','reason':reason}
    if environment_done:return stop('ENVIRONMENT_DONE')
    target=c['target_object_type']
    if _positive_visible_object(observation,target):return stop('TARGET_VISIBLE')
    if _take_admissible(menu,target):return stop('TARGET_TAKE_ADMISSIBLE')
    if c['public_stop_mode']=='VISIBLE_OR_CARRIED' and _carried(menu,observation,target):return stop('TARGET_CARRIED')
    if len(done)==len(acts):return stop('REGISTERED_ACTIONS_EXHAUSTED')
    action=acts[len(done)]
    if action not in menu:return stop('NEXT_REGISTERED_ACTION_NOT_ADMISSIBLE')
    return {'decision':'EXECUTE','action':action,'registered_action_index':len(done)}
