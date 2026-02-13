#!/usr/bin/env python3
"""Query HTAN metadata in ISB-CGC BigQuery.

Supports natural language queries (via Claude), direct SQL, table listing, and schema inspection.

Requires: pip install google-cloud-bigquery google-cloud-bigquery-storage pandas
Auth: Google Cloud credentials (ADC or service account key)

Usage:
    python3 scripts/htan_bigquery.py query "How many patients with breast cancer?"
    python3 scripts/htan_bigquery.py sql "SELECT COUNT(*) FROM ..."
    python3 scripts/htan_bigquery.py tables
    python3 scripts/htan_bigquery.py describe clinical_tier1_demographics
"""

import argparse
import csv
import io
import json
import re
import sys


HTAN_DATASET = "isb-cgc-bq.HTAN"
HTAN_DATASET_VERSIONED = "isb-cgc-bq.HTAN_versioned"
DEFAULT_LIMIT = 1000

# SQL keywords that indicate write/destructive operations — block these
BLOCKED_SQL_KEYWORDS = [
    "DELETE",
    "DROP",
    "UPDATE",
    "INSERT",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "MERGE",
    "GRANT",
    "REVOKE",
]

# SQL keywords that indicate read operations — allow these
ALLOWED_SQL_STARTS = ["SELECT", "WITH", "SHOW", "EXPLAIN"]

TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")

# Key table schemas for natural language query context
TABLE_SCHEMAS_SUMMARY = """
=== HTAN BigQuery Table Schemas (isb-cgc-bq.HTAN) ===
Tables use _current suffix, which always points to the latest release.
For reproducible analyses with a specific version, use isb-cgc-bq.HTAN_versioned with _rN suffixes.

--- Clinical tables ---

Table: clinical_tier1_demographics_current
  HTAN_Participant_ID (STRING) - Participant identifier, e.g. HTA1_1001
  HTAN_Center (STRING) - Atlas center, e.g. 'HTAN HTAPP', 'HTAN HMS'
  Age_at_Diagnosis (INTEGER) - Age in days at diagnosis
  Gender (STRING) - male, female
  Race (STRING) - e.g. white, black or african american, asian
  Ethnicity (STRING) - e.g. not hispanic or latino, hispanic or latino
  Vital_Status (STRING) - Alive, Dead

Table: clinical_tier1_diagnosis_current
  HTAN_Participant_ID (STRING)
  HTAN_Center (STRING)
  Primary_Diagnosis (STRING) - ICD-O-3 diagnosis, e.g. 'Infiltrating duct carcinoma, NOS'
  Site_of_Resection_or_Biopsy (STRING) - e.g. 'Breast, NOS', 'Colon, NOS'
  Tissue_or_Organ_of_Origin (STRING) - e.g. 'Breast', 'Colon'
  Tumor_Grade (STRING) - G1, G2, G3
  AJCC_Pathologic_Stage (STRING) - e.g. 'Stage IIA', 'Stage IIIC'
  Morphology (STRING) - ICD-O-3 morphology code

Table: clinical_tier1_followup_current
  HTAN_Participant_ID (STRING)
  Days_to_Follow_Up (INTEGER)
  Disease_Status (STRING)
  Progression_or_Recurrence (STRING)

--- Biospecimen ---

Table: biospecimen_current
  HTAN_Biospecimen_ID (STRING) - e.g. HTA1_1001_001
  HTAN_Participant_ID (STRING)
  HTAN_Center (STRING)
  Biospecimen_Type (STRING)
  Site_of_Resection (STRING)
  Preservation_Method (STRING) - Fresh Frozen, FFPE, OCT
  Tumor_Tissue_Type (STRING) - Tumor, Normal, Pre-cancer
  Collection_Days_from_Index (INTEGER)

--- Assay metadata (each has level1-4 variants) ---

Table: scRNAseq_level1_metadata_current (also level2, level3, level4)
  HTAN_Parent_Biospecimen_ID (STRING) - links to biospecimen table
  HTAN_Data_File_ID (STRING) - key for resolving to download coordinates
  Library_Construction_Method (STRING) - e.g. '10x 3' v3'
  Dissociation_Method (STRING)
  Filename (STRING)
  HTAN_Center (STRING)

Table: scATACseq_level1_metadata_current (also level2, level3, level4)
  HTAN_Parent_Biospecimen_ID (STRING)
  HTAN_Data_File_ID (STRING)
  Library_Construction_Method (STRING)

Table: bulkRNAseq_level1_metadata_current (also level2, level3)
  HTAN_Parent_Biospecimen_ID (STRING)
  HTAN_Data_File_ID (STRING)
  Library_Construction_Method (STRING)

Table: bulkWES_level1_metadata_current (also level2, level3)
  HTAN_Parent_Biospecimen_ID (STRING)
  HTAN_Data_File_ID (STRING)
  Library_Construction_Method (STRING)

Table: imaging_level2_metadata_current (also level1, level3_segmentation, level4)
  HTAN_Parent_Biospecimen_ID (STRING)
  HTAN_Data_File_ID (STRING)

Table: 10xvisium_spatialtranscriptomics_scRNAseq_level1_metadata_current (also level2, level3, level4)
  HTAN_Parent_Biospecimen_ID (STRING)
  HTAN_Data_File_ID (STRING)

Other assay tables: bulkMethylationseq, hiCseq, massSpectrometry, rppa,
  electron_microscopy, nanostring_spatialtranscriptomics_geomx, Slide_seq,
  10xxenium_spatialtranscriptomics, ScDNAseq (use `tables` subcommand to list all)

=== HTAN Centers ===
HTAN HTAPP, HTAN HMS, HTAN OHSU, HTAN MSK, HTAN Stanford,
HTAN Vanderbilt, HTAN WUSTL, HTAN CHOP, HTAN Duke, HTAN BU, HTAN DFCI,
HTAN TNP SARDANA, HTAN TNP SRRS, HTAN TNP TMA

=== Mapping table ===

Table: gc_drs_map_current
  HTAN_Data_File_ID (STRING)
  entityId (STRING) - Synapse ID for download
  drs_uri (STRING) - Gen3 DRS URI for controlled-access download
  name (STRING) - filename
  HTAN_Center (STRING)

=== Notes ===
- Join clinical tables on HTAN_Participant_ID; join assay to biospecimen on HTAN_Parent_Biospecimen_ID = HTAN_Biospecimen_ID
- Dataset: isb-cgc-bq.HTAN (use fully qualified table names with _current suffix)
- For reproducible analyses, use isb-cgc-bq.HTAN_versioned with _rN suffixes (e.g. _r7)
- Assay tables have level-specific variants (level1=raw, level2=aligned, level3=processed, level4=analysis)
- Assay metadata tables include entityId directly — use it for Synapse downloads
- For Gen3 DRS URIs, join to gc_drs_map_current on entityId or use htan_file_mapping.py for offline lookup
- After getting entityId: python3 scripts/htan_synapse.py download <entityId>
- After getting drs_uri: python3 scripts/htan_gen3.py download "drs://<drs_uri>"

=== Data Model Reference ===
- For valid values of any column, run: python3 scripts/htan_data_model.py valid-values "Column Name"
- For all attributes in a component: python3 scripts/htan_data_model.py attributes "Component Name"
- Component names match BigQuery table prefixes (e.g., "scRNA-seq Level 1" → scRNAseq_level1_metadata)
""".strip()


def validate_sql_safety(sql):
    """Validate that SQL is read-only. Returns (safe, reason)."""
    # Normalize whitespace and check
    normalized = " ".join(sql.upper().split())

    # Check for blocked keywords as standalone words
    for keyword in BLOCKED_SQL_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, normalized):
            return False, f"Blocked SQL keyword: {keyword}"

    # Verify it starts with an allowed keyword
    first_word = normalized.split()[0] if normalized.split() else ""
    if first_word not in ALLOWED_SQL_STARTS:
        return False, f"SQL must start with one of: {', '.join(ALLOWED_SQL_STARTS)}"

    return True, "OK"


def validate_table_name(name):
    """Validate table name contains only safe characters."""
    if not TABLE_NAME_PATTERN.match(name):
        print(f"Error: Invalid table name '{name}'. Use only alphanumeric and underscores.", file=sys.stderr)
        sys.exit(1)
    return name


def ensure_limit(sql, limit=DEFAULT_LIMIT):
    """Add LIMIT clause if none present."""
    normalized = " ".join(sql.upper().split())
    if "LIMIT" not in normalized:
        sql = sql.rstrip().rstrip(";")
        sql += f"\nLIMIT {limit}"
        print(f"Auto-applied LIMIT {limit}", file=sys.stderr)
    return sql


def get_bigquery_client(project=None):
    """Create BigQuery client."""
    try:
        from google.cloud import bigquery
    except ImportError:
        print(
            "Error: google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery",
            file=sys.stderr,
        )
        sys.exit(1)

    import os

    project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")

    try:
        if project:
            client = bigquery.Client(project=project)
        else:
            client = bigquery.Client()
        print(f"BigQuery project: {client.project}", file=sys.stderr)
        return client
    except Exception as e:
        print(f"Error: Could not create BigQuery client: {e}", file=sys.stderr)
        print("Run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS", file=sys.stderr)
        print("See references/authentication_guide.md for setup instructions.", file=sys.stderr)
        sys.exit(1)


def list_htan_tables(client, dry_run=False, versioned=False):
    """List available HTAN tables in BigQuery."""
    dataset = HTAN_DATASET_VERSIONED if versioned else HTAN_DATASET
    sql = f"""
    SELECT table_name, table_type
    FROM `{dataset}.INFORMATION_SCHEMA.TABLES`
    ORDER BY table_name
    """

    if dry_run:
        print("Dry run — would execute:", file=sys.stderr)
        print(f"  {sql.strip()}", file=sys.stderr)
        return

    try:
        df = client.query(sql).to_dataframe()
    except Exception as e:
        print(f"Error querying table list: {e}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print("No tables found.", file=sys.stderr)
        return

    for _, row in df.iterrows():
        print(row["table_name"])

    print(f"\n{len(df)} tables", file=sys.stderr)


def describe_table(client, table_name, dry_run=False, versioned=False):
    """Describe the schema of an HTAN table."""
    validate_table_name(table_name)
    dataset = HTAN_DATASET_VERSIONED if versioned else HTAN_DATASET
    # Auto-append _current suffix when using the default (non-versioned) dataset,
    # unless the name already ends with _current or a version suffix like _r7
    if not versioned and not re.search(r"_(current|r\d+(_v\d+)?)$", table_name):
        table_name = f"{table_name}_current"
        print(f"Using table: {table_name} (auto-appended _current suffix)", file=sys.stderr)
    full_table = f"{dataset}.{table_name}"

    if dry_run:
        print(f"Dry run — would describe: {full_table}", file=sys.stderr)
        return

    try:
        table = client.get_table(full_table)
    except Exception as e:
        print(f"Error: Could not access table '{full_table}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Table: {full_table}")
    print(f"Rows: {table.num_rows:,}")
    print(f"Size: {table.num_bytes:,} bytes")
    if table.description:
        print(f"Description: {table.description}")
    print()

    print(f"{'Column':<40} {'Type':<15} {'Mode':<10} {'Description'}")
    print(f"{'-'*40} {'-'*15} {'-'*10} {'-'*30}")
    for field in table.schema:
        desc = field.description or ""
        if len(desc) > 50:
            desc = desc[:47] + "..."
        print(f"{field.name:<40} {field.field_type:<15} {field.mode:<10} {desc}")

    print(f"\n{len(table.schema)} columns", file=sys.stderr)


def execute_query(client, sql, output_format="text", dry_run=False):
    """Execute a SQL query and display results."""
    from google.cloud import bigquery as bq

    safe, reason = validate_sql_safety(sql)
    if not safe:
        print(f"Error: {reason}", file=sys.stderr)
        print("Only read-only queries (SELECT, WITH) are allowed.", file=sys.stderr)
        sys.exit(1)

    sql = ensure_limit(sql)

    if dry_run:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        try:
            job = client.query(sql, job_config=job_config)
            bytes_est = job.total_bytes_processed or 0
            if bytes_est > 1_000_000_000:
                cost_str = f"{bytes_est / 1_000_000_000:.2f} GB"
            elif bytes_est > 1_000_000:
                cost_str = f"{bytes_est / 1_000_000:.1f} MB"
            else:
                cost_str = f"{bytes_est:,} bytes"
            print(f"Dry run — estimated data processed: {cost_str}", file=sys.stderr)
            print(f"SQL:\n{sql}", file=sys.stderr)
        except Exception as e:
            print(f"Error in dry run: {e}", file=sys.stderr)
            sys.exit(1)
        return

    print(f"Executing query...", file=sys.stderr)
    try:
        df = client.query(sql).to_dataframe()
    except Exception as e:
        print(f"Error executing query: {e}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print("Query returned no results.", file=sys.stderr)
        return

    print(f"Returned {len(df)} rows, {len(df.columns)} columns", file=sys.stderr)

    if output_format == "json":
        print(df.to_json(orient="records", indent=2))
    elif output_format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
        print(output.getvalue())
    else:
        print(df.to_string(index=False))


def cmd_query(args):
    """Handle the 'query' subcommand — natural language query.

    Outputs structured context for Claude to generate SQL.
    """
    question = args.question

    print("=== HTAN BigQuery Natural Language Query ===")
    print()
    print("USER QUESTION:", question)
    print()
    print(TABLE_SCHEMAS_SUMMARY)
    print()
    print("=== INSTRUCTIONS ===")
    print("Based on the user's question and the table schemas above, generate a safe")
    print("read-only SQL query against isb-cgc-bq.HTAN tables (using _current suffix).")
    print("Include entityId in SELECT when querying assay tables — this is the Synapse ID")
    print("needed for download via: python3 scripts/htan_synapse.py download <entityId>")
    print("Then execute it by running:")
    print(f'  python3 scripts/htan_bigquery.py sql "YOUR_SQL_HERE"', end="")
    if args.project:
        print(f" --project {args.project}", end="")
    if args.format != "text":
        print(f" --format {args.format}", end="")
    print()


def cmd_sql(args):
    """Handle the 'sql' subcommand — direct SQL execution."""
    client = get_bigquery_client(args.project)
    execute_query(client, args.sql, output_format=args.format, dry_run=args.dry_run)


def cmd_tables(args):
    """Handle the 'tables' subcommand."""
    client = get_bigquery_client(args.project)
    list_htan_tables(client, dry_run=args.dry_run, versioned=args.versioned)


def cmd_describe(args):
    """Handle the 'describe' subcommand."""
    client = get_bigquery_client(args.project)
    describe_table(client, args.table_name, dry_run=args.dry_run, versioned=args.versioned)


def main():
    parser = argparse.ArgumentParser(
        description="Query HTAN metadata in ISB-CGC BigQuery",
        epilog="Examples:\n"
        '  python3 scripts/htan_bigquery.py query "How many breast cancer patients?"\n'
        '  python3 scripts/htan_bigquery.py sql "SELECT COUNT(*) FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`"\n'
        "  python3 scripts/htan_bigquery.py tables\n"
        "  python3 scripts/htan_bigquery.py describe clinical_tier1_demographics\n"
        "  python3 scripts/htan_bigquery.py tables --versioned  # list from HTAN_versioned\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # query subcommand
    sp_query = subparsers.add_parser(
        "query", help="Natural language query (outputs context for Claude to generate SQL)"
    )
    sp_query.add_argument("question", help="Natural language question about HTAN data")
    sp_query.add_argument("--project", "-p", help="Google Cloud project ID for billing")
    sp_query.add_argument(
        "--format", "-f", choices=["text", "json", "csv"], default="text", help="Output format"
    )
    sp_query.add_argument("--limit", "-l", type=int, default=DEFAULT_LIMIT, help="Row limit")
    sp_query.add_argument("--dry-run", action="store_true", help="Show query plan without executing")

    # sql subcommand
    sp_sql = subparsers.add_parser("sql", help="Execute a direct SQL query")
    sp_sql.add_argument("sql", help="SQL query to execute")
    sp_sql.add_argument("--project", "-p", help="Google Cloud project ID for billing")
    sp_sql.add_argument(
        "--format", "-f", choices=["text", "json", "csv"], default="text", help="Output format"
    )
    sp_sql.add_argument("--dry-run", action="store_true", help="Estimate cost without executing")

    # tables subcommand
    sp_tables = subparsers.add_parser("tables", help="List available HTAN tables")
    sp_tables.add_argument("--project", "-p", help="Google Cloud project ID for billing")
    sp_tables.add_argument("--dry-run", action="store_true", help="Show query without executing")
    sp_tables.add_argument(
        "--versioned", action="store_true",
        help="List tables from HTAN_versioned dataset instead of HTAN (current)"
    )

    # describe subcommand
    sp_desc = subparsers.add_parser("describe", help="Describe table schema")
    sp_desc.add_argument(
        "table_name",
        help="Table name (e.g., clinical_tier1_demographics). "
        "_current suffix is auto-appended unless already present or using --versioned."
    )
    sp_desc.add_argument("--project", "-p", help="Google Cloud project ID for billing")
    sp_desc.add_argument("--dry-run", action="store_true", help="Show what would be queried")
    sp_desc.add_argument(
        "--versioned", action="store_true",
        help="Use HTAN_versioned dataset instead of HTAN (current)"
    )

    args = parser.parse_args()
    func = {
        "query": cmd_query,
        "sql": cmd_sql,
        "tables": cmd_tables,
        "describe": cmd_describe,
    }[args.command]
    func(args)


if __name__ == "__main__":
    main()
