from pathlib import Path

import round_plan
from io_utils import digest_file


def test_prepare_plan_consumes_load_source_rows_contract_without_shape_drift(tmp_path, monkeypatch):
    capture_zip = Path(__file__).resolve().parent / 'fixtures' / 'E_SOURCE_CAPTURE.zip'
    memory = tmp_path / 'memory.json'
    memory.write_text('{"schema_id":"TEST_MEMORY_BYTES"}\n', encoding='utf-8')

    monkeypatch.setattr(
        round_plan,
        'resolve_memory',
        lambda **kwargs: {
            'path': str(memory),
            'file_sha256': digest_file(memory),
            'value': {},
        },
    )

    def fake_gamefiles(*, source_rows, **kwargs):
        return {
            row['fingerprint']['source_task_id']: {'gamefile': '/unused/game.tw-pddl'}
            for row in source_rows
        }

    monkeypatch.setattr(round_plan, 'resolve_gamefiles', fake_gamefiles)

    class FakeSource:
        def canonical_bytes(self):
            return b'{"schema_id":"TEST_REPLAY_SOURCE"}\n'

    observed = []

    def fake_register(row, *, exact_gamefile, verify_gamefile=True):
        observed.append((row['handoff_state']['source_state_sha256'], exact_gamefile))
        return FakeSource()

    monkeypatch.setattr(round_plan, 'register_source', fake_register)

    plan = round_plan.prepare_plan(
        capture_zip=capture_zip,
        expected_sha256=digest_file(capture_zip),
        run_root=tmp_path / 'run',
        locators={},
        operations={'policy_timeout_seconds': 60.0},
    )

    assert len(plan['states']) == plan['handoff']['selected_state_count']
    assert len(plan['branch_bindings']) == plan['handoff']['selected_branch_run_budget']
    assert len(observed) == plan['handoff']['selected_state_count']
    assert all(row['semantics_status'] == 'COMPILED' for row in plan['states'])
    assert {
        row['native_source_fingerprint_sha256'] for row in plan['states']
    } == {
        binding['binding']['native_source_fingerprint_sha256']
        for binding in plan['branch_bindings']
    }
