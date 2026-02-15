"""Query HTAN metadata in ISB-CGC BigQuery.

Supports direct SQL, table listing, and schema inspection.
Requires: pip install htan[bigquery]

Usage as library:
    from htan.query.bq import BigQueryClient
    client = BigQueryClient()
    tables = client.list_tables()
    schema = client.describe_table("clinical_tier1_demographics")

Usage as CLI:
    htan query bq tables
    htan query bq describe clinical_tier1_demographics
    htan query bq sql "SELECT COUNT(*) FROM ..."
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

BLOCKED_SQL_KEYWORDS = [
    "DELETE", "DROP", "UPDATE", "INSERT", "CREATE",
    "ALTER", "TRUNCATE", "MERGE", "GRANT", "REVOKE",
]
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
  Primary_Diagnosis (STRING) - ICD-O-3 diagnosis
  Site_of_Resection_or_Biopsy (STRING)
  Tissue_or_Organ_of_Origin (STRING)
  Tumor_Grade (STRING) - G1, G2, G3
  AJCC_Pathologic_Stage (STRING)
  Morphology (STRING)

--- Biospecimen ---

Table: biospecimen_current
  HTAN_Biospecimen_ID (STRING) - e.g. HTA1_1001_001
  HTAN_Participant_ID (STRING)
  HTAN_Center (STRING)
  Biospecimen_Type (STRING)
  Preservation_Method (STRING)
  Tumor_Tissue_Type (STRING)

--- Assay metadata ---

Table: scRNAseq_level1_metadata_current (also level2, level3, level4)
  HTAN_Parent_Biospecimen_ID (STRING)
  HTAN_Data_File_ID (STRING)
  Library_Construction_Method (STRING)
  Filename (STRING)
  File_Size (INTEGER) -- file size in bytes (present in ALL assay metadata tables)
  entityId (STRING) -- Synapse ID (present in ALL assay metadata tables)
  HTAN_Center (STRING)

=== Notes ===
- Join clinical tables on HTAN_Participant_ID
- Join assay to biospecimen on HTAN_Parent_Biospecimen_ID = HTAN_Biospecimen_ID
- Dataset: isb-cgc-bq.HTAN (use fully qualified table names with _current suffix)
- File_Size (INTEGER, bytes) and entityId (STRING, Synapse ID) exist in ALL assay metadata tables
""".strip()


class BigQueryError(Exception):
    """BigQuery operation error."""
    pass


def validate_sql_safety(sql):
    """Validate that SQL is read-only. Returns (safe, reason)."""
    normalized = " ".join(sql.upper().split())
    for keyword in BLOCKED_SQL_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, normalized):
            return False, f"Blocked SQL keyword: {keyword}"
    first_word = normalized.split()[0] if normalized.split() else ""
    if first_word not in ALLOWED_SQL_STARTS:
        return False, f"SQL must start with one of: {', '.join(ALLOWED_SQL_STARTS)}"
    return True, "OK"


def _ensure_limit(sql, limit=DEFAULT_LIMIT):
    normalized = " ".join(sql.upper().split())
    if "LIMIT" not in normalized:
        sql = sql.rstrip().rstrip(";")
        sql += f"\nLIMIT {limit}"
        print(f"Auto-applied LIMIT {limit}", file=sys.stderr)
    return sql


def _get_bq_module():
    try:
        from google.cloud import bigquery
        return bigquery
    except ImportError:
        raise BigQueryError(
            "google-cloud-bigquery not installed. Run: pip install htan[bigquery]"
        )


class BigQueryClient:
    """High-level client for HTAN BigQuery queries.

    Requires: pip install htan[bigquery]

    Usage:
        client = BigQueryClient()
        tables = client.list_tables()
    """

    def __init__(self, project=None):
        """Initialize BigQuery client.

        Args:
            project: Google Cloud project ID for billing. If None, uses default.
        """
        import os
        bq = _get_bq_module()
        project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        try:
            self._client = bq.Client(project=project) if project else bq.Client()
        except Exception as e:
            raise BigQueryError(
                f"Could not create BigQuery client: {e}\n"
                "Run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS"
            )

    def query(self, sql, limit=DEFAULT_LIMIT, dry_run=False):
        """Execute a read-only SQL query. Returns pandas DataFrame."""
        bq = _get_bq_module()
        safe, reason = validate_sql_safety(sql)
        if not safe:
            raise BigQueryError(reason)
        sql = _ensure_limit(sql, limit)

        if dry_run:
            job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
            job = self._client.query(sql, job_config=job_config)
            return {"bytes_processed": job.total_bytes_processed or 0, "sql": sql}

        return self._client.query(sql).to_dataframe()

    def list_tables(self, versioned=False):
        """List available HTAN tables. Returns list of table name strings."""
        dataset = HTAN_DATASET_VERSIONED if versioned else HTAN_DATASET
        sql = f"SELECT table_name FROM `{dataset}.INFORMATION_SCHEMA.TABLES` ORDER BY table_name"
        df = self._client.query(sql).to_dataframe()
        return df["table_name"].tolist()

    def describe_table(self, table, versioned=False):
        """Describe table schema. Returns dict with table info and schema."""
        if not TABLE_NAME_PATTERN.match(table):
            raise BigQueryError(f"Invalid table name '{table}'.")
        dataset = HTAN_DATASET_VERSIONED if versioned else HTAN_DATASET
        if not versioned and not re.search(r"_(current|r\d+(_v\d+)?)$", table):
            table = f"{table}_current"
        full_table = f"{dataset}.{table}"
        try:
            tbl = self._client.get_table(full_table)
        except Exception as e:
            raise BigQueryError(f"Could not access table '{full_table}': {e}")
        return {
            "table": full_table,
            "num_rows": tbl.num_rows,
            "num_bytes": tbl.num_bytes,
            "description": tbl.description,
            "schema": [
                {"name": f.name, "type": f.field_type, "mode": f.mode, "description": f.description or ""}
                for f in tbl.schema
            ],
        }


# --- CLI ---

def cli_main(argv=None):
    """CLI entry point for BigQuery queries."""
    parser = argparse.ArgumentParser(
        description="Query HTAN metadata in ISB-CGC BigQuery",
        epilog="Examples:\n"
        "  htan query bq tables\n"
        "  htan query bq describe clinical_tier1_demographics\n"
        '  htan query bq sql "SELECT COUNT(*) FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`"\n'
        '  htan query bq query "How many breast cancer patients?"\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp_query = subparsers.add_parser("query", help="Natural language query (outputs context for Claude)")
    sp_query.add_argument("question", help="Natural language question")
    sp_query.add_argument("--project", "-p", help="Google Cloud project ID")
    sp_query.add_argument("--format", "-f", choices=["text", "json", "csv"], default="text")

    sp_sql = subparsers.add_parser("sql", help="Execute a direct SQL query")
    sp_sql.add_argument("sql", help="SQL query")
    sp_sql.add_argument("--project", "-p", help="Google Cloud project ID")
    sp_sql.add_argument("--format", "-f", choices=["text", "json", "csv"], default="text")
    sp_sql.add_argument("--dry-run", action="store_true")

    sp_tables = subparsers.add_parser("tables", help="List available HTAN tables")
    sp_tables.add_argument("--project", "-p", help="Google Cloud project ID")
    sp_tables.add_argument("--dry-run", action="store_true")
    sp_tables.add_argument("--versioned", action="store_true")

    sp_desc = subparsers.add_parser("describe", help="Describe table schema")
    sp_desc.add_argument("table_name", help="Table name")
    sp_desc.add_argument("--project", "-p", help="Google Cloud project ID")
    sp_desc.add_argument("--dry-run", action="store_true")
    sp_desc.add_argument("--versioned", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "query":
        # Output NL query context for Claude
        print("=== HTAN BigQuery Natural Language Query ===")
        print()
        print("USER QUESTION:", args.question)
        print()
        print(TABLE_SCHEMAS_SUMMARY)
        print()
        print("=== INSTRUCTIONS ===")
        print("Generate a safe read-only SQL query against isb-cgc-bq.HTAN tables.")
        print("Then execute with: htan query bq sql \"YOUR_SQL_HERE\"")
        return

    try:
        client = BigQueryClient(project=getattr(args, "project", None))
    except BigQueryError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "sql":
        try:
            if args.dry_run:
                result = client.query(args.sql, dry_run=True)
                bytes_est = result["bytes_processed"]
                if bytes_est > 1_000_000_000:
                    cost_str = f"{bytes_est / 1_000_000_000:.2f} GB"
                elif bytes_est > 1_000_000:
                    cost_str = f"{bytes_est / 1_000_000:.1f} MB"
                else:
                    cost_str = f"{bytes_est:,} bytes"
                print(f"Dry run — estimated data processed: {cost_str}", file=sys.stderr)
                print(f"SQL:\n{result['sql']}", file=sys.stderr)
                return

            df = client.query(args.sql)
            if df.empty:
                print("Query returned no results.", file=sys.stderr)
                return
            print(f"Returned {len(df)} rows, {len(df.columns)} columns", file=sys.stderr)
            if args.format == "json":
                print(df.to_json(orient="records", indent=2))
            elif args.format == "csv":
                output = io.StringIO()
                df.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
                print(output.getvalue())
            else:
                print(df.to_string(index=False))
        except BigQueryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "tables":
        if args.dry_run:
            dataset = HTAN_DATASET_VERSIONED if args.versioned else HTAN_DATASET
            print(f"Dry run — would list tables from {dataset}", file=sys.stderr)
            return
        try:
            tables = client.list_tables(versioned=args.versioned)
            for t in tables:
                print(t)
            print(f"\n{len(tables)} tables", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "describe":
        if args.dry_run:
            print(f"Dry run — would describe: {args.table_name}", file=sys.stderr)
            return
        try:
            info = client.describe_table(args.table_name, versioned=args.versioned)
            print(f"Table: {info['table']}")
            print(f"Rows: {info['num_rows']:,}")
            print(f"Size: {info['num_bytes']:,} bytes")
            if info["description"]:
                print(f"Description: {info['description']}")
            print()
            print(f"{'Column':<40} {'Type':<15} {'Mode':<10} {'Description'}")
            print(f"{'-'*40} {'-'*15} {'-'*10} {'-'*30}")
            for f in info["schema"]:
                desc = f["description"]
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                print(f"{f['name']:<40} {f['type']:<15} {f['mode']:<10} {desc}")
            print(f"\n{len(info['schema'])} columns", file=sys.stderr)
        except BigQueryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
