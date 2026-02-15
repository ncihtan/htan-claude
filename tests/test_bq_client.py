"""Tests for htan.query.bq — BigQueryClient, _ensure_limit, SQL safety,
and CLI dispatch."""

import re
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from htan.query.bq import (
    validate_sql_safety,
    _ensure_limit,
    BigQueryClient,
    BigQueryError,
    HTAN_DATASET,
    HTAN_DATASET_VERSIONED,
    TABLE_NAME_PATTERN,
)


# ===========================================================================
# validate_sql_safety — expanded tests
# ===========================================================================

def test_safe_with():
    safe, _ = validate_sql_safety("WITH cte AS (SELECT 1) SELECT * FROM cte")
    assert safe is True


def test_safe_explain():
    safe, _ = validate_sql_safety("EXPLAIN SELECT * FROM table")
    assert safe is True


def test_unsafe_create():
    safe, reason = validate_sql_safety("CREATE TABLE t (id INT)")
    assert safe is False
    assert "CREATE" in reason


def test_unsafe_alter():
    safe, reason = validate_sql_safety("ALTER TABLE t ADD COLUMN x INT")
    assert safe is False
    assert "ALTER" in reason


def test_unsafe_truncate():
    safe, reason = validate_sql_safety("TRUNCATE TABLE important")
    assert safe is False


def test_unsafe_merge():
    safe, reason = validate_sql_safety("MERGE INTO t USING s ON t.id = s.id")
    assert safe is False


def test_unsafe_grant():
    safe, reason = validate_sql_safety("GRANT SELECT ON table TO user")
    assert safe is False


def test_unsafe_revoke():
    safe, reason = validate_sql_safety("REVOKE SELECT ON table FROM user")
    assert safe is False


def test_unsafe_update():
    safe, reason = validate_sql_safety("UPDATE t SET x = 1")
    assert safe is False


def test_unsafe_delete():
    safe, reason = validate_sql_safety("DELETE FROM t WHERE id = 1")
    assert safe is False


def test_case_insensitive_block():
    safe, _ = validate_sql_safety("drop TABLE t")
    assert safe is False


def test_reject_unknown_start():
    safe, reason = validate_sql_safety("CALL procedure()")
    assert safe is False
    assert "must start with" in reason


# ===========================================================================
# _ensure_limit
# ===========================================================================

def test_ensure_limit_adds():
    result = _ensure_limit("SELECT * FROM t", limit=500)
    assert "LIMIT 500" in result


def test_ensure_limit_preserves_existing():
    sql = "SELECT * FROM t LIMIT 50"
    result = _ensure_limit(sql, limit=500)
    assert result == sql


def test_ensure_limit_strips_semicolon():
    result = _ensure_limit("SELECT * FROM t;", limit=100)
    assert "LIMIT 100" in result
    assert not result.rstrip().endswith(";")


# ===========================================================================
# BigQueryClient — with mocked google.cloud.bigquery
# ===========================================================================

def _make_fake_bq_module():
    """Create a mock google.cloud.bigquery module."""
    bq = MagicMock()
    mock_client = MagicMock()
    bq.Client.return_value = mock_client

    # query() returns something with .to_dataframe()
    mock_job = MagicMock()
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.__len__ = lambda self: 5
    mock_df.columns = ["col1", "col2"]
    mock_job.to_dataframe.return_value = mock_df
    mock_client.query.return_value = mock_job

    return bq, mock_client


def test_bq_client_query(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    result = client.query("SELECT * FROM t")
    mock_client.query.assert_called_once()


def test_bq_client_query_unsafe_raises(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    with pytest.raises(BigQueryError):
        client.query("DROP TABLE important")


def test_bq_client_query_dry_run(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    dry_job = MagicMock()
    dry_job.total_bytes_processed = 1000
    mock_client.query.return_value = dry_job
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    result = client.query("SELECT * FROM t", dry_run=True)
    assert result["bytes_processed"] == 1000
    assert "SELECT" in result["sql"]


def test_bq_client_list_tables(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    mock_df = MagicMock()
    mock_df.__getitem__ = lambda self, key: MagicMock(tolist=lambda: ["table_a", "table_b"])
    mock_job = MagicMock()
    mock_job.to_dataframe.return_value = mock_df
    mock_client.query.return_value = mock_job
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    tables = client.list_tables()
    sql_sent = mock_client.query.call_args[0][0]
    assert HTAN_DATASET in sql_sent


def test_bq_client_list_tables_versioned(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    mock_df = MagicMock()
    mock_df.__getitem__ = lambda self, key: MagicMock(tolist=lambda: ["table_a_r1"])
    mock_job = MagicMock()
    mock_job.to_dataframe.return_value = mock_df
    mock_client.query.return_value = mock_job
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    tables = client.list_tables(versioned=True)
    sql_sent = mock_client.query.call_args[0][0]
    assert HTAN_DATASET_VERSIONED in sql_sent


def test_bq_client_describe_table(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    mock_table = MagicMock()
    mock_table.num_rows = 500
    mock_table.num_bytes = 10000
    mock_table.description = "Demographics table"
    mock_field = MagicMock()
    mock_field.name = "HTAN_Participant_ID"
    mock_field.field_type = "STRING"
    mock_field.mode = "NULLABLE"
    mock_field.description = "Participant ID"
    mock_table.schema = [mock_field]
    mock_client.get_table.return_value = mock_table
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    info = client.describe_table("clinical_tier1_demographics")
    assert info["num_rows"] == 500
    assert len(info["schema"]) == 1
    assert info["schema"][0]["name"] == "HTAN_Participant_ID"
    # Should auto-append _current suffix
    assert "_current" in mock_client.get_table.call_args[0][0]


def test_bq_client_describe_table_invalid_name(monkeypatch):
    bq, mock_client = _make_fake_bq_module()
    monkeypatch.setattr("htan.query.bq._get_bq_module", lambda: bq)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    client = BigQueryClient(project="test-project")
    with pytest.raises(BigQueryError, match="Invalid table name"):
        client.describe_table("bad; DROP TABLE")


# ===========================================================================
# TABLE_NAME_PATTERN
# ===========================================================================

def test_table_name_pattern_valid():
    assert TABLE_NAME_PATTERN.match("clinical_tier1_demographics_current")
    assert TABLE_NAME_PATTERN.match("files")


def test_table_name_pattern_invalid():
    assert not TABLE_NAME_PATTERN.match("files; DROP")
    assert not TABLE_NAME_PATTERN.match("files--comment")
    assert not TABLE_NAME_PATTERN.match("")
