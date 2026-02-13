#!/usr/bin/env python3
"""Query the HTAN Phase 1 data model (ncihtan/data-models).

Fetches, caches, and queries the data model CSV from a pinned GitHub release tag.
Provides attribute lookup, valid values, component listings, and dependency chains.

No extra dependencies — uses only stdlib (csv, json, urllib, argparse).

Usage:
    python3 scripts/htan_data_model.py fetch
    python3 scripts/htan_data_model.py components
    python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"
    python3 scripts/htan_data_model.py describe "Library Construction Method"
    python3 scripts/htan_data_model.py valid-values "File Format"
    python3 scripts/htan_data_model.py search "barcode"
    python3 scripts/htan_data_model.py required "Biospecimen"
    python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"
"""

import argparse
import csv
import io
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

MODEL_TAG = "v25.2.1"
MODEL_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/ncihtan/data-models/{tag}/HTAN.model.csv"
)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "htan-skill")
CACHE_FILE = os.path.join(CACHE_DIR, "HTAN.model.csv")


def get_model_url(tag=None):
    """Return the URL for the data model CSV at the given tag."""
    return MODEL_URL_TEMPLATE.format(tag=tag or MODEL_TAG)


def download_model(tag=None, force=False, dry_run=False):
    """Download the data model CSV from GitHub and cache it locally."""
    url = get_model_url(tag)

    if dry_run:
        print(f"Dry run — would download from:", file=sys.stderr)
        print(f"  {url}", file=sys.stderr)
        print(f"  Cache: {CACHE_FILE}", file=sys.stderr)
        return None

    if os.path.exists(CACHE_FILE) and not force:
        size = os.path.getsize(CACHE_FILE)
        print(f"Cache exists: {CACHE_FILE} ({size:,} bytes)", file=sys.stderr)
        print("Use 'fetch' to re-download.", file=sys.stderr)
        return CACHE_FILE

    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"Downloading data model ({tag or MODEL_TAG})...", file=sys.stderr)
    print(f"  URL: {url}", file=sys.stderr)

    req = urllib.request.Request(url, headers={"User-Agent": "htan-skill/1.0"})

    # Try with certifi/default SSL context first, fall back to unverified on macOS cert issues
    try:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = resp.read()
    except urllib.error.URLError:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            print(f"Error downloading data model: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate it's parseable CSV before saving
    text = data.decode("utf-8")
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            print("Error: Downloaded CSV is empty.", file=sys.stderr)
            sys.exit(1)
        if "Attribute" not in reader.fieldnames:
            print("Error: CSV missing 'Attribute' column.", file=sys.stderr)
            sys.exit(1)
    except csv.Error as e:
        print(f"Error: Downloaded file is not valid CSV: {e}", file=sys.stderr)
        sys.exit(1)

    with open(CACHE_FILE, "wb") as f:
        f.write(data)

    print(f"Saved {len(rows):,} rows to {CACHE_FILE}", file=sys.stderr)
    return CACHE_FILE


def load_model(tag=None):
    """Load the cached model CSV. Auto-downloads on first use.

    Returns a list of dicts (one per row).
    """
    if not os.path.exists(CACHE_FILE):
        print("Model cache not found. Downloading...", file=sys.stderr)
        download_model(tag=tag, force=True)

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows):,} attributes from data model", file=sys.stderr)
    return rows


def get_components(rows):
    """Extract component definitions from the model.

    A row with non-empty 'DependsOn Component' is a component that depends on other
    components. Additionally, rows referenced in another component's 'DependsOn Component'
    that have their own 'DependsOn' attributes are also components (leaf components like
    Demographics, Diagnosis, etc.).
    """
    # First pass: find components with DependsOn Component
    components = []
    comp_names = set()
    referenced_components = set()

    for row in rows:
        dep_comp = (row.get("DependsOn Component") or "").strip()
        if dep_comp:
            name = row["Attribute"]
            parent = (row.get("Parent") or "").strip()
            depends_on = [a.strip() for a in (row.get("DependsOn") or "").split(",") if a.strip()]
            dep_components = [c.strip() for c in dep_comp.split(",") if c.strip()]
            components.append({
                "name": name,
                "parent": parent,
                "attribute_count": len(depends_on),
                "attributes": depends_on,
                "depends_on_components": dep_components,
            })
            comp_names.add(name)
            for dc in dep_components:
                referenced_components.add(dc)

    # Second pass: find referenced components that aren't already in the list
    # (leaf components like Demographics, Diagnosis, Therapy, etc.)
    for row in rows:
        name = row["Attribute"]
        if name in referenced_components and name not in comp_names:
            depends_on = [a.strip() for a in (row.get("DependsOn") or "").split(",") if a.strip()]
            if depends_on:
                parent = (row.get("Parent") or "").strip()
                components.append({
                    "name": name,
                    "parent": parent,
                    "attribute_count": len(depends_on),
                    "attributes": depends_on,
                    "depends_on_components": [],
                })
                comp_names.add(name)

    return components


def get_component_attributes(rows, component_name):
    """Get all attributes belonging to a component.

    Finds the component row, then returns details for each attribute listed
    in its DependsOn field. Works for both regular components (with DependsOn Component)
    and leaf components (with DependsOn attributes but no DependsOn Component).
    """
    # Get all known component names
    all_components = get_components(rows)
    comp_name_set = {c["name"].lower() for c in all_components}

    # Find the component row — match against known components
    comp_row = None
    for row in rows:
        if row["Attribute"].lower() == component_name.lower():
            depends_on = (row.get("DependsOn") or "").strip()
            if depends_on and row["Attribute"].lower() in comp_name_set:
                comp_row = row
                break

    if not comp_row:
        # Try fuzzy match against known components
        matches = []
        for row in rows:
            depends_on = (row.get("DependsOn") or "").strip()
            if depends_on and row["Attribute"].lower() in comp_name_set:
                if component_name.lower() in row["Attribute"].lower():
                    matches.append(row)
        if len(matches) == 1:
            comp_row = matches[0]
        elif matches:
            print(f"Ambiguous component name '{component_name}'. Did you mean:", file=sys.stderr)
            for m in matches:
                print(f"  - {m['Attribute']}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Error: Component '{component_name}' not found.", file=sys.stderr)
            print("Use 'components' to list all components.", file=sys.stderr)
            sys.exit(1)

    attr_names = [a.strip() for a in (comp_row.get("DependsOn") or "").split(",") if a.strip()]

    # Build a lookup dict for all rows
    attr_lookup = {}
    for row in rows:
        attr_lookup[row["Attribute"]] = row

    attributes = []
    for name in attr_names:
        row = attr_lookup.get(name)
        if row:
            valid_values = (row.get("Valid Values") or "").strip()
            vv_list = [v.strip() for v in valid_values.split(",") if v.strip()] if valid_values else []
            attributes.append({
                "name": name,
                "description": (row.get("Description") or "").strip(),
                "required": (row.get("Required") or "").strip().upper() == "TRUE",
                "valid_values_count": len(vv_list),
                "valid_values_preview": ", ".join(vv_list[:5]) + ("..." if len(vv_list) > 5 else ""),
                "validation_rules": (row.get("Validation Rules") or "").strip(),
                "parent": (row.get("Parent") or "").strip(),
            })
        else:
            attributes.append({
                "name": name,
                "description": "",
                "required": False,
                "valid_values_count": 0,
                "valid_values_preview": "",
                "validation_rules": "",
                "parent": "",
            })

    return comp_row["Attribute"], attributes


def find_attribute(rows, attr_name):
    """Find an attribute row by name (case-insensitive)."""
    # Exact match first
    for row in rows:
        if row["Attribute"].lower() == attr_name.lower():
            return row

    # Fuzzy match
    matches = [row for row in rows if attr_name.lower() in row["Attribute"].lower()]
    if len(matches) == 1:
        return matches[0]
    elif matches:
        print(f"Ambiguous attribute name '{attr_name}'. Did you mean:", file=sys.stderr)
        for m in matches[:10]:
            print(f"  - {m['Attribute']}", file=sys.stderr)
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more", file=sys.stderr)
        sys.exit(1)

    print(f"Error: Attribute '{attr_name}' not found.", file=sys.stderr)
    print("Use 'search' to find attributes by keyword.", file=sys.stderr)
    sys.exit(1)


def get_dependency_chain(rows, component_name):
    """Trace the dependency chain for a component.

    Follows DependsOn Component links to build the full chain, e.g.:
    scRNA-seq Level 1 → Biospecimen → Patient
    """
    # Build component lookup from all components (including leaf components)
    all_components = get_components(rows)
    comp_lookup = {}
    for comp in all_components:
        comp_lookup[comp["name"].lower()] = {
            "name": comp["name"],
            "depends_on_components": comp["depends_on_components"],
        }

    # Find the starting component
    start_key = component_name.lower()
    if start_key not in comp_lookup:
        # Fuzzy match
        matches = [k for k in comp_lookup if component_name.lower() in k]
        if len(matches) == 1:
            start_key = matches[0]
        elif matches:
            print(f"Ambiguous component '{component_name}'. Did you mean:", file=sys.stderr)
            for m in matches:
                print(f"  - {comp_lookup[m]['name']}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Error: Component '{component_name}' not found.", file=sys.stderr)
            sys.exit(1)

    # BFS to trace dependencies
    chain = []
    visited = set()
    queue = [start_key]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        comp = comp_lookup.get(current)
        if comp:
            chain.append(comp)
            for dep in comp["depends_on_components"]:
                dep_key = dep.lower()
                if dep_key not in visited:
                    queue.append(dep_key)

    return chain


def categorize_component(name, parent):
    """Assign a category to a component based on name and parent."""
    name_lower = name.lower()
    parent_lower = parent.lower() if parent else ""

    if any(x in name_lower for x in ["demographics", "diagnosis", "exposure", "follow",
                                       "therapy", "molecular test", "family history",
                                       "patient", "clinical"]):
        return "Clinical"
    if "biospecimen" in name_lower:
        return "Biospecimen"
    if any(x in name_lower for x in ["visium", "merfish", "slide-seq", "geomx",
                                       "nanostring", "xenium", "spatial"]):
        return "Spatial Transcriptomics"
    if any(x in name_lower for x in ["imaging", "cycif", "codex", "mibi", "ihc",
                                       "h&e", "hematoxylin", "electron microscopy",
                                       "imc", "saber"]):
        return "Imaging"
    if any(x in name_lower for x in ["scrna", "scatac", "snrna", "cite-seq",
                                       "bulkrna", "bulkwes", "bulkwgs", "hi-c",
                                       "methylation", "scdna", "rna-seq", "atac-seq",
                                       "wes", "wgs"]):
        return "Sequencing"
    if any(x in name_lower for x in ["mass spec", "rppa", "label free", "isobaric"]):
        return "Proteomics"
    if "sequencing" in parent_lower or "assay" in parent_lower:
        return "Sequencing"
    return "Other"


# --- Output formatters ---

def format_components_text(components):
    """Format component listing as text table."""
    # Group by category
    categorized = {}
    for comp in components:
        cat = categorize_component(comp["name"], comp["parent"])
        categorized.setdefault(cat, []).append(comp)

    lines = []
    # Order categories
    cat_order = ["Clinical", "Biospecimen", "Sequencing", "Imaging",
                 "Spatial Transcriptomics", "Proteomics", "Other"]
    for cat in cat_order:
        comps = categorized.get(cat, [])
        if not comps:
            continue
        lines.append(f"\n=== {cat} ({len(comps)} components) ===")
        lines.append(f"{'Component':<45} {'Attrs':>5}  {'Parent'}")
        lines.append(f"{'-'*45} {'-'*5}  {'-'*30}")
        for comp in sorted(comps, key=lambda c: c["name"]):
            name = comp["name"][:45]
            lines.append(f"{name:<45} {comp['attribute_count']:>5}  {comp['parent']}")

    lines.append(f"\nTotal: {len(components)} components")
    return "\n".join(lines)


def format_attributes_text(component_name, attributes):
    """Format attribute listing as text table."""
    lines = [
        f"Component: {component_name}",
        f"Attributes: {len(attributes)}",
        "",
        f"{'Attribute':<40} {'Req':>3}  {'Values':>6}  {'Valid Values Preview'}",
        f"{'-'*40} {'-'*3}  {'-'*6}  {'-'*40}",
    ]
    for attr in attributes:
        req = "Yes" if attr["required"] else ""
        preview = attr["valid_values_preview"][:40]
        lines.append(
            f"{attr['name']:<40} {req:>3}  {attr['valid_values_count']:>6}  {preview}"
        )
    return "\n".join(lines)


def format_describe_text(row):
    """Format full attribute detail as text."""
    valid_values = (row.get("Valid Values") or "").strip()
    vv_list = [v.strip() for v in valid_values.split(",") if v.strip()] if valid_values else []
    depends_on = (row.get("DependsOn") or "").strip()
    dep_list = [d.strip() for d in depends_on.split(",") if d.strip()] if depends_on else []

    lines = [
        f"Attribute: {row['Attribute']}",
        f"Description: {(row.get('Description') or 'N/A').strip()}",
        f"Required: {(row.get('Required') or 'FALSE').strip()}",
        f"Parent: {(row.get('Parent') or 'N/A').strip()}",
        f"Source: {(row.get('Source') or 'N/A').strip()}",
        f"Validation Rules: {(row.get('Validation Rules') or 'None').strip()}",
        f"DependsOn: {', '.join(dep_list) if dep_list else 'None'}",
    ]

    dep_comp = (row.get("DependsOn Component") or "").strip()
    if dep_comp:
        lines.append(f"DependsOn Component: {dep_comp}")

    lines.append(f"\nValid Values ({len(vv_list)}):")
    if vv_list:
        for v in vv_list:
            lines.append(f"  - {v}")
    else:
        lines.append("  (none — free text or computed)")

    return "\n".join(lines)


def format_valid_values_text(attr_name, values):
    """Format valid values list as text."""
    lines = [f"Valid values for '{attr_name}' ({len(values)}):"]
    for v in values:
        lines.append(f"  {v}")
    if not values:
        lines.append("  (none — free text or computed)")
    return "\n".join(lines)


def format_search_text(results):
    """Format search results as text."""
    if not results:
        return "No matches found."

    lines = [
        f"{'Attribute':<40} {'Parent':<25} {'Match In'}",
        f"{'-'*40} {'-'*25} {'-'*15}",
    ]
    for r in results:
        lines.append(f"{r['name']:<40} {r['parent']:<25} {r['match_in']}")
    lines.append(f"\n{len(results)} matches")
    return "\n".join(lines)


def format_required_text(component_name, attributes):
    """Format required attributes as text."""
    required = [a for a in attributes if a["required"]]
    optional = [a for a in attributes if not a["required"]]
    lines = [
        f"Component: {component_name}",
        f"Required: {len(required)}, Optional: {len(optional)}, Total: {len(attributes)}",
        "",
        "Required attributes:",
    ]
    for attr in required:
        vr = attr["validation_rules"]
        suffix = f"  [{vr}]" if vr else ""
        lines.append(f"  {attr['name']}{suffix}")
    return "\n".join(lines)


def format_deps_text(chain):
    """Format dependency chain as a tree."""
    if not chain:
        return "No dependency chain found."

    # Build a tree structure: for each component, show its children
    lines = []

    def render(comp, depth=0):
        indent = "  " * depth
        arrow = "→ " if depth > 0 else ""
        deps = comp.get("depends_on_components", [])
        if deps:
            lines.append(f"{indent}{arrow}{comp['name']}  (requires: {', '.join(deps)})")
        else:
            lines.append(f"{indent}{arrow}{comp['name']}")

    if not chain:
        return "No dependency chain found."

    # The first item is the root. Render it, then its direct deps as siblings at depth+1,
    # and continue recursively
    rendered = set()

    def render_tree(comp, depth=0):
        name = comp["name"]
        if name in rendered:
            return
        rendered.add(name)

        deps = comp.get("depends_on_components", [])
        if deps:
            lines.append(f"{'  ' * depth}{'→ ' if depth > 0 else ''}{name}")
            # Find each dependency in the chain and render it
            comp_by_name = {c["name"].lower(): c for c in chain}
            for dep_name in deps:
                dep_comp = comp_by_name.get(dep_name.lower())
                if dep_comp and dep_comp["name"] not in rendered:
                    render_tree(dep_comp, depth + 1)
                elif dep_name not in rendered:
                    lines.append(f"{'  ' * (depth + 1)}→ {dep_name}")
                    rendered.add(dep_name)
        else:
            lines.append(f"{'  ' * depth}{'→ ' if depth > 0 else ''}{name}")

    render_tree(chain[0], 0)
    return "\n".join(lines)


# --- Subcommand handlers ---

def cmd_fetch(args):
    """Handle 'fetch' subcommand — download/refresh model CSV."""
    download_model(tag=args.tag, force=True, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"Model version: {args.tag or MODEL_TAG}", file=sys.stderr)


def cmd_components(args):
    """Handle 'components' subcommand — list all components."""
    rows = load_model(tag=args.tag)
    components = get_components(rows)

    if not components:
        print("No components found in model.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(components, indent=2))
    else:
        print(format_components_text(components))


def cmd_attributes(args):
    """Handle 'attributes' subcommand — list attributes for a component."""
    rows = load_model(tag=args.tag)
    component_name, attributes = get_component_attributes(rows, args.component)

    if args.format == "json":
        print(json.dumps({"component": component_name, "attributes": attributes}, indent=2))
    else:
        print(format_attributes_text(component_name, attributes))


def cmd_describe(args):
    """Handle 'describe' subcommand — full detail for one attribute."""
    rows = load_model(tag=args.tag)
    row = find_attribute(rows, args.attribute)

    if args.format == "json":
        valid_values = (row.get("Valid Values") or "").strip()
        vv_list = [v.strip() for v in valid_values.split(",") if v.strip()] if valid_values else []
        depends_on = (row.get("DependsOn") or "").strip()
        dep_list = [d.strip() for d in depends_on.split(",") if d.strip()] if depends_on else []
        output = {
            "attribute": row["Attribute"],
            "description": (row.get("Description") or "").strip(),
            "required": (row.get("Required") or "").strip().upper() == "TRUE",
            "parent": (row.get("Parent") or "").strip(),
            "source": (row.get("Source") or "").strip(),
            "validation_rules": (row.get("Validation Rules") or "").strip(),
            "depends_on": dep_list,
            "depends_on_component": (row.get("DependsOn Component") or "").strip(),
            "valid_values": vv_list,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_describe_text(row))


def cmd_valid_values(args):
    """Handle 'valid-values' subcommand — list all valid values for an attribute."""
    rows = load_model(tag=args.tag)
    row = find_attribute(rows, args.attribute)

    valid_values = (row.get("Valid Values") or "").strip()
    vv_list = [v.strip() for v in valid_values.split(",") if v.strip()] if valid_values else []

    if args.format == "json":
        print(json.dumps({"attribute": row["Attribute"], "valid_values": vv_list}, indent=2))
    else:
        print(format_valid_values_text(row["Attribute"], vv_list))


def cmd_search(args):
    """Handle 'search' subcommand — search attributes by keyword."""
    rows = load_model(tag=args.tag)
    keyword = args.keyword.lower()

    results = []
    for row in rows:
        name = row["Attribute"]
        desc = (row.get("Description") or "").strip()
        valid = (row.get("Valid Values") or "").strip()
        parent = (row.get("Parent") or "").strip()

        match_in = []
        if keyword in name.lower():
            match_in.append("name")
        if keyword in desc.lower():
            match_in.append("description")
        if keyword in valid.lower():
            match_in.append("valid values")

        if match_in:
            results.append({
                "name": name,
                "parent": parent,
                "description": desc,
                "match_in": ", ".join(match_in),
            })

    print(f"Searching for '{args.keyword}'...", file=sys.stderr)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_search_text(results))


def cmd_required(args):
    """Handle 'required' subcommand — list required attributes for a component."""
    rows = load_model(tag=args.tag)
    component_name, attributes = get_component_attributes(rows, args.component)

    if args.format == "json":
        required = [a for a in attributes if a["required"]]
        print(json.dumps({"component": component_name, "required_attributes": required}, indent=2))
    else:
        print(format_required_text(component_name, attributes))


def cmd_deps(args):
    """Handle 'deps' subcommand — show dependency chain for a component."""
    rows = load_model(tag=args.tag)
    chain = get_dependency_chain(rows, args.component)

    if args.format == "json":
        print(json.dumps(chain, indent=2))
    else:
        print(format_deps_text(chain))


def main():
    parser = argparse.ArgumentParser(
        description="Query the HTAN Phase 1 data model (ncihtan/data-models)",
        epilog="Examples:\n"
        "  python3 scripts/htan_data_model.py fetch\n"
        "  python3 scripts/htan_data_model.py components\n"
        '  python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"\n'
        '  python3 scripts/htan_data_model.py describe "Library Construction Method"\n'
        '  python3 scripts/htan_data_model.py valid-values "File Format"\n'
        '  python3 scripts/htan_data_model.py search "barcode"\n'
        '  python3 scripts/htan_data_model.py required "Biospecimen"\n'
        '  python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common arguments
    def add_common_args(sp):
        sp.add_argument("--tag", default=None, help=f"Model version tag (default: {MODEL_TAG})")
        sp.add_argument(
            "--format", choices=["text", "json"], default="text",
            help="Output format (default: text)"
        )

    # fetch
    sp_fetch = subparsers.add_parser("fetch", help="Download or refresh the model CSV from GitHub")
    sp_fetch.add_argument("--tag", default=None, help=f"Model version tag (default: {MODEL_TAG})")
    sp_fetch.add_argument("--format", choices=["text", "json"], default="text", help=argparse.SUPPRESS)
    sp_fetch.add_argument("--dry-run", action="store_true", help="Show URL without downloading")

    # components
    sp_comp = subparsers.add_parser("components", help="List all manifest components")
    add_common_args(sp_comp)

    # attributes
    sp_attr = subparsers.add_parser("attributes", help="List attributes for a component")
    sp_attr.add_argument("component", help="Component name (e.g., 'scRNA-seq Level 1', 'Biospecimen')")
    add_common_args(sp_attr)

    # describe
    sp_desc = subparsers.add_parser("describe", help="Full detail for one attribute")
    sp_desc.add_argument("attribute", help="Attribute name (e.g., 'Library Construction Method')")
    add_common_args(sp_desc)

    # valid-values
    sp_vv = subparsers.add_parser("valid-values", help="List all valid values for an attribute")
    sp_vv.add_argument("attribute", help="Attribute name (e.g., 'File Format')")
    add_common_args(sp_vv)

    # search
    sp_search = subparsers.add_parser("search", help="Search attributes by keyword")
    sp_search.add_argument("keyword", help="Keyword to search for in names, descriptions, and values")
    add_common_args(sp_search)

    # required
    sp_req = subparsers.add_parser("required", help="List required attributes for a component")
    sp_req.add_argument("component", help="Component name")
    add_common_args(sp_req)

    # deps
    sp_deps = subparsers.add_parser("deps", help="Show dependency chain for a component")
    sp_deps.add_argument("component", help="Component name")
    add_common_args(sp_deps)

    args = parser.parse_args()
    func = {
        "fetch": cmd_fetch,
        "components": cmd_components,
        "attributes": cmd_attributes,
        "describe": cmd_describe,
        "valid-values": cmd_valid_values,
        "search": cmd_search,
        "required": cmd_required,
        "deps": cmd_deps,
    }[args.command]
    func(args)


if __name__ == "__main__":
    main()
