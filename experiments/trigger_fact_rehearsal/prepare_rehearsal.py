"""Allocated tokenizer proof and native dataset materialization before SFT."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from fact_rehearsal import rehearse
from supervision_coverage import full_prefix

# The native source root is prepended by the owner. Bind the entry helper
# explicitly so an older native module with the same name cannot shadow it.
_helper_path = Path(__file__).with_name('fact_practice.py')
_spec = importlib.util.spec_from_file_location('repair_trigger_fact_practice', _helper_path)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)
practice_labels = _helper.practice_labels
_target_spec = importlib.util.spec_from_file_location('repair_trigger_target_binding', Path(__file__).with_name('target_binding.py'))
_target_helper = importlib.util.module_from_spec(_target_spec)
_target_spec.loader.exec_module(_target_helper)
target_for_row = _target_helper.target_for_row


def prepare(corpus, plan, tokenizer, checked, once, root):
    assert os.environ.get('SLURM_JOB_ID'), 'ALLOCATED_TOKENIZER_REQUIRED'
    masks, bindings = {}, []
    approved = checked(plan['approved_execution_views_ref'])
    approved_proofs = {p['row_id']: p for p in approved['tokenization_proofs']}
    for i, row in enumerate(corpus['rows']):
        if row['view'] != 'RESEARCH' or row['stage'] not in ('L-A0', 'L-A1'):
            continue
        assert row['training_admitted'] is True
        target, target_ref = target_for_row(row, checked, approved_proofs)
        masks[i], proof = practice_labels(row, target, tokenizer)
        assert len(proof['fact_spans']) == 2 * len(json.loads(target)['local_analysis']['error_instances'])
        bindings.append({'row_index': i, 'row_id': row['row_id'],
                         'registered_target_ref': target_ref,
                         'historical_shared_target_ref': row.get('shared_scientific_target_ref'),
                         'actual_execution_target_sha256': hashlib.sha256(target.encode()).hexdigest(), **proof})
    trace = checked(plan['positive_lr_trace_ref'])
    records = [checked(r) for r in trace['step_refs']]
    indices = [r['step'] - 1 for r in records if r['learning_rate'] > 0]
    assert indices == plan['positive_lr_group_indices']
    assert len(records) == len(corpus['groups']) == plan['steps']
    revised, proof = rehearse(corpus, masks, indices)
    assert proof['changed_visits'] > 0, 'REHEARSAL_INTERVENTION_WOULD_BE_EMPTY'
    assert revised['rows'] == corpus['rows'] and revised['loss_weights'] == corpus['loss_weights']
    for before, after in zip(corpus['groups'], revised['groups'], strict=True):
        assert len(before) == len(after)
        for left, right in zip(before, after, strict=True):
            assert left['row_index'] == right['row_index']
            row = corpus['rows'][left['row_index']]
            if row['view'] != 'RESEARCH' or row['stage'] not in ('L-A0', 'L-A1'):
                assert left == right, 'NONLOCAL_OR_POLICY_SAMPLE_CHANGED'
    coverage = full_prefix(revised)
    assert coverage['expected_positions'] == plan['prepared_coverage']['expected_positions']
    assert coverage['prefix_groups'] == plan['steps']
    dataset_ref = once(root / 'inputs' / 'REHEARSAL_DATASET.json', revised)
    proof.update(schema_id='REPAIR_TRIGGER_FACT_REHEARSAL_MATERIALIZATION_V1',
                 parent_dataset_ref=plan['dataset_ref'], dataset_ref=dataset_ref,
                 positive_lr_trace_ref=plan['positive_lr_trace_ref'],
                 fact_helper_ref={'path': str(_helper_path),
                                  'sha256': hashlib.sha256(_helper_path.read_bytes()).hexdigest()},
                 target_binding_helper_ref={'path': str(Path(__file__).with_name('target_binding.py')),
                                            'sha256': hashlib.sha256(Path(__file__).with_name('target_binding.py').read_bytes()).hexdigest()},
                 token_bindings=bindings,
                 complete_coverage={k: v for k, v in coverage.items() if k != 'groups'},
                 new_teacher_responses=0, new_API_calls=0,
                 teacher_targets_and_inputs_unchanged=True,
                 independent_diagnosis_and_actor_acceptance_pending=True)
    proof_ref = once(root / 'REHEARSAL_MATERIALIZATION.json', proof)
    return revised, dataset_ref, proof_ref
