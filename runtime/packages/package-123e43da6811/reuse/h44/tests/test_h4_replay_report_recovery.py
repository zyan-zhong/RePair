from pathlib import Path

from pchsi.memory.source_state_contracts import SourceStateReplayReportV1
from recovery import diagnose
from tests.test_h3_recovery import _make_prior

KNOWN = "'SourceStateReplayReportV1' object has no attribute 'exact_match'"


def _report(status='PASS', failure_code=None):
    return SourceStateReplayReportV1(
        schema_id='SOURCE_STATE_REPLAY_REPORT_V1',
        schema_version=1,
        source_fingerprint_sha256='a'*64,
        replay_fingerprint_sha256='a'*64,
        transition_count=2,
        status=status,
        failure_code=failure_code,
        report_sha256=None,
    )


def test_native_branch_validates_replay_report_by_frozen_status_contract():
    import native_branch
    check = getattr(native_branch, '_assert_source_replay_pass', None)
    assert callable(check), 'native branch must expose the frozen replay-report status check'
    check(_report())


def test_known_exact_match_attribute_drift_is_pair_retryable(tmp_path: Path):
    prior = _make_prior(
        tmp_path,
        f0_error=('AttributeError', KNOWN),
        f1_error=('AttributeError', KNOWN),
    )
    census = diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is True
    assert census['retry_mode'] == 'ALL_INCOMPLETE_PAIRS_PAIRED_OPERATIONAL_RETRY'
    reasons = census['pair_rows'][0]['reasons']
    assert 'H4_FIX_REPLAY_REPORT_STATUS_FIELD_DRIFT:F0' in reasons
    assert 'H4_FIX_REPLAY_REPORT_STATUS_FIELD_DRIFT:F1' in reasons


def test_unknown_attribute_error_remains_no_blind_retry(tmp_path: Path):
    prior = _make_prior(
        tmp_path,
        f0_error=('AttributeError', "'OtherReport' object has no attribute 'x'"),
        f1_error=('AttributeError', "'OtherReport' object has no attribute 'x'"),
    )
    census = diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is False
    assert any('UNKNOWN_PROTOCOL_DEFECT_NO_BLIND_RETRY' in r for r in census['pair_rows'][0]['reasons'])


def test_known_drift_after_scientific_action_is_not_retried(tmp_path: Path):
    prior = _make_prior(
        tmp_path,
        f0_error=('AttributeError', KNOWN),
        f1_error=('AttributeError', KNOWN),
    )
    for branch_dir in (prior/'branches').iterdir():
        events = branch_dir/'events'
        events.mkdir()
        # This proves an environment action attributable to the scientific branch.
        from io_utils import put_json
        put_json(events/'000000.json', {'type':'ENVIRONMENT_ACTION_RESULT'})
    census = diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is False
    assert any('KNOWN_REPLAY_REPORT_DEFECT_AFTER_SCIENTIFIC_EFFECT_NO_RETRY' in r for r in census['pair_rows'][0]['reasons'])


def test_independent_verifier_accepts_frozen_replay_report_status_shape(tmp_path: Path):
    from tests.test_verifier import fixture_plan
    from independent_verifier import verify_plan
    from io_utils import read_json, put_json, canonical, sha
    plan_path = fixture_plan(tmp_path)
    plan = read_json(plan_path)
    for item in plan['branch_bindings']:
        key = item['binding']['branch_key_sha256']
        terminal_path = tmp_path/'branches'/key/'BRANCH_TERMINAL.json'
        row = read_json(terminal_path)
        fp = row['native_source_fingerprint_sha256']
        row['source_replay_report'] = SourceStateReplayReportV1(
            schema_id='SOURCE_STATE_REPLAY_REPORT_V1', schema_version=1,
            source_fingerprint_sha256=fp, replay_fingerprint_sha256=fp,
            transition_count=1, status='PASS', failure_code=None,
            report_sha256=None,
        ).to_dict()
        row['evidence_sha256'] = sha(canonical({k:v for k,v in row.items() if k!='evidence_sha256'}))
        terminal_path.write_bytes(canonical(row))
    result = verify_plan(plan_path, tmp_path)
    assert result['status'] == 'VERIFIED_COMPLETE'
    assert result['scientifically_complete_pair_count'] == result['frozen_pair_count']
