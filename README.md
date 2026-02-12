# HTAN Skill for Claude Code

A Claude Code plugin for working with the **Human Tumor Atlas Network (HTAN)** — an NCI Cancer Moonshot initiative constructing 3D atlases of the dynamic cellular, morphological, and molecular features of human cancers as they evolve from precancerous lesions to advanced disease.

## What It Does

| Capability | Auth Required | Description |
|---|---|---|
| **Portal queries** (ClickHouse) | None | Query file metadata, clinical data, download coordinates |
| **PubMed search** | None | Search HTAN-affiliated publications by keyword, author, year |
| **File mapping** | None | Resolve HTAN file IDs to Synapse/Gen3 download coordinates |
| **Synapse download** | Synapse token | Download open-access data (processed matrices, clinical) |
| **Gen3/CRDC download** | Gen3 credentials + dbGaP | Download controlled-access data (raw sequencing) |
| **BigQuery metadata** | Google Cloud ADC | Query HTAN metadata tables in ISB-CGC |

## Installation

### As a Claude Code plugin

```bash
# Add this repository as a marketplace
/plugin marketplace add owner/htan-skill

# Install the HTAN plugin
/plugin install htan@htan-skill
```

### Manual installation

```bash
git clone https://github.com/owner/htan-skill.git ~/.claude/skills/htan-skill
```

Then reference the skill directory in your Claude Code configuration.

## Quick Start (Zero Dependencies)

The portal and PubMed tools use only Python stdlib — no packages to install.

```bash
# Invoke the skill
/htan:htan

# Ask Claude to query the portal
"List all scRNA-seq files from breast cancer in HTAN"

# Search publications
"Search HTAN publications about spatial transcriptomics"

# Look up a file ID
"Look up HTAN file HTA9_1_19512"
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

Three services require credentials for full functionality:

| Service | How to Set Up |
|---|---|
| **Synapse** | Get a Personal Access Token from synapse.org, set `SYNAPSE_AUTH_TOKEN` or configure `~/.synapseConfig` |
| **Gen3/CRDC** | Request dbGaP access for study `phs002371`, download credentials from the CRDC portal |
| **BigQuery** | Run `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT` |

See `skills/htan/references/authentication_guide.md` for detailed instructions.

## Plugin Structure

```
htan-skill/
├── .claude-plugin/
│   ├── plugin.json             # Plugin manifest (for --plugin-dir loading)
│   └── marketplace.json        # Marketplace catalog (for distribution)
├── skills/
│   └── htan/                   # Auto-discovered skill → /htan:htan
│       ├── SKILL.md            # Skill definition (loaded by Claude Code)
│       ├── scripts/            # 7 core Python scripts
│       │   ├── htan_portal.py      # Portal ClickHouse queries (no auth)
│       │   ├── htan_pubmed.py      # PubMed search (no auth)
│       │   ├── htan_file_mapping.py # File ID resolution (no auth)
│       │   ├── htan_synapse.py     # Synapse downloads
│       │   ├── htan_gen3.py        # Gen3/CRDC downloads
│       │   ├── htan_bigquery.py    # BigQuery metadata queries
│       │   └── htan_setup.py       # Environment setup checker
│       └── references/         # 6 reference documents
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
