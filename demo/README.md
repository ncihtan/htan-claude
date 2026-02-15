# HTAN Skill Demo

Headless demo of the HTAN Claude Code skill across 8 prompts covering portal queries, BigQuery joins, PubMed search, data model lookups, and downloads.

## Running

From a project directory with `htan` installed:

```bash
bash demo/run_demo.sh demo/output
```

This runs each prompt via `claude -p` with `stream-json` output, then extracts the final response into readable `.md` files. Raw JSONL traces are saved alongside for debugging.

## Results

**Total: 50 tool calls, ~6 minutes, $1.69 API cost across all 8 prompts.**

| # | Prompt | Output | Trace | Tools | Time | Cost |
|---|---|---|---|---|---|---|
| 01 | [HTAN data overview](#01-htan-data-overview) | [.md](output/01_overview.md) | [.jsonl](output/01_overview.jsonl) | 2 | 22s | $0.08 |
| 02 | [10 smallest scRNA-seq breast files](#02-10-smallest-open-access-scrna-seq-breast-files) | [.md](output/02_scrna-breast.md) | [.jsonl](output/02_scrna-breast.jsonl) | 18 | 120s | $0.72 |
| 03 | [OHSU demographics](#03-ohsu-patient-demographics) | [.md](output/03_demographics-ohsu.md) | [.jsonl](output/03_demographics-ohsu.jsonl) | 1 | 16s | $0.08 |
| 04 | [Multimodal participants (BigQuery)](#04-participants-with-both-scrna-seq-and-imaging-bigquery) | [.md](output/04_bigquery-multimodal.md) | [.jsonl](output/04_bigquery-multimodal.jsonl) | 14 | 73s | $0.25 |
| 05 | [Spatial transcriptomics pubs](#05-spatial-transcriptomics-publications) | [.md](output/05_pubs-spatial.md) | [.jsonl](output/05_pubs-spatial.jsonl) | 3 | 22s | $0.10 |
| 06 | [scRNA-seq Level 1 manifest](#06-scrna-seq-level-1-manifest-attributes) | [.md](output/06_model-scrna.md) | [.jsonl](output/06_model-scrna.jsonl) | 2 | 13s | $0.07 |
| 07 | [Download smallest file](#07-download-smallest-open-access-file) | [.md](output/07_download-open.md) | [.jsonl](output/07_download-open.jsonl) | 10 | 75s | $0.37 |
| 08 | [Gen3 controlled-access dry run](#08-controlled-access-download-gen3) | [.md](output/08_download-controlled.md) | [.jsonl](output/08_download-controlled.jsonl) | 0 | 12s | $0.04 |

## How Claude Solved Each Prompt

### 01: HTAN data overview

**Strategy:** Two parallel portal queries.

1. `htan query portal summary` — file/participant counts by atlas, assay, organ
2. `htan query portal tables` — list the 7 available tables

Straightforward. Claude synthesized the raw counts into a structured overview with categories (imaging, single-cell, spatial, bulk, proteomics) and suggested next steps.

### 02: 10 smallest open-access scRNA-seq breast files

**Strategy:** Portal for file discovery, BigQuery fallback for file sizes. Most complex prompt — 18 tool calls with 6 errors along the way.

1. `htan query portal files --organ Breast --assay "scRNA-seq"` — found files but no size column
2. Tried several portal SQL queries — hit ClickHouse array column syntax errors (`organType` is `Array(String)`, needs `arrayExists()`)
3. `htan query portal describe files` — discovered column types, built working query
4. **Fell back to BigQuery** for `File_Size` — portal doesn't have file sizes
5. Joined scRNAseq metadata with diagnosis table to filter breast cancer
6. Successfully returned 10 files sorted by size with Synapse IDs

**Key insight:** The "Platform Data Gaps" section in SKILL.md was added specifically because earlier versions of this demo got stuck here. Claude now knows to check BigQuery for file sizes.

### 03: OHSU patient demographics

**Strategy:** Single direct portal query.

1. `htan query portal demographics --atlas "HTAN OHSU" --limit 50`

Simplest prompt — one tool call. Claude summarized the 33-patient cohort (all female, breast cancer focus, vital status breakdown) from the raw tabular output.

### 04: Participants with both scRNA-seq and imaging (BigQuery)

**Strategy:** Schema exploration, then a complex CTE query. 14 tool calls.

1. `htan query bq tables` + read reference docs — understand available tables
2. Described 3 tables in parallel (scRNAseq, imaging, diagnosis)
3. Discovered scRNAseq tables lack `HTAN_Participant_ID` — only have biospecimen IDs
4. **Key insight:** Used `REGEXP_EXTRACT` to derive participant IDs from the HTAN ID naming pattern (`HTA1_1001_001` → `HTA1_1001`)
5. Built a CTE with `INTERSECT` to find 190 participants with both modalities, joined to diagnosis for cancer types

### 05: Spatial transcriptomics publications

**Strategy:** Trial and error on CLI flags.

1. `htan pubs search --keyword "spatial transcriptomics" --min-date 2024/01/01` — **failed** (wrong flags)
2. `htan pubs search --help` — discovered correct `--year` flag
3. `htan pubs search --keyword "spatial transcriptomics" --year 2024` — found 7 papers

Demonstrates the recover-from-wrong-flags pattern: guess, fail, check `--help`, retry.

### 06: scRNA-seq Level 1 manifest attributes

**Strategy:** Two parallel data model queries.

1. `htan model required "scRNA-seq Level 1"` — 23 required attributes
2. `htan model valid-values "Library Construction Method"` — 18 valid values

Clean parallel execution. No errors.

### 07: Download smallest open-access file

**Strategy:** Same portal → BigQuery fallback as prompt 02, plus actual Synapse download. 10 tool calls.

1. Portal file search returned Level 1 (controlled) files — pivoted to SQL for Level 3-4
2. BigQuery for file sizes — found `HTA6_2502_80` (2.8 KB barcode file)
3. `htan files lookup` to verify download coordinates
4. `synapse get syn64372046 --downloadLocation ./data` — actual download

### 08: Controlled-access download (Gen3)

**Strategy:** Pure documentation response — zero tool calls.

Claude recognized "show me how" as an informational request and provided a 3-step workflow (find file → resolve DRS URI → download via gen3-client) with prerequisites and security notes. Correctly avoided running `htan download gen3 resolve` which would output signed URLs into the conversation.

## Patterns Observed

- **Portal-first, BigQuery-fallback**: Claude consistently starts with the portal for file discovery, then falls back to BigQuery when file sizes, cell counts, or assay metadata are needed.
- **ClickHouse array columns are tricky**: The `organType`, `Gender`, `Race` etc. columns are `Array(String)` and need `arrayExists()` — Claude often gets this wrong on the first try.
- **Participant ID derivation**: BigQuery assay tables lack a direct `HTAN_Participant_ID` column. Claude derives it from biospecimen IDs using regex on the HTAN naming convention.
- **Security awareness**: Gen3 commands that expose signed URLs are correctly avoided in the conversation.
