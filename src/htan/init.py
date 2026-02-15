"""Interactive setup wizard for HTAN CLI.

Provides ``htan init`` — an interactive wizard that walks through credential
configuration for each HTAN service (portal, Synapse, BigQuery, Gen3/CRDC).

Usage::

    htan init                          # Full interactive wizard
    htan init portal                   # Set up portal only
    htan init synapse                  # Set up synapse only
    htan init bigquery                 # Set up bigquery only
    htan init gen3                     # Set up gen3 only
    htan init --status                 # Show current config status
    htan init --non-interactive        # CI mode: detect only, no prompts
    htan init --force                  # Re-run even if configured
"""

import argparse
import base64
import json
import os
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from htan.config import (
    check_setup,
    detect_source,
    load_portal_config,
    get_clickhouse_url,
    save_to_keychain,
    CONFIG_DIR,
    CONFIG_PATH,
    REQUIRED_KEYS,
    SYNAPSE_CONFIG_PATH,
    GEN3_CREDS_PATH,
    BIGQUERY_ADC_PATH,
)

# Synapse File entity containing portal_credentials.json
# Hosted in project syn73720845 ("HTAN Claude Skill Users" team access)
PORTAL_CREDENTIALS_SYNAPSE_ID = "syn73720854"

SYNAPSE_TEAM_URL = "https://www.synapse.org/Team:3574960"

SERVICES = {
    "portal": {
        "label": "Portal (ClickHouse)",
        "desc": "Query files, metadata, clinical data",
    },
    "synapse": {
        "label": "Synapse",
        "desc": "Open-access data downloads",
    },
    "bigquery": {
        "label": "BigQuery (ISB-CGC)",
        "desc": "Advanced metadata queries",
    },
    "gen3": {
        "label": "Gen3/CRDC",
        "desc": "Controlled-access data (requires dbGaP)",
    },
}

INIT_ORDER = ["synapse", "portal", "bigquery", "gen3"]


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _status_icon(ok):
    """Return a check or cross icon for status display."""
    return "\u2713" if ok else "\u2717"


def _print_header(text):
    """Print a section header to stderr."""
    print(f"\n--- {text} ---", file=sys.stderr)


def _prompt(msg, default=""):
    """Prompt user for input, handling EOF gracefully."""
    try:
        response = input(msg).strip()
        return response if response else default
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return default


def _print_status(label, ok, message):
    """Print a formatted status line to stderr."""
    icon = _status_icon(ok)
    print(f"  {icon} {label}: {message}", file=sys.stderr)


def _print_skip(label, message):
    """Print a formatted skip line to stderr."""
    print(f"  - {label}: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status():
    """Display current configuration status for all services.

    Prints a formatted status table to stderr.

    Returns:
        Dict mapping service names to bool (configured or not).
    """
    setup = check_setup()
    source = detect_source()

    result = {}

    # Portal
    portal_ok = source is not None
    portal_detail = f"({source})" if source else "Not configured"
    if portal_ok:
        portal_detail = f"Configured ({source})"
    _print_status(SERVICES["portal"]["label"], portal_ok, portal_detail)
    result["portal"] = portal_ok

    # Synapse
    syn_info = setup["synapse"]
    syn_ok = syn_info["configured"]
    syn_detail = syn_info["method"] if syn_ok else "Not configured"
    if syn_ok:
        syn_detail = f"Configured ({syn_detail})"
    _print_status(SERVICES["synapse"]["label"], syn_ok, syn_detail)
    result["synapse"] = syn_ok

    # BigQuery
    bq_info = setup["bigquery"]
    bq_ok = bq_info["configured"]
    bq_detail = bq_info["method"] if bq_ok else "Not configured"
    if bq_ok:
        bq_detail = f"Configured ({bq_detail})"
    _print_status(SERVICES["bigquery"]["label"], bq_ok, bq_detail)
    result["bigquery"] = bq_ok

    # Gen3
    gen3_info = setup["gen3"]
    gen3_ok = gen3_info["configured"]
    gen3_detail = gen3_info["method"] if gen3_ok else "Not configured"
    if gen3_ok:
        gen3_detail = f"Configured ({gen3_detail})"
    _print_status(SERVICES["gen3"]["label"], gen3_ok, gen3_detail)
    result["gen3"] = gen3_ok

    return result


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _verify_portal():
    """Verify portal connectivity by running ``SELECT 1``.

    Uses :func:`htan.config.load_portal_config` and
    :func:`htan.config.get_clickhouse_url` — no sys.path hacks.

    Returns:
        True if the portal responds with ``1``.
    """
    try:
        cfg = load_portal_config()
    except Exception:
        return False

    url = get_clickhouse_url(cfg)
    user = cfg["user"]
    password = cfg["password"]

    params = urllib.parse.urlencode({"default_format": "TabSeparated"})
    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()

    req = urllib.request.Request(
        url + "?" + params,
        data=b"SELECT 1",
        headers={"Authorization": f"Basic {credentials}"},
        method="POST",
    )

    try:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = resp.read().decode("utf-8").strip()
            return result == "1"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Service init functions
# ---------------------------------------------------------------------------

def _init_synapse(force=False, non_interactive=False):
    """Set up Synapse authentication.

    Returns:
        Tuple of (ok: bool, synapse_client: object | None).
        The client is returned so it can be reused by ``_init_portal``.
    """
    _print_header("Synapse")

    token = os.environ.get("SYNAPSE_AUTH_TOKEN")
    has_config = os.path.exists(SYNAPSE_CONFIG_PATH)
    has_auth = bool(token) or has_config

    if has_auth and not force:
        if token:
            _print_status("Synapse auth", True, "SYNAPSE_AUTH_TOKEN is set")
        else:
            _print_status("Synapse auth", True, "~/.synapseConfig found")

        # Verify login
        try:
            import synapseclient  # lazy
            syn = synapseclient.Synapse()
            syn.login(silent=True)
            profile = syn.getUserProfile()
            username = getattr(profile, "userName", "unknown")
            _print_status("Synapse login", True, f"Logged in as: {username}")
            return True, syn
        except ImportError:
            _print_status("Synapse client", True,
                          "Credentials found (install htan[synapse] to verify login)")
            return True, None
        except Exception as e:
            _print_status("Synapse login", False, f"Login failed: {e}")
            if non_interactive:
                return False, None
            # Fall through to setup instructions

    if non_interactive:
        _print_skip("Synapse", "Not configured (non-interactive mode)")
        return False, None

    # Interactive: print instructions and wait
    if not has_auth or force:
        print(file=sys.stderr)
        print("  To set up Synapse auth:", file=sys.stderr)
        print("    1. Create a free account at https://www.synapse.org", file=sys.stderr)
        print("    2. Go to Account Settings > Personal Access Tokens", file=sys.stderr)
        print("       https://www.synapse.org/#!PersonalAccessTokens:", file=sys.stderr)
        print("    3. Generate a token with 'view', 'download' permissions", file=sys.stderr)
        print("    4. Create ~/.synapseConfig:", file=sys.stderr)
        print("         [authentication]", file=sys.stderr)
        print("         authtoken = <your-token>", file=sys.stderr)
        print(file=sys.stderr)

        response = _prompt("  Press Enter when ready (or 'skip' to skip): ")
        if response.lower() == "skip":
            _print_skip("Synapse", "Skipped by user")
            return False, None

        # Re-check after user action
        token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        if not token and not os.path.exists(SYNAPSE_CONFIG_PATH):
            _print_status("Synapse auth", False, "Still not configured")
            return False, None

    # Verify login
    try:
        import synapseclient  # lazy
        syn = synapseclient.Synapse()
        syn.login(silent=True)
        profile = syn.getUserProfile()
        username = getattr(profile, "userName", "unknown")
        _print_status("Synapse login", True, f"Logged in as: {username}")
        return True, syn
    except ImportError:
        _print_status("Synapse client", True,
                      "Credentials found (install htan[synapse] to verify login)")
        return True, None
    except Exception as e:
        _print_status("Synapse login", False, f"Login failed: {e}")
        return False, None


def _init_portal(force=False, non_interactive=False, synapse_client=None):
    """Set up portal ClickHouse credentials.

    Downloads credentials from Synapse (gated by team membership),
    stores them in the OS keychain (preferred) or config file (fallback).

    Args:
        force: Re-download even if already configured.
        non_interactive: Skip prompts — detect-only mode.
        synapse_client: Reuse an already-authenticated Synapse client.

    Returns:
        True if portal is configured and connectivity verified.
    """
    _print_header("Portal (ClickHouse)")

    source = detect_source()

    # Already configured and not forcing
    if source and not force:
        _print_status("Portal config", True, f"Credentials via {source}")
        if _verify_portal():
            _print_status("Portal connectivity", True, "SELECT 1 OK")
            return True
        else:
            _print_status("Portal connectivity", False,
                          "Config exists but connectivity failed. Use --force to re-download.")
            return False

    if non_interactive:
        if not synapse_client:
            _print_skip("Portal", "Synapse auth required (non-interactive mode)")
            return False
        # In non-interactive mode with a client, proceed automatically
    else:
        if not synapse_client:
            # Check if Synapse auth is available for ad-hoc login
            token = os.environ.get("SYNAPSE_AUTH_TOKEN")
            if not token and not os.path.exists(SYNAPSE_CONFIG_PATH):
                _print_status("Portal credentials", False,
                              "Synapse auth required first — run: htan init synapse")
                return False

    # Get or create a Synapse client
    syn = synapse_client
    if syn is None:
        try:
            import synapseclient  # lazy
            syn = synapseclient.Synapse()
            syn.login(silent=True)
        except ImportError:
            _print_status("Portal credentials", False,
                          "synapseclient not installed (pip install htan[synapse])")
            return False
        except Exception as e:
            _print_status("Portal credentials", False, f"Synapse login failed: {e}")
            return False

    # Download credentials from Synapse
    print("  Downloading portal credentials from Synapse...", file=sys.stderr)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            entity = syn.get(PORTAL_CREDENTIALS_SYNAPSE_ID, downloadLocation=tmpdir)
            with open(entity.path, "r") as f:
                creds = json.load(f)
    except Exception as e:
        error_str = str(e)
        if "403" in error_str or "access" in error_str.lower():
            _print_status("Portal credentials", False,
                          "Access denied — join the HTAN Claude Skill Users team first")
            print(f"    Join here: {SYNAPSE_TEAM_URL}", file=sys.stderr)
        else:
            _print_status("Portal credentials", False, f"Download failed: {e}")
        return False

    # Validate
    missing = [k for k in REQUIRED_KEYS if k not in creds]
    if missing:
        _print_status("Portal credentials", False,
                      f"Downloaded file missing keys: {', '.join(missing)}")
        return False

    # Save: try keychain first, fall back to config file
    saved_to = None
    if save_to_keychain(creds):
        saved_to = "keychain"
        _print_status("Portal credentials", True, "Saved to OS keychain")
    else:
        # Fall back to config file
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(creds, f, indent=2)
            f.write("\n")
        os.chmod(CONFIG_PATH, 0o600)
        saved_to = "file"
        _print_status("Portal credentials", True, f"Saved to {CONFIG_PATH}")

    # Verify connectivity
    if _verify_portal():
        _print_status("Portal connectivity", True, "SELECT 1 OK")
        return True
    else:
        _print_status("Portal connectivity", False,
                      f"Credentials saved ({saved_to}) but connectivity check failed")
        print("  The portal endpoint may be temporarily unavailable.", file=sys.stderr)
        return False


def _init_bigquery(force=False, non_interactive=False):
    """Set up BigQuery / ISB-CGC authentication.

    Returns:
        True if BigQuery credentials are detected.
    """
    _print_header("BigQuery (ISB-CGC)")

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    has_sa = sa_key and os.path.exists(sa_key)
    has_adc = os.path.exists(BIGQUERY_ADC_PATH)
    has_auth = has_sa or has_adc

    if has_auth and not force:
        if has_sa:
            msg = f"Service account key: {sa_key}"
        else:
            msg = "Application Default Credentials found"
        if project:
            msg += f", project: {project}"
        _print_status("BigQuery auth", True, msg)
        return True

    if non_interactive:
        _print_skip("BigQuery", "Not configured (non-interactive mode)")
        return False

    # Interactive
    print(file=sys.stderr)
    response = _prompt("  Set up BigQuery? [y/N]: ", default="n")
    if response.lower() not in ("y", "yes"):
        _print_skip("BigQuery", "Skipped by user")
        return False

    print(file=sys.stderr)
    print("  To set up BigQuery:", file=sys.stderr)
    print("    1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install",
          file=sys.stderr)
    print("    2. In another terminal, run:", file=sys.stderr)
    print("         gcloud auth application-default login", file=sys.stderr)
    print("    3. Set your billing project:", file=sys.stderr)
    print('         export GOOGLE_CLOUD_PROJECT="your-project-id"', file=sys.stderr)
    print(file=sys.stderr)

    response = _prompt("  Press Enter when ready (or 'skip' to skip): ")
    if response.lower() == "skip":
        _print_skip("BigQuery", "Skipped by user")
        return False

    # Re-check
    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    has_sa = sa_key and os.path.exists(sa_key)
    has_adc = os.path.exists(BIGQUERY_ADC_PATH)

    if has_sa or has_adc:
        _print_status("BigQuery auth", True, "Credentials detected")
        return True

    _print_status("BigQuery auth", False,
                  "Still not configured. Set up later: gcloud auth application-default login")
    return False


def _init_gen3(force=False, non_interactive=False):
    """Set up Gen3/CRDC authentication.

    Gen3 requires dbGaP authorization which cannot be automated, so this
    function is primarily informational.

    Returns:
        True if Gen3 credentials are detected.
    """
    _print_header("Gen3/CRDC")

    env_path = os.environ.get("GEN3_API_KEY")
    has_env = env_path and os.path.exists(env_path)
    has_config = os.path.exists(GEN3_CREDS_PATH)
    has_auth = has_env or has_config

    if has_auth and not force:
        if has_env:
            _print_status("Gen3 auth", True, f"GEN3_API_KEY -> {env_path}")
        else:
            _print_status("Gen3 auth", True, "~/.gen3/credentials.json found")
        return True

    if non_interactive:
        _print_skip("Gen3/CRDC", "Not configured (non-interactive mode)")
        return False

    # Informational — cannot automate dbGaP
    print(file=sys.stderr)
    print("  Gen3/CRDC provides controlled-access data (raw sequencing, "
          "protected genomic data).", file=sys.stderr)
    print("  Requires dbGaP authorization for HTAN study phs002371 "
          "(may take weeks).", file=sys.stderr)
    print(file=sys.stderr)
    print("  Steps when you are ready:", file=sys.stderr)
    print("    1. Apply for dbGaP access: https://dbgap.ncbi.nlm.nih.gov/",
          file=sys.stderr)
    print("    2. Log in to CRDC: https://nci-crdc.datacommons.io/",
          file=sys.stderr)
    print("    3. Download credentials to ~/.gen3/credentials.json",
          file=sys.stderr)
    _print_skip("Gen3/CRDC", "Requires dbGaP authorization — cannot automate")
    return False


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_SERVICE_INIT = {
    "synapse": _init_synapse,
    "portal": _init_portal,
    "bigquery": _init_bigquery,
    "gen3": _init_gen3,
}


def run_init(services=None, force=False, non_interactive=False, status_only=False):
    """Main init orchestrator.

    Args:
        services: List of service names to init, or None for interactive menu.
        force: Re-run even if already configured.
        non_interactive: Detect-only mode, no prompts.
        status_only: Just print status, do not init.
    """
    print(file=sys.stderr)
    print("Welcome to the HTAN CLI! This command will walk you through "
          "configuration.", file=sys.stderr)

    # Always show current status
    print(file=sys.stderr)
    print("Current configuration:", file=sys.stderr)
    current = show_status()

    if status_only:
        return current

    # Determine which services to init
    if services is None and not non_interactive:
        # Interactive menu
        print(file=sys.stderr)
        print("Which services would you like to set up?", file=sys.stderr)
        print("  [1] Portal database (recommended — query files, metadata, "
              "clinical data)", file=sys.stderr)
        print("  [2] Synapse downloads (open-access data)", file=sys.stderr)
        print("  [3] BigQuery (advanced metadata queries via ISB-CGC)",
              file=sys.stderr)
        print("  [4] Gen3/CRDC (controlled-access data — requires dbGaP)",
              file=sys.stderr)
        print("  [a] All services", file=sys.stderr)
        print("  [q] Quit (keep current configuration)", file=sys.stderr)
        print(file=sys.stderr)

        choice = _prompt("Your choice: ", default="q")

        choice_map = {
            "1": ["portal"],
            "2": ["synapse"],
            "3": ["bigquery"],
            "4": ["gen3"],
            "a": list(INIT_ORDER),
            "q": [],
        }
        services = choice_map.get(choice.lower(), [])

        if not services:
            print("\nNo changes made.", file=sys.stderr)
            return current

    elif services is None:
        # Non-interactive: check all services
        services = list(INIT_ORDER)

    # Enforce ordering: if portal is requested, ensure synapse comes first
    ordered = [s for s in INIT_ORDER if s in services]

    results = {}
    synapse_client = None

    for svc in ordered:
        if svc == "synapse":
            ok, synapse_client = _init_synapse(
                force=force, non_interactive=non_interactive,
            )
            results["synapse"] = ok
        elif svc == "portal":
            results["portal"] = _init_portal(
                force=force,
                non_interactive=non_interactive,
                synapse_client=synapse_client,
            )
        elif svc == "bigquery":
            results["bigquery"] = _init_bigquery(
                force=force, non_interactive=non_interactive,
            )
        elif svc == "gen3":
            results["gen3"] = _init_gen3(
                force=force, non_interactive=non_interactive,
            )

    # Summary
    print(file=sys.stderr)
    print("=== Setup Summary ===", file=sys.stderr)
    for svc in INIT_ORDER:
        label = SERVICES[svc]["label"]
        if svc in results:
            icon = _status_icon(results[svc])
            detail = "Ready" if results[svc] else "Not configured"
            suffix = "" if svc in ("portal", "synapse") else " (optional)"
            print(f"  {icon} {label}: {detail}{suffix}", file=sys.stderr)
    print(file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def cli_main(args=None):
    """Argparse entry point for ``htan init``.

    Args:
        args: List of arguments (default: sys.argv style from CLI dispatcher).
    """
    parser = argparse.ArgumentParser(
        prog="htan init",
        description="Interactive setup wizard for HTAN CLI credentials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  htan init                     # Full interactive wizard\n"
            "  htan init portal              # Set up portal only\n"
            "  htan init synapse             # Set up synapse only\n"
            "  htan init --status            # Show current config status\n"
            "  htan init --non-interactive   # CI mode: detect only\n"
            "  htan init --force             # Re-run even if configured\n"
        ),
    )
    parser.add_argument(
        "service",
        nargs="?",
        choices=["portal", "synapse", "bigquery", "gen3"],
        default=None,
        help="Set up a specific service (default: interactive menu)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current configuration status and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run setup even if already configured",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Detect existing config only — no interactive prompts (CI mode)",
    )

    parsed = parser.parse_args(args)

    services = [parsed.service] if parsed.service else None

    result = run_init(
        services=services,
        force=parsed.force,
        non_interactive=parsed.non_interactive,
        status_only=parsed.status,
    )

    # Exit non-zero if any requested service failed
    if result and isinstance(result, dict):
        # For status_only, exit 0 always
        if parsed.status:
            return
        # For init, exit 1 if any service is False
        if any(v is False for v in result.values()):
            sys.exit(1)
