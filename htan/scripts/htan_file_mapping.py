#!/usr/bin/env python3
"""HTAN file mapping: resolve HTAN_Data_File_ID to Synapse entityId and Gen3 DRS URI.

Downloads and caches the DRS mapping file from the HTAN portal, then provides
lookup by HTAN_Data_File_ID to get download coordinates for both platforms.

No extra dependencies — uses only stdlib (urllib, json).

Usage:
    python3 scripts/htan_file_mapping.py update
    python3 scripts/htan_file_mapping.py lookup HTA9_1_19512
    python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 HTA9_1_19553 --format json
    python3 scripts/htan_file_mapping.py lookup --file ids.txt
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

MAPPING_URL = (
    "https://raw.githubusercontent.com/ncihtan/htan-portal/"
    "4ce608118116f3e074415ef00a82bd460a9ba9ee/"
    "packages/data-portal-commons/src/assets/crdcgc_drs_mapping.json"
)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "htan-skill")
CACHE_FILE = os.path.join(CACHE_DIR, "crdcgc_drs_mapping.json")

# Validation pattern for HTAN_Data_File_ID (e.g., HTA9_1_19512)
FILE_ID_PATTERN = re.compile(r"^HTA\d+_\d+.*$")


def download_mapping(force=False):
    """Download the DRS mapping file from GitHub and cache it locally."""
    if os.path.exists(CACHE_FILE) and not force:
        size = os.path.getsize(CACHE_FILE)
        print(f"Cache exists: {CACHE_FILE} ({size:,} bytes)", file=sys.stderr)
        print("Use 'update' to re-download.", file=sys.stderr)
        return CACHE_FILE

    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"Downloading mapping file...", file=sys.stderr)

    try:
        req = urllib.request.Request(MAPPING_URL, headers={"User-Agent": "htan-skill/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.URLError as e:
        print(f"Error downloading mapping file: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate it's valid JSON before saving
    try:
        records = json.loads(data)
        if not isinstance(records, list):
            print("Error: Expected JSON array in mapping file.", file=sys.stderr)
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Downloaded file is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    with open(CACHE_FILE, "wb") as f:
        f.write(data)

    print(f"Saved {len(records):,} records to {CACHE_FILE}", file=sys.stderr)
    return CACHE_FILE


def load_mapping():
    """Load the mapping file and return a dict keyed by HTAN_Data_File_ID."""
    if not os.path.exists(CACHE_FILE):
        print("Mapping cache not found. Downloading...", file=sys.stderr)
        download_mapping(force=True)

    with open(CACHE_FILE, "r") as f:
        records = json.load(f)

    mapping = {}
    for rec in records:
        file_id = rec.get("HTAN_Data_File_ID")
        if file_id:
            mapping[file_id] = rec

    print(f"Loaded {len(mapping):,} file mappings", file=sys.stderr)
    return mapping


def infer_access_tier(file_id, level=None, assay=None):
    """Infer access tier based on HTAN portal rules.

    Args:
        file_id: HTAN_Data_File_ID
        level: Data level string (e.g., "Level 1", "Level 2", "Level 3", "Level 4")
        assay: Assay type string (e.g., "scRNA-seq", "Bulk RNA-seq", "CyCIF")

    Returns:
        "synapse" (open access), "gen3" (controlled access), or "unknown"
    """
    if level is None and assay is None:
        return "unknown"

    level_str = (level or "").strip().lower()
    assay_str = (assay or "").strip().lower()

    # Level 3, 4, Auxiliary, Other → always open access (Synapse)
    if any(x in level_str for x in ["level 3", "level 4", "auxiliary", "other"]):
        return "synapse"

    # Specialized assays → Synapse (open access)
    specialized = [
        "electron microscopy", "rppa", "slide-seq", "mass spec",
        "label free", "isobaric", "10x visium",
    ]
    if any(s in assay_str for s in specialized):
        return "synapse"

    # CODEX Level 1 → exception: open access (Synapse)
    if "codex" in assay_str and "level 1" in level_str:
        return "synapse"

    # Level 1-2 sequencing (bulk/-seq assays) → controlled (Gen3)
    seq_indicators = ["-seq", "bulk rna", "bulk wgs", "bulk wes", "scrna", "scatac", "snrna"]
    if any(x in level_str for x in ["level 1", "level 2"]):
        if any(s in assay_str for s in seq_indicators):
            return "gen3"

    return "unknown"


def format_text_output(results):
    """Format lookup results as a text table."""
    if not results:
        return ""

    # Column widths
    col_id = max(len("HTAN_Data_File_ID"), max(len(r.get("HTAN_Data_File_ID", "")) for r in results))
    col_name = max(len("Name"), max(len(r.get("name", "")[:40]) for r in results))
    col_eid = max(len("entityId"), max(len(r.get("entityId", "") or "") for r in results))
    col_drs = max(len("drs_uri"), min(45, max(len(r.get("drs_uri", "") or "") for r in results)))
    col_center = max(len("Center"), max(len(r.get("HTAN_Center", "") or "") for r in results))

    header = (
        f"{'HTAN_Data_File_ID':<{col_id}}  "
        f"{'Name':<{col_name}}  "
        f"{'entityId':<{col_eid}}  "
        f"{'drs_uri':<{col_drs}}  "
        f"{'Center':<{col_center}}"
    )
    sep = (
        f"{'-' * col_id}  "
        f"{'-' * col_name}  "
        f"{'-' * col_eid}  "
        f"{'-' * col_drs}  "
        f"{'-' * col_center}"
    )

    lines = [header, sep]
    for r in results:
        file_id = r.get("HTAN_Data_File_ID", "")
        name = r.get("name", "")[:40]
        eid = r.get("entityId", "") or ""
        drs = r.get("drs_uri", "") or ""
        if len(drs) > col_drs:
            drs = drs[:col_drs - 3] + "..."
        center = r.get("HTAN_Center", "") or ""
        lines.append(
            f"{file_id:<{col_id}}  "
            f"{name:<{col_name}}  "
            f"{eid:<{col_eid}}  "
            f"{drs:<{col_drs}}  "
            f"{center:<{col_center}}"
        )
    return "\n".join(lines)


def format_json_output(results):
    """Format lookup results as JSON with download commands."""
    output = []
    for r in results:
        entry = {
            "HTAN_Data_File_ID": r.get("HTAN_Data_File_ID", ""),
            "name": r.get("name", ""),
            "entityId": r.get("entityId", ""),
            "drs_uri": r.get("drs_uri", ""),
            "HTAN_Center": r.get("HTAN_Center", ""),
        }
        eid = r.get("entityId")
        drs = r.get("drs_uri")
        if eid:
            entry["synapse_download_cmd"] = f"python3 scripts/htan_synapse.py download {eid}"
        if drs:
            full_drs = drs if drs.startswith("drs://") else f"drs://{drs}"
            entry["gen3_download_cmd"] = f'python3 scripts/htan_gen3.py download "{full_drs}"'
        output.append(entry)
    return json.dumps(output, indent=2)


def cmd_update(args):
    """Handle the 'update' subcommand — download/refresh mapping cache."""
    download_mapping(force=True)


def cmd_lookup(args):
    """Handle the 'lookup' subcommand — look up file IDs."""
    # Collect file IDs from positional args and/or --file
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

    # Validate IDs
    for fid in file_ids:
        if not FILE_ID_PATTERN.match(fid):
            print(f"Warning: '{fid}' does not match expected HTAN_Data_File_ID format (HTA*_*_*)", file=sys.stderr)

    mapping = load_mapping()

    results = []
    not_found = []
    for fid in file_ids:
        rec = mapping.get(fid)
        if rec:
            results.append(rec)
        else:
            not_found.append(fid)

    if not_found:
        print(f"Not found in mapping ({len(not_found)}): {', '.join(not_found)}", file=sys.stderr)

    if not results:
        print("No matching records found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(results)}/{len(file_ids)} files", file=sys.stderr)

    if args.format == "json":
        print(format_json_output(results))
    else:
        print(format_text_output(results))


def cmd_stats(args):
    """Handle the 'stats' subcommand — show mapping statistics."""
    mapping = load_mapping()

    centers = {}
    with_drs = 0
    with_entity = 0
    for rec in mapping.values():
        center = rec.get("HTAN_Center", "Unknown")
        centers[center] = centers.get(center, 0) + 1
        if rec.get("drs_uri"):
            with_drs += 1
        if rec.get("entityId"):
            with_entity += 1

    print(f"Total files: {len(mapping):,}")
    print(f"With Synapse entityId: {with_entity:,}")
    print(f"With DRS URI (Gen3): {with_drs:,}")
    print()
    print("Files per center:")
    for center in sorted(centers, key=centers.get, reverse=True):
        print(f"  {center:<25} {centers[center]:>6,}")


def main():
    parser = argparse.ArgumentParser(
        description="HTAN file mapping: resolve HTAN_Data_File_ID to Synapse/Gen3 download coordinates",
        epilog="Examples:\n"
        "  python3 scripts/htan_file_mapping.py update\n"
        "  python3 scripts/htan_file_mapping.py lookup HTA9_1_19512\n"
        "  python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 HTA9_1_19553 --format json\n"
        "  python3 scripts/htan_file_mapping.py lookup --file ids.txt\n"
        "  python3 scripts/htan_file_mapping.py stats\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # update subcommand
    subparsers.add_parser("update", help="Download or refresh the mapping cache from GitHub")

    # lookup subcommand
    sp_lookup = subparsers.add_parser(
        "lookup", help="Look up HTAN_Data_File_IDs to get Synapse/Gen3 download info"
    )
    sp_lookup.add_argument("ids", nargs="*", help="One or more HTAN_Data_File_IDs")
    sp_lookup.add_argument("--file", "-f", help="File containing IDs (one per line)")
    sp_lookup.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)"
    )

    # stats subcommand
    subparsers.add_parser("stats", help="Show mapping statistics (file counts by center)")

    args = parser.parse_args()
    func = {
        "update": cmd_update,
        "lookup": cmd_lookup,
        "stats": cmd_stats,
    }[args.command]
    func(args)


if __name__ == "__main__":
    main()
