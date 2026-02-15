"""Download HTAN open-access files from Synapse by entity ID.

Requires: pip install htan[synapse]

Usage as library:
    from htan.download.synapse import download
    path = download("syn26535909", output_dir="./data")

Usage as CLI:
    htan download synapse syn26535909
    htan download synapse syn26535909 --output-dir ./data --dry-run
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
        print("Error: synapseclient not installed. Run: pip install htan[synapse]", file=sys.stderr)
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


def download(synapse_id, output_dir=".", dry_run=False):
    """Download a file from Synapse by entity ID.

    Args:
        synapse_id: Synapse entity ID (e.g., "syn26535909").
        output_dir: Directory to download to (default: current dir).
        dry_run: If True, only fetch metadata without downloading.

    Returns:
        Local file path of downloaded file (or None for dry-run).
    """
    _validate_synapse_id(synapse_id)
    output_dir = os.path.realpath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    syn = _get_synapse_client()

    from synapseclient.operations import get as syn_get
    from synapseclient.operations.factory_operations import FileOptions

    if dry_run:
        print(f"Fetching metadata for {synapse_id}...", file=sys.stderr)
        try:
            entity = syn_get(synapse_id, file_options=FileOptions(download_file=False), synapse_client=syn)
        except Exception as e:
            print(f"Error: Could not access {synapse_id}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Dry run — {entity.name}", file=sys.stderr)
        if hasattr(entity, "content_size") and entity.content_size:
            print(f"  Size: {entity.content_size} bytes", file=sys.stderr)
        print(f"  Would download to: {output_dir}", file=sys.stderr)
        return None

    print(f"Downloading {synapse_id} to {output_dir}...", file=sys.stderr)
    try:
        entity = syn_get(synapse_id, file_options=FileOptions(download_file=True, download_location=output_dir), synapse_client=syn)
    except Exception as e:
        print(f"Error: Could not download {synapse_id}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Downloaded: {entity.path}", file=sys.stderr)
    return entity.path


# --- CLI ---

def cli_main(argv=None):
    """CLI entry point for Synapse downloads."""
    parser = argparse.ArgumentParser(
        description="Download HTAN open-access files from Synapse",
        epilog="Examples:\n"
        "  htan download synapse syn26535909\n"
        "  htan download synapse syn26535909 --output-dir ./data\n"
        "  htan download synapse syn26535909 --dry-run\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("synapse_id", help="Synapse entity ID (e.g., syn26535909)")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show metadata without downloading")

    args = parser.parse_args(argv)
    path = download(args.synapse_id, output_dir=args.output_dir, dry_run=args.dry_run)
    if path:
        print(path)
