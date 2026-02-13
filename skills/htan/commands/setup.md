---
description: Set up HTAN skill credentials and dependencies
allowed-tools:
  - Bash
  - Read
---

# HTAN Setup

Check credential status and configure access for the HTAN skill.

## Arguments

- `$ARGUMENTS` = empty or "setup" -> full setup flow (Steps 1-5)
- `$ARGUMENTS` = "check" or "status" -> only Step 1 (status dashboard)

## Steps

### Step 1: Check status

```bash
python3 "$HTAN_DIR/scripts/htan_quicksetup.py" check
```

Parse the JSON output and present a dashboard to the user:

```
HTAN Skill — Setup Status

  Synapse credentials    ~/.synapseConfig found
  Portal credentials     Stored in OS Keychain (encrypted)
  Gen3/CRDC              Optional — needed for controlled-access downloads
  BigQuery               Optional — needed for advanced metadata queries
```

Show the `portal_source` field value: "env" (environment variable), "keychain" (OS Keychain), "file" (config file), or null (not configured).

If `$ARGUMENTS` is "check" or "status", **stop here** — do not proceed to setup steps.

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
> Once done, run `/htan:setup` again to continue.

**Do not proceed past this step** if Synapse is not configured. The remaining steps depend on it.

### Step 3: Auto-configure portal credentials

If `status.portal.configured` is `false`, download credentials from Synapse. This uses stdlib HTTP only — **no venv needed**:

```bash
python3 "$HTAN_DIR/scripts/htan_quicksetup.py" portal
```

This will:
- Log in to Synapse using the auth token from `~/.synapseConfig` or `SYNAPSE_AUTH_TOKEN`
- Auto-join the HTAN Claude Skill Users team if eligible
- Download credentials via Synapse REST API (stdlib only)
- Store in OS Keychain (macOS/Linux) and config file (backward compat)
- Verify connectivity

If it fails with an access error, tell the user to join the team at https://www.synapse.org/Team:3574960.

### Step 4: Re-check and show final status

```bash
python3 "$HTAN_DIR/scripts/htan_quicksetup.py" check
```

Present updated dashboard. For optional items, show instructions:

- **Gen3/CRDC** (controlled-access data): Requires dbGaP authorization for study `phs002371` — apply at https://dbgap.ncbi.nlm.nih.gov/
- **BigQuery** (advanced metadata queries): Run `gcloud auth application-default login` in your terminal

### Step 5: venv (only if needed)

Only create a venv if the user needs Synapse downloads, Gen3 downloads, or BigQuery queries. Portal setup, portal queries, PubMed, data model, and file mapping are all stdlib-only.

```bash
python3 "$HTAN_DIR/scripts/htan_quicksetup.py" venv
```

## Environment differences

- **Local Claude Code**: Portal credentials stored in OS Keychain (encrypted at rest)
- **Cowork**: Tell the user to set `SYNAPSE_AUTH_TOKEN` and `HTAN_PORTAL_CREDENTIALS` (JSON string) in project environment variables
