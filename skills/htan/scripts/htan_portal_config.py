#!/usr/bin/env python3
"""Shared configuration loader for HTAN portal ClickHouse credentials.

3-tier credential resolution (all stdlib):
  1. Env var: HTAN_PORTAL_CREDENTIALS (JSON string) — for Cowork
  2. OS Keychain: macOS `security` / Linux `secret-tool` — for local
  3. Config file: ~/.config/htan-skill/portal.json — backward compat

Stdlib only — no third-party imports. This keeps htan_portal.py stdlib-pure.
"""

import json
import os
import platform
import subprocess
import sys

CONFIG_DIR = os.path.expanduser("~/.config/htan-skill")
CONFIG_PATH = os.path.join(CONFIG_DIR, "portal.json")

REQUIRED_KEYS = ("host", "port", "user", "password")

KEYCHAIN_SERVICE = "htan-portal"
KEYCHAIN_ACCOUNT = "htan"


class ConfigError(Exception):
    """Portal configuration error — credentials missing or invalid."""
    pass


def _validate_config(cfg):
    """Validate that a config dict has all required keys. Returns list of missing keys."""
    return [k for k in REQUIRED_KEYS if k not in cfg]


def _load_from_env():
    """Load credentials from HTAN_PORTAL_CREDENTIALS env var (JSON string).

    Returns:
        Dict with credentials, or None if env var not set or invalid.
    """
    raw = os.environ.get("HTAN_PORTAL_CREDENTIALS")
    if not raw:
        return None
    try:
        cfg = json.loads(raw)
        if _validate_config(cfg):
            return None
        return cfg
    except (json.JSONDecodeError, TypeError):
        return None


def _load_from_keychain():
    """Load credentials from OS keychain (macOS `security` / Linux `secret-tool`).

    Returns:
        Dict with credentials, or None if not found or unsupported platform.
    """
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["security", "find-generic-password",
                 "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return None
            raw = result.stdout.strip()
        elif system == "Linux":
            result = subprocess.run(
                ["secret-tool", "lookup",
                 "service", KEYCHAIN_SERVICE, "account", KEYCHAIN_ACCOUNT],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return None
            raw = result.stdout.strip()
        else:
            return None

        if not raw:
            return None
        cfg = json.loads(raw)
        if _validate_config(cfg):
            return None
        return cfg
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError,
            OSError):
        return None


def _load_from_file(config_path=None):
    """Load credentials from config file.

    Returns:
        Dict with credentials, or None if file missing or invalid.
    """
    path = config_path or CONFIG_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            cfg = json.load(f)
        if _validate_config(cfg):
            return None
        return cfg
    except (json.JSONDecodeError, PermissionError, OSError):
        return None


def save_to_keychain(creds):
    """Store credentials in OS keychain.

    Args:
        creds: Dict with portal credentials.

    Returns:
        True if stored successfully, False otherwise.
    """
    system = platform.system()
    creds_json = json.dumps(creds)
    try:
        if system == "Darwin":
            subprocess.run(
                ["security", "add-generic-password",
                 "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT,
                 "-w", creds_json, "-U"],
                check=True, capture_output=True, text=True, timeout=10,
            )
            return True
        elif system == "Linux":
            subprocess.run(
                ["secret-tool", "store",
                 "--label=HTAN Portal",
                 "service", KEYCHAIN_SERVICE, "account", KEYCHAIN_ACCOUNT],
                input=creds_json.encode(), check=True,
                capture_output=True, timeout=10,
            )
            return True
        else:
            return False
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError):
        return False


def detect_source():
    """Detect which credential source would be used.

    Returns:
        "env" if HTAN_PORTAL_CREDENTIALS is set and valid,
        "keychain" if OS keychain has valid credentials,
        "file" if config file exists and is valid,
        None if no source is available.
    """
    if _load_from_env() is not None:
        return "env"
    if _load_from_keychain() is not None:
        return "keychain"
    if _load_from_file() is not None:
        return "file"
    return None


def load_portal_config(config_path=None):
    """Load portal credentials using 3-tier resolution.

    Resolution order:
      1. HTAN_PORTAL_CREDENTIALS env var (JSON string)
      2. OS Keychain (macOS security / Linux secret-tool)
      3. Config file (~/.config/htan-skill/portal.json)

    Args:
        config_path: Override path for config file (tier 3 only).

    Returns:
        Dict with keys: host, port, user, password, and optionally default_database.

    Raises:
        ConfigError if no valid credentials found in any tier.
    """
    # Tier 1: Environment variable
    cfg = _load_from_env()
    if cfg is not None:
        return cfg

    # Tier 2: OS Keychain
    cfg = _load_from_keychain()
    if cfg is not None:
        return cfg

    # Tier 3: Config file
    cfg = _load_from_file(config_path)
    if cfg is not None:
        return cfg

    raise ConfigError(
        "Portal credentials not configured.\n\n"
        "Options:\n"
        "  1. Run /htan:setup to auto-configure (recommended)\n"
        "  2. Set HTAN_PORTAL_CREDENTIALS env var (JSON string, for Cowork)\n"
        "  3. Create ~/.config/htan-skill/portal.json manually\n\n"
        "Portal credentials require HTAN Claude Skill Users team membership:\n"
        "  https://www.synapse.org/Team:3574960"
    )


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
