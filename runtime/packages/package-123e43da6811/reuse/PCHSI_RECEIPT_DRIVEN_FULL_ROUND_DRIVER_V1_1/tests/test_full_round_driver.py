import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "full_round_driver.py"


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def base_plan(tmp_path: Path, gates):
    return {
        "schema_id": "PCHSI_FULL_ROUND_PLAN_V1",
        "schema_version": 1,
        "round_id": "test-round",
        "policy_version": "pi-k",
        "expected_repo_head": None,
        "gates": gates,
    }


def gate(gid, command, receipt, *, depends=None, side="DETERMINISTIC", bound=True):
    return {
        "gate_id": gid,
        "depends_on": depends or [],
        "binding_status": "BOUND" if bound else "UNBOUND",
        "side_effect_class": side,
        "command": command,
        "cwd": None,
        "terminal_receipt": str(receipt),
        "terminal_contract": {"kind": "JSON_FIELD", "field": "status", "equals": "PASS"},
    }


def run_driver(tmp_path: Path, plan, *extra):
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    state = tmp_path / "state"
    cp = subprocess.run(
        [sys.executable, str(DRIVER), "--plan", str(plan_path), "--state-root", str(state), *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return cp, state


def test_executes_in_dependency_order_and_writes_receipts(tmp_path):
    log = tmp_path / "order.txt"
    ra = tmp_path / "a.json"
    rb = tmp_path / "b.json"
    py = sys.executable
    gates = [
        gate("A", [py, "-c", f"from pathlib import Path; import json; Path({str(log)!r}).write_text('A\\n'); Path({str(ra)!r}).write_text(json.dumps({{'status':'PASS'}}))"], ra),
        gate("B", [py, "-c", f"from pathlib import Path; import json; p=Path({str(log)!r}); p.write_text(p.read_text()+'B\\n'); Path({str(rb)!r}).write_text(json.dumps({{'status':'PASS'}}))"], rb, depends=["A"]),
    ]
    cp, state = run_driver(tmp_path, base_plan(tmp_path, gates))
    assert cp.returncode == 0, cp.stdout
    assert log.read_text() == "A\nB\n"
    assert (state / "gates" / "A" / "terminal.json").is_file()
    assert (state / "gates" / "B" / "terminal.json").is_file()
    assert "PCHSI_FULL_ROUND_DRIVER_PASS" in cp.stdout


def test_reuses_existing_valid_terminal_receipt_without_reexecution(tmp_path):
    marker = tmp_path / "should_not_exist.txt"
    receipt = tmp_path / "already.json"
    write_json(receipt, {"status": "PASS"})
    gates = [gate("A", [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('BAD')"], receipt)]
    cp, _ = run_driver(tmp_path, base_plan(tmp_path, gates))
    assert cp.returncode == 0, cp.stdout
    assert not marker.exists()
    assert "GATE_REUSED=A" in cp.stdout


def test_unbound_gate_preflight_blocks_without_executing(tmp_path):
    marker = tmp_path / "should_not_exist.txt"
    receipt = tmp_path / "x.json"
    gates = [gate("A", [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('BAD')"], receipt, bound=False)]
    cp, _ = run_driver(tmp_path, base_plan(tmp_path, gates), "--preflight-only")
    assert cp.returncode != 0
    assert not marker.exists()
    assert "UNBOUND_GATE=A" in cp.stdout


def test_partial_unsafe_gate_stops_before_resend(tmp_path):
    marker = tmp_path / "should_not_exist.txt"
    receipt = tmp_path / "x.json"
    gates = [gate("A", [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('BAD')"], receipt, side="PROVIDER_OR_ENVIRONMENT")]
    plan = base_plan(tmp_path, gates)
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    state = tmp_path / "state"
    started = state / "gates" / "A" / "started.json"
    write_json(started, {"gate_id": "A", "command_sha256": "unknown-old-attempt"})
    cp = subprocess.run([sys.executable, str(DRIVER), "--plan", str(plan_path), "--state-root", str(state)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert cp.returncode != 0
    assert not marker.exists()
    assert "PARTIAL_UNSAFE_GATE=A" in cp.stdout


def test_failed_gate_blocks_downstream(tmp_path):
    rb = tmp_path / "b.json"
    marker = tmp_path / "downstream.txt"
    gates = [
        gate("A", [sys.executable, "-c", "raise SystemExit(7)"], tmp_path / "a.json"),
        gate("B", [sys.executable, "-c", f"from pathlib import Path; import json; Path({str(marker)!r}).write_text('BAD'); Path({str(rb)!r}).write_text(json.dumps({{'status':'PASS'}}))"], rb, depends=["A"]),
    ]
    cp, _ = run_driver(tmp_path, base_plan(tmp_path, gates))
    assert cp.returncode != 0
    assert not marker.exists()
    assert "GATE_COMMAND_FAILED=A:rc=7" in cp.stdout


def test_cycle_is_rejected(tmp_path):
    gates = [
        gate("A", ["true"], tmp_path / "a.json", depends=["B"]),
        gate("B", ["true"], tmp_path / "b.json", depends=["A"]),
    ]
    cp, _ = run_driver(tmp_path, base_plan(tmp_path, gates), "--preflight-only")
    assert cp.returncode != 0
    assert "DEPENDENCY_CYCLE" in cp.stdout


def test_terminal_contract_failure_is_not_completion(tmp_path):
    receipt = tmp_path / "bad.json"
    gates = [gate("A", [sys.executable, "-c", f"from pathlib import Path; import json; Path({str(receipt)!r}).write_text(json.dumps({{'status':'NOT_PASS'}}))"], receipt)]
    cp, _ = run_driver(tmp_path, base_plan(tmp_path, gates))
    assert cp.returncode != 0
    assert "TERMINAL_RECEIPT_INVALID=A" in cp.stdout
