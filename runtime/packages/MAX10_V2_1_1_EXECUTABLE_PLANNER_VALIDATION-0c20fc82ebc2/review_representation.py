"""Reuse the proven lossless source-review normalizations, no recovery launcher."""
from copy import deepcopy

def normalize(review):
    result=deepcopy(review);changes=[]
    for plan in result['plans']:
        for phase_index,phase in enumerate(plan['program']):
            for rule_index,rule in enumerate(phase['rules']):
                command=rule['command'];kept=[]
                for predicate_index,predicate in enumerate(rule['when_all']):
                    redundant=(command['kind']=='EXACT' and command['suffix']==''
                        and not command['text'].endswith(' ')
                        and predicate=={'kind':'MENU_COMMAND_PREFIX','arguments':[command['text']],'negate':False})
                    if redundant:
                        changes.append({'condition':plan['condition'],'phase_index':phase_index,
                            'rule_index':rule_index,'predicate_index':predicate_index,'removed_predicate':deepcopy(predicate),
                            'unchanged_exact_command':deepcopy(command),
                            'equivalence':'Exact selector requires command in live menu, which entails this positive prefix predicate.'})
                    else:kept.append(predicate)
                rule['when_all']=kept
    return result,changes

def group_context_reviews(value,items,schema):
    """Losslessly group context-only variants; never choose among repair plans."""
    import jsonschema
    from strategy_planner import validate_review
    jsonschema.Draft202012Validator(schema).validate(value)
    expected={i['fragment_id']:i for i in items};groups={k:[] for k in expected}
    for row in value['reviews']:
        if row['fragment_id'] not in expected:raise ValueError('CONTEXT_GROUP_UNKNOWN_FRAGMENT')
        item=expected[row['fragment_id']]
        if item['original_candidate_pair'] is not None or row['plans']:raise ValueError('CONTEXT_GROUP_CANDIDATE_SELECTION_FORBIDDEN')
        validate_review(row,packet_id=item['packet_id'],context=item['exact_source_context'],pair=None)
        groups[row['fragment_id']].append(row)
    if any(not rows for rows in groups.values()):raise ValueError('CONTEXT_GROUP_MISSING_FRAGMENT')
    reviews=[];changes=[]
    for fragment,rows in groups.items():
        row=deepcopy(rows[0])
        if len(rows)>1:
            for name in ['diagnosis','counterevidence','falsifiable_hypothesis']:
                if any(r[name]!=rows[0][name] for r in rows):
                    row[name]='Unranked source-context variants are preserved verbatim in context_review_variants; no variant is selected or discarded.'
            row['context_review_variants']=deepcopy(rows)
            changes.append({'fragment_id':fragment,'variant_count':len(rows),'all_original_rows_retained':True,
                'variant_ranking_performed':False,'candidate_plans_present':False,'derived_text_is_structural_disclosure':True})
        reviews.append(row)
    if not changes:raise ValueError('CONTEXT_GROUP_NO_DUPLICATE_VARIANTS')
    extended=deepcopy(schema)
    extended['properties']['reviews']['items']['properties']['context_review_variants']={
        'type':'array','minItems':2,'items':deepcopy(schema['properties']['reviews']['items'])}
    result={**value,'reviews':reviews};jsonschema.Draft202012Validator(extended).validate(result)
    return result,changes
