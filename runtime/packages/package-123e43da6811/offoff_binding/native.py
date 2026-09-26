"""Load exact registered sources; no historical worktree or directory discovery."""
from __future__ import annotations
from dataclasses import dataclass
import importlib
import types as pytypes
from pathlib import Path
import sys

from continuity_binding.api import ContinuityError, read_bytes_ref

STAGE0 = 'scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9'
STAGE4E = 'scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX'
BASE_VERIFIER = 'scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/clean_adapter.py'
STAGE4D = 'scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING'
ARRAY_CONFIG = STAGE4E + '/config.json'
READINESS = 'scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX'
REQUIRED = (
    'src/pchsi/evaluation/select_policy_runtime.py',
    'src/pchsi/evaluation/select_execution_identity.py',
    'src/pchsi/evaluation/select_result_audit.py',
    'src/pchsi/evaluation/policy_condition.py',
    'src/pchsi/evaluation/condition_run_schedule.py',
    'src/pchsi/evaluation/episode_evaluator.py',
    'src/pchsi/round_control/promotion.py',
    'scripts/memory/materialize_sequence_failure_experience_v1.py',
    BASE_VERIFIER,
    *(STAGE0 + '/stage0/' + n for n in ('__init__.py', 'constants.py', 'common.py',
       'receipts.py', 'attempt_recovery.py', 'twin_contract.py', 'closeout.py',
       'live_runner.py', 'result_audit.py', 'runtime_server.py')),
    STAGE4E + '/stage4e/__init__.py', STAGE4E + '/stage4e/audit.py',
    ARRAY_CONFIG, *(STAGE4D + '/stage4d_full/' + name for name in ('__init__.py','parallel.py','contract.py')),
    *(READINESS + '/stage4d_pkg/' + name for name in ('__init__.py','prepare.py','common.py')),
    *(f'src/pchsi/evaluation/{name}.py' for name in ('raw_policy_prompt','runtime_core','raw_policy_parser')),
)


@dataclass
class Native:
    root: Path
    sources: dict

    @classmethod
    def load(cls, root, source_refs):
        root = Path(root).absolute()
        sources = {str(Path(ref['path'])): ref for ref in source_refs}
        if len(sources) != len(source_refs):
            raise ContinuityError('DUPLICATE_NATIVE_SOURCE_REF')
        for name in REQUIRED:
            if str(root / name) not in sources:
                raise ContinuityError('REGISTERED_NATIVE_SOURCE_REQUIRED:' + name)
        result = cls(root, sources)
        result.revalidate()
        sys.path.insert(0, str(root / 'src'))
        module = importlib.import_module('pchsi.evaluation.select_policy_runtime')
        if Path(module.__file__).resolve() != (root / REQUIRED[0]).resolve():
            raise ContinuityError('NATIVE_IMPORT_ROOT_CONFLICT')
        return result

    def revalidate(self):
        for ref in self.sources.values():
            read_bytes_ref(ref)

    def parallel(self):
        """Original deterministic ordinal partition; historical launchers stay unused."""
        self.revalidate()
        sys.path.insert(0, str(self.root / STAGE4D))
        module = importlib.import_module('stage4d_full.parallel')
        if Path(module.__file__).resolve() != (self.root / STAGE4D / 'stage4d_full/parallel.py').resolve():
            raise ContinuityError('NATIVE_PARALLEL_IMPORT_ROOT_CONFLICT')
        return module

    def readiness(self):
        self.revalidate()
        sys.path.insert(0, str(self.root / READINESS))
        module = importlib.import_module('stage4d_pkg.prepare')
        if Path(module.__file__).resolve() != (self.root / READINESS / 'stage4d_pkg/prepare.py').resolve():
            raise ContinuityError('NATIVE_SELECT_GRID_IMPORT_ROOT_CONFLICT')
        return module

    def verify_clean_base(self, policy):
        path = self.root / BASE_VERIFIER
        read_bytes_ref(self.sources[str(path)])
        spec = importlib.util.spec_from_file_location('_offoff_native_clean_base_verifier', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.verify_clean_base({'manifest_path': policy['artifact_manifest']['path'],
            'manifest_sha256': policy['artifact_manifest']['sha256'], 'snapshot_path': policy['artifact_root'],
            'repository_id': policy['base_model_repository'], 'revision': policy['base_model_revision']})

    def runners(self):
        """Linux-only invocation dependencies; no server or environment starts here."""
        self.revalidate()
        for package, parent in (('stage0', STAGE0), ('stage4e', STAGE4E)):
            sys.path.insert(0, str(self.root / parent))
            module = importlib.import_module(package)
            if Path(module.__file__).resolve() != (self.root / parent / package / '__init__.py').resolve():
                raise ContinuityError('NATIVE_RUNNER_IMPORT_ROOT_CONFLICT:' + package)
        # The same two operational-label substitutions used by registered Stage4D.
        # The episode runner, recovery, evaluator and publication bodies are retained.
        path = self.root / STAGE0 / 'stage0/live_runner.py'
        source = path.read_text(encoding='utf8')
        substitutions = {
            '"human-stage0-"': 'CURRENT_RUN_NAMESPACE + "-"',
            'run_id="human-pilot-stage0-" + label.lower()': 'run_id=CURRENT_RUN_NAMESPACE + "-" + label.lower()',
        }
        for old, new in substitutions.items():
            if source.count(old) != 1:
                raise ContinuityError('NATIVE_OPERATIONAL_LABEL_ANCHOR_DRIFT')
            source = source.replace(old, new)
        name = 'stage0.current_offoff_live_runner'
        live = pytypes.ModuleType(name)
        live.__file__ = str(path)
        live.__package__ = 'stage0'
        sys.modules[name] = live
        exec(compile(source, str(path), 'exec'), live.__dict__)
        audit = importlib.import_module('stage4e.audit')
        aggregate = importlib.import_module('stage0.result_audit').aggregate_paired_results
        server = importlib.import_module('stage0.runtime_server')
        live.GENERIC_WORKTREE = self.root
        types = live._load_repo_types()
        auditor = live._load_attempt_auditor(self.root)
        return live, audit, aggregate, server, types, auditor
