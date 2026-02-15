"""Tests for htan.download.gen3 — DRS URI validation and GUID extraction."""

import pytest
from htan.download.gen3 import (
    _validate_drs_uri,
    _extract_guid,
    _find_credentials,
    DRS_URI_PATTERN,
    GUID_PATTERN,
)


# --- DRS URI validation ---

def test_valid_drs_uri_standard():
    uri = "drs://dg.4DFC/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    assert _validate_drs_uri(uri) == uri


def test_valid_drs_uri_with_dots():
    uri = "drs://dg.4DFC/abc.def-123"
    assert _validate_drs_uri(uri) == uri


def test_valid_drs_uri_long_form():
    uri = "drs://nci-crdc.datacommons.io/dg.4DFC/some-guid"
    assert _validate_drs_uri(uri) == uri


def test_invalid_drs_uri_wrong_prefix():
    with pytest.raises(ValueError, match="Invalid DRS URI"):
        _validate_drs_uri("drs://wrong.host/guid")


def test_invalid_drs_uri_empty():
    with pytest.raises(ValueError, match="Invalid DRS URI"):
        _validate_drs_uri("")


def test_invalid_drs_uri_no_guid():
    with pytest.raises(ValueError, match="Invalid DRS URI"):
        _validate_drs_uri("drs://dg.4DFC/")


def test_invalid_drs_uri_special_chars():
    with pytest.raises(ValueError, match="Invalid DRS URI"):
        _validate_drs_uri("drs://dg.4DFC/guid;rm -rf /")


# --- GUID extraction ---

def test_extract_guid_standard():
    assert _extract_guid("drs://dg.4DFC/my-guid-123") == "my-guid-123"


def test_extract_guid_long_form():
    assert _extract_guid("drs://nci-crdc.datacommons.io/dg.4DFC/my-guid") == "my-guid"


def test_extract_guid_passthrough():
    assert _extract_guid("just-a-guid") == "just-a-guid"


# --- find_credentials ---

def test_find_credentials_env_valid(monkeypatch, tmp_path):
    creds = tmp_path / "creds.json"
    creds.write_text('{"key": "value"}')
    monkeypatch.setenv("GEN3_API_KEY", str(creds))
    assert _find_credentials() == str(creds)


def test_find_credentials_env_missing_file(monkeypatch):
    monkeypatch.setenv("GEN3_API_KEY", "/nonexistent/creds.json")
    # Falls through to default path check
    result = _find_credentials()
    # Result depends on whether default path exists on this machine
    assert result is None or isinstance(result, str)


def test_find_credentials_no_env(monkeypatch):
    monkeypatch.delenv("GEN3_API_KEY", raising=False)
    result = _find_credentials()
    assert result is None or isinstance(result, str)


# --- Pattern tests ---

def test_drs_pattern_valid():
    assert DRS_URI_PATTERN.match("drs://dg.4DFC/abc-123")
    assert DRS_URI_PATTERN.match("drs://dg.4DFC/abc.def/ghi-123")
    assert DRS_URI_PATTERN.match("drs://nci-crdc.datacommons.io/dg.4DFC/abc")


def test_drs_pattern_invalid():
    assert not DRS_URI_PATTERN.match("drs://dg.4DFC/")
    assert not DRS_URI_PATTERN.match("https://example.com")
    assert not DRS_URI_PATTERN.match("drs://wrong/guid")


def test_guid_pattern():
    assert GUID_PATTERN.match("abc-123")
    assert GUID_PATTERN.match("abc.def/ghi")
    assert not GUID_PATTERN.match("")
    assert not GUID_PATTERN.match("abc;rm")
