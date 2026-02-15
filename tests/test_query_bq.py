"""Unit tests for htan.query.bq — SQL safety validation."""

from htan.query.bq import validate_sql_safety


def test_safe_select():
    safe, reason = validate_sql_safety("SELECT * FROM table LIMIT 10")
    assert safe is True


def test_unsafe_drop():
    safe, reason = validate_sql_safety("DROP TABLE important")
    assert safe is False
    assert "DROP" in reason


def test_unsafe_insert():
    safe, reason = validate_sql_safety("INSERT INTO table VALUES (1)")
    assert safe is False
