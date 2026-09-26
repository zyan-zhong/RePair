"""Finite Planner-authored phases over public observations and live menu only.

Reuses V190 public predicate semantics. No environment oracle or task solver.
The native branch loop owns environment execution, budgets and terminal truth.
"""
from copy import deepcopy
import re

KINDS=['MENU_COMMAND_PREFIX','OBSERVATION_ALL_SUBSTRINGS','PUBLIC_TARGET_VISIBLE','PUBLIC_TARGET_CARRIED']

def program_schema():
    def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    text={'type':'string','minLength':1}
    predicate=obj({'kind':{'type':'string','enum':KINDS},'arguments':{'type':'array','items':text,'minItems':1},'negate':{'type':'boolean'}})
    rule=obj({'when_all':{'type':'array','items':predicate},
        'command':obj({'kind':{'type':'string','enum':['EXACT','PREFIX_SUFFIX']},'text':text,'suffix':{'type':'string'}}),
        'max_uses':{'type':'integer','minimum':1}})
    return {'type':'array','items':obj({'purpose':text,'complete_when_any':{'type':'array','items':predicate},
        'rules':{'type':'array','minItems':1,'items':rule}})}

def validate_program(program):
    import jsonschema
    try:jsonschema.Draft202012Validator(program_schema()).validate(program)
    except jsonschema.ValidationError as exc:raise ValueError('GUARDED_PROGRAM_SCHEMA:'+exc.message) from exc
    for phase in program:
        predicates=list(phase['complete_when_any'])
        for rule in phase['rules']:
            predicates+=rule['when_all'];command=rule['command']
            if type(rule['max_uses']) is not int:raise ValueError('GUARDED_RULE_INTEGER_REQUIRED')
            if command['kind']=='EXACT' and command['suffix']:raise ValueError('GUARDED_EXACT_SUFFIX_FORBIDDEN')
            if command['kind']=='PREFIX_SUFFIX' and not command['text'].endswith(' '):raise ValueError('GUARDED_PREFIX_TOKEN_BOUNDARY')
        for predicate in predicates:
            args=predicate['arguments'];kind=predicate['kind']
            if kind!='OBSERVATION_ALL_SUBSTRINGS' and len(args)!=1:raise ValueError('GUARDED_PREDICATE_ARITY')
            if any(not a.strip() for a in args):raise ValueError('GUARDED_EMPTY_PREDICATE')
            if kind=='MENU_COMMAND_PREFIX' and not args[0].endswith(' '):raise ValueError('GUARDED_PREFIX_TOKEN_BOUNDARY')
            if kind.startswith('PUBLIC_TARGET') and not re.fullmatch('[a-z][a-z0-9_]*',args[0]):raise ValueError('GUARDED_TARGET_TYPE')
    return program

def predicate_hit(predicate,observation,menu):
    public='\n'.join(line for line in observation.splitlines() if not line.strip().lower().startswith(('your task is','task:','goal:'))).casefold()
    kind=predicate['kind'];args=predicate['arguments']
    if kind=='MENU_COMMAND_PREFIX':hit=any(c.casefold().startswith(args[0].casefold()) for c in menu)
    elif kind=='OBSERVATION_ALL_SUBSTRINGS':hit=all(a.casefold() in public for a in args)
    elif kind=='PUBLIC_TARGET_VISIBLE':
        from option_adapter import _positive_visible_object
        hit=_positive_visible_object(public,args[0])
    elif kind=='PUBLIC_TARGET_CARRIED':
        from option_adapter import _carried
        # The registered ALFWorld adapter exposes transfer as "move ... to ...".
        # Match only an entire currently admissible command, never task prose.
        move=re.compile(r'move '+re.escape(args[0])+r' [0-9]+ to .+')
        hit=_carried(menu,public,args[0]) or any(move.fullmatch(c) for c in menu)
    else:raise ValueError('GUARDED_UNKNOWN_PREDICATE')
    return bool(hit)!=predicate['negate']

class Engine:
    def __init__(self,program,initial_action):
        self.program=deepcopy(validate_program(program));self.initial=initial_action
        self.phase=0;self.uses={};self.issued=[];self.trace=[]

    def decide(self,executed_actions,observation,menu,environment_done):
        if list(executed_actions)!=self.issued:raise ValueError('GUARDED_EXECUTED_PREFIX_CHANGED')
        if type(environment_done) is not bool:raise ValueError('GUARDED_DONE_TYPE')
        if environment_done:return self.stop('ENVIRONMENT_DONE')
        if not self.issued:
            if self.initial not in menu:return self.stop('NEXT_REGISTERED_ACTION_NOT_ADMISSIBLE')
            return self.issue(self.initial,{'initial':True})
        while self.phase<len(self.program):
            phase=self.program[self.phase]
            hits=[i for i,p in enumerate(phase['complete_when_any']) if predicate_hit(p,observation,menu)]
            if hits:
                self.trace.append({'phase':self.phase,'event':'PUBLIC_COMPLETION_PREDICATE','predicate_indices':hits})
                self.phase+=1;continue
            for index,rule in enumerate(phase['rules']):
                key=(self.phase,index)
                if self.uses.get(key,0)>=rule['max_uses'] or not all(predicate_hit(p,observation,menu) for p in rule['when_all']):continue
                command=rule['command']
                choices=[c for c in menu if c==command['text']] if command['kind']=='EXACT' else [c for c in menu if c.startswith(command['text']) and c.endswith(command['suffix'])]
                if not choices:continue
                if len(choices)!=1:return self.stop('AMBIGUOUS_REGISTERED_MENU_RULE')
                self.uses[key]=self.uses.get(key,0)+1
                return self.issue(choices[0],{'phase':self.phase,'rule':index,'use':self.uses[key]})
            return self.stop('NO_REGISTERED_RULE_APPLICABLE')
        return self.stop('REGISTERED_PHASES_COMPLETE')

    def issue(self,action,origin):
        result={'decision':'EXECUTE','action':action,'registered_action_index':len(self.issued)}
        self.trace.append({**result,**origin});self.issued.append(action);return result

    def stop(self,reason):
        result={'decision':'STOP','reason':reason}
        self.trace.append({**result,'phase':self.phase});return result
