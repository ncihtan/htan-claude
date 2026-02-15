"""Unified CLI for HTAN tools.

Entry point: `htan` command (installed via pip install htan).

Subcommands:
    htan query portal ...    — Portal ClickHouse queries
    htan query bq ...        — BigQuery queries
    htan download synapse ... — Synapse open-access downloads
    htan download gen3 ...   — Gen3/CRDC controlled-access downloads
    htan pubs ...            — PubMed publication search
    htan model ...           — HTAN data model queries
    htan files ...           — File ID to download coordinate mapping
    htan config ...          — Credential status and setup
"""

import sys


def main():
    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(1)

    command = sys.argv[1]
    rest = sys.argv[2:]

    if command in ("-h", "--help", "help"):
        _print_usage()
        return

    if command == "--version":
        from htan import __version__
        print(f"htan {__version__}")
        return

    if command == "init":
        from htan.init import cli_main
        cli_main(rest)
    elif command == "query":
        _dispatch_query(rest)
    elif command == "download":
        _dispatch_download(rest)
    elif command == "pubs":
        from htan.pubs import cli_main
        cli_main(rest)
    elif command == "model":
        from htan.model import cli_main
        cli_main(rest)
    elif command == "files":
        from htan.files import cli_main
        cli_main(rest)
    elif command == "config":
        _dispatch_config(rest)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        _print_usage()
        sys.exit(1)


def _dispatch_query(args):
    if not args:
        print("Usage: htan query {portal,bq} ...", file=sys.stderr)
        sys.exit(1)

    backend = args[0]
    rest = args[1:]

    if backend == "portal":
        from htan.query.portal import cli_main
        cli_main(rest)
    elif backend == "bq":
        from htan.query.bq import cli_main
        cli_main(rest)
    else:
        print(f"Unknown query backend: {backend}. Use 'portal' or 'bq'.", file=sys.stderr)
        sys.exit(1)


def _dispatch_download(args):
    if not args:
        print("Usage: htan download {synapse,gen3} ...", file=sys.stderr)
        sys.exit(1)

    backend = args[0]
    rest = args[1:]

    if backend == "synapse":
        from htan.download.synapse import cli_main
        cli_main(rest)
    elif backend == "gen3":
        from htan.download.gen3 import cli_main
        cli_main(rest)
    else:
        print(f"Unknown download backend: {backend}. Use 'synapse' or 'gen3'.", file=sys.stderr)
        sys.exit(1)


def _dispatch_config(args):
    import json
    from htan.config import check_setup

    if args and args[0] in ("-h", "--help"):
        print("Usage: htan config check")
        print("       htan config init-portal")
        return

    command = args[0] if args else "check"

    if command == "check":
        status = check_setup()
        print(json.dumps({"ok": True, "status": status}, indent=2))
    elif command == "init-portal":
        print("Deprecated: use 'htan init portal' instead.", file=sys.stderr)
        from htan.init import cli_main as init_main
        init_main(["portal"])
    else:
        print(f"Unknown config command: {command}", file=sys.stderr)
        sys.exit(1)


def _print_usage():
    print("""Usage: htan <command> [args...]

Commands:
  init                Interactive setup wizard (configure credentials)
  query portal ...    Query HTAN portal ClickHouse database
  query bq ...        Query HTAN metadata in ISB-CGC BigQuery
  download synapse .. Download open-access files from Synapse
  download gen3 ...   Download controlled-access files from Gen3/CRDC
  pubs ...            Search HTAN publications on PubMed
  model ...           Query HTAN data model (components, attributes, valid values)
  files ...           Map HTAN file IDs to download coordinates
  config check        Check credential configuration status

Options:
  --help              Show this help message
  --version           Show version

Run 'htan <command> --help' for command-specific help.""")
