---
name: htan
description: Access HTAN (Human Tumor Atlas Network) data — query the portal database, download from Synapse and Gen3/CRDC, query metadata in BigQuery, and search HTAN publications on PubMed.
---

# HTAN Skill

Tools for accessing data from the **Human Tumor Atlas Network (HTAN)**, an NCI Cancer Moonshot initiative constructing 3D atlases of human cancers from precancerous lesions to advanced disease.

## IMPORTANT: Do Not Run Setup Scripts

**NEVER run `htan_setup.py init`, `htan_setup.py init-portal`, `htan_setup.py --check`, or any setup/init command via the Bash tool.** These require interactive Synapse login and will fail or create broken state when run through Claude.

Instead, **before doing anything else**, check if the portal is configured:

```bash
test -f ~/.config/htan-skill/portal.json && echo "CONFIGURED" || echo "NOT_CONFIGURED"
```

- If `CONFIGURED`: proceed to the user's request using the scripts below.
- If `NOT_CONFIGURED`: **stop and tell the user** they need to run setup in their own terminal first. Give them this message:

  "The HTAN portal credentials aren't set up yet. Please run this in your own terminal (it requires interactive Synapse login that can't work through Claude):"

  ```
  python3 scripts/htan_setup.py init
  ```

  "You'll need to join the [HTAN Claude Skill Users](https://www.synapse.org/Team:3574960) Synapse team first. Once setup is complete, come back and invoke `/htan` again."

**No-auth tools** — these work immediately without any setup:
- `htan_pubmed.py` — PubMed search
- `htan_data_model.py` — data model queries

---

## Quick Reference

| User Intent | Command |
|---|---|
| **Find files by organ/assay/atlas** | `python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq"` |
| **Get download info for a file ID** | `python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json` |
| **Query portal database directly** | `python3 scripts/htan_portal.py sql "SELECT ..."` |
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
| Describe a table schema | `python3 scripts/htan_bigquery.py describe TABLE` |
| Resolve file ID to download info (offline) | `python3 scripts/htan_file_mapping.py lookup HTAN_DATA_FILE_ID` |

---

---

## 2. Portal Database (ClickHouse) — Recommended Starting Point

The fastest way to find HTAN files and get download coordinates. Uses the portal's ClickHouse backend with credentials gated through Synapse team membership.

**First-time setup**: Join the [HTAN Claude Skill Users](https://www.synapse.org/Team:3574960) team, then run `python3 scripts/htan_setup.py init-portal`.

```bash
# Find files
python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --limit 20
python3 scripts/htan_portal.py files --atlas "HTAN HMS" --level "Level 3"
python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json

# Clinical data
python3 scripts/htan_portal.py demographics --atlas "HTAN OHSU" --limit 10
python3 scripts/htan_portal.py diagnosis --organ Breast --limit 10
python3 scripts/htan_portal.py cases --organ Breast
python3 scripts/htan_portal.py specimen --preservation FFPE --limit 10

# Schema and SQL
python3 scripts/htan_portal.py tables
python3 scripts/htan_portal.py describe files
python3 scripts/htan_portal.py sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name ORDER BY n DESC"

# Overview and manifests
python3 scripts/htan_portal.py summary
python3 scripts/htan_portal.py manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

**Output formats**: `--output text` (default), `--output json`, `--output csv`. All SQL is read-only; write operations are blocked. For `sql`, a `LIMIT 1000` is auto-applied if no LIMIT clause present (use `--no-limit` to skip). Structured subcommands default to `LIMIT 100`.

See `references/clickhouse_portal.md` for full schema, SQL gotchas (array columns, JSON extraction, column naming), and query examples.

---

## 3. Downloading Data

### Open Access (Synapse)

De-identified clinical, processed matrices, and imaging metadata. Requires `SYNAPSE_AUTH_TOKEN` or `~/.synapseConfig`.

```bash
python3 scripts/htan_synapse.py download syn26535909
python3 scripts/htan_synapse.py download syn26535909 --output-dir ./data
python3 scripts/htan_synapse.py download syn26535909 --dry-run
```

### Controlled Access (Gen3/CRDC)

Raw sequencing and protected genomic data. Requires dbGaP authorization for study `phs002371`.

```bash
python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid" --credentials creds.json
python3 scripts/htan_gen3.py download --manifest drs_uris.txt --credentials creds.json
python3 scripts/htan_gen3.py resolve "drs://dg.4DFC/guid" --credentials creds.json
python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid" --dry-run
```

### Access Tier Rules

| Data Level / Type | Access | Platform |
|---|---|---|
| Level 3-4, Auxiliary, Other | Open | Synapse |
| Level 1-2 sequencing with DRS URI | Controlled | Gen3 |
| CODEX Level 1, specialized assays (EM, RPPA, slide-seq, mass spec) | Open | Synapse |

### File Mapping (offline lookups)

Bridges BigQuery file IDs to download coordinates when the portal is unavailable:

```bash
python3 scripts/htan_file_mapping.py update                    # Refresh cache
python3 scripts/htan_file_mapping.py lookup HTA9_1_19512       # Single lookup
python3 scripts/htan_file_mapping.py lookup --file ids.txt     # Batch lookup
python3 scripts/htan_file_mapping.py stats                     # Mapping statistics
```

---

## 4. BigQuery Metadata Queries

Deep clinical queries with multi-table joins, assay-level metadata (cell counts, library methods), and follow-up data. Requires Google Cloud credentials with billing project.

```bash
# Natural language → SQL workflow
python3 scripts/htan_bigquery.py query "How many patients with breast cancer in HTAN?"
# Read the schema context output, generate SQL, then execute:
python3 scripts/htan_bigquery.py sql "SELECT COUNT(DISTINCT HTAN_Participant_ID) FROM \`isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current\` WHERE Tissue_or_Organ_of_Origin = 'Breast'"

# Direct SQL
python3 scripts/htan_bigquery.py sql "SELECT HTAN_Center, COUNT(*) FROM \`isb-cgc-bq.HTAN.clinical_tier1_demographics_current\` GROUP BY HTAN_Center" --format json

# Explore tables
python3 scripts/htan_bigquery.py tables
python3 scripts/htan_bigquery.py describe clinical_tier1_demographics
```

Only read-only SQL allowed. `LIMIT 1000` auto-applied if no LIMIT clause present. Join on `HTAN_Participant_ID` (clinical) or `HTAN_Biospecimen_ID` (biospecimen/assay).

See `references/bigquery_tables.md` for table schemas, naming conventions, and example queries.

---

## 5. Publication Search (PubMed)

Search HTAN-affiliated publications by NCI grant numbers and affiliated authors. **No authentication required.**

```bash
python3 scripts/htan_pubmed.py search                                     # All HTAN publications
python3 scripts/htan_pubmed.py search --keyword "spatial transcriptomics"
python3 scripts/htan_pubmed.py search --author "Sorger PK" --year 2024
python3 scripts/htan_pubmed.py fetch 12345678 87654321                    # Fetch by PMID
python3 scripts/htan_pubmed.py fulltext "tumor microenvironment"          # PMC full-text
python3 scripts/htan_pubmed.py search --format json --dry-run
```

---

## 6. Data Model (Phase 1)

Query the HTAN Phase 1 data model — 1,071 attributes across 64 manifest components with controlled vocabularies and validation rules. **No authentication required** (stdlib only, fetches from GitHub).

```bash
python3 scripts/htan_data_model.py components                             # List all 64 components
python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"         # Component attributes
python3 scripts/htan_data_model.py describe "Library Construction Method" # Full attribute detail
python3 scripts/htan_data_model.py valid-values "File Format"             # Valid values
python3 scripts/htan_data_model.py search "barcode"                       # Keyword search
python3 scripts/htan_data_model.py required "Biospecimen"                 # Required fields
python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"               # Dependency chain
python3 scripts/htan_data_model.py fetch                                  # Download/refresh cache
```

See `references/htan_data_model.md` for the full component catalog, controlled vocabularies, and identifier patterns.

---

## Workflows

**Recommended: Portal → Download** (2 steps, simplest)
1. `htan_portal.py files` to find files — returns `synapseId` and `drs_uri`
2. `htan_synapse.py download` (open access) or `htan_gen3.py download` (controlled)

**Alternative: BigQuery → Download** (for complex clinical queries needing multi-table joins)
1. `htan_bigquery.py query/sql` to find `HTAN_Data_File_ID`
2. `htan_file_mapping.py lookup` to get download coordinates
3. Download via Synapse or Gen3

**HTAN Documentation**: For topics like citing HTAN, dbGaP access requests, data levels, visualization tools (CellxGene, Minerva, Xena), and governance, see `references/htan_docs_manual.md`.

**Atlas Centers**: For the 14 atlas centers, their cancer types, and grant numbers, see `references/htan_atlases.md`.

---

## Reference Documents

| Document | When to Read |
|---|---|
| `references/clickhouse_portal.md` | Writing portal SQL — schema, array columns, JSON extraction, common mistakes |
| `references/bigquery_tables.md` | Writing BigQuery SQL — table schemas, naming conventions, example queries |
| `references/authentication_guide.md` | Setting up credentials for Synapse, Gen3, BigQuery |
| `references/htan_data_model.md` | Looking up components, controlled vocabularies, identifier patterns |
| `references/htan_atlases.md` | Atlas centers, cancer types, grant numbers |
| `references/htan_docs_manual.md` | HTAN Manual site map, citing HTAN, dbGaP access, visualization tools |

---

## Security Notes

- **Credentials**: Never log or display tokens, API keys, or credentials in output
- **SQL safety**: All SQL is validated — only SELECT/WITH allowed; write operations blocked
- **Input validation**: DRS URIs, Synapse IDs, table names, and file paths are validated before use
