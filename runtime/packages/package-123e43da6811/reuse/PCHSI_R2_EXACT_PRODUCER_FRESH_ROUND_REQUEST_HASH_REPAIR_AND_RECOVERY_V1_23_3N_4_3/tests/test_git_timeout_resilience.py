from __future__ import annotations

import recovery_core as c
import pytest


def _result(argv, returncode, stdout="", stderr=""):
    return {
        "argv": list(argv),
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def test_git_status_timeout_retries_identical_argv_once(monkeypatch):
    argv = ["git", "-C", "/repo", "status", "--porcelain=v1", "--untracked-files=all"]
    calls = []

    def fake_cmd(actual, *, timeout=120, cwd=None):
        calls.append((list(actual), timeout, cwd))
        if len(calls) == 1:
            return _result(actual, 124, stderr="TIMEOUT:")
        return _result(actual, 0, stdout="")

    monkeypatch.setattr(c, "cmd", fake_cmd)
    out = c.checked_timeout_retry(
        argv,
        initial_timeout=120,
        retry_timeout=180,
    )
    assert out == ""
    assert calls == [(argv, 120, None), (argv, 180, None)]


def test_git_status_non_timeout_failure_is_not_retried(monkeypatch):
    argv = ["git", "status"]
    calls = []

    def fake_cmd(actual, *, timeout=120, cwd=None):
        calls.append((list(actual), timeout, cwd))
        return _result(actual, 128, stderr="fatal: not a git repository")

    monkeypatch.setattr(c, "cmd", fake_cmd)
    with pytest.raises(ValueError, match="COMMAND_FAILED"):
        c.checked_timeout_retry(argv, initial_timeout=120, retry_timeout=180)
    assert calls == [(argv, 120, None)]


def test_git_status_second_timeout_fails_closed_after_one_retry(monkeypatch):
    argv = ["git", "status"]
    calls = []

    def fake_cmd(actual, *, timeout=120, cwd=None):
        calls.append((list(actual), timeout, cwd))
        return _result(actual, 124, stderr="TIMEOUT:")

    monkeypatch.setattr(c, "cmd", fake_cmd)
    with pytest.raises(ValueError, match="COMMAND_FAILED"):
        c.checked_timeout_retry(argv, initial_timeout=120, retry_timeout=180)
    assert calls == [(argv, 120, None), (argv, 180, None)]
