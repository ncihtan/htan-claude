#!/usr/bin/env python3
"""Claude-safe HTAN setup: non-interactive, clean JSON output, no prompts.

Designed to be invoked by Claude via Bash. Three subcommands:

  check  — JSON status of all services (stdlib only, no imports needed)
  venv   — Create .venv and install deps using uv
  portal — Download portal credentials from Synapse (requires synapseclient)

Usage:
    python3 htan_quicksetup.py check
    python3 htan_quicksetup.py venv [DIR]
    .venv/bin/python htan_quicksetup.py portal
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


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


# --- check subcommand ---


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

    # Portal credentials
    has_portal = os.path.exists(PORTAL_CONFIG_PATH)
    portal_valid = False
    if has_portal:
        try:
            with open(PORTAL_CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            portal_valid = all(k in cfg for k in ("host", "port", "user", "password"))
        except (json.JSONDecodeError, PermissionError):
            portal_valid = False
    status["portal"] = {
        "configured": has_portal and portal_valid,
        "path": PORTAL_CONFIG_PATH if has_portal else None,
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
    """Download portal credentials from Synapse.

    Requires synapseclient to be installed (run `venv` subcommand first).
    Auto-joins the HTAN Claude Skill Users team if possible.
    """
    import tempfile

    # Check if config already exists
    if os.path.exists(PORTAL_CONFIG_PATH) and not args.force:
        # Validate existing config
        try:
            with open(PORTAL_CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            if all(k in cfg for k in ("host", "port", "user", "password")):
                _result({
                    "ok": True,
                    "action": "already_configured",
                    "path": PORTAL_CONFIG_PATH,
                })
        except (json.JSONDecodeError, PermissionError):
            pass  # Fall through to re-download

    # Import synapseclient
    try:
        import synapseclient
    except ImportError:
        _error(
            "synapseclient not installed",
            "Run the venv subcommand first to install dependencies, "
            "then run this with: .venv/bin/python htan_quicksetup.py portal",
        )

    # Log in to Synapse
    _log("Logging in to Synapse...")
    try:
        syn = synapseclient.Synapse()
        syn.login(silent=True)
    except Exception as e:
        _error(f"Synapse login failed: {e}")

    # Get user profile for team check
    try:
        profile = syn.getUserProfile()
        user_id = profile.get("ownerId", "")
        _log(f"Logged in as: {profile.get('userName', 'unknown')}")
    except Exception:
        user_id = ""

    # Check team membership and auto-join if possible
    if user_id:
        try:
            membership = syn.restGET(
                f"/team/{SYNAPSE_TEAM_ID}/member/{user_id}/membershipStatus"
            )
            is_member = membership.get("isMember", False)
            can_join = membership.get("canJoin", False)

            if not is_member and can_join:
                _log("Auto-joining HTAN Claude Skill Users team...")
                try:
                    syn.restPOST(
                        "/membershipRequest",
                        body=json.dumps({
                            "teamId": SYNAPSE_TEAM_ID,
                            "message": "Auto-join via HTAN Claude skill setup",
                        }),
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

    # Download credentials file
    _log(f"Downloading portal credentials ({PORTAL_CREDENTIALS_SYNAPSE_ID})...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            entity = syn.get(
                PORTAL_CREDENTIALS_SYNAPSE_ID, downloadLocation=tmpdir
            )
            with open(entity.path, "r") as f:
                creds = json.load(f)
    except Exception as e:
        error_str = str(e)
        if "403" in error_str or "access" in error_str.lower():
            _error(
                "Access denied — you need to join the HTAN Claude Skill Users team",
                "Join at: https://www.synapse.org/Team:3574960 — then re-run this command",
            )
        else:
            _error(f"Failed to download credentials: {e}")

    # Validate
    required_keys = ("host", "port", "user", "password")
    missing = [k for k in required_keys if k not in creds]
    if missing:
        _error(f"Downloaded credentials missing keys: {', '.join(missing)}")

    # Write config
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
        import ssl
        import urllib.error
        import urllib.parse
        import urllib.request

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

        ctx = None
        try:
            import certifi

            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = resp.read().decode("utf-8").strip()
            connected = result == "1"
    except Exception as e:
        _log(f"Warning: Connectivity check failed: {e}")

    _result({
        "ok": True,
        "action": "configured",
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
        help="Download portal credentials from Synapse",
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
