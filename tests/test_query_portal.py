"""Unit tests for htan.query.portal — SQL validation, helpers, PortalClient."""

import pytest
from htan.query.portal import (
    normalize_sql,
    validate_sql_safety,
    validate_table_name,
    escape_sql_string,
    ensure_limit,
    build_where_clauses,
    FILES_ARRAY_COLUMNS,
    PortalClient,
    PortalError,
)


# --- normalize_sql ---

def test_normalize_sql_replaces_ne():
    assert "<>" in normalize_sql("SELECT * FROM t WHERE x != 1")


def test_normalize_sql_replaces_escaped_ne():
    assert "<>" in normalize_sql("SELECT * FROM t WHERE x \\!= 1")


def test_normalize_sql_preserves_valid():
    sql = "SELECT * FROM t WHERE x <> 1"
    assert normalize_sql(sql) == sql


# --- validate_sql_safety ---

def test_safe_select():
    safe, reason = validate_sql_safety("SELECT * FROM files LIMIT 10")
    assert safe is True


def test_safe_with():
    safe, reason = validate_sql_safety("WITH cte AS (SELECT 1) SELECT * FROM cte")
    assert safe is True


def test_safe_show():
    safe, reason = validate_sql_safety("SHOW TABLES")
    assert safe is True


def test_safe_describe():
    safe, reason = validate_sql_safety("DESCRIBE files")
    assert safe is True


def test_unsafe_delete():
    safe, reason = validate_sql_safety("DELETE FROM files WHERE 1=1")
    assert safe is False
    assert "DELETE" in reason


def test_unsafe_drop():
    safe, reason = validate_sql_safety("DROP TABLE files")
    assert safe is False


def test_unsafe_insert():
    safe, reason = validate_sql_safety("INSERT INTO files VALUES (1)")
    assert safe is False


def test_unsafe_update():
    safe, reason = validate_sql_safety("UPDATE files SET x=1")
    assert safe is False


def test_unsafe_truncate():
    safe, reason = validate_sql_safety("TRUNCATE TABLE files")
    assert safe is False


def test_reject_unknown_start():
    safe, reason = validate_sql_safety("CALL some_proc()")
    assert safe is False


# --- validate_table_name ---

def test_valid_table_name():
    # validate_table_name returns the name on success
    assert validate_table_name("files") == "files"
    assert validate_table_name("demographics") == "demographics"
    assert validate_table_name("clinical_tier1_demographics_current")


def test_invalid_table_name():
    with pytest.raises(ValueError):
        validate_table_name("files; DROP TABLE")
    with pytest.raises(ValueError):
        validate_table_name("files--comment")
    with pytest.raises(ValueError):
        validate_table_name("")


# --- escape_sql_string ---

def test_escape_normal_string():
    assert escape_sql_string("Breast") == "Breast"


def test_escape_single_quote():
    assert "\\'" in escape_sql_string("O'Brien")


def test_escape_backslash():
    assert "\\\\" in escape_sql_string("path\\to")


# --- ensure_limit ---

def test_adds_limit_when_missing():
    result = ensure_limit("SELECT * FROM files", limit=100)
    assert "LIMIT 100" in result


def test_preserves_existing_limit():
    sql = "SELECT * FROM files LIMIT 50"
    result = ensure_limit(sql, limit=100)
    assert result == sql


def test_strips_trailing_semicolon():
    result = ensure_limit("SELECT * FROM files;", limit=100)
    assert "LIMIT 100" in result
    assert not result.rstrip().endswith(";")


# --- build_where_clauses ---

def test_basic_filter():
    clauses = build_where_clauses({"atlas_name": "HTAN HMS"})
    assert len(clauses) == 1
    assert "atlas_name" in clauses[0]
    assert "HTAN HMS" in clauses[0]


def test_none_values_skipped():
    clauses = build_where_clauses({"atlas_name": None, "organ": "Breast"})
    assert len(clauses) == 1
    assert "organ" in clauses[0].lower() or "Breast" in clauses[0]


def test_array_column_uses_arrayexists():
    clauses = build_where_clauses(
        {"organType": "Breast"},
        array_columns=FILES_ARRAY_COLUMNS,
    )
    assert len(clauses) == 1
    assert "arrayExists" in clauses[0]


def test_regular_column_uses_ilike():
    clauses = build_where_clauses(
        {"atlas_name": "HTAN HMS"},
        array_columns=FILES_ARRAY_COLUMNS,
    )
    assert len(clauses) == 1
    assert "ILIKE" in clauses[0]


# --- PortalClient instantiation ---

def test_portal_client_creates():
    client = PortalClient(config={"host": "x", "port": "443", "user": "u", "password": "p"})
    assert client is not None


def test_portal_error_hints():
    err = PortalError("test error", hints=["hint1", "hint2"])
    assert str(err) == "test error"
    assert len(err.hints) == 2
