---
description: Set up HTAN skill credentials and dependencies
allowed-tools:
  - Bash
  - Read
---

# HTAN Setup

Check credential status and configure access for the HTAN skill. The `htan` CLI is the [`htan` PyPI package](https://pypi.org/project/htan/), sourced from [ncihtan/htan-cli](https://github.com/ncihtan/htan-cli).

## Arguments

- `$ARGUMENTS` = empty or "setup" → full interactive flow (`htan init`)
- `$ARGUMENTS` = "check" or "status" → status only (`htan init --status`)

## Steps

### Step 1: Verify the CLI is installed

Run `uv run htan --version`. If `htan` is not found, walk the user through installing it before doing anything else:

```bash
uv venv && uv pip install htan
```

Without uv:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install htan
```

The package pulls in all required dependencies (`synapseclient`, `gen3`, `google-cloud-bigquery`, `pandas`).

### Step 2: Check status

```bash
uv run htan init --status
```

Parse the output and present a dashboard to the user:

```
HTAN — Setup Status

  Synapse credentials    ~/.synapseConfig found
  Portal credentials     Stored in OS Keychain (encrypted)
  Gen3/CRDC              Optional — needed for controlled-access downloads
  BigQuery               Optional — needed for advanced metadata queries
```

If `$ARGUMENTS` is "check" or "status", **stop here** — do not proceed past this step.

### Step 3: Run the interactive setup wizard

```bash
uv run htan init
```

This walks the user through each service:
- **Synapse**: prompts for a Personal Access Token (or detects an existing `~/.synapseConfig` / `SYNAPSE_AUTH_TOKEN`).
- **Portal**: with Synapse credentials present, auto-fetches portal credentials from the gated Synapse project (`syn73720854`) — requires membership in the [HTAN Claude Skill Users](https://www.synapse.org/Team:3574960) team.
- **BigQuery**: detects Application Default Credentials and `GOOGLE_CLOUD_PROJECT`.
- **Gen3/CRDC**: detects `~/.gen3/credentials.json` (controlled-access; requires dbGaP authorization for study `phs002371`).

To target a single service, use `uv run htan init <service>` (e.g., `uv run htan init portal`).

If portal setup fails with an access error, tell the user to join the team at https://www.synapse.org/Team:3574960.

### Step 4: Re-check and show final status

```bash
uv run htan init --status
```

Present the updated dashboard. For optional items not yet configured:

- **Gen3/CRDC**: requires dbGaP authorization for study `phs002371` — apply at https://dbgap.ncbi.nlm.nih.gov/
- **BigQuery**: run `gcloud auth application-default login` in your own terminal (not via Claude)

## Environment differences

- **Local Claude Code**: portal credentials are stored in the OS Keychain (encrypted at rest) when available, with a config file fallback.
- **Cowork / containerized environments**: tell the user to set `SYNAPSE_AUTH_TOKEN` and `HTAN_PORTAL_CREDENTIALS` (a JSON string) as project environment variables.
