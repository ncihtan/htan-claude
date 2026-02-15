# HTAN Skill for Claude Code

## Project Overview

This is a Claude Code skill for working with the **Human Tumor Atlas Network (HTAN)** — an NCI Cancer Moonshot initiative that constructs 3D atlases of the dynamic cellular, morphological, and molecular features of human cancers as they evolve from precancerous lesions to advanced disease. The skill provides tools for accessing HTAN data across four platforms (HTAN Portal ClickHouse, Synapse, CRDC/Gen3, ISB-CGC BigQuery), searching HTAN publications, and querying HTAN metadata.

## Package Structure

The core functionality lives in the `htan` pip-installable package (`src/htan/`). The skill definition (`skills/htan/SKILL.md`) teaches Claude the CLI commands. No MCP server — just Bash calls to the `htan` CLI.

| Module | Source | Notes |
|---|---|---|
| `htan.config` | `src/htan/config.py` | 3-tier credential resolution (env > keychain > config file) |
| `htan.query.portal` | `src/htan/query/portal.py` | Portal ClickHouse queries, `PortalClient` class (stdlib only) |
| `htan.query.bq` | `src/htan/query/bq.py` | BigQuery queries, `BigQueryClient` class (needs `htan[bigquery]`) |
| `htan.download.synapse` | `src/htan/download/synapse.py` | Synapse downloads (needs `htan[synapse]`) |
| `htan.download.gen3` | `src/htan/download/gen3.py` | Gen3/CRDC DRS downloads (needs `htan[gen3]`) |
| `htan.pubs` | `src/htan/pubs.py` | PubMed search (stdlib only) |
| `htan.model` | `src/htan/model.py` | HTAN data model queries, `DataModel` class (stdlib only) |
| `htan.files` | `src/htan/files.py` | File ID to download coordinate mapping (stdlib only) |
| `htan.cli` | `src/htan/cli.py` | Unified CLI entry point (`htan` command) |

### What Still Needs Live Testing

- `htan download synapse synXXXXXXXX --dry-run` — test with Synapse credentials
- `htan query bq tables` — test with GCP project
- `htan query bq sql "SELECT ..."` — test actual query execution
- `htan download gen3 resolve` — test with Gen3 credentials (requires dbGaP)

## Environment Setup

The project uses a **uv virtual environment** and a `pyproject.toml`-based package layout.

### uv Package Management Rules

All Python dependencies **must** be managed with `uv`. Never use `pip`, `pip-tools`, `poetry`, or `conda` for dependency tasks.

- **Install the package**: `uv pip install -e ".[dev]"` (editable mode with dev deps)
- **Install all extras**: `uv pip install -e ".[all,dev]"`
- **Run CLI**: `uv run htan <command>` or just `htan <command>` after install
- **Run tests**: `uv run pytest tests/`
- **Run PyPI tools directly**: `uvx ruff`, `uvx pytest`
- **Build wheel**: `uv build`

When executing any Python code in this project, **always use `uv run`** instead of activating the venv manually. This ensures the correct environment is used regardless of shell state.

### Package Dependencies (pyproject.toml)

Core package is stdlib-only. Optional extras for platform-specific features:

```bash
pip install htan              # Core: portal, pubs, model, files (stdlib only)
pip install htan[synapse]     # + Synapse downloads
pip install htan[gen3]        # + Gen3/CRDC downloads
pip install htan[bigquery]    # + BigQuery queries
pip install htan[all]         # All of the above
pip install htan[dev]         # + pytest, ruff
```

## Credential Security

**Important**: Credentials are stored in config files, NOT environment variables in this setup:
- **Portal ClickHouse**: `~/.config/htan-skill/portal.json` (populated by `htan_setup.py init-portal`, downloaded from Synapse project syn73720845 gated by Team:3574960 membership)
- Synapse: `~/.synapseConfig`
- Gen3: `~/.gen3/credentials.json`
- BigQuery: Application Default Credentials (via `gcloud auth application-default login`)

Portal credentials are **not stored in source code**. They are fetched from Synapse behind a team membership gate, providing an audit trail of who accessed them.

**When using Claude Code**, avoid running commands that would print credentials or signed URLs into the conversation (which flows through the Anthropic API). Specifically:
- **Safe to run via Claude**: `--help`, `--dry-run`, PubMed searches, all portal queries (credentials read from local config, not echoed), BigQuery `tables`/`describe`/`sql` (metadata results are not sensitive), file mapping `update`/`lookup`/`stats`, all data model commands (fetches from public GitHub, no credentials)
- **Run in your own terminal**: `htan download gen3 resolve` (outputs signed URLs), any command where error messages might echo tokens

## Project Layout

```
htan-skill/
├── pyproject.toml                    # Package definition (hatchling build)
├── src/
│   └── htan/                         # pip-installable package
│       ├── __init__.py               # Version
│       ├── cli.py                    # Unified CLI: `htan <command>`
│       ├── config.py                 # Credential management (3-tier: env > keychain > file)
│       ├── query/
│       │   ├── portal.py             # Portal ClickHouse queries (stdlib only)
│       │   └── bq.py                 # BigQuery queries (needs htan[bigquery])
│       ├── download/
│       │   ├── synapse.py            # Synapse downloads (needs htan[synapse])
│       │   └── gen3.py               # Gen3/CRDC DRS downloads (needs htan[gen3])
│       ├── pubs.py                   # PubMed publication search (stdlib only)
│       ├── model.py                  # HTAN data model queries (stdlib only)
│       └── files.py                  # File ID → download coordinate mapping (stdlib only)
├── tests/                            # Package tests (pytest)
├── skills/
│   └── htan/
│       ├── SKILL.md                  # Skill definition (teaches Claude the CLI)
│       ├── scripts/                  # Legacy standalone scripts (kept for backward compat)
│       └── references/               # Reference docs (schema, auth, atlases, model)
├── .claude-plugin/
│   └── plugin.json                   # Plugin metadata (no MCP server)
├── CLAUDE.md                         # Project instructions (this file)
└── LICENSE.txt
```

## Core Dependencies

Dependencies are defined in `pyproject.toml`. Core package is stdlib-only; optional extras add platform support:

| Extra | Dependencies | Purpose |
|---|---|---|
| (core) | stdlib only | Portal queries, PubMed, data model, file mapping |
| `synapse` | `synapseclient>=4.0` | Synapse open-access downloads |
| `gen3` | `gen3>=4.27` | Gen3/CRDC controlled-access downloads |
| `bigquery` | `google-cloud-bigquery`, `pandas`, etc. | ISB-CGC BigQuery queries |
| `all` | synapse + gen3 + bigquery | All platform extras |
| `dev` | `pytest`, `ruff` | Development tools |

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
htan query portal files --organ Breast --assay "scRNA-seq" --output json
htan query portal manifest HTA9_1_19512 --output-dir ./manifests
htan download synapse download syn26535909
```

### Alternative: BigQuery → File Mapping → Download (3 steps, for complex queries)

For deep clinical queries requiring multi-table joins or assay-level metadata (cell counts, library methods):

1. **Query BigQuery** to find files of interest (returns `HTAN_Data_File_ID`)
2. **Look up file IDs** via `htan_file_mapping.py` to get `entityId` (Synapse) and `drs_uri` (Gen3)
3. **Download** from the appropriate platform based on access tier

### File Mapping

`htan.files` (`htan files`) bridges BigQuery results and downloads using the HTAN portal's DRS mapping file (~67,000 files):

```bash
htan files update                              # Download/refresh cache
htan files lookup HTA9_1_19512                 # Look up file ID
htan files lookup HTA9_1_19512 --format json   # JSON with download cmds
htan files lookup --file ids.txt               # Batch lookup from file
htan files stats                               # Mapping statistics
```

Cache is stored at `~/.cache/htan-skill/crdcgc_drs_mapping.json` (auto-downloaded on first use).

### Access Tier Determination

Based on the HTAN portal source (`FileTable.tsx` + `processSynapseJSON.ts`):

| Data Level / Type | Access | Platform |
|---|---|---|
| Level 3, Level 4, Auxiliary, Other | Open | Synapse (`entityId`) |
| Level 1-2 sequencing (bulk/-seq assays) with DRS URI | Controlled | Gen3 (`drs_uri`) |
| CODEX Level 1 | Open (exception) | Synapse |
| Specialized assays (electron microscopy, RPPA, slide-seq, mass spec) | Open | Synapse |
| Imaging in dbGaP set with DRS URI | Open | CRDC-GC |

The `infer_access_tier(file_id, level, assay)` function in `htan.files` implements these rules.

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

## CLI Reference

The `htan` command provides a unified interface to all functionality. Install with `pip install htan` (or `uv pip install -e .` for development).

### Portal Queries

```bash
htan query portal tables
htan query portal describe files
htan query portal files --organ Breast --assay "scRNA-seq" --limit 10
htan query portal files --data-file-id HTA9_1_19512 --output json
htan query portal demographics --atlas "HTAN OHSU" --limit 10
htan query portal diagnosis --organ Breast --limit 10
htan query portal sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"
htan query portal manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

### BigQuery Queries

```bash
htan query bq query "How many patients with breast cancer in HTAN?"
htan query bq sql "SELECT COUNT(*) FROM ..."
htan query bq tables
htan query bq tables --versioned
htan query bq describe clinical_tier1_demographics
```

### Downloads

```bash
htan download synapse download syn26535909
htan download synapse download syn26535909 --output-dir ./data --dry-run
htan download gen3 download "drs://dg.4DFC/guid-here" --credentials credentials.json
htan download gen3 download --manifest drs_uris.txt
htan download gen3 resolve "drs://dg.4DFC/guid-here"
```

### Publications

```bash
htan pubs search
htan pubs search --keyword "spatial transcriptomics"
htan pubs search --author "Sorger PK" --format json
htan pubs fetch 12345678
htan pubs fulltext "tumor microenvironment"
```

### Data Model

```bash
htan model fetch
htan model components
htan model attributes "scRNA-seq Level 1"
htan model describe "Library Construction Method"
htan model valid-values "File Format"
htan model search "barcode"
htan model required "Biospecimen"
htan model deps "scRNA-seq Level 1"
```

### File Mapping

```bash
htan files update
htan files lookup HTA9_1_19512 HTA9_1_19553
htan files lookup --file ids.txt --format json
htan files stats
```

### Config

```bash
htan config check
```

### Setup (standalone script)

The setup wizard remains a standalone script (not part of the package):
```bash
python3 skills/htan/scripts/htan_setup.py init
python3 skills/htan/scripts/htan_setup.py --check
python3 skills/htan/scripts/htan_setup.py init-portal
```

## SKILL.md Guidelines

The SKILL.md should:
- Use `name: htan` as the skill name (invoked via `/htan`)
- Description should mention: HTAN data access, portal ClickHouse, Synapse, Gen3/CRDC, BigQuery, and publication search
- Teach Claude the `htan` CLI commands with examples — no MCP server
- Include first-time setup instructions for `Bash(htan *)` permission
- Reference the `htan` CLI for each operation
- Keep under 500 lines — move detailed docs to `references/`

## Security Requirements

- **Never log or display credentials/tokens** in output
- **Validate all user-supplied inputs** before passing to APIs (Synapse IDs, DRS URIs, SQL)
- **Block write operations** in BigQuery and portal ClickHouse queries (no DELETE, DROP, UPDATE, INSERT, CREATE, ALTER, TRUNCATE)
- **Sanitize SQL** — use parameterized queries where possible, never string-interpolate user input into SQL
- **DRS URI validation**: Verify format before attempting resolution
- **File path validation**: Prevent path traversal in download destinations

## Testing Approach

### Unit Tests

```bash
uv run pytest tests/ -v          # Run all 58 tests
uv run pytest tests/ -k portal   # Run portal tests only
```

### CLI Smoke Tests (safe — no credentials exposed)

```bash
# Portal queries
htan query portal tables
htan query portal describe files
htan query portal files --organ Breast --limit 5
htan query portal sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name ORDER BY n DESC"
htan query portal files --organ Breast --dry-run

# PubMed (no auth needed)
htan pubs search --max-results 5
htan pubs search --keyword "spatial transcriptomics" --max-results 3

# Data model (no auth needed)
htan model components
htan model attributes "scRNA-seq Level 1"
htan model describe "File Format"
htan model search "barcode"

# File mapping
htan files update
htan files lookup HTA9_1_19512
htan files stats
```

### Testing in your own terminal (credentials involved)

```bash
# Synapse
htan download synapse download syn26535909 --dry-run

# BigQuery
export GOOGLE_CLOUD_PROJECT="your-project-id"
htan query bq tables
htan query bq describe clinical_tier1_demographics

# Gen3 (requires dbGaP authorization)
htan download gen3 resolve "drs://dg.4DFC/your-guid"
```
