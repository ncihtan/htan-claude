---
name: htan
description: Access HTAN (Human Tumor Atlas Network) data — query the portal database, download from Synapse and Gen3/CRDC, query metadata in BigQuery, and search HTAN publications on PubMed.
---

# HTAN Skill

Tools for accessing data from the **Human Tumor Atlas Network (HTAN)**, an NCI Cancer Moonshot initiative constructing 3D atlases of human cancers from precancerous lesions to advanced disease.

## Quick Reference

| User Intent | Command |
|---|---|
| Set up environment | `python3 scripts/htan_setup.py` |
| **Find files by organ/assay/atlas (no auth)** | `python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq"` |
| **Get download info for a file ID (no auth)** | `python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json` |
| **Query portal database directly (no auth)** | `python3 scripts/htan_portal.py sql "SELECT ..."` |
| **Generate download manifests** | `python3 scripts/htan_portal.py manifest HTA9_1_19512 --output-dir ./manifests` |
| **Get a quick overview of HTAN data** | `python3 scripts/htan_portal.py summary` |
| **List portal tables** | `python3 scripts/htan_portal.py tables` |
| Search HTAN publications | `python3 scripts/htan_pubmed.py search --keyword "..."` |
| **Look up data model attributes/vocabularies** | `python3 scripts/htan_data_model.py components` |
| Fetch paper details by PMID | `python3 scripts/htan_pubmed.py fetch PMID` |
| Download open-access data | `python3 scripts/htan_synapse.py download synID` |
| Download controlled-access data | `python3 scripts/htan_gen3.py download "drs://dg.4DFC/..."` |
| Ask a question about HTAN metadata | `python3 scripts/htan_bigquery.py query "question"` |
| Run a SQL query on HTAN tables | `python3 scripts/htan_bigquery.py sql "SELECT ..."` |
| List BigQuery tables | `python3 scripts/htan_bigquery.py tables` |
| Describe a table schema | `python3 scripts/htan_bigquery.py describe TABLE` |
| Resolve file ID to download info (offline) | `python3 scripts/htan_file_mapping.py lookup HTAN_DATA_FILE_ID` |
| Refresh file mapping cache | `python3 scripts/htan_file_mapping.py update` |
| Show mapping statistics | `python3 scripts/htan_file_mapping.py stats` |

---

## 1. Setup and Authentication

Run the setup script to check dependencies and authentication:

```bash
python3 scripts/htan_setup.py          # Check and install missing packages
python3 scripts/htan_setup.py --check  # Check only, don't install
python3 scripts/htan_setup.py --service synapse  # Check specific service
```

Three services require authentication:

| Service | Auth Method | Env Var |
|---|---|---|
| **Synapse** (open-access data) | Personal Access Token | `SYNAPSE_AUTH_TOKEN` |
| **Gen3/CRDC** (controlled-access data) | Credentials JSON (requires dbGaP) | `GEN3_API_KEY` |
| **BigQuery** (metadata queries) | Google Cloud ADC | `GOOGLE_CLOUD_PROJECT` |

See `references/authentication_guide.md` for detailed setup instructions.

---

## 2. Querying HTAN Portal Database (ClickHouse) — Recommended Starting Point

The HTAN data portal uses a ClickHouse cloud database with **public read-only access** — no credentials, GCP project, or billing required. This is the fastest way to find HTAN files and get download coordinates.

**Requirements**: None (uses public read-only endpoint)

### Find Files by Organ, Assay, Atlas, Level

```bash
# Browse available files
python3 scripts/htan_portal.py files --limit 10

# Filter by organ and assay
python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --limit 20

# Filter by atlas and data level
python3 scripts/htan_portal.py files --atlas "HTAN HMS" --level "Level 3"

# Look up specific file IDs (returns synapseId and DRS URI)
python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json
```

### Query Clinical Data

```bash
# Patient demographics
python3 scripts/htan_portal.py demographics --atlas "HTAN OHSU" --limit 10

# Diagnosis information
python3 scripts/htan_portal.py diagnosis --organ Breast --limit 10

# Merged cases (demographics + diagnosis)
python3 scripts/htan_portal.py cases --organ Breast

# Biospecimen metadata
python3 scripts/htan_portal.py specimen --preservation FFPE --limit 10
```

### Direct SQL and Schema Exploration

```bash
# List tables
python3 scripts/htan_portal.py tables

# Describe a table schema
python3 scripts/htan_portal.py describe files

# Run direct SQL
python3 scripts/htan_portal.py sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name ORDER BY n DESC"

# Dry run — show SQL without executing
python3 scripts/htan_portal.py files --organ Breast --dry-run
```

### ClickHouse SQL Notes

When writing SQL for the portal ClickHouse database, be aware of these gotchas:

1. **`!=` is not valid** — use `<>` for not-equal comparisons (the script auto-normalizes this, but good to know)
2. **Array columns** in the `files` table require special handling:
   - `organType`, `TissueorOrganofOrigin`, `Gender`, `Race`, `PrimaryDiagnosis`, `biospecimenIds`, `demographicsIds`, `diagnosisIds` are all `Array(String)`
   - Filter with `arrayExists(x -> x = 'value', col)` or `arrayExists(x -> x ILIKE '%value%', col)`
   - Expand with `arrayJoin(col)` to get one row per array element
   - Concatenate with `arrayStringConcat(col, ', ')` for display
   - These same columns are plain `String` in `demographics`, `diagnosis`, `cases` tables
3. **Dirty data**: `DaystoBirth` and `AgeatDiagnosis` contain non-numeric values ('unknown', 'NaN'). Use `toInt32OrNull()` / `toFloat64OrNull()` with `IS NOT NULL` filtering
4. **`drs_uri` is not a column** — extract with `JSONExtractString(viewers, 'crdcGc', 'drs_uri') as drs_uri`
5. **`FileFormat` uses generic names**: `.h5ad` files are stored as `hdf5`, so search `Filename LIKE '%.h5ad'` instead of `FileFormat = 'h5ad'`
6. **Participant IDs in `files` table**: There's no `ParticipantID` column in `files`. Use `arrayJoin(demographicsIds)` to get participant IDs, or join via `demographics`/`cases` tables
7. **`Level` vs `level`** — the column is lowercase `level`
8. **`organ` is not a column** — use `organType` (Array) in `files`, or `TissueorOrganofOrigin` (String) in `diagnosis`/`cases`

### Get a Quick Overview

```bash
# Summary of file/participant counts by atlas, assay, and organ
python3 scripts/htan_portal.py summary
```

### Generate Download Manifests

After finding files, generate manifests for batch download:

```bash
# Generate Synapse + Gen3 manifests from file IDs
python3 scripts/htan_portal.py manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests

# From a file (one ID per line)
python3 scripts/htan_portal.py manifest --file ids.txt --output-dir ./manifests
```

**Output formats**: `--output text` (default), `--output json`, `--output csv`

**Important**: Only read-only SQL is allowed. Write operations are blocked. For the `sql` subcommand, a `LIMIT 1000` is auto-applied if no LIMIT clause is present (use `--no-limit` to skip). Structured subcommands (`files`, `demographics`, etc.) default to `LIMIT 100`.

See `references/clickhouse_portal.md` for full schema documentation and query examples.

---

## 3. Downloading Open-Access Data (Synapse)

HTAN open-access data (de-identified clinical, processed matrices, imaging metadata) is hosted on Synapse. Use BigQuery + file mapping to find entity IDs, then download here.

**Requirements**: `SYNAPSE_AUTH_TOKEN` environment variable or `~/.synapseConfig`

```bash
# Download a file by Synapse entity ID
python3 scripts/htan_synapse.py download syn26535909

# Download to a specific directory
python3 scripts/htan_synapse.py download syn26535909 --output-dir ./data

# Dry run — check metadata without downloading
python3 scripts/htan_synapse.py download syn26535909 --dry-run
```

To find entity IDs, use the end-to-end workflow: query BigQuery for `HTAN_Data_File_ID`, then resolve via `htan_file_mapping.py lookup`.

---

## 4. Downloading Controlled-Access Data (Gen3/CRDC)

Raw sequencing data and protected genomic data are on the Cancer Research Data Commons (CRDC) via Gen3.

**Requirements**: dbGaP authorization for study `phs002371`, Gen3 credentials JSON

```bash
# Download a single file by DRS URI
python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid" --credentials creds.json

# Download multiple files from a manifest
python3 scripts/htan_gen3.py download --manifest drs_uris.txt --credentials creds.json

# Resolve a DRS URI to get the signed download URL
python3 scripts/htan_gen3.py resolve "drs://dg.4DFC/guid" --credentials creds.json

# Dry run — validate URIs and credentials
python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid" --dry-run
```

Credentials are searched in order: `--credentials` flag, `GEN3_API_KEY` env var, `~/.gen3/credentials.json`.

---

## 5. Querying HTAN Metadata (BigQuery)

HTAN metadata is available in Google BigQuery via ISB-CGC. Supports both natural language questions and direct SQL.

**Requirements**: Google Cloud credentials, a project with billing enabled

### Natural Language Queries

When a user asks a question about HTAN metadata, use the `query` subcommand:

```bash
python3 scripts/htan_bigquery.py query "How many patients with breast cancer in HTAN?"
```

This outputs schema context and the user's question. You should then:
1. Read the schema context from the output
2. Generate a safe, read-only SQL query based on the question and schemas
3. Execute it with the `sql` subcommand:

```bash
python3 scripts/htan_bigquery.py sql "SELECT COUNT(DISTINCT HTAN_Participant_ID) as count FROM \`isb-cgc-bq.HTAN_versioned.clinical_tier1_diagnosis_r5\` WHERE Tissue_or_Organ_of_Origin = 'Breast'"
```

### Direct SQL Queries

```bash
# Execute SQL directly
python3 scripts/htan_bigquery.py sql "SELECT HTAN_Center, COUNT(*) FROM \`isb-cgc-bq.HTAN_versioned.clinical_tier1_demographics_r5\` GROUP BY HTAN_Center"

# Output as JSON or CSV
python3 scripts/htan_bigquery.py sql "SELECT ..." --format json
python3 scripts/htan_bigquery.py sql "SELECT ..." --format csv

# Dry run — estimate cost without executing
python3 scripts/htan_bigquery.py sql "SELECT ..." --dry-run
```

### Explore Tables

```bash
# List all available HTAN tables
python3 scripts/htan_bigquery.py tables

# Describe a specific table's schema
python3 scripts/htan_bigquery.py describe clinical_tier1_demographics_r5
```

**Important**: Only read-only SQL (SELECT, WITH) is allowed. The script blocks DELETE, DROP, UPDATE, INSERT, CREATE, ALTER, TRUNCATE, and other write operations. A `LIMIT 1000` is auto-applied if no LIMIT clause is present.

### Key Tables (latest release: r7)

| Table | Description |
|---|---|
| `clinical_tier1_demographics_r7` | Patient demographics (age, sex, race, vital status) |
| `clinical_tier1_diagnosis_r7` | Diagnosis (primary diagnosis, stage, grade, site) |
| `clinical_tier1_followup_r7` | Follow-up and disease status |
| `biospecimen_r7` | Biospecimen metadata (type, preservation, tissue type) |
| `scRNAseq_level1_metadata_r7` | scRNA-seq level 1 (also level2, level3, level4) |
| `scATACseq_level1_metadata_r7` | scATAC-seq level 1 (also level2, level3, level4) |
| `bulkRNAseq_level1_metadata_r7` | Bulk RNA-seq level 1 (also level2, level3) |
| `bulkWES_level1_metadata_r7` | Bulk WES level 1 (also level2, level3) |
| `imaging_level2_metadata_r7` | Imaging metadata (CyCIF, CODEX, MIBI, etc.) |

Assay tables have level-specific variants: level1=raw, level2=aligned, level3=processed, level4=analysis. Use `python3 scripts/htan_bigquery.py tables` to list all 408 tables.

Join on `HTAN_Participant_ID` (clinical tables) or `HTAN_Biospecimen_ID` (biospecimen/assay tables). See `references/bigquery_tables.md` for full schemas and example queries.

---

## 6. Searching HTAN Publications (PubMed)

Search for HTAN-affiliated publications on PubMed and PubMed Central. **No authentication required.**

```bash
# Search all HTAN publications
python3 scripts/htan_pubmed.py search

# Search by keyword
python3 scripts/htan_pubmed.py search --keyword "spatial transcriptomics"

# Search by author
python3 scripts/htan_pubmed.py search --author "Sorger PK"

# Filter by year
python3 scripts/htan_pubmed.py search --year 2024

# Fetch details for specific PMIDs
python3 scripts/htan_pubmed.py fetch 12345678 87654321

# Full-text search across PubMed Central
python3 scripts/htan_pubmed.py fulltext "tumor microenvironment"

# Output as JSON
python3 scripts/htan_pubmed.py search --format json

# Dry run — show query URL without making requests
python3 scripts/htan_pubmed.py search --dry-run
```

HTAN publications are identified by NCI grant numbers (CA233xxx Phase 1, CA294xxx Phase 2) and affiliated last authors.

---

## 7. HTAN Data Model (Phase 1)

Query the formal HTAN Phase 1 data model — 1,071 attributes across 64 manifest components with controlled vocabularies, validation rules, and dependency chains. **No authentication required** (stdlib only, fetches from GitHub).

Source: [ncihtan/data-models](https://github.com/ncihtan/data-models) v25.2.1 (final Phase 1 release)

```bash
# List all 64 manifest components (grouped by category)
python3 scripts/htan_data_model.py components

# List attributes for a specific component
python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"
python3 scripts/htan_data_model.py attributes "Biospecimen"
python3 scripts/htan_data_model.py attributes "Demographics"

# Full detail for one attribute (description, valid values, validation rules, dependencies)
python3 scripts/htan_data_model.py describe "Library Construction Method"

# List all valid values for an attribute
python3 scripts/htan_data_model.py valid-values "File Format"
python3 scripts/htan_data_model.py valid-values "Preservation Method"

# Search attributes by keyword (searches names, descriptions, and valid values)
python3 scripts/htan_data_model.py search "barcode"

# List required attributes for a component
python3 scripts/htan_data_model.py required "Biospecimen"

# Show dependency chain (e.g., scRNA-seq L1 → Biospecimen → Patient)
python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"

# Download/refresh model cache
python3 scripts/htan_data_model.py fetch
python3 scripts/htan_data_model.py fetch --dry-run
```

**Output formats**: `--format text` (default), `--format json`

Cache: `~/.cache/htan-skill/HTAN.model.csv` (auto-downloaded on first use)

See `references/htan_data_model.md` for the full component catalog, controlled vocabularies, and identifier validation rules.

---

## Atlas Centers

| Atlas | Cancer Type | Phase |
|---|---|---|
| HTAN HTAPP | Pan-cancer | 1 |
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

See `references/htan_atlases.md` for grant numbers and detailed cancer type mapping.

---

## End-to-End Data Access Workflow

### Recommended: Portal Query → Download (2 steps, no auth)

The simplest workflow uses the portal ClickHouse database, which includes download coordinates directly:

**Step 1: Find files and get download info**

```bash
python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --output json
# → Returns DataFileID, synapseId, drs_uri, Filename, etc.
```

Or generate batch download manifests:

```bash
python3 scripts/htan_portal.py manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

**Step 2: Download via the appropriate platform**

```bash
# Open access → Synapse (using synapseId from results)
python3 scripts/htan_synapse.py download syn26535909

# Controlled access → Gen3 (using drs_uri from results)
python3 scripts/htan_gen3.py download "drs://dg.4DFC/9ea89378-c9b2-11ed-9a72-63851f9776b7"
```

### Alternative: BigQuery → Download (for complex clinical queries)

For deep clinical queries requiring multi-table joins (follow-up data, assay-level metadata like cell counts or library methods), use BigQuery:

```bash
python3 scripts/htan_bigquery.py query "Find scRNA-seq data for breast cancer"
# → Claude generates SQL, returns HTAN_Data_File_ID and entityId
python3 scripts/htan_synapse.py download syn68499155
```

### Alternative: Offline file mapping

For offline or batch lookups when the portal is unavailable:

```bash
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 --format json
python3 scripts/htan_file_mapping.py lookup --file ids.txt
```

### Access Tier Rules

| Data Level / Type | Access | Platform |
|---|---|---|
| Level 3, Level 4, Auxiliary, Other | Open | Synapse |
| Level 1-2 sequencing (bulk/-seq assays) with DRS URI | Controlled | Gen3 |
| CODEX Level 1 | Open (exception) | Synapse |
| Specialized assays (electron microscopy, RPPA, slide-seq, mass spec) | Open | Synapse |
| Imaging in dbGaP set with DRS URI | Open | CRDC-GC |

### File Mapping Management

```bash
# Download/refresh the mapping cache (~15 MB, cached in .cache/)
python3 scripts/htan_file_mapping.py update

# View mapping statistics (file counts by center)
python3 scripts/htan_file_mapping.py stats
```

The mapping is automatically downloaded on first use. Use `update` to refresh.

---

## HTAN Documentation Manual

The official HTAN Manual at **https://docs.humantumoratlas.org** covers topics beyond what the skill scripts provide. Point users to relevant pages when they ask about:

| Topic | Manual Page |
|---|---|
| What is HTAN? / Network overview | [Introduction](https://docs.humantumoratlas.org/overview/introduction/) |
| HTAN centers and cancer types | [Centers](https://docs.humantumoratlas.org/overview/centers/) |
| How to cite HTAN data | [Citing HTAN](https://docs.humantumoratlas.org/data_access/citing_htan/) — cite Rozenblatt-Rosen et al. 2020 (Cell) + de Bruijn et al. 2025 (Nat Methods) |
| Open vs. controlled access explained | [Data Access Overview](https://docs.humantumoratlas.org/overview/data_access/) |
| How to request dbGaP access | [Requesting dbGaP Access](https://docs.humantumoratlas.org/data_access/db_gap/) — study phs002371 |
| Using the data portal interactively | [Using the Portal](https://docs.humantumoratlas.org/data_access/portal/) |
| BigQuery access and examples | [Google BigQuery](https://docs.humantumoratlas.org/data_access/biq_query/) |
| Gen3-client CLI setup | [Gen3-Client](https://docs.humantumoratlas.org/data_access/cds_gen3/) |
| Data model and standards | [Data Model Introduction](https://docs.humantumoratlas.org/data_model/overview/) |
| HTAN identifier formats | [Identifiers](https://docs.humantumoratlas.org/data_model/identifiers/) |
| Data levels (1-4) and clinical tiers | [Data Levels](https://docs.humantumoratlas.org/data_model/data_levels/) |
| CellxGene visualization | [CellxGene](https://docs.humantumoratlas.org/data_visualization/cell_by_gene/) |
| Minerva imaging viewer | [Minerva](https://docs.humantumoratlas.org/data_visualization/minerva/) |
| Xena multiomics visualization | [Xena](https://docs.humantumoratlas.org/data_visualization/xena/) |
| Data governance and policies | [Governance](https://docs.humantumoratlas.org/addtnl_info/governance/) |
| FAQ | [FAQ](https://docs.humantumoratlas.org/faq/) |

See `references/htan_docs_manual.md` for the full 41-page site map, key facts, identifier regex patterns, and platform details.

---

## Reference Documents

| Document | Description |
|---|---|
| `references/clickhouse_portal.md` | Portal ClickHouse schema, queries, and limitations |
| `references/authentication_guide.md` | Auth setup for Synapse, Gen3, and BigQuery |
| `references/htan_atlases.md` | Atlas centers, cancer types, and grant numbers |
| `references/htan_data_model.md` | Data model v25.2.1: 64 components, controlled vocabularies, validation rules, identifiers |
| `references/bigquery_tables.md` | BigQuery table schemas and example SQL queries |
| `references/htan_docs_manual.md` | HTAN Manual site map, citations, identifiers, platforms, FAQ |

---

## Security Notes

- **Credentials**: Never log or display tokens, API keys, or credentials in output
- **SQL safety**: All SQL is validated — only SELECT/WITH queries are allowed; write operations are blocked
- **DRS URI validation**: URIs are validated against the expected `drs://dg.4DFC/` format before resolution
- **Input validation**: Synapse IDs, table names, and file paths are validated before use
- **Path traversal**: Output directories are resolved to absolute paths to prevent traversal
