# HTAN Plugin for Claude Code

## Project Overview

This is a Claude Code plugin for working with the **Human Tumor Atlas Network (HTAN)** — an NCI Cancer Moonshot initiative constructing 3D atlases of human cancers from precancerous lesions to advanced disease. The plugin teaches Claude how to use the `htan` CLI to query portal/BigQuery, download from Synapse and Gen3/CRDC, search publications, and explore the HTAN data model.

> **The `htan` CLI itself lives in a separate repo: [ncihtan/htan-cli](https://github.com/ncihtan/htan-cli).** It is published to PyPI as [`htan`](https://pypi.org/project/htan/). Bug reports about CLI behavior, new commands, and library changes belong over there. This repo only owns the skill definition, slash commands, reference docs, and demo.

## What Lives Here

```
htan-claude/
├── skills/htan/
│   ├── SKILL.md                     # Skill definition (teaches Claude the htan CLI)
│   ├── commands/setup.md            # /htan:setup slash command
│   └── references/                  # HTAN-specific reference docs
│       ├── clickhouse_portal.md     # Portal SQL schema and tips
│       ├── bigquery_tables.md       # BigQuery table schemas and examples
│       ├── authentication_guide.md  # Credential setup walkthrough
│       ├── htan_data_model.md       # Components, controlled vocabularies
│       ├── htan_atlases.md          # Atlas centers, cancer types, grants
│       └── htan_docs_manual.md      # HTAN Manual sitemap, dbGaP access, citations
├── .claude-plugin/plugin.json       # Plugin metadata
├── demo/                            # Headless example outputs (claude -p traces)
├── README.md                        # Marketplace-facing user guide
├── CLAUDE.md                        # This file (plugin development guide)
└── LICENSE.txt
```

## Skill Authoring Conventions

The `skills/htan/SKILL.md` should:
- Use `name: htan` (invoked via `/htan`)
- Mention all four data platforms (portal ClickHouse, Synapse, Gen3/CRDC, BigQuery) plus pubs and data model
- Teach Claude the `htan` CLI commands with examples
- Tell Claude to install the CLI from PyPI on first use (`uv pip install htan`)
- Reference the `htan` CLI for each operation
- Keep under 500 lines — move detailed docs to `references/`

## Plugin Development Workflow

```bash
# Use this repo as a local plugin to test changes
claude --plugin-dir /path/to/htan-claude

# Distribute via the Claude Code marketplace
/plugin marketplace add ncihtan/htan-claude
/plugin install htan@htan-claude
```

When changing the CLI (commands, output, behavior), do that in [ncihtan/htan-cli](https://github.com/ncihtan/htan-cli), publish a new version to PyPI, and **then** update SKILL.md / commands here to reflect any new behavior.

## Demo

`demo/` contains 9 headless invocations of the skill via `claude -p`, with both the raw JSONL session traces and the extracted markdown outputs. Re-run with:

```bash
bash demo/run_demo.sh demo/output
```

These outputs document expected behavior end-to-end and are the closest thing this repo has to integration tests. When changing SKILL.md materially, regenerate.

## Authentication & Credential Security

Credentials are managed by the `htan` CLI in standard config locations:

- **Portal ClickHouse**: `~/.config/htan-skill/portal.json` or OS Keychain (populated by `htan init`, fetched from Synapse project syn73720854 gated by Team:3574960 membership)
- **Synapse**: `SYNAPSE_AUTH_TOKEN` env var or `~/.synapseConfig`
- **Gen3**: `~/.gen3/credentials.json` (requires dbGaP authorization for `phs002371`)
- **BigQuery**: Application Default Credentials (`gcloud auth application-default login`)

When using Claude Code, avoid running commands that print credentials or signed URLs into the conversation:
- **Safe via Claude**: `--help`, `--dry-run`, all portal queries, BigQuery `tables`/`describe`/`sql`, file mapping, all `model`/`pubs` commands.
- **Run in your own terminal**: `htan download gen3 resolve` (outputs signed URLs), or anything where errors might echo tokens.

## HTAN Atlas Centers (reference)

| Atlas | Cancer | Phase |
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

## Where to find more

- **CLI source, library docs, release notes**: [ncihtan/htan-cli](https://github.com/ncihtan/htan-cli)
- **HTAN portal**: https://humantumoratlas.org
- **HTAN Manual**: see `skills/htan/references/htan_docs_manual.md`
