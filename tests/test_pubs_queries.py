"""Tests for htan.pubs — query building and article parsing."""

from htan.pubs import (
    build_grant_query,
    build_author_query,
    build_search_query,
    ALL_GRANTS,
    HTAN_AUTHORS,
    _parse_article_xml,
)
import xml.etree.ElementTree as ET


# --- build_grant_query ---

def test_build_grant_query_includes_all_grants():
    q = build_grant_query()
    for g in ALL_GRANTS:
        assert f"{g}[gr]" in q


def test_build_grant_query_uses_or():
    q = build_grant_query()
    assert " OR " in q


# --- build_author_query ---

def test_build_author_query_all():
    q = build_author_query()
    assert "Sorger PK[LASTAU]" in q
    assert " OR " in q


def test_build_author_query_specific():
    q = build_author_query("Sorger PK")
    assert q == "Sorger PK[LASTAU]"
    assert " OR " not in q


# --- build_search_query ---

def test_build_search_query_basic():
    q = build_search_query()
    assert "[gr]" in q
    assert "[LASTAU]" in q


def test_build_search_query_with_keyword():
    q = build_search_query(keyword="spatial transcriptomics")
    assert "spatial transcriptomics" in q


def test_build_search_query_with_year():
    q = build_search_query(year="2024")
    assert "2024[pdat]" in q


def test_build_search_query_with_author():
    q = build_search_query(author="Sorger PK")
    assert "Sorger PK[LASTAU]" in q
    # Should not include all authors, just the specified one
    assert "Ding L" not in q


def test_build_search_query_all_filters():
    q = build_search_query(keyword="scRNA-seq", author="Sorger PK", year="2023")
    assert "scRNA-seq" in q
    assert "Sorger PK[LASTAU]" in q
    assert "2023[pdat]" in q


# --- _parse_article_xml ---

def test_parse_article_xml_basic():
    xml_str = """
    <PubmedArticle>
      <MedlineCitation>
        <PMID>12345678</PMID>
        <Article>
          <ArticleTitle>Test Title</ArticleTitle>
          <Journal>
            <Title>Test Journal</Title>
            <JournalIssue>
              <PubDate><Year>2024</Year></PubDate>
            </JournalIssue>
          </Journal>
          <AuthorList>
            <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
          </AuthorList>
          <Abstract><AbstractText>Test abstract.</AbstractText></Abstract>
        </Article>
      </MedlineCitation>
      <PubmedData>
        <ArticleIdList>
          <ArticleId IdType="doi">10.1234/test</ArticleId>
        </ArticleIdList>
      </PubmedData>
    </PubmedArticle>
    """
    elem = ET.fromstring(xml_str)
    article = _parse_article_xml(elem)
    assert article["pmid"] == "12345678"
    assert article["title"] == "Test Title"
    assert article["journal"] == "Test Journal"
    assert article["year"] == "2024"
    assert "Smith J" in article["authors"]
    assert article["doi"] == "10.1234/test"
    assert "Test abstract" in article["abstract"]


def test_parse_article_xml_missing_fields():
    xml_str = """
    <PubmedArticle>
      <MedlineCitation>
        <PMID>99999999</PMID>
        <Article>
          <ArticleTitle>Minimal Article</ArticleTitle>
          <Journal>
            <Title>Some Journal</Title>
            <JournalIssue><PubDate></PubDate></JournalIssue>
          </Journal>
        </Article>
      </MedlineCitation>
    </PubmedArticle>
    """
    elem = ET.fromstring(xml_str)
    article = _parse_article_xml(elem)
    assert article["pmid"] == "99999999"
    assert article["title"] == "Minimal Article"
    assert article["authors"] == []
    assert article["abstract"] == ""
