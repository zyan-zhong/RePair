"""Expose existing native trainer constraints; never choose or repair a recipe."""
from contextlib import contextmanager
from unittest.mock import patch

CONTRACT = 'NATIVE_MATCHED_SEED_COMPLETE_ACCUMULATION_V1'
PROMPT = '''
Native execution capabilities (binding contract, not optional advice):
training_seed == data_seed. Choose ONE nonnegative integer seed and put exactly
that same value in BOTH fields; the existing native trainer uses this one seed
for model randomness and the frozen data order. Distinct seeds are unsupported.
micro_batch_size is 1. gradient_accumulation_steps must exactly divide row_count;
use one of the current dataset-specific schema enum values. No partial final
accumulation group, padding, or example duplication is allowed.
optimizer_steps = epochs * row_count / gradient_accumulation_steps.
warmup_steps must be an integer between 0 and optimizer_steps, inclusive.
Choose all free values yourself from the evidence and current dataset. These
capabilities do not select TRAIN, require promotion, or change any effect label.
'''

def constrain_schema(schema, context):
    from copy import deepcopy
    result=deepcopy(schema);props=result['properties']
    for name in ('training_seed','data_seed'):
        props[name]['description']='Choose one shared nonnegative integer: training_seed == data_seed is mandatory in the native trainer.'
    props['warmup_steps']['description']='Integer 0 <= warmup_steps <= epochs * row_count / gradient_accumulation_steps.'
    if context is not None:
        n=context['row_count']
        if type(n) is not int or n<=0:raise ValueError('RECIPE_CURRENT_ROW_COUNT')
        props['gradient_accumulation_steps']['enum']=[i for i in range(1,n+1) if n%i==0]
        fixed=[context[k] for k in ('training_seed','data_seed') if k in context]
        if fixed:
            if any(type(x) is not int or x<0 or x!=fixed[0] for x in fixed):raise ValueError('REGISTERED_SEED_CONSTRAINT_CONFLICT')
            for name in ('training_seed','data_seed'):props[name]['const']=fixed[0]
    result['description']='Existing native training recipe contract '+CONTRACT
    return result

@contextmanager
def install():
    import training_binding.materializer as materializer
    import post_binding.runtime as runtime
    old_schema=materializer.recipe_schema;old_prompt=runtime.extend_prompt
    def schema(context=None):return constrain_schema(old_schema(context),context)
    def prompt(original):return old_prompt(original)+'\n'+CONTRACT+'\n'+PROMPT
    with patch.object(materializer,'recipe_schema',schema),patch.object(runtime,'extend_prompt',prompt):yield
