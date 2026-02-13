#!/usr/bin/env python3
"""HTAN environment setup and dependency verification.

Provides an interactive `init` wizard for first-time setup, as well as
`init-portal` (portal credentials only) and `--check` (detection only).

Usage:
    python3 scripts/htan_setup.py init              # Interactive setup wizard
    python3 scripts/htan_setup.py init --force       # Re-run all steps even if configured
    python3 scripts/htan_setup.py init --non-interactive  # Skip interactive prompts
    python3 scripts/htan_setup.py                    # Check and install missing packages
    python3 scripts/htan_setup.py --check            # Check only, don't install
    python3 scripts/htan_setup.py --service synapse  # Check specific service
    python3 scripts/htan_setup.py init-portal        # Download portal credentials from Synapse
    python3 scripts/htan_setup.py init-portal --force  # Overwrite existing config
"""

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys


REQUIRED_PACKAGES = {
    "synapseclient": {"import_name": "synapseclient", "service": "synapse"},
    "gen3": {"import_name": "gen3", "service": "gen3"},
    "google-cloud-bigquery": {"import_name": "google.cloud.bigquery", "service": "bigquery"},
    "google-cloud-bigquery-storage": {
        "import_name": "google.cloud.bigquery_storage",
        "service": "bigquery",
    },
    "pandas": {"import_name": "pandas", "service": "all"},
    "db-dtypes": {"import_name": "db_dtypes", "service": "bigquery"},
}

ALL_PIP_PACKAGES = [
    "synapseclient", "gen3", "google-cloud-bigquery",
    "google-cloud-bigquery-storage", "pandas", "db-dtypes",
]

# Synapse File entity containing portal_credentials.json
# Hosted in project syn73720845 ("HTAN Claude Skill Users" team access)
PORTAL_CREDENTIALS_SYNAPSE_ID = "syn73720854"

SYNAPSE_TEAM_URL = "https://www.synapse.org/Team:3574960"


# --- Utility functions ---


def print_status(label, ok, message):
    """Print a formatted status line to stderr."""
    symbol = "OK" if ok else "FAIL"
    print(f"  [{symbol}] {label}: {message}", file=sys.stderr)


def print_skip(label, message):
    """Print a formatted skip line to stderr."""
    print(f"  [SKIP] {label}: {message}", file=sys.stderr)


def prompt_user(msg, default=""):
    """Prompt user for input. Returns the input string, or default if empty."""
    try:
        response = input(msg).strip()
        return response if response else default
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return default


def _get_project_root():
    """Get the project root (directory containing CLAUDE.md or .git)."""
    # Walk up from the script location
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        if os.path.exists(os.path.join(d, "CLAUDE.md")) or os.path.exists(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    # Fallback: current working directory
    return os.getcwd()


# --- Check functions (used by both init and check) ---


def check_python_version():
    """Verify Python >= 3.11."""
    version = sys.version_info
    ok = version >= (3, 11)
    msg = f"{version.major}.{version.minor}.{version.micro}"
    if not ok:
        msg += " (requires >= 3.11)"
    print_status("Python", ok, msg)
    return ok


def check_package(pip_name, import_name):
    """Check if a package is installed and return (installed, version)."""
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", getattr(mod, "version", "installed"))
        return True, str(version)
    except ImportError:
        return False, "not installed"


def install_package(pip_name):
    """Install a package via pip. Returns True on success."""
    try:
        print(f"  Installing {pip_name}...", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pip_name, "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_synapse_auth():
    """Check Synapse authentication configuration."""
    token = os.environ.get("SYNAPSE_AUTH_TOKEN")
    if token:
        print_status("Synapse auth", True, "SYNAPSE_AUTH_TOKEN is set")
        return True

    config_path = os.path.expanduser("~/.synapseConfig")
    if os.path.exists(config_path):
        print_status("Synapse auth", True, "~/.synapseConfig found")
        return True

    print_status("Synapse auth", False, "Set SYNAPSE_AUTH_TOKEN or create ~/.synapseConfig")
    return False


def check_gen3_auth():
    """Check Gen3/CRDC authentication configuration."""
    env_path = os.environ.get("GEN3_API_KEY")
    if env_path and os.path.exists(env_path):
        print_status("Gen3 auth", True, f"GEN3_API_KEY -> {env_path}")
        return True

    default_path = os.path.expanduser("~/.gen3/credentials.json")
    if os.path.exists(default_path):
        print_status("Gen3 auth", True, "~/.gen3/credentials.json found")
        return True

    print_status(
        "Gen3 auth",
        False,
        "No credentials found. Download from CRDC portal to ~/.gen3/credentials.json",
    )
    return False


def check_portal_connectivity():
    """Check connectivity to the HTAN portal ClickHouse backend using local config."""
    import base64
    import ssl
    import urllib.error
    import urllib.parse
    import urllib.request

    # Load config from the shared config module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from htan_portal_config import CONFIG_PATH, load_portal_config, get_clickhouse_url

    if not os.path.exists(CONFIG_PATH):
        print_status(
            "Portal (ClickHouse)", False,
            "Config not found. Run: python3 scripts/htan_setup.py init-portal"
        )
        return False

    try:
        cfg = load_portal_config()
    except SystemExit:
        print_status("Portal (ClickHouse)", False, "Invalid config. Run: python3 scripts/htan_setup.py init-portal --force")
        return False

    url = get_clickhouse_url(cfg)
    host = cfg["host"]
    user = cfg["user"]
    password = cfg["password"]

    params = urllib.parse.urlencode({"default_format": "TabSeparated"})
    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()

    req = urllib.request.Request(
        url + "?" + params,
        data=b"SELECT 1",
        headers={
            "Authorization": f"Basic {credentials}",
        },
        method="POST",
    )

    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = resp.read().decode("utf-8").strip()
            if result == "1":
                print_status("Portal (ClickHouse)", True, f"Connected to {host}")
                return True
            else:
                print_status("Portal (ClickHouse)", False, f"Unexpected response: {result[:50]}")
                return False
    except urllib.error.HTTPError as e:
        print_status("Portal (ClickHouse)", False, f"HTTP {e.code} — credentials may have changed")
        return False
    except urllib.error.URLError as e:
        print_status("Portal (ClickHouse)", False, f"Connection failed: {e.reason}")
        return False
    except Exception as e:
        print_status("Portal (ClickHouse)", False, f"Error: {e}")
        return False


def check_bigquery_auth():
    """Check BigQuery/Google Cloud authentication configuration."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if sa_key and os.path.exists(sa_key):
        msg = f"Service account key: {sa_key}"
        if project:
            msg += f", project: {project}"
        print_status("BigQuery auth", True, msg)
        return True

    # Check for application default credentials
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if os.path.exists(adc_path):
        msg = "Application Default Credentials found"
        if project:
            msg += f", project: {project}"
        else:
            msg += " (set GOOGLE_CLOUD_PROJECT for billing)"
        print_status("BigQuery auth", True, msg)
        return True

    print_status(
        "BigQuery auth",
        False,
        "Run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS",
    )
    return False


# --- Init wizard step functions ---


def step_environment(force=False):
    """Step 1: Check Python, uv, venv, and install dependencies.

    Returns True if environment is ready.
    """
    all_ok = True

    # 1a. Python version
    version = sys.version_info
    ok = version >= (3, 11)
    msg = f"{version.major}.{version.minor}.{version.micro}"
    if not ok:
        msg += " (requires >= 3.11)"
        all_ok = False
    print_status("Python", ok, msg)

    if not ok:
        print("  Python 3.11+ is required. Please upgrade Python.", file=sys.stderr)
        return False

    # 1b. uv installed
    uv_path = shutil.which("uv")
    if uv_path:
        try:
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, timeout=5
            )
            uv_version = result.stdout.strip().replace("uv ", "")
            print_status("uv", True, uv_version)
        except Exception:
            print_status("uv", True, uv_path)
    else:
        print_status("uv", False, "Not found on PATH")
        print(file=sys.stderr)
        print("  Install uv (recommended package manager):", file=sys.stderr)
        print("    curl -LsSf https://astral.sh/uv/install.sh | sh", file=sys.stderr)
        print("  Or: brew install uv", file=sys.stderr)
        print(file=sys.stderr)
        all_ok = False
        return False

    # 1c. Virtual environment
    project_root = _get_project_root()
    venv_path = os.path.join(project_root, ".venv")
    if os.path.exists(venv_path) and not force:
        print_status("Virtual environment", True, venv_path)
    else:
        print("  Creating virtual environment...", file=sys.stderr)
        try:
            subprocess.run(
                ["uv", "venv", venv_path],
                check=True, capture_output=True, text=True,
            )
            print_status("Virtual environment", True, f"Created {venv_path}")
        except subprocess.CalledProcessError as e:
            print_status("Virtual environment", False, f"Failed: {e.stderr.strip()}")
            all_ok = False
            return False

    # 1d. Install dependencies
    print("  Installing dependencies...", file=sys.stderr)
    try:
        cmd = ["uv", "pip", "install", "-q", "--python", os.path.join(venv_path, "bin", "python")]
        cmd.extend(ALL_PIP_PACKAGES)
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print_status("Dependencies", True, "All packages installed")
    except subprocess.CalledProcessError as e:
        print_status("Dependencies", False, f"Install failed: {e.stderr.strip()[:100]}")
        all_ok = False

    return all_ok


def step_synapse_auth(force=False, non_interactive=False):
    """Step 2: Detect and guide Synapse authentication setup.

    Returns True if Synapse auth is configured and working.
    """
    token = os.environ.get("SYNAPSE_AUTH_TOKEN")
    config_path = os.path.expanduser("~/.synapseConfig")

    has_auth = bool(token) or os.path.exists(config_path)

    if has_auth and not force:
        if token:
            print_status("Synapse auth", True, "SYNAPSE_AUTH_TOKEN is set")
        else:
            print_status("Synapse auth", True, "~/.synapseConfig found")

        # Verify login works
        try:
            import synapseclient
            syn = synapseclient.Synapse()
            syn.login(silent=True)
            profile = syn.getUserProfile()
            username = getattr(profile, "userName", "unknown")
            print_status("Synapse login", True, f"Logged in as: {username}")
            return True
        except Exception as e:
            print_status("Synapse login", False, f"Login failed: {e}")
            if non_interactive:
                return False
            # Fall through to setup instructions
    elif non_interactive:
        print_skip("Synapse auth", "Not configured (non-interactive mode)")
        return False

    if not has_auth:
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

        response = prompt_user("  Press Enter when ready (or 'skip' to skip): ")
        if response.lower() == "skip":
            print_skip("Synapse auth", "Skipped by user")
            return False

        # Re-check after user action
        token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        if not token and not os.path.exists(config_path):
            print_status("Synapse auth", False, "Still not configured")
            return False

    # Verify login
    try:
        import synapseclient
        syn = synapseclient.Synapse()
        syn.login(silent=True)
        profile = syn.getUserProfile()
        username = getattr(profile, "userName", "unknown")
        print_status("Synapse login", True, f"Logged in as: {username}")
        return True
    except ImportError:
        print_status("Synapse login", False, "synapseclient not installed — run Step 1 first")
        return False
    except Exception as e:
        print_status("Synapse login", False, f"Login failed: {e}")
        return False


def step_portal_credentials(force=False, non_interactive=False, synapse_verified=False):
    """Step 3: Download portal ClickHouse credentials from Synapse.

    Returns True if portal credentials are configured and connectivity verified.
    """
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from htan_portal_config import CONFIG_DIR, CONFIG_PATH, REQUIRED_KEYS

    # Check if config already exists and is working
    if os.path.exists(CONFIG_PATH) and not force:
        print_status("Portal config", True, CONFIG_PATH)
        # Verify connectivity
        if check_portal_connectivity():
            return True
        else:
            print("  Config exists but connectivity failed. Use --force to re-download.", file=sys.stderr)
            return False

    if non_interactive:
        if not synapse_verified:
            print_skip("Portal credentials", "Synapse auth required (non-interactive mode)")
            return False

    # Need Synapse auth to download credentials
    if not synapse_verified:
        # Try to check if Synapse auth is available
        token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        config_path = os.path.expanduser("~/.synapseConfig")
        if not token and not os.path.exists(config_path):
            print_status("Portal credentials", False, "Synapse auth required first (Step 2)")
            return False

    # Import synapseclient
    try:
        import synapseclient
    except ImportError:
        print_status("Portal credentials", False, "synapseclient not installed — run Step 1 first")
        return False

    # Log in to Synapse
    print("  Downloading from Synapse...", file=sys.stderr)
    try:
        syn = synapseclient.Synapse()
        syn.login(silent=True)
    except Exception as e:
        print_status("Portal credentials", False, f"Synapse login failed: {e}")
        return False

    # Download credentials file from Synapse
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            entity = syn.get(PORTAL_CREDENTIALS_SYNAPSE_ID, downloadLocation=tmpdir)
            downloaded_path = entity.path

            with open(downloaded_path, "r") as f:
                creds = json.load(f)
    except Exception as e:
        error_str = str(e)
        if "403" in error_str or "access" in error_str.lower():
            print_status("Portal credentials", False, "Access denied — join the HTAN Claude Skill Users team first")
            print(f"    Join here: {SYNAPSE_TEAM_URL}", file=sys.stderr)
        else:
            print_status("Portal credentials", False, f"Download failed: {e}")
        return False

    # Validate downloaded credentials
    missing = [k for k in REQUIRED_KEYS if k not in creds]
    if missing:
        print_status("Portal credentials", False, f"Downloaded file missing keys: {', '.join(missing)}")
        return False

    # Write to local config
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")

    # Set restrictive permissions (owner read/write only)
    os.chmod(CONFIG_PATH, 0o600)

    print_status("Portal config", True, CONFIG_PATH)

    # Verify connectivity
    if check_portal_connectivity():
        return True
    else:
        print("  Config saved but connectivity check failed.", file=sys.stderr)
        print("  The portal endpoint may be temporarily unavailable.", file=sys.stderr)
        return False


def step_bigquery_auth(force=False, non_interactive=False):
    """Step 4: Detect and guide BigQuery authentication setup.

    Returns True if BigQuery auth is configured.
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")

    has_auth = (sa_key and os.path.exists(sa_key)) or os.path.exists(adc_path)

    if has_auth and not force:
        if sa_key and os.path.exists(sa_key):
            msg = f"Service account key: {sa_key}"
        else:
            msg = "Application Default Credentials found"
        if project:
            msg += f", project: {project}"
        print_status("BigQuery auth", True, msg)
        return True

    if non_interactive:
        print_skip("BigQuery", "Not configured (non-interactive mode)")
        return False

    print(file=sys.stderr)
    response = prompt_user("  Set up BigQuery? [y/N]: ", default="n")
    if response.lower() not in ("y", "yes"):
        print_skip("BigQuery", "Skipped by user")
        return False

    print(file=sys.stderr)
    print("  To set up BigQuery:", file=sys.stderr)
    print("    1. Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install", file=sys.stderr)
    print("    2. In another terminal, run:", file=sys.stderr)
    print("         gcloud auth application-default login", file=sys.stderr)
    print("    3. Set your billing project:", file=sys.stderr)
    print("         export GOOGLE_CLOUD_PROJECT=\"your-project-id\"", file=sys.stderr)
    print(file=sys.stderr)

    response = prompt_user("  Press Enter when ready (or 'skip' to skip): ")
    if response.lower() == "skip":
        print_skip("BigQuery", "Skipped by user")
        return False

    # Re-check
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if (sa_key and os.path.exists(sa_key)) or os.path.exists(adc_path):
        print_status("BigQuery auth", True, "Credentials detected")
        return True

    print_status("BigQuery auth", False, "Still not configured — set up later with: gcloud auth application-default login")
    return False


def step_gen3_auth(force=False, non_interactive=False):
    """Step 5: Detect and inform about Gen3/CRDC authentication.

    Returns True if Gen3 auth is configured.
    """
    env_path = os.environ.get("GEN3_API_KEY")
    default_path = os.path.expanduser("~/.gen3/credentials.json")

    has_auth = (env_path and os.path.exists(env_path)) or os.path.exists(default_path)

    if has_auth and not force:
        if env_path and os.path.exists(env_path):
            print_status("Gen3 auth", True, f"GEN3_API_KEY -> {env_path}")
        else:
            print_status("Gen3 auth", True, "~/.gen3/credentials.json found")
        return True

    if non_interactive:
        print_skip("Gen3/CRDC", "Not configured (non-interactive mode)")
        return False

    print(file=sys.stderr)
    print("  Gen3/CRDC provides controlled-access data (raw sequencing, protected genomic).", file=sys.stderr)
    print("  Requires dbGaP authorization for HTAN study phs002371 (may take weeks).", file=sys.stderr)
    print("  This cannot be fully automated — see references/authentication_guide.md.", file=sys.stderr)
    print(file=sys.stderr)
    print("  Steps when you're ready:", file=sys.stderr)
    print("    1. Apply for dbGaP access: https://dbgap.ncbi.nlm.nih.gov/", file=sys.stderr)
    print("    2. Log in to CRDC: https://nci-crdc.datacommons.io/", file=sys.stderr)
    print("    3. Download credentials to ~/.gen3/credentials.json", file=sys.stderr)
    print_skip("Gen3/CRDC", "Requires dbGaP authorization — see references/authentication_guide.md")
    return False


# --- init subcommand ---


def cmd_init(args):
    """Interactive setup wizard for first-time HTAN skill configuration."""
    force = args.force
    non_interactive = args.non_interactive

    print(file=sys.stderr)
    print("=== HTAN Skill Setup ===", file=sys.stderr)

    results = {}

    # Step 1: Environment
    print(file=sys.stderr)
    print("Step 1/5: Environment", file=sys.stderr)
    results["environment"] = step_environment(force=force)

    # Step 2: Synapse Auth (required)
    print(file=sys.stderr)
    print("Step 2/5: Synapse Authentication (required)", file=sys.stderr)
    results["synapse"] = step_synapse_auth(force=force, non_interactive=non_interactive)

    # Step 3: Portal Credentials (required)
    print(file=sys.stderr)
    print("Step 3/5: Portal Credentials (required)", file=sys.stderr)
    results["portal"] = step_portal_credentials(
        force=force,
        non_interactive=non_interactive,
        synapse_verified=results["synapse"],
    )

    # Step 4: BigQuery (optional)
    print(file=sys.stderr)
    print("Step 4/5: BigQuery / ISB-CGC (optional)", file=sys.stderr)
    results["bigquery"] = step_bigquery_auth(force=force, non_interactive=non_interactive)

    # Step 5: Gen3/CRDC (optional)
    print(file=sys.stderr)
    print("Step 5/5: Gen3 / CRDC (optional)", file=sys.stderr)
    results["gen3"] = step_gen3_auth(force=force, non_interactive=non_interactive)

    # Summary
    print(file=sys.stderr)
    print("=== Setup Complete ===", file=sys.stderr)

    def _label(ok):
        return "Ready" if ok else "Not configured"

    print(f"  Environment: {_label(results['environment'])}", file=sys.stderr)
    print(f"  Synapse:     {_label(results['synapse'])}", file=sys.stderr)
    print(f"  Portal:      {_label(results['portal'])}", file=sys.stderr)
    print(f"  BigQuery:    {_label(results['bigquery'])} (optional)", file=sys.stderr)
    print(f"  Gen3:        {_label(results['gen3'])} (optional)", file=sys.stderr)
    print(file=sys.stderr)

    # Exit with error if required services are not configured
    required_ok = results["environment"] and results["synapse"] and results["portal"]
    if not required_ok:
        print("Some required services are not configured. Re-run: python3 scripts/htan_setup.py init", file=sys.stderr)
        sys.exit(1)


# --- init-portal subcommand ---


def cmd_init_portal(args):
    """Download portal ClickHouse credentials from Synapse and cache locally."""
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from htan_portal_config import CONFIG_DIR, CONFIG_PATH, REQUIRED_KEYS

    # Check if config already exists
    if os.path.exists(CONFIG_PATH) and not args.force:
        print(f"Portal config already exists at: {CONFIG_PATH}", file=sys.stderr)
        print("Use --force to overwrite.", file=sys.stderr)
        sys.exit(0)

    # Import synapseclient
    try:
        import synapseclient
    except ImportError:
        print("Error: synapseclient is not installed.", file=sys.stderr)
        print("Install it with: uv pip install synapseclient", file=sys.stderr)
        sys.exit(1)

    # Log in to Synapse
    print("Logging in to Synapse...", file=sys.stderr)
    try:
        syn = synapseclient.Synapse()
        syn.login(silent=True)
    except Exception as e:
        print(f"Error: Synapse login failed: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Set up Synapse auth:", file=sys.stderr)
        print("  1. Get a Personal Access Token from https://www.synapse.org/#!PersonalAccessTokens:", file=sys.stderr)
        print("  2. Create ~/.synapseConfig with:", file=sys.stderr)
        print("     [authentication]", file=sys.stderr)
        print("     authtoken = <your-token>", file=sys.stderr)
        print("", file=sys.stderr)
        print("See references/authentication_guide.md for details.", file=sys.stderr)
        sys.exit(1)

    # Download credentials file from Synapse
    print(f"Downloading portal credentials from Synapse ({PORTAL_CREDENTIALS_SYNAPSE_ID})...", file=sys.stderr)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            entity = syn.get(PORTAL_CREDENTIALS_SYNAPSE_ID, downloadLocation=tmpdir)
            downloaded_path = entity.path

            with open(downloaded_path, "r") as f:
                creds = json.load(f)
    except synapseclient.core.exceptions.SynapseHTTPError as e:
        error_str = str(e)
        if "403" in error_str or "access" in error_str.lower():
            print("Error: Access denied. You may need to join the HTAN Claude Skill Users team.", file=sys.stderr)
            print(f"  Join here: {SYNAPSE_TEAM_URL}", file=sys.stderr)
            print("  Then re-run this command.", file=sys.stderr)
        else:
            print(f"Error downloading from Synapse: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error downloading from Synapse: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate downloaded credentials
    missing = [k for k in REQUIRED_KEYS if k not in creds]
    if missing:
        print(f"Error: Downloaded credentials missing required keys: {', '.join(missing)}", file=sys.stderr)
        print("The credentials file on Synapse may be malformed. Contact the HTAN skill maintainer.", file=sys.stderr)
        sys.exit(1)

    # Write to local config
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")

    # Set restrictive permissions (owner read/write only)
    os.chmod(CONFIG_PATH, 0o600)

    print(f"Portal config written to: {CONFIG_PATH}", file=sys.stderr)

    # Verify connectivity
    print("\nVerifying connectivity...", file=sys.stderr)
    if check_portal_connectivity():
        print("\nPortal setup complete.", file=sys.stderr)
    else:
        print("\nConfig saved but connectivity check failed.", file=sys.stderr)
        print("The portal endpoint may be temporarily unavailable.", file=sys.stderr)
        sys.exit(1)


# --- check subcommand (default) ---


def cmd_check(args):
    """Run dependency and authentication checks."""
    check_only = args.check or args.dry_run
    service_filter = args.service

    all_ok = True

    # Python version
    print("\nPython:", file=sys.stderr)
    if not check_python_version():
        all_ok = False

    # Packages
    print("\nPackages:", file=sys.stderr)
    for pip_name, info in REQUIRED_PACKAGES.items():
        if service_filter != "all" and info["service"] not in (service_filter, "all"):
            continue
        installed, version = check_package(pip_name, info["import_name"])
        if installed:
            print_status(pip_name, True, version)
        elif check_only:
            print_status(pip_name, False, "not installed")
            all_ok = False
        else:
            if install_package(pip_name):
                installed, version = check_package(pip_name, info["import_name"])
                print_status(pip_name, installed, version if installed else "install failed")
                if not installed:
                    all_ok = False
            else:
                print_status(pip_name, False, "install failed")
                all_ok = False

    # Portal connectivity (reads from config file)
    if service_filter in ("all", "portal"):
        print("\nPortal:", file=sys.stderr)
        if not check_portal_connectivity():
            all_ok = False

    # Authentication
    print("\nAuthentication:", file=sys.stderr)
    auth_checks = {
        "synapse": check_synapse_auth,
        "gen3": check_gen3_auth,
        "bigquery": check_bigquery_auth,
    }
    for svc, check_fn in auth_checks.items():
        if service_filter not in ("all", svc):
            continue
        if not check_fn():
            all_ok = False

    # Summary
    print(file=sys.stderr)
    if all_ok:
        print("All checks passed.", file=sys.stderr)
    else:
        print("Some checks failed. See above for details.", file=sys.stderr)
        print("See references/authentication_guide.md for setup instructions.", file=sys.stderr)

    sys.exit(0 if all_ok else 1)


def main():
    parser = argparse.ArgumentParser(
        description="HTAN environment setup and dependency checker",
        epilog="Examples:\n"
        "  python3 scripts/htan_setup.py init              # Interactive setup wizard\n"
        "  python3 scripts/htan_setup.py init --force       # Re-run all steps\n"
        "  python3 scripts/htan_setup.py                    # Check and install\n"
        "  python3 scripts/htan_setup.py --check            # Check only\n"
        "  python3 scripts/htan_setup.py --service synapse\n"
        "  python3 scripts/htan_setup.py init-portal        # Download portal credentials\n"
        "  python3 scripts/htan_setup.py init-portal --force\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # init subcommand
    sp_init = subparsers.add_parser(
        "init",
        help="Interactive setup wizard (first-time setup)",
        description="Interactive wizard that walks through environment setup, Synapse auth,\n"
        "portal credentials, BigQuery, and Gen3/CRDC configuration.\n\n"
        "Each step detects what's already configured, skips if satisfied,\n"
        "and provides instructions when action is needed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sp_init.add_argument(
        "--force", action="store_true",
        help="Re-run all steps even if already configured",
    )
    sp_init.add_argument(
        "--non-interactive", action="store_true",
        help="Skip interactive prompts (for CI or scripted setup)",
    )

    # init-portal subcommand
    sp_init_portal = subparsers.add_parser(
        "init-portal",
        help="Download portal ClickHouse credentials from Synapse",
        description="Download portal ClickHouse credentials from Synapse and cache locally.\n"
        "Requires Synapse auth (~/.synapseConfig) and membership in the\n"
        "HTAN Claude Skill Users team (https://www.synapse.org/Team:3574960).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sp_init_portal.add_argument(
        "--force", action="store_true",
        help="Overwrite existing config file",
    )

    # Default check arguments (when no subcommand given)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only, do not install missing packages",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Same as --check",
    )
    parser.add_argument(
        "--service",
        choices=["synapse", "gen3", "bigquery", "portal", "all"],
        default="all",
        help="Check a specific service (default: all)",
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "init-portal":
        cmd_init_portal(args)
    else:
        # Default: run check (backwards compatible)
        cmd_check(args)


if __name__ == "__main__":
    main()
