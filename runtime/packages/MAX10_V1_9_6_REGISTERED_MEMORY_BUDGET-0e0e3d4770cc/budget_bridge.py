"""Bind existing native memory builders to the current registered budget."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import types,hashlib,functools

def contract_identity(contract,runtime):
    if contract.contract_sha256!=runtime.get('token_budget_contract_sha256'):
        raise ValueError('MEMORY_BUDGET_RUNTIME_CONTRACT_IDENTITY')
    return True

def budgeted_builder(native,contract):
    @functools.wraps(native)
    def build(**kw):
        tokenizer=kw['tokenizer']
        if (tokenizer.tokenizer_id,tokenizer.tokenizer_revision)!=(contract.tokenizer_id,contract.tokenizer_revision):
            raise ValueError('MEMORY_BUDGET_TOKENIZER_IDENTITY')
        return native(**{**kw,'hard_ceiling':contract.single_record_hard_ceiling})
    return build

@contextmanager
def budget_scope(binding,a):
    import pchsi.memory.candidate_materialization as cm
    import pchsi.memory.descriptive_eligibility as eligibility
    from pchsi.memory.token_budget_contract import FailureMemoryTokenBudgetContractV1
    from memory_binding.current_source import read_ref
    import json
    for source in a['budget_native_source_refs']:
        raw=Path(source['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('MEMORY_BUDGET_NATIVE_SOURCE_DRIFT')
    contract=FailureMemoryTokenBudgetContractV1.from_json(read_ref(binding['refs']['analyzer_token_contract']))
    runtime=json.loads(read_ref(binding['refs']['memory_runtime']));contract_identity(contract,runtime)
    native=eligibility.govern_descriptive_dev_record_v1
    namespace={**native.__globals__,
        'build_fm1_matched_raw_episodic_view_v1':budgeted_builder(eligibility.build_fm1_matched_raw_episodic_view_v1,contract),
        'build_failure_memory_policy_projection_v1':budgeted_builder(eligibility.build_failure_memory_policy_projection_v1,contract)}
    governed=types.FunctionType(native.__code__,namespace,native.__name__,native.__defaults__,native.__closure__)
    governed.__kwdefaults__=native.__kwdefaults__;functools.update_wrapper(governed,native)
    with patch.object(cm,'govern_descriptive_dev_record_v1',governed),patch.object(cm,'build_failure_memory_policy_projection_v1',budgeted_builder(cm.build_failure_memory_policy_projection_v1,contract)):
        yield contract

@contextmanager
def installed(a):
    import memory_binding.api as api
    from memory_binding.current_source import read_ref
    from memory_binding.producer import write_once,canonical
    import json
    native=api.materialize_round_memory
    def materialize(**kw):
        binding=kw['binding'];request=json.loads(read_ref(binding['refs']['request']))
        if request['request_sha256'] in a['preserved_closed_requests']:
            return native(**kw)
        with budget_scope(binding,a) as contract:
            sink=Path(kw['output_root'])/'registered_budget'/contract.contract_sha256
            write_once(sink/'TOKEN_BUDGET_AUTHORITY.json',canonical({
                'schema_id':'CURRENT_MEMORY_MATERIALIZATION_TOKEN_BUDGET_AUTHORITY_V1',
                'request_ref':binding['refs']['request'],'contract_ref':binding['refs']['analyzer_token_contract'],
                'runtime_ref':binding['refs']['memory_runtime'],'contract_sha256':contract.contract_sha256,
                'single_record_hard_ceiling':contract.single_record_hard_ceiling,
                'library_total_hard_ceiling':contract.library_total_hard_ceiling,'max_record_count':contract.max_record_count,
                'implementation_ref':{'path':str(Path(__file__)),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                'source_refs':a['budget_native_source_refs'],'research_gate_changed':False}))
            return native(**{**kw,'output_root':sink})
    with patch.object(api,'materialize_round_memory',materialize):yield
