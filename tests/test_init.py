"""Tests for htan.init — the interactive setup wizard."""

import os
import sys
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Import smoke tests
# ---------------------------------------------------------------------------

def test_import_init_module():
    from htan.init import (
        cli_main,
        run_init,
        show_status,
        PORTAL_CREDENTIALS_SYNAPSE_ID,
        SYNAPSE_TEAM_URL,
        SERVICES,
        INIT_ORDER,
    )
    assert PORTAL_CREDENTIALS_SYNAPSE_ID == "syn73720854"
    assert len(SERVICES) == 4
    assert INIT_ORDER[0] == "synapse"  # synapse before portal


def test_import_ui_helpers():
    from htan.init import _status_icon, _print_header, _prompt, _print_status


def test_import_verify_portal():
    from htan.init import _verify_portal


def test_import_service_inits():
    from htan.init import _init_synapse, _init_portal, _init_bigquery, _init_gen3


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def test_status_icon():
    from htan.init import _status_icon
    assert _status_icon(True) == "\u2713"
    assert _status_icon(False) == "\u2717"


def test_print_header(capsys):
    from htan.init import _print_header
    _print_header("Test Section")
    captured = capsys.readouterr()
    assert "Test Section" in captured.err


def test_print_status(capsys):
    from htan.init import _print_status
    _print_status("MyService", True, "all good")
    captured = capsys.readouterr()
    assert "MyService" in captured.err
    assert "all good" in captured.err
    assert "\u2713" in captured.err


def test_print_skip(capsys):
    from htan.init import _print_skip
    _print_skip("Skipped", "reason here")
    captured = capsys.readouterr()
    assert "Skipped" in captured.err
    assert "reason here" in captured.err


def test_prompt_eof():
    """_prompt returns default when input raises EOFError."""
    from htan.init import _prompt
    with mock.patch("builtins.input", side_effect=EOFError):
        assert _prompt("question? ", "fallback") == "fallback"


def test_prompt_keyboard_interrupt():
    from htan.init import _prompt
    with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
        assert _prompt("question? ", "default") == "default"


def test_prompt_returns_user_input():
    from htan.init import _prompt
    with mock.patch("builtins.input", return_value="  hello  "):
        assert _prompt("question? ") == "hello"


def test_prompt_empty_returns_default():
    from htan.init import _prompt
    with mock.patch("builtins.input", return_value=""):
        assert _prompt("question? ", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# show_status
# ---------------------------------------------------------------------------

def test_show_status_returns_dict(capsys):
    from htan.init import show_status
    result = show_status()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"portal", "synapse", "bigquery", "gen3"}
    for v in result.values():
        assert isinstance(v, bool)


def test_show_status_prints_to_stderr(capsys):
    from htan.init import show_status
    show_status()
    captured = capsys.readouterr()
    assert captured.out == ""  # nothing on stdout
    assert "Portal" in captured.err
    assert "Synapse" in captured.err


# ---------------------------------------------------------------------------
# _verify_portal
# ---------------------------------------------------------------------------

def test_verify_portal_no_config():
    """_verify_portal returns False when no config is available."""
    from htan.init import _verify_portal
    from htan.config import ConfigError
    with mock.patch("htan.init.load_portal_config", side_effect=ConfigError("no config")):
        assert _verify_portal() is False


def test_verify_portal_network_error():
    """_verify_portal returns False on network errors."""
    from htan.init import _verify_portal
    fake_cfg = {"host": "invalid", "port": "8443", "user": "u", "password": "p"}
    with mock.patch("htan.init.load_portal_config", return_value=fake_cfg):
        assert _verify_portal() is False


# ---------------------------------------------------------------------------
# _init_synapse (non-interactive)
# ---------------------------------------------------------------------------

def test_init_synapse_no_auth_non_interactive(capsys):
    """Non-interactive mode returns (False, None) when no auth configured."""
    from htan.init import _init_synapse
    with mock.patch.dict(os.environ, {}, clear=False):
        # Remove SYNAPSE_AUTH_TOKEN if set
        env = {k: v for k, v in os.environ.items() if k != "SYNAPSE_AUTH_TOKEN"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("os.path.exists", return_value=False):
                ok, client = _init_synapse(non_interactive=True)
    assert ok is False
    assert client is None


def test_init_synapse_has_token_but_no_synapseclient(capsys):
    """When token exists but synapseclient not importable."""
    from htan.init import _init_synapse
    with mock.patch.dict(os.environ, {"SYNAPSE_AUTH_TOKEN": "fake-token"}):
        with mock.patch("htan.init.os.path.exists", return_value=False):
            # Make import fail for synapseclient
            with mock.patch.dict(sys.modules, {"synapseclient": None}):
                ok, client = _init_synapse(non_interactive=True)
    # Should try to import and fail
    assert client is None


# ---------------------------------------------------------------------------
# _init_portal (non-interactive)
# ---------------------------------------------------------------------------

def test_init_portal_already_configured(capsys):
    """Returns True if portal is already configured and connectivity works."""
    from htan.init import _init_portal
    with mock.patch("htan.init.detect_source", return_value="keychain"):
        with mock.patch("htan.init._verify_portal", return_value=True):
            result = _init_portal(non_interactive=True)
    assert result is True
    captured = capsys.readouterr()
    assert "keychain" in captured.err


def test_init_portal_configured_but_connectivity_fails(capsys):
    """Returns False if configured but connectivity fails."""
    from htan.init import _init_portal
    with mock.patch("htan.init.detect_source", return_value="file"):
        with mock.patch("htan.init._verify_portal", return_value=False):
            result = _init_portal(non_interactive=True)
    assert result is False


def test_init_portal_not_configured_no_synapse(capsys):
    """Returns False when no portal config and no synapse client in non-interactive mode."""
    from htan.init import _init_portal
    with mock.patch("htan.init.detect_source", return_value=None):
        result = _init_portal(non_interactive=True, synapse_client=None)
    assert result is False


# ---------------------------------------------------------------------------
# _init_bigquery (non-interactive)
# ---------------------------------------------------------------------------

def test_init_bigquery_not_configured_non_interactive(capsys):
    from htan.init import _init_bigquery
    with mock.patch.dict(os.environ, {}, clear=False):
        env = {k: v for k, v in os.environ.items()
               if k not in ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT")}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("htan.init.os.path.exists", return_value=False):
                result = _init_bigquery(non_interactive=True)
    assert result is False


def test_init_bigquery_has_adc(capsys):
    from htan.init import _init_bigquery, BIGQUERY_ADC_PATH
    # Patch os.path.exists to return True for ADC path
    original_exists = os.path.exists

    def mock_exists(path):
        if path == BIGQUERY_ADC_PATH:
            return True
        return original_exists(path)

    with mock.patch("htan.init.os.path.exists", side_effect=mock_exists):
        result = _init_bigquery(non_interactive=True)
    assert result is True


# ---------------------------------------------------------------------------
# _init_gen3 (non-interactive)
# ---------------------------------------------------------------------------

def test_init_gen3_not_configured_non_interactive(capsys):
    from htan.init import _init_gen3
    with mock.patch.dict(os.environ, {}, clear=False):
        env = {k: v for k, v in os.environ.items() if k != "GEN3_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("htan.init.os.path.exists", return_value=False):
                result = _init_gen3(non_interactive=True)
    assert result is False


def test_init_gen3_has_config(capsys):
    from htan.init import _init_gen3, GEN3_CREDS_PATH
    original_exists = os.path.exists

    def mock_exists(path):
        if path == GEN3_CREDS_PATH:
            return True
        return original_exists(path)

    with mock.patch("htan.init.os.path.exists", side_effect=mock_exists):
        result = _init_gen3(non_interactive=True)
    assert result is True


# ---------------------------------------------------------------------------
# run_init
# ---------------------------------------------------------------------------

def test_run_init_status_only(capsys):
    """--status mode shows status and returns dict."""
    from htan.init import run_init
    result = run_init(status_only=True)
    assert isinstance(result, dict)
    assert "portal" in result
    captured = capsys.readouterr()
    assert "Welcome" in captured.err


def test_run_init_non_interactive(capsys):
    """Non-interactive mode runs all services without prompting."""
    from htan.init import run_init
    with mock.patch("htan.init._init_synapse", return_value=(False, None)) as m_syn:
        with mock.patch("htan.init._init_portal", return_value=False) as m_portal:
            with mock.patch("htan.init._init_bigquery", return_value=False) as m_bq:
                with mock.patch("htan.init._init_gen3", return_value=False) as m_gen3:
                    result = run_init(non_interactive=True)
    assert m_syn.called
    assert m_portal.called
    assert m_bq.called
    assert m_gen3.called
    assert result == {
        "synapse": False, "portal": False, "bigquery": False, "gen3": False,
    }


def test_run_init_specific_service(capsys):
    """Running with services=['bigquery'] only inits bigquery."""
    from htan.init import run_init
    with mock.patch("htan.init._init_bigquery", return_value=True) as m_bq:
        result = run_init(services=["bigquery"], non_interactive=True)
    assert m_bq.called
    assert result == {"bigquery": True}


def test_run_init_portal_triggers_synapse_first(capsys):
    """Requesting portal also runs synapse first (ordering enforcement)."""
    from htan.init import run_init
    call_order = []

    def fake_synapse(**kwargs):
        call_order.append("synapse")
        return False, None

    def fake_portal(**kwargs):
        call_order.append("portal")
        return False

    with mock.patch("htan.init._init_synapse", side_effect=fake_synapse):
        with mock.patch("htan.init._init_portal", side_effect=fake_portal):
            run_init(services=["portal", "synapse"], non_interactive=True)

    assert call_order == ["synapse", "portal"]


# ---------------------------------------------------------------------------
# cli_main
# ---------------------------------------------------------------------------

def test_cli_main_status(capsys):
    """cli_main --status runs without error."""
    from htan.init import cli_main
    cli_main(["--status"])
    captured = capsys.readouterr()
    assert "Welcome" in captured.err


def test_cli_main_help(capsys):
    """cli_main --help prints usage."""
    from htan.init import cli_main
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--help"])
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# config.check_setup portal fix
# ---------------------------------------------------------------------------

def test_check_setup_uses_detect_source():
    """check_setup portal detection uses detect_source (3-tier) not just file."""
    from htan.config import check_setup
    with mock.patch("htan.config.detect_source", return_value="keychain") as m:
        status = check_setup()
    m.assert_called_once()
    assert status["portal"]["configured"] is True
    assert status["portal"]["source"] == "keychain"


def test_check_setup_portal_not_configured():
    from htan.config import check_setup
    with mock.patch("htan.config.detect_source", return_value=None):
        status = check_setup()
    assert status["portal"]["configured"] is False
    assert status["portal"]["source"] is None
