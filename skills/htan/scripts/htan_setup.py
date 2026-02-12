#!/usr/bin/env python3
"""HTAN environment setup and dependency verification.

Checks Python version, required packages, and authentication configuration
for Synapse, Gen3/CRDC, and BigQuery services.

Usage:
    python3 scripts/htan_setup.py              # Check and install missing packages
    python3 scripts/htan_setup.py --check      # Check only, don't install
    python3 scripts/htan_setup.py --service synapse  # Check specific service
"""

import argparse
import importlib
import os
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
}


def print_status(label, ok, message):
    """Print a formatted status line to stderr."""
    symbol = "OK" if ok else "FAIL"
    print(f"  [{symbol}] {label}: {message}", file=sys.stderr)


def check_python_version():
    """Verify Python >= 3.8."""
    version = sys.version_info
    ok = version >= (3, 8)
    msg = f"{version.major}.{version.minor}.{version.micro}"
    if not ok:
        msg += " (requires >= 3.8)"
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
        print_status("Synapse auth", True, f"~/.synapseConfig found")
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
    """Check connectivity to the HTAN portal ClickHouse backend."""
    import base64
    import ssl
    import urllib.error
    import urllib.parse
    import urllib.request

    host = "REDACTED_HOST"
    port = 8443
    user = "REDACTED_USER"
    password = "REDACTED_PASSWORD"

    url = f"https://{host}:{port}/"
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


def main():
    parser = argparse.ArgumentParser(
        description="HTAN environment setup and dependency checker",
        epilog="Examples:\n"
        "  python3 scripts/htan_setup.py              # Check and install\n"
        "  python3 scripts/htan_setup.py --check      # Check only\n"
        "  python3 scripts/htan_setup.py --service synapse\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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

    # Portal connectivity (no auth needed, just check reachability)
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


if __name__ == "__main__":
    main()
