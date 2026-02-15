"""Tests for htan.files — lookup, stats, formatting, caching."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from htan.files import (
    lookup,
    stats,
    _load_mapping,
    _format_text_output,
    _format_json_output,
)


SAMPLE_MAPPING = [
    {
        "HTAN_Data_File_ID": "HTA9_1_19512",
        "name": "sample1.fastq.gz",
        "entityId": "syn12345678",
        "drs_uri": "dg.4DFC/abc-123",
        "HTAN_Center": "HTAN OHSU",
    },
    {
        "HTAN_Data_File_ID": "HTA9_1_19553",
        "name": "sample2.bam",
        "entityId": "syn87654321",
        "drs_uri": "",
        "HTAN_Center": "HTAN OHSU",
    },
    {
        "HTAN_Data_File_ID": "HTA1_1_100",
        "name": "sample3.h5ad",
        "entityId": "",
        "drs_uri": "dg.4DFC/def-456",
        "HTAN_Center": "HTAN HMS",
    },
    # Record with no file ID (should be skipped in mapping)
    {
        "name": "orphan.txt",
        "entityId": "syn99999999",
    },
]


@pytest.fixture
def mock_mapping(tmp_path):
    """Write sample mapping to a temp cache file and patch CACHE_FILE."""
    cache_file = tmp_path / "crdcgc_drs_mapping.json"
    cache_file.write_text(json.dumps(SAMPLE_MAPPING))
    with patch("htan.files.CACHE_FILE", str(cache_file)):
        yield str(cache_file)


# ===========================================================================
# _load_mapping
# ===========================================================================

def test_load_mapping_builds_dict(mock_mapping):
    mapping = _load_mapping()
    assert "HTA9_1_19512" in mapping
    assert "HTA9_1_19553" in mapping
    assert "HTA1_1_100" in mapping
    # Orphan record without HTAN_Data_File_ID should be excluded
    assert len(mapping) == 3


def test_load_mapping_skips_records_without_id(mock_mapping):
    mapping = _load_mapping()
    for key in mapping:
        assert key.startswith("HTA")


# ===========================================================================
# lookup
# ===========================================================================

def test_lookup_single_found(mock_mapping):
    results = lookup(["HTA9_1_19512"])
    assert len(results) == 1
    assert results[0]["entityId"] == "syn12345678"


def test_lookup_multiple_found(mock_mapping):
    results = lookup(["HTA9_1_19512", "HTA9_1_19553"])
    assert len(results) == 2


def test_lookup_some_missing(mock_mapping, capsys):
    results = lookup(["HTA9_1_19512", "HTA_NONEXISTENT"])
    assert len(results) == 1
    captured = capsys.readouterr()
    assert "Not found" in captured.err


def test_lookup_all_missing(mock_mapping, capsys):
    results = lookup(["HTA_NOPE1", "HTA_NOPE2"])
    assert len(results) == 0
    captured = capsys.readouterr()
    assert "Not found" in captured.err


# ===========================================================================
# stats
# ===========================================================================

def test_stats_counts(mock_mapping):
    s = stats()
    assert s["total_files"] == 3
    assert s["with_synapse_entity_id"] == 2  # HTA9 records have entityId
    assert s["with_drs_uri"] == 2  # HTA9_1_19512 and HTA1_1_100


def test_stats_files_per_center(mock_mapping):
    s = stats()
    fpc = s["files_per_center"]
    assert fpc["HTAN OHSU"] == 2
    assert fpc["HTAN HMS"] == 1


# ===========================================================================
# _format_text_output
# ===========================================================================

def test_format_text_output_basic():
    results = [
        {"HTAN_Data_File_ID": "HTA9_1_19512", "name": "test.fastq",
         "entityId": "syn123", "drs_uri": "", "HTAN_Center": "HTAN OHSU"},
    ]
    text = _format_text_output(results)
    assert "HTA9_1_19512" in text
    assert "syn123" in text
    assert "HTAN OHSU" in text


def test_format_text_output_empty():
    assert _format_text_output([]) == ""


# ===========================================================================
# _format_json_output
# ===========================================================================

def test_format_json_output_has_download_cmds():
    results = [
        {"HTAN_Data_File_ID": "HTA9_1_19512", "name": "test.fastq",
         "entityId": "syn123", "drs_uri": "dg.4DFC/abc-123", "HTAN_Center": "HTAN OHSU"},
    ]
    out = json.loads(_format_json_output(results))
    assert len(out) == 1
    assert "synapse_download_cmd" in out[0]
    assert "gen3_download_cmd" in out[0]
    assert "syn123" in out[0]["synapse_download_cmd"]
    assert "drs://" in out[0]["gen3_download_cmd"]


def test_format_json_output_no_drs():
    results = [
        {"HTAN_Data_File_ID": "HTA9_1_19512", "name": "test.fastq",
         "entityId": "syn123", "drs_uri": "", "HTAN_Center": "HTAN OHSU"},
    ]
    out = json.loads(_format_json_output(results))
    assert "gen3_download_cmd" not in out[0]
    assert "synapse_download_cmd" in out[0]


def test_format_json_output_no_entity_id():
    results = [
        {"HTAN_Data_File_ID": "HTA1_1_100", "name": "test.h5ad",
         "entityId": "", "drs_uri": "dg.4DFC/abc", "HTAN_Center": "HTAN HMS"},
    ]
    out = json.loads(_format_json_output(results))
    assert "synapse_download_cmd" not in out[0]
    assert "gen3_download_cmd" in out[0]
