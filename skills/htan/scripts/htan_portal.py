#!/usr/bin/env python3
"""Query HTAN data via the HTAN Data Portal's ClickHouse backend.

The HTAN data portal (data.humantumoratlas.org) uses a ClickHouse cloud database.
Credentials are loaded from ~/.config/htan-skill/portal.json (populated by
`htan_setup.py init-portal`). This script queries via the HTTP interface —
zero extra dependencies (stdlib only).

Provides a simpler 2-step workflow: portal query → download (vs. BigQuery → file
mapping → download). No GCP project or billing required.

Usage:
    python3 scripts/htan_portal.py tables
    python3 scripts/htan_portal.py describe files
    python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --limit 5
    python3 scripts/htan_portal.py sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"
    python3 scripts/htan_portal.py manifest HTA9_1_19512 --output-dir /tmp/manifests
"""

import argparse
import base64
import csv
import io
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


# --- ClickHouse connection (lazy-loaded from config file) ---
_portal_cfg = None


def _cfg():
    """Lazy-load portal credentials from ~/.config/htan-skill/portal.json."""
    global _portal_cfg
    if _portal_cfg is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from htan_portal_config import load_portal_config
        _portal_cfg = load_portal_config()
    return _portal_cfg


DEFAULT_LIMIT = 100
SQL_DEFAULT_LIMIT = 1000

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
ALLOWED_SQL_STARTS = ["SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN", "EXISTS"]

TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def normalize_sql(sql):
    """Normalize SQL for ClickHouse compatibility.

    ClickHouse doesn't support the != operator — use <> instead.
    This is safe because != and <> are semantically identical in all SQL dialects.
    """
    sql = sql.replace('!=', '<>')
    return sql


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


def validate_table_name(name):
    """Validate table name contains only safe characters."""
    if not TABLE_NAME_PATTERN.match(name):
        print(f"Error: Invalid table name '{name}'. Use only alphanumeric and underscores.", file=sys.stderr)
        sys.exit(1)
    return name


def escape_sql_string(s):
    """Escape a string value for safe inclusion in SQL. Returns the escaped string without quotes."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def ensure_limit(sql, limit=DEFAULT_LIMIT):
    """Add LIMIT clause if none present."""
    normalized = " ".join(sql.upper().split())
    if "LIMIT" not in normalized:
        sql = sql.rstrip().rstrip(";")
        sql += f"\nLIMIT {limit}"
        print(f"Auto-applied LIMIT {limit}", file=sys.stderr)
    return sql


def discover_database():
    """Discover the latest HTAN database by querying SHOW DATABASES.

    Falls back to the config file's default_database if discovery fails.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from htan_portal_config import get_default_database
    config_default = get_default_database(_cfg())

    try:
        # Query without specifying a database
        resp = clickhouse_query("SHOW DATABASES LIKE 'htan_%'", fmt="TabSeparated", database="")
        if not resp.strip():
            return config_default

        databases = [line.strip() for line in resp.strip().split("\n") if line.strip()]
        # Sort by name (date suffix means lexicographic = chronological)
        htan_dbs = sorted([db for db in databases if db.startswith("htan_")], reverse=True)
        if htan_dbs:
            latest = htan_dbs[0]
            if config_default and latest != config_default:
                print(f"Discovered newer database: {latest} (config default was {config_default})", file=sys.stderr)
            return latest
    except Exception:
        pass

    return config_default


def clickhouse_query(sql, fmt="JSONEachRow", database=None, timeout=60):
    """Execute a read-only SQL query against the ClickHouse HTTP interface.

    Args:
        sql: SQL query string
        fmt: ClickHouse output format (JSONEachRow, TabSeparated, CSV, etc.)
        database: Database name to query against (None = use config default)
        timeout: HTTP request timeout in seconds (default: 60)

    Returns:
        Raw response body as string.

    Raises:
        SystemExit on HTTP or connection errors.
    """
    sql = normalize_sql(sql)

    cfg = _cfg()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from htan_portal_config import get_clickhouse_url

    params = {"default_format": fmt}
    if database is not None:
        params["database"] = database

    url = get_clickhouse_url(cfg) + "?" + urllib.parse.urlencode(params)

    # Basic auth header
    credentials = base64.b64encode(f"{cfg['user']}:{cfg['password']}".encode()).decode()

    req = urllib.request.Request(
        url,
        data=sql.encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
        },
        method="POST",
    )

    # Create SSL context for HTTPS
    # On macOS with python.org Python, the default cert store may be empty.
    # Try certifi first (if installed), then fall back to default context.
    ctx = None
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        # Try to extract a cleaner error message from ClickHouse JSON error response
        clean_msg = error_body[:500]
        if error_body.startswith("{"):
            try:
                err_json = json.loads(error_body)
                clean_msg = err_json.get("exception", clean_msg)
            except (json.JSONDecodeError, KeyError):
                pass
        print(f"Error: ClickHouse HTTP {e.code}: {clean_msg}", file=sys.stderr)
        # Provide actionable hints for common errors
        hints = []
        if "Unrecognized token" in clean_msg and "!=" in clean_msg:
            hints.append("Hint: Use <> instead of != for not-equal comparisons in ClickHouse")
        if "UNKNOWN_IDENTIFIER" in clean_msg or "Missing columns" in clean_msg:
            hints.append("Hint: Run 'describe <table>' to see available column names")
        if "CANNOT_PARSE_TEXT" in clean_msg or "CANNOT_PARSE_INPUT" in clean_msg:
            hints.append("Hint: Use toInt32OrNull() or toFloat64OrNull() for columns with non-numeric values (e.g., DaystoBirth, AgeatDiagnosis)")
        if "Array" in clean_msg and ("ILLEGAL_TYPE" in clean_msg or "argument of function" in clean_msg):
            hints.append("Hint: Use arrayExists() or arrayJoin() for Array(String) columns like organType, Gender, Race, PrimaryDiagnosis")
        for hint in hints:
            print(hint, file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to HTAN portal ClickHouse: {e.reason}", file=sys.stderr)
        print("The portal endpoint may be temporarily unavailable.", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print(f"Error: Query timed out after {timeout}s. Try a simpler query or add a LIMIT clause.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def parse_json_rows(response_text):
    """Parse JSONEachRow response into a list of dicts.

    If any lines fail to parse as JSON, they are collected and reported to stderr.
    This surfaces ClickHouse error messages that arrive as non-JSON text in a 200 response.
    """
    if not response_text or not response_text.strip():
        return []

    rows = []
    error_lines = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            error_lines.append(line)

    # If we got no valid rows but did get non-JSON text, it's likely a ClickHouse error
    if not rows and error_lines:
        error_text = "\n".join(error_lines[:5])  # Show first 5 lines
        print(f"Error: ClickHouse returned non-JSON response:\n{error_text}", file=sys.stderr)
        sys.exit(1)

    # If we got some rows but also some error lines, warn but continue
    if error_lines:
        print(f"Warning: {len(error_lines)} non-JSON line(s) in response (possible partial error)", file=sys.stderr)

    return rows


def _format_cell_value(val):
    """Format a cell value for text table display.

    Lists/arrays are joined with ', ' instead of using Python repr (which
    produces brackets and quotes). Other values are converted via str().
    """
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)


def format_text_table(rows):
    """Format rows as an aligned text table."""
    if not rows:
        return ""

    columns = list(rows[0].keys())

    # Pre-format all cell values (join arrays before measuring widths)
    formatted = []
    for row in rows:
        formatted.append({col: _format_cell_value(row.get(col, "")) for col in columns})

    # Compute column widths
    widths = {}
    for col in columns:
        widths[col] = max(
            len(col),
            max((len(frow[col]) for frow in formatted), default=0),
        )

    # Adaptive cap: use terminal width if available, otherwise generous default.
    # With many columns, use a tighter cap to keep rows readable.
    try:
        term_width = os.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        term_width = 200

    if len(columns) <= 3:
        max_col_width = max(term_width // 2, 80)
    elif len(columns) <= 6:
        max_col_width = max(term_width // len(columns), 40)
    else:
        max_col_width = max(term_width // len(columns), 20)

    truncated = False
    for col in columns:
        if widths[col] > max_col_width:
            widths[col] = max_col_width
            truncated = True

    # Header
    header = "  ".join(f"{col:<{widths[col]}}" for col in columns)
    sep = "  ".join("-" * widths[col] for col in columns)

    lines = [header, sep]
    for frow in formatted:
        parts = []
        for col in columns:
            val = frow[col]
            if len(val) > widths[col]:
                val = val[: widths[col] - 3] + "..."
                truncated = True
            parts.append(f"{val:<{widths[col]}}")
        lines.append("  ".join(parts))

    if truncated:
        print("Hint: Some values were truncated. Use --output json for full values.", file=sys.stderr)

    return "\n".join(lines)


def format_output(rows, output_format="text"):
    """Format rows in the requested output format."""
    if not rows:
        print("No results.", file=sys.stderr)
        return

    if output_format == "json":
        print(json.dumps(rows, indent=2))
    elif output_format == "csv":
        if rows:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys(), quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            writer.writerows(rows)
            print(output.getvalue(), end="")
    else:
        print(format_text_table(rows))


# Columns that are Array(String) in the files table — need arrayExists() instead of ILIKE.
# Only applies to the files table; clinical tables use plain String for the same column names.
FILES_ARRAY_COLUMNS = {
    "organType", "Gender", "Ethnicity", "Race", "VitalStatus",
    "TreatmentType", "PrimaryDiagnosis", "TissueorOrganofOrigin",
    "biospecimenIds", "publicationIds", "diagnosisIds", "demographicsIds", "therapyIds",
}


def build_where_clauses(filters, array_columns=None):
    """Build WHERE clause fragments from a dict of {column: value} filters.

    Args:
        filters: Dict mapping column names to filter values. None values are skipped.
        array_columns: Set of column names that are Array(String) and need arrayExists().
            If None, all columns are treated as plain String.

    Returns:
        List of SQL condition strings.
    """
    if array_columns is None:
        array_columns = set()
    clauses = []
    for col, val in filters.items():
        if val is not None:
            escaped = escape_sql_string(val)
            if col in array_columns:
                clauses.append(f"arrayExists(x -> x ILIKE '%{escaped}%', {col})")
            else:
                clauses.append(f"{col} ILIKE '%{escaped}%'")
    return clauses


# --- Subcommand handlers ---


def cmd_files(args):
    """Query the files table with optional filters."""
    columns = [
        "DataFileID",
        "Filename",
        "FileFormat",
        "assayName",
        "level",
        "organType",
        "atlas_name",
        "synapseId",
        "JSONExtractString(viewers, 'crdcGc', 'drs_uri') as drs_uri",
        "downloadSource",
    ]

    filters = {
        "organType": args.organ,
        "assayName": args.assay,
        "atlas_name": args.atlas,
        "level": args.level,
        "FileFormat": args.file_format,
        "Filename": args.filename,
    }

    where = build_where_clauses(filters, array_columns=FILES_ARRAY_COLUMNS)

    # DataFileID exact match (not ILIKE)
    if args.data_file_id:
        ids = [args.data_file_id] if isinstance(args.data_file_id, str) else args.data_file_id
        escaped_ids = ", ".join(f"'{escape_sql_string(fid)}'" for fid in ids)
        where.append(f"DataFileID IN ({escaped_ids})")

    sql = f"SELECT {', '.join(columns)} FROM files"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f"\nLIMIT {args.limit}"

    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        return

    print(f"Querying files in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)
    print(f"Returned {len(rows)} rows", file=sys.stderr)
    format_output(rows, args.output)


def cmd_demographics(args):
    """Query the demographics table."""
    filters = {
        "atlas_name": args.atlas,
        "Gender": args.gender,
        "Race": args.race,
    }

    where = build_where_clauses(filters)

    sql = "SELECT * FROM demographics"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f"\nLIMIT {args.limit}"

    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        return

    print(f"Querying demographics in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)
    print(f"Returned {len(rows)} rows", file=sys.stderr)
    format_output(rows, args.output)


def cmd_diagnosis(args):
    """Query the diagnosis table."""
    filters = {
        "atlas_name": args.atlas,
        "TissueorOrganofOrigin": args.organ,
        "PrimaryDiagnosis": args.primary_diagnosis,
    }

    where = build_where_clauses(filters)

    sql = "SELECT * FROM diagnosis"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f"\nLIMIT {args.limit}"

    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        return

    print(f"Querying diagnosis in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)
    print(f"Returned {len(rows)} rows", file=sys.stderr)
    format_output(rows, args.output)


def cmd_cases(args):
    """Query the cases table (merged demographics + diagnosis)."""
    filters = {
        "atlas_name": args.atlas,
        "TissueorOrganofOrigin": args.organ,
    }

    where = build_where_clauses(filters)

    sql = "SELECT * FROM cases"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f"\nLIMIT {args.limit}"

    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        return

    print(f"Querying cases in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)
    print(f"Returned {len(rows)} rows", file=sys.stderr)
    format_output(rows, args.output)


def cmd_specimen(args):
    """Query the specimen table."""
    filters = {
        "atlas_name": args.atlas,
        "PreservationMethod": args.preservation,
        "TumorTissueType": args.tissue_type,
    }

    where = build_where_clauses(filters)

    sql = "SELECT * FROM specimen"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f"\nLIMIT {args.limit}"

    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        return

    print(f"Querying specimen in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)
    print(f"Returned {len(rows)} rows", file=sys.stderr)
    format_output(rows, args.output)


def cmd_sql(args):
    """Execute a direct SQL query against ClickHouse."""
    sql = args.sql

    safe, reason = validate_sql_safety(sql)
    if not safe:
        print(f"Error: {reason}", file=sys.stderr)
        print("Only read-only queries (SELECT, WITH, SHOW, DESCRIBE) are allowed.", file=sys.stderr)
        sys.exit(1)

    no_limit = getattr(args, "no_limit", False)
    limit = args.limit if hasattr(args, "limit") else SQL_DEFAULT_LIMIT
    if not no_limit:
        sql = ensure_limit(sql, limit)

    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        return

    print(f"Executing query in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)
    print(f"Returned {len(rows)} rows", file=sys.stderr)

    # Warn if result count matches the applied limit (may be truncated)
    if not no_limit and len(rows) == limit:
        print(f"Warning: Result count ({len(rows)}) matches the applied limit. "
              f"There may be more rows — use --no-limit or a higher --limit.", file=sys.stderr)

    format_output(rows, args.output)


def cmd_tables(args):
    """List available tables in the HTAN ClickHouse database."""
    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print("SQL: SHOW TABLES", file=sys.stderr)
        return

    print(f"Listing tables in {database}...", file=sys.stderr)
    resp = clickhouse_query("SHOW TABLES", fmt="TabSeparated", database=database)

    tables = [line.strip() for line in resp.strip().split("\n") if line.strip()]
    for t in sorted(tables):
        print(t)
    print(f"\n{len(tables)} tables", file=sys.stderr)


def cmd_describe(args):
    """Describe the schema of a table."""
    table_name = validate_table_name(args.table_name)
    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL: DESCRIBE {table_name}", file=sys.stderr)
        return

    print(f"Describing {table_name} in {database}...", file=sys.stderr)
    resp = clickhouse_query(f"DESCRIBE {table_name}", fmt="JSONEachRow", database=database)
    rows = parse_json_rows(resp)

    if not rows:
        print(f"No schema found for table '{table_name}'.", file=sys.stderr)
        sys.exit(1)

    # Also get row count
    count_resp = clickhouse_query(f"SELECT count() as cnt FROM {table_name}", database=database)
    count_rows = parse_json_rows(count_resp)
    row_count = count_rows[0].get("cnt", "?") if count_rows else "?"

    print(f"Table: {database}.{table_name}")
    print(f"Rows: {row_count:,}" if isinstance(row_count, int) else f"Rows: {row_count}")
    print()

    # Format schema as table
    print(f"{'Column':<40} {'Type':<30} {'Default':<15} {'Comment'}")
    print(f"{'-'*40} {'-'*30} {'-'*15} {'-'*30}")
    for row in rows:
        name = row.get("name", "")
        dtype = row.get("type", "")
        default = row.get("default_expression", "") or ""
        comment = row.get("comment", "") or ""
        if len(comment) > 40:
            comment = comment[:37] + "..."
        print(f"{name:<40} {dtype:<30} {default:<15} {comment}")

    print(f"\n{len(rows)} columns", file=sys.stderr)


def cmd_summary(args):
    """Show a summary of HTAN portal data: file/participant counts by atlas, assay, and organ."""
    database = args.database or discover_database()

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print("Would run summary aggregation queries against: files, demographics", file=sys.stderr)
        return

    print(f"Querying summary from {database}...", file=sys.stderr)

    queries = {
        "Files by atlas": "SELECT atlas_name, count() as file_count FROM files GROUP BY atlas_name ORDER BY file_count DESC",
        "Files by assay": "SELECT assayName, count() as file_count FROM files GROUP BY assayName ORDER BY file_count DESC",
        "Files by organ": "SELECT arrayJoin(organType) as organ, count() as file_count FROM files GROUP BY organ ORDER BY file_count DESC",
        "Participants by atlas": "SELECT atlas_name, count() as participant_count FROM demographics GROUP BY atlas_name ORDER BY participant_count DESC",
        "Total files": "SELECT count() as total FROM files",
        "Total participants": "SELECT count() as total FROM demographics",
    }

    results = {}
    for label, sql in queries.items():
        try:
            resp = clickhouse_query(sql, database=database)
            results[label] = parse_json_rows(resp)
        except SystemExit:
            results[label] = []

    # Format output
    if args.output == "json":
        print(json.dumps(results, indent=2))
        return

    total_files = results.get("Total files", [{}])[0].get("total", "?")
    total_participants = results.get("Total participants", [{}])[0].get("total", "?")
    print(f"HTAN Portal Summary (database: {database})")
    print(f"Total files: {total_files:,}" if isinstance(total_files, int) else f"Total files: {total_files}")
    print(f"Total participants: {total_participants:,}" if isinstance(total_participants, int) else f"Total participants: {total_participants}")
    print()

    for label in ["Files by atlas", "Files by assay", "Files by organ", "Participants by atlas"]:
        rows = results.get(label, [])
        if not rows:
            continue
        print(f"--- {label} ---")
        print(format_text_table(rows))
        print()


def cmd_manifest(args):
    """Generate download manifests from HTAN_Data_File_IDs.

    Queries ClickHouse for file download coordinates and generates:
    - synapse_manifest.tsv for Synapse files (synapseclient)
    - gen3_manifest.json for Gen3/CRDC files (gen3-client)
    """
    # Collect file IDs
    file_ids = list(args.ids) if args.ids else []

    if args.file:
        try:
            with open(args.file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        file_ids.append(line)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

    if not file_ids:
        print("Error: No file IDs provided. Pass IDs as arguments or use --file.", file=sys.stderr)
        sys.exit(1)

    database = args.database or discover_database()

    # Query ClickHouse for download coordinates
    escaped_ids = ", ".join(f"'{escape_sql_string(fid)}'" for fid in file_ids)
    sql = f"""SELECT DataFileID, Filename, synapseId,
       JSONExtractString(viewers, 'crdcGc', 'drs_uri') as drs_uri,
       downloadSource
FROM files
WHERE DataFileID IN ({escaped_ids})"""

    if args.dry_run:
        print(f"Database: {database}", file=sys.stderr)
        print(f"SQL:\n{sql}", file=sys.stderr)
        print(f"Would generate manifests in: {args.output_dir}", file=sys.stderr)
        return

    print(f"Looking up {len(file_ids)} file(s) in {database}...", file=sys.stderr)
    resp = clickhouse_query(sql, database=database)
    rows = parse_json_rows(resp)

    if not rows:
        print("No matching files found in the portal database.", file=sys.stderr)
        sys.exit(1)

    found_ids = {r["DataFileID"] for r in rows}
    not_found = [fid for fid in file_ids if fid not in found_ids]
    if not_found:
        print(f"Not found ({len(not_found)}): {', '.join(not_found)}", file=sys.stderr)

    print(f"Found {len(rows)}/{len(file_ids)} files", file=sys.stderr)

    # Separate into Synapse and Gen3 files
    synapse_files = [r for r in rows if r.get("synapseId")]
    gen3_files = [r for r in rows if r.get("drs_uri")]

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    files_written = []

    # Generate Synapse manifest (TSV)
    if synapse_files:
        manifest_path = os.path.join(output_dir, "synapse_manifest.tsv")
        with open(manifest_path, "w") as f:
            f.write("synapseId\tDataFileID\tFilename\n")
            for row in synapse_files:
                syn_id = row.get("synapseId", "")
                data_id = row.get("DataFileID", "")
                filename = row.get("Filename", "")
                f.write(f"{syn_id}\t{data_id}\t{filename}\n")
        print(f"Synapse manifest: {manifest_path} ({len(synapse_files)} files)", file=sys.stderr)
        files_written.append(manifest_path)

    # Generate Gen3 manifest (JSON)
    if gen3_files:
        manifest_path = os.path.join(output_dir, "gen3_manifest.json")
        manifest = []
        for row in gen3_files:
            drs = row.get("drs_uri", "")
            if not drs.startswith("drs://"):
                drs = f"drs://{drs}"
            manifest.append({
                "object_id": drs,
                "DataFileID": row.get("DataFileID", ""),
                "Filename": row.get("Filename", ""),
            })
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Gen3 manifest: {manifest_path} ({len(gen3_files)} files)", file=sys.stderr)
        files_written.append(manifest_path)

    # Summary to stdout
    print(json.dumps({
        "total_files": len(rows),
        "synapse_files": len(synapse_files),
        "gen3_files": len(gen3_files),
        "not_found": not_found,
        "manifests": files_written,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Query HTAN data via the portal ClickHouse backend",
        epilog="Examples:\n"
        "  python3 scripts/htan_portal.py tables\n"
        "  python3 scripts/htan_portal.py describe files\n"
        '  python3 scripts/htan_portal.py files --organ Breast --assay "scRNA-seq" --limit 5\n'
        "  python3 scripts/htan_portal.py files --data-file-id HTA9_1_19512 --output json\n"
        '  python3 scripts/htan_portal.py sql "SELECT atlas_name, COUNT(*) as n FROM files GROUP BY atlas_name"\n'
        "  python3 scripts/htan_portal.py manifest HTA9_1_19512 --output-dir /tmp/manifests\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Common arguments helper ---
    def add_common_args(sp, include_limit=True):
        if include_limit:
            sp.add_argument("--limit", "-l", type=int, default=DEFAULT_LIMIT, help=f"Row limit (default: {DEFAULT_LIMIT})")
        sp.add_argument("--output", "-o", choices=["text", "json", "csv"], default="text", help="Output format")
        sp.add_argument("--dry-run", action="store_true", help="Show SQL without executing")
        sp.add_argument("--database", "-d", help="Database name (default: auto-discover)")

    # files subcommand
    sp_files = subparsers.add_parser("files", help="Query files with filters (organ, assay, atlas, level)")
    sp_files.add_argument("--organ", help="Filter by organ type (e.g., Breast, Colon, Lung)")
    sp_files.add_argument("--assay", help="Filter by assay name (e.g., scRNA-seq, CyCIF, CODEX)")
    sp_files.add_argument("--atlas", help="Filter by atlas name (e.g., HTAN HMS, HTAN WUSTL)")
    sp_files.add_argument("--level", help="Filter by data level (e.g., Level 1, Level 3)")
    sp_files.add_argument("--file-format", help="Filter by file format (e.g., fastq, bam, h5ad)")
    sp_files.add_argument("--filename", help="Filter by filename (substring match)")
    sp_files.add_argument("--data-file-id", nargs="+", help="Look up specific HTAN_Data_File_ID(s)")
    add_common_args(sp_files)

    # demographics subcommand
    sp_demo = subparsers.add_parser("demographics", help="Query patient demographics")
    sp_demo.add_argument("--atlas", help="Filter by atlas name")
    sp_demo.add_argument("--gender", help="Filter by gender (e.g., male, female)")
    sp_demo.add_argument("--race", help="Filter by race")
    add_common_args(sp_demo)

    # diagnosis subcommand
    sp_diag = subparsers.add_parser("diagnosis", help="Query diagnosis information")
    sp_diag.add_argument("--atlas", help="Filter by atlas name")
    sp_diag.add_argument("--organ", help="Filter by tissue/organ of origin")
    sp_diag.add_argument("--primary-diagnosis", help="Filter by primary diagnosis")
    add_common_args(sp_diag)

    # cases subcommand
    sp_cases = subparsers.add_parser("cases", help="Query merged cases (demographics + diagnosis)")
    sp_cases.add_argument("--atlas", help="Filter by atlas name")
    sp_cases.add_argument("--organ", help="Filter by tissue/organ of origin")
    add_common_args(sp_cases)

    # specimen subcommand
    sp_spec = subparsers.add_parser("specimen", help="Query biospecimen metadata")
    sp_spec.add_argument("--atlas", help="Filter by atlas name")
    sp_spec.add_argument("--preservation", help="Filter by preservation method (e.g., FFPE, Fresh Frozen)")
    sp_spec.add_argument("--tissue-type", help="Filter by tumor tissue type (e.g., Tumor, Normal)")
    add_common_args(sp_spec)

    # summary subcommand
    sp_summary = subparsers.add_parser("summary", help="Show summary of HTAN data (file/participant counts by atlas, assay, organ)")
    sp_summary.add_argument("--output", "-o", choices=["text", "json"], default="text", help="Output format")
    sp_summary.add_argument("--dry-run", action="store_true", help="Show what would be queried")
    sp_summary.add_argument("--database", "-d", help="Database name")

    # sql subcommand
    sp_sql = subparsers.add_parser("sql", help="Execute a direct read-only SQL query")
    sp_sql.add_argument("sql", help="SQL query to execute")
    sp_sql.add_argument("--limit", "-l", type=int, default=SQL_DEFAULT_LIMIT, help=f"Row limit (default: {SQL_DEFAULT_LIMIT})")
    sp_sql.add_argument("--no-limit", action="store_true", help="Skip auto-applying LIMIT clause")
    sp_sql.add_argument("--output", "-o", choices=["text", "json", "csv"], default="text", help="Output format")
    sp_sql.add_argument("--dry-run", action="store_true", help="Show SQL without executing")
    sp_sql.add_argument("--database", "-d", help="Database name (default: auto-discover)")

    # tables subcommand
    sp_tables = subparsers.add_parser("tables", help="List available tables")
    sp_tables.add_argument("--dry-run", action="store_true", help="Show what would be queried")
    sp_tables.add_argument("--database", "-d", help="Database name")

    # describe subcommand
    sp_desc = subparsers.add_parser("describe", help="Describe table schema")
    sp_desc.add_argument("table_name", help="Table name (e.g., files, demographics, diagnosis)")
    sp_desc.add_argument("--dry-run", action="store_true", help="Show what would be queried")
    sp_desc.add_argument("--database", "-d", help="Database name")

    # manifest subcommand
    sp_manifest = subparsers.add_parser("manifest", help="Generate Synapse/Gen3 download manifests from file IDs")
    sp_manifest.add_argument("ids", nargs="*", help="One or more HTAN_Data_File_IDs")
    sp_manifest.add_argument("--file", "-f", help="File containing IDs (one per line)")
    sp_manifest.add_argument("--output-dir", default=".", help="Directory to write manifest files (default: current dir)")
    sp_manifest.add_argument("--dry-run", action="store_true", help="Show SQL without executing")
    sp_manifest.add_argument("--database", "-d", help="Database name")

    args = parser.parse_args()
    func = {
        "files": cmd_files,
        "demographics": cmd_demographics,
        "diagnosis": cmd_diagnosis,
        "cases": cmd_cases,
        "specimen": cmd_specimen,
        "summary": cmd_summary,
        "sql": cmd_sql,
        "tables": cmd_tables,
        "describe": cmd_describe,
        "manifest": cmd_manifest,
    }[args.command]
    func(args)


if __name__ == "__main__":
    main()
