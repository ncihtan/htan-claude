#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.0",
# ]
# ///
"""HTAN Portal MCP Server.

Runs on the host machine via stdio transport. Loads credentials using 3-tier
resolution: env var > OS keychain > config file. Auto-downloads credentials
from Synapse via stdlib HTTP if missing but Synapse auth is configured.

Exposes HTAN portal ClickHouse queries as MCP tools for Cowork compatibility.
The existing skill + scripts architecture is preserved for Claude Code users;
this server is an additive layer.

Usage:
    uv run servers/htan_portal_server.py
"""

import json
import logging
import os
import shutil
import sys

from mcp.server.fastmcp import FastMCP

# --- Path setup: import shared modules from skills/htan/scripts/ ---
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SERVER_DIR)
SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, "skills", "htan", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

# Import reusable functions from existing scripts (refactored to raise exceptions)
from htan_portal import (
    PortalError,
    clickhouse_query,
    parse_json_rows,
    discover_database as _portal_discover_database,
    normalize_sql,
    validate_sql_safety,
    escape_sql_string,
    build_where_clauses,
    ensure_limit,
    FILES_ARRAY_COLUMNS,
    TABLE_NAME_PATTERN,
)
from htan_portal_config import (
    CONFIG_PATH,
    REQUIRED_KEYS,
    load_portal_config,
    ConfigError as PortalConfigError,
    save_to_keychain,
)

logger = logging.getLogger("htan-portal-mcp")

# --- Constants ---
SYNAPSE_CONFIG_PATH = os.path.expanduser("~/.synapseConfig")
GEN3_CREDS_PATH = os.path.expanduser("~/.gen3/credentials.json")
BIGQUERY_ADC_PATH = os.path.expanduser(
    "~/.config/gcloud/application_default_credentials.json"
)
PORTAL_CREDENTIALS_SYNAPSE_ID = "syn73720854"
SYNAPSE_TEAM_ID = "3574960"


# --- Credential management ---

class CredentialError(Exception):
    """Credentials not available or auto-setup failed."""
    pass


_portal_cfg = None
_database = None


def _load_portal_config_safe():
    """Load portal config using 3-tier resolution. Returns dict or raises CredentialError."""
    try:
        return load_portal_config()
    except PortalConfigError as e:
        raise CredentialError(str(e))


def _auto_setup_portal():
    """Attempt to auto-download portal credentials from Synapse via stdlib HTTP.

    No synapseclient dependency. Uses Synapse REST API directly.
    Requires ~/.synapseConfig or SYNAPSE_AUTH_TOKEN to exist.
    Downloads from Synapse entity syn73720854 (gated behind Team:3574960 membership).
    """
    import configparser
    import ssl
    import urllib.error
    import urllib.request

    # Read Synapse auth token
    token = os.environ.get("SYNAPSE_AUTH_TOKEN", "").strip()
    if not token and os.path.exists(SYNAPSE_CONFIG_PATH):
        config = configparser.ConfigParser()
        config.read(SYNAPSE_CONFIG_PATH)
        token = (config.get("authentication", "authtoken", fallback=None) or "").strip()

    if not token:
        raise CredentialError(
            "Portal credentials not configured and no Synapse credentials found.\n"
            "Set up ~/.synapseConfig first:\n"
            "1. Create a free account at https://www.synapse.org\n"
            "2. Go to Account Settings > Personal Access Tokens\n"
            "3. Create a token with view and download permissions\n"
            "4. Save to ~/.synapseConfig:\n"
            "   [authentication]\n"
            "   authtoken = <your-token>"
        )

    def _ssl_ctx():
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def _synapse_get(path, endpoint="https://repo-prod.prod.sagebase.org"):
        req = urllib.request.Request(
            f"{endpoint}{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
            return json.loads(resp.read())

    def _synapse_post(path, body, endpoint="https://repo-prod.prod.sagebase.org"):
        req = urllib.request.Request(
            f"{endpoint}{path}",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
            return json.loads(resp.read())

    logger.info("Auto-setup: downloading portal credentials from Synapse (stdlib)...")

    # Check team membership and auto-join
    try:
        profile = _synapse_get("/repo/v1/userProfile")
        user_id = profile.get("ownerId", "")
        if user_id:
            membership = _synapse_get(
                f"/repo/v1/team/{SYNAPSE_TEAM_ID}/member/{user_id}/membershipStatus"
            )
            if not membership.get("isMember", False) and membership.get("canJoin", False):
                logger.info("Auto-joining HTAN Claude Skill Users team...")
                try:
                    _synapse_post("/repo/v1/membershipRequest", {
                        "teamId": SYNAPSE_TEAM_ID,
                        "message": "Auto-join via HTAN MCP server",
                    })
                except Exception as e:
                    logger.warning(f"Could not auto-join team: {e}")
            elif not membership.get("isMember", False):
                logger.warning("Not a team member. Join at: https://www.synapse.org/Team:3574960")
    except Exception as e:
        logger.warning(f"Could not check team membership: {e}")

    # Get entity bundle -> file handle ID
    try:
        bundle = _synapse_post(
            f"/repo/v1/entity/{PORTAL_CREDENTIALS_SYNAPSE_ID}/bundle2",
            {"includeEntity": True, "includeFileHandles": True},
        )
        fh_id = bundle["entity"]["dataFileHandleId"]
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise CredentialError(
                "Access denied. Join the HTAN Claude Skill Users team first: "
                "https://www.synapse.org/Team:3574960"
            )
        raise CredentialError(f"Failed to get entity bundle: {e}")
    except Exception as e:
        raise CredentialError(f"Failed to get entity bundle: {e}")

    # Get pre-signed download URL
    try:
        download_url = _synapse_get(
            f"/file/v1/fileHandle/{fh_id}/url?redirect=false",
            endpoint="https://file-prod.prod.sagebase.org",
        )
        if not isinstance(download_url, str):
            download_url = str(download_url)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise CredentialError(
                "Access denied. Join the HTAN Claude Skill Users team first: "
                "https://www.synapse.org/Team:3574960"
            )
        raise CredentialError(f"Failed to get download URL: {e}")

    # Download credentials
    try:
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
            creds = json.loads(resp.read())
    except Exception as e:
        raise CredentialError(f"Failed to download portal credentials: {e}")

    # Validate
    missing = [k for k in REQUIRED_KEYS if k not in creds]
    if missing:
        raise CredentialError(f"Downloaded credentials missing keys: {', '.join(missing)}")

    # Store in keychain + config file
    try:
        save_to_keychain(creds)
    except Exception:
        pass

    config_dir = os.path.dirname(CONFIG_PATH)
    os.makedirs(config_dir, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")
    os.chmod(CONFIG_PATH, 0o600)

    logger.info(f"Portal credentials saved to {CONFIG_PATH}")
    return creds


def _ensure_portal_config():
    """Get portal config, auto-setting up if needed. Returns config dict."""
    global _portal_cfg
    if _portal_cfg is not None:
        return _portal_cfg

    try:
        _portal_cfg = _load_portal_config_safe()
    except CredentialError:
        # Try auto-setup
        _portal_cfg = _auto_setup_portal()

    return _portal_cfg


def _get_database():
    """Get the current HTAN database name (cached)."""
    global _database
    if _database is not None:
        return _database
    cfg = _ensure_portal_config()
    _database = _portal_discover_database(config=cfg)
    return _database


def _query(sql, fmt="JSONEachRow", database=None, timeout=60):
    """Execute a ClickHouse query using the server's credential management."""
    cfg = _ensure_portal_config()
    db = database if database is not None else _get_database()
    return clickhouse_query(sql, fmt=fmt, database=db, config=cfg, timeout=timeout)


def _error_response(e):
    """Format an exception as a JSON error response for MCP tools."""
    result = {"error": str(e)}
    if hasattr(e, "hints") and e.hints:
        result["hints"] = e.hints
    return json.dumps(result)


# --- MCP Server ---

server = FastMCP(
    "htan-portal",
    instructions=(
        "HTAN portal ClickHouse query server. Provides tools to search HTAN "
        "(Human Tumor Atlas Network) files, query clinical data, and explore "
        "the portal database schema."
    ),
)


@server.tool()
def htan_portal_query(sql: str, limit: int = 1000) -> str:
    """Run a read-only SQL query against the HTAN portal ClickHouse database.

    The database contains HTAN file metadata, clinical data, and download coordinates.
    Only SELECT, WITH, SHOW, DESCRIBE, and EXPLAIN queries are allowed.
    Write operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked.

    Key tables: files, demographics, diagnosis, cases, specimen, atlases,
    publication_manifest.

    Array columns in the files table (organType, Gender, Race, etc.) require
    arrayExists() for filtering. Use <> instead of != for not-equal comparisons.

    Args:
        sql: SQL query to execute (read-only)
        limit: Maximum rows to return (default 1000, auto-applied if no LIMIT clause)
    """
    try:
        safe, reason = validate_sql_safety(sql)
        if not safe:
            return json.dumps({"error": reason, "hint": "Only read-only queries are allowed."})

        sql = ensure_limit(sql, limit)
        database = _get_database()
        resp = _query(sql, database=database)
        rows = parse_json_rows(resp)
        return json.dumps({"database": database, "row_count": len(rows), "rows": rows})
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_portal_files(
    organ: str = "",
    assay: str = "",
    atlas: str = "",
    level: str = "",
    data_file_id: str = "",
    limit: int = 100,
) -> str:
    """Search for HTAN data files with optional filters.

    Returns file metadata including DataFileID, Filename, FileFormat, assay,
    level, organ, atlas, synapseId (for open-access download), and drs_uri
    (for controlled-access download).

    Args:
        organ: Filter by organ type (e.g., "Breast", "Colon", "Lung")
        assay: Filter by assay name (e.g., "scRNA-seq", "CyCIF", "CODEX")
        atlas: Filter by atlas name (e.g., "HTAN HMS", "HTAN WUSTL")
        level: Filter by data level (e.g., "Level 1", "Level 3")
        data_file_id: Exact match on HTAN_Data_File_ID (comma-separated for multiple)
        limit: Maximum rows to return (default 100)
    """
    try:
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

        filters = {}
        if organ:
            filters["organType"] = organ
        if assay:
            filters["assayName"] = assay
        if atlas:
            filters["atlas_name"] = atlas
        if level:
            filters["level"] = level

        where = build_where_clauses(filters, array_columns=FILES_ARRAY_COLUMNS)

        if data_file_id:
            ids = [fid.strip() for fid in data_file_id.split(",") if fid.strip()]
            escaped_ids = ", ".join(f"'{escape_sql_string(fid)}'" for fid in ids)
            where.append(f"DataFileID IN ({escaped_ids})")

        sql = f"SELECT {', '.join(columns)} FROM files"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f"\nLIMIT {limit}"

        database = _get_database()
        resp = _query(sql, database=database)
        rows = parse_json_rows(resp)
        return json.dumps({"database": database, "row_count": len(rows), "rows": rows})
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_portal_summary() -> str:
    """Get an overview of HTAN data: file and participant counts by atlas, assay, and organ.

    Returns summary statistics from the portal database including total files,
    total participants, and breakdowns by atlas center, assay type, and organ.
    """
    try:
        database = _get_database()
        queries = {
            "files_by_atlas": (
                "SELECT atlas_name, count() as file_count FROM files "
                "GROUP BY atlas_name ORDER BY file_count DESC"
            ),
            "files_by_assay": (
                "SELECT assayName, count() as file_count FROM files "
                "GROUP BY assayName ORDER BY file_count DESC"
            ),
            "files_by_organ": (
                "SELECT arrayJoin(organType) as organ, count() as file_count FROM files "
                "GROUP BY organ ORDER BY file_count DESC"
            ),
            "participants_by_atlas": (
                "SELECT atlas_name, count() as participant_count FROM demographics "
                "GROUP BY atlas_name ORDER BY participant_count DESC"
            ),
            "total_files": "SELECT count() as total FROM files",
            "total_participants": "SELECT count() as total FROM demographics",
        }

        results = {}
        for label, sql in queries.items():
            try:
                resp = _query(sql, database=database)
                results[label] = parse_json_rows(resp)
            except PortalError:
                results[label] = []

        total_files = results.get("total_files", [{}])
        total_participants = results.get("total_participants", [{}])

        return json.dumps({
            "database": database,
            "total_files": total_files[0].get("total", 0) if total_files else 0,
            "total_participants": total_participants[0].get("total", 0) if total_participants else 0,
            "files_by_atlas": results.get("files_by_atlas", []),
            "files_by_assay": results.get("files_by_assay", []),
            "files_by_organ": results.get("files_by_organ", []),
            "participants_by_atlas": results.get("participants_by_atlas", []),
        })
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_portal_tables() -> str:
    """List all available tables in the HTAN portal ClickHouse database.

    Returns table names from the current HTAN database.
    Key tables: files, demographics, diagnosis, cases, specimen, atlases,
    publication_manifest.
    """
    try:
        database = _get_database()
        resp = _query("SHOW TABLES", fmt="TabSeparated", database=database)
        tables = sorted([line.strip() for line in resp.strip().split("\n") if line.strip()])
        return json.dumps({"database": database, "tables": tables, "count": len(tables)})
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_portal_describe(table: str) -> str:
    """Describe the schema of a portal ClickHouse table.

    Returns column names, types, and row count for the specified table.

    Args:
        table: Table name (e.g., "files", "demographics", "diagnosis", "cases", "specimen")
    """
    try:
        if not TABLE_NAME_PATTERN.match(table):
            return json.dumps({
                "error": f"Invalid table name '{table}'. Use only alphanumeric and underscores."
            })

        database = _get_database()
        resp = _query(f"DESCRIBE {table}", fmt="JSONEachRow", database=database)
        schema = parse_json_rows(resp)

        if not schema:
            return json.dumps({"error": f"No schema found for table '{table}'"})

        # Get row count
        row_count = None
        try:
            count_resp = _query(f"SELECT count() as cnt FROM {table}", database=database)
            count_rows = parse_json_rows(count_resp)
            row_count = count_rows[0].get("cnt") if count_rows else None
        except PortalError:
            pass

        columns = [
            {
                "name": row.get("name", ""),
                "type": row.get("type", ""),
                "default_expression": row.get("default_expression", ""),
                "comment": row.get("comment", ""),
            }
            for row in schema
        ]

        return json.dumps({
            "database": database,
            "table": table,
            "row_count": row_count,
            "columns": columns,
            "column_count": len(columns),
        })
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_portal_clinical(
    table: str,
    organ: str = "",
    atlas: str = "",
    limit: int = 100,
) -> str:
    """Query clinical data from the HTAN portal (demographics, diagnosis, cases, specimen).

    Args:
        table: Clinical table — one of: "demographics", "diagnosis", "cases", "specimen"
        organ: Filter by organ/tissue (applies to diagnosis, cases, specimen)
        atlas: Filter by atlas name (e.g., "HTAN HMS", "HTAN OHSU")
        limit: Maximum rows to return (default 100)
    """
    try:
        valid_tables = {"demographics", "diagnosis", "cases", "specimen"}
        if table not in valid_tables:
            return json.dumps({
                "error": f"Invalid table '{table}'. Must be one of: {', '.join(sorted(valid_tables))}"
            })

        filters = {}
        if atlas:
            filters["atlas_name"] = atlas
        if organ:
            if table in ("diagnosis", "cases"):
                filters["TissueorOrganofOrigin"] = organ
            elif table == "specimen":
                filters["TissueorOrganofOrigin"] = organ

        where = build_where_clauses(filters)

        sql = f"SELECT * FROM {table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f"\nLIMIT {limit}"

        database = _get_database()
        resp = _query(sql, database=database)
        rows = parse_json_rows(resp)
        return json.dumps({
            "database": database,
            "table": table,
            "row_count": len(rows),
            "rows": rows,
        })
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_portal_manifest(file_ids: list[str]) -> str:
    """Generate download manifest data for given HTAN Data File IDs.

    Looks up files in the portal database and returns Synapse IDs and DRS URIs
    for downloading via Synapse (open access) or Gen3/CRDC (controlled access).

    Args:
        file_ids: List of HTAN_Data_File_IDs (e.g., ["HTA9_1_19512", "HTA9_1_19553"])
    """
    try:
        if not file_ids:
            return json.dumps({"error": "No file IDs provided."})

        database = _get_database()
        escaped_ids = ", ".join(f"'{escape_sql_string(fid)}'" for fid in file_ids)
        sql = (
            "SELECT DataFileID, Filename, synapseId, "
            "JSONExtractString(viewers, 'crdcGc', 'drs_uri') as drs_uri, "
            "downloadSource "
            "FROM files "
            f"WHERE DataFileID IN ({escaped_ids})"
        )

        resp = _query(sql, database=database)
        rows = parse_json_rows(resp)

        found_ids = {r["DataFileID"] for r in rows}
        not_found = [fid for fid in file_ids if fid not in found_ids]

        synapse_files = [r for r in rows if r.get("synapseId")]
        gen3_files = [r for r in rows if r.get("drs_uri")]

        return json.dumps({
            "database": database,
            "total_found": len(rows),
            "total_requested": len(file_ids),
            "not_found": not_found,
            "synapse_files": [
                {
                    "DataFileID": r["DataFileID"],
                    "Filename": r.get("Filename", ""),
                    "synapseId": r["synapseId"],
                }
                for r in synapse_files
            ],
            "gen3_files": [
                {
                    "DataFileID": r["DataFileID"],
                    "Filename": r.get("Filename", ""),
                    "drs_uri": r["drs_uri"],
                }
                for r in gen3_files
            ],
        })
    except (PortalError, CredentialError) as e:
        return _error_response(e)


@server.tool()
def htan_setup_status() -> str:
    """Check the status of HTAN credential configuration on the host machine.

    Reports whether each service (Synapse, portal, Gen3, BigQuery) is configured,
    along with Python version and uv availability.
    """
    status = {}

    # Synapse
    has_synapse_env = bool(os.environ.get("SYNAPSE_AUTH_TOKEN"))
    has_synapse_config = os.path.exists(SYNAPSE_CONFIG_PATH)
    status["synapse"] = {
        "configured": has_synapse_env or has_synapse_config,
        "method": (
            "SYNAPSE_AUTH_TOKEN"
            if has_synapse_env
            else ("~/.synapseConfig" if has_synapse_config else None)
        ),
    }

    # Portal
    has_portal = os.path.exists(CONFIG_PATH)
    portal_valid = False
    if has_portal:
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            portal_valid = all(k in cfg for k in REQUIRED_KEYS)
        except (json.JSONDecodeError, PermissionError):
            portal_valid = False
    status["portal"] = {
        "configured": has_portal and portal_valid,
        "path": CONFIG_PATH if has_portal else None,
    }

    # Gen3
    has_gen3_env = bool(
        os.environ.get("GEN3_API_KEY")
        and os.path.exists(os.environ.get("GEN3_API_KEY", ""))
    )
    has_gen3_config = os.path.exists(GEN3_CREDS_PATH)
    status["gen3"] = {
        "configured": has_gen3_env or has_gen3_config,
        "method": (
            "GEN3_API_KEY"
            if has_gen3_env
            else ("~/.gen3/credentials.json" if has_gen3_config else None)
        ),
    }

    # BigQuery
    has_bq_sa = bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        and os.path.exists(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""))
    )
    has_bq_adc = os.path.exists(BIGQUERY_ADC_PATH)
    status["bigquery"] = {
        "configured": has_bq_sa or has_bq_adc,
        "method": (
            "GOOGLE_APPLICATION_CREDENTIALS"
            if has_bq_sa
            else ("application_default_credentials" if has_bq_adc else None)
        ),
    }

    # uv
    uv_path = shutil.which("uv")
    status["uv"] = {"available": uv_path is not None, "path": uv_path}

    # Python
    v = sys.version_info
    status["python"] = {
        "version": f"{v.major}.{v.minor}.{v.micro}",
        "sufficient": v >= (3, 10),
    }

    return json.dumps({"ok": True, "status": status})


if __name__ == "__main__":
    server.run()
