"""Tests for htan.cli — command routing / dispatch logic."""

import sys
from unittest.mock import patch, MagicMock

import pytest

from htan.cli import main, _dispatch_query, _dispatch_download, _dispatch_config


# ===========================================================================
# _dispatch_query
# ===========================================================================

def test_dispatch_query_portal():
    with patch("htan.query.portal.cli_main") as mock_cli:
        _dispatch_query(["portal", "tables"])
    mock_cli.assert_called_once_with(["tables"])


def test_dispatch_query_bq():
    with patch("htan.query.bq.cli_main") as mock_cli:
        _dispatch_query(["bq", "tables"])
    mock_cli.assert_called_once_with(["tables"])


def test_dispatch_query_no_args():
    with pytest.raises(SystemExit):
        _dispatch_query([])


def test_dispatch_query_unknown_backend():
    with pytest.raises(SystemExit):
        _dispatch_query(["unknown_backend"])


# ===========================================================================
# _dispatch_download
# ===========================================================================

def test_dispatch_download_synapse():
    with patch("htan.download.synapse.cli_main") as mock_cli:
        _dispatch_download(["synapse", "syn12345678"])
    mock_cli.assert_called_once_with(["syn12345678"])


def test_dispatch_download_gen3():
    with patch("htan.download.gen3.cli_main") as mock_cli:
        _dispatch_download(["gen3", "download", "drs://dg.4DFC/abc"])
    mock_cli.assert_called_once_with(["download", "drs://dg.4DFC/abc"])


def test_dispatch_download_no_args():
    with pytest.raises(SystemExit):
        _dispatch_download([])


def test_dispatch_download_unknown_backend():
    with pytest.raises(SystemExit):
        _dispatch_download(["ftp"])


# ===========================================================================
# _dispatch_config
# ===========================================================================

def test_dispatch_config_check(capsys):
    with patch("htan.config.check_setup", return_value={"portal": "configured"}):
        _dispatch_config(["check"])
    out = capsys.readouterr().out
    assert '"ok": true' in out


def test_dispatch_config_help(capsys):
    _dispatch_config(["--help"])
    out = capsys.readouterr().out
    assert "Usage:" in out


def test_dispatch_config_init_portal():
    with patch("htan.init.cli_main") as mock_init:
        _dispatch_config(["init-portal"])
    mock_init.assert_called_once_with(["portal"])


def test_dispatch_config_unknown():
    with pytest.raises(SystemExit):
        _dispatch_config(["unknown_cmd"])


def test_dispatch_config_no_args(capsys):
    """No args defaults to 'check'."""
    with patch("htan.config.check_setup", return_value={"portal": "none"}):
        _dispatch_config([])
    out = capsys.readouterr().out
    assert '"ok": true' in out


# ===========================================================================
# main() routing
# ===========================================================================

def test_main_routes_pubs():
    with patch("htan.pubs.cli_main") as mock_cli, \
         patch.object(sys, "argv", ["htan", "pubs", "search"]):
        main()
    mock_cli.assert_called_once_with(["search"])


def test_main_routes_model():
    with patch("htan.model.cli_main") as mock_cli, \
         patch.object(sys, "argv", ["htan", "model", "components"]):
        main()
    mock_cli.assert_called_once_with(["components"])


def test_main_routes_files():
    with patch("htan.files.cli_main") as mock_cli, \
         patch.object(sys, "argv", ["htan", "files", "stats"]):
        main()
    mock_cli.assert_called_once_with(["stats"])


def test_main_routes_init():
    with patch("htan.init.cli_main") as mock_cli, \
         patch.object(sys, "argv", ["htan", "init"]):
        main()
    mock_cli.assert_called_once_with([])


def test_main_routes_query():
    with patch("htan.query.portal.cli_main") as mock_cli, \
         patch.object(sys, "argv", ["htan", "query", "portal", "tables"]):
        main()
    mock_cli.assert_called_once_with(["tables"])


def test_main_routes_download():
    with patch("htan.download.synapse.cli_main") as mock_cli, \
         patch.object(sys, "argv", ["htan", "download", "synapse", "syn123"]):
        main()
    mock_cli.assert_called_once_with(["syn123"])
