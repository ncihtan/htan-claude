# Test Coverage Analysis

**Date**: 2026-02-15
**Test suite**: 168 tests across 14 test files, all passing
**Overall line coverage**: **28%** (674 / 2368 statements covered)

## Coverage by Module

| Module | Stmts | Missed | Coverage | Assessment |
|---|---|---|---|---|
| `htan/__init__.py` | 1 | 0 | 100% | Complete |
| `htan/__main__.py` | 2 | 2 | 0% | Trivial entry point |
| `htan/config.py` | 120 | 29 | **76%** | Good |
| `htan/init.py` | 342 | 157 | **54%** | Moderate |
| `htan/pubs.py` | 251 | 164 | **35%** | Gaps in core API |
| `htan/query/portal.py` | 601 | 447 | **26%** | Helpers tested; client/CLI not |
| `htan/files.py` | 176 | 141 | **20%** | Only `infer_access_tier` tested |
| `htan/download/gen3.py` | 155 | 124 | **20%** | Only validation tested |
| `htan/download/synapse.py` | 68 | 56 | **18%** | Only validation tested |
| `htan/query/bq.py` | 177 | 145 | **18%** | 3 tests (SQL safety only) |
| `htan/model.py` | 393 | 353 | **10%** | Nearly untested |
| `htan/cli.py` | 82 | 76 | **7%** | Only top-level dispatch |

## What's Well Tested

The existing test suite does a solid job on **input validation and pure helper functions**:

- **SQL safety validation** (`portal.py`, `bq.py`): Blocked keywords (DELETE, DROP, INSERT, UPDATE, TRUNCATE), allowed starts, normalize/escape, ensure_limit
- **Credential loading** (`config.py`): All 3 tiers (env, keychain, file), validation, error cases
- **ID validation**: Synapse IDs, DRS URIs, GUID extraction, HTAN file ID patterns
- **Access tier inference** (`files.py`): All access tier rules (Synapse vs Gen3 for different levels/assays)
- **Output formatting** (`portal.py`): parse_json_rows, format_text_table, format_output (JSON/text/CSV)
- **PubMed query building** (`pubs.py`): Grant queries, author queries, combined search queries, article XML parsing
- **Init wizard** (`init.py`): UI helpers, service init paths, status display

## Gap Analysis and Recommendations

### Priority 1: `htan.model` — 10% coverage (353 lines uncovered)

This module has the most complex pure logic in the codebase and almost no tests. All of it is testable without network access using fixture CSV data.

**What to test**:

1. **`_get_components(rows)`** — Parses model CSV rows into component dicts. Test with a small fixture CSV containing 3-4 components with dependencies. Verify it finds components by `DependsOn Component`, discovers referenced-but-not-declared components, and returns correct attribute counts.

2. **`_get_component_attributes(rows, name)`** — Looks up a component and returns its attributes with metadata. Test exact match, case-insensitive match, partial match (single result), ambiguous match (ValueError), and not-found (ValueError). Verify it returns correct `required`, `valid_values_count`, and `validation_rules` fields.

3. **`_find_attribute(rows, name)`** — Case-insensitive attribute lookup with fuzzy matching. Test exact, partial unique match, ambiguous (ValueError), not found (ValueError).

4. **`_get_dependency_chain(rows, name)`** — BFS traversal of component dependencies. Test linear chain (A → B → C), diamond dependencies, cycle handling (visited set), and not-found errors.

5. **`_categorize_component(name, parent)`** — Classifies components into categories (Clinical, Biospecimen, Assay, etc.). Test representative names from each category.

6. **`DataModel` class methods** — `components()`, `attributes()`, `describe()`, `valid_values()`, `search()`, `required()`, `deps()`. These can be tested by mocking `_load_model` to return fixture data.

7. **Formatting functions** — `_format_components_text`, `_format_attributes_text`, `_format_describe_text`, `_format_deps_text`. Verify output structure for typical and edge-case inputs.

**Approach**: Create a `tests/fixtures/model_fixture.csv` with ~20 representative rows. Mock `_load_model` / `CACHE_FILE` to use it. All tests are fast and offline.

### Priority 2: `htan.query.portal` PortalClient — 26% coverage (447 lines uncovered)

The pure helpers are well-tested, but the `PortalClient` class methods and CLI handlers have zero behavioral tests.

**What to test**:

1. **`PortalClient.query(sql, limit)`** — Mock `clickhouse_query` to return canned JSONEachRow responses. Verify: SQL safety check is enforced (unsafe SQL raises `PortalError`), `ensure_limit` is applied, response is parsed correctly.

2. **`PortalClient.find_files(**filters)`** — Mock `clickhouse_query`. Verify: correct SQL is generated for various filter combinations (single filter, multiple filters, array columns, data_file_id lookup, no filters). Check that `escape_sql_string` is applied to user input.

3. **`PortalClient.list_tables()`** — Mock to return tab-separated table names. Verify sorted output.

4. **`PortalClient.describe_table(table)`** — Mock the DESCRIBE + count queries. Verify table name validation rejects bad names, output dict has correct structure.

5. **`PortalClient.get_demographics()` / `get_diagnosis()`** — Mock `_clinical_query`. Verify filter pass-through.

6. **`PortalClient.get_manifest(file_ids)`** — Mock query. Verify correct SQL construction for manifest generation.

7. **`clickhouse_query()` error handling** — Mock `urllib.request.urlopen` to simulate HTTP errors, timeouts, auth failures. Verify `PortalError` messages include helpful hints.

8. **`discover_database()`** — Mock the `SHOW DATABASES` query to test the auto-discovery logic (multiple databases, no databases, naming patterns).

**Approach**: Use `unittest.mock.patch` on `clickhouse_query` for PortalClient tests, and on `urllib.request.urlopen` for lower-level tests.

### Priority 3: `htan.query.bq` — 18% coverage (145 lines uncovered)

Only 3 SQL safety tests exist. The `BigQueryClient` class and CLI are untested.

**What to test**:

1. **`validate_sql_safety`** — Expand to test all blocked keywords (CREATE, ALTER, MERGE, GRANT, REVOKE), case variations, keywords embedded in strings vs. standalone.

2. **`_ensure_limit(sql, limit)`** — Test adding LIMIT to SELECT, preserving existing LIMIT, handling subqueries.

3. **`BigQueryClient.query()`** — Mock `google.cloud.bigquery.Client`. Verify: SQL validation is enforced, limit is applied, `dry_run` mode returns SQL without executing, results are converted to list of dicts.

4. **`BigQueryClient.list_tables()`** — Mock BigQuery client to return table references. Test both current and versioned datasets, filtering by suffix.

5. **`BigQueryClient.describe_table()`** — Mock schema response. Verify table name pattern validation, correct output structure.

6. **CLI dispatch** (`cli_main`) — Test `tables`, `describe`, `sql`, and `query` subcommands with mocked BigQueryClient. Verify error handling for missing project.

**Approach**: Mock `_get_bq_module()` to return a fake BigQuery module, avoiding the need for `google-cloud-bigquery` to be installed.

### Priority 4: `htan.files` — 20% coverage (141 lines uncovered)

Only `infer_access_tier` and `FILE_ID_PATTERN` are tested. The lookup, caching, and stats logic is not.

**What to test**:

1. **`lookup(file_ids, format)`** — Mock `_load_mapping` to return a small fixture dict. Test: single ID found, multiple IDs (some found / some missing), text vs JSON format output, invalid file ID rejected.

2. **`_load_mapping()`** — Mock the cache file. Verify it builds a correct dict keyed by `HTAN_Data_File_ID`, handles records with missing IDs.

3. **`stats()`** — Mock `_load_mapping`. Verify it computes correct counts (total files, unique atlases, files with Synapse IDs, files with DRS URIs).

4. **`_download_mapping()`** — Mock `urllib.request.urlopen`. Test: cache-hit skip, successful download, invalid JSON response, network error.

5. **CLI dispatch** (`cli_main`) — Test `lookup`, `update`, `stats` subcommands.

**Approach**: Use `tmp_path` fixtures for cache directory, mock urllib for network calls.

### Priority 5: `htan.pubs` — 35% coverage (164 lines uncovered)

Query building and XML parsing are tested. The actual search/fetch/fulltext functions and CLI are not.

**What to test**:

1. **`eutils_request()`** — Mock `urllib.request.urlopen`. Test: successful response, HTTP error, timeout, rate-limiting delay.

2. **`search()`** — Mock `eutils_request`. Test: basic search returns articles, keyword/author/year filters, empty results, max_results cap.

3. **`fetch()`** — Mock `eutils_request` to return canned XML. Test: single PMID, batch of PMIDs (>200 triggers batching), invalid PMID handling.

4. **`fulltext()`** — Mock `eutils_request`. Test: basic PMC search, empty results.

5. **`format_article_text()`** — Pure function. Test with complete article dict, article with missing fields, empty article.

6. **CLI dispatch** (`cli_main`) — Test `search`, `fetch`, `fulltext` subcommands with mocked network.

### Priority 6: `htan.download.synapse` and `htan.download.gen3` — 18-20% coverage

Validation is well-tested. The actual download/resolve functions are not.

**What to test**:

1. **`synapse.download()`** — Mock `_get_synapse_client()`. Test: dry_run mode (prints command, doesn't download), successful download, output_dir creation, invalid Synapse ID error.

2. **`gen3.resolve()`** — Mock `_get_gen3_auth()`. Test: successful resolution returns URL dict, invalid DRS URI error, missing credentials error.

3. **`gen3.download()`** — Mock resolve + urllib. Test: dry_run mode, manifest file reading, single file download.

4. **CLI dispatch** for both modules — Test argument parsing and error messages.

### Priority 7: `htan.cli` — 7% coverage (76 lines uncovered)

The main dispatch logic routes to submodules but has minimal testing beyond `--help` and `--version`.

**What to test**:

1. **Command routing** — Mock each submodule's `cli_main`. Verify `htan query portal ...` calls `portal.cli_main`, `htan download synapse ...` calls `synapse.cli_main`, etc.

2. **`_dispatch_query()`** — Test unknown backend error, missing backend error.

3. **`_dispatch_download()`** — Test unknown backend error, missing backend error.

4. **`_dispatch_config()`** — Test `check`, `init-portal` (deprecated), unknown command, `--help`.

## Suggested Test Implementation Order

For maximum impact on coverage with minimum effort:

1. **`model.py` pure logic** (~+25% module coverage from fixture-based tests)
2. **`portal.py` PortalClient** (~+20% module coverage from mocked client tests)
3. **`files.py` lookup/stats** (~+30% module coverage)
4. **`bq.py` BigQueryClient** (~+30% module coverage)
5. **`pubs.py` search/fetch** (~+25% module coverage)
6. **`cli.py` dispatch routing** (~+60% module coverage, all simple mocks)
7. **Download modules** (~+30% module coverage each)

Implementing priorities 1-3 would move overall coverage from **28% → ~45%**. Completing all recommendations would bring it to approximately **65-70%**.

## Patterns to Follow

The existing tests set good conventions:
- Tests are fast and offline (no network calls)
- `unittest.mock.patch` is used for environment and file system mocks
- Tests are organized by module (`test_<module>.py`)
- Test names are descriptive (`test_<what>_<condition>`)
- Edge cases and error paths are tested alongside happy paths

New tests should follow these same patterns, adding fixture files under `tests/fixtures/` where useful (e.g., model CSV, mapping JSON).
