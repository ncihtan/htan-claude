"""Tests for htan.pubs — search, fetch, fulltext, format_article_text, eutils_request."""

import json
from unittest.mock import patch, MagicMock

import pytest

from htan.pubs import (
    eutils_request,
    search,
    fetch,
    fulltext,
    format_article_text,
    EUTILS_BASE,
)


# ===========================================================================
# eutils_request
# ===========================================================================

def test_eutils_request_success():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"result": "ok"}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("htan.pubs.urllib.request.urlopen", return_value=mock_resp), \
         patch("htan.pubs.time.sleep"):
        result = eutils_request("esearch.fcgi", {"db": "pubmed", "term": "test"})
    assert result == '{"result": "ok"}'


def test_eutils_request_adds_tool_params():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"ok"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("htan.pubs.urllib.request.urlopen", return_value=mock_resp) as mock_open, \
         patch("htan.pubs.time.sleep"):
        eutils_request("esearch.fcgi", {"db": "pubmed"})
    url_called = mock_open.call_args[0][0].full_url
    assert "tool=htan_skill" in url_called
    assert "email=" in url_called


# ===========================================================================
# search
# ===========================================================================

MOCK_ESEARCH_RESPONSE = json.dumps({
    "esearchresult": {
        "count": "2",
        "idlist": ["12345678", "87654321"],
    }
})

MOCK_EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Spatial transcriptomics of breast cancer</ArticleTitle>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>AB</Initials></Author>
          <Author><LastName>Sorger</LastName><Initials>PK</Initials></Author>
        </AuthorList>
        <Journal>
          <Title>Nature</Title>
          <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
        </Journal>
        <Abstract>
          <AbstractText>This is the abstract.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1038/test-doi</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>87654321</PMID>
      <Article>
        <ArticleTitle>Single-cell atlas</ArticleTitle>
        <AuthorList>
          <Author><LastName>Regev</LastName><Initials>A</Initials></Author>
        </AuthorList>
        <Journal>
          <Title>Science</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList></ArticleIdList></PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _mock_eutils(endpoint, params, timeout=60):
    """Mock eutils_request that returns search or fetch data."""
    if "esearch" in endpoint:
        return MOCK_ESEARCH_RESPONSE
    elif "efetch" in endpoint:
        return MOCK_EFETCH_XML
    elif "esummary" in endpoint:
        return json.dumps({"result": {}})
    return ""


def test_search_returns_articles():
    with patch("htan.pubs.eutils_request", side_effect=_mock_eutils):
        articles = search(keyword="spatial")
    assert len(articles) == 2
    assert articles[0]["pmid"] == "12345678"
    assert articles[0]["title"] == "Spatial transcriptomics of breast cancer"


def test_search_empty_results():
    empty_response = json.dumps({"esearchresult": {"count": "0", "idlist": []}})
    with patch("htan.pubs.eutils_request", return_value=empty_response):
        articles = search(keyword="nonexistent_thing_xyz")
    assert articles == []


def test_search_with_author():
    with patch("htan.pubs.eutils_request", side_effect=_mock_eutils):
        articles = search(author="Sorger PK")
    assert len(articles) == 2


def test_search_with_year():
    with patch("htan.pubs.eutils_request", side_effect=_mock_eutils):
        articles = search(year="2024")
    assert len(articles) == 2


# ===========================================================================
# fetch
# ===========================================================================

def test_fetch_single_pmid():
    with patch("htan.pubs.eutils_request", return_value=MOCK_EFETCH_XML):
        articles = fetch("12345678")
    assert len(articles) == 2  # XML has 2 articles


def test_fetch_list_of_pmids():
    with patch("htan.pubs.eutils_request", return_value=MOCK_EFETCH_XML):
        articles = fetch(["12345678", "87654321"])
    assert len(articles) >= 1


def test_fetch_empty_list():
    articles = fetch([])
    assert articles == []


def test_fetch_extracts_fields():
    with patch("htan.pubs.eutils_request", return_value=MOCK_EFETCH_XML):
        articles = fetch(["12345678"])
    art = next(a for a in articles if a["pmid"] == "12345678")
    assert "Sorger PK" in art["authors"]
    assert art["journal"] == "Nature"
    assert art["year"] == "2024"
    assert art["doi"] == "10.1038/test-doi"
    assert art["abstract"] == "This is the abstract."


# ===========================================================================
# fulltext
# ===========================================================================

def test_fulltext_returns_articles():
    esearch_resp = json.dumps({
        "esearchresult": {"count": "1", "idlist": ["PMC123456"]}
    })
    esummary_resp = json.dumps({
        "result": {
            "PMC123456": {
                "title": "A PMC article",
                "fulljournalname": "Nature Methods",
                "pubdate": "2024 Jan",
                "articleids": [{"idtype": "pmid", "value": "99999"}],
                "authors": [{"name": "Author A"}, {"name": "Author B"}],
            }
        }
    })

    def mock_eutils(endpoint, params, timeout=60):
        if "esearch" in endpoint:
            return esearch_resp
        return esummary_resp

    with patch("htan.pubs.eutils_request", side_effect=mock_eutils):
        articles = fulltext("tumor microenvironment")
    assert len(articles) == 1
    assert articles[0]["pmc_id"] == "PMCPMC123456"
    assert articles[0]["title"] == "A PMC article"


def test_fulltext_empty_results():
    empty_response = json.dumps({"esearchresult": {"count": "0", "idlist": []}})
    with patch("htan.pubs.eutils_request", return_value=empty_response):
        articles = fulltext("nothing matches xyz")
    assert articles == []


# ===========================================================================
# format_article_text
# ===========================================================================

def test_format_article_text_full():
    article = {
        "pmid": "12345678",
        "title": "Test Article Title",
        "authors": ["Smith AB", "Jones CD"],
        "journal": "Nature",
        "year": "2024",
        "doi": "10.1038/test",
        "abstract": "This is the abstract text.",
    }
    text = format_article_text(article)
    assert "PMID: 12345678" in text
    assert "Test Article Title" in text
    assert "Smith AB" in text
    assert "Nature" in text
    assert "doi.org" in text
    assert "abstract text" in text


def test_format_article_text_pmc():
    article = {
        "pmc_id": "PMC12345",
        "title": "PMC Article",
        "authors": [],
        "journal": "Science",
        "year": "2023",
    }
    text = format_article_text(article)
    assert "PMC: PMC12345" in text


def test_format_article_text_many_authors():
    article = {
        "pmid": "1",
        "title": "Test",
        "authors": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
        "journal": "J",
        "year": "2024",
    }
    text = format_article_text(article)
    assert "+2 more" in text


def test_format_article_text_long_abstract():
    article = {
        "pmid": "1",
        "title": "Test",
        "authors": [],
        "journal": "J",
        "year": "2024",
        "abstract": "x" * 500,
    }
    text = format_article_text(article)
    assert "..." in text


def test_format_article_text_missing_doi():
    article = {
        "pmid": "1",
        "title": "Test",
        "authors": [],
        "journal": "J",
        "year": "2024",
        "doi": "",
    }
    text = format_article_text(article)
    assert "DOI" not in text


def test_format_article_text_no_abstract():
    article = {
        "pmid": "1",
        "title": "Test",
        "authors": [],
        "journal": "J",
        "year": "2024",
    }
    text = format_article_text(article)
    assert "Abstract" not in text
