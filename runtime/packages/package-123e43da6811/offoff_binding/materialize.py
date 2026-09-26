"""Materialize native SELECT identities from current, exact machine references."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

from continuity_binding.api import (ContinuityError, canonical, native_request,
    read_bytes_ref, read_ref, regular_path, write_once)


def need(ok, reason):
    if not ok:
        raise ContinuityError(reason)


def _artifact(policy):
    """Verify the real finite artifact member map, including adapter weights."""
    root = regular_path(policy['artifact_root'])
    manifest = read_ref(policy['artifact_manifest'])
    files = manifest.get('files')
    need(isinstance(files, dict) and files, 'POLICY_ARTIFACT_FILE_MAP_REQUIRED')
    if policy['kind'] == 'LORA_ADAPTER':
        need({'adapter_config.json', 'adapter_model.safetensors'} <= set(files), 'LORA_WEIGHT_MEMBERS_REQUIRED')
        need(manifest.get('adapter_bundle_sha256') == policy['artifact_sha256'], 'LORA_BUNDLE_IDENTITY')
    for name, spec in files.items():
        member = Path(name)
        need(not member.is_absolute() and '..' not in member.parts and '\\' not in name,
             'ARTIFACT_MEMBER_ESCAPE')
        raw = read_bytes_ref({'path': str(root / member), 'sha256': spec['sha256']})
        need(len(raw) == spec['size_bytes'], 'POLICY_ARTIFACT_MEMBER_SIZE')
    if policy['kind'] == 'LORA_ADAPTER':
        config = read_ref({'path': str(root / 'adapter_config.json'),
                           'sha256': files['adapter_config.json']['sha256']})
        need(config.get('r') == policy['adapter_rank'], 'LORA_RANK_IDENTITY')
    else:
        need(policy['kind'] == 'BASE_MODEL', 'UNSUPPORTED_NATIVE_SELECT_POLICY_KIND')
        if 'runtime_ref' in policy:
            runtime = read_ref(policy['runtime_ref'])
            need(runtime.get('schema_id') == 'CLEAN_PI0_LIVE_RUNTIME_BINDING_V2' and
                 runtime['policy_runtime_manifest_sha256'] == policy['artifact_sha256'] and
                 runtime['base_model_local_path'] == policy['artifact_root'] and
                 runtime['tokenizer_revision'] == policy['base_model_revision'], 'CURRENT_CLEAN_RUNTIME_ARTIFACT_IDENTITY')
        else:
            # Supports native manifest-bound base fixtures and registered prior base identities.
            need(policy['artifact_sha256'] == policy['artifact_manifest']['sha256'], 'BASE_ARTIFACT_IDENTITY')
    return manifest


def prepare(*, native, request_ref, parent_ref, candidate_ref, protocol_ref,
            infrastructure_ref):
    """Validate everything before immutable materialization or scientific calls."""
    native.revalidate()
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
    from pchsi.evaluation.distillation_access import TaskAccessManifestV1, DistillationAccessClass
    from pchsi.evaluation.condition_run_schedule import build_condition_run_schedule, ConditionRunPurpose
    from pchsi.evaluation.policy_condition import PolicyConditionManifestV1, CheckpointKind, TrainingMethod
    from pchsi.evaluation.select_policy_runtime import (SelectServerRuntimeManifestV1,
        SelectStaticLoRARegistrationV1, SelectPolicyRuntimeManifestV1, PI0_CONDITION_ID,
        PI0_SERVED_MODEL_NAME)
    from pchsi.evaluation.select_execution_identity import (bind_select_condition_cell,
        select_i1_request_contract_sha256, build_select_i1_execution_profile)
    from pchsi.evaluation.distillation_governance import canonical_model_sha256
    from pchsi.evaluation.budget import BudgetLimits
    from pchsi.evaluation.run_schedule import REPLICATE_SEEDS

    start = read_ref(request_ref); request = native_request(start)
    parent, candidate = read_ref(parent_ref), read_ref(candidate_ref)
    protocol, infra = read_ref(protocol_ref), read_ref(infrastructure_ref)
    need(parent['policy_id'] == request.parent_policy_id and
         parent['artifact_sha256'] == request.parent_policy_artifact_sha256, 'CURRENT_PARENT_POLICY_IDENTITY')
    need(candidate['parent_policy_id'] == parent['policy_id'] and
         candidate['parent_policy_artifact_sha256'] == parent['artifact_sha256'] and
         candidate['round_id'] == request.round_id and
         candidate['execution_attempt_id'] == request.execution_attempt_id and
         candidate['request_sha256'] == request.request_sha256, 'CURRENT_CANDIDATE_LINEAGE')
    need(candidate['policy_id'] != parent['policy_id'] and
         candidate['artifact_sha256'] != parent['artifact_sha256'], 'CANDIDATE_MUST_BIND_CHANGED_WEIGHTS')
    need(candidate['kind'] == 'LORA_ADAPTER', 'NATIVE_CANDIDATE_LORA_REQUIRED')
    for policy in (parent, candidate):
        _artifact(policy)
    if parent['kind'] == 'BASE_MODEL' and 'runtime_ref' in parent:
        need(parent['runtime_ref']['sha256'] == request.policy_runtime_binding_sha256,
             'CURRENT_BASE_RUNTIME_FILE_IDENTITY')
    need(protocol['access_class'] == 'TRAIN_SELECT' and
         protocol['memory_state'] == protocol['harness_state'] == 'OFF' and
         protocol['protocol_frozen'] is True and
         protocol['benchmark_feedback_authorized'] is False and
         protocol['primary_statistical_unit'] == 'unique_task', 'FROZEN_OFFOFF_TRAIN_SELECT_PROTOCOL_REQUIRED')
    # Source is registered before execution; this adapter never chooses a rule.
    read_ref(protocol['promotion_rule_ref'])
    task_raw = read_bytes_ref(protocol['task_access_ref'])
    access = TaskAccessManifestV1.from_json(task_raw)
    need(all(row.dataset_split == 'train' and row.access_class is DistillationAccessClass.SELECT_SUMMARY_ONLY
             for row in access.records), 'ONLY_CURRENT_TRAIN_SELECT_TASKS_ALLOWED')
    need([r.task_id for r in access.records] == protocol['task_ids'], 'FROZEN_SELECT_TASK_ORDER')
    need(all(seed in REPLICATE_SEEDS for seed in protocol['replicate_seeds']), 'NATIVE_EVALUATOR_REPLICATE_SEEDS')
    i1_sha = select_i1_request_contract_sha256()
    need(protocol['policy_request_schema_sha256'] == i1_sha, 'NATIVE_I1_REQUEST_IDENTITY')
    read_bytes_ref(infra['environment_runtime_ref'])
    read_bytes_ref(infra['gamefile_identity_ref'])
    base = read_ref(infra['base_policy_ref']); _artifact(base)
    need(base['kind'] == 'BASE_MODEL', 'BASE_MODEL_ARTIFACT_REQUIRED')
    native.verify_clean_base(base)
    need(set(protocol['episode_budget']) == {'max_policy_attempts', 'max_environment_steps',
         'max_consecutive_nonexecuted_attempts'}, 'EXPLICIT_FROZEN_EPISODE_BUDGET_REQUIRED')
    BudgetLimits(**protocol['episode_budget'])
    template = dict(infra['server_runtime_parameters'])
    registrations = []
    for policy in (parent, candidate):
        if policy['kind'] == 'LORA_ADAPTER':
            registrations.append(SelectStaticLoRARegistrationV1(
                logical_condition_id=policy['logical_condition_id'],
                checkpoint_instance_id=policy['checkpoint_instance_id'],
                training_seed=policy['training_seed'], served_model_name=policy['checkpoint_instance_id'],
                adapter_path=policy['artifact_root'], adapter_bundle_sha256=policy['artifact_sha256'],
                adapter_rank=policy['adapter_rank']))
        else:
            need(policy['artifact_sha256'] == base['artifact_sha256'], 'CURRENT_BASE_PARENT_WEIGHTS')
    need('static_lora_registry' not in template, 'SERVER_REGISTRY_IS_CURRENT_POLICY_DERIVED')
    template['static_lora_registry'] = tuple(registrations)
    server = SelectServerRuntimeManifestV1(**template)
    for policy in (base, parent, candidate):
        need(policy['base_model_repository'] == server.base_model_repository and
             policy['base_model_revision'] == server.base_model_revision, 'CURRENT_MODEL_BASE_IDENTITY')
    server_sha = sha256_bytes(canonical_json_bytes(server.to_dict()))
    bundles = {}
    for label, policy in (('parent', parent), ('candidate', candidate)):
        base_kind = policy['kind'] == 'BASE_MODEL'
        condition_id = PI0_CONDITION_ID if base_kind else policy['checkpoint_instance_id']
        logical_id = PI0_CONDITION_ID if base_kind else policy['logical_condition_id']
        served_name = PI0_SERVED_MODEL_NAME if base_kind else policy['checkpoint_instance_id']
        runtime = SelectPolicyRuntimeManifestV1(
            schema_id=SelectPolicyRuntimeManifestV1.SCHEMA_ID, schema_version=1,
            manifest_id=request.round_id + '-' + label, server_runtime_manifest_sha256=server_sha,
            policy_condition_id=condition_id, logical_condition_id=logical_id,
            checkpoint_instance_id=condition_id, training_seed=None if base_kind else policy['training_seed'],
            served_model_name=served_name, adapter_path=None if base_kind else policy['artifact_root'],
            adapter_bundle_sha256=None if base_kind else policy['artifact_sha256'],
            adapter_rank=None if base_kind else policy['adapter_rank'])
        runtime_sha = sha256_bytes(canonical_json_bytes(runtime.to_dict()))
        if not base_kind:
            read_bytes_ref(policy['training_config_ref'])
        condition = PolicyConditionManifestV1(
            schema_id=PolicyConditionManifestV1.SCHEMA_ID, schema_version=1,
            policy_condition_id=condition_id, base_model_repository=server.base_model_repository,
            base_model_revision=server.base_model_revision,
            checkpoint_kind=CheckpointKind.BASE_MODEL if base_kind else CheckpointKind.LORA_ADAPTER,
            checkpoint_path=None if base_kind else policy['artifact_root'],
            checkpoint_sha256=None if base_kind else policy['artifact_sha256'],
            training_method=TrainingMethod.NONE if base_kind else TrainingMethod.SFT,
            training_run_id=None if base_kind else policy['training_run_id'],
            training_config_sha256=None if base_kind else policy['training_config_ref']['sha256'],
            policy_runtime_manifest_sha256=runtime_sha,
            tokenizer_identity_manifest_sha256=server.tokenizer_identity_manifest_sha256,
            chat_template_sha256=server.chat_template_sha256, served_model_name=served_name,
            policy_version='pi0' if base_kind else logical_id, memory_version='MEMORY_M0_V1',
            raw_protocol_sha256=protocol['raw_protocol_sha256'],
            runtime_core_commit=protocol['runtime_core_commit'], evaluator_commit=protocol['evaluator_commit'])
        condition_sha = canonical_model_sha256(condition)
        schedule = build_condition_run_schedule(task_access_manifest=access,
            task_access_manifest_sha256=protocol['task_access_ref']['sha256'], policy_condition=condition,
            policy_condition_manifest_sha256=condition_sha, run_purpose=ConditionRunPurpose.P4_HARNESS_OFF_SELECT,
            target_access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY,
            replicate_seeds=protocol['replicate_seeds'],
            output_namespace='offoff-' + request.request_sha256[:24] + '-' + label)
        schedule_sha = canonical_model_sha256(schedule)
        for cell in schedule.cells:
            bound = bind_select_condition_cell(schedule_cell=cell, task_access=access.records[cell.manifest_index],
                policy_condition=condition, policy_runtime=runtime,
                task_access_manifest_sha256=protocol['task_access_ref']['sha256'],
                policy_condition_manifest_sha256=condition_sha, condition_run_schedule_sha256=schedule_sha,
                select_policy_runtime_manifest_sha256=runtime_sha)
            build_select_i1_execution_profile(bound.execution_identity, request_contract_sha256=i1_sha)
        bundles[label] = (condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha)
    return dict(start=start, parent=parent, candidate=candidate, protocol=protocol, infra=infra,
                base=base, server=server, access=access, bundles=bundles)


def derive_clean_parent_policy(*, native, request_ref, runtime_ref, profile_ref, sink):
    """Use the already implemented current clean-parent provenance adapter."""
    from training_binding.clean_base import derive_clean_parent_metadata, PROFILE_REL
    need(Path(profile_ref['path']) == native.root / PROFILE_REL, 'REGISTERED_CLEAN_ARCHITECTURE_PROFILE_PATH')
    read_bytes_ref(profile_ref)
    start = read_ref(request_ref); native_request(start)
    metadata = derive_clean_parent_metadata(source_request=start, runtime_bytes=read_bytes_ref(runtime_ref),
        native_repo_root=native.root, profile_file_sha256=profile_ref['sha256'])
    parent = metadata['parent']
    policy = dict(schema_id='CURRENT_OFFOFF_POLICY_BINDING_V1', policy_id=start['parent_policy_id'], kind='BASE_MODEL',
        artifact_sha256=start['parent_policy_artifact_sha256'], artifact_root=parent['base_model_local_path'],
        artifact_manifest={'path': parent['base_model_artifact_manifest_path'],
                           'sha256': parent['base_model_artifact_manifest_sha256']},
        runtime_ref=runtime_ref, base_model_repository=parent['base_model_repository'],
        base_model_revision=parent['base_model_revision'], architecture_reference=profile_ref)
    _artifact(policy); native.verify_clean_base(policy)
    return write_once(Path(sink) / 'CURRENT_CLEAN_PARENT_OFFOFF_POLICY.json', policy)


def materialize(*, native, request_ref, parent_ref, candidate_ref, protocol_ref, infrastructure_ref, sink):
    refs = dict(request_ref=request_ref, parent_ref=parent_ref, candidate_ref=candidate_ref,
                protocol_ref=protocol_ref, infrastructure_ref=infrastructure_ref)
    context = prepare(native=native, **refs)
    sink = regular_path(Path(sink).absolute())
    documents = {'SERVER_RUNTIME.json': context['server'].to_dict()}
    for label, (condition, runtime, schedule, *_) in context['bundles'].items():
        for suffix, value in (('CONDITION', condition), ('RUNTIME', runtime), ('SCHEDULE', schedule)):
            documents[label.upper() + '_' + suffix + '.json'] = value.to_dict()
    # Ensure restart conflicts are detected before any output publication.
    for name, value in documents.items():
        path = sink / name
        if path.exists():
            need(regular_path(path).read_bytes() == canonical(value) + b'\n', 'OFFOFF_MATERIALIZATION_CONFLICT')
    output_refs = {name: write_once(sink / name, value) for name, value in documents.items()}
    binding = dict(schema_id='CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1', schema_version=1,
        round_id=context['start']['round_id'], request_sha256=context['start']['request_sha256'],
        execution_attempt_id=context['start']['execution_attempt_id'],
        input_refs=refs, output_refs=output_refs, source_refs=list(native.sources.values()),
        native_repo_root=str(native.root),
        paired_cell_count=len(context['bundles']['parent'][2].cells),
        execution_root=str(sink / 'execution'), memory_state='OFF', harness_state='OFF',
        scientific_execution_started=False)
    return write_once(sink / 'CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING.json', binding)


def server_command(context, *, host, port):
    """Mechanical vLLM arguments from validated native static registrations."""
    need(host in ('127.0.0.1', 'localhost') and type(port) is int and 0 < port < 65536,
         'LOOPBACK_SERVER_REQUIRED')
    server = context['server']
    from pchsi.evaluation.select_policy_runtime import PI0_SERVED_MODEL_NAME
    argv = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server', '--model',
            context['base']['artifact_root'], '--served-model-name', PI0_SERVED_MODEL_NAME,
            '--host', host, '--port', str(port)]
    for option, field in (('dtype', 'dtype'), ('tensor-parallel-size', 'tensor_parallel_size'),
        ('generation-config', 'generation_config_mode'), ('chat-template-content-format', 'chat_template_content_format'),
        ('max-lora-rank', 'max_lora_rank'), ('max-loras', 'max_loras'), ('max-cpu-loras', 'max_cpu_loras'),
        ('lora-dtype', 'lora_dtype')):
        argv.extend(['--' + option, str(getattr(server, field))])
    argv += ['--enable-lora', '--lora-modules'] + [r.served_model_name + '=' + r.adapter_path
                                                 for r in server.static_lora_registry]
    return argv
