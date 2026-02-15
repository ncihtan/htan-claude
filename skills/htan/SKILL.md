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
   htan init
   ```

3. **Allow `htan` commands** — ask the user to add this to their project `.claude/settings.json`:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(htan *)"
       ]
     }
   }
   ```

All `htan` commands are read-only and safe — credentials are read from local config files, never echoed.

## Critical Rules

**NEVER create a virtual environment or install packages inside the plugin cache directory.** Venvs go in the user's working directory.

**NEVER run `htan_setup.py` via Bash.** It is an interactive wizard that will fail.

---

## CLI Reference

All commands use the `htan` CLI. Run any command with `--help` for full usage.

### Portal Database (Recommended Starting Point)

The fastest way to find HTAN files and get download coordinates. Uses the portal's ClickHouse backend.

```bash
htan query portal files --organ Breast --assay "scRNA-seq" --limit 20
htan query portal sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"
htan query portal tables
htan query portal describe files
htan query portal demographics --atlas "HTAN OHSU"
htan query portal diagnosis --organ Breast --limit 10
htan query portal cases --atlas "HTAN MSK"
htan query portal specimen --organ Colon
htan query portal summary
htan query portal manifest HTA9_1_19512 HTA9_1_19553 --output-dir ./manifests
```

**SQL notes**: Array columns (`organType`, `Gender`, `Race`, etc.) require `arrayExists()`. Use `<>` instead of `!=`. LIMIT is auto-applied. See `references/clickhouse_portal.md` for full schema.

### Publications (No Auth Required)

```bash
htan pubs search --keyword "spatial transcriptomics" --max-results 5
htan pubs search --author "Sorger PK"
htan pubs fetch 12345678
htan pubs fulltext "tumor microenvironment"
```

### Data Model (No Auth Required)

Query the HTAN Phase 1 data model — 1,071 attributes across 64 manifest components with controlled vocabularies.

```bash
htan model components
htan model attributes "scRNA-seq Level 1"
htan model describe "File Format"
htan model valid-values "File Format"
htan model search "barcode"
htan model required "Biospecimen"
htan model deps "scRNA-seq Level 1"
htan model fetch
```

See `references/htan_data_model.md` for the full component catalog and identifier patterns.

### File Mapping (No Auth Required)

Bridges file IDs to download coordinates using the HTAN portal's DRS mapping (~67,000 files).

```bash
htan files lookup HTA9_1_19512
htan files lookup HTA9_1_19512 --format json
htan files update
htan files stats
```

### BigQuery (Requires Google Cloud Credentials)

Deep clinical queries with multi-table joins, assay-level metadata.

```bash
htan query bq tables
htan query bq tables --versioned
htan query bq describe clinical_tier1_demographics
htan query bq sql "SELECT COUNT(*) FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`"
htan query bq query "How many patients with breast cancer?"
```

See `references/bigquery_tables.md` for table schemas and query examples.

### Downloads

Use native platform CLIs — they're simpler and clearer.

**Synapse (open access):**
```bash
synapse get syn26535909
synapse get syn26535909 --downloadLocation ./data
synapse get -r syn12345678    # recursive folder download
```

**Gen3/CRDC (controlled access):**
```bash
gen3-client download-single --profile=htan --guid=<guid>
```

### Configuration

```bash
htan config check    # Check credential status for all services
```

---

## Setup

Use `htan config check` to see what's configured.

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
1. `htan query portal files --organ Breast --assay "scRNA-seq"` — find files with `synapseId` and `drs_uri`
2. `synapse get <synID>` (open access) or `gen3-client download-single --guid <guid>` (controlled)

**Alternative: BigQuery → Download** (for complex clinical queries)
1. `htan query bq sql "SELECT ..."` — find `HTAN_Data_File_ID`
2. `htan query portal manifest <file_ids>` — get download coordinates
3. Download via `synapse get` or `gen3-client`

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
