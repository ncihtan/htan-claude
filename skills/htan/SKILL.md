---
name: htan
description: Access HTAN (Human Tumor Atlas Network) data — query the portal database, download from Synapse and Gen3/CRDC, query metadata in BigQuery, and search HTAN publications on PubMed.
---

# HTAN Skill

Tools for accessing data from the **Human Tumor Atlas Network (HTAN)**, an NCI Cancer Moonshot initiative constructing 3D atlases of human cancers from precancerous lesions to advanced disease.

## Critical Rules

**NEVER run `htan_setup.py` via Bash.** It is an interactive wizard that will fail or create broken state.

**NEVER `cd` into the plugin cache directory.** Always use absolute paths via `$HTAN_DIR`.

**NEVER create a virtual environment or install packages inside the plugin cache directory.** Venvs go in the user's working directory.

## MCP Tools (Local Claude Code)

The HTAN portal MCP server (`servers/htan_portal_server.py`) provides direct tool access for **local Claude Code** sessions. When these tools are available, prefer them over Bash script invocation:

| MCP Tool | Equivalent Script Command |
|----------|--------------------------|
| `htan_portal_files` | `htan_portal.py files` |
| `htan_portal_query` | `htan_portal.py sql` |
| `htan_portal_summary` | `htan_portal.py summary` |
| `htan_portal_tables` | `htan_portal.py tables` |
| `htan_portal_describe` | `htan_portal.py describe` |
| `htan_portal_clinical` | `htan_portal.py demographics/diagnosis/cases/specimen` |
| `htan_portal_manifest` | `htan_portal.py manifest` |
| `htan_setup_status` | `htan_quicksetup.py check` |

The MCP server auto-downloads portal credentials from Synapse on first use if `~/.synapseConfig` is configured. No manual setup needed.

**Cowork mode limitation**: Plugin-provided MCP servers do **not** currently appear in Cowork sessions due to a platform limitation ([#20377](https://github.com/anthropics/claude-code/issues/20377), [#15308](https://github.com/anthropics/claude-code/issues/15308)). In Cowork, use the Bash script equivalents instead. If you need MCP tools in Cowork, you can try adding the server at user scope on the host machine:

```bash
claude mcp add --scope user --transport stdio htan-portal \
  -- uv run /path/to/htan-skill/skills/htan/servers/htan_portal_server.py
```

**No-auth tools** (PubMed, data model) work in both local and Cowork modes via Bash — they need no credentials.

---

## Running Scripts

Set this variable once at the start of the session and use it for ALL script invocations:

```bash
HTAN_DIR="$(dirname "$(find ~/.claude/plugins -path '*/htan/*/skills/htan/SKILL.md' -print -quit 2>/dev/null)")"
echo "$HTAN_DIR"
```

Then run scripts as:
```bash
python3 "$HTAN_DIR/scripts/htan_portal.py" tables
```

## Setup

Run `/htan:setup` to check credential status and configure access.
To check status only: `/htan:setup check`

**Credential storage**:
- **Local Claude Code**: Portal credentials stored in OS Keychain (encrypted at rest)
- **Cowork**: Set `SYNAPSE_AUTH_TOKEN` and `HTAN_PORTAL_CREDENTIALS` (JSON) in project environment variables
- Backward compat: `~/.config/htan-skill/portal.json` config file also works

**No-auth tools** (always work, no setup needed):
- `htan_pubmed.py` — PubMed search (stdlib only)
- `htan_data_model.py` — data model queries (stdlib only)

Only create a venv if the user needs Synapse downloads, Gen3 downloads, or BigQuery queries.
Portal setup and all portal queries are stdlib-only (no venv needed).

---

## Quick Reference

| User Intent | Script + Args |
|---|---|
| **Find files by organ/assay/atlas** | `htan_portal.py files --organ Breast --assay "scRNA-seq"` |
| **Get download info for a file ID** | `htan_portal.py files --data-file-id HTA9_1_19512 --output json` |
| **Query portal database directly** | `htan_portal.py sql "SELECT ..."` |
| **Generate download manifests** | `htan_portal.py manifest HTA9_1_19512 --output-dir ./manifests` |
| **Get a quick overview of HTAN data** | `htan_portal.py summary` |
| **List portal tables** | `htan_portal.py tables` |
| **Describe a table schema** | `htan_portal.py describe files` |
| Search HTAN publications | `htan_pubmed.py search --keyword "..."` |
| Fetch paper details by PMID | `htan_pubmed.py fetch PMID` |
| Look up data model attributes | `htan_data_model.py components` |
| Download open-access data | `htan_synapse.py download synID` |
| Download controlled-access data | `htan_gen3.py download "drs://dg.4DFC/..."` |
| Ask a question about HTAN metadata | `htan_bigquery.py query "question"` |
| Run a SQL query on HTAN tables | `htan_bigquery.py sql "SELECT ..."` |
| Resolve file ID to download info | `htan_file_mapping.py lookup HTAN_DATA_FILE_ID` |

All scripts accept `--help` for full usage. Prefix each with `python3 "$HTAN_DIR/scripts/"`.

---

## Portal Database (ClickHouse) — Recommended Starting Point

The fastest way to find HTAN files and get download coordinates. Uses the portal's ClickHouse backend.

```bash
# Find files
python3 "$HTAN_DIR/scripts/htan_portal.py" files --organ Breast --assay "scRNA-seq" --limit 20
python3 "$HTAN_DIR/scripts/htan_portal.py" files --atlas "HTAN HMS" --level "Level 3"
python3 "$HTAN_DIR/scripts/htan_portal.py" files --data-file-id HTA9_1_19512 --output json

# Clinical data
python3 "$HTAN_DIR/scripts/htan_portal.py" demographics --atlas "HTAN OHSU" --limit 10
python3 "$HTAN_DIR/scripts/htan_portal.py" diagnosis --organ Breast --limit 10
python3 "$HTAN_DIR/scripts/htan_portal.py" cases --organ Breast
python3 "$HTAN_DIR/scripts/htan_portal.py" specimen --preservation FFPE --limit 10

# Schema and SQL
python3 "$HTAN_DIR/scripts/htan_portal.py" tables
python3 "$HTAN_DIR/scripts/htan_portal.py" describe files
python3 "$HTAN_DIR/scripts/htan_portal.py" sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name ORDER BY n DESC"

# Overview and manifests
python3 "$HTAN_DIR/scripts/htan_portal.py" summary
python3 "$HTAN_DIR/scripts/htan_portal.py" manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

**Output formats**: `--output text` (default), `--output json`, `--output csv`. All SQL is read-only; write operations are blocked. For `sql`, a `LIMIT 1000` is auto-applied if no LIMIT clause present (use `--no-limit` to skip). Structured subcommands default to `LIMIT 100`.

See `references/clickhouse_portal.md` for full schema, SQL gotchas (array columns, JSON extraction, column naming), and query examples.

---

## Downloading Data

### Open Access (Synapse)

De-identified clinical, processed matrices, and imaging metadata. Requires `SYNAPSE_AUTH_TOKEN` or `~/.synapseConfig`.

```bash
python3 "$HTAN_DIR/scripts/htan_synapse.py" download syn26535909
python3 "$HTAN_DIR/scripts/htan_synapse.py" download syn26535909 --output-dir ./data
python3 "$HTAN_DIR/scripts/htan_synapse.py" download syn26535909 --dry-run
```

### Controlled Access (Gen3/CRDC)

Raw sequencing and protected genomic data. Requires dbGaP authorization for study `phs002371`.

```bash
python3 "$HTAN_DIR/scripts/htan_gen3.py" download "drs://dg.4DFC/guid" --credentials creds.json
python3 "$HTAN_DIR/scripts/htan_gen3.py" download --manifest drs_uris.txt --credentials creds.json
python3 "$HTAN_DIR/scripts/htan_gen3.py" resolve "drs://dg.4DFC/guid" --credentials creds.json
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
python3 "$HTAN_DIR/scripts/htan_file_mapping.py" update
python3 "$HTAN_DIR/scripts/htan_file_mapping.py" lookup HTA9_1_19512
python3 "$HTAN_DIR/scripts/htan_file_mapping.py" lookup --file ids.txt
python3 "$HTAN_DIR/scripts/htan_file_mapping.py" stats
```

---

## BigQuery Metadata Queries

Deep clinical queries with multi-table joins, assay-level metadata (cell counts, library methods), and follow-up data. Requires Google Cloud credentials with billing project.

```bash
python3 "$HTAN_DIR/scripts/htan_bigquery.py" query "How many patients with breast cancer in HTAN?"
python3 "$HTAN_DIR/scripts/htan_bigquery.py" sql "SELECT COUNT(DISTINCT HTAN_Participant_ID) FROM \`isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current\` WHERE Tissue_or_Organ_of_Origin = 'Breast'"
python3 "$HTAN_DIR/scripts/htan_bigquery.py" tables
python3 "$HTAN_DIR/scripts/htan_bigquery.py" describe clinical_tier1_demographics
```

Only read-only SQL allowed. `LIMIT 1000` auto-applied if no LIMIT clause present. Join on `HTAN_Participant_ID` (clinical) or `HTAN_Biospecimen_ID` (biospecimen/assay).

See `references/bigquery_tables.md` for table schemas, naming conventions, and example queries.

---

## Publication Search (PubMed)

Search HTAN-affiliated publications by NCI grant numbers and affiliated authors. **No authentication required.**

```bash
python3 "$HTAN_DIR/scripts/htan_pubmed.py" search
python3 "$HTAN_DIR/scripts/htan_pubmed.py" search --keyword "spatial transcriptomics"
python3 "$HTAN_DIR/scripts/htan_pubmed.py" search --author "Sorger PK" --year 2024
python3 "$HTAN_DIR/scripts/htan_pubmed.py" fetch 12345678 87654321
python3 "$HTAN_DIR/scripts/htan_pubmed.py" fulltext "tumor microenvironment"
```

---

## Data Model (Phase 1)

Query the HTAN Phase 1 data model — 1,071 attributes across 64 manifest components with controlled vocabularies and validation rules. **No authentication required** (stdlib only, fetches from GitHub).

```bash
python3 "$HTAN_DIR/scripts/htan_data_model.py" components
python3 "$HTAN_DIR/scripts/htan_data_model.py" attributes "scRNA-seq Level 1"
python3 "$HTAN_DIR/scripts/htan_data_model.py" describe "Library Construction Method"
python3 "$HTAN_DIR/scripts/htan_data_model.py" valid-values "File Format"
python3 "$HTAN_DIR/scripts/htan_data_model.py" search "barcode"
python3 "$HTAN_DIR/scripts/htan_data_model.py" required "Biospecimen"
python3 "$HTAN_DIR/scripts/htan_data_model.py" deps "scRNA-seq Level 1"
python3 "$HTAN_DIR/scripts/htan_data_model.py" fetch
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
