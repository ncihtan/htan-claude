# HTAN Skill for Claude Code

A Claude Code plugin for working with the **Human Tumor Atlas Network (HTAN)** — an NCI Cancer Moonshot initiative constructing 3D atlases of the dynamic cellular, morphological, and molecular features of human cancers as they evolve from precancerous lesions to advanced disease.

![frame_0008](https://github.com/user-attachments/assets/e26f18ec-cd74-477e-914f-b25dfd29a3b2)

## What It Does

| Capability | Auth Required | Description |
|---|---|---|
| **Portal queries** (ClickHouse) | Synapse team membership | Query file metadata, clinical data, download coordinates |
| **Data model** | None | Query HTAN data model components, attributes, controlled vocabularies |
| **PubMed search** | None | Search HTAN-affiliated publications by keyword, author, year |
| **File mapping** | None | Resolve HTAN file IDs to Synapse/Gen3 download coordinates |
| **Synapse download** | Synapse token | Download open-access data (processed matrices, clinical) |
| **Gen3/CRDC download** | Gen3 credentials + dbGaP | Download controlled-access data (raw sequencing) |
| **BigQuery metadata** | Google Cloud ADC | Query HTAN metadata tables in ISB-CGC |

## Install (Users)

### 1. Add the plugin to Claude Code

```bash
# From the marketplace
/plugin marketplace add ncihtan/htan-claude
/plugin install htan@htan-claude
```

### 2. Set up and go

Invoke the skill with `/htan`. On first use, Claude will:

1. Create a venv in your project and install the `htan` CLI from the plugin
2. Run `uv run htan init` to configure credentials
3. Suggest adding `Bash(uv run htan *)` to your project permissions for smooth usage

Then just ask:

```
"List all scRNA-seq files from breast cancer in HTAN"
"Search HTAN publications about spatial transcriptomics"
"What attributes are required for scRNA-seq Level 1 manifests?"
```

## Demo Outputs

Example outputs from running the skill headlessly via `claude -p`:

| Prompt | Output |
|---|---|
| Give me an overview of what data is available in HTAN | [01_overview.md](demo/output/01_overview.md) |
| Find the 10 smallest open-access scRNA-seq breast files | [02_scrna-breast.md](demo/output/02_scrna-breast.md) |
| What clinical demographics are available for HTAN OHSU? | [03_demographics-ohsu.md](demo/output/03_demographics-ohsu.md) |
| Participants per cancer type with both scRNA-seq and imaging (BigQuery) | [04_bigquery-multimodal.md](demo/output/04_bigquery-multimodal.md) |
| HTAN publications about spatial transcriptomics from 2024 | [05_pubs-spatial.md](demo/output/05_pubs-spatial.md) |
| Required attributes for scRNA-seq Level 1 manifest | [06_model-scrna.md](demo/output/06_model-scrna.md) |
| Download the smallest open-access scRNA-seq breast file | [07_download-open.md](demo/output/07_download-open.md) |
| Download a controlled-access file via Gen3 (dry run) | [08_download-controlled.md](demo/output/08_download-controlled.md) |

Re-run with: `bash demo/run_demo.sh demo/output`

## Develop (Contributors)

```bash
git clone https://github.com/ncihtan/htan-claude.git
cd htan-claude
uv venv && uv pip install -e ".[dev]"
uv run pytest tests/               # 168 tests

# Use as a local plugin
claude --plugin-dir .
```

## Authentication

| Service | How to Set Up |
|---|---|
| **Portal** | Join [HTAN Claude Skill Users](https://www.synapse.org/Team:3574960) team, then run `uv run htan init` |
| **Synapse** | Get a Personal Access Token from synapse.org, set `SYNAPSE_AUTH_TOKEN` or configure `~/.synapseConfig` |
| **Gen3/CRDC** | Request dbGaP access for study `phs002371`, download credentials from the CRDC portal |
| **BigQuery** | Run `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT` |

See `skills/htan/references/authentication_guide.md` for detailed instructions.

## CLI Reference

The `htan` command is the single interface — used by Claude (via `uv run`) and by you directly.

```bash
uv run htan query portal files --organ Breast --assay "scRNA-seq" --limit 20
uv run htan query portal sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"
uv run htan pubs search --keyword "spatial transcriptomics"
uv run htan model components
uv run htan files lookup HTA9_1_19512
uv run htan query bq tables
uv run htan config check
```

All commands accept `--help` for full usage.

## Architecture

```
htan-claude/
├── src/htan/                    # pip-installable package (all deps included)
│   ├── cli.py                   # Unified CLI: `htan <command>`
│   ├── config.py                # Credential management
│   ├── query/portal.py          # Portal ClickHouse queries
│   ├── query/bq.py              # BigQuery queries
│   ├── download/synapse.py      # Synapse downloads
│   ├── download/gen3.py         # Gen3/CRDC downloads
│   ├── pubs.py                  # PubMed search
│   ├── model.py                 # HTAN data model queries
│   └── files.py                 # File ID mapping
├── skills/htan/
│   ├── SKILL.md                 # Skill definition (teaches Claude the CLI)
│   └── references/              # Reference docs (schema, auth, atlases)
├── .claude-plugin/plugin.json   # Plugin metadata
├── pyproject.toml               # Package definition
└── CLAUDE.md                    # Developer instructions
```

No MCP server. The skill teaches Claude the CLI commands. Claude runs them via `uv run` with blanket `Bash(uv run htan *)` permission.

## License

MIT
