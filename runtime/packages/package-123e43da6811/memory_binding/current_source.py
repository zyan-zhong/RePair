"""Distinct current-round source authority; never rewrites historical V1 labels."""
from dataclasses import asdict, dataclass, fields
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf8')


def read_ref(ref):
    path = Path(ref['path'])
    if not path.is_absolute() or '..' in path.parts or not path.is_file():
        raise ValueError('EXACT_SOURCE_REF_REQUIRED')
    if any(node.is_symlink() or (hasattr(node,'is_junction') and node.is_junction()) for node in (path,*path.parents)):
        raise ValueError('EXACT_SOURCE_ALIAS_FORBIDDEN')
    raw = path.read_bytes()
    if sha(raw) != ref['file_sha256']:
        raise ValueError('SOURCE_REF_SHA_MISMATCH')
    return raw


def _sha(value):
    if not isinstance(value, str) or len(value) != 64 or any(x not in '0123456789abcdef' for x in value):
        raise ValueError('INVALID_SHA256')


@dataclass(frozen=True)
class SequenceSourceTaskAccessBindingV2:
    schema_id: str
    schema_version: int
    task_manifest_sha256: str
    request_sha256: str
    request_file_sha256: str
    round_id: str
    round_execution_attempt_id: str
    parent_policy_id: str
    parent_policy_artifact_sha256: str
    source_attempt_id: str
    source_task_id: str
    source_bundle_sha256: str
    task_access_record_line_index: int
    task_access_record_sha256: str
    task_gamefile_group_id: str
    dataset_relative_gamefile: str
    gamefile_sha256: str
    task_type: str
    split: str
    access_class: str

    def __post_init__(self):
        from pchsi.memory.task_access import canonical_task_gamefile_group_id
        if self.schema_id != 'SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V2' or self.schema_version != 2:
            raise ValueError('CURRENT_SOURCE_SCHEMA')
        if self.split != 'train' or self.access_class != 'TRAIN_UPDATE':
            raise ValueError('CURRENT_SOURCE_REQUIRES_ACTUAL_TRAIN_UPDATE')
        for key, value in asdict(self).items():
            if key.endswith('sha256') or key == 'task_gamefile_group_id':
                _sha(value)
            elif isinstance(value, str) and (not value or any(x in value for x in ('\x00','\r','\n'))):
                raise ValueError('INVALID_SOURCE_TEXT:' + key)
        if type(self.task_access_record_line_index) is not int or self.task_access_record_line_index < 0:
            raise ValueError('CURRENT_SOURCE_ROW_INDEX')
        path = PurePosixPath(self.dataset_relative_gamefile)
        if path.is_absolute() or '..' in path.parts or '\\' in str(path):
            raise ValueError('CURRENT_SOURCE_GAMEFILE_PATH')
        if canonical_task_gamefile_group_id(relative_gamefile=str(path), gamefile_sha256=self.gamefile_sha256) != self.task_gamefile_group_id:
            raise ValueError('CURRENT_SOURCE_GAMEFILE_GROUP')

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {field.name for field in fields(cls)}:
            raise ValueError('CURRENT_SOURCE_KEYS')
        return cls(**value)


def build_current_source_access(*, request_ref, train_manifest_ref, source):
    """Select exactly the source episode's row in this request's frozen manifest."""
    from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
    from pchsi.memory.task_access import canonical_task_gamefile_group_id
    request_raw = read_ref(request_ref)
    request = json.loads(request_raw)
    native = RoundRolloutCollectionRequestV1(**{f.name: request[f.name]
        for f in fields(RoundRolloutCollectionRequestV1) if f.name in request})
    if native.to_dict() != request:
        raise ValueError('CURRENT_REQUEST_NATIVE_IDENTITY')
    manifest_raw = read_ref(train_manifest_ref)
    if sha(manifest_raw) != native.train_update_manifest_sha256:
        raise ValueError('CURRENT_REQUEST_TRAIN_MANIFEST')
    episode = source.episode_artifact
    rows = [(index, raw, json.loads(raw)) for index, raw in enumerate(manifest_raw.splitlines(keepends=True))]
    matches = [(index, raw, row) for index, raw, row in rows if row.get('id') == episode.task_id]
    if len(matches) != 1:
        raise ValueError('CURRENT_SOURCE_TASK_MEMBERSHIP')
    index, raw, row = matches[0]
    if (row.get('schema_id') != 'ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1' or
            row.get('split') != 'train' or row.get('train_pool') != 'TRAIN_UPDATE'):
        raise ValueError('CURRENT_SOURCE_REQUIRES_ACTUAL_TRAIN_UPDATE')
    if row['gamefile_sha256'] != episode.gamefile_sha256 or row['task_type'] != episode.task_type:
        raise ValueError('CURRENT_SOURCE_EPISODE_TASK_IDENTITY')
    if any(trace.provenance.policy_version != native.parent_policy_id for trace in source.traces):
        raise ValueError('CURRENT_SOURCE_PARENT_POLICY_IDENTITY')
    # The rollout source manifest/cell is checked by the caller against the accepted
    # current handoff. This binds the exact sealed episode into its current request.
    access = SequenceSourceTaskAccessBindingV2(
        schema_id='SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V2', schema_version=2,
        task_manifest_sha256=sha(manifest_raw), request_sha256=native.request_sha256,
        request_file_sha256=sha(request_raw), round_id=native.round_id,
        round_execution_attempt_id=native.execution_attempt_id,
        parent_policy_id=native.parent_policy_id,
        parent_policy_artifact_sha256=native.parent_policy_artifact_sha256,
        source_attempt_id=episode.execution_attempt_id, source_task_id=episode.task_id,
        source_bundle_sha256=source.attempt_bundle.attempt_bundle_sha256,
        task_access_record_line_index=index, task_access_record_sha256=sha(raw),
        task_gamefile_group_id=canonical_task_gamefile_group_id(
            relative_gamefile=row['gamefile_relpath'],gamefile_sha256=row['gamefile_sha256']),
        dataset_relative_gamefile=row['gamefile_relpath'],gamefile_sha256=row['gamefile_sha256'],
        task_type=row['task_type'],split=row['split'],access_class=row['train_pool'])
    return access, raw


def validate_current_source_record(source, binding):
    if sha(source.task_access_record_bytes) != binding.task_access_record_sha256:
        raise ValueError('CURRENT_SOURCE_ROW_SHA')
    if source.task_access_record_line_index != binding.task_access_record_line_index:
        raise ValueError('CURRENT_SOURCE_ROW_INDEX')
    row = json.loads(source.task_access_record_bytes)
    for key, expected in {'id':binding.source_task_id,'gamefile_relpath':binding.dataset_relative_gamefile,
            'gamefile_sha256':binding.gamefile_sha256,'task_type':binding.task_type,
            'split':'train','train_pool':'TRAIN_UPDATE'}.items():
        if row.get(key) != expected:
            raise ValueError('CURRENT_SOURCE_ROW_FIELD:' + key)
    if (source.episode_artifact.execution_attempt_id != binding.source_attempt_id or
            source.attempt_bundle.attempt_bundle_sha256 != binding.source_bundle_sha256):
        raise ValueError('CURRENT_SOURCE_ATTEMPT_IDENTITY')
