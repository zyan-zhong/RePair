from pathlib import Path
import json,hashlib
import pool_context as pc
import pytest
from copy import deepcopy

def test_r5_actual_failed_request_preserves_all_evidence_and_fits():
    root=Path(__file__).parent
    f=json.loads((root/'R5_PRE_FIXTURE.json').read_bytes())
    policy=json.loads((root/'AUTHORITY.json').read_bytes())['pre_context_encoding_policy']
    out=pc.amend(f['bundle'],policy=policy,authority_ref={'path':'registered','sha256':'a'},
        hash_request=lambda x:hashlib.sha256(pc.canonical(x)).hexdigest())
    assert len(pc.canonical(out['provider_request']))<=f['budget']
    doc=json.loads(out['provider_request']['input'][1]['content'][0]['text'])
    assert pc.canonical(pc.restore(doc['projection'],doc['encoding']['file_ref_roots']))==pc.canonical(f['bundle']['input_projection'])
    for k in ('text','model','reasoning','max_output_tokens','tools','truncation','store'):
        assert out['provider_request'][k]==f['bundle']['provider_request'][k]

@pytest.mark.parametrize('ref',[-1,True,1.0,'0',2])
def test_corrupt_dictionary_indices_cannot_silently_replace_evidence(ref):
    with pytest.raises(ValueError):
        pc.restore({'$strings':{'values':['exact evidence'],'value':{'$s':ref}}},{})

def test_literal_markers_are_rejected_and_scalar_types_preserved():
    with pytest.raises(ValueError):pc.compact({'$s':0},{})
    value={'rows':[{'text':'full long evidence statement retained exactly','x':False},
                   {'text':'full long evidence statement retained exactly','x':0},
                   {'text':'full long evidence statement retained exactly','x':0.0}]}
    assert pc.canonical(pc.restore(pc.pool_strings(value),{}))==pc.canonical(value)

def test_larger_future_history_is_preserved_without_fixed_round_count():
    root=Path(__file__).parent;f=json.loads((root/'R5_PRE_FIXTURE.json').read_bytes())
    b=deepcopy(f['bundle']);mem=b['input_projection']['blind_input']['prior_closed_round_research_memory']
    mem['lessons']=mem['lessons']*10
    policy=json.loads((root/'AUTHORITY.json').read_bytes())['pre_context_encoding_policy']
    out=pc.amend(b,policy=policy,authority_ref={},hash_request=lambda x:hashlib.sha256(pc.canonical(x)).hexdigest())
    doc=json.loads(out['provider_request']['input'][1]['content'][0]['text'])
    assert pc.canonical(pc.restore(doc['projection'],doc['encoding']['file_ref_roots']))==pc.canonical(b['input_projection'])
    assert len(pc.canonical(out['provider_request']))<=f['budget']
