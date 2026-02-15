"""Tests for htan.download.synapse — Synapse ID validation."""

import pytest
from htan.download.synapse import _validate_synapse_id, SYNAPSE_ID_PATTERN


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


def test_pattern_matches_valid():
    assert SYNAPSE_ID_PATTERN.match("syn26535909")
    assert SYNAPSE_ID_PATTERN.match("syn1")


def test_pattern_rejects_invalid():
    assert not SYNAPSE_ID_PATTERN.match("syn")
    assert not SYNAPSE_ID_PATTERN.match("syn12 34")
    assert not SYNAPSE_ID_PATTERN.match("abc123")
