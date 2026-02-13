# HTAN Skill for Claude Code

## Project Overview

This is a Claude Code skill for working with the **Human Tumor Atlas Network (HTAN)** — an NCI Cancer Moonshot initiative that constructs 3D atlases of the dynamic cellular, morphological, and molecular features of human cancers as they evolve from precancerous lesions to advanced disease. The skill provides tools for accessing HTAN data across four platforms (HTAN Portal ClickHouse, Synapse, CRDC/Gen3, ISB-CGC BigQuery), searching HTAN publications, and querying HTAN metadata.

## Implementation Status

All 14 files have been implemented and verified:

| File | Status | Notes |
|---|---|---|
| `SKILL.md` | Done | Skill definition with unified workflow |
| `scripts/htan_portal_config.py` | Done | Shared config loader for portal credentials (stdlib only) |
| `scripts/htan_portal.py` | Done | Portal ClickHouse queries — credentials from config file, zero dependencies |
| `scripts/htan_setup.py` | Done | `init` wizard, `init-portal`, `--check` verified; portal check reads from config |
| `scripts/htan_pubmed.py` | Done | `--help`, `--dry-run`, and live search verified |
| `scripts/htan_synapse.py` | Done | `--help` verified; needs live test with credentials |
| `scripts/htan_gen3.py` | Done | `--help` and `--dry-run` verified; needs live test with credentials + dbGaP |
| `scripts/htan_bigquery.py` | Done | `--help` and NL query output verified; needs live test with GCP project |
| `scripts/htan_file_mapping.py` | Done | `--help`, `update`, `lookup`, `stats` verified |
| `scripts/htan_data_model.py` | Done | `--help`, `fetch`, `components`, `attributes`, `describe`, `valid-values`, `search`, `required`, `deps` verified; no auth, stdlib only |
| `references/clickhouse_portal.md` | Done | Portal schema, queries, limitations |
| `references/authentication_guide.md` | Done | |
| `references/htan_atlases.md` | Done | |
| `references/htan_data_model.md` | Done | Model-derived reference (v25.2.1): 64 components, controlled vocabularies, validation rules |
| `references/bigquery_tables.md` | Done | |
| `references/htan_docs_manual.md` | Done | Full site map of docs.humantumoratlas.org, citations, identifiers, platforms, FAQ |
| `LICENSE.txt` | Done | MIT |

### What Has Been Tested

- `htan_setup.py --check` — all packages installed, all auth configs detected, portal connectivity checked
- `htan_portal.py tables` — lists portal ClickHouse tables
- `htan_portal.py files --organ Breast --limit 5` — file queries with filters
- `htan_portal.py sql "SELECT ..."` — direct SQL execution
- `htan_portal.py files --dry-run` — SQL generation without execution
- `htan_pubmed.py search --keyword "spatial transcriptomics" --max-results 3` — live PubMed search returned results
- `htan_pubmed.py search --dry-run` — correct E-utilities URL construction
- `htan_gen3.py download "drs://dg.4DFC/abc-123-def" --dry-run` — DRS URI validation works
- `htan_bigquery.py query "..." --dry-run` — schema context output correct
- `htan_data_model.py fetch` — downloads model CSV from GitHub, caches locally
- `htan_data_model.py components` — lists all 64 manifest components
- `htan_data_model.py attributes "scRNA-seq Level 1"` — lists attributes for a component
- `htan_data_model.py describe "File Format"` — full attribute detail with valid values
- `htan_data_model.py search "barcode"` — keyword search across attributes
- All scripts `--help` — works correctly

### What Still Needs Live Testing

- `htan_synapse.py download synXXXXXXXX --dry-run` — test with Synapse credentials
- `htan_bigquery.py tables` — test with GCP project
- `htan_bigquery.py sql "SELECT ..."` — test actual query execution
- `htan_gen3.py resolve` — test with Gen3 credentials (requires dbGaP)

## Environment Setup

The project uses a **uv virtual environment** for reproducibility.

### uv Package Management Rules

All Python dependencies **must** be managed with `uv`. Never use `pip`, `pip-tools`, `poetry`, or `conda` for dependency tasks.

- **Run scripts**: `uv run scripts/<name>.py` (automatically resolves dependencies — no manual venv activation needed)
- **Run PyPI tools directly**: `uvx ruff`, `uvx pytest`
- **Add a package to the venv**: `uv pip install <package>`
- **Recreate the environment**: `uv venv .venv && uv pip install synapseclient gen3 google-cloud-bigquery google-cloud-bigquery-storage pandas db-dtypes`

When executing any Python code in this project, **always use `uv run`** instead of activating the venv manually. This ensures the correct environment is used regardless of shell state.

### PEP 723 Inline Script Metadata

Scripts that require third-party packages should declare dependencies inline using PEP 723 metadata. This makes each script fully portable — `uv run` will automatically fetch the declared dependencies without any prior environment setup:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "synapseclient>=4.0",
#     "pandas>=2.0",
# ]
# ///
```

Never rely on implicit existence of packages in the surrounding environment. Explicit dependency specification should travel with the code. Scripts using only stdlib (e.g., `htan_portal.py`, `htan_pubmed.py`, `htan_data_model.py`) do not need a metadata block.

## Credential Security

**Important**: Credentials are stored in config files, NOT environment variables in this setup:
- **Portal ClickHouse**: `~/.config/htan-skill/portal.json` (populated by `htan_setup.py init-portal`, downloaded from Synapse project syn73720845 gated by Team:3574960 membership)
- Synapse: `~/.synapseConfig`
- Gen3: `~/.gen3/credentials.json`
- BigQuery: Application Default Credentials (via `gcloud auth application-default login`)

Portal credentials are **not stored in source code**. They are fetched from Synapse behind a team membership gate, providing an audit trail of who accessed them.

**When using Claude Code**, avoid running commands that would print credentials or signed URLs into the conversation (which flows through the Anthropic API). Specifically:
- **Safe to run via Claude**: `--help`, `--dry-run`, PubMed searches, all `htan_portal.py` commands (credentials read from local config, not echoed), BigQuery `tables`/`describe`/`sql` (metadata results are not sensitive), file mapping `update`/`lookup`/`stats`, all `htan_data_model.py` commands (fetches from public GitHub, no credentials)
- **Run in your own terminal**: `htan_gen3.py resolve` (outputs signed URLs), any command where error messages might echo tokens

## Skill Architecture

```
htan-skill/
├── .cache/                           # Cached mapping file (not committed)
├── .venv/                            # uv virtual environment (not committed)
├── CLAUDE.md                         # Project instructions (this file)
├── LICENSE.txt
├── README.md
└── skills/
    └── portal/
        ├── SKILL.md                  # Skill definition (name, description, instructions)
        ├── scripts/
        │   ├── htan_portal_config.py # Shared config loader for portal credentials (stdlib only)
        │   ├── htan_portal.py        # Query HTAN portal ClickHouse (creds from config, zero deps)
        │   ├── htan_synapse.py       # Synapse open-access data download
        │   ├── htan_gen3.py          # Gen3/CRDC controlled-access data download via DRS
        │   ├── htan_bigquery.py      # Natural language query of HTAN metadata in ISB-CGC
        │   ├── htan_file_mapping.py  # File ID → Synapse/Gen3 download coordinate mapping
        │   ├── htan_pubmed.py        # PubMed search for HTAN publications
        │   ├── htan_data_model.py    # Phase 1 data model queries (no auth, stdlib only)
        │   └── htan_setup.py         # Environment setup and dependency installation
        └── references/
            ├── clickhouse_portal.md  # Portal ClickHouse schema, queries, and limitations
            ├── htan_data_model.md    # HTAN data model, entity types, and controlled vocabularies
            ├── htan_atlases.md       # Atlas centers and their cancer types
            ├── bigquery_tables.md    # ISB-CGC BigQuery table reference for HTAN
            ├── authentication_guide.md  # Auth setup for Synapse, Gen3, and BigQuery
            └── htan_docs_manual.md   # Full site map of docs.humantumoratlas.org + key facts
```

## Core Dependencies

Dependencies are managed by `uv`. Scripts with third-party deps should declare them via PEP 723 inline metadata (see above). To install all deps into the project venv:

```bash
uv pip install synapseclient gen3 google-cloud-bigquery google-cloud-bigquery-storage pandas db-dtypes
```

| Dependency | Purpose |
|---|---|
| `synapseclient` (4.11.0) | Download open-access HTAN data from Synapse |
| `gen3` (4.27.5) | Download controlled-access data from CRDC via DRS URIs |
| `google-cloud-bigquery` (3.40.0) | Query HTAN metadata tables in ISB-CGC |
| `google-cloud-bigquery-storage` (2.36.0) | Fast BigQuery result retrieval |
| `pandas` (2.3.3) | Data manipulation for query results |
| `db-dtypes` (1.5.0) | BigQuery data type support for pandas |

PubMed search uses only stdlib (`urllib`, `json`, `xml.etree.ElementTree`) — no additional dependencies.

Portal ClickHouse queries (`htan_portal.py`) also use only stdlib (`urllib`, `json`, `base64`, `ssl`) — no additional dependencies. Credentials are loaded from `~/.config/htan-skill/portal.json` via `htan_portal_config.py`.

Data model queries (`htan_data_model.py`) use only stdlib (`csv`, `json`, `urllib`, `argparse`) — no additional dependencies.

## Data Access Tiers

HTAN data has two access levels. The skill must handle both. The portal provides a unified query interface.

### Portal Metadata + File Discovery (ClickHouse)

- **Platform**: HTAN Data Portal ClickHouse backend
- **Client**: stdlib only (`urllib`, `json`, `base64`, `ssl`)
- **Auth**: Credentials cached at `~/.config/htan-skill/portal.json` (fetched from Synapse via `htan_setup.py init-portal`)
- **Data types**: File metadata, download coordinates, basic clinical data
- **Key tables**: `files`, `demographics`, `diagnosis`, `cases`, `specimen`, `atlases`, `publication_manifest`
- **Key operations**: SQL queries via HTTP POST, file discovery with filters, manifest generation
- **Limitations**: No SLA, database name changes with releases, simpler schema than BigQuery
- **See**: `references/clickhouse_portal.md` for full schema

### Open Access (Synapse)

- **Platform**: Synapse (synapse.org)
- **Client**: `synapseclient` Python package
- **Auth**: Personal Access Token via `SYNAPSE_AUTH_TOKEN` env var or `~/.synapseConfig`
- **Data types**: De-identified clinical data, processed matrices, imaging metadata
- **Key operations**: `syn.get(synapse_id)`, `synapseutils.syncFromSynapse()`

### Controlled Access (CRDC/Gen3)

- **Platform**: Cancer Research Data Commons (CRDC) via Gen3
- **Client**: `gen3` Python SDK or `gen3-client` CLI
- **Auth**: Gen3 credentials JSON file (downloaded from CRDC portal after dbGaP authorization)
- **API endpoint**: `https://nci-crdc.datacommons.io`
- **Data types**: Raw sequencing data (FASTQs, BAMs), protected genomic data
- **Identifiers**: DRS URIs in format `drs://dg.4DFC/<guid>`
- **Key operations**: Resolve DRS URI to signed URL, then download

### Metadata Query (ISB-CGC BigQuery)

- **Platform**: Google BigQuery via ISB-CGC
- **Project**: `isb-cgc-bq`
- **Dataset**: `HTAN` (default, `_current` tables) or `HTAN_versioned` (`_rN` tables for reproducible analyses)
- **Auth**: Google Cloud credentials (service account or user ADC)
- **Key tables** (using `_current` suffix from `isb-cgc-bq.HTAN`):
  - `clinical_tier1_demographics_current` — Patient demographics
  - `clinical_tier1_diagnosis_current` — Diagnosis information
  - `biospecimen_current` — Sample metadata
  - `scRNAseq_level1_metadata_current` — scRNA-seq assay metadata (also level2-4)
  - `imaging_level2_metadata_current` — Imaging metadata
- **Key operations**: SQL queries via `google.cloud.bigquery.Client`

## Unified Data Access Workflow

### Recommended: Portal → Download (2 steps, no auth)

The simplest workflow uses the portal ClickHouse database, which includes download coordinates directly:

1. **Query portal** to find files of interest — returns `DataFileID`, `synapseId`, and `drs_uri` in one query
2. **Download** from the appropriate platform based on access tier

```bash
python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --output json
python3 scripts/htan_portal.py manifest HTA9_1_19512 --output-dir ./manifests
python3 scripts/htan_synapse.py download syn26535909
```

### Alternative: BigQuery → File Mapping → Download (3 steps, for complex queries)

For deep clinical queries requiring multi-table joins or assay-level metadata (cell counts, library methods):

1. **Query BigQuery** to find files of interest (returns `HTAN_Data_File_ID`)
2. **Look up file IDs** via `htan_file_mapping.py` to get `entityId` (Synapse) and `drs_uri` (Gen3)
3. **Download** from the appropriate platform based on access tier

### File Mapping Script

`scripts/htan_file_mapping.py` bridges BigQuery results and downloads using the HTAN portal's DRS mapping file (~67,000 files):

```bash
python3 scripts/htan_file_mapping.py update                         # Download/refresh cache
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512            # Look up file ID
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 --format json  # JSON with download cmds
python3 scripts/htan_file_mapping.py lookup --file ids.txt          # Batch lookup from file
python3 scripts/htan_file_mapping.py stats                          # Mapping statistics
```

Cache is stored at `.cache/crdcgc_drs_mapping.json` (auto-downloaded on first use).

### Access Tier Determination

Based on the HTAN portal source (`FileTable.tsx` + `processSynapseJSON.ts`):

| Data Level / Type | Access | Platform |
|---|---|---|
| Level 3, Level 4, Auxiliary, Other | Open | Synapse (`entityId`) |
| Level 1-2 sequencing (bulk/-seq assays) with DRS URI | Controlled | Gen3 (`drs_uri`) |
| CODEX Level 1 | Open (exception) | Synapse |
| Specialized assays (electron microscopy, RPPA, slide-seq, mass spec) | Open | Synapse |
| Imaging in dbGaP set with DRS URI | Open | CRDC-GC |

The `infer_access_tier(file_id, level, assay)` function in `htan_file_mapping.py` implements these rules.

## Synapse Integration Details

### Authentication Pattern

```python
import synapseclient

# Preferred: environment variable
# User sets SYNAPSE_AUTH_TOKEN before running
syn = synapseclient.Synapse()
syn.login()

# Alternative: explicit token
syn = synapseclient.login(authToken="token_here")

# Alternative: ~/.synapseConfig file
syn = synapseclient.login()
```

### Download Patterns

```python
# Single file by Synapse ID
entity = syn.get("syn12345678", downloadLocation="/path/to/dir")
print(entity.path)  # local file path

# Bulk download a folder/project
import synapseutils
files = synapseutils.syncFromSynapse(
    syn,
    entity="syn12345678",
    path="/local/download/dir",
    ifcollision="keep.local"
)

# Get metadata only (no download)
entity = syn.get("syn12345678", downloadFile=False)
```

### Key HTAN Synapse IDs

The HTAN Data Coordinating Center maintains data at: `syn18488466` (HTAN project on Synapse).

## Gen3/CRDC Integration Details

### Authentication Pattern

```python
from gen3.auth import Gen3Auth
from gen3.file import Gen3File

# Auth using credentials JSON from CRDC portal
auth = Gen3Auth(endpoint="https://nci-crdc.datacommons.io", refresh_file="credentials.json")
file_client = Gen3File(endpoint="https://nci-crdc.datacommons.io", auth_provider=auth)
```

### DRS URI Resolution and Download

```python
# Resolve DRS URI to a signed download URL
drs_uri = "drs://dg.4DFC/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
guid = drs_uri.replace("drs://dg.4DFC/", "")

# Get signed URL
url_info = file_client.get_presigned_url(guid, protocol="s3")
download_url = url_info["url"]

# Download the file
import requests
response = requests.get(download_url, stream=True)
with open(output_filename, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

### Input Validation Requirements

When handling DRS URIs and Gen3 profiles, always validate inputs:
- **GUID**: Must match `^[a-zA-Z0-9._\/-]+$`
- **API endpoint**: Must be valid HTTPS URL
- **Profile name**: Must match `^[a-zA-Z0-9_-]+$`

## BigQuery Integration Details

### Authentication Pattern

```python
from google.cloud import bigquery

# Uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS env var
client = bigquery.Client(project="user-billing-project")
```

### Query Pattern

```python
query = """
SELECT *
FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`
WHERE HTAN_Center = 'HTAN HTAPP'
LIMIT 100
"""
df = client.query(query).to_dataframe()
```

### Natural Language Query Approach

The BigQuery integration should support natural language queries. Use the LLM to:
1. Parse the user's natural language question
2. Map entities to HTAN BigQuery table/column names
3. Generate safe, parameterized SQL
4. Execute and return results with explanation

Always validate generated SQL before execution — block DELETE, DROP, UPDATE, INSERT, and other write operations.

## PubMed Search for HTAN Publications

### Grant Numbers

HTAN publications are identified by citing one of these NCI grants:

**Phase 1 (CA233xxx):**
CA233195, CA233238, CA233243, CA233254, CA233262, CA233280, CA233284, CA233285, CA233291, CA233303, CA233311

**Phase 2 (CA294xxx):**
CA294459, CA294507, CA294514, CA294518, CA294527, CA294532, CA294536, CA294548, CA294551, CA294552

**DCC Contract:**
HHSN261201500003I

### Last Authors (HTAN PIs)

The complete list of HTAN-affiliated last authors for filtering:

Achilefu S, Ashenberg O, Aster J, Cerami E, Coffey RJ, Curtis C, Demir E, Ding L, Dubinett S, Esplin ED, Fields R, Ford JM, Ghosh S, Gillanders W, Goecks J, Gray JW, Greenleaf W, Guinney J, Hanlon SE, Hughes SK, Hunger SE, Hupalowska A, Hwang ES, Iacobuzio-Donahue CA, Jane-Valbuena J, Johnson BE, Lau KS, Lively T, Maley C, Mazzilli SA, Mills GB, Nawy T, Oberdoerffer P, Pe'er D, Regev A, Rood JE, Rozenblatt-Rosen O, Santagata S, Schapiro D, Shalek AK, Shrubsole MJ, Snyder MP, Sorger PK, Spira AE, Srivastava S, Suva M, Tan K, Thomas GV, West RB, Williams EH, Wold B, Bastian B, Dos Santos DC, Fertig E, Chen F, Shain AH, Ghobrial I, Yeh I, Amatruda J, Spraggins J, Brody J, Wood L, Wang L, Cai L, Shrubsole M, Thomson M, Birrer M, Xu M, Li M, Mansfield P, Everson R, Fan R, Sears R, Pachynski R, Fields R, Mok S, Ferri-Borgogno S, Asgharzadeh S, Halene S, Hwang TH, Ma Z

### PubMed E-utilities API

Use the NCBI E-utilities REST API (no extra dependencies needed):

```python
import urllib.request
import json

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Build grant query
grant_ids = ["CA233195", "CA233238", ...]  # all grant IDs above
grant_query = " OR ".join(f"{g}[gr]" for g in grant_ids)

# Build author query
authors = ["Achilefu S", "Ashenberg O", ...]  # all authors above
author_query = " OR ".join(f"{a} [LASTAU]" for a in authors)

# Combined query
query = f"({grant_query}) AND ({author_query})"

# Search
url = f"{EUTILS_BASE}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax=10000&retmode=json&sort=pub_date"
```

**Rate limits**: 3 requests/sec without API key, 10/sec with key. Always include `tool=htan_skill&email=user@email.com` parameters.

**Fetching abstracts**: Use `efetch.fcgi` with `rettype=xml` to get full structured records including title, authors, abstract, DOI, journal, and publication date.

### Full-Text Search

For searching across HTAN manuscript full text, use the PubMed Central (PMC) API:
- E-utilities with `db=pmc` for PMC-indexed articles
- The Open Access subset provides full-text XML

## HTAN Atlas Centers Reference

| Atlas | Cancer Type | Phase |
|---|---|---|
| HTAN HTAPP | Multiple (pan-cancer) | 1 |
| HTAN HMS | Melanoma, breast, colorectal | 1 |
| HTAN OHSU | Breast | 1 |
| HTAN MSK | Colorectal, pancreatic | 1 |
| HTAN Stanford | Breast | 1 |
| HTAN Vanderbilt | Colorectal | 1 |
| HTAN WUSTL | Breast, pancreatic | 1 |
| HTAN CHOP | Pediatric | 1 |
| HTAN Duke | Breast | 1 |
| HTAN BU | Lung (pre-cancer) | 1 |
| HTAN DFCI | Multiple myeloma | 1 |
| HTAN TNP SARDANA | Multiple | 2 |
| HTAN TNP SRRS | Multiple | 2 |
| HTAN TNP TMA | Multiple | 2 |

## Script Implementation Guidelines

### General Principles

- Every script must be **self-contained and runnable via `python3 scripts/<name>.py`**
- Use `argparse` for CLI parameters
- Print clear progress messages to stderr, results to stdout
- Handle authentication errors gracefully with actionable messages
- Never hardcode credentials — always use env vars or config files
- Include `--help` with examples

### Error Handling Pattern

```python
import sys

def check_auth(service_name, env_var):
    """Check if authentication is configured and provide actionable guidance."""
    import os
    token = os.environ.get(env_var)
    if not token:
        print(f"Error: {service_name} authentication not configured.", file=sys.stderr)
        print(f"Set the {env_var} environment variable.", file=sys.stderr)
        print(f"See references/authentication_guide.md for setup instructions.", file=sys.stderr)
        sys.exit(1)
    return token
```

### Script: htan_portal.py

```bash
# List tables in the portal database
python3 scripts/htan_portal.py tables

# Describe a table schema
python3 scripts/htan_portal.py describe files

# Query files with filters
python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --limit 10

# Look up specific file IDs (returns synapseId and DRS URI)
python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json

# Clinical queries
python3 scripts/htan_portal.py demographics --atlas "HTAN OHSU" --limit 10
python3 scripts/htan_portal.py diagnosis --organ Breast --limit 10

# Direct SQL
python3 scripts/htan_portal.py sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"

# Generate download manifests
python3 scripts/htan_portal.py manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

### Script: htan_setup.py

Interactive setup wizard and dependency/auth checker:
```bash
python3 scripts/htan_setup.py init              # Interactive setup wizard (first-time setup)
python3 scripts/htan_setup.py init --force       # Re-run all steps even if configured
python3 scripts/htan_setup.py init --non-interactive  # Skip prompts (CI/scripted)
python3 scripts/htan_setup.py                    # Check all services
python3 scripts/htan_setup.py --check            # Check only, don't install
python3 scripts/htan_setup.py init-portal        # Download portal credentials from Synapse
python3 scripts/htan_setup.py init-portal --force  # Overwrite existing config
```

### Script: htan_synapse.py

```bash
# Download a file by Synapse entity ID
python3 scripts/htan_synapse.py download syn26535909

# Download to a specific directory
python3 scripts/htan_synapse.py download syn26535909 --output-dir ./data

# Dry run — check metadata without downloading
python3 scripts/htan_synapse.py download syn26535909 --dry-run
```

### Script: htan_gen3.py

```bash
# Download by DRS URI
python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid-here" --credentials credentials.json

# Download multiple DRS URIs from file
python3 scripts/htan_gen3.py download --manifest drs_uris.txt --credentials credentials.json

# Resolve DRS URI to signed URL (no download)
python3 scripts/htan_gen3.py resolve "drs://dg.4DFC/guid-here" --credentials credentials.json
```

### Script: htan_file_mapping.py

```bash
# Download/refresh the mapping cache
python3 scripts/htan_file_mapping.py update

# Look up one or more file IDs
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 HTA9_1_19553

# Look up from a file (one ID per line)
python3 scripts/htan_file_mapping.py lookup --file ids.txt

# JSON output with download commands
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 --format json

# Show mapping statistics
python3 scripts/htan_file_mapping.py stats
```

### Script: htan_bigquery.py

```bash
# Natural language query
python3 scripts/htan_bigquery.py query "How many patients with breast cancer in HTAN?"

# Direct SQL query
python3 scripts/htan_bigquery.py sql "SELECT COUNT(*) FROM ..."

# List available tables (defaults to HTAN dataset with _current tables)
python3 scripts/htan_bigquery.py tables

# List versioned tables
python3 scripts/htan_bigquery.py tables --versioned

# Describe a table schema (auto-appends _current suffix)
python3 scripts/htan_bigquery.py describe clinical_tier1_demographics
```

### Script: htan_pubmed.py

```bash
# Search all HTAN publications
python3 scripts/htan_pubmed.py search

# Search with keyword filter
python3 scripts/htan_pubmed.py search --keyword "spatial transcriptomics"

# Search by specific atlas/center
python3 scripts/htan_pubmed.py search --author "Sorger PK"

# Get details for a specific PMID
python3 scripts/htan_pubmed.py fetch 12345678

# Full-text search across PMC articles
python3 scripts/htan_pubmed.py fulltext "tumor microenvironment"

# Output as JSON for programmatic use
python3 scripts/htan_pubmed.py search --format json
```

### Script: htan_data_model.py

Query the HTAN Phase 1 data model (ncihtan/data-models v25.2.1). No auth required, stdlib only.

```bash
# Download/refresh model CSV
python3 scripts/htan_data_model.py fetch
python3 scripts/htan_data_model.py fetch --dry-run

# List all 64 manifest components
python3 scripts/htan_data_model.py components

# List attributes for a component
python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"
python3 scripts/htan_data_model.py attributes "Biospecimen"

# Full detail for one attribute
python3 scripts/htan_data_model.py describe "Library Construction Method"

# List valid values
python3 scripts/htan_data_model.py valid-values "File Format"

# Search by keyword
python3 scripts/htan_data_model.py search "barcode"

# Required fields for a component
python3 scripts/htan_data_model.py required "Biospecimen"

# Dependency chain
python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"
```

## SKILL.md Guidelines

The SKILL.md should:
- Use `name: portal` as the skill name (invoked via `/htan:portal`)
- Description should mention: HTAN data access, portal ClickHouse, Synapse, Gen3/CRDC, BigQuery, and publication search
- Body should explain the 6 capabilities and when to use each
- Reference scripts for each operation
- Keep under 500 lines — move detailed docs to `references/`

## Security Requirements

- **Never log or display credentials/tokens** in output
- **Validate all user-supplied inputs** before passing to APIs (Synapse IDs, DRS URIs, SQL)
- **Block write operations** in BigQuery and portal ClickHouse queries (no DELETE, DROP, UPDATE, INSERT, CREATE, ALTER, TRUNCATE)
- **Sanitize SQL** — use parameterized queries where possible, never string-interpolate user input into SQL
- **DRS URI validation**: Verify format before attempting resolution
- **File path validation**: Prevent path traversal in download destinations

## Testing Approach

Every script supports `--dry-run` for validation without API calls.

### Testing via Claude Code (safe — no credentials exposed)

```bash
source .venv/bin/activate

# First-time setup (interactive wizard — run once)
# python3 scripts/htan_setup.py init

# Check status
python3 scripts/htan_setup.py --check
python3 scripts/htan_portal.py tables
python3 scripts/htan_portal.py describe files
python3 scripts/htan_portal.py files --organ Breast --limit 5
python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json
python3 scripts/htan_portal.py sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name ORDER BY n DESC"
python3 scripts/htan_portal.py files --organ Breast --dry-run

# PubMed (no auth needed)
python3 scripts/htan_pubmed.py search --max-results 5
python3 scripts/htan_pubmed.py search --keyword "spatial transcriptomics" --max-results 3
python3 scripts/htan_pubmed.py search --dry-run

# Data model (no auth needed, stdlib only)
python3 scripts/htan_data_model.py fetch
python3 scripts/htan_data_model.py fetch --dry-run
python3 scripts/htan_data_model.py components
python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"
python3 scripts/htan_data_model.py describe "File Format"
python3 scripts/htan_data_model.py valid-values "Preservation Method"
python3 scripts/htan_data_model.py search "barcode"
python3 scripts/htan_data_model.py required "Biospecimen"
python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"

# Other dry-run tests
python3 scripts/htan_gen3.py download "drs://dg.4DFC/test-guid" --dry-run
python3 scripts/htan_bigquery.py query "How many breast cancer patients?"
python3 scripts/htan_file_mapping.py update
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512
python3 scripts/htan_file_mapping.py stats
```

### Testing in your own terminal (credentials involved)

```bash
source .venv/bin/activate

# Synapse
python3 scripts/htan_synapse.py download syn26535909 --dry-run

# BigQuery (set your project first)
export GOOGLE_CLOUD_PROJECT="your-project-id"
python3 scripts/htan_bigquery.py tables
python3 scripts/htan_bigquery.py describe clinical_tier1_demographics
python3 scripts/htan_bigquery.py sql "SELECT HTAN_Center, COUNT(*) as n FROM \`isb-cgc-bq.HTAN.clinical_tier1_demographics_current\` GROUP BY HTAN_Center"

# Gen3 (requires dbGaP authorization for phs002371)
python3 scripts/htan_gen3.py resolve "drs://dg.4DFC/your-guid"
```

### BigQuery dry_run cost estimation

```bash
python3 scripts/htan_bigquery.py sql "SELECT * FROM \`isb-cgc-bq.HTAN.clinical_tier1_demographics_current\`" --dry-run
```

This uses `QueryJobConfig(dry_run=True)` to estimate bytes processed without executing.
