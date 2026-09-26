from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "tests" / "security"
SCRIPT_ROOT = REPO_ROOT / "scripts" / "security"
NATIVE_ROOT = REPO_ROOT / "native" / "s1_backend_probe"
NATIVE_TEST_ROOT = NATIVE_ROOT / "tests"
PROBE_ROOT = NATIVE_ROOT / "probes"
MAKEFILE = NATIVE_ROOT / "Makefile"
BINARY = NATIVE_ROOT / "build" / "pchsi-s1-backend-probe"

FORBIDDEN_EXECUTABLE_NAMES = {
    "bash",
    "bwrap",
    "dash",
    "firejail",
    "mount",
    "nsenter",
    "pivot_root",
    "sh",
    "sudo",
    "umount",
    "unshare",
    "zsh",
}

FORBIDDEN_ARGUMENT_MARKERS = {
    "CLONE_NEW",
    "SECCOMP_SET_MODE_FILTER",
    "landlock_restrict_self",
    "mount_setattr",
    "pivot_root",
}

SUBPROCESS_FUNCTIONS = {
    "call",
    "check_call",
    "check_output",
    "Popen",
    "run",
}

FORBIDDEN_OS_FUNCTIONS = {
    "popen",
    "system",
}

FORBIDDEN_CTYPES_FUNCTIONS = {
    "CDLL",
    "PyDLL",
    "WinDLL",
    "cdll",
    "pydll",
}

FORBIDDEN_SOCKET_FUNCTIONS = {
    "create_connection",
    "socket",
    "socketpair",
}

ALLOWED_SUBPROCESS_EXECUTE_CALLS = {
    (
        "tests/security/test_native_build.py",
        "test_native_execute_is_closed",
    ),
    (
        "tests/security/test_orchestrator.py",
        "test_backend_runner_execute_remains_closed",
    ),
}

ALLOWED_LOCAL_EXECUTE_CALLS = {
    (
        "tests/security/test_execution_gate.py",
        "test_python_execute_is_closed",
    ),
    (
        "tests/security/test_execution_gate.py",
        "test_repository_approval_path_cannot_open_gate",
    ),
}

LOCAL_EXECUTION_WRAPPERS = {
    "run_orchestrator",
}

ALLOWED_DYNAMIC_SUBPROCESS_HEADS = {
    (
        "tests/security/test_contracts.py",
        "test_c_validator_matches_shared_vectors",
    ): "str_path",
    (
        "tests/security/test_contracts_resources.py",
        "_compile_and_run",
    ): "str_path",
    (
        "tests/security/test_evidence_path.py",
        "test_native_path_and_evidence_unit_binary",
    ): "str_path",
    (
        "tests/security/test_evidence_stream.py",
        "test_native_evidence_tree_and_publication_contract",
    ): "str_path",
    (
        "tests/security/test_execution_gate.py",
        "run_orchestrator",
    ): "sys.executable",
    (
        "tests/security/test_manifests.py",
        "test_native_sha256_known_answers",
    ): "str_path",
    (
        "tests/security/test_native_build.py",
        "test_native_binary_describes_backend",
    ): "str_path",
    (
        "tests/security/test_native_build.py",
        "test_native_execute_is_closed",
    ): "str_path",
    (
        "tests/security/test_native_build.py",
        "test_native_version_is_stable",
    ): "str_path",
    (
        "tests/security/test_native_unit.py",
        "test_native_fake_only_unit_case",
    ): "str_path",
    (
        "tests/security/test_native_unit.py",
        "test_pure_supervisor_and_namespace_plans",
    ): "str_path",
    (
        "tests/security/test_orchestrator.py",
        "test_backend_runner_describe_is_dry",
    ): "sys.executable",
    (
        "tests/security/test_orchestrator.py",
        "test_backend_runner_execute_remains_closed",
    ): "sys.executable",
    (
        "tests/security/test_syscall_table.py",
        "test_generation_scripts_are_nonexecuting",
    ): "sys.executable",
}

FORBIDDEN_NATIVE_CALLS = {
    "clone",
    "clone3",
    "execve",
    "fork",
    "landlock_add_rule",
    "landlock_create_ruleset",
    "landlock_restrict_self",
    "mount",
    "mount_setattr",
    "pivot_root",
    "prctl",
    "seccomp",
    "setgid",
    "setns",
    "setrlimit",
    "setuid",
    "socket",
    "syscall",
    "umount2",
    "unshare",
    "vfork",
}

FORBIDDEN_DEFAULT_BINARY_SOURCES = {
    "mount_contract.c",
    "namespace_init.c",
    "real_system_ops.c",
    "seccomp_filter.c",
    "security_state.c",
    "source_copy.c",
    "source_resolution.c",
    "supervisor.c",
}

RISKY_DYNAMIC_SYMBOLS = {
    "clone",
    "clone3",
    "fork",
    "landlock_restrict_self",
    "mount",
    "pivot_root",
    "seccomp",
    "setgid",
    "setns",
    "setrlimit",
    "setuid",
    "socket",
    "syscall",
    "umount2",
    "unshare",
    "vfork",
}

_C_COMMENTS_AND_LITERALS = re.compile(
    r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|"
    r"'(?:\\.|[^'\\])*'",
    flags=re.DOTALL,
)


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _literal_strings(node: ast.AST) -> tuple[str, ...]:
    values: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.append(child.value)

    return tuple(values)


def _literal_command_head(node: ast.Call) -> str | None:
    if not node.args:
        return None

    command = node.args[0]

    if isinstance(command, ast.Constant) and isinstance(command.value, str):
        return command.value

    if isinstance(command, (ast.List, ast.Tuple)) and command.elts:
        head = command.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value

    return None


def _import_bindings(
    tree: ast.AST,
) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    module_aliases: dict[str, str] = {}
    direct_calls: dict[str, tuple[str, str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {
                    "ctypes",
                    "os",
                    "socket",
                    "subprocess",
                }:
                    module_aliases[alias.asname or alias.name] = alias.name

        if isinstance(node, ast.ImportFrom) and node.module in {
            "ctypes",
            "os",
            "socket",
            "subprocess",
        }:
            for alias in node.names:
                direct_calls[alias.asname or alias.name] = (
                    node.module,
                    alias.name,
                )

    return module_aliases, direct_calls


def _call_target(
    node: ast.Call,
    module_aliases: dict[str, str],
    direct_calls: dict[str, tuple[str, str]],
) -> tuple[str, str] | None:
    function = node.func

    if isinstance(function, ast.Name):
        return direct_calls.get(function.id)

    if (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
    ):
        module = module_aliases.get(function.value.id)
        if module is not None:
            return module, function.attr

    return None


def _keyword_is_true(node: ast.Call, name: str) -> bool:
    for keyword in node.keywords:
        if keyword.arg != name:
            continue
        return (
            isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
        )
    return False


class _CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_stack: list[str] = []
        self.calls: list[tuple[ast.Call, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        context = (
            self.function_stack[-1]
            if self.function_stack
            else "<module>"
        )
        self.calls.append((node, context))
        self.generic_visit(node)


def _call_contexts(tree: ast.AST) -> tuple[tuple[ast.Call, str], ...]:
    collector = _CallCollector()
    collector.visit(tree)
    return tuple(collector.calls)


def _dynamic_command_head_kind(node: ast.Call) -> str | None:
    if not node.args:
        return None

    command = node.args[0]
    if not isinstance(command, (ast.List, ast.Tuple)) or not command.elts:
        return None

    head = command.elts[0]

    if (
        isinstance(head, ast.Attribute)
        and isinstance(head.value, ast.Name)
        and head.value.id == "sys"
        and head.attr == "executable"
    ):
        return "sys.executable"

    if (
        isinstance(head, ast.Call)
        and isinstance(head.func, ast.Name)
        and head.func.id == "str"
        and len(head.args) == 1
        and not head.keywords
    ):
        return "str_path"

    return None


def _python_source_violations(
    path: Path,
    source: str,
) -> list[str]:
    relative = _relative(path)
    tree = ast.parse(source, filename=relative)
    module_aliases, direct_calls = _import_bindings(tree)
    violations: list[str] = []

    for alias, module in module_aliases.items():
        if module in {"ctypes", "socket"}:
            violations.append(
                f"{relative}:import:{module} as {alias}"
            )

    for alias, (module, imported_name) in direct_calls.items():
        if module in {"ctypes", "socket"}:
            violations.append(
                f"{relative}:import:{module}.{imported_name} as {alias}"
            )

    for node, context in _call_contexts(tree):
        strings = _literal_strings(node)
        local_function = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else None
        )

        if (
            local_function in LOCAL_EXECUTION_WRAPPERS
            and "--execute" in strings
            and (relative, context) not in ALLOWED_LOCAL_EXECUTE_CALLS
        ):
            violations.append(
                f"{relative}:{node.lineno}:unapproved local --execute call"
            )

        target = _call_target(
            node,
            module_aliases,
            direct_calls,
        )
        if target is None:
            continue

        module, function = target

        if module == "subprocess" and function in SUBPROCESS_FUNCTIONS:
            if _keyword_is_true(node, "shell"):
                violations.append(
                    f"{relative}:{node.lineno}:subprocess shell=True"
                )

            for value in strings:
                executable = Path(value).name
                if executable in FORBIDDEN_EXECUTABLE_NAMES:
                    violations.append(
                        f"{relative}:{node.lineno}:forbidden executable:{value}"
                    )

                for marker in FORBIDDEN_ARGUMENT_MARKERS:
                    if marker in value:
                        violations.append(
                            f"{relative}:{node.lineno}:forbidden marker:{marker}"
                        )

            if (
                "--execute" in strings
                and (relative, context)
                not in ALLOWED_SUBPROCESS_EXECUTE_CALLS
            ):
                violations.append(
                    f"{relative}:{node.lineno}:unapproved subprocess --execute call"
                )

            head = _literal_command_head(node)
            if head is None:
                expected_kind = ALLOWED_DYNAMIC_SUBPROCESS_HEADS.get(
                    (relative, context)
                )
                observed_kind = _dynamic_command_head_kind(node)

                if expected_kind is None:
                    violations.append(
                        f"{relative}:{node.lineno}:unreviewed dynamic subprocess command"
                    )
                elif observed_kind != expected_kind:
                    violations.append(
                        f"{relative}:{node.lineno}:dynamic subprocess head changed:"
                        f"expected={expected_kind}:observed={observed_kind}"
                    )

        if module == "os":
            if (
                function in FORBIDDEN_OS_FUNCTIONS
                or function.startswith("exec")
                or function.startswith("spawn")
            ):
                violations.append(
                    f"{relative}:{node.lineno}:forbidden os.{function}"
                )

        if module == "ctypes" and function in FORBIDDEN_CTYPES_FUNCTIONS:
            violations.append(
                f"{relative}:{node.lineno}:forbidden ctypes.{function}"
            )

        if module == "socket" and function in FORBIDDEN_SOCKET_FUNCTIONS:
            violations.append(
                f"{relative}:{node.lineno}:forbidden socket.{function}"
            )

    return violations


def _strip_c_comments_and_literals(source: str) -> str:
    return _C_COMMENTS_AND_LITERALS.sub(" ", source)


def _native_source_violations(
    path: Path,
    source: str,
) -> list[str]:
    relative = _relative(path)
    sanitized = _strip_c_comments_and_literals(source)
    violations: list[str] = []

    for function in sorted(FORBIDDEN_NATIVE_CALLS):
        pattern = re.compile(
            rf"(?<![A-Za-z0-9_.>])\b{re.escape(function)}\s*\("
        )
        if pattern.search(sanitized) is not None:
            violations.append(
                f"{relative}:direct native call:{function}"
            )

    return violations


def _makefile_violations(source: str) -> list[str]:
    violations: list[str] = []
    lines = source.splitlines()

    try:
        sources_start = lines.index("SOURCES := \\")
    except ValueError:
        sources_start = -1

    objects_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("OBJECTS :=")
        ),
        -1,
    )

    if (
        sources_start < 0
        or objects_start <= sources_start
    ):
        violations.append("Makefile:SOURCES block missing")
        body = ""
    else:
        body = "\n".join(
            lines[sources_start + 1:objects_start]
        )

    for filename in sorted(FORBIDDEN_DEFAULT_BINARY_SOURCES):
        if filename in body:
            violations.append(
                f"Makefile:default binary links:{filename}"
            )

    if 'probe-payloads:' not in source:
        violations.append("Makefile:probe-payloads target missing")

    if '-c "$<" -o "$@"' not in source:
        violations.append("Makefile:payload recipe is not compile-only")

    if 'run-probe-payloads' in source:
        violations.append("Makefile:payload execution target exists")

    if '! "$(BINARY)" --execute' not in source:
        violations.append("Makefile:closed native execute check missing")

    return violations


def test_python_scanner_rejects_subprocess_alias() -> None:
    source = (
        "from subprocess import run as launch\n"
        "launch(['/usr/bin/unshare'])\n"
    )

    violations = _python_source_violations(
        REPO_ROOT / "scripts/security/example.py",
        source,
    )

    assert any("unshare" in violation for violation in violations)


def test_python_scanner_rejects_shell_true() -> None:
    source = (
        "import subprocess as sp\n"
        "sp.run(command, shell=True)\n"
    )

    violations = _python_source_violations(
        REPO_ROOT / "scripts/security/example.py",
        source,
    )

    assert any("shell=True" in violation for violation in violations)


def test_python_scanner_rejects_unreviewed_dynamic_command() -> None:
    source = (
        "import subprocess\n"
        "def launch(command):\n"
        "    return subprocess.run(command)\n"
    )

    violations = _python_source_violations(
        REPO_ROOT / "tests/security/unreviewed.py",
        source,
    )

    assert any(
        "unreviewed dynamic subprocess command" in violation
        for violation in violations
    )


def test_python_scanner_allows_reviewed_sys_executable_head() -> None:
    source = (
        "import subprocess\n"
        "import sys\n"
        "def test_backend_runner_describe_is_dry():\n"
        "    subprocess.run([sys.executable, 'runner.py', '--describe'])\n"
    )

    assert _python_source_violations(
        REPO_ROOT / "tests/security/test_orchestrator.py",
        source,
    ) == []


def test_python_scanner_rejects_os_exec_and_socket_import() -> None:
    source = (
        "import os as operating_system\n"
        "import socket\n"
        "operating_system.execve('/bin/true', ['/bin/true'], {})\n"
    )

    violations = _python_source_violations(
        REPO_ROOT / "tests/security/example.py",
        source,
    )

    assert any("os.execve" in violation for violation in violations)
    assert any("import:socket" in violation for violation in violations)


def test_python_scanner_allows_fixed_readelf_command() -> None:
    source = (
        "import subprocess\n"
        "subprocess.run(['/usr/bin/readelf', '--wide', 'binary'])\n"
    )

    assert _python_source_violations(
        REPO_ROOT / "scripts/security/example.py",
        source,
    ) == []


def test_native_scanner_rejects_direct_mount_but_allows_injected_call() -> None:
    unsafe = 'mount(NULL, "/x", "tmpfs", 0UL, NULL);\n'
    safe = (
        'operations.mount_fn(operations.context, NULL, "/x", '
        '"tmpfs", 0UL, NULL);\n'
    )

    assert _native_source_violations(
        REPO_ROOT / "native/s1_backend_probe/tests/unsafe.c",
        unsafe,
    )
    assert _native_source_violations(
        REPO_ROOT / "native/s1_backend_probe/tests/safe.c",
        safe,
    ) == []


def test_makefile_scanner_rejects_default_real_ops_link() -> None:
    continuation = chr(92)
    unsafe = "\n".join(
        (
            f"SOURCES := {continuation}",
            f"\tsrc/errors.c {continuation}",
            f"\tsrc/main.c {continuation}",
            "\tsrc/real_system_ops.c",
            "OBJECTS := build/errors.o",
            "probe-payloads:",
            '\t$(CC) -c "$<" -o "$@"',
            "unit:",
            '\t! "$(BINARY)" --execute',
        )
    ) + "\n"

    violations = _makefile_violations(unsafe)

    assert any(
        "real_system_ops.c" in violation
        for violation in violations
    )


def test_security_tests_scripts_and_native_fixtures_are_nonexecuting() -> None:
    violations: list[str] = []

    python_paths = [
        *sorted(TEST_ROOT.glob("test_*.py")),
        *sorted(SCRIPT_ROOT.glob("*.py")),
    ]

    for path in python_paths:
        if path.resolve() == Path(__file__).resolve():
            continue
        violations.extend(
            _python_source_violations(
                path,
                path.read_text(encoding="utf-8"),
            )
        )

    native_paths = [
        *sorted(NATIVE_TEST_ROOT.glob("*.c")),
        *sorted(PROBE_ROOT.glob("*.c")),
    ]

    for path in native_paths:
        violations.extend(
            _native_source_violations(
                path,
                path.read_text(encoding="utf-8"),
            )
        )

    violations.extend(
        _makefile_violations(
            MAKEFILE.read_text(encoding="utf-8")
        )
    )

    assert violations == []


def test_default_native_binary_has_no_risky_dynamic_symbols() -> None:
    assert BINARY.is_file(), f"native binary missing: {BINARY}"

    result = subprocess.run(
        ["/usr/bin/nm", "-u", str(BINARY)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr

    observed = {
        symbol
        for symbol in RISKY_DYNAMIC_SYMBOLS
        if re.search(
            rf"\b{re.escape(symbol)}(?:@|\b)",
            result.stdout,
        ) is not None
    }

    assert observed == set()
