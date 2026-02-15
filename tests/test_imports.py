"""Smoke tests: verify all package modules import cleanly."""


def test_import_top_level():
    from htan import __version__
    assert __version__ == "0.2.0"


def test_import_config():
    from htan.config import (
        load_portal_config,
        check_setup,
        CONFIG_PATH,
        REQUIRED_KEYS,
        ConfigError,
    )
    assert "host" in REQUIRED_KEYS


def test_import_query_portal():
    from htan.query.portal import (
        PortalClient,
        PortalError,
        validate_sql_safety,
        escape_sql_string,
        normalize_sql,
        ensure_limit,
        build_where_clauses,
    )


def test_import_query_bq():
    from htan.query.bq import BigQueryClient, validate_sql_safety


def test_import_download_synapse():
    from htan.download.synapse import download


def test_import_download_gen3():
    from htan.download.gen3 import download, resolve


def test_import_pubs():
    from htan.pubs import search, fetch, fulltext


def test_import_model():
    from htan.model import DataModel, download_model


def test_import_files():
    from htan.files import lookup, update_cache, stats, infer_access_tier


def test_import_cli():
    from htan.cli import main
