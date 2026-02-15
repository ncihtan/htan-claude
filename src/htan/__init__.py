"""HTAN — Python tools for accessing Human Tumor Atlas Network data.

Core modules (stdlib only, no extra dependencies):
    htan.config          — Credential management (portal, keychain, env)
    htan.query.portal    — ClickHouse portal queries
    htan.pubs            — PubMed publication search
    htan.model           — HTAN data model queries
    htan.files           — File ID to download coordinate mapping

Optional modules (require extras):
    htan.query.bq        — BigQuery metadata queries   (pip install htan[bigquery])
    htan.download.synapse — Synapse open-access data    (pip install htan[synapse])
    htan.download.gen3   — Gen3/CRDC controlled-access  (pip install htan[gen3])
"""

__version__ = "0.1.0"
