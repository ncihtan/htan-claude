"""Search HTAN publications on PubMed and PubMed Central.

Uses NCBI E-utilities REST API — no external dependencies required (stdlib only).

Usage as library:
    from htan.pubs import search, fetch, fulltext
    articles = search(keyword="spatial transcriptomics", max_results=10)
    details = fetch("12345678")

Usage as CLI:
    htan pubs search --keyword "spatial transcriptomics"
    htan pubs fetch 12345678
    htan pubs fulltext "tumor microenvironment"
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "htan_skill"
TOOL_EMAIL = "htan-skill@example.com"
REQUEST_DELAY = 0.34  # seconds between requests (3 req/sec limit without API key)
DEFAULT_TIMEOUT = 60

# HTAN Phase 1 grant numbers (CA233xxx series)
PHASE1_GRANTS = [
    "CA233195", "CA233238", "CA233243", "CA233254", "CA233262",
    "CA233280", "CA233284", "CA233285", "CA233291", "CA233303", "CA233311",
]

# HTAN Phase 2 grant numbers (CA294xxx series)
PHASE2_GRANTS = [
    "CA294459", "CA294507", "CA294514", "CA294518", "CA294527",
    "CA294532", "CA294536", "CA294548", "CA294551", "CA294552",
]

# DCC contract
DCC_GRANTS = ["HHSN261201500003I"]

ALL_GRANTS = PHASE1_GRANTS + PHASE2_GRANTS + DCC_GRANTS

# HTAN-affiliated last authors (PIs)
HTAN_AUTHORS = [
    "Achilefu S", "Ashenberg O", "Aster J", "Cerami E", "Coffey RJ",
    "Curtis C", "Demir E", "Ding L", "Dubinett S", "Esplin ED",
    "Fields R", "Ford JM", "Ghosh S", "Gillanders W", "Goecks J",
    "Gray JW", "Greenleaf W", "Guinney J", "Hanlon SE", "Hughes SK",
    "Hunger SE", "Hupalowska A", "Hwang ES", "Iacobuzio-Donahue CA",
    "Jane-Valbuena J", "Johnson BE", "Lau KS", "Lively T", "Maley C",
    "Mazzilli SA", "Mills GB", "Nawy T", "Oberdoerffer P", "Pe'er D",
    "Regev A", "Rood JE", "Rozenblatt-Rosen O", "Santagata S",
    "Schapiro D", "Shalek AK", "Shrubsole MJ", "Snyder MP",
    "Sorger PK", "Spira AE", "Srivastava S", "Suva M", "Tan K",
    "Thomas GV", "West RB", "Williams EH", "Wold B", "Bastian B",
    "Dos Santos DC", "Fertig E", "Chen F", "Shain AH", "Ghobrial I",
    "Yeh I", "Amatruda J", "Spraggins J", "Brody J", "Wood L",
    "Wang L", "Cai L", "Shrubsole M", "Thomson M", "Birrer M",
    "Xu M", "Li M", "Mansfield P", "Everson R", "Fan R",
    "Sears R", "Pachynski R", "Fields R", "Mok S",
    "Ferri-Borgogno S", "Asgharzadeh S", "Halene S", "Hwang TH", "Ma Z",
]


def build_grant_query():
    """Build PubMed grant number query string."""
    return " OR ".join(f"{g}[gr]" for g in ALL_GRANTS)


def build_author_query(author=None):
    """Build PubMed author query. If author is given, filter to that author only."""
    if author:
        return f"{author}[LASTAU]"
    return " OR ".join(f"{a}[LASTAU]" for a in HTAN_AUTHORS)


def build_search_query(keyword=None, author=None, year=None):
    """Build a combined PubMed search query for HTAN publications."""
    grant_query = build_grant_query()
    author_query = build_author_query(author)
    query = f"({grant_query}) AND ({author_query})"
    if keyword:
        query = f"({query}) AND ({keyword})"
    if year:
        query = f"({query}) AND ({year}[pdat])"
    return query


def eutils_request(endpoint, params, timeout=DEFAULT_TIMEOUT):
    """Make a rate-limited request to NCBI E-utilities."""
    params["tool"] = TOOL_NAME
    params["email"] = TOOL_EMAIL
    url = f"{EUTILS_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    time.sleep(REQUEST_DELAY)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} from E-utilities: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to E-utilities: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print(f"Error: PubMed request timed out after {timeout}s.", file=sys.stderr)
        sys.exit(1)


def _parse_article_xml(article_elem):
    """Parse a PubmedArticle XML element into a dict."""
    try:
        medline = article_elem.find("MedlineCitation")
        if medline is None:
            return None

        pmid_elem = medline.find("PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""

        article = medline.find("Article")
        if article is None:
            return None

        title_elem = article.find("ArticleTitle")
        title = "".join(title_elem.itertext()) if title_elem is not None else ""

        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for author_elem in author_list.findall("Author"):
                last = author_elem.find("LastName")
                initials = author_elem.find("Initials")
                if last is not None:
                    name = last.text
                    if initials is not None:
                        name += f" {initials.text}"
                    authors.append(name)

        journal_elem = article.find("Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""

        year = ""
        pub_date = article.find("Journal/JournalIssue/PubDate")
        if pub_date is not None:
            year_elem = pub_date.find("Year")
            if year_elem is not None:
                year = year_elem.text
            else:
                medline_date = pub_date.find("MedlineDate")
                if medline_date is not None and medline_date.text:
                    year = medline_date.text[:4]

        abstract_parts = []
        abstract_elem = article.find("Abstract")
        if abstract_elem is not None:
            for abs_text in abstract_elem.findall("AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext()) or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        abstract = "\n".join(abstract_parts)

        doi = ""
        article_id_list = article_elem.find("PubmedData/ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text or ""
                    break

        return {
            "pmid": pmid, "title": title, "authors": authors,
            "journal": journal, "year": year, "doi": doi, "abstract": abstract,
        }
    except Exception as e:
        print(f"Warning: Failed to parse article: {e}", file=sys.stderr)
        return None


# --- Public API ---

def search(keyword=None, author=None, year=None, max_results=100, timeout=DEFAULT_TIMEOUT):
    """Search HTAN publications on PubMed.

    Args:
        keyword: Optional keyword filter.
        author: Optional last author filter (e.g., "Sorger PK").
        year: Optional publication year filter.
        max_results: Maximum number of results (default 100).
        timeout: HTTP timeout in seconds.

    Returns:
        List of article dicts with keys: pmid, title, authors, journal, year, doi, abstract.
    """
    query = build_search_query(keyword=keyword, author=author, year=year)
    params = {
        "db": "pubmed", "term": query, "retmax": str(max_results),
        "retmode": "json", "sort": "pub_date",
    }
    raw = eutils_request("esearch.fcgi", params, timeout=timeout)
    data = json.loads(raw)
    result = data.get("esearchresult", {})
    count = int(result.get("count", 0))
    pmids = result.get("idlist", [])
    print(f"Found {count} results, returning {len(pmids)}", file=sys.stderr)

    if not pmids:
        return []

    return fetch(pmids, timeout=timeout)


def fetch(pmids, timeout=DEFAULT_TIMEOUT):
    """Fetch article details for a list of PMIDs.

    Args:
        pmids: Single PMID string or list of PMIDs.
        timeout: HTTP timeout in seconds.

    Returns:
        List of article dicts.
    """
    if isinstance(pmids, str):
        pmids = [pmids]
    if not pmids:
        return []

    articles = []
    batch_size = 200
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i : i + batch_size]
        params = {"db": "pubmed", "id": ",".join(batch), "rettype": "xml", "retmode": "xml"}
        raw = eutils_request("efetch.fcgi", params, timeout=timeout)
        root = ET.fromstring(raw)
        for article_elem in root.findall(".//PubmedArticle"):
            article = _parse_article_xml(article_elem)
            if article:
                articles.append(article)

    return articles


def fulltext(query, max_results=50, timeout=DEFAULT_TIMEOUT):
    """Search HTAN articles in PubMed Central (full-text).

    Args:
        query: Full-text search query.
        max_results: Maximum number of results.
        timeout: HTTP timeout in seconds.

    Returns:
        List of article dicts with keys: pmc_id, title, journal, year, doi, pmid, authors.
    """
    grant_query = build_grant_query()
    full_query = f"({grant_query}) AND ({query})"

    params = {
        "db": "pmc", "term": full_query, "retmax": str(max_results),
        "retmode": "json", "sort": "pub_date",
    }
    raw = eutils_request("esearch.fcgi", params, timeout=timeout)
    data = json.loads(raw)
    result = data.get("esearchresult", {})
    count = int(result.get("count", 0))
    pmc_ids = result.get("idlist", [])
    print(f"Found {count} PMC results, returning {len(pmc_ids)}", file=sys.stderr)

    if not pmc_ids:
        return []

    params = {"db": "pmc", "id": ",".join(pmc_ids), "retmode": "json"}
    raw = eutils_request("esummary.fcgi", params, timeout=timeout)
    data = json.loads(raw)
    summaries = data.get("result", {})

    articles = []
    for pmc_id in pmc_ids:
        info = summaries.get(pmc_id, {})
        if not isinstance(info, dict):
            continue
        articles.append({
            "pmc_id": f"PMC{pmc_id}",
            "title": info.get("title", ""),
            "journal": info.get("fulljournalname", info.get("source", "")),
            "year": info.get("pubdate", "")[:4],
            "doi": "",
            "pmid": info.get("articleids", [{}])[0].get("value", "") if info.get("articleids") else "",
            "authors": [a.get("name", "") for a in info.get("authors", [])],
        })

    return articles


# --- Formatting ---

def format_article_text(article):
    """Format a single article for text output."""
    lines = []
    pmid = article.get("pmid", "")
    pmc_id = article.get("pmc_id", "")
    identifier = f"PMID: {pmid}" if pmid else f"PMC: {pmc_id}"
    lines.append(f"{identifier}")
    lines.append(f"  Title: {article.get('title', 'N/A')}")
    authors = article.get("authors", [])
    if authors:
        if len(authors) > 5:
            author_str = ", ".join(authors[:5]) + f", ... (+{len(authors)-5} more)"
        else:
            author_str = ", ".join(authors)
        lines.append(f"  Authors: {author_str}")
    lines.append(f"  Journal: {article.get('journal', 'N/A')} ({article.get('year', 'N/A')})")
    if article.get("doi"):
        lines.append(f"  DOI: https://doi.org/{article['doi']}")
    if article.get("abstract"):
        abstract = article["abstract"]
        if len(abstract) > 300:
            abstract = abstract[:300] + "..."
        lines.append(f"  Abstract: {abstract}")
    return "\n".join(lines)


# --- CLI ---

def cli_main(argv=None):
    """CLI entry point for publication search."""
    parser = argparse.ArgumentParser(
        description="Search HTAN publications on PubMed and PubMed Central",
        epilog="Examples:\n"
        "  htan pubs search\n"
        '  htan pubs search --keyword "spatial transcriptomics"\n'
        '  htan pubs search --author "Sorger PK"\n'
        "  htan pubs fetch 12345678\n"
        '  htan pubs fulltext "tumor microenvironment"\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp_search = subparsers.add_parser("search", help="Search HTAN publications on PubMed")
    sp_search.add_argument("--keyword", "-k", help="Filter by keyword")
    sp_search.add_argument("--author", "-a", help="Filter by last author")
    sp_search.add_argument("--year", "-y", help="Filter by publication year")
    sp_search.add_argument("--max-results", "-n", type=int, default=100, help="Maximum results (default: 100)")
    sp_search.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    sp_search.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"HTTP timeout (default: {DEFAULT_TIMEOUT})")
    sp_search.add_argument("--dry-run", action="store_true", help="Show query URL without executing")

    sp_fetch = subparsers.add_parser("fetch", help="Fetch details for specific PMIDs")
    sp_fetch.add_argument("pmids", nargs="+", help="PubMed IDs to fetch")
    sp_fetch.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    sp_fetch.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    sp_fetch.add_argument("--dry-run", action="store_true")

    sp_full = subparsers.add_parser("fulltext", help="Search HTAN articles in PubMed Central")
    sp_full.add_argument("query", help="Full-text search query")
    sp_full.add_argument("--max-results", "-n", type=int, default=50, help="Maximum results (default: 50)")
    sp_full.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    sp_full.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    sp_full.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "search":
        query = build_search_query(keyword=args.keyword, author=args.author, year=args.year)
        if args.dry_run:
            params = {"db": "pubmed", "term": query, "retmax": str(args.max_results),
                      "retmode": "json", "sort": "pub_date", "tool": TOOL_NAME, "email": TOOL_EMAIL}
            url = f"{EUTILS_BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
            print(f"Dry run — would request:", file=sys.stderr)
            print(f"  URL: {url}", file=sys.stderr)
            return
        articles = search(keyword=args.keyword, author=args.author, year=args.year,
                          max_results=args.max_results, timeout=args.timeout)
        if not articles:
            print("No articles found.", file=sys.stderr)
            return
        if args.format == "json":
            print(json.dumps(articles, indent=2))
        else:
            for a in articles:
                print(format_article_text(a))
                print()

    elif args.command == "fetch":
        if args.dry_run:
            print(f"Dry run — would fetch PMIDs: {', '.join(args.pmids)}", file=sys.stderr)
            return
        articles = fetch(args.pmids, timeout=args.timeout)
        if not articles:
            print("No articles found.", file=sys.stderr)
            return
        if args.format == "json":
            print(json.dumps(articles, indent=2))
        else:
            for a in articles:
                print(format_article_text(a))
                print()

    elif args.command == "fulltext":
        if args.dry_run:
            grant_query = build_grant_query()
            full_query = f"({grant_query}) AND ({args.query})"
            params = {"db": "pmc", "term": full_query, "retmax": str(args.max_results),
                      "retmode": "json", "sort": "pub_date", "tool": TOOL_NAME, "email": TOOL_EMAIL}
            url = f"{EUTILS_BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
            print(f"Dry run — would request:", file=sys.stderr)
            print(f"  URL: {url}", file=sys.stderr)
            return
        articles = fulltext(args.query, max_results=args.max_results, timeout=args.timeout)
        if not articles:
            print("No PMC articles found.", file=sys.stderr)
            return
        if args.format == "json":
            print(json.dumps(articles, indent=2))
        else:
            for a in articles:
                print(format_article_text(a))
                print()
