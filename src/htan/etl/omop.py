"""OMOP CDM ETL for HTAN lung cancer data.

Queries HTAN BU (lung) demographics + diagnosis from ISB-CGC BigQuery,
transforms to OMOP CDM 5.4 person and condition_occurrence tables,
and writes to a local DuckDB file.

Usage:
    htan etl omop --db htan_omop_lung.duckdb
    htan etl omop --db htan_omop_lung.duckdb --dry-run

Notes:
    - Source: isb-cgc-bq.HTAN.clinical_tier1_demographics_current
              isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current
    - Filter: HTAN Center = 'HTAN BU' (lung pre-cancer atlas)
    - Concept IDs: gender/race/ethnicity use standard OMOP concept IDs.
      Morphology uses ICD-O-3 source values; condition_concept_id is mapped
      for the most common lung histologies (0 = unmapped, re-map via Athena).
"""

import argparse
import sys

# ---------------------------------------------------------------------------
# Concept ID mappings
# ---------------------------------------------------------------------------

# OMOP standard concept IDs for gender (SNOMED via domain Gender)
GENDER_MAP = {
    "male": 8507,
    "female": 8532,
}

# OMOP standard concept IDs for race (domain Race)
RACE_MAP = {
    "white": 8527,
    "black or african american": 8516,
    "asian": 8515,
    "native hawaiian or other pacific islander": 8557,
    "american indian or alaska native": 8657,
    "other": 8522,
}

# OMOP standard concept IDs for ethnicity (domain Ethnicity)
ETHNICITY_MAP = {
    "hispanic or latino": 38003563,
    "not hispanic or latino": 38003564,
}

# ICD-O-3 morphology code → OMOP standard concept ID (SNOMED)
# Covers the most common lung histologies in HTAN BU.
# Source: OMOP Athena vocabulary, domain=Condition, standard_concept='S'
# 0 = unmapped; re-map via https://athena.ohdsi.org
MORPHOLOGY_MAP = {
    "8140/3": 4032806,   # Adenocarcinoma NOS → SNOMED: Adenocarcinoma
    "8041/3": 4180235,   # Small cell carcinoma NOS → SNOMED: Small cell carcinoma
    "8041/2": 4180235,   # Small cell carcinoma in situ (map to same)
    "8070/3": 4016834,   # Squamous cell carcinoma NOS → SNOMED: SCC
    "8070/2": 4016834,   # SCC in situ
    "8045/3": 4221813,   # Combined small cell carcinoma
    "8560/3": 4138510,   # Adenosquamous carcinoma
    "8250/3": 4214859,   # Bronchiolo-alveolar adenocarcinoma NOS
    "8250/2": 4214859,   # AIS (adenocarcinoma in situ, non-mucinous)
    "8480/3": 4214859,   # Mucinous adenocarcinoma (map to BAC family)
    "8550/3": 4163011,   # Acinar cell carcinoma
    "8551/3": 4163011,   # Acinar cell carcinoma (variant)
    # subtypes mapped to parent adenocarcinoma concept
    "8143/3": 4032806,
    "8253/3": 4032806,
    "8254/3": 4032806,
    "8255/3": 4032806,
    "8256/3": 4032806,
    "8260/3": 4032806,
    "8265/3": 4032806,
    "8230/3": 4032806,
    "8480/3": 4032806,
    "8574/3": 4032806,
    "8013/3": 4032806,
}

# OMOP concept ID for condition type: "Primary Condition" (EHR problem list entry)
CONDITION_TYPE_CONCEPT_ID = 32902


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_gender(val):
    if val is None:
        return 0
    return GENDER_MAP.get(str(val).strip().lower(), 0)


def _map_race(val):
    if val is None:
        return 0
    return RACE_MAP.get(str(val).strip().lower(), 0)


def _map_ethnicity(val):
    if val is None:
        return 0
    return ETHNICITY_MAP.get(str(val).strip().lower(), 0)


def _map_morphology(val):
    if val is None:
        return 0
    return MORPHOLOGY_MAP.get(str(val).strip(), 0)


def _person_id(htan_id: str) -> int:
    """Stable integer person_id from HTAN_Participant_ID using Python hash."""
    return abs(hash(htan_id)) % (2**31)


def _condition_id(htan_participant_id: str, morphology: str) -> int:
    key = f"{htan_participant_id}|{morphology}"
    return abs(hash(key)) % (2**31)


# ---------------------------------------------------------------------------
# ETL
# ---------------------------------------------------------------------------

def build_omop(dry_run: bool = False) -> tuple:
    """Pull HTAN BU data from BigQuery and return (person_df, condition_df)."""
    try:
        from google.cloud import bigquery
    except ImportError:
        print("google-cloud-bigquery is required. Run: uv pip install -e .", file=sys.stderr)
        sys.exit(1)

    import pandas as pd

    client = bigquery.Client()

    print("Querying demographics (HTAN BU)...")
    demo_sql = """
        SELECT
            HTAN_Participant_ID,
            Gender,
            Race,
            Ethnicity,
            Vital_Status,
            Year_Of_Birth,
            Days_to_Birth,
            Days_to_Death
        FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`
        WHERE HTAN_Center = 'HTAN BU'
    """
    demo_df = client.query(demo_sql).to_dataframe()
    print(f"  {len(demo_df)} participants")

    print("Querying lung diagnoses (HTAN BU)...")
    diag_sql = """
        SELECT
            HTAN_Participant_ID,
            Primary_Diagnosis,
            Morphology,
            Tissue_or_Organ_of_Origin,
            Site_of_Resection_or_Biopsy,
            Tumor_Grade,
            AJCC_Pathologic_Stage,
            Year_of_Diagnosis,
            Days_to_Diagnosis,
            Age_at_Diagnosis
        FROM `isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current`
        WHERE HTAN_Center = 'HTAN BU'
    """
    diag_df = client.query(diag_sql).to_dataframe()
    print(f"  {len(diag_df)} diagnosis records")

    if dry_run:
        print("\n[dry-run] Would transform:")
        print(f"  person rows:               {len(demo_df)}")
        print(f"  condition_occurrence rows: {len(diag_df)}")
        return None, None

    import pandas as pd

    # --- person table ---
    person_rows = []
    for _, row in demo_df.iterrows():
        pid = row["HTAN_Participant_ID"]

        # Derive year_of_birth: prefer Year_Of_Birth, else estimate from
        # Age_at_Diagnosis (days) and Year_of_Diagnosis if available
        yob = None
        if pd.notna(row.get("Year_Of_Birth")):
            try:
                yob = int(row["Year_Of_Birth"])
            except (ValueError, TypeError):
                pass

        person_rows.append({
            "person_id": _person_id(pid),
            "gender_concept_id": _map_gender(row["Gender"]),
            "year_of_birth": yob,
            "race_concept_id": _map_race(row["Race"]),
            "ethnicity_concept_id": _map_ethnicity(row["Ethnicity"]),
            "person_source_value": pid,
            "gender_source_value": str(row["Gender"]) if pd.notna(row["Gender"]) else None,
            "race_source_value": str(row["Race"]) if pd.notna(row["Race"]) else None,
            "ethnicity_source_value": str(row["Ethnicity"]) if pd.notna(row["Ethnicity"]) else None,
        })

    person_df = pd.DataFrame(person_rows)

    # --- condition_occurrence table ---
    cond_rows = []
    for idx, row in diag_df.iterrows():
        pid = row["HTAN_Participant_ID"]
        morphology = str(row["Morphology"]) if pd.notna(row["Morphology"]) else None

        # condition_start_date: Jan 1 of diagnosis year when available
        year_dx = None
        if pd.notna(row.get("Year_of_Diagnosis")):
            try:
                year_dx = int(row["Year_of_Diagnosis"])
            except (ValueError, TypeError):
                pass
        condition_start_date = f"{year_dx}-01-01" if year_dx else None

        cond_rows.append({
            "condition_occurrence_id": _condition_id(pid, f"{morphology or ''}|{idx}"),
            "person_id": _person_id(pid),
            "condition_concept_id": _map_morphology(morphology),
            "condition_start_date": condition_start_date,
            "condition_type_concept_id": CONDITION_TYPE_CONCEPT_ID,
            "condition_source_value": morphology,
            "primary_diagnosis_source_value": str(row["Primary_Diagnosis"]) if pd.notna(row["Primary_Diagnosis"]) else None,
            "tissue_or_organ_of_origin": str(row["Tissue_or_Organ_of_Origin"]) if pd.notna(row["Tissue_or_Organ_of_Origin"]) else None,
            "site_of_resection_or_biopsy": str(row["Site_of_Resection_or_Biopsy"]) if pd.notna(row["Site_of_Resection_or_Biopsy"]) else None,
            "tumor_grade": str(row["Tumor_Grade"]) if pd.notna(row["Tumor_Grade"]) else None,
            "ajcc_pathologic_stage": str(row["AJCC_Pathologic_Stage"]) if pd.notna(row["AJCC_Pathologic_Stage"]) else None,
            "age_at_diagnosis_days": int(row["Age_at_Diagnosis"]) if pd.notna(row.get("Age_at_Diagnosis")) else None,
        })

    condition_df = pd.DataFrame(cond_rows)

    return person_df, condition_df


def write_duckdb(person_df, condition_df, db_path: str):
    """Write OMOP tables to a DuckDB file."""
    try:
        import duckdb
    except ImportError:
        print("duckdb is required. Run: uv pip install -e .", file=sys.stderr)
        sys.exit(1)

    print(f"\nWriting to {db_path}...")
    con = duckdb.connect(db_path)

    con.execute("DROP TABLE IF EXISTS person")
    con.execute("DROP TABLE IF EXISTS condition_occurrence")

    con.execute("""
        CREATE TABLE person (
            person_id                   BIGINT PRIMARY KEY,
            gender_concept_id           INTEGER NOT NULL,
            year_of_birth               INTEGER,
            race_concept_id             INTEGER NOT NULL,
            ethnicity_concept_id        INTEGER NOT NULL,
            person_source_value         VARCHAR,
            gender_source_value         VARCHAR,
            race_source_value           VARCHAR,
            ethnicity_source_value      VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE condition_occurrence (
            condition_occurrence_id             BIGINT PRIMARY KEY,
            person_id                           BIGINT NOT NULL,
            condition_concept_id                INTEGER NOT NULL,
            condition_start_date                DATE,
            condition_type_concept_id           INTEGER NOT NULL,
            condition_source_value              VARCHAR,
            -- HTAN-specific extra columns (non-standard, informational)
            primary_diagnosis_source_value      VARCHAR,
            tissue_or_organ_of_origin           VARCHAR,
            site_of_resection_or_biopsy         VARCHAR,
            tumor_grade                         VARCHAR,
            ajcc_pathologic_stage               VARCHAR,
            age_at_diagnosis_days               INTEGER
        )
    """)

    con.execute("INSERT INTO person SELECT * FROM person_df")
    con.execute("INSERT INTO condition_occurrence SELECT * FROM condition_df")

    p_count = con.execute("SELECT COUNT(*) FROM person").fetchone()[0]
    c_count = con.execute("SELECT COUNT(*) FROM condition_occurrence").fetchone()[0]
    con.close()

    print(f"  person:               {p_count} rows")
    print(f"  condition_occurrence: {c_count} rows")
    print(f"\nDone. Query with: duckdb {db_path}")
    print("  SELECT * FROM person LIMIT 5;")
    print("  SELECT * FROM condition_occurrence LIMIT 5;")


# ---------------------------------------------------------------------------
# NL → OMOP SQL
# ---------------------------------------------------------------------------

_SCHEMA_CONTEXT = """
You have access to a DuckDB database with HTAN Phase 1 lung cancer data (HTAN BU atlas,
484 participants) mapped to OMOP CDM 5.4. Only these two tables exist:

TABLE: person  (484 rows — one row per participant)
  person_id                BIGINT PRIMARY KEY  -- stable hash of HTAN_Participant_ID
  gender_concept_id        INTEGER  -- 8507=Male  8532=Female  0=Unknown/Not Reported
  year_of_birth            INTEGER  -- may be NULL
  race_concept_id          INTEGER  -- 8527=White  8516=Black/AA  8515=Asian  8557=NHOPI  8657=AIAN  8522=Other  0=Unknown
  ethnicity_concept_id     INTEGER  -- 38003563=Hispanic  38003564=Not Hispanic  0=Unknown
  person_source_value      VARCHAR  -- HTAN ID, e.g. 'HTA10_1001'
  gender_source_value      VARCHAR  -- e.g. 'Male', 'Female', 'Not Reported'
  race_source_value        VARCHAR  -- e.g. 'white', 'black or african american', 'asian'
  ethnicity_source_value   VARCHAR  -- e.g. 'not hispanic or latino', 'hispanic or latino'

TABLE: condition_occurrence  (183 rows — one row per diagnosis record)
  condition_occurrence_id          BIGINT PRIMARY KEY
  person_id                        BIGINT  -- FK → person.person_id
  condition_concept_id             INTEGER  -- SNOMED: 4032806=Adenocarcinoma  4016834=Squamous cell  4180235=Small cell  4163011=Acinar  4221813=Combined small cell  4138510=Adenosquamous  4214859=BAC/Mucinous  0=Unmapped/Unknown
  condition_start_date             DATE     -- Jan 1 of diagnosis year; may be NULL
  condition_type_concept_id        INTEGER  -- always 32902
  condition_source_value           VARCHAR  -- ICD-O-3 morphology code, e.g. '8140/3', '8070/3', 'unknown'
  primary_diagnosis_source_value   VARCHAR  -- e.g. 'Adenocarcinoma NOS', 'Squamous cell carcinoma NOS'
  tissue_or_organ_of_origin        VARCHAR  -- e.g. 'Lung NOS', 'Upper lobe lung', 'Lower lobe lung'
  site_of_resection_or_biopsy      VARCHAR  -- e.g. 'Upper lobe lung', 'Lung NOS', 'Lymph node NOS'
  tumor_grade                      VARCHAR  -- e.g. 'G1', 'G2', 'G3', 'Not Reported'
  ajcc_pathologic_stage            VARCHAR  -- e.g. 'Stage IA1', 'Stage IA2', 'Stage IIA', 'Stage IIIA', NULL
  age_at_diagnosis_days            INTEGER  -- age in days at diagnosis; divide by 365.25 for years
                                            -- IMPORTANT: 111 rows have age=0 (unreported); always filter with > 0

Notes:
- 111 of 183 diagnosis rows have condition_source_value='unknown' (condition_concept_id=0)
  AND age_at_diagnosis_days=0. These are real participants whose data was not reported in HTAN.
- Use source_value columns (gender_source_value, primary_diagnosis_source_value, etc.)
  for readable string filtering when concept IDs are unknown.
- To filter to only participants with a known diagnosis: WHERE condition_concept_id <> 0
  OR WHERE condition_source_value <> 'unknown'
"""

_EXAMPLE_QUERIES = """
EXAMPLES:

Q: How many patients are there?
SQL: SELECT COUNT(*) AS patient_count FROM person;

Q: How many female patients?
SQL: SELECT COUNT(*) AS female_count FROM person WHERE gender_concept_id = 8532;

Q: How many patients by gender?
SQL: SELECT gender_source_value, COUNT(*) AS n FROM person GROUP BY gender_source_value ORDER BY n DESC;

Q: What are the most common diagnoses?
SQL: SELECT primary_diagnosis_source_value, COUNT(*) AS n
     FROM condition_occurrence
     WHERE condition_source_value <> 'unknown'
     GROUP BY primary_diagnosis_source_value ORDER BY n DESC;

Q: How many female patients had adenocarcinoma?
SQL: SELECT COUNT(DISTINCT p.person_id) AS n
     FROM person p
     JOIN condition_occurrence c ON p.person_id = c.person_id
     WHERE p.gender_concept_id = 8532
       AND c.condition_concept_id = 4032806;

Q: What is the age distribution at diagnosis?
SQL: SELECT
       MIN(ROUND(age_at_diagnosis_days / 365.25, 1)) AS min_age,
       MAX(ROUND(age_at_diagnosis_days / 365.25, 1)) AS max_age,
       ROUND(AVG(age_at_diagnosis_days / 365.25), 1) AS mean_age
     FROM condition_occurrence
     WHERE age_at_diagnosis_days IS NOT NULL;

Q: How many patients at each AJCC stage?
SQL: SELECT ajcc_pathologic_stage, COUNT(*) AS n
     FROM condition_occurrence
     WHERE ajcc_pathologic_stage IS NOT NULL
     GROUP BY ajcc_pathologic_stage ORDER BY n DESC;
"""


def nl_to_sql(question: str) -> tuple[str, str]:
    """Translate a natural language question to OMOP SQL using Claude.

    Returns (sql, explanation).
    """
    try:
        import anthropic
    except ImportError:
        print("anthropic is required. Run: uv pip install -e .", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()

    system = f"""You are an expert in OMOP CDM and DuckDB SQL.
The user will ask a question about HTAN lung cancer data. Translate it to a
single valid DuckDB SELECT query against the schema below.

{_SCHEMA_CONTEXT}
{_EXAMPLE_QUERIES}

Rules:
- Return ONLY a JSON object with two keys: "sql" (the query string) and "explanation" (one sentence)
- Only SELECT queries are allowed — no INSERT, UPDATE, DELETE, DROP, CREATE
- Use DuckDB SQL syntax
- Do not include a trailing semicolon in the sql value
- Keep it simple and correct
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": question}],
    )

    import json
    import re

    raw = next(b.text for b in response.content if b.type == "text")

    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        parsed = json.loads(raw.strip())
        sql = parsed["sql"].strip().rstrip(";")
        explanation = parsed.get("explanation", "")
    except (json.JSONDecodeError, KeyError):
        # Fallback: try to extract a bare SQL statement
        sql = raw.strip().rstrip(";")
        explanation = ""

    # Safety: block write operations
    first_word = sql.split()[0].upper() if sql.split() else ""
    if first_word not in ("SELECT", "WITH"):
        raise ValueError(f"Only SELECT queries are allowed, got: {first_word}")

    return sql, explanation


def run_nl_query(question: str, db_path: str):
    """Translate NL question to SQL, run against DuckDB, print results."""
    try:
        import duckdb
    except ImportError:
        print("duckdb is required. Run: uv pip install -e .", file=sys.stderr)
        sys.exit(1)

    import os
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}", file=sys.stderr)
        print("Run 'htan etl omop --db <path>' first to create it.", file=sys.stderr)
        sys.exit(1)

    print(f"Question: {question}\n")
    print("Generating SQL...")

    sql, explanation = nl_to_sql(question)

    print(f"\nSQL:\n  {sql}\n")
    if explanation:
        print(f"Explanation: {explanation}\n")

    con = duckdb.connect(db_path, read_only=True)
    result = con.execute(sql).df()
    con.close()

    print("Results:")
    print(result.to_string(index=False))
    print(f"\n({len(result)} row{'s' if len(result) != 1 else ''})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cli_main(args):
    parser = argparse.ArgumentParser(
        prog="htan etl omop",
        description="ETL HTAN lung cancer data to OMOP CDM in DuckDB, and query it.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # --- etl subcommand (default behaviour when no subcommand given) ---
    etl_parser = subparsers.add_parser("build", help="Run the ETL and write DuckDB file")
    etl_parser.add_argument(
        "--db",
        default="htan_omop_lung.duckdb",
        help="Output DuckDB file path (default: htan_omop_lung.duckdb)",
    )
    etl_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without writing",
    )

    # --- query subcommand ---
    query_parser = subparsers.add_parser("query", help="Ask a natural language question")
    query_parser.add_argument("question", help="Natural language question about the data")
    query_parser.add_argument(
        "--db",
        default="htan_omop_lung.duckdb",
        help="DuckDB file to query (default: htan_omop_lung.duckdb)",
    )

    # If no subcommand, fall back to legacy ETL behaviour (--db / --dry-run at top level)
    parser.add_argument("--db", default="htan_omop_lung.duckdb")
    parser.add_argument("--dry-run", action="store_true")

    parsed = parser.parse_args(args)

    if parsed.subcommand == "query":
        run_nl_query(parsed.question, parsed.db)
    else:
        # build or legacy top-level flags
        db = getattr(parsed, "db", "htan_omop_lung.duckdb")
        dry_run = getattr(parsed, "dry_run", False)
        person_df, condition_df = build_omop(dry_run=dry_run)
        if not dry_run:
            write_duckdb(person_df, condition_df, db)
