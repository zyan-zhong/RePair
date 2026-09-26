from __future__ import annotations
from pathlib import Path
import json, pytest
from round_entry_binding import validate_round_entry_binding, render_round_entry_argv


def binding():
    return {"schema_id":"NEXT_ROUND_UPSTREAM_LAUNCH_BINDING_V1","schema_version":1,
            "fixed_head":"61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a",
            "argv_template":["python","/runner.py","--round-id","{round_id}","--parent-policy-id","{parent_policy_id}",
                             "--memory-snapshot","{memory_snapshot_path}","--output-root","{round_root}"],
            "required_placeholders":["round_id","parent_policy_id","memory_snapshot_path","round_root"],
            "started_receipt_relative_path":"ROUND_STARTED_V1.json",
            "terminal_receipt_relative_path":"ROUND_UPSTREAM_TERMINAL_V1.json",
            "shell":False,"human_decision_required":False}


def test_next_round_binding_requires_no_human_and_shell_false():
    x=validate_round_entry_binding(binding())
    assert x['human_decision_required'] is False and x['shell'] is False


def test_render_next_round_argv_is_mechanical():
    x=render_round_entry_argv(binding(),round_id='R2',parent_policy_id='PI1',memory_snapshot_path='/m.json',round_root='/r2')
    assert x[-1]=='/r2' and 'R2' in x and 'PI1' in x


def test_missing_placeholder_fails_closed():
    b=binding(); b['argv_template']=["python","/runner.py","--round-id","{round_id}"]
    with pytest.raises(ValueError,match='PLACEHOLDER'):
        validate_round_entry_binding(b)
