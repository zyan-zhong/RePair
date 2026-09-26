"""Restricted TRAIN_SELECT terminal metric; never an environment reward."""
from fractions import Fraction

METRIC_ID='terminal_dynamic_goal_condition_fraction_v1'

def compile_goal(goal,domains,static_facts,dynamic_predicates):
    """Compile native unnormalized conjunctive existential goals.

    Static literals and equality constrain witnesses, never earn progress.
    Native parser has already uniquely renamed all quantified variables.
    Each connected variable component is solved jointly; witnesses cannot
    be mixed between literals. Unsupported fragments are rejected before use.
    """
    parameters={};literals=[]
    def flatten(node):
        kind=node['kind']
        if kind=='ExistentialCondition':
            for p in node['parameters']:
                if p['name'] in parameters:raise ValueError('GOAL_VARIABLE_NOT_UNIQUE')
                parameters[p['name']]=tuple(domains[p['type']])
            for part in node['parts']:flatten(part)
        elif kind=='Conjunction':
            for part in node['parts']:flatten(part)
        elif kind in ('Atom','NegatedAtom'):
            literals.append((node['predicate'],tuple(node['args']),kind=='NegatedAtom'))
        else:raise ValueError('UNSUPPORTED_GOAL_FRAGMENT:'+kind)
    flatten(goal)
    def variables(lit):return set(a for a in lit[1] if a.startswith('?'))
    if any(not variables(l).issubset(parameters) for l in literals):raise ValueError('GOAL_FREE_VARIABLE')
    groups=[]
    for literal in literals:
        vs=variables(literal);members=[literal];rest=[]
        for oldvs,old in groups:
            if vs & oldvs:vs|=oldvs;members+=old
            else:rest.append((oldvs,old))
        groups=rest+[(vs,members)]
    result=[]
    for vs,members in groups:
        constraints=[l for l in members if l[0] not in dynamic_predicates]
        objectives=[l for l in members if l[0] in dynamic_predicates]
        bindings=[]
        def ground(lit,binding):return lit[0],tuple(binding.get(a,a) for a in lit[1]),lit[2]
        def true(lit):
            p,args,neg=lit;v=args[0]==args[1] if p=='=' else (p,args) in static_facts
            return v!=neg
        candidates={v:tuple(value for value in parameters[v] if all(true(ground(l,{v:value})) for l in constraints if variables(l)<= {v})) for v in vs}
        ordered=sorted(vs,key=lambda x:(len(candidates[x]),x))
        def visit(binding,i):
            if any(variables(l).issubset(binding) and not true(ground(l,binding)) for l in constraints):return
            if i==len(ordered):bindings.append([ground(l,binding) for l in objectives]);return
            v=ordered[i]
            for value in candidates[v]:visit({**binding,v:value},i+1)
        visit({},0)
        if not bindings:raise ValueError('GOAL_STATIC_WITNESS_UNAVAILABLE')
        if objectives:result.append({'count':len(objectives),'alternatives':bindings})
    if not result:raise ValueError('NO_DYNAMIC_GOAL_CONDITIONS')
    return {'metric_id':METRIC_ID,'groups':result}

def completion(spec,facts):
    numerator=denominator=0
    for group in spec['groups']:
        denominator+=group['count']
        numerator+=max(sum(((p,tuple(args)) in facts)!=neg for p,args,neg in alternative) for alternative in group['alternatives'])
    return numerator,denominator

def compare(parent_success,candidate_success,parent_progress,candidate_progress):
    if candidate_success!=parent_success:return 'PROMOTE' if candidate_success>parent_success else 'ROLLBACK'
    if not parent_progress or len(parent_progress)!=len(candidate_progress):raise ValueError('PROGRESS_COMPLETE_PAIRED_GRID_REQUIRED')
    def mean(values):
        for n,d in values:
            if type(n) is not int or type(d) is not int or d<=0 or not 0<=n<=d:raise ValueError('PROGRESS_FRACTION_INVALID')
        return sum((Fraction(n,d) for n,d in values),Fraction())/len(values)
    return 'PROMOTE' if mean(candidate_progress)>mean(parent_progress) else 'ROLLBACK'

def from_game(game):
    """Reuse installed FastDownward's original parser, before SAS normalization."""
    import sys,contextlib,io
    argv=sys.argv
    try:
        sys.argv=['translate.py','domain','task']
        from fast_downward.translate.pddl_parser import lisp_parser,parsing_functions
        with contextlib.redirect_stdout(io.StringIO()):
            task=parsing_functions.parse_task(lisp_parser.parse_nested_list(game['pddl_domain'].splitlines()),lisp_parser.parse_nested_list(game['pddl_problem'].splitlines()))
    finally:sys.argv=argv
    if task.axioms:raise ValueError('GOAL_DERIVED_PREDICATES_UNSUPPORTED')
    def tree(c):
        d={'kind':type(c).__name__}
        if hasattr(c,'predicate'):d.update(predicate=c.predicate,args=list(c.args))
        if hasattr(c,'parameters'):d['parameters']=[{'name':v.name,'type':v.type_name} for v in c.parameters]
        if hasattr(c,'parts'):d['parts']=[tree(x) for x in c.parts]
        return d
    parents={t.name:t.basetype_name for t in task.types};domains={t.name:[] for t in task.types}
    for obj in task.objects:
        typ=obj.type_name;seen=set()
        while typ is not None:
            if typ in seen:raise ValueError('GOAL_TYPE_HIERARCHY_CYCLE')
            seen.add(typ);domains.setdefault(typ,[]).append(obj.name)
            parent=parents.get(typ)
            if parent==typ:break  # Native ALFWorld redeclares its root type.
            typ=parent
    static={(a.predicate,tuple(a.args)) for a in task.init if hasattr(a,'predicate')}
    dynamic={e.literal.predicate for a in task.actions for e in a.effects}
    return compile_goal(tree(task.goal),domains,static,dynamic)

def state_facts(state):
    return {(f.name.lower(),tuple(a.name.lower() for a in f.arguments)) for f in state.facts}
