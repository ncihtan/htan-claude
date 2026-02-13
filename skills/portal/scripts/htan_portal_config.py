#!/usr/bin/env python3
"""Shared configuration loader for HTAN portal ClickHouse credentials.

Reads credentials from ~/.config/htan-skill/portal.json, which is populated
by `htan_setup.py init-portal` (downloads from Synapse).

Stdlib only — no third-party imports. This keeps htan_portal.py stdlib-pure.
"""

import json
import os
import sys

CONFIG_DIR = os.path.expanduser("~/.config/htan-skill")
CONFIG_PATH = os.path.join(CONFIG_DIR, "portal.json")

REQUIRED_KEYS = ("host", "port", "user", "password")


def load_portal_config(config_path=None):
    """Load portal credentials from the config file.

    Args:
        config_path: Override path to config JSON. Defaults to CONFIG_PATH.

    Returns:
        Dict with keys: host, port, user, password, and optionally default_database.

    Raises:
        SystemExit if the config file is missing or invalid.
    """
    path = config_path or CONFIG_PATH

    if not os.path.exists(path):
        print("Error: Portal credentials not configured.", file=sys.stderr)
        print(f"Expected config at: {path}", file=sys.stderr)
        print("", file=sys.stderr)
        print("To set up portal access:", file=sys.stderr)
        print("  1. Join the HTAN Claude Skill Users team: https://www.synapse.org/Team:3574960", file=sys.stderr)
        print("  2. Run: python3 scripts/htan_setup.py init-portal", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "r") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        print("Re-run: python3 scripts/htan_setup.py init-portal --force", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Cannot read {path} — check file permissions.", file=sys.stderr)
        sys.exit(1)

    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        print(f"Error: Config file {path} missing required keys: {', '.join(missing)}", file=sys.stderr)
        print("Re-run: python3 scripts/htan_setup.py init-portal --force", file=sys.stderr)
        sys.exit(1)

    return cfg


def get_clickhouse_url(cfg):
    """Build the ClickHouse HTTP URL from config.

    Args:
        cfg: Config dict from load_portal_config().

    Returns:
        URL string like 'https://host:port/'
    """
    return f"https://{cfg['host']}:{cfg['port']}/"


def get_default_database(cfg):
    """Get the default database name from config, or None if auto-discover.

    Args:
        cfg: Config dict from load_portal_config().

    Returns:
        Database name string, or None if set to 'auto' (triggers discovery).
    """
    db = cfg.get("default_database", "auto")
    if db == "auto" or not db:
        return None
    return db
