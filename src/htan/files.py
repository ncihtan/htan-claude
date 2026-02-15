"""HTAN file mapping: resolve HTAN_Data_File_ID to Synapse entityId and Gen3 DRS URI.

Downloads and caches the DRS mapping file from the HTAN portal, then provides
lookup by HTAN_Data_File_ID to get download coordinates for both platforms.

No extra dependencies — uses only stdlib (urllib, json).

Usage as library:
    from htan.files import lookup, update_cache, stats
    results = lookup(["HTA9_1_19512"])
    update_cache()

Usage as CLI:
    htan files lookup HTA9_1_19512
    htan files update
    htan files stats
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

FILE_ID_PATTERN = re.compile(r"^HTA\d+_\d+.*$")


def _download_mapping(force=False):
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


def _load_mapping():
    """Load the mapping file and return a dict keyed by HTAN_Data_File_ID."""
    if not os.path.exists(CACHE_FILE):
        print("Mapping cache not found. Downloading...", file=sys.stderr)
        _download_mapping(force=True)

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

    Returns:
        "synapse" (open access), "gen3" (controlled access), or "unknown"
    """
    if level is None and assay is None:
        return "unknown"

    level_str = (level or "").strip().lower()
    assay_str = (assay or "").strip().lower()

    if any(x in level_str for x in ["level 3", "level 4", "auxiliary", "other"]):
        return "synapse"

    specialized = [
        "electron microscopy", "rppa", "slide-seq", "mass spec",
        "label free", "isobaric", "10x visium",
    ]
    if any(s in assay_str for s in specialized):
        return "synapse"

    if "codex" in assay_str and "level 1" in level_str:
        return "synapse"

    seq_indicators = ["-seq", "bulk rna", "bulk wgs", "bulk wes", "scrna", "scatac", "snrna"]
    if any(x in level_str for x in ["level 1", "level 2"]):
        if any(s in assay_str for s in seq_indicators):
            return "gen3"

    return "unknown"


# --- Public API ---

def lookup(file_ids, format="text"):
    """Look up file IDs and return download coordinates.

    Args:
        file_ids: List of HTAN_Data_File_ID strings.
        format: Output format ("text" or "json").

    Returns:
        List of mapping record dicts for found files.
    """
    mapping = _load_mapping()

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

    return results


def update_cache():
    """Download/refresh the mapping cache. Returns cache file path."""
    return _download_mapping(force=True)


def stats():
    """Get mapping statistics. Returns dict with counts."""
    mapping = _load_mapping()

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

    return {
        "total_files": len(mapping),
        "with_synapse_entity_id": with_entity,
        "with_drs_uri": with_drs,
        "files_per_center": dict(sorted(centers.items(), key=lambda x: x[1], reverse=True)),
    }


# --- CLI ---

def _format_text_output(results):
    if not results:
        return ""
    col_id = max(len("HTAN_Data_File_ID"), max(len(r.get("HTAN_Data_File_ID", "")) for r in results))
    col_name = max(len("Name"), max(len(r.get("name", "")[:40]) for r in results))
    col_eid = max(len("entityId"), max(len(r.get("entityId", "") or "") for r in results))
    col_drs = max(len("drs_uri"), min(45, max(len(r.get("drs_uri", "") or "") for r in results)))
    col_center = max(len("Center"), max(len(r.get("HTAN_Center", "") or "") for r in results))

    header = f"{'HTAN_Data_File_ID':<{col_id}}  {'Name':<{col_name}}  {'entityId':<{col_eid}}  {'drs_uri':<{col_drs}}  {'Center':<{col_center}}"
    sep = f"{'-' * col_id}  {'-' * col_name}  {'-' * col_eid}  {'-' * col_drs}  {'-' * col_center}"

    lines = [header, sep]
    for r in results:
        file_id = r.get("HTAN_Data_File_ID", "")
        name = r.get("name", "")[:40]
        eid = r.get("entityId", "") or ""
        drs = r.get("drs_uri", "") or ""
        if len(drs) > col_drs:
            drs = drs[:col_drs - 3] + "..."
        center = r.get("HTAN_Center", "") or ""
        lines.append(f"{file_id:<{col_id}}  {name:<{col_name}}  {eid:<{col_eid}}  {drs:<{col_drs}}  {center:<{col_center}}")
    return "\n".join(lines)


def _format_json_output(results):
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
            entry["synapse_download_cmd"] = f"htan download synapse {eid}"
        if drs:
            full_drs = drs if drs.startswith("drs://") else f"drs://{drs}"
            entry["gen3_download_cmd"] = f'htan download gen3 "{full_drs}"'
        output.append(entry)
    return json.dumps(output, indent=2)


def cli_main(argv=None):
    """CLI entry point for file mapping."""
    parser = argparse.ArgumentParser(
        description="HTAN file mapping: resolve HTAN_Data_File_ID to download coordinates",
        epilog="Examples:\n"
        "  htan files update\n"
        "  htan files lookup HTA9_1_19512\n"
        "  htan files lookup HTA9_1_19512 HTA9_1_19553 --format json\n"
        "  htan files stats\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("update", help="Download or refresh the mapping cache")

    sp_lookup = subparsers.add_parser("lookup", help="Look up HTAN_Data_File_IDs")
    sp_lookup.add_argument("ids", nargs="*", help="HTAN_Data_File_IDs")
    sp_lookup.add_argument("--file", "-f", help="File containing IDs (one per line)")
    sp_lookup.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    subparsers.add_parser("stats", help="Show mapping statistics")

    args = parser.parse_args(argv)

    if args.command == "update":
        update_cache()
    elif args.command == "lookup":
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
            print("Error: No file IDs provided.", file=sys.stderr)
            sys.exit(1)

        for fid in file_ids:
            if not FILE_ID_PATTERN.match(fid):
                print(f"Warning: '{fid}' does not match expected format (HTA*_*_*)", file=sys.stderr)

        results = lookup(file_ids)
        if not results:
            print("No matching records found.", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(results)}/{len(file_ids)} files", file=sys.stderr)
        if args.format == "json":
            print(_format_json_output(results))
        else:
            print(_format_text_output(results))

    elif args.command == "stats":
        s = stats()
        print(f"Total files: {s['total_files']:,}")
        print(f"With Synapse entityId: {s['with_synapse_entity_id']:,}")
        print(f"With DRS URI (Gen3): {s['with_drs_uri']:,}")
        print()
        print("Files per center:")
        for center, count in s["files_per_center"].items():
            print(f"  {center:<25} {count:>6,}")
