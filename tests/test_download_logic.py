"""Tests for htan.download.synapse and htan.download.gen3 — download/resolve
logic beyond validation (which is already tested)."""

import os
from unittest.mock import patch, MagicMock

import pytest

from htan.download.gen3 import (
    download as gen3_download,
    resolve as gen3_resolve,
    _get_gen3_auth,
    _validate_drs_uri,
)
from htan.download.synapse import (
    download as synapse_download,
    _validate_synapse_id,
    _get_synapse_client,
)


# ===========================================================================
# gen3 — download dry run
# ===========================================================================

def test_gen3_download_dry_run(capsys):
    result = gen3_download("drs://dg.4DFC/abc-123", dry_run=True)
    assert result is None
    err = capsys.readouterr().err
    assert "Dry run" in err
    assert "abc-123" in err


def test_gen3_download_dry_run_invalid_uri():
    with pytest.raises(ValueError, match="Invalid DRS URI"):
        gen3_download("not-a-drs-uri", dry_run=True)


# ===========================================================================
# gen3 — resolve
# ===========================================================================

def test_gen3_resolve_invalid_uri():
    with pytest.raises(ValueError, match="Invalid DRS URI"):
        gen3_resolve("bad-uri")


# ===========================================================================
# gen3 — _get_gen3_auth
# ===========================================================================

def test_get_gen3_auth_missing_creds_file():
    with pytest.raises(ValueError, match="not found"):
        _get_gen3_auth("/nonexistent/path/credentials.json")


def test_get_gen3_auth_no_gen3_package():
    """If gen3 not installed, should exit."""
    with patch.dict("sys.modules", {"gen3": None, "gen3.auth": None}), \
         patch("builtins.__import__", side_effect=ImportError("no gen3")):
        with pytest.raises(SystemExit):
            _get_gen3_auth()


# ===========================================================================
# synapse — download dry_run not directly testable (needs synapseclient),
# but we can test validation path
# ===========================================================================

def test_synapse_download_invalid_id():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        synapse_download("not-a-syn-id")


def test_synapse_download_validates_before_network(tmp_path):
    """Validate ID validation runs before any network/synapse calls."""
    out_dir = tmp_path / "new_subdir"
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        synapse_download("BAD_ID", output_dir=str(out_dir))


# ===========================================================================
# synapse — _get_synapse_client
# ===========================================================================

def test_get_synapse_client_no_package():
    """If synapseclient not installed, should exit."""
    with patch.dict("sys.modules", {"synapseclient": None}), \
         patch("builtins.__import__", side_effect=ImportError("no synapseclient")):
        with pytest.raises(SystemExit):
            _get_synapse_client()


# ===========================================================================
# gen3 CLI — dry run paths
# ===========================================================================

def test_gen3_cli_download_dry_run():
    from htan.download.gen3 import cli_main
    cli_main(["download", "drs://dg.4DFC/test-guid", "--dry-run"])


def test_gen3_cli_resolve_dry_run():
    from htan.download.gen3 import cli_main
    cli_main(["resolve", "drs://dg.4DFC/test-guid", "--dry-run"])


# ===========================================================================
# synapse CLI — help
# ===========================================================================

def test_synapse_cli_help():
    from htan.download.synapse import cli_main
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--help"])
    assert exc_info.value.code == 0
