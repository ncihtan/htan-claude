"""Tests for htan.query.portal — formatting and parsing functions."""

from htan.query.portal import (
    parse_json_rows,
    format_text_table,
    format_output,
    _format_cell_value,
)


# --- parse_json_rows ---

def test_parse_json_rows_basic():
    text = '{"a": 1, "b": "hello"}\n{"a": 2, "b": "world"}\n'
    rows = parse_json_rows(text)
    assert len(rows) == 2
    assert rows[0] == {"a": 1, "b": "hello"}
    assert rows[1] == {"a": 2, "b": "world"}


def test_parse_json_rows_empty():
    assert parse_json_rows("") == []
    assert parse_json_rows("  \n  ") == []


def test_parse_json_rows_skips_blank_lines():
    text = '{"a": 1}\n\n{"a": 2}\n'
    rows = parse_json_rows(text)
    assert len(rows) == 2


def test_parse_json_rows_skips_error_lines():
    text = 'Code: 47. Some error\n{"a": 1}\n'
    rows = parse_json_rows(text)
    assert len(rows) == 1


# --- _format_cell_value ---

def test_format_cell_value_string():
    assert _format_cell_value("hello") == "hello"


def test_format_cell_value_list():
    result = _format_cell_value(["a", "b", "c"])
    assert "a" in result
    assert "b" in result


def test_format_cell_value_none():
    # None is converted to "None" string via str()
    assert _format_cell_value(None) == "None"


def test_format_cell_value_number():
    assert _format_cell_value(42) == "42"


# --- format_text_table ---

def test_format_text_table_basic():
    rows = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    text = format_text_table(rows)
    assert "name" in text
    assert "Alice" in text
    assert "Bob" in text


def test_format_text_table_empty():
    text = format_text_table([])
    assert text == ""


def test_format_text_table_single_row():
    rows = [{"col1": "value1"}]
    text = format_text_table(rows)
    assert "col1" in text
    assert "value1" in text


# --- format_output ---

def test_format_output_json(capsys):
    rows = [{"a": 1}, {"a": 2}]
    format_output(rows, output_format="json")
    import json
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert len(parsed) == 2


def test_format_output_text(capsys):
    rows = [{"name": "test"}]
    format_output(rows, output_format="text")
    captured = capsys.readouterr()
    assert "name" in captured.out
    assert "test" in captured.out


def test_format_output_csv(capsys):
    rows = [{"name": "Alice", "age": 30}]
    format_output(rows, output_format="csv")
    captured = capsys.readouterr()
    assert "name" in captured.out
    assert "Alice" in captured.out
