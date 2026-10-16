"""Find the shortest complete prefix of an existing native sample sequence.

This proves supervised-position coverage only. It neither chooses scientific
answers nor demonstrates learning, diagnostic quality or policy capability.
"""
from copy import deepcopy


def full_prefix(dataset):
    rows=dataset['rows']
    expected={i:{j for j,value in enumerate(row['labels']) if j>0 and value!=-100}
              for i,row in enumerate(rows)}
    if not rows or any(not columns for columns in expected.values()):
        raise ValueError('REGISTERED_SUPERVISION_EMPTY_ROW')
    seen={i:set() for i in expected}
    for count,group in enumerate(dataset['groups'],1):
        for sample in group:
            i=sample['row_index']
            if type(i) is not int or i not in expected:
                raise ValueError('NATIVE_GROUP_ROW_IDENTITY')
            labels=sample['labels']
            if len(labels)!=len(rows[i]['labels']):
                raise ValueError('NATIVE_GROUP_LABEL_LENGTH')
            columns={j for j,value in enumerate(labels) if j>0 and value!=-100}
            if not columns<=expected[i] or any(labels[j]!=rows[i]['labels'][j] for j in columns):
                raise ValueError('NATIVE_GROUP_LABEL_SUBSTITUTION')
            if len(columns)!=sample['target_tokens']:
                raise ValueError('NATIVE_GROUP_TOKEN_COUNT')
            seen[i]|=columns
        if all(expected[i]<=seen[i] for i in expected):
            return {'prefix_groups':count,'groups':deepcopy(dataset['groups'][:count]),
                    'rows':len(rows),'expected_positions':sum(map(len,expected.values())),
                    'all_registered_target_positions_covered':True,
                    'native_order_and_masks_retained':True,
                    'scientific_method_qualified':False,'actor_capability_qualified':False}
    raise ValueError('UNCOVERED_REGISTERED_TARGET_POSITIONS:'+str({i:len(expected[i]-seen[i])
                                                                  for i in expected if expected[i]-seen[i]}))
