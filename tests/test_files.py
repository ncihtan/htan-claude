"""Unit tests for htan.files — access tier inference."""

from htan.files import infer_access_tier, FILE_ID_PATTERN


# --- infer_access_tier ---

def test_level3_is_synapse():
    assert infer_access_tier("HTA1_1_1", level="Level 3", assay="scRNA-seq") == "synapse"


def test_level4_is_synapse():
    assert infer_access_tier("HTA1_1_1", level="Level 4", assay="scRNA-seq") == "synapse"


def test_auxiliary_is_synapse():
    assert infer_access_tier("HTA1_1_1", level="Auxiliary", assay="scRNA-seq") == "synapse"


def test_other_is_synapse():
    assert infer_access_tier("HTA1_1_1", level="Other", assay="scRNA-seq") == "synapse"


def test_level1_scrnaseq_is_gen3():
    assert infer_access_tier("HTA1_1_1", level="Level 1", assay="scRNA-seq") == "gen3"


def test_level2_bulkrna_is_gen3():
    assert infer_access_tier("HTA1_1_1", level="Level 2", assay="Bulk RNA-seq") == "gen3"


def test_codex_level1_is_synapse():
    assert infer_access_tier("HTA1_1_1", level="Level 1", assay="CODEX") == "synapse"


def test_specialized_assays_are_synapse():
    for assay in ["Electron Microscopy", "RPPA", "10x Visium", "Mass Spec"]:
        assert infer_access_tier("HTA1_1_1", level="Level 1", assay=assay) == "synapse"


def test_no_info_is_unknown():
    assert infer_access_tier("HTA1_1_1") == "unknown"


def test_case_insensitive():
    assert infer_access_tier("HTA1_1_1", level="level 3", assay="scrna-seq") == "synapse"


# --- FILE_ID_PATTERN ---

def test_valid_file_id():
    assert FILE_ID_PATTERN.match("HTA9_1_19512")
    assert FILE_ID_PATTERN.match("HTA12_34_567")


def test_invalid_file_id():
    assert not FILE_ID_PATTERN.match("INVALID_ID")
    assert not FILE_ID_PATTERN.match("syn12345")
