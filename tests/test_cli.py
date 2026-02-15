"""Tests for htan.cli — command dispatch and __main__."""

import subprocess
import sys


def test_cli_help():
    """htan --help should print usage and exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "htan", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_cli_version():
    """htan --version should print version."""
    result = subprocess.run(
        [sys.executable, "-m", "htan", "--version"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "htan" in result.stdout


def test_cli_unknown_command():
    """Unknown command should exit non-zero."""
    result = subprocess.run(
        [sys.executable, "-m", "htan", "nonexistent"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


def test_cli_no_args():
    """No args should print usage and exit non-zero."""
    result = subprocess.run(
        [sys.executable, "-m", "htan"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Usage:" in result.stdout


def test_cli_query_no_backend():
    """htan query with no backend should exit non-zero."""
    result = subprocess.run(
        [sys.executable, "-m", "htan", "query"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


def test_cli_config_check():
    """htan config check should return JSON."""
    result = subprocess.run(
        [sys.executable, "-m", "htan", "config", "check"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "python" in result.stdout


def test_main_module_invocation():
    """python -m htan should work."""
    result = subprocess.run(
        [sys.executable, "-m", "htan", "--version"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "0.2.0" in result.stdout
