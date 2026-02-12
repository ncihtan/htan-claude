# HTAN Data Model

This document describes the HTAN data model including clinical tiers, biospecimen metadata, assay data levels, and identifier formats.

---

## Clinical Data Tiers

HTAN clinical data is organized into three tiers of increasing detail:

### Tier 1 (Required)

Minimum required clinical annotations for all HTAN participants.

| Category | Key Attributes |
|----------|---------------|
| **Demographics** | Age at diagnosis, sex, race, ethnicity, vital status |
| **Diagnosis** | Primary diagnosis (ICD-O-3), site of resection, tumor grade, stage |
| **Treatment** | Treatment type, therapeutic agent, treatment outcome |
| **Follow-up** | Disease status, progression/recurrence, vital status at follow-up |

### Tier 2 (Recommended)

Additional clinical detail recommended for atlas-level annotation.

| Category | Key Attributes |
|----------|---------------|
| **Demographics** | Country of residence, education level |
| **Diagnosis** | Histological subtype, molecular markers, TNM staging details |
| **Exposure** | Tobacco use, alcohol use, BMI |
| **Family History** | Family history of cancer, relationship, cancer type |
| **Treatment** | Dosage, duration, response criteria |

### Tier 3 (Atlas-Specific)

Custom clinical attributes defined by individual atlas centers.

---

## Biospecimen Metadata

Biospecimen metadata tracks the chain from participant to sample to analyte.

### Key Attributes

| Attribute | Description | Example |
|-----------|-------------|---------|
| `HTAN_Biospecimen_ID` | Unique biospecimen identifier | `HTA1_1001_001` |
| `HTAN_Participant_ID` | Parent participant identifier | `HTA1_1001` |
| `Biospecimen_Type` | Type of specimen | Tissue, Blood, Cell Line |
| `Site_of_Resection` | Anatomical site | Breast, Colon |
| `Preservation_Method` | How specimen was preserved | Fresh Frozen, FFPE, OCT |
| `Tumor_Tissue_Type` | Tumor vs normal classification | Tumor, Normal, Pre-cancer |
| `Collection_Days_from_Index` | Days from index date to collection | 0, 365 |
| `Adjacent_Biospecimen_IDs` | Related biospecimens | HTA1_1001_002 |

### Biospecimen Hierarchy

```
Participant (HTAN_Participant_ID)
  └── Biospecimen (HTAN_Biospecimen_ID)
        └── Derived biospecimen (sectioning, dissociation, etc.)
              └── Analyte (DNA, RNA, protein, etc.)
```

---

## Assay Data Levels

HTAN data progresses through processing levels:

| Level | Description | Access Tier | Examples |
|-------|-------------|-------------|---------|
| **Level 1** | Raw data | Controlled | FASTQ, raw BAM, raw images |
| **Level 2** | Aligned/processed data | Controlled | Aligned BAM, segmented images |
| **Level 3** | Derived quantification | Open* | Gene expression matrices, cell segmentation |
| **Level 4** | Interpreted results | Open | Cell type annotations, spatial maps |

*Level 3 data may be controlled if derived from controlled inputs.

---

## Assay Types

### Single-Cell Genomics

| Assay | Description | Key Metadata |
|-------|-------------|--------------|
| **scRNA-seq** | Single-cell RNA sequencing | Platform, library strategy, cell count |
| **scATAC-seq** | Single-cell chromatin accessibility | Platform, peak caller, cell count |
| **snRNA-seq** | Single-nucleus RNA sequencing | Nuclei isolation method |
| **CITE-seq** | Cellular indexing of transcriptomes and epitopes | Antibody panel |

### Bulk Genomics

| Assay | Description | Key Metadata |
|-------|-------------|--------------|
| **Bulk RNA-seq** | Bulk RNA sequencing | Library strategy, read length |
| **Bulk WES** | Whole-exome sequencing | Target capture kit, coverage |
| **Bulk WGS** | Whole-genome sequencing | Coverage, platform |

### Imaging

| Assay | Description | Key Metadata |
|-------|-------------|--------------|
| **CyCIF** | Cyclic immunofluorescence | Antibody panel, cycle count |
| **CODEX** | CO-Detection by indEXing | Antibody panel |
| **MIBI** | Multiplexed ion beam imaging | Antibody panel |
| **mIHC** | Multiplex immunohistochemistry | Marker panel |
| **H&E** | Hematoxylin and eosin staining | Magnification, scanner |
| **IMC** | Imaging mass cytometry | Antibody panel |
| **MERFISH** | Multiplexed error-robust FISH | Gene panel |
| **10x Visium** | Spatial transcriptomics | Spot count, gene count |

---

## HTAN Identifier Formats

HTAN uses hierarchical identifiers:

| Entity | Format | Example |
|--------|--------|---------|
| Center | `HTAn` (n = center number) | `HTA1` (HTAPP) |
| Participant | `HTAn_NNNN` | `HTA1_1001` |
| Biospecimen | `HTAn_NNNN_NNN` | `HTA1_1001_001` |
| File | `HTAn_NNNN_NNN_NNN` | `HTA1_1001_001_001` |

### Center Numbering

| Number | Center |
|--------|--------|
| HTA1 | HTAPP |
| HTA2 | HMS |
| HTA3 | OHSU |
| HTA4 | MSK |
| HTA5 | Stanford |
| HTA6 | Vanderbilt |
| HTA7 | WUSTL |
| HTA8 | CHOP |
| HTA9 | Duke |
| HTA10 | BU |
| HTA11 | DFCI |
| HTA12 | TNP SARDANA |
| HTA13 | TNP SRRS |
| HTA14 | TNP TMA |

---

## Controlled Vocabularies

HTAN uses standard ontologies and controlled vocabularies:

| Domain | Standard |
|--------|----------|
| Diagnosis | ICD-O-3 (International Classification of Diseases for Oncology) |
| Anatomical site | Uberon |
| Cell type | Cell Ontology (CL) |
| Disease | NCIT (NCI Thesaurus) |
| Species | NCBI Taxonomy |
| Assay | OBI (Ontology for Biomedical Investigations) |
