#!/usr/bin/env python3
"""Download HTAN open-access files from Synapse by entity ID.

File discovery is handled by BigQuery + htan_file_mapping.py. This script
only needs to download files given their Synapse entity ID (e.g. syn26535909).

Requires: pip install synapseclient
Auth: Set SYNAPSE_AUTH_TOKEN env var or configure ~/.synapseConfig

Usage:
    python3 scripts/htan_synapse.py download syn26535909
    python3 scripts/htan_synapse.py download syn26535909 --output-dir ./data
    python3 scripts/htan_synapse.py download syn26535909 --dry-run
"""

import argparse
import os
import re
import sys


SYNAPSE_ID_PATTERN = re.compile(r"^syn\d+$")


def validate_synapse_id(synapse_id):
    """Validate Synapse ID format (synNNNN...)."""
    if not SYNAPSE_ID_PATTERN.match(synapse_id):
        print(f"Error: Invalid Synapse ID '{synapse_id}'. Must match 'synNNNNNN'.", file=sys.stderr)
        sys.exit(1)
    return synapse_id


def validate_output_dir(path):
    """Validate and resolve output directory path."""
    resolved = os.path.realpath(path)
    if not os.path.isabs(resolved):
        print(f"Error: Could not resolve output directory to absolute path.", file=sys.stderr)
        sys.exit(1)
    return resolved


def get_synapse_client():
    """Create and authenticate a Synapse client."""
    try:
        import synapseclient
    except ImportError:
        print("Error: synapseclient not installed. Run: pip install synapseclient", file=sys.stderr)
        sys.exit(1)

    syn = synapseclient.Synapse()
    try:
        syn.login(silent=True)
    except synapseclient.core.exceptions.SynapseAuthenticationError:
        print("Error: Synapse authentication failed.", file=sys.stderr)
        print("Set SYNAPSE_AUTH_TOKEN or configure ~/.synapseConfig", file=sys.stderr)
        print("See references/authentication_guide.md for setup instructions.", file=sys.stderr)
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


def download_file(syn, synapse_id, output_dir, dry_run=False):
    """Download a file from Synapse by entity ID."""
    from synapseclient.operations import get as syn_get
    from synapseclient.operations.factory_operations import FileOptions

    if dry_run:
        print(f"Fetching metadata for {synapse_id}...", file=sys.stderr)
        try:
            entity = syn_get(
                synapse_id,
                file_options=FileOptions(download_file=False),
                synapse_client=syn,
            )
        except Exception as e:
            print(f"Error: Could not access {synapse_id}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Dry run — {entity.name}", file=sys.stderr)
        if hasattr(entity, "content_size") and entity.content_size:
            print(f"  Size: {entity.content_size} bytes", file=sys.stderr)
        print(f"  Would download to: {output_dir}", file=sys.stderr)
        return

    print(f"Downloading {synapse_id} to {output_dir}...", file=sys.stderr)
    try:
        entity = syn_get(
            synapse_id,
            file_options=FileOptions(download_file=True, download_location=output_dir),
            synapse_client=syn,
        )
    except Exception as e:
        print(f"Error: Could not download {synapse_id}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Downloaded: {entity.path}", file=sys.stderr)
    print(entity.path)


def main():
    parser = argparse.ArgumentParser(
        description="Download HTAN open-access files from Synapse",
        epilog="Examples:\n"
        "  python3 scripts/htan_synapse.py download syn26535909\n"
        "  python3 scripts/htan_synapse.py download syn26535909 --output-dir ./data\n"
        "  python3 scripts/htan_synapse.py download syn26535909 --dry-run\n"
        "\n"
        "To find entity IDs, use BigQuery + file mapping:\n"
        "  python3 scripts/htan_bigquery.py query \"Find scRNA-seq for breast cancer\"\n"
        "  python3 scripts/htan_file_mapping.py lookup HTA9_1_19512 --format json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=["download"], help="Download a file from Synapse")
    parser.add_argument("synapse_id", help="Synapse entity ID (e.g., syn26535909)")
    parser.add_argument(
        "--output-dir", "-o", default=".", help="Output directory (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show file metadata without downloading"
    )

    args = parser.parse_args()
    validate_synapse_id(args.synapse_id)

    output_dir = validate_output_dir(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    syn = get_synapse_client()
    download_file(syn, args.synapse_id, output_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
