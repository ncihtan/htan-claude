---
name: htan
description: Access HTAN (Human Tumor Atlas Network) data — query the portal database, download from Synapse and Gen3/CRDC, query metadata in BigQuery, and search HTAN publications on PubMed.
---

# HTAN Skill

Tools for accessing data from the **Human Tumor Atlas Network (HTAN)**, an NCI Cancer Moonshot initiative constructing 3D atlases of human cancers from precancerous lesions to advanced disease.

## First-Time Setup

On first use, check if the `htan` CLI is available by running `htan --version`. If it is not installed, guide the user through setup:

1. **Create a venv in the user's project** (not in the plugin directory):
   ```bash
   uv venv && uv pip install "${CLAUDE_PLUGIN_ROOT}"
   ```
   Or without uv:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate && pip install "${CLAUDE_PLUGIN_ROOT}"
   ```

2. **Configure credentials** (portal, Synapse, etc.):
   ```bash
   uv run htan init
   ```

3. **Allow `htan` commands** — ask the user to add this to their project `.claude/settings.json`:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(uv run htan *)"
       ]
     }
   }
   ```

All `htan` commands are read-only and safe — credentials are read from local config files, never echoed.

## Critical Rules

**ALWAYS prefix commands with `uv run`** when a venv exists (e.g., `uv run htan query portal tables`). NEVER use `source .venv/bin/activate &&` — `uv run` handles the venv automatically.

**NEVER create a virtual environment or install packages inside the plugin cache directory.** Venvs go in the user's working directory.

**NEVER run `htan_setup.py` via Bash.** It is an interactive wizard that will fail.

---

## CLI Reference

All commands use `uv run htan ...`. NEVER use `source .venv/bin/activate`. Run any command with `--help` for full usage.

### Portal Database (Recommended Starting Point)

The fastest way to find HTAN files and get download coordinates. Uses the portal's ClickHouse backend.

```bash
uv run htan query portal files --organ Breast --assay "scRNA-seq" --limit 20
uv run htan query portal sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"
uv run htan query portal tables
uv run htan query portal describe files
uv run htan query portal demographics --atlas "HTAN OHSU"
uv run htan query portal diagnosis --organ Breast --limit 10
uv run htan query portal cases --atlas "HTAN MSK"
uv run htan query portal specimen --organ Colon
uv run htan query portal summary
uv run htan query portal manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

**SQL notes**: Array columns (`organType`, `Gender`, `Race`, etc.) require `arrayExists()`. Use `<>` instead of `!=`. LIMIT is auto-applied. See `references/clickhouse_portal.md` for full schema.

### Publications (No Auth Required)

```bash
uv run htan pubs search --keyword "spatial transcriptomics" --max-results 5
uv run htan pubs search --author "Sorger PK"
uv run htan pubs fetch 12345678
uv run htan pubs fulltext "tumor microenvironment"
```

### Data Model (No Auth Required)

Query the HTAN Phase 1 data model — 1,071 attributes across 64 manifest components with controlled vocabularies.

```bash
uv run htan model components
uv run htan model attributes "scRNA-seq Level 1"
uv run htan model describe "File Format"
uv run htan model valid-values "File Format"
uv run htan model search "barcode"
uv run htan model required "Biospecimen"
uv run htan model deps "scRNA-seq Level 1"
uv run htan model fetch
```

See `references/htan_data_model.md` for the full component catalog and identifier patterns.

### File Mapping (No Auth Required)

Bridges file IDs to download coordinates using the HTAN portal's DRS mapping (~67,000 files).

```bash
uv run htan files lookup HTA9_1_19512
uv run htan files lookup HTA9_1_19512 --format json
uv run htan files update
uv run htan files stats
```

### BigQuery (Requires Google Cloud Credentials)

Deep clinical queries, assay-level metadata (cell counts, library methods, **file sizes**).

```bash
uv run htan query bq tables
uv run htan query bq tables --versioned
uv run htan query bq describe clinical_tier1_demographics
uv run htan query bq sql "SELECT COUNT(*) FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`"
uv run htan query bq query "How many patients with breast cancer?"
```

See `references/bigquery_tables.md` for table schemas and query examples.

### Downloads

Use native platform CLIs — they're simpler and clearer.

**Synapse (open access):**
```bash
uv run synapse get syn26535909
uv run synapse get syn26535909 --downloadLocation ./data
uv run synapse get -r syn12345678    # recursive folder download
```

**Gen3/CRDC (controlled access):**
```bash
gen3-client download-single --profile=htan --guid=<guid>
```

### Configuration

```bash
uv run htan config check    # Check credential status for all services
```

---

## Setup

Use `uv run htan config check` to see what's configured.

**Credential storage**:
- **Portal ClickHouse**: `~/.config/htan-skill/portal.json` (or OS Keychain)
- **Synapse**: `SYNAPSE_AUTH_TOKEN` env var or `~/.synapseConfig`
- **Gen3**: `~/.gen3/credentials.json` (requires dbGaP authorization)
- **BigQuery**: Application Default Credentials (`gcloud auth application-default login`)

**No-auth commands** (always work, no setup needed):
- `htan pubs ...` — PubMed search
- `htan model ...` — data model queries
- `htan files ...` — file mapping lookups

---

## Access Tier Rules

| Data Level / Type | Access | Platform |
|---|---|---|
| Level 3-4, Auxiliary, Other | Open | Synapse (`synapseId`) |
| Level 1-2 sequencing with DRS URI | Controlled | Gen3 (`drs_uri`) |
| CODEX Level 1, specialized assays (EM, RPPA, slide-seq, mass spec) | Open | Synapse |

---

## Workflows

**Recommended: Portal → Download** (2 steps)
1. `uv run htan query portal files --organ Breast --assay "scRNA-seq"` — find files with `synapseId` and `drs_uri`
2. `uv run synapse get <synID>` (open access) or `gen3-client download-single --guid <guid>` (controlled)

**Alternative: BigQuery → Download** (for complex clinical queries)
1. `uv run htan query bq sql "SELECT ..."` — find `HTAN_Data_File_ID`
2. `uv run htan query portal manifest <file_ids>` — get download coordinates
3. Download via `uv run synapse get` or `gen3-client`

## Platform Data Gaps

| Data | Portal | BigQuery |
|---|---|---|
| File size | Not available | `File_Size` (INTEGER, bytes) in assay metadata tables |
| Cell counts | Not available | `Cell_Total` in scRNAseq tables |
| Library method | Not available | `Library_Construction_Method` in assay tables |
| Download coordinates | `synapseId`, DRS URI | `entityId` only |

Note: `File_Size` and `entityId` exist in **all** BigQuery assay metadata tables (scRNAseq, bulkRNAseq, imaging, scATACseq, electron_microscopy, bulkWES, etc.), not just scRNAseq.

**Fallback rule**: If a query needs file sizes, cell counts, or assay-level metadata not in the portal, use BigQuery assay metadata tables (e.g., `scRNAseq_level3_metadata_current`, `imaging_level2_metadata_current`). Then use portal or `htan files lookup` for download coordinates.

**HTAN Documentation**: See `references/htan_docs_manual.md` for citing HTAN, dbGaP access, data levels, visualization tools.

**Atlas Centers**: See `references/htan_atlases.md` for the 14 atlas centers, cancer types, and grant numbers.

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
- **Signed URLs**: Gen3 DRS resolution returns sensitive signed URLs — do not log them
