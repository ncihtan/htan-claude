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

## Getting Started

### 1. Set up the environment

```bash
# Clone the repo
git clone https://github.com/ncihtan/htan-claude.git
cd htan-claude

# Create a virtual environment and install the package
uv venv
uv pip install -e .

# Optional: install platform-specific extras as needed
uv pip install -e ".[synapse]"    # Synapse downloads
uv pip install -e ".[gen3]"       # Gen3/CRDC downloads
uv pip install -e ".[bigquery]"   # BigQuery queries
uv pip install -e ".[all]"        # All of the above
```

### 2. Configure credentials

```bash
# Run the interactive setup wizard
htan init

# Or check what's already configured
htan config check
```

| Service | How to Set Up |
|---|---|
| **Portal** | Join [HTAN Claude Skill Users](https://www.synapse.org/Team:3574960) team, then run `htan init` |
| **Synapse** | Get a Personal Access Token from synapse.org, set `SYNAPSE_AUTH_TOKEN` or configure `~/.synapseConfig` |
| **Gen3/CRDC** | Request dbGaP access for study `phs002371`, download credentials from the CRDC portal |
| **BigQuery** | Run `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT` |

See `skills/htan/references/authentication_guide.md` for detailed instructions.

### 3. Install the Claude Code plugin

```bash
# Option A: From the marketplace (when published)
# In Claude Code, run:
/plugin marketplace add ncihtan/htan-claude
/plugin install htan@htan-claude

# Option B: Local plugin directory
claude --plugin-dir /path/to/htan-claude
```

### 4. Allow `htan` commands

On first use, add this to your project's `.claude/settings.json` to allow all `htan` CLI commands without per-command prompts:

```json
{
  "permissions": {
    "allow": [
      "Bash(htan *)"
    ]
  }
}
```

### 5. Go

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

## CLI Reference

The `htan` command is the single interface — used by Claude and by you directly.

```bash
htan query portal files --organ Breast --assay "scRNA-seq" --limit 20
htan query portal sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"
htan query portal summary
htan pubs search --keyword "spatial transcriptomics"
htan model components
htan model attributes "scRNA-seq Level 1"
htan files lookup HTA9_1_19512
htan query bq tables
htan config check
```

All commands accept `--help` for full usage.

## Architecture

```
htan-claude/
├── src/htan/                    # pip-installable package (stdlib core)
│   ├── cli.py                   # Unified CLI: `htan <command>`
│   ├── config.py                # Credential management
│   ├── query/portal.py          # Portal ClickHouse queries
│   ├── query/bq.py              # BigQuery queries (needs htan[bigquery])
│   ├── download/synapse.py      # Synapse downloads (needs htan[synapse])
│   ├── download/gen3.py         # Gen3/CRDC downloads (needs htan[gen3])
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

No MCP server. The skill teaches Claude the CLI commands. Claude runs them via Bash with blanket `Bash(htan *)` permission.

## License

MIT
