"""The concrete existing-component route owned by campaign_owner."""
from __future__ import annotations

from pathlib import Path
import sys

from exact_bindings import (BindingError, canonical, digest, file_ref, immutable_json,
                            read_json, read_ref, build_from_rollout_result)
from rollout_adapter.materializer import build_registered_spec, materialize
from analyzer_binding.source_binding import build_source_binding, SourceLayout
from analyzer_binding.aggregate_context import project_previous_select_context
from .rollout import await_rollout


def _native_ref(ref):
    return {'path': ref['path'], 'sha256': ref.get('sha256', ref.get('file_sha256'))}


def _file_ref(ref):
    return {'path': ref['path'], 'file_sha256': ref.get('file_sha256', ref.get('sha256'))}


def current_rollout_inputs(materialized, start, out, *, prior_input_refs=None):
    refs = {}
    for role, request_field in [('runtime', 'policy_runtime_binding_sha256'),
        ('memory', 'round_memory_runtime_authority_sha256'),
        ('train_manifest', 'train_update_manifest_sha256')]:
        row = materialized['input_member_manifest'][role]
        member = Path(row['member'])
        if member.is_absolute() or '..' in member.parts or '\\' in row['member']:
            raise BindingError('CURRENT_ROLLOUT_INPUT_MEMBER_ESCAPE:' + role)
        ref = {'path': str(Path(materialized['root']) / 'input_capsule' / row['member']),
               'sha256': row['sha256']}
        read_ref(_file_ref(ref), as_bytes=True)
        if row['sha256'] != start[request_field]:
            raise BindingError('CURRENT_ROLLOUT_INPUT_IDENTITY:' + role)
        refs[role] = ref
    refs['profile'] = materialized['execution_profile_ref']
    read_ref(_file_ref(refs['profile']))
    if refs['profile']['sha256'] != start['execution_profile_sha256']:
        raise BindingError('CURRENT_ROLLOUT_PROFILE_IDENTITY')
    # The already materialized current capsule owns the engine and service
    # identities. Preserve these across a later NO_TRAIN or ROLLBACK as well.
    name = 'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json'
    bound_ref = {'path':str(Path(materialized['root'])/'input_capsule'/name),
                 'file_sha256':materialized['capsule_member_sha256'][name]}
    bound = read_ref(bound_ref)
    if (bound['round_id'] != start['round_id'] or bound['parent_policy_id'] != start['parent_policy_id']
            or bound['runtime_authority']['runtime_binding_file_sha256'] != start['policy_runtime_binding_sha256']):
        raise BindingError('CURRENT_ROLLOUT_CAPSULE_POLICY_IDENTITY')
    engine_path = Path(out)/'CURRENT_ENGINE_PROFILE.json'
    immutable_json(engine_path, bound['engine_profile_authority'])
    refs['engine_profile'] = _native_ref(file_ref(engine_path))
    if prior_input_refs is not None:
        prior = read_ref(_file_ref(prior_input_refs))
        if prior.get('schema_id') != 'ROUND_ROLLOUT_INPUT_REFERENCES_V1' or prior.get('request_sha256') != start['request_sha256']:
            raise BindingError('CURRENT_PRIOR_INPUT_REQUEST_IDENTITY')
        for role in ('policy_launch_authority','resource_plan','train_authority'):
            if role in prior:
                read_ref(_file_ref(prior[role]))
                refs[role] = _native_ref(prior[role])
        if 'engine_profile' in prior and read_ref(_file_ref(prior['engine_profile'])) != bound['engine_profile_authority']:
            raise BindingError('CURRENT_PRIOR_ENGINE_IDENTITY')
        if 'policy_launch_authority' in refs:
            authority=read_ref(_file_ref(refs['policy_launch_authority']))
            if any(authority.get(k)!=v for k,v in {
                    'schema_id':'ROUND_POLICY_NATIVE_LAUNCH_AUTHORITY_V1',
                    'parent_policy_id':start['parent_policy_id'],
                    'parent_policy_artifact_sha256':start['parent_policy_artifact_sha256'],
                    'runtime_binding_file_sha256':start['policy_runtime_binding_sha256']}.items()):
                raise BindingError('CURRENT_PRIOR_LAUNCH_POLICY_IDENTITY')
            if read_ref(_file_ref(authority['launch_contract'])) != bound['service_launch_contract']:
                raise BindingError('CURRENT_PRIOR_SERVICE_LAUNCH_IDENTITY')
    value = {'schema_id': 'ROUND_ROLLOUT_INPUT_REFERENCES_V1',
             'request_sha256': start['request_sha256'], **refs}
    path = Path(out) / 'CURRENT_ROLLOUT_INPUT_REFERENCES.json'
    immutable_json(path, value)
    return _native_ref(file_ref(path))


def current_h44_evidence(analyzer_output):
    root = Path(analyzer_output) / 'h44/run'
    terminal = read_json(root / 'post/POST_TERMINAL.json')
    logical = terminal['logical_call_id']
    if not isinstance(logical, str) or len(logical) != 64 or any(c not in '0123456789abcdef' for c in logical):
        raise BindingError('CURRENT_POST_LOGICAL_ID_REQUIRED')
    return {key: _native_ref(file_ref(root / relative)) for key, relative in {
        'execution_plan': 'EXECUTION_PLAN.json',
        'verifier': 'verifier/ENVIRONMENT_RESULT_PACKAGE.json',
        'post_projection': 'post/projection.json',
        'post_artifact': 'post/calls/' + logical + '/validated_artifact.json',
        'post_logical_call': 'post/calls/' + logical + '/logical_call.json',
    }.items()}


def replay_closed_h44(result):
    """Original independent replay only; never execute environment/provider code."""
    from reuse import package_root, load_file
    binding=read_json(Path(result['attempt_root'])/'CURRENT_ANALYZER_BINDING.json')
    root=package_root(binding,'h44')
    for name in ('io_utils','native_branch','option_adapter'):
        existing=sys.modules.get(name)
        if existing is not None and Path(existing.__file__).resolve() != (root/(name+'.py')).resolve():
            raise BindingError('RESIDENT_VERIFIER_SOURCE_IMPORT_CONFLICT:'+name)
    sys.path.insert(0,str(root))
    verifier=load_file('_resident_original_h44_verifier',root/'independent_verifier.py')
    refs=result['stage_evidence_refs']
    plan_ref=_file_ref(refs['execution_plan']);read_ref(plan_ref)
    expected=read_ref(_file_ref(refs['verifier']))
    plan_path=Path(plan_ref['path'])
    observed=verifier.verify_plan(plan_path,plan_path.parent)
    if observed != expected:
        raise BindingError('RESIDENT_PERSISTED_H44_VERIFIER_MISMATCH')


class ExistingComponentRoundDriver:
    """No research choices: consumes native decisions and carries exact refs."""

    def __init__(self, *, bundle_root, formal_root, owner_root, deployment, initial):
        self.bundle_root = Path(bundle_root).absolute()
        self.formal_root = Path(formal_root).absolute()
        self.owner_root = Path(owner_root).absolute()
        self.deployment = deployment
        self.initial = dict(initial)
        self.source_identity_sha256 = deployment['entry_source_sha256']
        self.repo = Path(deployment['scientific_repo_root'])
        self.layout = SourceLayout.bundle(self.bundle_root)

    def _binding_path(self, start):
        return self.owner_root / 'request_bindings' / (start['request_sha256'] + '.json')

    def register_initial(self):
        value = {'schema_id': 'CURRENT_FORMAL_RESIDENT_REQUEST_BINDING_V1',
            'request': _native_ref(file_ref(self.formal_root / 'ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json')),
            'execution_binding': _native_ref(file_ref(self.formal_root / 'ROUND_ROLLOUT_EXECUTION_BINDING_V1.json')),
            'input_refs': None, 'current_index': None, 'memory_state': None,
            'current_parent_context': None, 'round_index': 1}
        immutable_json(self._binding_path(self.initial), value)

    def preflight(self):
        from .preflight import validate_deployment
        validate_deployment(self.deployment, formal_root=self.formal_root, bundle_root=self.bundle_root)
        self.register_initial()

    def _binding(self, start):
        value = read_json(self._binding_path(start))
        if read_ref(_file_ref(value['request'])) != start:
            raise BindingError('RESIDENT_CURRENT_REQUEST_BINDING_CHANGED')
        return value

    def execute_round(self, start, attempt_root):
        from adapter import run_bound_round
        from .tail import close_round_tail
        root = Path(attempt_root).absolute()
        current = self._binding(start)
        from .progress import update
        update(self.owner_root,stage='ROLLOUT',round_id=start['round_id'],attempt_root=str(root),
               rollout_manifest_ref=None)
        result_path = root/'DRIVER_ROUND_RESULT.json'
        if result_path.is_file():
            result = read_json(result_path)
            if result.get('attempt_root') != str(root):
                raise BindingError('RESIDENT_RECOVERY_ATTEMPT_ROOT')
            self.validate_result(start, result)
            return result
        from .source_recovery import registration
        from .rollout_recovery import invalid_result
        recovery = registration(self.bundle_root)
        if recovery is not None and start == self.initial:
            result = invalid_result(manifest_ref=recovery['refs']['manifest'], start=start,
                attempt_root=root, current_parent_context=current['current_parent_context'],
                settings=self.deployment['rollout_settings'])
            self.validate_result(start, result)
            immutable_json(result_path, result)
            return result
        spec = build_registered_spec(captured_root=self.layout.received,
            formal_root=self.formal_root, implementation_worktree=self.repo,
            current_request=current['request'], current_binding=current['execution_binding'],
            input_refs=current['input_refs'])
        rolled = materialize(spec, root / 'rollout')
        update(self.owner_root,rollout_manifest_ref=_native_ref(file_ref(rolled['manifest_path'])))
        route = await_rollout(rolled['manifest_path'], settings=self.deployment['rollout_settings'])
        if route['status'] == 'SCIENTIFIC_ROLLOUT_INVALID':
            result = invalid_result(manifest_ref={'path':rolled['manifest_path'],
                'sha256':file_ref(rolled['manifest_path'])['file_sha256']}, start=start,
                attempt_root=root,current_parent_context=current['current_parent_context'],
                settings=self.deployment['rollout_settings'])
            self.validate_result(start, result)
            immutable_json(result_path, result)
            return result
        input_ref = current_rollout_inputs(rolled, start, root, prior_input_refs=current['input_refs'])
        index = read_ref(_file_ref(current['current_index'])) if current['current_index'] else None
        source = build_source_binding(rolled, layout=self.layout,
            output_root=root / 'analyzer_sources', current_index=index)
        binding = build_from_rollout_result(rolled, source_binding=source, output_root=root / 'analyzer',
                                           current_index=index)
        binding['campaign_startup_authority'] = file_ref(self.formal_root / 'CAMPAIGN_STARTUP_AUTHORITY_V1.json')
        binding['source_registration'] = source['source_registration']
        binding['training_source_registration'] = self.deployment['training_source_registration']
        immutable_json(root / 'CURRENT_ANALYZER_BINDING.json', binding)
        update(self.owner_root,stage='ANALYZER_PLANNER_CAUSAL_VERIFICATION')
        run_bound_round(binding, execute=True)
        evidence = current_h44_evidence(root / 'analyzer')
        from continuity_binding.api import validate_current_post
        post, _ = validate_current_post(start=start, evidence_refs=evidence)
        training_result_ref = None
        next_policy_input_refs = None
        parent_context = current['current_parent_context']
        if post['researcher_training_recommendation'] == 'TRAIN':
            from .training_job import execute_current_training_job
            from .offoff_job import execute_current_offoff_job
            update(self.owner_root,stage='TRAINING')
            trained = execute_current_training_job(start=start, analyzer_binding=binding,
                h44_run_root=root / 'analyzer/h44/run', output_root=root / 'training',
                current_parent_context=current['current_parent_context'],
                round_index=current['round_index'], deployment=self.deployment)
            update(self.owner_root,stage='TRAIN_SELECT_OFFOFF')
            evaluated = execute_current_offoff_job(start=start,
                current_inputs_ref=input_ref, trained=trained, output_root=root / 'offoff',
                deployment=self.deployment)
            training_result_ref = evaluated['terminal_ref']
            if read_ref(_file_ref(training_result_ref))['outcome'] == 'PROMOTED':
                next_policy_input_refs = evaluated['next_policy_input_refs']
                parent_context = evaluated['current_parent_context']
        update(self.owner_root,stage='MEMORY_AND_ROUND_CLOSURE')
        result = close_round_tail(start=start, analyzer_binding=binding,
            analyzer_output_root=root / 'analyzer', attempt_root=root,
            stage_evidence_refs=evidence, current_execution_binding_ref=current['execution_binding'],
            current_inputs_ref=input_ref, current_memory_state_ref=current['memory_state'],
            training_result_ref=training_result_ref, next_policy_input_refs=next_policy_input_refs)
        result.update(attempt_root=str(root), current_parent_context=parent_context)
        self.validate_result(start, result)
        immutable_json(result_path, result)
        return result

    def recover_round(self, start, attempt_root):
        # Component owners can adopt exact native receipts. Their own persistent
        # submission/logical-call intents reject ambiguous resends.
        return self.execute_round(start, attempt_root)

    def export_result(self,start,result,attempt_root):
        from .paper_export import export_attempt
        return export_attempt(attempt_root=attempt_root,start=start,result=result,deployment=self.deployment)

    def validate_result(self, start, result):
        if result['outcome'] == 'PROTOCOL_INFRA_INVALID':
            from .rollout_recovery import validate_invalid_result
            validate_invalid_result(start,result)
            if result['current_parent_context'] != self._binding(start)['current_parent_context']:
                raise BindingError('INVALID_ROLLOUT_PARENT_CHANGED')
            return
        from .tail import validate_closed_round_tail
        replay_closed_h44(result)
        validate_closed_round_tail(start=start, result=result)
        if result['outcome'] in {'PROMOTED','ROLLED_BACK'}:
            from offoff_binding.execute import validate_completed_offoff_terminal
            from .candidate_runtime import publish_candidate
            validate_completed_offoff_terminal(result['terminal_ref'])
            terminal = read_ref(_file_ref(result['terminal_ref']))
            execution = read_ref(_file_ref(terminal['binding_ref']))
            candidate_ref = execution['input_refs']['candidate_ref']
            candidate = read_ref(_file_ref(candidate_ref))
            trained_ref = candidate['training_result_ref']
            trained = {**read_ref(_file_ref(trained_ref)), 'result_ref':trained_ref}
            # The publisher replays the original accepted training output reader
            # and actual adapter bytes. Equal publication performs no training.
            published = publish_candidate(start=start,
                current_inputs_ref=result['stage_evidence_refs']['current_inputs'],trained=trained,
                output_root=Path(candidate_ref['path']).parent,
                source_registration=self.deployment['candidate_source_registration'])
            if published['candidate_ref'] != candidate_ref:
                raise BindingError('RESIDENT_RECOVERED_ACCEPTED_CANDIDATE_IDENTITY')
        current = self._binding(start)
        if result['outcome'] != 'PROMOTED':
            expected_context = current['current_parent_context']
        else:
            terminal = read_ref(_file_ref(result['terminal_ref']))
            execution = read_ref(_file_ref(terminal['binding_ref']))
            candidate = read_ref(_file_ref(execution['input_refs']['candidate_ref']))
            expected_context = candidate['current_parent_context']
        if result.get('current_parent_context') != expected_context:
            raise BindingError('RESIDENT_RESULT_CURRENT_PARENT_CONTEXT')

    def build_next(self, start, result, governance):
        if result['outcome'] == 'PROTOCOL_INFRA_INVALID':
            from .rollout_recovery import build_retry
            return build_retry(self,start,result)
        from .tail import build_next_round_tail
        # Result binds its exact operational root; no history/path discovery.
        root = Path(result['attempt_root'])
        self.validate_result(start, result)
        nxt = build_next_round_tail(start=start, result=result, governance=governance,
                                   attempt_root=root)
        next_request = nxt['next_request']
        if read_ref(_file_ref(nxt['request'])) != next_request:
            raise BindingError('RESIDENT_NEXT_REQUEST_REF_IDENTITY')
        next_inputs = read_ref(_file_ref(nxt['input_refs']))
        if next_inputs.get('request_sha256') != next_request['request_sha256']:
            raise BindingError('RESIDENT_NEXT_INPUT_REQUEST_IDENTITY')
        for role, field in (('runtime','policy_runtime_binding_sha256'),('profile','execution_profile_sha256'),
                ('memory','round_memory_runtime_authority_sha256'),('train_manifest','train_update_manifest_sha256')):
            read_ref(_file_ref(next_inputs[role]), as_bytes=True)
            if _native_ref(next_inputs[role])['sha256'] != next_request[field]:
                raise BindingError('RESIDENT_NEXT_INPUT_IDENTITY:' + role)
        read_ref(_file_ref(nxt['memory_state']))
        read_ref(_file_ref(nxt['memory_source_partitions']))
        execution = read_ref(_file_ref(nxt['execution_binding']))
        if execution.get('request_sha256') != next_request['request_sha256']:
            raise BindingError('RESIDENT_NEXT_EXECUTION_REQUEST_IDENTITY')
        index = {'schema_id': 'CURRENT_FORMAL_RESIDENT_INPUT_INDEX_V1',
                  'round_id': next_request['round_id'], 'request_sha256': next_request['request_sha256'],
                  'refs': {'memory_source_partitions': _file_ref(nxt['memory_source_partitions'])}}
        if result['outcome'] in {'PROMOTED', 'ROLLED_BACK'}:
            # validate_result above already replayed the exact native evaluation.
            # Transport only a closed prior-round aggregate; never the restricted
            # task/episode/protocol references retained in the native summary.
            terminal = read_ref(_file_ref(result['terminal_ref']))
            summary_ref = _native_ref(terminal['summary_ref'])
            context = project_previous_select_context(
                summary=read_ref(_file_ref(summary_ref)), summary_sha256=summary_ref['sha256'],
                closed_result=result, next_request=next_request)
            context_path = root / 'tail/next_round/PREVIOUS_TRAIN_SELECT_RESEARCH_CONTEXT.json'
            immutable_json(context_path, context)
            index['refs']['previous_select_context'] = file_ref(context_path)
        index_path = root / 'tail/next_round/CURRENT_INPUT_INDEX.json'
        immutable_json(index_path, index)
        value = {'schema_id': 'CURRENT_FORMAL_RESIDENT_REQUEST_BINDING_V1',
                 'request': nxt['request'], 'execution_binding': nxt['execution_binding'],
                 'input_refs': nxt['input_refs'], 'memory_state': nxt['memory_state'],
                 'current_index': _native_ref(file_ref(index_path)),
                 'current_parent_context': result['current_parent_context'],
                 'round_index': governance.valid_rounds_consumed + 1}
        request = read_ref(_file_ref(value['request']))
        immutable_json(self._binding_path(request), value)
        return request
