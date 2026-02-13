#!/usr/bin/env python3
"""Claude-safe HTAN setup: non-interactive, clean JSON output, no prompts.

Designed to be invoked by Claude via Bash. Three subcommands:

  check  — JSON status of all services (stdlib only, no imports needed)
  venv   — Create .venv and install deps using uv
  portal — Download portal credentials from Synapse (stdlib only — no venv needed!)

Usage:
    python3 htan_quicksetup.py check
    python3 htan_quicksetup.py venv [DIR]
    python3 htan_quicksetup.py portal
"""

import argparse
import configparser
import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


# --- Constants ---

PORTAL_CONFIG_PATH = os.path.expanduser("~/.config/htan-skill/portal.json")
PORTAL_CONFIG_DIR = os.path.expanduser("~/.config/htan-skill")
SYNAPSE_CONFIG_PATH = os.path.expanduser("~/.synapseConfig")
GEN3_CREDS_PATH = os.path.expanduser("~/.gen3/credentials.json")
BIGQUERY_ADC_PATH = os.path.expanduser(
    "~/.config/gcloud/application_default_credentials.json"
)

PORTAL_CREDENTIALS_SYNAPSE_ID = "syn73720854"
SYNAPSE_TEAM_ID = "3574960"

SYNAPSE_REPO_ENDPOINT = "https://repo-prod.prod.sagebase.org"
SYNAPSE_FILE_ENDPOINT = "https://file-prod.prod.sagebase.org"

ALL_PIP_PACKAGES = [
    "synapseclient",
    "gen3",
    "google-cloud-bigquery",
    "google-cloud-bigquery-storage",
    "pandas",
    "db-dtypes",
]


def _log(msg):
    """Print a message to stderr."""
    print(msg, file=sys.stderr)


def _result(data, exit_code=0):
    """Print JSON result to stdout and exit."""
    print(json.dumps(data, indent=2))
    sys.exit(exit_code)


def _error(message, details=None):
    """Print JSON error to stdout and exit with code 1."""
    err = {"ok": False, "error": message}
    if details:
        err["details"] = details
    _result(err, exit_code=1)


# --- Synapse REST API helpers (stdlib only) ---


def _read_synapse_token():
    """Read Synapse auth token from env var or ~/.synapseConfig.

    Returns:
        Token string, or None if not found.
    """
    # 1. Environment variable
    token = os.environ.get("SYNAPSE_AUTH_TOKEN")
    if token:
        return token.strip()
    # 2. Config file (INI format)
    if os.path.exists(SYNAPSE_CONFIG_PATH):
        config = configparser.ConfigParser()
        config.read(SYNAPSE_CONFIG_PATH)
        token = config.get("authentication", "authtoken", fallback=None)
        if token:
            return token.strip()
    return None


def _make_ssl_context():
    """Create an SSL context, trying certifi first."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _synapse_rest_get(path, token, endpoint=None):
    """GET request to Synapse REST API with bearer auth."""
    endpoint = endpoint or SYNAPSE_REPO_ENDPOINT
    req = urllib.request.Request(
        f"{endpoint}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    ctx = _make_ssl_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return json.loads(resp.read())


def _synapse_rest_post(path, body, token, endpoint=None):
    """POST request to Synapse REST API with bearer auth."""
    endpoint = endpoint or SYNAPSE_REPO_ENDPOINT
    req = urllib.request.Request(
        f"{endpoint}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    ctx = _make_ssl_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return json.loads(resp.read())


# --- check subcommand ---


def _detect_portal_source():
    """Detect which portal credential source is active.

    Returns one of: "env", "keychain", "file", or None.
    """
    # Import from sibling module
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    try:
        from htan_portal_config import detect_source
        return detect_source()
    except ImportError:
        # Fallback: just check file
        if os.path.exists(PORTAL_CONFIG_PATH):
            try:
                with open(PORTAL_CONFIG_PATH, "r") as f:
                    cfg = json.load(f)
                if all(k in cfg for k in ("host", "port", "user", "password")):
                    return "file"
            except (json.JSONDecodeError, PermissionError):
                pass
        return None


def cmd_check(args):
    """Check status of all services. Stdlib only — no third-party imports.

    Output: JSON to stdout with status of each service.
    """
    status = {}

    # Synapse auth
    has_synapse_env = bool(os.environ.get("SYNAPSE_AUTH_TOKEN"))
    has_synapse_config = os.path.exists(SYNAPSE_CONFIG_PATH)
    status["synapse"] = {
        "configured": has_synapse_env or has_synapse_config,
        "method": (
            "SYNAPSE_AUTH_TOKEN"
            if has_synapse_env
            else ("~/.synapseConfig" if has_synapse_config else None)
        ),
    }

    # Portal credentials (3-tier)
    portal_source = _detect_portal_source()
    status["portal"] = {
        "configured": portal_source is not None,
        "source": portal_source,
    }

    # Gen3/CRDC
    has_gen3_env = bool(
        os.environ.get("GEN3_API_KEY")
        and os.path.exists(os.environ.get("GEN3_API_KEY", ""))
    )
    has_gen3_config = os.path.exists(GEN3_CREDS_PATH)
    status["gen3"] = {
        "configured": has_gen3_env or has_gen3_config,
        "method": (
            "GEN3_API_KEY"
            if has_gen3_env
            else ("~/.gen3/credentials.json" if has_gen3_config else None)
        ),
    }

    # BigQuery
    has_bq_sa = bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        and os.path.exists(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""))
    )
    has_bq_adc = os.path.exists(BIGQUERY_ADC_PATH)
    status["bigquery"] = {
        "configured": has_bq_sa or has_bq_adc,
        "method": (
            "GOOGLE_APPLICATION_CREDENTIALS"
            if has_bq_sa
            else ("application_default_credentials" if has_bq_adc else None)
        ),
    }

    # uv available
    uv_path = shutil.which("uv")
    status["uv"] = {
        "available": uv_path is not None,
        "path": uv_path,
    }

    # Python version
    v = sys.version_info
    status["python"] = {
        "version": f"{v.major}.{v.minor}.{v.micro}",
        "sufficient": v >= (3, 10),
    }

    _result({"ok": True, "status": status})


# --- venv subcommand ---


def cmd_venv(args):
    """Create a virtual environment and install dependencies using uv.

    Creates .venv in the specified directory (default: current working directory).
    """
    target_dir = os.path.abspath(args.directory or os.getcwd())
    venv_path = os.path.join(target_dir, ".venv")

    # Check uv is available
    if not shutil.which("uv"):
        _error(
            "uv not found on PATH",
            "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh",
        )

    # Create venv if it doesn't exist (or --force)
    if os.path.exists(venv_path) and not args.force:
        _log(f"Virtual environment already exists: {venv_path}")
    else:
        _log(f"Creating virtual environment: {venv_path}")
        try:
            subprocess.run(
                ["uv", "venv", venv_path],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            _error(f"Failed to create venv: {e.stderr.strip()}")

    # Install dependencies
    _log("Installing dependencies...")
    python_path = os.path.join(venv_path, "bin", "python")
    try:
        cmd = ["uv", "pip", "install", "-q", "--python", python_path]
        cmd.extend(ALL_PIP_PACKAGES)
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        _error(f"Failed to install packages: {e.stderr.strip()[:200]}")

    _log("Dependencies installed successfully")
    _result({
        "ok": True,
        "venv_path": venv_path,
        "python_path": python_path,
        "packages": ALL_PIP_PACKAGES,
    })


# --- portal subcommand ---


def cmd_portal(args):
    """Download portal credentials from Synapse via stdlib HTTP.

    No venv or synapseclient needed. Uses the Synapse REST API directly.
    Auto-joins the HTAN Claude Skill Users team if possible.
    """
    # Check if config already exists (via any tier)
    if not args.force:
        portal_source = _detect_portal_source()
        if portal_source is not None:
            _result({
                "ok": True,
                "action": "already_configured",
                "source": portal_source,
            })

    # Read Synapse auth token
    token = _read_synapse_token()
    if not token:
        _error(
            "No Synapse auth token found",
            "Set SYNAPSE_AUTH_TOKEN env var or create ~/.synapseConfig with:\n"
            "  [authentication]\n"
            "  authtoken = <your-token>",
        )

    # Get user profile for team check
    user_id = ""
    try:
        profile = _synapse_rest_get("/repo/v1/userProfile", token)
        user_id = profile.get("ownerId", "")
        _log(f"Logged in as: {profile.get('userName', 'unknown')}")
    except Exception as e:
        _error(f"Synapse login failed: {e}")

    # Check team membership and auto-join if possible
    if user_id:
        try:
            membership = _synapse_rest_get(
                f"/repo/v1/team/{SYNAPSE_TEAM_ID}/member/{user_id}/membershipStatus",
                token,
            )
            is_member = membership.get("isMember", False)
            can_join = membership.get("canJoin", False)

            if not is_member and can_join:
                _log("Auto-joining HTAN Claude Skill Users team...")
                try:
                    _synapse_rest_post(
                        "/repo/v1/membershipRequest",
                        {
                            "teamId": SYNAPSE_TEAM_ID,
                            "message": "Auto-join via HTAN Claude skill setup",
                        },
                        token,
                    )
                    _log("Team join request submitted")
                except Exception as e:
                    _log(f"Warning: Could not auto-join team: {e}")
            elif is_member:
                _log("Already a member of HTAN Claude Skill Users team")
            else:
                _log(
                    "Warning: Cannot auto-join team. "
                    "Join manually: https://www.synapse.org/Team:3574960"
                )
        except Exception as e:
            _log(f"Warning: Could not check team membership: {e}")

    # Get entity bundle -> file handle ID
    _log(f"Downloading portal credentials ({PORTAL_CREDENTIALS_SYNAPSE_ID})...")
    try:
        bundle = _synapse_rest_post(
            f"/repo/v1/entity/{PORTAL_CREDENTIALS_SYNAPSE_ID}/bundle2",
            {"includeEntity": True, "includeFileHandles": True},
            token,
        )
        fh_id = bundle["entity"]["dataFileHandleId"]
    except urllib.error.HTTPError as e:
        if e.code == 403:
            _error(
                "Access denied — you need to join the HTAN Claude Skill Users team",
                "Join at: https://www.synapse.org/Team:3574960 — then re-run this command",
            )
        _error(f"Failed to get entity bundle: {e}")
    except Exception as e:
        _error(f"Failed to get entity bundle: {e}")

    # Get pre-signed download URL
    try:
        url_resp = _synapse_rest_get(
            f"/file/v1/fileHandle/{fh_id}/url?redirect=false",
            token,
            endpoint=SYNAPSE_FILE_ENDPOINT,
        )
        # Response is a string URL (JSON-encoded)
        download_url = url_resp if isinstance(url_resp, str) else str(url_resp)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            _error(
                "Access denied — you need to join the HTAN Claude Skill Users team",
                "Join at: https://www.synapse.org/Team:3574960 — then re-run this command",
            )
        _error(f"Failed to get download URL: {e}")
    except Exception as e:
        _error(f"Failed to get download URL: {e}")

    # Download credentials file
    try:
        req = urllib.request.Request(download_url)
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            creds = json.loads(resp.read())
    except Exception as e:
        _error(f"Failed to download credentials: {e}")

    # Validate
    required_keys = ("host", "port", "user", "password")
    missing = [k for k in required_keys if k not in creds]
    if missing:
        _error(f"Downloaded credentials missing keys: {', '.join(missing)}")

    # Store in keychain
    keychain_ok = False
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        from htan_portal_config import save_to_keychain
        keychain_ok = save_to_keychain(creds)
        if keychain_ok:
            _log("Portal credentials stored in OS Keychain")
        else:
            _log("Could not store in OS Keychain — using config file only")
    except ImportError:
        _log("Warning: Could not import htan_portal_config for keychain storage")

    # Also write config file (backward compat)
    os.makedirs(PORTAL_CONFIG_DIR, exist_ok=True)
    with open(PORTAL_CONFIG_PATH, "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")
    os.chmod(PORTAL_CONFIG_PATH, 0o600)
    _log(f"Portal config saved to: {PORTAL_CONFIG_PATH}")

    # Quick connectivity check
    connected = False
    try:
        import base64

        url = f"https://{creds['host']}:{creds['port']}/"
        params = urllib.parse.urlencode({"default_format": "TabSeparated"})
        credentials = base64.b64encode(
            f"{creds['user']}:{creds['password']}".encode()
        ).decode()

        req = urllib.request.Request(
            url + "?" + params,
            data=b"SELECT 1",
            headers={"Authorization": f"Basic {credentials}"},
            method="POST",
        )
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = resp.read().decode("utf-8").strip()
            connected = result == "1"
    except Exception as e:
        _log(f"Warning: Connectivity check failed: {e}")

    _result({
        "ok": True,
        "action": "configured",
        "source": "keychain" if keychain_ok else "file",
        "path": PORTAL_CONFIG_PATH,
        "connected": connected,
    })


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description="Claude-safe HTAN setup (non-interactive, JSON output)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    subparsers.add_parser(
        "check", help="Check status of all services (JSON output)"
    )

    # venv
    sp_venv = subparsers.add_parser(
        "venv", help="Create .venv and install dependencies using uv"
    )
    sp_venv.add_argument(
        "directory",
        nargs="?",
        help="Directory to create .venv in (default: current directory)",
    )
    sp_venv.add_argument(
        "--force", action="store_true", help="Recreate venv even if it exists"
    )

    # portal
    sp_portal = subparsers.add_parser(
        "portal",
        help="Download portal credentials from Synapse (stdlib only)",
    )
    sp_portal.add_argument(
        "--force", action="store_true", help="Overwrite existing config"
    )

    args = parser.parse_args()

    if args.command == "check":
        cmd_check(args)
    elif args.command == "venv":
        cmd_venv(args)
    elif args.command == "portal":
        cmd_portal(args)


if __name__ == "__main__":
    main()
