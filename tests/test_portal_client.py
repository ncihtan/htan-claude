"""Tests for htan.query.portal — PortalClient methods and clickhouse_query."""

import json
from unittest.mock import patch, MagicMock
import urllib.error

import pytest

from htan.query.portal import (
    PortalClient,
    PortalError,
    clickhouse_query,
    discover_database,
)


FAKE_CONFIG = {"host": "ch.example.com", "port": "443", "user": "u", "password": "p"}


# ===========================================================================
# PortalClient.query
# ===========================================================================

def test_portal_client_query_basic():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = '{"atlas_name":"HTAN HMS","n":"42"}\n'
        rows = client.query("SELECT atlas_name, count() as n FROM files GROUP BY atlas_name")
    assert len(rows) == 1
    assert rows[0]["n"] == "42"


def test_portal_client_query_unsafe_sql():
    client = PortalClient(config=FAKE_CONFIG)
    with pytest.raises(PortalError, match="read-only"):
        client.query("DROP TABLE files")


def test_portal_client_query_applies_limit():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = ""
        client.query("SELECT * FROM files")
        sql_sent = mock_ch.call_args[0][0]
        assert "LIMIT" in sql_sent


# ===========================================================================
# PortalClient.find_files
# ===========================================================================

def test_portal_client_find_files_with_organ_filter():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = '{"DataFileID":"HTA1_1_1","Filename":"test.fastq"}\n'
        rows = client.find_files(organ="Breast")
    sql_sent = mock_ch.call_args[0][0]
    assert "arrayExists" in sql_sent  # organType is an array column
    assert "Breast" in sql_sent


def test_portal_client_find_files_with_data_file_id():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = '{"DataFileID":"HTA9_1_19512"}\n'
        rows = client.find_files(data_file_id="HTA9_1_19512")
    sql_sent = mock_ch.call_args[0][0]
    assert "DataFileID IN" in sql_sent
    assert "HTA9_1_19512" in sql_sent


def test_portal_client_find_files_no_filters():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = ""
        client.find_files()
    sql_sent = mock_ch.call_args[0][0]
    assert "WHERE" not in sql_sent


def test_portal_client_find_files_multiple_filters():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = ""
        client.find_files(organ="Breast", assay="scRNA-seq", atlas="HTAN OHSU")
    sql_sent = mock_ch.call_args[0][0]
    assert "Breast" in sql_sent
    assert "scRNA-seq" in sql_sent
    assert "HTAN OHSU" in sql_sent


def test_portal_client_find_files_escapes_input():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = ""
        client.find_files(data_file_id="O'Brien")
    sql_sent = mock_ch.call_args[0][0]
    assert "\\'" in sql_sent  # single quote is escaped


# ===========================================================================
# PortalClient.list_tables
# ===========================================================================

def test_portal_client_list_tables():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = "files\ndemographics\ncases\n"
        tables = client.list_tables()
    assert tables == ["cases", "demographics", "files"]  # sorted


# ===========================================================================
# PortalClient.describe_table
# ===========================================================================

def test_portal_client_describe_table():
    client = PortalClient(config=FAKE_CONFIG)
    schema_resp = '{"name":"DataFileID","type":"String","default_expression":"","comment":""}\n'
    count_resp = '{"cnt":"1234"}\n'
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.side_effect = [schema_resp, count_resp]
        info = client.describe_table("files")
    assert info["table"] == "files"
    assert info["row_count"] == "1234"
    assert len(info["columns"]) == 1
    assert info["columns"][0]["name"] == "DataFileID"


def test_portal_client_describe_table_invalid_name():
    client = PortalClient(config=FAKE_CONFIG)
    with pytest.raises(ValueError, match="Invalid table name"):
        client.describe_table("files; DROP TABLE")


# ===========================================================================
# PortalClient.get_demographics / get_diagnosis
# ===========================================================================

def test_portal_client_get_demographics():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = '{"Gender":"male"}\n'
        rows = client.get_demographics(atlas="HTAN OHSU")
    assert len(rows) == 1
    sql_sent = mock_ch.call_args[0][0]
    assert "demographics" in sql_sent


def test_portal_client_get_diagnosis():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = '{"Primary_Diagnosis":"Breast cancer"}\n'
        rows = client.get_diagnosis(organ="Breast")
    assert len(rows) == 1


# ===========================================================================
# PortalClient.get_manifest
# ===========================================================================

def test_portal_client_get_manifest():
    client = PortalClient(config=FAKE_CONFIG)
    with patch("htan.query.portal.discover_database", return_value="htan_v1"), \
         patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = '{"DataFileID":"HTA9_1_19512","synapseId":"syn123"}\n'
        rows = client.get_manifest(["HTA9_1_19512"])
    assert len(rows) == 1
    sql_sent = mock_ch.call_args[0][0]
    assert "HTA9_1_19512" in sql_sent


# ===========================================================================
# clickhouse_query error handling
# ===========================================================================

def test_clickhouse_query_http_error():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"Syntax error"
    http_err = urllib.error.HTTPError("http://x", 400, "Bad Request", {}, mock_resp)
    with patch("htan.query.portal.urllib.request.urlopen", side_effect=http_err), \
         patch("htan.query.portal._make_ssl_context"):
        with pytest.raises(PortalError, match="ClickHouse HTTP 400"):
            clickhouse_query("SELECT 1", config=FAKE_CONFIG)


def test_clickhouse_query_url_error():
    with patch("htan.query.portal.urllib.request.urlopen",
               side_effect=urllib.error.URLError("Connection refused")), \
         patch("htan.query.portal._make_ssl_context"):
        with pytest.raises(PortalError, match="Could not connect"):
            clickhouse_query("SELECT 1", config=FAKE_CONFIG)


def test_clickhouse_query_timeout():
    with patch("htan.query.portal.urllib.request.urlopen",
               side_effect=TimeoutError()), \
         patch("htan.query.portal._make_ssl_context"):
        with pytest.raises(PortalError, match="timed out"):
            clickhouse_query("SELECT 1", config=FAKE_CONFIG)


def test_clickhouse_query_hint_not_equal():
    """Error message containing != should suggest <> hint."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"Unrecognized token: !="
    http_err = urllib.error.HTTPError("http://x", 400, "Bad Request", {}, mock_resp)
    with patch("htan.query.portal.urllib.request.urlopen", side_effect=http_err), \
         patch("htan.query.portal._make_ssl_context"):
        with pytest.raises(PortalError) as exc_info:
            clickhouse_query("SELECT * WHERE x != 1", config=FAKE_CONFIG)
        assert any("<>" in h for h in exc_info.value.hints)


# ===========================================================================
# discover_database
# ===========================================================================

def test_discover_database_finds_latest():
    with patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = "htan_v1\nhtan_v2\nhtan_v3\n"
        db = discover_database(config={**FAKE_CONFIG, "database": ""})
    assert db == "htan_v3"


def test_discover_database_falls_back_to_config():
    with patch("htan.query.portal.clickhouse_query", side_effect=Exception("fail")):
        db = discover_database(config={**FAKE_CONFIG, "default_database": "htan_fallback"})
    assert db == "htan_fallback"


def test_discover_database_empty_response():
    with patch("htan.query.portal.clickhouse_query") as mock_ch:
        mock_ch.return_value = ""
        db = discover_database(config={**FAKE_CONFIG, "default_database": "htan_default"})
    assert db == "htan_default"
