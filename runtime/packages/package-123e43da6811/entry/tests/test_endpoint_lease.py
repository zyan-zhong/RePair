import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    path = ROOT / 'rollout_adapter/endpoint_lease.py'
    assert path.is_file(), 'per-service exclusive endpoint implementation missing'
    spec = importlib.util.spec_from_file_location('endpoint_lease_test', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_concurrent_services_have_exclusive_kernel_selected_endpoints():
    m = module()
    with m.reserve_endpoint('127.0.0.1') as a, m.reserve_endpoint('127.0.0.1') as b:
        assert a.getsockname()[1] != b.getsockname()[1]
        for leased in (a, b):
            with socket.socket() as other:
                with pytest.raises(OSError):
                    other.bind(leased.getsockname())


def test_only_deployment_port_changes_model_and_lora_flags_preserved():
    m = module()
    command = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server', '--host',
               '127.0.0.1', '--port', '8000', '--model', '/registered/base',
               '--enable-lora', '--lora-modules', 'candidate=/registered/adapter']
    with m.reserve_endpoint('127.0.0.1') as leased:
        changed = m.bind_command(command, leased)
        assert changed[command.index('--port') + 1] == str(leased.getsockname()[1])
        i = command.index('--port') + 1
        assert changed[:i] + changed[i+1:] == command[:i] + command[i+1:]
        assert command[i] == '8000'


@pytest.mark.parametrize('host', ['0.0.0.0', 'example.com', '192.168.1.1'])
def test_lease_cannot_expand_loopback_authority(host):
    with pytest.raises(ValueError, match='LOOPBACK'):
        module().reserve_endpoint(host)


@pytest.mark.skipif(os.name != 'posix', reason='live server uses Linux inherited descriptors')
def test_child_inherits_exclusive_socket_without_release_race(tmp_path):
    m = module()
    helper = tmp_path / 'child.py'
    helper.write_text('import socket,sys\ns=socket.socket(fileno=int(sys.argv[1]));s.listen();c,_=s.accept();c.sendall(b"owned");c.close()\n')
    import subprocess
    with m.reserve_endpoint('127.0.0.1') as leased:
        proc = subprocess.Popen([sys.executable, str(helper), str(leased.fileno())],
                                pass_fds=(leased.fileno(),))
        try:
            import time
            deadline = time.monotonic() + 5
            while True:
                try:
                    client = socket.create_connection(leased.getsockname(), timeout=1)
                    break
                except ConnectionRefusedError:
                    if time.monotonic() >= deadline: raise
                    time.sleep(.01)
            with client: assert client.recv(5) == b'owned'
            assert proc.wait(timeout=5) == 0
        finally:
            if proc.poll() is None: proc.kill()
