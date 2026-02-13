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


class ConfigError(Exception):
    """Portal configuration error — credentials missing or invalid."""
    pass


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
        raise ConfigError(
            "Portal credentials not configured.\n"
            f"Expected config at: {path}\n\n"
            "To set up portal access:\n"
            "  1. Join the HTAN Claude Skill Users team: https://www.synapse.org/Team:3574960\n"
            "  2. Run: python3 scripts/htan_setup.py init-portal"
        )

    try:
        with open(path, "r") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Invalid JSON in {path}: {e}\n"
            "Re-run: python3 scripts/htan_setup.py init-portal --force"
        )
    except PermissionError:
        raise ConfigError(f"Cannot read {path} — check file permissions.")

    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ConfigError(
            f"Config file {path} missing required keys: {', '.join(missing)}\n"
            "Re-run: python3 scripts/htan_setup.py init-portal --force"
        )

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
