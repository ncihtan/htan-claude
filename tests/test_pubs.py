"""Unit tests for htan.pubs — grant/author constants."""

from htan.pubs import ALL_GRANTS, HTAN_AUTHORS


def test_grants_not_empty():
    assert len(ALL_GRANTS) > 10


def test_grants_format():
    for g in ALL_GRANTS:
        assert g.startswith("CA") or g.startswith("HH"), f"Unexpected grant format: {g}"


def test_authors_not_empty():
    assert len(HTAN_AUTHORS) > 10


def test_known_author_present():
    assert "Sorger PK" in HTAN_AUTHORS
    assert "Regev A" in HTAN_AUTHORS
