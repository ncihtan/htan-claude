# Show me how I would download a controlled-access file via Gen3 dry run only

---

To download a controlled-access file via Gen3, you'd use the `gen3-client` CLI. Here's how a dry run would look:

### 1. Find a controlled-access file (has a DRS URI)

```bash
uv run htan query portal files --assay "scRNA-seq" --limit 5
```

Look for files with a `drs_uri` column value (e.g., `drs://dg.4DFC:...`). These are controlled-access Level 1-2 sequencing files.

### 2. Resolve the DRS URI to get the GUID

```bash
uv run htan files lookup <HTAN_Data_File_ID> --format json
```

This returns the `drs_uri` and other coordinates without downloading anything.

### 3. Download command (what you would run)

```bash
gen3-client download-single \
  --profile=htan \
  --guid=dg.4DFC/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
  --download-path=./data
```

### Prerequisites for controlled access

1. **dbGaP authorization** — You need approved access to HTAN's controlled data (phs002371)
2. **Gen3 credentials** — Download from the [CRDC portal](https://data.humantumornetlas.org/) and save to `~/.gen3/credentials.json`
3. **gen3-client installed** — The Gen3 CLI binary must be on your PATH

### Check your current setup

```bash
uv run htan config check
```

This will show whether Gen3 credentials are configured without actually downloading anything.

There's no built-in `--dry-run` flag on `gen3-client`, so the safest "dry run" approach is:
1. Use `htan files lookup` to resolve the file coordinates
2. Verify your credentials with `htan config check`
3. Only run `gen3-client download-single` when you're ready to actually download

Want me to run any of these lookup steps for you?
