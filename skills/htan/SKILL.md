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

## First-Run Setup

On first invocation (or when services are not configured), follow this flow **in order**.

### Step 1: Check status

```bash
python3 "$HTAN_DIR/scripts/htan_quicksetup.py" check
```

This outputs JSON with the status of each service. Parse it and present a dashboard to the user:

```
HTAN Skill — Setup Status

✅ Synapse credentials    ~/.synapseConfig found
❌ Portal credentials     Not configured — requires setup
⚠️  Gen3/CRDC              Optional — needed for controlled-access downloads
⚠️  BigQuery               Optional — needed for advanced metadata queries
```

### Step 2: Synapse auth (required)

If `status.synapse.configured` is `false`: **stop and tell the user** they need to create Synapse credentials. Do NOT try to create the file yourself. Show them:

> **Synapse credentials are required for HTAN setup.** Please do the following:
>
> 1. Create a free account at https://www.synapse.org
> 2. Go to **Account Settings > Personal Access Tokens**: https://www.synapse.org/#!PersonalAccessTokens:
> 3. Create a token with **view** and **download** permissions
> 4. Create the file `~/.synapseConfig`:
>    ```
>    [authentication]
>    authtoken = <your-token-here>
>    ```
>
> Once done, invoke `/htan` again to continue setup.

**Do not proceed past this step** if Synapse is not configured. The remaining steps depend on it.

### Step 3: Create venv and install dependencies

If there is no `.venv` in the user's current working directory, create one. This is needed before the portal step (which requires `synapseclient`).

```bash
python3 "$HTAN_DIR/scripts/htan_quicksetup.py" venv
```

This creates `.venv/` in the current working directory with all HTAN dependencies. **Not** in the plugin cache.

### Step 4: Auto-configure portal credentials

If `status.portal.configured` is `false`, download credentials from Synapse. Must use the venv Python since it requires `synapseclient`:

```bash
.venv/bin/python "$HTAN_DIR/scripts/htan_quicksetup.py" portal
```

This will:
- Log in to Synapse using `~/.synapseConfig`
- Auto-join the HTAN Claude Skill Users team if eligible
- Download and save credentials to `~/.config/htan-skill/portal.json`
- Verify connectivity

If it fails with an access error, tell the user to join the team at https://www.synapse.org/Team:3574960.

### Step 5: Show final status and optional setup

After steps 1-4, present the updated status. For optional items, show instructions:

- **Gen3/CRDC** (controlled-access data): Requires dbGaP authorization for study `phs002371` — apply at https://dbgap.ncbi.nlm.nih.gov/
- **BigQuery** (advanced metadata queries): Run `gcloud auth application-default login` in your terminal

### When setup is already complete

If Step 1 shows synapse + portal are both configured, **skip all setup steps** and proceed directly to the user's request. No need to create a venv for portal/pubmed/data-model queries (they use stdlib only).

Only create a venv if the user needs Synapse downloads, Gen3 downloads, or BigQuery queries.

**No-auth tools** (always work, no setup needed):
- `htan_pubmed.py` — PubMed search (stdlib only)
- `htan_data_model.py` — data model queries (stdlib only, fetches from GitHub)

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
