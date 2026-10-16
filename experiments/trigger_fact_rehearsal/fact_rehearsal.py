"""Focus redundant local visits only after complete positive-LR supervision.

Rows, teacher tokens, group order and nonlocal/policy samples stay immutable.
This is a supervised-learning intervention, not a scientific qualification.
"""
from copy import deepcopy


def rehearse(dataset, focus_masks, positive_group_indices):
    rows = dataset['rows']
    positive = set(positive_group_indices)
    if any(type(i) is not int or not 0 <= i < len(dataset['groups']) for i in positive):
        raise ValueError('POSITIVE_GROUP_INDEX')
    expected = {i: {j for j, v in enumerate(r['labels']) if j > 0 and v != -100}
                for i, r in enumerate(rows) if r['view'] == 'RESEARCH'}
    for i, mask in focus_masks.items():
        if i not in expected or rows[i]['stage'] not in ('L-A0', 'L-A1'):
            raise ValueError('LOCAL_RESEARCH_ONLY')
        if len(mask) != len(rows[i]['labels']):
            raise ValueError('TEACHER_LABEL_LENGTH')
        columns = {j for j, v in enumerate(mask) if j > 0 and v != -100}
        if not columns or not columns < expected[i]:
            raise ValueError('PARTIAL_TEACHER_FOCUS_REQUIRED')
        if any(mask[j] != rows[i]['labels'][j] for j in columns):
            raise ValueError('TEACHER_LABEL_SUBSTITUTION')
    result = deepcopy(dataset)
    seen = {i: set() for i in expected}
    changes = []
    for g, group in enumerate(result['groups']):
        # Only previous updates count; an earlier microbatch in the same
        # optimizer update has not yet changed the parameters.
        complete_before_update = {i for i in expected if expected[i] <= seen[i]}
        for n, sample in enumerate(group):
            i = sample['row_index']
            labels = sample['labels']
            if len(labels) != len(rows[i]['labels']):
                raise ValueError('GROUP_LABEL_LENGTH')
            columns = {j for j, v in enumerate(labels) if j > 0 and v != -100}
            if (len(columns) != sample['target_tokens'] or
                    any(labels[j] != rows[i]['labels'][j] for j in columns)):
                raise ValueError('GROUP_TEACHER_LABEL_SUBSTITUTION')
            if g in positive and i in focus_masks and i in complete_before_update:
                mask = focus_masks[i]
                focused = [v if j > 0 and mask[j] != -100 else -100
                           for j, v in enumerate(labels)]
                count = sum(v != -100 for v in focused[1:])
                if 0 < count < sample['target_tokens']:
                    changes.append({'group_index': g, 'sample_index': n,
                                    'row_index': i, 'row_id': rows[i]['row_id'],
                                    'old_target_tokens': sample['target_tokens'],
                                    'new_target_tokens': count})
                    sample.update(labels=focused, target_tokens=count)
            if g in positive and i in seen:
                seen[i].update(j for j, v in enumerate(sample['labels']) if j > 0 and v != -100)
    missing = {i: len(expected[i] - seen[i]) for i in expected if expected[i] - seen[i]}
    if missing:
        raise ValueError('POSITIVE_LR_FULL_RESEARCH_COVERAGE:' + str(missing))
    return result, {'changed_visits': len(changes), 'changes': changes,
                    'eligible_local_rows': len(focus_masks),
                    'research_rows_with_complete_positive_lr_coverage': len(expected),
                    'positive_lr_research_positions': sum(map(len, expected.values())),
                    'rows_and_teacher_targets_unchanged': result['rows'] == rows,
                    'nonlocal_and_policy_samples_unchanged': True,
                    'optimizer_steps_and_group_order_unchanged': True,
                    'raw_per_update_masks_unchanged_claimed': False,
                    'within_research_loss_mass_changed': bool(changes),
                    'method_qualified': False}
