"""Query the HTAN Phase 1 data model (ncihtan/data-models).

Fetches, caches, and queries the data model CSV from a pinned GitHub release tag.
No extra dependencies — uses only stdlib (csv, json, urllib, argparse).

Usage as library:
    from htan.model import DataModel
    dm = DataModel()
    components = dm.components()
    attrs = dm.attributes("scRNA-seq Level 1")

Usage as CLI:
    htan model components
    htan model attributes "scRNA-seq Level 1"
    htan model describe "Library Construction Method"
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


def _get_model_url(tag=None):
    return MODEL_URL_TEMPLATE.format(tag=tag or MODEL_TAG)


def _make_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download_model(tag=None, force=False, dry_run=False):
    """Download the data model CSV from GitHub and cache it locally."""
    url = _get_model_url(tag)

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

    req = urllib.request.Request(url, headers={"User-Agent": "htan-skill/1.0"})

    try:
        ctx = _make_ssl_context()
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


def _load_model(tag=None):
    """Load the cached model CSV. Auto-downloads on first use."""
    if not os.path.exists(CACHE_FILE):
        print("Model cache not found. Downloading...", file=sys.stderr)
        download_model(tag=tag, force=True)

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows):,} attributes from data model", file=sys.stderr)
    return rows


def _get_components(rows):
    """Extract component definitions from the model."""
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
                "name": name, "parent": parent,
                "attribute_count": len(depends_on), "attributes": depends_on,
                "depends_on_components": dep_components,
            })
            comp_names.add(name)
            for dc in dep_components:
                referenced_components.add(dc)

    for row in rows:
        name = row["Attribute"]
        if name in referenced_components and name not in comp_names:
            depends_on = [a.strip() for a in (row.get("DependsOn") or "").split(",") if a.strip()]
            if depends_on:
                parent = (row.get("Parent") or "").strip()
                components.append({
                    "name": name, "parent": parent,
                    "attribute_count": len(depends_on), "attributes": depends_on,
                    "depends_on_components": [],
                })
                comp_names.add(name)

    return components


def _get_component_attributes(rows, component_name):
    """Get all attributes belonging to a component."""
    all_components = _get_components(rows)
    comp_name_set = {c["name"].lower() for c in all_components}

    comp_row = None
    for row in rows:
        if row["Attribute"].lower() == component_name.lower():
            depends_on = (row.get("DependsOn") or "").strip()
            if depends_on and row["Attribute"].lower() in comp_name_set:
                comp_row = row
                break

    if not comp_row:
        matches = []
        for row in rows:
            depends_on = (row.get("DependsOn") or "").strip()
            if depends_on and row["Attribute"].lower() in comp_name_set:
                if component_name.lower() in row["Attribute"].lower():
                    matches.append(row)
        if len(matches) == 1:
            comp_row = matches[0]
        elif matches:
            raise ValueError(
                f"Ambiguous component name '{component_name}'. Did you mean: "
                + ", ".join(m["Attribute"] for m in matches)
            )
        else:
            raise ValueError(f"Component '{component_name}' not found. Use components() to list all.")

    attr_names = [a.strip() for a in (comp_row.get("DependsOn") or "").split(",") if a.strip()]
    attr_lookup = {row["Attribute"]: row for row in rows}

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
                "name": name, "description": "", "required": False,
                "valid_values_count": 0, "valid_values_preview": "",
                "validation_rules": "", "parent": "",
            })

    return comp_row["Attribute"], attributes


def _find_attribute(rows, attr_name):
    """Find an attribute row by name (case-insensitive)."""
    for row in rows:
        if row["Attribute"].lower() == attr_name.lower():
            return row
    matches = [row for row in rows if attr_name.lower() in row["Attribute"].lower()]
    if len(matches) == 1:
        return matches[0]
    elif matches:
        raise ValueError(
            f"Ambiguous attribute name '{attr_name}'. Did you mean: "
            + ", ".join(m["Attribute"] for m in matches[:10])
        )
    raise ValueError(f"Attribute '{attr_name}' not found. Use search() to find by keyword.")


def _get_dependency_chain(rows, component_name):
    """Trace the dependency chain for a component."""
    all_components = _get_components(rows)
    comp_lookup = {}
    for comp in all_components:
        comp_lookup[comp["name"].lower()] = {
            "name": comp["name"],
            "depends_on_components": comp["depends_on_components"],
        }

    start_key = component_name.lower()
    if start_key not in comp_lookup:
        matches = [k for k in comp_lookup if component_name.lower() in k]
        if len(matches) == 1:
            start_key = matches[0]
        elif matches:
            raise ValueError(
                f"Ambiguous component '{component_name}'. Did you mean: "
                + ", ".join(comp_lookup[m]["name"] for m in matches)
            )
        else:
            raise ValueError(f"Component '{component_name}' not found.")

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


# --- DataModel class ---

class DataModel:
    """Query the HTAN Phase 1 data model.

    Auto-fetches model CSV from GitHub on first use.

    Usage:
        dm = DataModel()
        comps = dm.components()
        attrs = dm.attributes("scRNA-seq Level 1")
        detail = dm.describe("File Format")
    """

    def __init__(self, cache_dir=None, tag=None):
        self._tag = tag
        self._rows = None
        if cache_dir:
            global CACHE_DIR, CACHE_FILE
            CACHE_DIR = cache_dir
            CACHE_FILE = os.path.join(CACHE_DIR, "HTAN.model.csv")

    def _load(self):
        if self._rows is None:
            self._rows = _load_model(tag=self._tag)
        return self._rows

    def components(self):
        """List all manifest components. Returns list of component dicts."""
        return _get_components(self._load())

    def attributes(self, component):
        """List attributes for a component. Returns (component_name, list of attr dicts)."""
        return _get_component_attributes(self._load(), component)

    def describe(self, attribute):
        """Get full details for one attribute. Returns dict."""
        row = _find_attribute(self._load(), attribute)
        valid_values = (row.get("Valid Values") or "").strip()
        vv_list = [v.strip() for v in valid_values.split(",") if v.strip()] if valid_values else []
        depends_on = (row.get("DependsOn") or "").strip()
        dep_list = [d.strip() for d in depends_on.split(",") if d.strip()] if depends_on else []
        return {
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

    def valid_values(self, attribute):
        """List valid values for an attribute. Returns list of strings."""
        row = _find_attribute(self._load(), attribute)
        valid_values = (row.get("Valid Values") or "").strip()
        return [v.strip() for v in valid_values.split(",") if v.strip()] if valid_values else []

    def search(self, keyword):
        """Search attributes by keyword. Returns list of match dicts."""
        keyword_lower = keyword.lower()
        results = []
        for row in self._load():
            name = row["Attribute"]
            desc = (row.get("Description") or "").strip()
            valid = (row.get("Valid Values") or "").strip()
            parent = (row.get("Parent") or "").strip()

            match_in = []
            if keyword_lower in name.lower():
                match_in.append("name")
            if keyword_lower in desc.lower():
                match_in.append("description")
            if keyword_lower in valid.lower():
                match_in.append("valid values")

            if match_in:
                results.append({
                    "name": name, "parent": parent, "description": desc,
                    "match_in": ", ".join(match_in),
                })
        return results

    def required(self, component):
        """List required attributes for a component. Returns list of attr dicts."""
        _, attrs = self.attributes(component)
        return [a for a in attrs if a["required"]]

    def deps(self, component):
        """Show dependency chain for a component. Returns list of component dicts."""
        return _get_dependency_chain(self._load(), component)


# --- Formatting helpers ---

def _categorize_component(name, parent):
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


def _format_components_text(components):
    categorized = {}
    for comp in components:
        cat = _categorize_component(comp["name"], comp["parent"])
        categorized.setdefault(cat, []).append(comp)

    lines = []
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


def _format_attributes_text(component_name, attributes):
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
        lines.append(f"{attr['name']:<40} {req:>3}  {attr['valid_values_count']:>6}  {preview}")
    return "\n".join(lines)


def _format_describe_text(detail):
    lines = [
        f"Attribute: {detail['attribute']}",
        f"Description: {detail.get('description') or 'N/A'}",
        f"Required: {detail.get('required', False)}",
        f"Parent: {detail.get('parent') or 'N/A'}",
        f"Source: {detail.get('source') or 'N/A'}",
        f"Validation Rules: {detail.get('validation_rules') or 'None'}",
        f"DependsOn: {', '.join(detail.get('depends_on', [])) or 'None'}",
    ]
    dep_comp = detail.get("depends_on_component", "")
    if dep_comp:
        lines.append(f"DependsOn Component: {dep_comp}")
    vv = detail.get("valid_values", [])
    lines.append(f"\nValid Values ({len(vv)}):")
    if vv:
        for v in vv:
            lines.append(f"  - {v}")
    else:
        lines.append("  (none — free text or computed)")
    return "\n".join(lines)


def _format_deps_text(chain):
    if not chain:
        return "No dependency chain found."
    lines = []
    rendered = set()

    def render_tree(comp, depth=0):
        name = comp["name"]
        if name in rendered:
            return
        rendered.add(name)
        deps = comp.get("depends_on_components", [])
        if deps:
            lines.append(f"{'  ' * depth}{'→ ' if depth > 0 else ''}{name}")
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


# --- CLI ---

def cli_main(argv=None):
    """CLI entry point for data model queries."""
    parser = argparse.ArgumentParser(
        description="Query the HTAN Phase 1 data model (ncihtan/data-models)",
        epilog="Examples:\n"
        "  htan model fetch\n"
        "  htan model components\n"
        '  htan model attributes "scRNA-seq Level 1"\n'
        '  htan model describe "Library Construction Method"\n'
        '  htan model valid-values "File Format"\n'
        '  htan model search "barcode"\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_args(sp):
        sp.add_argument("--tag", default=None, help=f"Model version tag (default: {MODEL_TAG})")
        sp.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    sp_fetch = subparsers.add_parser("fetch", help="Download or refresh the model CSV")
    sp_fetch.add_argument("--tag", default=None)
    sp_fetch.add_argument("--format", choices=["text", "json"], default="text", help=argparse.SUPPRESS)
    sp_fetch.add_argument("--dry-run", action="store_true")

    sp_comp = subparsers.add_parser("components", help="List all manifest components")
    add_common_args(sp_comp)

    sp_attr = subparsers.add_parser("attributes", help="List attributes for a component")
    sp_attr.add_argument("component", help="Component name")
    add_common_args(sp_attr)

    sp_desc = subparsers.add_parser("describe", help="Full detail for one attribute")
    sp_desc.add_argument("attribute", help="Attribute name")
    add_common_args(sp_desc)

    sp_vv = subparsers.add_parser("valid-values", help="List valid values for an attribute")
    sp_vv.add_argument("attribute", help="Attribute name")
    add_common_args(sp_vv)

    sp_search = subparsers.add_parser("search", help="Search attributes by keyword")
    sp_search.add_argument("keyword", help="Keyword to search for")
    add_common_args(sp_search)

    sp_req = subparsers.add_parser("required", help="List required attributes for a component")
    sp_req.add_argument("component", help="Component name")
    add_common_args(sp_req)

    sp_deps = subparsers.add_parser("deps", help="Show dependency chain for a component")
    sp_deps.add_argument("component", help="Component name")
    add_common_args(sp_deps)

    args = parser.parse_args(argv)
    dm = DataModel(tag=args.tag if hasattr(args, "tag") else None)

    if args.command == "fetch":
        download_model(tag=args.tag, force=True, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"Model version: {args.tag or MODEL_TAG}", file=sys.stderr)
    elif args.command == "components":
        comps = dm.components()
        if args.format == "json":
            print(json.dumps(comps, indent=2))
        else:
            print(_format_components_text(comps))
    elif args.command == "attributes":
        comp_name, attrs = dm.attributes(args.component)
        if args.format == "json":
            print(json.dumps({"component": comp_name, "attributes": attrs}, indent=2))
        else:
            print(_format_attributes_text(comp_name, attrs))
    elif args.command == "describe":
        detail = dm.describe(args.attribute)
        if args.format == "json":
            print(json.dumps(detail, indent=2))
        else:
            print(_format_describe_text(detail))
    elif args.command == "valid-values":
        vv = dm.valid_values(args.attribute)
        row = _find_attribute(dm._load(), args.attribute)
        attr_name = row["Attribute"]
        if args.format == "json":
            print(json.dumps({"attribute": attr_name, "valid_values": vv}, indent=2))
        else:
            print(f"Valid values for '{attr_name}' ({len(vv)}):")
            for v in vv:
                print(f"  {v}")
            if not vv:
                print("  (none — free text or computed)")
    elif args.command == "search":
        results = dm.search(args.keyword)
        print(f"Searching for '{args.keyword}'...", file=sys.stderr)
        if args.format == "json":
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No matches found.")
            else:
                print(f"{'Attribute':<40} {'Parent':<25} {'Match In'}")
                print(f"{'-'*40} {'-'*25} {'-'*15}")
                for r in results:
                    print(f"{r['name']:<40} {r['parent']:<25} {r['match_in']}")
                print(f"\n{len(results)} matches")
    elif args.command == "required":
        comp_name, attrs = dm.attributes(args.component)
        required = [a for a in attrs if a["required"]]
        if args.format == "json":
            print(json.dumps({"component": comp_name, "required_attributes": required}, indent=2))
        else:
            optional = [a for a in attrs if not a["required"]]
            print(f"Component: {comp_name}")
            print(f"Required: {len(required)}, Optional: {len(optional)}, Total: {len(attrs)}")
            print("\nRequired attributes:")
            for attr in required:
                vr = attr["validation_rules"]
                suffix = f"  [{vr}]" if vr else ""
                print(f"  {attr['name']}{suffix}")
    elif args.command == "deps":
        chain = dm.deps(args.component)
        if args.format == "json":
            print(json.dumps(chain, indent=2))
        else:
            print(_format_deps_text(chain))
