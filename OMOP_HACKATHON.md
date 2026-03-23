# HTAN → OMOP ETL + Natural Language Query

A Python ETL pipeline that pulls lung cancer clinical data from the [Human Tumor Atlas Network (HTAN)](https://humantumoratlas.org) into the [OMOP CDM 5.4](https://ohdsi.github.io/CommonDataModel/) standard, stored locally in [DuckDB](https://duckdb.org), with a natural language query interface powered by Claude.

Built at the HTAN hackathon.

---

## What it does

1. **ETL** — Queries HTAN BU (Boston University lung pre-cancer atlas) clinical data from [ISB-CGC BigQuery](https://isb-cgc.appspot.com/), maps it to OMOP CDM, and writes two tables to a local DuckDB file:
   - `person` — 484 participants with gender, race, ethnicity
   - `condition_occurrence` — 183 diagnosis records with morphology, AJCC stage, age at diagnosis

2. **Natural language queries** — Ask plain-English questions about the data; Claude translates them to OMOP SQL and runs them against DuckDB.

---

## Quickstart

### Prerequisites

- Python 3.10+, [uv](https://docs.astral.sh/uv/)
- Google Cloud credentials with BigQuery access (`gcloud auth application-default login`)
- An [Anthropic API key](https://console.anthropic.com) (for NL queries)

### Install

```bash
git clone https://github.com/ncihtan/htan-claude
cd htan-claude
uv pip install -e ".[dev]"
```

### Run the ETL

```bash
uv run htan etl omop build --db htan_omop_lung.duckdb
```

```
Querying demographics (HTAN BU)...
  484 participants
Querying lung diagnoses (HTAN BU)...
  183 diagnosis records

Writing to htan_omop_lung.duckdb...
  person:               484 rows
  condition_occurrence: 183 rows
```

### Query in natural language

```bash
export ANTHROPIC_API_KEY="your-key-here"
uv run htan etl omop query "How many patients had adenocarcinoma?" --db htan_omop_lung.duckdb
```

```
Question: How many patients had adenocarcinoma?

Generating SQL...

SQL:
  SELECT COUNT(DISTINCT person_id) AS n
  FROM condition_occurrence
  WHERE condition_concept_id = 4032806

Results:
   n
  72
```

More example questions:
```bash
uv run htan etl omop query "What is the age distribution at diagnosis?"
uv run htan etl omop query "How many patients by race?"
uv run htan etl omop query "How many female patients had squamous cell carcinoma?"
uv run htan etl omop query "What are the most common AJCC stages?"
```

### Query with raw SQL

```bash
duckdb htan_omop_lung.duckdb "SELECT * FROM person LIMIT 5"
duckdb htan_omop_lung.duckdb "SELECT ajcc_pathologic_stage, COUNT(*) AS n FROM condition_occurrence GROUP BY 1 ORDER BY n DESC"
```

---

## OMOP Mapping

| HTAN field | OMOP table | OMOP column |
|---|---|---|
| `HTAN_Participant_ID` | `person` | `person_source_value` |
| `Gender` | `person` | `gender_concept_id` (SNOMED) |
| `Race` | `person` | `race_concept_id` |
| `Ethnicity` | `person` | `ethnicity_concept_id` |
| `Morphology` (ICD-O-3) | `condition_occurrence` | `condition_concept_id` (SNOMED) |
| `AJCC_Pathologic_Stage` | `condition_occurrence` | `ajcc_pathologic_stage` |
| `Age_at_Diagnosis` | `condition_occurrence` | `age_at_diagnosis_days` |

Concept IDs use the [OMOP Athena vocabulary](https://athena.ohdsi.org). Unmapped morphology codes get `condition_concept_id = 0` and can be re-mapped via Athena.

---

## Data source

- **Atlas**: HTAN BU (Boston University) — lung pre-cancer atlas
- **Source tables**: `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`, `isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current`
- **Participants**: 484 (183 with diagnosis data)
- **Access**: Requires ISB-CGC BigQuery access (free, register at [isb-cgc.org](https://isb-cgc.org))

---

## Code

```
src/htan/etl/omop.py    # ETL logic, OMOP concept mappings, NL→SQL via Claude
src/htan/cli.py         # htan etl omop entry point
```
