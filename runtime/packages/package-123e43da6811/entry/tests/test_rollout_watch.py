"""Operational deadlines use registered limits and contain only receipt-owned jobs."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from entry.rollout import await_rollout
from rollout_adapter.materializer import canonical, put, ref, AuthorityError


def fixture(tmp_path):
    path = tmp_path / 'MATERIALIZED.json'
    put(path, canonical({'root': str(tmp_path)}))
    put(tmp_path / 'SUBMISSION_RECEIPT.json', canonical({'array_job_id': '12345',
                                                       'manifest_sha256': ref(path)['sha256']}))
    return path, dict(watch_timeout_seconds=20, poll_seconds=2,
                     publication_grace_seconds=4, native_preflight_timeout_seconds=3)


def test_exact_native_handoff_completes_without_containment(tmp_path):
    path, settings = fixture(tmp_path)
    result = await_rollout(path, settings=settings, clock=lambda: 1,
        tick=lambda *a, **k: {'status': 'VALID_CURRENT_ROUND_HANDOFF'},
        command=lambda *a, **k: pytest.fail('completed rollout must not cancel'))
    assert result['status'] == 'VALID_CURRENT_ROUND_HANDOFF'


def test_missing_publication_contains_only_registered_job_after_grace(tmp_path):
    path, settings = fixture(tmp_path)
    now = [1]; commands = []
    def sleep(seconds): now[0] += seconds
    def command(argv, **kwargs): commands.append(argv); return {'returncode': 0}
    with pytest.raises(AuthorityError, match='WITHIN_REGISTERED_GRACE'):
        await_rollout(path, settings=settings, clock=lambda: now[0], sleep=sleep,
            tick=lambda *a, **k: {'status': 'ARRAY_INACTIVE_AWAITING_PUBLICATION', 'array_job_id': '12345'},
            command=command)
    assert commands == [['scancel', '12345']]
    assert now[0] == 5
    record = json.loads((tmp_path / 'RESIDENT_ROLLOUT_CONTAINMENT.json').read_bytes())
    assert record['scientific_round_consumed'] is False


def test_ambiguous_submission_never_resends_or_guesses_a_job(tmp_path):
    path, settings = fixture(tmp_path)
    with pytest.raises(AuthorityError, match='SUBMISSION_AMBIGUOUS_NO_RESEND'):
        await_rollout(path, settings=settings, clock=lambda: 1,
            tick=lambda *a, **k: {'status': 'SUBMISSION_AMBIGUOUS_NO_RESEND'},
            command=lambda *a, **k: pytest.fail('no guessed cancellation'))


def test_recovery_cannot_replace_registered_deadline(tmp_path):
    path, settings = fixture(tmp_path)
    await_rollout(path, settings=settings, clock=lambda: 1,
                  tick=lambda *a, **k: {'status': 'VALID_CURRENT_ROUND_HANDOFF'})
    with pytest.raises(AuthorityError, match='AUTHORITY_DRIFT'):
        await_rollout(path, settings={**settings, 'watch_timeout_seconds': 200}, clock=lambda: 2,
                      tick=lambda *a, **k: pytest.fail('must reject before work'))
