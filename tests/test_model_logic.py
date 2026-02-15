"""Tests for htan.model — pure logic: component extraction, attribute lookup,
dependency chains, DataModel class methods, formatting, and categorization.

Uses small fixture data (no network, no cache file).
"""

import pytest

from htan.model import (
    _get_components,
    _get_component_attributes,
    _find_attribute,
    _get_dependency_chain,
    _categorize_component,
    _format_components_text,
    _format_attributes_text,
    _format_describe_text,
    _format_deps_text,
    _get_model_url,
    DataModel,
    MODEL_TAG,
)


# ---------------------------------------------------------------------------
# Fixture rows – minimal CSV-like dicts that mirror the real model CSV schema.
# ---------------------------------------------------------------------------

def _make_row(attr, parent="", depends_on="", dep_comp="", required="",
              desc="", valid_values="", validation_rules="", source=""):
    return {
        "Attribute": attr,
        "Parent": parent,
        "DependsOn": depends_on,
        "DependsOn Component": dep_comp,
        "Required": required,
        "Description": desc,
        "Valid Values": valid_values,
        "Validation Rules": validation_rules,
        "Source": source,
    }


FIXTURE_ROWS = [
    # Two top-level components (have DependsOn Component)
    _make_row("Biospecimen", parent="Component",
              depends_on="Biospecimen Type,HTAN Biospecimen ID,Preservation Method",
              dep_comp="Clinical"),
    _make_row("scRNA-seq Level 1", parent="Sequencing",
              depends_on="Library Construction Method,File Format,HTAN Data File ID",
              dep_comp="Biospecimen"),
    # Clinical is referenced as a dep-component but not explicitly declared with dep_comp,
    # so _get_components should discover it via the "referenced_components" second pass.
    _make_row("Clinical", parent="Component",
              depends_on="HTAN Participant ID,Gender,Race"),
    # Regular attributes
    _make_row("Biospecimen Type", parent="Biospecimen", desc="Type of biospecimen",
              valid_values="Bulk cells,Tissue,Organoid,Sorted cells",
              required="TRUE"),
    _make_row("HTAN Biospecimen ID", parent="Biospecimen", desc="Biospecimen identifier",
              required="TRUE", validation_rules="regex match HTA"),
    _make_row("Preservation Method", parent="Biospecimen", desc="How the sample was preserved",
              valid_values="FFPE,Fresh,Frozen"),
    _make_row("Library Construction Method", parent="Assay", desc="Library prep method",
              valid_values="10x 3',10x 5',Smart-seq2,Drop-seq,inDrop,sci-RNA-seq",
              required="TRUE"),
    _make_row("File Format", parent="Assay", desc="Format of the data file",
              valid_values="fastq,bam,h5ad,csv,tsv"),
    _make_row("HTAN Data File ID", parent="Assay", desc="File identifier", required="TRUE"),
    _make_row("HTAN Participant ID", parent="Clinical", desc="Participant identifier",
              required="TRUE"),
    _make_row("Gender", parent="Clinical", desc="Gender of patient",
              valid_values="male,female,unknown"),
    _make_row("Race", parent="Clinical", desc="Race of patient",
              valid_values="white,black or african american,asian"),
    # A standalone attribute with no connections
    _make_row("Barcode", parent="Assay", desc="Sample barcode sequence"),
]


# ===========================================================================
# _get_model_url
# ===========================================================================

def test_get_model_url_default():
    url = _get_model_url()
    assert MODEL_TAG in url
    assert "HTAN.model.csv" in url


def test_get_model_url_custom_tag():
    url = _get_model_url("v1.0.0")
    assert "v1.0.0" in url


# ===========================================================================
# _get_components
# ===========================================================================

def test_get_components_finds_declared():
    """Components with DependsOn Component should be found."""
    comps = _get_components(FIXTURE_ROWS)
    names = {c["name"] for c in comps}
    assert "Biospecimen" in names
    assert "scRNA-seq Level 1" in names


def test_get_components_discovers_referenced():
    """Clinical is referenced as a dep-component by Biospecimen, so should be discovered."""
    comps = _get_components(FIXTURE_ROWS)
    names = {c["name"] for c in comps}
    assert "Clinical" in names


def test_get_components_attribute_counts():
    comps = _get_components(FIXTURE_ROWS)
    by_name = {c["name"]: c for c in comps}
    assert by_name["Biospecimen"]["attribute_count"] == 3
    assert by_name["scRNA-seq Level 1"]["attribute_count"] == 3
    assert by_name["Clinical"]["attribute_count"] == 3


def test_get_components_dep_components():
    comps = _get_components(FIXTURE_ROWS)
    by_name = {c["name"]: c for c in comps}
    assert by_name["Biospecimen"]["depends_on_components"] == ["Clinical"]
    assert by_name["scRNA-seq Level 1"]["depends_on_components"] == ["Biospecimen"]
    # Discovered component has empty dep list
    assert by_name["Clinical"]["depends_on_components"] == []


def test_get_components_does_not_include_plain_attributes():
    comps = _get_components(FIXTURE_ROWS)
    names = {c["name"] for c in comps}
    assert "Barcode" not in names
    assert "File Format" not in names


# ===========================================================================
# _get_component_attributes
# ===========================================================================

def test_get_component_attributes_exact_match():
    name, attrs = _get_component_attributes(FIXTURE_ROWS, "Biospecimen")
    assert name == "Biospecimen"
    assert len(attrs) == 3
    attr_names = [a["name"] for a in attrs]
    assert "Biospecimen Type" in attr_names


def test_get_component_attributes_case_insensitive():
    name, attrs = _get_component_attributes(FIXTURE_ROWS, "biospecimen")
    assert name == "Biospecimen"


def test_get_component_attributes_required_flag():
    _, attrs = _get_component_attributes(FIXTURE_ROWS, "Biospecimen")
    by_name = {a["name"]: a for a in attrs}
    assert by_name["Biospecimen Type"]["required"] is True
    assert by_name["Preservation Method"]["required"] is False


def test_get_component_attributes_valid_values():
    _, attrs = _get_component_attributes(FIXTURE_ROWS, "Biospecimen")
    by_name = {a["name"]: a for a in attrs}
    assert by_name["Biospecimen Type"]["valid_values_count"] == 4
    assert "Bulk cells" in by_name["Biospecimen Type"]["valid_values_preview"]


def test_get_component_attributes_not_found():
    with pytest.raises(ValueError, match="not found"):
        _get_component_attributes(FIXTURE_ROWS, "NonexistentComponent")


def test_get_component_attributes_partial_match():
    """Partial match with single result should work."""
    name, attrs = _get_component_attributes(FIXTURE_ROWS, "scRNA-seq")
    assert name == "scRNA-seq Level 1"


def test_get_component_attributes_validation_rules():
    _, attrs = _get_component_attributes(FIXTURE_ROWS, "Biospecimen")
    by_name = {a["name"]: a for a in attrs}
    assert "regex" in by_name["HTAN Biospecimen ID"]["validation_rules"]


# ===========================================================================
# _find_attribute
# ===========================================================================

def test_find_attribute_exact():
    row = _find_attribute(FIXTURE_ROWS, "File Format")
    assert row["Attribute"] == "File Format"


def test_find_attribute_case_insensitive():
    row = _find_attribute(FIXTURE_ROWS, "file format")
    assert row["Attribute"] == "File Format"


def test_find_attribute_partial_unique():
    row = _find_attribute(FIXTURE_ROWS, "Barcode")
    assert row["Attribute"] == "Barcode"


def test_find_attribute_not_found():
    with pytest.raises(ValueError, match="not found"):
        _find_attribute(FIXTURE_ROWS, "ZZZnoexist")


def test_find_attribute_ambiguous():
    """'HTAN' matches multiple attributes."""
    with pytest.raises(ValueError, match="Ambiguous|Did you mean"):
        _find_attribute(FIXTURE_ROWS, "HTAN")


# ===========================================================================
# _get_dependency_chain
# ===========================================================================

def test_dependency_chain_linear():
    """scRNA-seq Level 1 → Biospecimen → Clinical."""
    chain = _get_dependency_chain(FIXTURE_ROWS, "scRNA-seq Level 1")
    names = [c["name"] for c in chain]
    assert names[0] == "scRNA-seq Level 1"
    assert "Biospecimen" in names
    assert "Clinical" in names


def test_dependency_chain_leaf():
    """Clinical has no outgoing deps, so chain is just itself."""
    chain = _get_dependency_chain(FIXTURE_ROWS, "Clinical")
    assert len(chain) == 1
    assert chain[0]["name"] == "Clinical"


def test_dependency_chain_partial_match():
    chain = _get_dependency_chain(FIXTURE_ROWS, "scRNA")
    assert chain[0]["name"] == "scRNA-seq Level 1"


def test_dependency_chain_not_found():
    with pytest.raises(ValueError, match="not found"):
        _get_dependency_chain(FIXTURE_ROWS, "ZZZNoComponent")


# ===========================================================================
# _categorize_component
# ===========================================================================

def test_categorize_clinical():
    assert _categorize_component("Demographics", "") == "Clinical"
    assert _categorize_component("Diagnosis", "") == "Clinical"
    assert _categorize_component("ClinicalTier1", "") == "Clinical"


def test_categorize_biospecimen():
    assert _categorize_component("Biospecimen", "") == "Biospecimen"


def test_categorize_sequencing():
    assert _categorize_component("scRNA-seq Level 1", "") == "Sequencing"
    assert _categorize_component("BulkRNA-seq Level 2", "") == "Sequencing"
    assert _categorize_component("BulkWES Level 1", "") == "Sequencing"


def test_categorize_imaging():
    assert _categorize_component("CyCIF Level 2", "") == "Imaging"
    assert _categorize_component("CODEX Level 1", "") == "Imaging"
    assert _categorize_component("H&E Image", "") == "Imaging"


def test_categorize_spatial():
    assert _categorize_component("10x Visium Level 1", "") == "Spatial Transcriptomics"
    assert _categorize_component("MERFISH Level 1", "") == "Spatial Transcriptomics"


def test_categorize_proteomics():
    assert _categorize_component("Mass Spec Level 1", "") == "Proteomics"
    assert _categorize_component("RPPA Level 2", "") == "Proteomics"


def test_categorize_by_parent():
    assert _categorize_component("SomeUnknownAssay", "Sequencing") == "Sequencing"


def test_categorize_other():
    assert _categorize_component("UnknownThing", "") == "Other"


# ===========================================================================
# DataModel (with mocked _load_model)
# ===========================================================================

def test_datamodel_components(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    comps = dm.components()
    names = {c["name"] for c in comps}
    assert "Biospecimen" in names
    assert "scRNA-seq Level 1" in names


def test_datamodel_attributes(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    name, attrs = dm.attributes("Biospecimen")
    assert name == "Biospecimen"
    assert len(attrs) == 3


def test_datamodel_describe(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    detail = dm.describe("File Format")
    assert detail["attribute"] == "File Format"
    assert detail["description"] == "Format of the data file"
    assert "fastq" in detail["valid_values"]
    assert isinstance(detail["depends_on"], list)


def test_datamodel_valid_values(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    vv = dm.valid_values("Gender")
    assert "male" in vv
    assert "female" in vv


def test_datamodel_valid_values_empty(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    vv = dm.valid_values("Barcode")
    assert vv == []


def test_datamodel_search(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    results = dm.search("barcode")
    assert len(results) >= 1
    assert any(r["name"] == "Barcode" for r in results)
    assert any("name" in r["match_in"] for r in results)


def test_datamodel_search_in_description(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    results = dm.search("identifier")
    assert any("description" in r["match_in"] for r in results)


def test_datamodel_search_in_valid_values(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    results = dm.search("fastq")
    assert any("valid values" in r["match_in"] for r in results)


def test_datamodel_search_no_results(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    results = dm.search("zzz_nothing_matches")
    assert results == []


def test_datamodel_required(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    req = dm.required("Biospecimen")
    names = [a["name"] for a in req]
    assert "Biospecimen Type" in names
    assert "HTAN Biospecimen ID" in names
    # Preservation Method is not required
    assert "Preservation Method" not in names


def test_datamodel_deps(monkeypatch):
    monkeypatch.setattr("htan.model._load_model", lambda tag=None: FIXTURE_ROWS)
    dm = DataModel()
    chain = dm.deps("scRNA-seq Level 1")
    names = [c["name"] for c in chain]
    assert "scRNA-seq Level 1" in names
    assert "Biospecimen" in names


# ===========================================================================
# Formatting helpers
# ===========================================================================

def test_format_components_text():
    comps = _get_components(FIXTURE_ROWS)
    text = _format_components_text(comps)
    assert "Biospecimen" in text
    assert "Total:" in text


def test_format_components_text_categories():
    comps = _get_components(FIXTURE_ROWS)
    text = _format_components_text(comps)
    # Should have at least one category header
    assert "===" in text


def test_format_attributes_text():
    name, attrs = _get_component_attributes(FIXTURE_ROWS, "Biospecimen")
    text = _format_attributes_text(name, attrs)
    assert "Component: Biospecimen" in text
    assert "Attributes: 3" in text
    assert "Biospecimen Type" in text


def test_format_describe_text():
    detail = {
        "attribute": "File Format",
        "description": "Format of the data file",
        "required": True,
        "parent": "Assay",
        "source": "",
        "validation_rules": "",
        "depends_on": [],
        "depends_on_component": "",
        "valid_values": ["fastq", "bam", "h5ad"],
    }
    text = _format_describe_text(detail)
    assert "File Format" in text
    assert "Required: True" in text
    assert "fastq" in text


def test_format_describe_text_no_valid_values():
    detail = {
        "attribute": "Barcode",
        "description": "Sample barcode",
        "required": False,
        "parent": "Assay",
        "source": "",
        "validation_rules": "",
        "depends_on": [],
        "depends_on_component": "",
        "valid_values": [],
    }
    text = _format_describe_text(detail)
    assert "free text" in text


def test_format_deps_text():
    chain = _get_dependency_chain(FIXTURE_ROWS, "scRNA-seq Level 1")
    text = _format_deps_text(chain)
    assert "scRNA-seq Level 1" in text
    assert "Biospecimen" in text


def test_format_deps_text_empty():
    text = _format_deps_text([])
    assert "No dependency" in text
