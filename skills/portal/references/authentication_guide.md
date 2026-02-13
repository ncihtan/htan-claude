# HTAN Authentication Guide

## Recommended: Interactive Setup Wizard

The easiest way to set up all authentication is the interactive wizard:

```bash
python3 scripts/htan_setup.py init
```

This walks through environment setup, Synapse, portal credentials, BigQuery, and Gen3/CRDC in order, detecting what's already configured and providing instructions for anything missing.

The manual instructions below are kept as reference for individual service setup.

---

This guide covers authentication setup for all three HTAN data platforms.

---

## 1. Synapse (Open-Access Data)

### Overview

Synapse hosts HTAN open-access data (de-identified clinical data, processed matrices, imaging metadata). You need a free Synapse account and a Personal Access Token.

### Setup Steps

1. **Create a Synapse account** at [synapse.org](https://www.synapse.org/)
2. **Generate a Personal Access Token**:
   - Log in to Synapse
   - Go to **Account Settings** → **Personal Access Tokens**
   - Click **Create New Token**
   - Select scopes: `view`, `download`
   - Copy the generated token
3. **Configure authentication** (choose one method):

#### Method A: Environment Variable (Recommended)

```bash
export SYNAPSE_AUTH_TOKEN="your-token-here"
```

Add to your shell profile (`~/.bashrc`, `~/.zshrc`) for persistence.

#### Method B: Config File

Create `~/.synapseConfig`:

```ini
[authentication]
authtoken = your-token-here
```

Set permissions:

```bash
chmod 600 ~/.synapseConfig
```

### Verification

```bash
python3 -c "
import synapseclient
syn = synapseclient.Synapse()
syn.login()
print('Synapse auth OK:', syn.getUserProfile().userName)
"
```

---

## 2. Gen3 / CRDC (Controlled-Access Data)

### Overview

The Cancer Research Data Commons (CRDC) via Gen3 hosts controlled-access HTAN data (raw sequencing data, protected genomic data). Access requires dbGaP authorization.

### Prerequisites

1. **eRA Commons account** — required for dbGaP
2. **dbGaP authorization** for HTAN study `phs002371`
   - Apply at [dbGaP](https://dbgap.ncbi.nlm.nih.gov/)
   - Approval may take several weeks
3. **Link your eRA Commons account** to your Gen3/CRDC profile

### Setup Steps

1. **Log in** to the [CRDC Portal](https://nci-crdc.datacommons.io/)
2. **Download credentials**:
   - Click your username → **Profile**
   - Click **Create API Key** (or **Download Credentials**)
   - Save the JSON file as `~/.gen3/credentials.json`
3. **Configure authentication** (choose one method):

#### Method A: Default Location

Place the credentials file at:

```
~/.gen3/credentials.json
```

#### Method B: Environment Variable

```bash
export GEN3_API_KEY="/path/to/credentials.json"
```

#### Method C: Explicit Flag

Pass `--credentials /path/to/credentials.json` to the script.

### Credentials File Format

The downloaded file should look like:

```json
{
  "api_key": "your-api-key-here",
  "key_id": "your-key-id-here"
}
```

### Verification

```bash
python3 -c "
from gen3.auth import Gen3Auth
auth = Gen3Auth(endpoint='https://nci-crdc.datacommons.io',
                refresh_file='~/.gen3/credentials.json')
print('Gen3 auth OK')
"
```

---

## 3. BigQuery / ISB-CGC (Metadata Queries)

### Overview

HTAN metadata is available in Google BigQuery via the ISB-CGC project. You need a Google Cloud account with billing enabled (queries against public datasets incur small costs).

### Prerequisites

1. **Google Cloud account** with a project that has billing enabled
2. **BigQuery API enabled** on your project
3. Install the **Google Cloud SDK** (`gcloud` CLI)

### Setup Steps

#### Method A: Application Default Credentials (Recommended)

```bash
gcloud auth application-default login
```

This opens a browser for OAuth login and saves credentials locally.

Set your default project:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

#### Method B: Service Account Key

1. Create a service account in your GCP project
2. Grant it the `BigQuery Job User` and `BigQuery Data Viewer` roles
3. Download the JSON key file
4. Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Verification

```bash
python3 -c "
from google.cloud import bigquery
client = bigquery.Client()
query = 'SELECT 1 as test'
result = list(client.query(query).result())
print('BigQuery auth OK, project:', client.project)
"
```

### Cost Notes

- HTAN tables in `isb-cgc-bq` are public — no data access charges
- You pay only for query processing (first 1 TB/month free)
- Use `--dry-run` to estimate query cost before executing

---

## Troubleshooting

### Synapse

| Issue | Solution |
|-------|----------|
| `SynapseAuthenticationError` | Token expired — generate a new one |
| `SynapseHTTPError: 403` | You lack download permissions — check Terms of Use acceptance |
| Token not found | Verify `SYNAPSE_AUTH_TOKEN` is set or `~/.synapseConfig` exists |

### Gen3

| Issue | Solution |
|-------|----------|
| `401 Unauthorized` | Credentials expired — download fresh credentials from CRDC portal |
| `403 Forbidden` | dbGaP authorization not approved or not linked to CRDC account |
| Credentials file not found | Check path: `~/.gen3/credentials.json` or `--credentials` flag |

### BigQuery

| Issue | Solution |
|-------|----------|
| `DefaultCredentialsError` | Run `gcloud auth application-default login` |
| `403: Access Denied: Project` | Enable BigQuery API and ensure billing is enabled |
| `NotFound: Table` | Check table name — use `htan_bigquery.py tables` to list available tables |

---

## Environment Variable Summary

| Variable | Service | Required | Description |
|----------|---------|----------|-------------|
| `SYNAPSE_AUTH_TOKEN` | Synapse | Yes* | Personal Access Token |
| `GEN3_API_KEY` | Gen3/CRDC | No | Path to credentials.json (default: `~/.gen3/credentials.json`) |
| `GOOGLE_CLOUD_PROJECT` | BigQuery | Yes | GCP project ID for billing |
| `GOOGLE_APPLICATION_CREDENTIALS` | BigQuery | No | Path to service account key (alternative to ADC) |

*Required unless `~/.synapseConfig` is configured.
