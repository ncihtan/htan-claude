#!/usr/bin/env python3
"""Download HTAN controlled-access data from CRDC/Gen3 via DRS URIs.

Requires: pip install gen3
Auth: Gen3 credentials JSON from CRDC portal (dbGaP authorization required)

Usage:
    python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid-here" --credentials creds.json
    python3 scripts/htan_gen3.py download --manifest drs_uris.txt --credentials creds.json
    python3 scripts/htan_gen3.py resolve "drs://dg.4DFC/guid-here" --credentials creds.json
    python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid-here" --dry-run
"""

import argparse
import json
import os
import re
import sys
import urllib.request


GEN3_ENDPOINT = "https://nci-crdc.datacommons.io"
# Two DRS URI formats seen in the wild:
#   drs://dg.4DFC/<guid>
#   drs://nci-crdc.datacommons.io/dg.4DFC/<guid>
DRS_URI_PATTERN = re.compile(r"^drs://(dg\.4DFC|nci-crdc\.datacommons\.io/dg\.4DFC)/[a-zA-Z0-9._/\-]+$")
GUID_PATTERN = re.compile(r"^[a-zA-Z0-9._/\-]+$")


def validate_drs_uri(uri):
    """Validate DRS URI format."""
    if not DRS_URI_PATTERN.match(uri):
        print(f"Error: Invalid DRS URI '{uri}'.", file=sys.stderr)
        print(f"Expected format: drs://dg.4DFC/<guid>", file=sys.stderr)
        sys.exit(1)
    return uri


def validate_credentials_file(path):
    """Validate that credentials file exists and is valid JSON."""
    if not os.path.exists(path):
        print(f"Error: Credentials file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path) as f:
            data = json.load(f)
        if "api_key" not in data or "key_id" not in data:
            print(
                f"Error: Credentials file missing 'api_key' or 'key_id' fields.",
                file=sys.stderr,
            )
            sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Credentials file is not valid JSON: {path}", file=sys.stderr)
        sys.exit(1)

    return path


def extract_guid(drs_uri):
    """Extract GUID from a DRS URI.

    Handles both formats:
      drs://dg.4DFC/<guid>
      drs://nci-crdc.datacommons.io/dg.4DFC/<guid>
    """
    for prefix in ("drs://nci-crdc.datacommons.io/dg.4DFC/", "drs://dg.4DFC/"):
        if drs_uri.startswith(prefix):
            return drs_uri[len(prefix):]
    return drs_uri


def find_credentials():
    """Find Gen3 credentials file from environment or default location."""
    env_path = os.environ.get("GEN3_API_KEY")
    if env_path:
        path = os.path.expanduser(env_path)
        if os.path.exists(path):
            return path

    default_path = os.path.expanduser("~/.gen3/credentials.json")
    if os.path.exists(default_path):
        return default_path

    return None


def get_gen3_auth(credentials_file=None):
    """Create Gen3 authentication provider."""
    try:
        from gen3.auth import Gen3Auth
    except ImportError:
        print("Error: gen3 package not installed. Run: pip install gen3", file=sys.stderr)
        sys.exit(1)

    if credentials_file:
        creds_path = validate_credentials_file(credentials_file)
    else:
        creds_path = find_credentials()
        if not creds_path:
            print("Error: No Gen3 credentials found.", file=sys.stderr)
            print("Provide --credentials, set GEN3_API_KEY, or place at ~/.gen3/credentials.json", file=sys.stderr)
            print("See references/authentication_guide.md for setup instructions.", file=sys.stderr)
            sys.exit(1)

    print(f"Using credentials: {creds_path}", file=sys.stderr)
    try:
        auth = Gen3Auth(endpoint=GEN3_ENDPOINT, refresh_file=creds_path)
        return auth
    except Exception as e:
        print(f"Error: Gen3 authentication failed: {e}", file=sys.stderr)
        sys.exit(1)


def get_file_client(auth):
    """Create Gen3 file client."""
    from gen3.file import Gen3File

    return Gen3File(endpoint=GEN3_ENDPOINT, auth_provider=auth)


def resolve_drs_uri(file_client, guid, protocol="s3"):
    """Resolve a DRS GUID to a signed download URL."""
    try:
        url_info = file_client.get_presigned_url(guid, protocol=protocol)
        if "url" not in url_info:
            print(f"Error: Could not resolve GUID {guid}. Response: {url_info}", file=sys.stderr)
            sys.exit(1)
        return url_info["url"]
    except Exception as e:
        print(f"Error: Failed to resolve GUID {guid}: {e}", file=sys.stderr)
        sys.exit(1)


def download_file(url, output_path):
    """Download a file from a signed URL with progress reporting."""
    print(f"Downloading to {output_path}...", file=sys.stderr)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            total_size = response.headers.get("Content-Length")
            total_size = int(total_size) if total_size else None

            downloaded = 0
            with open(output_path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        pct = downloaded * 100 / total_size
                        print(
                            f"\r  {downloaded:,} / {total_size:,} bytes ({pct:.1f}%)",
                            end="",
                            file=sys.stderr,
                        )
                    else:
                        print(f"\r  {downloaded:,} bytes", end="", file=sys.stderr)
            print(file=sys.stderr)  # newline after progress

        print(f"Downloaded: {output_path}", file=sys.stderr)
        return output_path
    except Exception as e:
        print(f"\nError: Download failed: {e}", file=sys.stderr)
        # Clean up partial download
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(1)


def read_manifest(path):
    """Read DRS URIs from a manifest file (one per line)."""
    if not os.path.exists(path):
        print(f"Error: Manifest file not found: {path}", file=sys.stderr)
        sys.exit(1)

    uris = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if not DRS_URI_PATTERN.match(line):
                print(
                    f"Error: Invalid DRS URI on line {line_num}: {line}",
                    file=sys.stderr,
                )
                sys.exit(1)
            uris.append(line)

    if not uris:
        print("Error: No DRS URIs found in manifest file.", file=sys.stderr)
        sys.exit(1)

    print(f"Read {len(uris)} DRS URIs from {path}", file=sys.stderr)
    return uris


def cmd_download(args):
    """Handle the 'download' subcommand."""
    # Collect URIs
    if args.manifest:
        uris = read_manifest(args.manifest)
    elif args.drs_uri:
        validate_drs_uri(args.drs_uri)
        uris = [args.drs_uri]
    else:
        print("Error: Provide a DRS URI or --manifest file.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Dry run — would download {len(uris)} file(s):", file=sys.stderr)
        for uri in uris:
            guid = extract_guid(uri)
            print(f"  {uri} (GUID: {guid})", file=sys.stderr)
        print(f"Output directory: {args.output_dir}", file=sys.stderr)
        print(f"Protocol: {args.protocol}", file=sys.stderr)
        return

    # Authenticate
    auth = get_gen3_auth(args.credentials)
    file_client = get_file_client(auth)

    # Validate output directory
    output_dir = os.path.realpath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Download each URI
    downloaded = []
    for i, uri in enumerate(uris, 1):
        guid = extract_guid(uri)
        print(f"\n[{i}/{len(uris)}] Resolving {uri}...", file=sys.stderr)

        signed_url = resolve_drs_uri(file_client, guid, protocol=args.protocol)

        # Derive filename from GUID
        filename = guid.replace("/", "_")
        output_path = os.path.join(output_dir, filename)

        if os.path.exists(output_path):
            print(f"  Skipping (already exists): {output_path}", file=sys.stderr)
            downloaded.append(output_path)
            continue

        path = download_file(signed_url, output_path)
        downloaded.append(path)

    print(f"\nDownloaded {len(downloaded)} file(s) to {output_dir}", file=sys.stderr)
    for path in downloaded:
        print(path)


def cmd_resolve(args):
    """Handle the 'resolve' subcommand."""
    validate_drs_uri(args.drs_uri)
    guid = extract_guid(args.drs_uri)

    if args.dry_run:
        print(f"Dry run — would resolve:", file=sys.stderr)
        print(f"  DRS URI: {args.drs_uri}", file=sys.stderr)
        print(f"  GUID: {guid}", file=sys.stderr)
        print(f"  Endpoint: {GEN3_ENDPOINT}", file=sys.stderr)
        return

    auth = get_gen3_auth(args.credentials)
    file_client = get_file_client(auth)

    print(f"Resolving {args.drs_uri}...", file=sys.stderr)
    signed_url = resolve_drs_uri(file_client, guid, protocol=args.protocol)
    print(signed_url)


def main():
    parser = argparse.ArgumentParser(
        description="Download HTAN controlled-access data from CRDC/Gen3",
        epilog="Examples:\n"
        '  python3 scripts/htan_gen3.py download "drs://dg.4DFC/guid" --credentials creds.json\n'
        "  python3 scripts/htan_gen3.py download --manifest uris.txt --credentials creds.json\n"
        '  python3 scripts/htan_gen3.py resolve "drs://dg.4DFC/guid" --credentials creds.json\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # download subcommand
    sp_dl = subparsers.add_parser("download", help="Download files by DRS URI")
    sp_dl.add_argument("drs_uri", nargs="?", help="DRS URI (e.g., drs://dg.4DFC/guid)")
    sp_dl.add_argument("--manifest", "-m", help="File with DRS URIs (one per line)")
    sp_dl.add_argument("--credentials", "-c", help="Path to Gen3 credentials JSON")
    sp_dl.add_argument(
        "--output-dir", "-o", default=".", help="Output directory (default: current directory)"
    )
    sp_dl.add_argument(
        "--protocol", choices=["s3", "gs"], default="s3", help="Download protocol (default: s3)"
    )
    sp_dl.add_argument("--dry-run", action="store_true", help="Validate inputs without downloading")

    # resolve subcommand
    sp_res = subparsers.add_parser("resolve", help="Resolve DRS URI to signed download URL")
    sp_res.add_argument("drs_uri", help="DRS URI to resolve")
    sp_res.add_argument("--credentials", "-c", help="Path to Gen3 credentials JSON")
    sp_res.add_argument(
        "--protocol", choices=["s3", "gs"], default="s3", help="Download protocol (default: s3)"
    )
    sp_res.add_argument("--dry-run", action="store_true", help="Validate inputs without resolving")

    args = parser.parse_args()
    args.func = {"download": cmd_download, "resolve": cmd_resolve}[args.command]
    args.func(args)


if __name__ == "__main__":
    main()
