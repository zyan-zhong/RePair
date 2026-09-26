"""Mechanical capture of exact accepted PRE and original native source bundles."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from exact_bindings import (BindingError, canonical, digest, file_ref, immutable_bytes,
                            immutable_json, read_json, read_ref, regular)
from reuse import package_root


def materialize_capture(binding, values, core, pre_root, accepted, handoff, sources, out):
    from pchsi.memory.source_state_contracts import (
        ReplayTransitionExpectationV1, build_source_decision_state_fingerprint_v1)
    from pchsi.evaluation.budget import BudgetState
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes
    from pchsi.research_intelligence.human_f0f1_runtime import build_bound_continuation_request_v1

    out = Path(out); pre_root = Path(pre_root); members = {}
    if read_ref(accepted['handoff']) != handoff:
        raise BindingError('CAPTURE_ACCEPTED_HANDOFF_CHANGED')

    def add(name, raw):
        if name in members and members[name] != raw:
            raise BindingError('CAPTURE_MEMBER_CONFLICT:' + name)
        members[name] = raw

    add('current_rollout/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json', read_ref(binding['refs']['request'], as_bytes=True))
    add('actor_runtime/runtime_binding.json', read_ref(binding['refs']['actor_runtime'], as_bytes=True))
    for filename in ('V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json', 'RESEARCHER_MEMORY_VIEW_V1.json',
                     'V1232V_PRE_SCIENTIFIC_UNIT_IDENTITY_V1.json', 'V1232V_PRE_TASK_ACCESS_V1.json',
                     'EXACT_RUNTIME_MANIFEST.json', 'ACCEPTED_PRE_REF.json', 'PRE_PROVIDER_SCHEMA.json',
                     'PRE_STRATEGY_PROMPT.txt', 'NATIVE_LABELS_SOURCE_SEAL.json'):
        add('pre_root/' + filename, regular(pre_root / filename).read_bytes())
    call_id = accepted['accepted_pre_logical_call_id']
    from training_binding.capture import REF_KEYS, RECEIPT_MEMBER, BINDING_MEMBER
    from training_binding.materializer import _read_ref, _verify_seal
    receipt_raw = read_ref(accepted['pre_strategy_receipt'], as_bytes=True)
    receipt = json.loads(receipt_raw); _verify_seal(receipt, 'pre_strategy_receipt_sha256')
    if receipt['logical_call_id'] != call_id or receipt['source_pre_primary_record_sha256'] != accepted['pre_primary_record_sha256']:
        raise BindingError('CAPTURE_PRE_STRATEGY_IDENTITY')
    add(RECEIPT_MEMBER, receipt_raw)
    refs = {}
    for key in REF_KEYS:
        ref = receipt[key]; path = Path(ref['path'])
        if path.parent.resolve() != (pre_root / 'strong_pre_runtime' / call_id).resolve():
            raise BindingError('CAPTURE_PRE_REFERENCE_NOT_IN_ACCEPTED_CALL:' + key)
        member = 'pre_root/strong_pre_runtime/' + call_id + '/' + path.name
        add(member, _read_ref(ref))
        refs[key] = {'member': member, 'original_path': ref['path'], 'sha256': ref['sha256']}
    labels_raw = read_ref(accepted['native_labels_source_seal'], as_bytes=True)
    if labels_raw != members['pre_root/NATIVE_LABELS_SOURCE_SEAL.json']:
        raise BindingError('CAPTURE_NATIVE_LABELS_SOURCE_SEAL_CHANGED')
    add(BINDING_MEMBER, canonical({'schema_id': 'CURRENT_PRE_STRATEGY_CAPTURE_BINDING_V1',
        'receipt_member': RECEIPT_MEMBER, 'receipt_file_sha256': digest(receipt_raw),
        'pre_strategy_receipt_sha256': receipt['pre_strategy_receipt_sha256'], 'ref_members': refs,
        'native_labels_source_seal_member': 'pre_root/NATIVE_LABELS_SOURCE_SEAL.json',
        'native_labels_source_seal_sha256': digest(labels_raw)}))
    # H4.4's own POST policy fixes this scope. It is a statement of design,
    # never an observed environmental effect or an A3-vs-A2 claim.
    scope = {'schema_id': 'HYPOTHESIS_SCOPE_NOTICE_V1', 'schema_version': 1,
        'comparison_scope': 'SELECTED_REPAIR_VS_PARENT_CONTINUATION_NOT_A3_VS_A2',
        'hypothesis_status': 'UNRESOLVED_FOR_ORIGINAL_A3_VERSUS_A2_CLAIM',
        'effect_authority': 'INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY'}
    if 'hypothesis_scope_notice' in binding['refs']:
        add('native_execution_gate/HYPOTHESIS_SCOPE_NOTICE_V1.json',
            read_ref(binding['refs']['hypothesis_scope_notice'], as_bytes=True))
    else:
        add('native_execution_gate/HYPOTHESIS_SCOPE_NOTICE_V1.json', canonical(scope))
    prepared = []; used = set()
    for selected in handoff['selected_states']:
        state = selected['source_state_sha256']
        if state not in sources:
            raise BindingError('REGISTERED_SOURCE_CONTEXT_MISSING:' + state)
        source = sources[state]; directory = Path(source['bundle_path'])
        bundle = core.api['load_attempt_directory_v1'](directory)
        if bundle.attempt_bundle.attempt_bundle_sha256 != source['bundle_sha256']:
            raise BindingError('CAPTURE_SOURCE_BUNDLE_IDENTITY_MISMATCH')
        calls = {x.model_call_index: x for x in bundle.policy_calls}
        call = calls[source['source_call_index']]; episode = bundle.episode_artifact
        context = source['context']
        for key, observed in [('menu_sha256', call.admissible_commands_sequence_sha256),
                              ('observation', call.observation), ('admissible_commands', list(call.admissible_commands)),
                              ('source_call_index', call.model_call_index)]:
            if context.get(key) != observed:
                raise BindingError('ANALYZER_NATIVE_CONTEXT_MISMATCH:' + key)
        original_wire = json.loads(call.request_wire_bytes)
        request = build_bound_continuation_request_v1(runtime=values['actor_runtime'],
            prompt_text=call.prompt_text, seed=original_wire['seed'], request_id=call.client_request_id)
        if digest(request.to_wire_bytes()) != call.request_wire_sha256:
            raise BindingError('SOURCE_REQUEST_WIRE_MISMATCH')
        condition = episode.policy_condition_id
        if not condition:
            raise BindingError('REGISTERED_SOURCE_POLICY_CONDITION_MISSING')
        prefix = sorted((x for x in bundle.public_transitions if x.model_call_index < call.model_call_index),
                        key=lambda x: x.environment_step_index)
        expectations = []
        for index, transition in enumerate(prefix):
            if transition.environment_step_index != index:
                raise BindingError('SOURCE_PREFIX_NONCONTIGUOUS')
            expectations.append(ReplayTransitionExpectationV1(environment_step_index=index,
                action=transition.submitted_action, pre_observation_sha256=transition.pre_action_observation_sha256,
                pre_menu_sequence_sha256=transition.pre_action_admissible_commands_sha256,
                resulting_observation_sha256=transition.resulting_observation_sha256,
                resulting_menu_sequence_sha256=transition.resulting_admissible_commands_sha256,
                score=transition.score, done=transition.done, won=transition.won))
        prefix_sha = digest(b'SOURCE_EXECUTED_PREFIX_V1\0' + canonical_json_bytes([x.to_dict() for x in expectations]))
        fingerprint = build_source_decision_state_fingerprint_v1(source_task_id=episode.task_id,
            source_gamefile_sha256=episode.gamefile_sha256, source_bundle_sha256=source['bundle_sha256'],
            source_policy_condition=condition, executed_prefix_sha256=prefix_sha,
            observation_sha256=call.observation_sha256, menu_sequence_sha256=call.admissible_commands_sequence_sha256,
            memory_m0_sha256=call.executed_history_sha256, interface_feedback_code=call.interface_feedback_before,
            budget_state=BudgetState(**dict(call.budget_before)), model_call_index=call.model_call_index,
            base_policy_input_sha256=call.prompt_sha256)
        fp = fingerprint.fingerprint_sha256
        # Distinct Analyzer states may intentionally share one native state only
        # when all execution and source-candidate bindings agree. H4 path format
        # has one bridge per fingerprint, so conflicting candidates fail closed.
        bridge = {'schema_id': 'ANALYZER_TO_NATIVE_SOURCE_BINDING_V1', 'schema_version': 1,
            'analyzer_source_state_sha256': state, 'native_source_fingerprint_sha256': fp,
            'source_candidate_sha256': selected['preferred_candidate_sha256'],
            'source_bundle_sha256': source['bundle_sha256'], 'source_call_index': call.model_call_index,
            'source_policy_call_sha256': digest(call.to_json().encode())}
        add(f'native_preparation/states/{fp}/SOURCE_DECISION_STATE_FINGERPRINT_V1.json', fingerprint.canonical_bytes())
        add(f'native_preparation/states/{fp}/ANALYZER_TO_NATIVE_SOURCE_BINDING_V1.json', canonical(bridge))
        prepared.append({'analyzer_source_state_sha256': state, 'native_source_fingerprint_sha256': fp})
        if source['bundle_sha256'] not in used:
            for name in ('attempt.json', 'action_traces.jsonl', 'policy_calls.jsonl', 'public_transitions.jsonl', 'SHA256SUMS'):
                add('selected_source_bundles/' + source['bundle_sha256'] + '/' + name, regular(directory / name).read_bytes())
            used.add(source['bundle_sha256'])
    add('native_preparation/CURRENT_NATIVE_REPLAY_PROMPT_PREPARATION_V1.json', canonical({
        'schema_id': 'CURRENT_NATIVE_REPLAY_PROMPT_PREPARATION_V1', 'schema_version': 1,
        'round_id': binding['round_id'], 'states': prepared}))
    index = {'schema_id': 'EXACT_CURRENT_H44_CAPTURE_INDEX_V1_6', 'files': [
        {'member': name, 'sha256': digest(raw), 'bytes': len(raw)} for name, raw in sorted(members.items())]}
    add('CAPTURE_INDEX.json', canonical(index))
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, raw)
    destination = out / 'CURRENT_H44_CAPTURE.zip'; immutable_bytes(destination, archive.getvalue())
    return file_ref(destination)


def run_h44(binding, capture_ref, out, *, execute):
    """Run original H4.4 in a fresh process with only two exact locator rewrites."""
    root = package_root(binding, 'h44'); out = Path(out).absolute()
    locators = read_json(root / 'assets/deployment_authorities.json')
    # Current registered paths; Memory fallback glob is disabled by explicit env.
    locators.update(train_update_manifest_path=binding['refs']['train_update_manifest']['path'],
                    train_root=binding['train_root'], output_parent=str(out))
    locators_path = out / 'DEPLOYMENT_AUTHORITY.json'; immutable_json(locators_path, locators)
    request = {'h44_root': str(root), 'capture': capture_ref, 'run_root': str(out / 'run'),
        'h44_manifest': binding['packages']['h44']['manifest'],
        'locators': locators, 'memory_runtime': binding['refs']['memory_runtime'],
        'execute': execute, 'scientific_repo_root': binding['scientific_repo_root'],
        'strategy_receipt_relative_path': 'pre_root/PRE_STRATEGY_RECEIPT.json'}
    raw_capture = read_ref(capture_ref, as_bytes=True)
    with zipfile.ZipFile(io.BytesIO(raw_capture)) as archive:
        label_seal = json.loads(archive.read('pre_root/NATIVE_LABELS_SOURCE_SEAL.json'))
    if label_seal['scientific_repo_root'] != binding['scientific_repo_root']:
        raise BindingError('H44_NATIVE_LABELS_REPOSITORY_MISMATCH')
    request['native_labels_sources'] = {name: ref['file_sha256'] for name, ref in label_seal['files'].items()}
    request_path = out / 'H44_ADAPTER_REQUEST.json'; immutable_json(request_path, request)
    result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('h44_worker.py')),
                             '--request', str(request_path)], check=False)
    terminal = out / 'run' / 'ROUND_EXECUTION_TERMINAL.json'
    if result.returncode != 0:
        raise BindingError('H44_EXISTING_CORE_RETURNED:' + str(result.returncode))
    if execute and not terminal.is_file():
        raise BindingError('H44_EXECUTION_RETURNED_WITHOUT_TERMINAL')
    return file_ref(terminal) if execute else file_ref(out / 'run' / 'EXECUTION_PLAN.json')
