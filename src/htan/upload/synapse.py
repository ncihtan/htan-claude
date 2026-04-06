"""Upload files to Synapse by parent entity ID.

Requires: synapseclient (included in htan core dependencies)

Usage as library:
    from htan.upload.synapse import upload, upload_bulk

    # Single file
    entity_id = upload("./results.csv", parent_id="syn12345678")

    # Single file with annotations
    entity_id = upload(
        "./results.csv",
        parent_id="syn12345678",
        annotations={"assay": "scRNA-seq", "atlas": "HTAN_OHSU"},
    )

    # Bulk upload
    ids = upload_bulk(["./a.csv", "./b.csv"], parent_id="syn12345678")

Usage as CLI:
    htan upload synapse file ./results.csv --parent syn12345678
    htan upload synapse file ./results.csv --parent syn12345678 --annotation assay=scRNA-seq
    htan upload synapse bulk ./data/ --parent syn12345678
    htan upload synapse bulk ./manifest.txt --parent syn12345678 --dry-run
"""

import argparse
import os
import re
import sys


SYNAPSE_ID_PATTERN = re.compile(r"^syn\d+$")


def _validate_synapse_id(synapse_id):
    if not SYNAPSE_ID_PATTERN.match(synapse_id):
        raise ValueError(f"Invalid Synapse ID '{synapse_id}'. Must match 'synNNNNNN'.")
    return synapse_id


def _get_synapse_client():
    try:
        import synapseclient
    except ImportError:
        print("Error: synapseclient not installed. Run: pip install htan", file=sys.stderr)
        sys.exit(1)

    syn = synapseclient.Synapse()
    try:
        syn.login(silent=True)
    except synapseclient.core.exceptions.SynapseAuthenticationError:
        print("Error: Synapse authentication failed.", file=sys.stderr)
        print("Set SYNAPSE_AUTH_TOKEN or configure ~/.synapseConfig", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not connect to Synapse: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        from synapseclient.models import UserProfile
        profile = UserProfile.from_id(syn.credentials.owner_id)
        print(f"Authenticated as: {profile.username}", file=sys.stderr)
    except Exception:
        print("Authenticated.", file=sys.stderr)
    return syn


def _parse_annotations(annotation_list):
    """Parse a list of 'key=value' strings into a dict.

    Args:
        annotation_list: List of strings like ["assay=scRNA-seq", "batch=2024Q1"].

    Returns:
        Dict of {key: value} strings.

    Raises:
        ValueError: If any item is not in 'key=value' format.
    """
    out = {}
    for item in annotation_list:
        if "=" not in item:
            raise ValueError(f"Annotation must be key=value, got: {item!r}")
        k, _, v = item.partition("=")
        out[k.strip()] = v.strip()
    return out


def upload(file_path, parent_id, annotations=None, dry_run=False):
    """Upload a single file to Synapse.

    Args:
        file_path: Local path to the file to upload.
        parent_id: Synapse entity ID of the parent project/folder (e.g., "syn12345678").
        annotations: Optional dict of key-value metadata to attach to the entity.
        dry_run: If True, only validate and print metadata without uploading.

    Returns:
        Synapse entity ID of the uploaded file (str), or None for dry-run.

    Raises:
        ValueError: If parent_id is not a valid Synapse ID.
        FileNotFoundError: If file_path does not exist.
    """
    _validate_synapse_id(parent_id)

    file_path = os.path.realpath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not os.path.isfile(file_path):
        raise ValueError(f"Path is not a file: {file_path}")

    if annotations is not None and not isinstance(annotations, dict):
        raise ValueError("annotations must be a dict")

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    if dry_run:
        print(f"Dry run — would upload: {file_name}", file=sys.stderr)
        print(f"  Size:   {file_size} bytes", file=sys.stderr)
        print(f"  Parent: {parent_id}", file=sys.stderr)
        if annotations:
            for k, v in annotations.items():
                print(f"  Annotation: {k}={v}", file=sys.stderr)
        return None

    syn = _get_synapse_client()

    print(f"Uploading {file_name} ({file_size} bytes) to {parent_id}...", file=sys.stderr)
    try:
        from synapseclient.models import File as SynapseFile

        f = SynapseFile(path=file_path, parent_id=parent_id)
        if annotations:
            f.annotations = annotations
        f = f.store(synapse_client=syn)
    except Exception as e:
        print(f"Error: Upload failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Uploaded: {f.id} ({file_name})", file=sys.stderr)
    return f.id


def upload_bulk(paths, parent_id, annotations=None, dry_run=False):
    """Upload multiple files to Synapse.

    Args:
        paths: List of local file paths to upload.
        parent_id: Synapse entity ID of the parent project/folder.
        annotations: Optional dict of key-value metadata to attach to each entity.
        dry_run: If True, only validate and print metadata without uploading.

    Returns:
        List of Synapse entity IDs (str) or Nones for dry-run, one per path.
    """
    _validate_synapse_id(parent_id)

    results = []
    total = len(paths)

    if total == 0:
        print("Warning: No files to upload.", file=sys.stderr)
        return results

    # Validate all paths before uploading anything
    for path in paths:
        real = os.path.realpath(path)
        if not os.path.exists(real):
            raise FileNotFoundError(f"File not found: {real}")
        if not os.path.isfile(real):
            raise ValueError(f"Path is not a file: {real}")

    syn = None if dry_run else _get_synapse_client()

    for i, path in enumerate(paths, 1):
        file_name = os.path.basename(path)
        file_size = os.path.getsize(path)
        print(f"[{i}/{total}] {file_name} ({file_size} bytes)", file=sys.stderr)

        if dry_run:
            print(f"  Dry run — would upload to {parent_id}", file=sys.stderr)
            if annotations:
                for k, v in annotations.items():
                    print(f"  Annotation: {k}={v}", file=sys.stderr)
            results.append(None)
            continue

        try:
            from synapseclient.models import File as SynapseFile

            f = SynapseFile(path=os.path.realpath(path), parent_id=parent_id)
            if annotations:
                f.annotations = annotations
            f = f.store(synapse_client=syn)
            print(f"  Uploaded: {f.id}", file=sys.stderr)
            results.append(f.id)
        except Exception as e:
            print(f"  Error: Upload failed for {file_name}: {e}", file=sys.stderr)
            results.append(None)

    return results


def _collect_paths_from_target(target):
    """Resolve a directory or manifest file to a list of file paths.

    Args:
        target: Path to a directory or a .txt/.csv manifest file.

    Returns:
        List of file paths.

    Raises:
        ValueError: If target does not exist or is not a directory/manifest file.
    """
    target = os.path.realpath(target)
    if not os.path.exists(target):
        raise ValueError(f"Target does not exist: {target}")

    if os.path.isdir(target):
        paths = [
            os.path.join(target, name)
            for name in sorted(os.listdir(target))
            if os.path.isfile(os.path.join(target, name))
        ]
        if not paths:
            raise ValueError(f"Directory contains no files: {target}")
        return paths

    if os.path.isfile(target):
        ext = os.path.splitext(target)[1].lower()
        if ext not in (".txt", ".csv"):
            raise ValueError(
                f"Manifest must be a .txt or .csv file (one path per line), got: {target}"
            )
        with open(target) as fh:
            paths = [line.strip() for line in fh if line.strip()]
        if not paths:
            raise ValueError(f"Manifest file is empty: {target}")
        return paths

    raise ValueError(f"Target must be a directory or manifest file: {target}")


# --- CLI ---

def cli_main(argv=None):
    """CLI entry point for Synapse uploads."""
    parser = argparse.ArgumentParser(
        prog="htan upload synapse",
        description="Upload files to Synapse",
        epilog=(
            "Examples:\n"
            "  htan upload synapse file ./results.csv --parent syn12345678\n"
            "  htan upload synapse file ./results.csv --parent syn12345678 "
            "--annotation assay=scRNA-seq --annotation atlas=HTAN_OHSU\n"
            "  htan upload synapse bulk ./data/ --parent syn12345678\n"
            "  htan upload synapse bulk ./manifest.txt --parent syn12345678 --dry-run\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", metavar="{file,bulk}")

    # --- file subcommand ---
    file_parser = subparsers.add_parser("file", help="Upload a single file")
    file_parser.add_argument("path", help="Local file path to upload")
    file_parser.add_argument("--parent", "-p", required=True, help="Synapse parent entity ID (e.g., syn12345678)")
    file_parser.add_argument(
        "--annotation", "-a",
        metavar="KEY=VALUE",
        action="append",
        default=[],
        help="Annotation in key=value format; can be repeated",
    )
    file_parser.add_argument("--dry-run", action="store_true", help="Validate and preview without uploading")

    # --- bulk subcommand ---
    bulk_parser = subparsers.add_parser(
        "bulk",
        help="Upload all files in a directory or from a manifest (.txt/.csv, one path per line)",
    )
    bulk_parser.add_argument("target", help="Directory or manifest file path")
    bulk_parser.add_argument("--parent", "-p", required=True, help="Synapse parent entity ID (e.g., syn12345678)")
    bulk_parser.add_argument(
        "--annotation", "-a",
        metavar="KEY=VALUE",
        action="append",
        default=[],
        help="Annotation in key=value format; applied to every file; can be repeated",
    )
    bulk_parser.add_argument("--dry-run", action="store_true", help="Validate and preview without uploading")

    if not argv:
        parser.print_help()
        return

    args = parser.parse_args(argv)

    if args.subcommand is None:
        parser.print_help()
        return

    # Parse annotations
    try:
        annotations = _parse_annotations(args.annotation) if args.annotation else None
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.subcommand == "file":
        try:
            entity_id = upload(args.path, args.parent, annotations=annotations, dry_run=args.dry_run)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        if entity_id:
            print(entity_id)

    elif args.subcommand == "bulk":
        try:
            paths = _collect_paths_from_target(args.target)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        results = upload_bulk(paths, args.parent, annotations=annotations, dry_run=args.dry_run)
        for entity_id in results:
            if entity_id:
                print(entity_id)
