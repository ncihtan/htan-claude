# Upload to Synapse

Upload one or more local files to a Synapse project or folder using `htan upload synapse`.

## Your job

### Step 1 — Check auth first, before anything else

Try to actually authenticate with Synapse:
```bash
uv run python -c "import synapseclient; syn = synapseclient.Synapse(); syn.login(silent=True); print('ok')" 2>&1
```

If the output is `ok` → auth is good, proceed.

If it errors (any output other than `ok`), do the following **and stop**:

1. Check if `.env` already exists:
   ```bash
   test -f .env && echo "exists" || echo "missing"
   ```

2. If `.env` is missing, create it from the template:
   ```bash
   cp .env.example .env
   ```
   Then tell the user:
   > Your Synapse token isn't set. I've created a `.env` file from the template.
   >
   > **To finish setup:**
   > 1. Get your token: go to [synapse.org](https://www.synapse.org) → your profile → Settings → Access Tokens → Create new token
   > 2. Open `.env` in a text editor and replace `your_personal_access_token_here` with your token
   > 3. In your terminal, run: `source .env` then restart Claude Code so it picks up the new variable
   > 4. Then ask me to upload again

3. If `.env` already exists, tell the user:
   > Synapse authentication failed. Either your token isn't in `.env` yet, or Claude Code was started before you ran `source .env`. Please restart Claude Code after running `source .env`, then ask me to upload again.

### Step 2 — Identify the file(s)

Use `$ARGUMENTS` if the user passed a path. Otherwise check what file they have open in the IDE, or ask them.

### Step 3 — Get the parent Synapse ID

If not already provided, ask:
> Which Synapse project or folder should I upload to? (e.g. syn12345678)

### Step 4 — Look up the parent syn ID in the HTAN2 config

Fetch the config and search for the parent syn ID:
```bash
curl -s https://raw.githubusercontent.com/ncihtan/htan2_project_setup/main/schema_binding_config.yml | grep -B5 "<parent_syn_id>"
```

**Decision rules (in order):**

1. **Not a CSV/TSV** (`.h5ad`, `.fastq`, `.bam`, `.tiff`, `.gz`, etc.) → **plain file upload**

2. **Parent syn ID found under `record_based`** → **RecordSet** — proceed below

3. **Parent syn ID not found in the config at all** → stop:
   > I can't find `<parent_syn_id>` in the HTAN2 project configuration. Please reach out to the DCC at [htan@sagebase.org](mailto:htan@sagebase.org) to get the correct upload destination for your data.

4. **Parent syn ID found under `file_based`** → stop:
   > `<parent_syn_id>` is configured for assay file uploads, which aren't handled here. Please reach out to the DCC at [htan@sagebase.org](mailto:htan@sagebase.org) for guidance on submitting assay data.

#### If RecordSet:

Ask the user:
> What is the Synapse ID of the existing **RecordSet** to upload into? (e.g. syn12345678)

Do not create a new RecordSet. The RecordSet already exists — the user provides its syn ID.

Read the CSV headers to auto-detect upsert keys:
```bash
head -1 "<path>"
```

Find all columns matching `HTAN_*_ID` (case-insensitive). Use every match as an upsert key. If none found, use the first column. Do not ask the user about this.

Then upsert the rows into the existing RecordSet:
```python
uv run python - << 'EOF'
import synapseclient
from synapseclient.models import RecordSet
import pandas as pd

syn = synapseclient.login(silent=True)
df = pd.read_csv("<path>")
record_set = RecordSet(id="<recordset_syn_id>")
record_set = record_set.get(synapse_client=syn)
record_set.upsert_rows(rows=df.to_dict(orient="records"), upsert_keys=<detected_keys>, synapse_client=syn)
print(f"Upserted {len(df)} rows into {record_set.id}")
EOF
```

Tell the user how many rows were upserted and the RecordSet ID.

#### If plain file upload:

```bash
uv run htan upload synapse file "<path>" --parent <syn_id> --dry-run
```
For bulk: `uv run htan upload synapse bulk <dir_or_manifest> --parent <syn_id> --dry-run`

Show the output and ask: "Looks good — shall I go ahead and upload?"

### Step 5 — Upload (plain files only)

If confirmed, run without `--dry-run` and show the returned Synapse entity ID(s).

### Step 6 — Annotations (optional)

If the user mentioned metadata (e.g. "tag it as assay=scRNA-seq"), add `--annotation key=value` flags to the plain file upload.

## Security rules

- NEVER suggest passing `SYNAPSE_AUTH_TOKEN` as a command-line argument or flag.
- NEVER ask the user to paste their token into the chat — it would flow through the Anthropic API.
- NEVER read or display the contents of `.env`.
- Always direct the user to fill in their token themselves in a text editor.

## Examples

Single file:
```bash
uv run htan upload synapse file ./data.csv --parent syn12345678 --dry-run
uv run htan upload synapse file ./data.csv --parent syn12345678
```

With annotations:
```bash
uv run htan upload synapse file ./matrix.h5ad --parent syn12345678 \
  --annotation assay=scRNA-seq --annotation atlas=HTAN_OHSU
```

Bulk from directory:
```bash
uv run htan upload synapse bulk ./processed/ --parent syn12345678 --dry-run
uv run htan upload synapse bulk ./processed/ --parent syn12345678
```
