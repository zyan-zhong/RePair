"""Bind current selected candidates to the existing native replay dataclasses.

Candidate (Analyzer) identities are never rewritten into native fingerprints.
The native bundle loader and request factory remain the validation authorities.
"""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from io_utils import read_json,sha,digest_file

ROOT=Path(__file__).resolve().parent
NATIVE=ROOT/'native_repo'
if str(NATIVE/'src') not in sys.path:sys.path.insert(0,str(NATIVE/'src'))


def _loader():
    path=NATIVE/'scripts/memory/materialize_sequence_failure_experience_v1.py'
    spec=importlib.util.spec_from_file_location('_native_bundle_loader',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def load_source_rows(capture:Path)->list[dict[str,Any]]:
    from pchsi.memory.source_state_contracts import SourceDecisionStateFingerprintV1
    from pchsi.research_intelligence.human_f0f1_runtime import build_bound_continuation_request_v1
    handoff=read_json(capture/'pre_root/V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json')
    prep=read_json(capture/'native_preparation/CURRENT_NATIVE_REPLAY_PROMPT_PREPARATION_V1.json')
    runtime=read_json(capture/'actor_runtime/runtime_binding.json')
    prepared=prep['states'];by_state={x['analyzer_source_state_sha256']:x for x in prepared}
    if len(by_state)!=len(prepared):raise ValueError('duplicate source bridge')
    loader=_loader();out=[]
    for selected in handoff['selected_states']:
        state=selected['source_state_sha256']
        if state not in by_state:raise ValueError('selected source has no native bridge')
        row=by_state[state]
        native_fp=row['native_source_fingerprint_sha256']
        fp=read_json(capture/f'native_preparation/states/{native_fp}/SOURCE_DECISION_STATE_FINGERPRINT_V1.json')
        SourceDecisionStateFingerprintV1.from_dict(fp)
        bridge=read_json(capture/f'native_preparation/states/{native_fp}/ANALYZER_TO_NATIVE_SOURCE_BINDING_V1.json')
        candidate=selected['candidate']
        if candidate['source_state_sha256']!=state or candidate['candidate_sha256']!=selected['preferred_candidate_sha256']:
            raise ValueError('candidate identity differs from selected authority')
        if bridge['source_candidate_sha256']!=candidate['candidate_sha256'] or bridge['analyzer_source_state_sha256']!=state:
            raise ValueError('candidate/source bridge mismatch')
        bundle_dir=capture/'selected_source_bundles'/bridge['source_bundle_sha256']
        bundle=loader.load_attempt_directory_v1(bundle_dir)
        if bundle.attempt_bundle.attempt_bundle_sha256!=bridge['source_bundle_sha256']:raise ValueError('native bundle SHA mismatch')
        idx=bridge['source_call_index'];calls={x.model_call_index:x for x in bundle.policy_calls}
        call=calls[idx]
        if sha(call.to_json().encode())!=bridge['source_policy_call_sha256']:raise ValueError('source policy call mismatch')
        if sha(call.prompt_text.encode())!=fp['base_policy_input_sha256']:raise ValueError('source prompt fingerprint mismatch')
        wire=json.loads(call.request_wire_bytes)
        request=build_bound_continuation_request_v1(runtime=runtime,prompt_text=call.prompt_text,
                  seed=wire['seed'],request_id=call.client_request_id)
        if sha(request.to_wire_bytes())!=call.request_wire_sha256:raise ValueError('original source wire mismatch')
        out.append({'handoff_state':selected,'candidate':candidate,'fingerprint':fp,'bridge':bridge,
                    'bundle':bundle,'bundle_dir':bundle_dir,'source_call':call})
    if len(out)!=handoff['selected_state_count']:raise ValueError('selected count mismatch')
    return out


def register_source(row:dict[str,Any],*,exact_gamefile:Path,verify_gamefile:bool=True):
    from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1,ReplayTransitionExpectationV1,SourceDecisionStateFingerprintV1
    from pchsi.evaluation.action_trace import ExecutionStatus,sha256_string_sequence
    fp=SourceDecisionStateFingerprintV1.from_dict(row['fingerprint'])
    bundle=row['bundle'];episode=bundle.episode_artifact
    if verify_gamefile and (not exact_gamefile.is_file() or digest_file(exact_gamefile)!=fp.source_gamefile_sha256):
        raise ValueError('exact gamefile missing or hash mismatch')
    if episode.task_id!=fp.source_task_id or episode.gamefile_sha256!=fp.source_gamefile_sha256:raise ValueError('task/gamefile source mismatch')
    traces=sorted(bundle.traces,key=lambda x:x.model_call_index)
    prefix=[t for t in traces if t.model_call_index<fp.model_call_index and t.execution_status==ExecutionStatus.EXECUTED]
    transitions={x.environment_step_index:x for x in bundle.public_transitions}
    expectations=[]
    for t in prefix:
        p=transitions[t.environment_step_index]
        if p.submitted_action!=t.final_executed_action or p.pre_action_observation_sha256!=sha(t.observation.encode()) or p.pre_action_admissible_commands_sha256!=sha256_string_sequence(tuple(t.admissible_commands)):
            raise ValueError('executed prefix trace/transition mismatch')
        expectations.append(ReplayTransitionExpectationV1(
            environment_step_index=p.environment_step_index,action=p.submitted_action,
            pre_observation_sha256=p.pre_action_observation_sha256,
            pre_menu_sequence_sha256=p.pre_action_admissible_commands_sha256,
            resulting_observation_sha256=p.resulting_observation_sha256,
            resulting_menu_sequence_sha256=p.resulting_admissible_commands_sha256,
            score=p.score,done=p.done,won=p.won))
    if len(expectations)!=fp.budget_state.environment_step_count:raise ValueError('prefix/environment budget mismatch')
    return RegisteredReplaySourceV1(
        schema_id='REGISTERED_SOURCE_STATE_REPLAY_V1',schema_version=1,
        source_task_id=fp.source_task_id,exact_gamefile=str(exact_gamefile.absolute()),
        source_gamefile_sha256=fp.source_gamefile_sha256,source_bundle_sha256=fp.source_bundle_sha256,
        source_policy_condition=fp.source_policy_condition,runtime_manifest_sha256=episode.environment_runtime_manifest_sha256,
        executed_prefix_sha256=fp.executed_prefix_sha256,
        reset_observation_sha256=sha(traces[0].observation.encode()),
        reset_menu_sequence_sha256=sha256_string_sequence(tuple(traces[0].admissible_commands)),
        transitions=tuple(expectations),memory_m0_sha256=fp.memory_m0_sha256,
        interface_feedback_code=fp.interface_feedback_code,budget_state=fp.budget_state,
        model_call_index=fp.model_call_index,base_policy_input_sha256=fp.base_policy_input_sha256,
        expected_source_fingerprint=fp)
