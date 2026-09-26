"""Allocation-local endpoint ownership; scientific launch arguments stay intact.

The socket is bound without SO_REUSEPORT and inherited by the native server.
There is no close-then-bind window, endpoint scan, or reuse of another service.
"""
import hashlib
import importlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from urllib.parse import urlsplit


def reserve_endpoint(host):
    try:
        address = ipaddress.ip_address(host)
        if not address.is_loopback:
            raise ValueError()
    except ValueError as exc:
        raise ValueError('REGISTERED_LOOPBACK_ENDPOINT_REQUIRED') from exc
    sock = socket.socket(socket.AF_INET6 if address.version == 6 else socket.AF_INET,
                         socket.SOCK_STREAM)
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((host, 0))
        return sock
    except BaseException:
        sock.close()
        raise


def _flag(command, name):
    if command.count(name) != 1 or command.index(name) + 1 >= len(command):
        raise ValueError('EXACT_NATIVE_LAUNCH_FLAG_REQUIRED:' + name)
    return command.index(name) + 1


def bind_command(command, sock):
    result = list(command)
    if result[_flag(result, '--host')] != sock.getsockname()[0]:
        raise ValueError('ENDPOINT_HOST_AUTHORITY_CHANGED')
    result[_flag(result, '--port')] = str(sock.getsockname()[1])
    return result


def launch_with_lease(command, *, output_root, stdout, stderr, cwd=None, env=None):
    if os.name != 'posix':
        raise ValueError('NATIVE_LINUX_DESCRIPTOR_INHERITANCE_REQUIRED')
    # The original registered entrypoint and all model/adapter/engine flags travel
    # unchanged to the original parser; this wrapper owns only its listening FD.
    if command[1:3] != ['-m', 'vllm.entrypoints.openai.api_server']:
        raise ValueError('REGISTERED_VLLM_ENTRYPOINT_REQUIRED')
    host = command[_flag(command, '--host')]
    with reserve_endpoint(host) as sock:
        bound = bind_command(command, sock)
        port = sock.getsockname()[1]
        display_host = '[' + host + ']' if ':' in host else host
        url = 'http://' + display_host + ':' + str(port)
        argv = [bound[0], '-B', str(Path(__file__).resolve()), '--serve',
                str(sock.fileno()), *bound[1:]]
        row = {'schema_id': 'ALLOCATION_LOCAL_POLICY_ENDPOINT_LEASE_V1',
               'node': socket.gethostname(), 'slurm_job_id': os.environ.get('SLURM_JOB_ID'),
               'original_argv': command, 'bound_native_argv': bound, 'argv': argv,
               'policy_base_url': url, 'kernel_allocated_port': port,
               'exclusive_socket_inherited': True, 'scientific_arguments_changed': False}
        root = Path(output_root); root.mkdir(parents=True, exist_ok=True)
        with (root / 'POLICY_ENDPOINT_LEASE.json').open('x', encoding='utf8') as stream:
            json.dump(row, stream, sort_keys=True); stream.write('\n')
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, start_new_session=True, pass_fds=(sock.fileno(),))
        return proc, url


def serve(fd, command):
    if command[:2] != ['-m', 'vllm.entrypoints.openai.api_server']:
        raise ValueError('REGISTERED_VLLM_ENTRYPOINT_REQUIRED')
    sock = socket.socket(fileno=fd)
    if sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT):
        raise ValueError('SHARED_ENDPOINT_FORBIDDEN')
    api = importlib.import_module(command[1])
    # Receipt and runtime checks bind the installed version; this also checks the
    # concrete socket handoff interface before any model is instantiated.
    for name in ('cli_env_setup', 'FlexibleArgumentParser', 'make_arg_parser',
                 'validate_parsed_serve_args', 'create_server_socket', 'run_server', 'uvloop'):
        if not hasattr(api, name):
            raise ValueError('NATIVE_SOCKET_HANDOFF_INTERFACE_MISSING:' + name)
    api.cli_env_setup()
    parser = api.make_arg_parser(api.FlexibleArgumentParser(
        description='Registered policy service with an allocation-owned socket.'))
    args = parser.parse_args(command[2:])
    api.validate_parsed_serve_args(args)
    expected = sock.getsockname()[:2]
    if (args.host, args.port) != expected:
        raise ValueError('NATIVE_SOCKET_ADDRESS_MISMATCH')
    original = api.create_server_socket
    used = False

    def adopt(addr):
        nonlocal used
        if used or addr != expected:
            raise ValueError('NATIVE_SOCKET_HANDOFF_IDENTITY')
        used = True
        return sock

    api.create_server_socket = adopt
    try:
        api.uvloop.run(api.run_server(args))
    finally:
        api.create_server_socket = original
        sock.close()


if __name__ == '__main__':
    if len(sys.argv) < 5 or sys.argv[1] != '--serve':
        raise SystemExit('LEASED_SERVICE_ARGUMENTS_REQUIRED')
    serve(int(sys.argv[2]), sys.argv[3:])
