"""Resolve the registered execution teacher without changing any row tokens."""
import hashlib
import json

sha = lambda s: hashlib.sha256(s.encode()).hexdigest()


def target_for_row(row, checked, approved_proofs):
    # Admission belongs to the current SHA-bound execution dataset and its
    # checked authority. Historical teacher-rendering flags remain provenance.
    if row.get('training_admitted') is not True:
        raise ValueError('EXECUTION_ROW_NOT_ADMITTED')
    if 'conditional_teacher_target_ref' in row:
        ref = row['conditional_teacher_target_ref']
        teacher = checked(ref)
        raw = teacher['target_text']
        text = row['target']
        if text != raw:
            if row.get('target_representation') != 'APPROVED_LOSSLESS_NATIVE_JSON_EXECUTION_VIEW':
                raise ValueError('CONDITIONAL_EXECUTION_TARGET_BINDING')
            proof = approved_proofs.get(row['row_id'])
            approval = checked(row['execution_view_approval_ref'])
            if (proof is None or approval.get('decision') != 'APPROVED' or
                    row['row_id'] not in approval['row_ids'] or
                    row.get('raw_teacher_target_ref') != ref or proof['raw_teacher_target_ref'] != ref or
                    proof['raw_text_sha256'] != sha(raw) or proof['view_text_sha256'] != sha(text) or
                    not proof['all_scientific_values_and_array_order_equal'] or not proof['native_emittable']):
                raise ValueError('APPROVED_EXECUTION_TARGET_PROOF_BINDING')
            if json.loads(text) != json.loads(raw):
                raise ValueError('APPROVED_VIEW_SCIENTIFIC_VALUE_CHANGE')
        return text, ref
    if 'shared_scientific_target_ref' in row:
        ref = row['shared_scientific_target_ref']
        text = checked(ref)['target_text']
        if 'target' in row and row['target'] != text:
            raise ValueError('SHARED_EXECUTION_TARGET_BINDING')
        return text, ref
    return row['target'], row.get('complete_teacher_target_ref')
