from pathlib import Path
import json,copy,pytest,jsonschema
from recipe_contract import constrain_schema,install,CONTRACT
from training_binding.materializer import recipe_schema,validate_recipe
from post_binding.runtime import extend_prompt
FIX=json.loads((Path(__file__).parent/'REGRESSION_FIXTURE.json').read_bytes())

def test_actual_failure_reproduced_without_masking():
    value=FIX['recipe'];context=FIX['context']
    jsonschema.validate(value,recipe_schema(context))
    with pytest.raises(ValueError,match='MATCHED_SEEDS'):validate_recipe(value,context)

def test_native_constraints_present_in_actual_functions():
    import training_binding.materializer as m,post_binding.runtime as r
    with install():
        assert 'training_seed == data_seed' in r.extend_prompt('original')
        assert CONTRACT in r.extend_prompt('original')
        schema=m.recipe_schema(FIX['context'])
        assert schema['properties']['gradient_accumulation_steps']['enum']==[1,2]
        for key in ['training_seed','data_seed']:assert 'training_seed == data_seed' in schema['properties'][key]['description']

@pytest.mark.parametrize('n,expected',[(1,[1]),(2,[1,2]),(6,[1,2,3,6]),(13,[1,13])])
def test_accumulation_from_current_dataset(n,expected):
    context={**FIX['context'],'row_count':n}
    assert constrain_schema(recipe_schema(context),context)['properties']['gradient_accumulation_steps']['enum']==expected

def test_valid_native_recipe_unchanged():
    value=copy.deepcopy(FIX['recipe']);value['data_seed']=value['training_seed']
    with install():assert validate_recipe(value,FIX['context'])==value
    assert FIX['recipe']['data_seed']!=FIX['recipe']['training_seed']

def test_no_silent_seed_correction():
    with install(),pytest.raises(ValueError,match='MATCHED_SEEDS'):validate_recipe(FIX['recipe'],FIX['context'])

def test_registered_seed_conflict_rejected():
    context={**FIX['context'],'training_seed':1,'data_seed':2}
    with pytest.raises(ValueError,match='SEED_CONSTRAINT_CONFLICT'):constrain_schema(recipe_schema(context),context)

def test_frozen_seed_propagates_without_new_choice():
    context={**FIX['context'],'training_seed':12}
    schema=constrain_schema(recipe_schema(context),context)
    assert schema['properties']['data_seed']['const']==schema['properties']['training_seed']['const']==12

def test_impossible_accumulation_rejected_before_send():
    schema=constrain_schema(recipe_schema(FIX['context']),FIX['context']);value=copy.deepcopy(FIX['recipe']);value['gradient_accumulation_steps']=3
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(value,schema)

def test_prompt_restored_after_scope():
    import post_binding.runtime as r
    original=r.extend_prompt
    with install():assert r.extend_prompt is not original
    assert r.extend_prompt is original
