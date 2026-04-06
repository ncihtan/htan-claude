"""Tests for htan.upload.synapse — validation, annotation parsing, and upload logic."""

import os
import pytest
from unittest.mock import MagicMock, patch

from htan.upload.synapse import (
    _validate_synapse_id,
    _parse_annotations,
    _collect_paths_from_target,
    upload,
    upload_bulk,
    SYNAPSE_ID_PATTERN,
)


# ===========================================================================
# _validate_synapse_id
# ===========================================================================

def test_valid_synapse_id():
    assert _validate_synapse_id("syn12345678") == "syn12345678"


def test_valid_synapse_id_short():
    assert _validate_synapse_id("syn1") == "syn1"


def test_invalid_synapse_id_no_prefix():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        _validate_synapse_id("12345678")


def test_invalid_synapse_id_wrong_prefix():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        _validate_synapse_id("SYN12345678")


def test_invalid_synapse_id_letters():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        _validate_synapse_id("synABCDEF")


def test_invalid_synapse_id_empty():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        _validate_synapse_id("")


# ===========================================================================
# _parse_annotations
# ===========================================================================

def test_parse_annotations_valid():
    result = _parse_annotations(["assay=scRNA-seq", "batch=2024Q1"])
    assert result == {"assay": "scRNA-seq", "batch": "2024Q1"}


def test_parse_annotations_single():
    result = _parse_annotations(["key=value"])
    assert result == {"key": "value"}


def test_parse_annotations_value_with_equals():
    # Value can contain '=' — only first '=' is the separator
    result = _parse_annotations(["url=http://example.com?a=1"])
    assert result == {"url": "http://example.com?a=1"}


def test_parse_annotations_empty_list():
    assert _parse_annotations([]) == {}


def test_parse_annotations_missing_equals():
    with pytest.raises(ValueError, match="Annotation must be key=value"):
        _parse_annotations(["badvalue"])


def test_parse_annotations_whitespace_stripped():
    result = _parse_annotations([" key = value "])
    assert result == {"key": "value"}


# ===========================================================================
# upload — validation (no network)
# ===========================================================================

def test_upload_invalid_parent_id():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        upload("somefile.csv", parent_id="notasynid")


def test_upload_file_not_found():
    with pytest.raises(FileNotFoundError, match="File not found"):
        upload("/nonexistent/path/file.csv", parent_id="syn12345678")


def test_upload_path_is_directory(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        upload(str(tmp_path), parent_id="syn12345678")


def test_upload_annotations_not_dict():
    with pytest.raises(ValueError, match="annotations must be a dict"):
        # We need a real file for this to get past the file check
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            upload(f.name, parent_id="syn12345678", annotations=["not", "a", "dict"])


def test_upload_dry_run(tmp_path, capsys):
    test_file = tmp_path / "results.csv"
    test_file.write_text("a,b,c\n1,2,3\n")

    result = upload(
        str(test_file),
        parent_id="syn12345678",
        annotations={"assay": "scRNA-seq"},
        dry_run=True,
    )

    assert result is None
    err = capsys.readouterr().err
    assert "Dry run" in err
    assert "results.csv" in err
    assert "syn12345678" in err
    assert "assay=scRNA-seq" in err


def test_upload_dry_run_no_annotations(tmp_path, capsys):
    test_file = tmp_path / "data.tsv"
    test_file.write_text("col1\tval1\n")

    result = upload(str(test_file), parent_id="syn99999", dry_run=True)

    assert result is None
    err = capsys.readouterr().err
    assert "Dry run" in err
    assert "data.tsv" in err


# ===========================================================================
# upload_bulk — validation (no network)
# ===========================================================================

def test_upload_bulk_dry_run(tmp_path, capsys):
    files = []
    for name in ["a.csv", "b.csv", "c.csv"]:
        f = tmp_path / name
        f.write_text("data\n")
        files.append(str(f))

    results = upload_bulk(files, parent_id="syn12345678", dry_run=True)

    assert results == [None, None, None]
    err = capsys.readouterr().err
    assert "[1/3]" in err
    assert "[3/3]" in err


def test_upload_bulk_empty_paths(capsys):
    results = upload_bulk([], parent_id="syn12345678", dry_run=True)
    assert results == []
    err = capsys.readouterr().err
    assert "No files" in err


def test_upload_bulk_file_not_found():
    with pytest.raises(FileNotFoundError):
        upload_bulk(["/nonexistent/file.csv"], parent_id="syn12345678", dry_run=True)


def test_upload_bulk_invalid_parent():
    with pytest.raises(ValueError, match="Invalid Synapse ID"):
        upload_bulk([], parent_id="notvalid")


# ===========================================================================
# _collect_paths_from_target
# ===========================================================================

def test_collect_from_directory(tmp_path):
    (tmp_path / "file1.csv").write_text("a")
    (tmp_path / "file2.tsv").write_text("b")
    (tmp_path / "subdir").mkdir()  # should be excluded

    paths = _collect_paths_from_target(str(tmp_path))
    names = [os.path.basename(p) for p in paths]
    assert "file1.csv" in names
    assert "file2.tsv" in names
    assert "subdir" not in names


def test_collect_from_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="no files"):
        _collect_paths_from_target(str(tmp_path))


def test_collect_from_txt_manifest(tmp_path):
    f1 = tmp_path / "a.csv"
    f2 = tmp_path / "b.csv"
    f1.write_text("data")
    f2.write_text("data")

    manifest = tmp_path / "manifest.txt"
    manifest.write_text(f"{f1}\n{f2}\n")

    paths = _collect_paths_from_target(str(manifest))
    assert str(f1) in paths
    assert str(f2) in paths


def test_collect_from_csv_manifest(tmp_path):
    f1 = tmp_path / "x.csv"
    f1.write_text("data")

    manifest = tmp_path / "manifest.csv"
    manifest.write_text(f"{f1}\n")

    paths = _collect_paths_from_target(str(manifest))
    assert str(f1) in paths


def test_collect_from_empty_manifest(tmp_path):
    manifest = tmp_path / "empty.txt"
    manifest.write_text("\n\n")

    with pytest.raises(ValueError, match="empty"):
        _collect_paths_from_target(str(manifest))


def test_collect_wrong_manifest_extension(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("/some/path\n")

    with pytest.raises(ValueError, match="Manifest must be a .txt or .csv"):
        _collect_paths_from_target(str(manifest))


def test_collect_nonexistent_target():
    with pytest.raises(ValueError, match="does not exist"):
        _collect_paths_from_target("/nonexistent/path")
