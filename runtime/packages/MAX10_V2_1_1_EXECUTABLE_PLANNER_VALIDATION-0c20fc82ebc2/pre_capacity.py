"""Pure source joins, lossless review fragmentation and caller-rendered packing.

No transport, scientific selection or model summaries are implemented here.
Coverage proves the presence of all inputs/acknowledgments, not model comprehension.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pointer(path):
    return '/' + '/'.join(str(x).replace('~', '~0').replace('/', '~1') for x in path)


def _unique(rows, key):
    result = {}
    for row in rows:
        value = key(row)
        if value in result:
            raise ValueError('DUPLICATE_JOIN_IDENTITY:' + str(value))
        result[value] = row
    return result


def build_review_packets(projection):
    """Return all source packets plus residual/global evidence, preserving values.

    The caller supplies the already native-validated, outcome-blind projection.
    Additional identity checks prevent incorrect mechanical source joins.
    """
    original = deepcopy(projection)
    blind = original['blind_input']; evidence = blind['analyzer_evidence_view']
    universe = blind['registered_candidate_universe']; pairs = universe['pair_table']
    ep = ['blind_input', 'analyzer_evidence_view']
    up = ['blind_input', 'registered_candidate_universe']
    categories = ('source_contexts', 'group_findings', 'group_membership',
                  'local_findings', 'component_attributions', 'crosschecks', 'method_statuses')
    records = {}; refs = []

    def add(path, value):
        ref = {'pointer': _pointer(path), 'path': path, 'canonical_sha256': digest(value)}
        ref['record_id'] = digest(ref)
        records[tuple(path)] = {'ref': ref, 'value': value}; refs.append(ref)

    for key, value in original.items():
        if key != 'blind_input': add([key], value)
    for key, value in blind.items():
        if key not in ('analyzer_evidence_view', 'registered_candidate_universe'):
            add(['blind_input', key], value)
    for key, value in evidence.items():
        if key in categories and value:
            for i, row in enumerate(value): add(ep + [key, i], row)
        else: add(ep + [key], value)
    for key, value in universe.items():
        if key == 'pair_table' and value:
            for i, row in enumerate(value): add(up + [key, i], row)
        else: add(up + [key], value)

    sources = _unique(evidence['source_contexts'], lambda x: x['source_state_sha256'])
    groups = _unique(evidence['group_findings'], lambda x: x['artifact']['group_result_sha256'])
    memberships = _unique(evidence['group_membership'], lambda x: x['group_manifest_sha256'])
    locals_by_id = _unique(evidence['local_findings'], lambda x: x['local_result_sha256'])
    _unique(pairs, lambda x: x['source_state_sha256'])
    for pair in pairs:
        sid = pair['source_state_sha256']
        if sid not in sources: raise ValueError('PAIR_SOURCE_MISSING')
        source = sources[sid]; context = pair['source_context']
        if context['source_state_sha256'] != sid: raise ValueError('PAIR_SOURCE_CHANGED')
        if any(canonical(context[k]) != canonical(source[k]) for k in ('menu_sha256', 'admissible_commands')):
            raise ValueError('SOURCE_MENU_MISMATCH')
        for arm in ('A2', 'A3'):
            row = pair[arm]; candidate = row['candidate']
            if (row['source_state_sha256'] != sid or candidate['source_state_sha256'] != sid
                    or candidate['candidate_sha256'] != row['candidate_sha256']
                    or candidate['menu_sha256'] != source['menu_sha256']):
                raise ValueError('CANDIDATE_SOURCE_IDENTITY_MISMATCH')
            if not set(row['group_result_sha256s']) <= groups.keys():
                raise ValueError('GROUP_TARGET_MISSING')

    used = set(); packets = []

    def packet(kind, source, selected):
        rows = [records[path] for path in selected]
        value = {'kind': kind, 'source': source, 'records': rows}
        value['packet_id'] = digest({'kind': kind, 'source': source, 'records': [r['ref'] for r in rows]})
        packets.append(value); used.update(selected)

    for si, source in enumerate(evidence['source_contexts']):
        sid = source['source_state_sha256']
        matched_pairs = [(i, p) for i, p in enumerate(pairs) if p['source_state_sha256'] == sid]
        gids = {g for _, p in matched_pairs for arm in ('A2', 'A3') for g in p[arm]['group_result_sha256s']}
        seeds = [g for g in evidence['group_findings'] if g['artifact']['group_result_sha256'] in gids
                 or any(p['source_state_sha256'] == sid for p in g['artifact']['source_conditioned_proposals'])]
        mids = {g['artifact']['group_manifest_sha256'] for g in seeds}
        if not mids <= memberships.keys(): raise ValueError('GROUP_MEMBERSHIP_MISSING')
        matched_groups = [g for g in evidence['group_findings'] if g['artifact']['group_manifest_sha256'] in mids]
        gids = {g['artifact']['group_result_sha256'] for g in matched_groups}
        lids = set()
        for mid in mids:
            for member in memberships[mid]['membership_records']:
                if member['task_id'] != source['task_id'] or member['gamefile_sha256'] != source['gamefile_sha256']:
                    raise ValueError('MEMBERSHIP_SOURCE_MISMATCH')
                lid = member['local_result_sha256']; lids.add(lid)
                if lid not in locals_by_id: raise ValueError('LOCAL_FINDING_MISSING')
                if member['error_instance_id'] not in {e['error_instance_id'] for e in locals_by_id[lid]['error_instances']}:
                    raise ValueError('LOCAL_ERROR_INSTANCE_MISSING')
        predicates = {
            'group_findings': lambda r: r['artifact']['group_result_sha256'] in gids,
            'group_membership': lambda r: r['group_manifest_sha256'] in mids,
            'local_findings': lambda r: r['local_result_sha256'] in lids,
            'component_attributions': lambda r: r['artifact']['group_result_sha256'] in gids,
            'crosschecks': lambda r: r['artifact']['target_artifact_sha256'] in gids,
        }
        selected = [tuple(ep + ['source_contexts', si])] + [tuple(up + ['pair_table', i]) for i, _ in matched_pairs]
        for category, matches in predicates.items():
            selected.extend(tuple(ep + [category, i]) for i, row in enumerate(evidence[category]) if matches(row))
        calls = {records[path]['value']['source_ref']['path'].rsplit('/', 2)[-2]
                 for path in selected if 'source_ref' in records[path]['value']}
        selected.extend(tuple(ep + ['method_statuses', i]) for i, row in enumerate(evidence['method_statuses'])
                        if row['logical_call_id'] in calls)
        anchor = {k: source[k] for k in ('source_state_sha256', 'public_task_goal', 'task_id', 'gamefile_sha256', 'source_call_index')}
        anchor['source_context_ref'] = records[tuple(ep + ['source_contexts', si])]['ref']
        packet('SOURCE_REVIEW', anchor, selected)
    packet('GLOBAL_REVIEW', {'round_id': blind['round_id']}, [path for path in records if path not in used])
    inventory = {'schema_id': 'PRE_REVIEW_INVENTORY_V1', 'projection_canonical_sha256': digest(original),
                 'expected_records': refs, 'packets': packets}
    inventory['inventory_id'] = digest(inventory)
    return inventory


def wire_size(render, items):
    """render must be deterministic and side-effect free, returning exact bytes,
    a serialized string, or a request object using this canonical JSON encoding.
    """
    result = render(items)
    if isinstance(result, bytes): return len(result)
    if isinstance(result, str): return len(result.encode('utf-8'))
    return len(canonical(result))


def pack_review_packets(inventory, *, render, context_limit, max_output):
    """Greedily pack all evidence; fragment oversized records without truncation.

    Batches contain immutable content IDs, not provider execution identities.
    Bind them to the registered stage/runtime/round identity before transport.
    """
    if type(context_limit) is not int or type(max_output) is not int or not 0 <= max_output < context_limit:
        raise ValueError('INVALID_CONTEXT_BUDGET')
    if digest({k: v for k, v in inventory.items() if k != 'inventory_id'}) != inventory['inventory_id']:
        raise ValueError('INVENTORY_IDENTITY_CHANGED')
    limit = context_limit - max_output
    if wire_size(render, []) >= limit: raise ValueError('REQUEST_ENVELOPE_EXCEEDS_BUDGET')
    fragments = []
    for packet in inventory['packets']:
        source = deepcopy(packet['source'])

        def item(parts):
            value = {'packet_id': packet['packet_id'], 'kind': packet['kind'], 'source': source, 'parts': parts}
            value['fragment_id'] = digest(value)
            return value

        def fits(parts): return wire_size(render, [item(parts)]) <= limit

        def span_probe(record_id, pointer, path, value):
            length = len(canonical(value).decode('utf-8'))
            return {'record_id': record_id, 'record_pointer': pointer, 'path': path,
                    'text_span': {'offset': length, 'total_chars': length, 'text': '\x00"\\\n'}}

        def header_fits():
            return all(fits([span_probe(r['ref']['record_id'], r['ref']['pointer'], [], r['value'])])
                       for r in packet['records'])

        # An unusually large goal is still included completely in its source
        # record. Repeat its exact reference rather than an invented short goal.
        if not header_fits():
            source = {k: v for k, v in source.items() if k != 'public_task_goal'}
            source['public_goal_in_source_context_fragments'] = True
        if not header_fits():
            source = {k: v for k, v in source.items() if k in ('source_state_sha256', 'source_context_ref', 'round_id')}
            source['public_goal_in_source_context_fragments'] = True
        if not header_fits():
            raise ValueError('REVIEW_IDENTITY_ENVELOPE_EXCEEDS_BUDGET')

        def split(part):
            if fits([part]): return [part]
            value = part['value']; path = part['path']
            identity = {k: part[k] for k in ('record_id', 'record_pointer')}
            children = (list(value.items()) if isinstance(value, dict) else list(enumerate(value)) if isinstance(value, list) else [])
            if children:
                probes = [span_probe(part['record_id'], part['record_pointer'], path + [key], child)
                          for key, child in children]
                if all(fits([probe]) for probe in probes):
                    return [piece for key, child in children for piece in split({**identity, 'path': path + [key], 'value': child})]
            text = canonical(value).decode('utf-8'); result = []; start = 0
            while start < len(text):
                def span(end):
                    return {**identity, 'path': path,
                            'text_span': {'offset': start, 'total_chars': len(text), 'text': text[start:end]}}
                low, high = start + 1, len(text); end = start
                while low <= high:
                    mid = (low + high) // 2
                    if fits([span(mid)]): end = mid; low = mid + 1
                    else: high = mid - 1
                if end == start: raise ValueError('FRAGMENT_METADATA_ENVELOPE_EXCEEDS_BUDGET')
                result.append(span(end)); start = end
            return result

        current = []
        for record in packet['records']:
            if digest(record['value']) != record['ref']['canonical_sha256']:
                raise ValueError('RECORD_IDENTITY_CHANGED')
            part = {'record_id': record['ref']['record_id'], 'record_pointer': record['ref']['pointer'],
                    'path': [], 'value': record['value']}
            for piece in split(part):
                if current and not fits(current + [piece]): fragments.append(item(current)); current = []
                current.append(piece)
        if current: fragments.append(item(current))

    batches = []; current = []

    def close(items):
        value = {'items': items, 'wire_bytes': wire_size(render, items)}
        value['batch_id'] = digest({'fragment_ids': [i['fragment_id'] for i in items], 'wire_bytes': value['wire_bytes']})
        batches.append(value)

    for fragment in fragments:
        if current and wire_size(render, current + [fragment]) > limit: close(current); current = []
        current.append(fragment)
    if current: close(current)
    plan = {'schema_id': 'PRE_BOUNDED_REVIEW_PLAN_V1', 'inventory_id': inventory['inventory_id'],
            'projection_canonical_sha256': inventory['projection_canonical_sha256'],
            'expected_records': deepcopy(inventory['expected_records']),
            'expected_fragment_ids': [f['fragment_id'] for f in fragments],
            'context_limit': context_limit, 'max_output': max_output, 'input_wire_limit': limit,
            'batches': batches}
    plan['plan_id'] = digest(plan)
    return plan


def verify_review_coverage(plan, fragment_ids):
    """Require one acknowledged review per expected fragment before aggregation."""
    if digest({k: v for k, v in plan.items() if k != 'plan_id'}) != plan['plan_id']:
        raise ValueError('PLAN_IDENTITY_CHANGED')
    observed = list(fragment_ids); expected = plan['expected_fragment_ids']
    if (len(observed) != len(set(observed)) or len(expected) != len(set(expected))
            or set(observed) != set(expected)):
        raise ValueError('REVIEW_FRAGMENT_COVERAGE_INCOMPLETE_OR_DUPLICATE')
    return {'reviewed_fragment_count': len(observed), 'coverage_sha256': digest(sorted(observed))}


_MISSING = object()


def _place(root, path, value):
    if not path:
        if root is not _MISSING and canonical(root) != canonical(value): raise ValueError('CONFLICTING_RECORD_PARTS')
        return deepcopy(value)
    if root is _MISSING: root = [] if type(path[0]) is int else {}
    key = path[0]
    if isinstance(root, list):
        if type(key) is not int or key < 0: raise ValueError('INVALID_ARRAY_PART')
        while len(root) <= key: root.append(_MISSING)
        root[key] = _place(root[key], path[1:], value)
    elif isinstance(root, dict): root[key] = _place(root.get(key, _MISSING), path[1:], value)
    else: raise ValueError('INVALID_RECORD_PART_PATH')
    return root


def restore_projection(plan):
    """Audit helper: reconstruct every original field and verify all identities."""
    if digest({k: v for k, v in plan.items() if k != 'plan_id'}) != plan['plan_id']:
        raise ValueError('PLAN_IDENTITY_CHANGED')
    parts = defaultdict(list); ids = []
    for batch in plan['batches']:
        for item in batch['items']:
            if digest({k: v for k, v in item.items() if k != 'fragment_id'}) != item['fragment_id']:
                raise ValueError('FRAGMENT_IDENTITY_CHANGED')
            ids.append(item['fragment_id'])
            for part in item['parts']: parts[(item['packet_id'], part['record_id'])].append(part)
    verify_review_coverage(plan, ids)
    expected = {r['record_id']: r for r in plan['expected_records']}
    if {rid for _, rid in parts} != set(expected): raise ValueError('ORIGINAL_RECORD_COVERAGE_MISMATCH')
    projection = _MISSING
    # Shared evidence can have different split points under different source
    # headers. Reconstruct each complete occurrence before comparing its hash.
    for (_, rid), rows in parts.items():
        by_path = defaultdict(list)
        for row in rows: by_path[tuple(row['path'])].append(row)
        values = []
        for path, pieces in by_path.items():
            plain = [x['value'] for x in pieces if 'value' in x]
            spans = [x['text_span'] for x in pieces if 'text_span' in x]
            if spans:
                totals = {x['total_chars'] for x in spans}
                if len(totals) != 1: raise ValueError('FRAGMENT_LENGTH_CONFLICT')
                positions = {}
                for span in spans:
                    key = span['offset']
                    if key in positions and positions[key] != span['text']: raise ValueError('FRAGMENT_SPAN_CONFLICT')
                    positions[key] = span['text']
                cursor = 0; texts = []
                for offset, text in sorted(positions.items()):
                    if offset != cursor: raise ValueError('FRAGMENT_GAP_OR_OVERLAP')
                    texts.append(text); cursor += len(text)
                if cursor != next(iter(totals)): raise ValueError('FRAGMENT_LENGTH_MISMATCH')
                plain.append(json.loads(''.join(texts)))
            if not plain or any(canonical(v) != canonical(plain[0]) for v in plain): raise ValueError('RECORD_PART_CONFLICT')
            values.append((path, plain[0]))
        value = _MISSING
        for path, part in sorted(values, key=lambda x: len(x[0])): value = _place(value, path, part)
        ref = expected[rid]
        if digest(value) != ref['canonical_sha256']: raise ValueError('RESTORED_RECORD_HASH_MISMATCH')
        projection = _place(projection, ref['path'], value)
    if digest(projection) != plan['projection_canonical_sha256']: raise ValueError('RESTORED_PROJECTION_HASH_MISMATCH')
    return projection
