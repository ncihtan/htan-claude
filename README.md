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

## Installation

### As a Claude Code plugin

```bash
# Add this repository as a marketplace
/plugin marketplace add ncihtan/htan-claude

# Install the HTAN plugin
/plugin install htan@htan-claude
```

### Manual installation

```bash
git clone https://github.com/ncihtan/htan-claude.git ~/.claude/skills/htan-claude
```

Then reference the skill directory in your Claude Code configuration.

## Setup

After installing, run the setup command:

```
/htan:setup
```

This checks credential status and auto-configures portal access. Portal setup uses stdlib HTTP only — no venv or `synapseclient` needed.

To check status only: `/htan:setup check`

**Credential storage** (3-tier resolution):
- **Environment variable**: `HTAN_PORTAL_CREDENTIALS` (JSON string) — best for Cowork
- **OS Keychain**: macOS Keychain / Linux `secret-tool` — best for local (encrypted at rest)
- **Config file**: `~/.config/htan-skill/portal.json` — backward compatible

Portal queries, PubMed search, and data model queries use only Python stdlib — no packages to install beyond Python 3.11+.

## Quick Start

```bash
# Invoke the skill
/htan

# Ask Claude to query the portal
"List all scRNA-seq files from breast cancer in HTAN"

# Search publications
"Search HTAN publications about spatial transcriptomics"

# Look up a file ID
"Look up HTAN file HTA9_1_19512"

# Query the data model
"What attributes are required for scRNA-seq Level 1 manifests?"
```

## Optional Dependencies

For downloading data and querying BigQuery, install the Python packages:

```bash
# Create a virtual environment (recommended)
uv venv .venv && source .venv/bin/activate

# Install all optional dependencies
uv pip install synapseclient gen3 google-cloud-bigquery google-cloud-bigquery-storage pandas db-dtypes
```

| Package | Purpose |
|---|---|
| `synapseclient` | Download open-access data from Synapse |
| `gen3` | Download controlled-access data from CRDC |
| `google-cloud-bigquery` | Query HTAN metadata in ISB-CGC BigQuery |
| `google-cloud-bigquery-storage` | Fast BigQuery result retrieval |
| `pandas` | Data manipulation for query results |
| `db-dtypes` | BigQuery data type support |

## Authentication Setup

| Service | How to Set Up |
|---|---|
| **Portal** | Join [HTAN Claude Skill Users](https://www.synapse.org/Team:3574960) team, then run `/htan:setup` |
| **Synapse** | Get a Personal Access Token from synapse.org, set `SYNAPSE_AUTH_TOKEN` or configure `~/.synapseConfig` |
| **Gen3/CRDC** | Request dbGaP access for study `phs002371`, download credentials from the CRDC portal |
| **BigQuery** | Run `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT` |

See `skills/htan/references/authentication_guide.md` for detailed instructions.

## Plugin Structure

```
htan-claude/
├── .claude-plugin/
│   ├── plugin.json             # Plugin manifest
│   └── marketplace.json        # Marketplace catalog
├── skills/
│   └── htan/                   # Auto-discovered skill → /htan
│       ├── SKILL.md            # Skill definition (loaded by Claude Code)
│       ├── commands/
│       │   └── setup.md            # /htan:setup command
│       ├── scripts/
│       │   ├── htan_portal_config.py  # Portal credential loader (stdlib)
│       │   ├── htan_portal.py         # Portal ClickHouse queries (stdlib)
│       │   ├── htan_pubmed.py         # PubMed search (stdlib)
│       │   ├── htan_data_model.py     # Data model queries (stdlib)
│       │   ├── htan_file_mapping.py   # File ID resolution
│       │   ├── htan_synapse.py        # Synapse downloads
│       │   ├── htan_gen3.py           # Gen3/CRDC downloads
│       │   ├── htan_bigquery.py       # BigQuery metadata queries
│       │   ├── htan_quicksetup.py      # Claude-safe setup (JSON output, stdlib)
│       │   └── htan_setup.py          # Setup wizard and auth checker
│       └── references/
│           ├── clickhouse_portal.md
│           ├── authentication_guide.md
│           ├── bigquery_tables.md
│           ├── htan_atlases.md
│           ├── htan_data_model.md
│           └── htan_docs_manual.md
├── README.md
├── LICENSE.txt                 # MIT
└── CLAUDE.md                   # Developer instructions
```

## License

MIT
