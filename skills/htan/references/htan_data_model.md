# HTAN Data Model (Phase 1)

**Version**: v25.2.1 (2025-05-08, final Phase 1 release)
**Source**: [ncihtan/data-models](https://github.com/ncihtan/data-models)
**Stats**: 1,071 attributes across 64 manifest components
**Query tool**: `python3 scripts/htan_data_model.py`

---

## Component Catalog

The HTAN data model defines 64 manifest components — templates that specify which metadata attributes are required when submitting data. Components are organized by category:

### Clinical (7 components)

| Component | Attributes | Depends On |
|---|---|---|
| Patient | 2 | Demographics, Family History, Exposure, Follow Up, Diagnosis, Therapy, Molecular Test |
| Demographics | ~20 | — |
| Diagnosis | ~30 | — |
| Exposure | ~10 | — |
| Follow Up | ~15 | — |
| Therapy | ~15 | — |
| Molecular Test | ~15 | — |

Disease-specific Tier 3 components extend Diagnosis with specialized fields:
- **Breast Cancer Tier 3** — ER/PR/HER2 status, Oncotype DX score
- **Colorectal Cancer Tier 3** — MSI status, KRAS/BRAF mutations
- **Lung Cancer Tier 3** — EGFR/ALK/ROS1 status, smoking history
- **Sarcoma Tier 3** — Histological subtype, molecular markers

### Biospecimen (1 component)

| Component | Attributes | Depends On |
|---|---|---|
| Biospecimen | ~40 | — |

### Sequencing (12+ components)

| Component | Levels | Key Attributes |
|---|---|---|
| scRNA-seq | Level 1–4 | Library Construction Method, Dissociation Method, Single Cell Isolation Method |
| scATAC-seq | Level 1–4 | Library Construction Method, Transposase |
| snRNA-seq | Level 1–2 | Nuclei Isolation Method |
| CITE-seq | Level 1–4 | Antibody Panel |
| Bulk RNA-seq | Level 1–3 | Library Construction Method, Read Length |
| Bulk WES | Level 1–3 | Target Capture Kit, Coverage |
| Bulk WGS | Level 1–3 | Coverage, Platform |
| Bulk Methylation-seq | Level 1–3 | Library Construction Method |
| Hi-C-seq | Level 1–3 | Restriction Enzyme |
| ScDNA-seq | Level 1–3 | Library Construction Method |

Each level is a separate component (e.g., "scRNA-seq Level 1", "scRNA-seq Level 2").

### Imaging (6+ components)

| Component | Levels | Key Attributes |
|---|---|---|
| Imaging | Level 1–4 | Imaging Modality, Channel Metadata |
| Electron Microscopy | Level 1–2 | Magnification, Accelerating Voltage |

Imaging encompasses CyCIF, CODEX, MIBI, mIHC, H&E, IMC, and other modalities.

### Spatial Transcriptomics (6+ components)

| Component | Levels | Key Attributes |
|---|---|---|
| 10x Visium | Level 1–4 | Spot Count, Gene Count |
| 10x Xenium | Level 1–2 | Gene Panel |
| MERFISH | Level 1–2 | Probe Set |
| Slide-seq | Level 1–2 | Bead Size |
| NanoString GeoMx | Level 1–3 | ROI Selection Method |

### Proteomics (3+ components)

| Component | Key Attributes |
|---|---|
| RPPA | Antibody Panel |
| Mass Spectrometry (Label Free) | Instrument, Fragmentation Method |
| Mass Spectrometry (Isobaric Label) | Label Type, Plex Size |

### Other

| Component | Purpose |
|---|---|
| Other Assay | Catch-all for assays not yet in the model |
| Auxiliary File | Supporting files (e.g., antibody panels, gene lists) |

Use `python3 scripts/htan_data_model.py components` for the complete list with exact attribute counts.

---

## Key Controlled Vocabularies

These are the most commonly needed valid-value sets. Use `python3 scripts/htan_data_model.py valid-values "Attribute Name"` for the complete list of any attribute.

### File Format

hdf5, bam, fastq, fastq.gz, tiff, OME-TIFF, svs, csv, tsv, txt, vcf, maf, bed, bigwig, h5ad, mtx, pdf, html, json, and ~80 more formats.

### Library Construction Method

10x 3' v2, 10x 3' v3, 10x 5' v1, 10x 5' v2, 10x Multiome, Smart-seq2, Drop-seq, CEL-seq2, inDrop, sci-RNA-seq, and more.

### Sequencing Platform

Illumina NovaSeq 6000, Illumina HiSeq 4000, Illumina NextSeq 500, Illumina MiSeq, PacBio Sequel II, Oxford Nanopore MinION, and more.

### Preservation Method

Fresh Frozen, FFPE (Formalin-Fixed Paraffin-Embedded), OCT (Optimal Cutting Temperature), Cryopreserved, Fresh, Snap Frozen, and more.

### Tumor Tissue Type

Tumor, Normal, Pre-cancer, Metastatic, Recurrent, Post-neoadjuvant therapy, and more.

### Dissociation Method

Enzymatic (Trypsin), Enzymatic (Collagenase), Mechanical, FACS, None, and more.

### Single Cell Isolation Method

10x Chromium, FACS, Fluidigm C1, Drop-seq, inDrop, Microwell, and more.

---

## Identifier Formats and Validation

The data model defines regex patterns for HTAN identifiers:

| Entity | Regex | Example |
|---|---|---|
| HTAN Participant ID | `^(HTA([1-9]\|1[0-6]))_((EXT)?([0-9]\d*\|0000))$` | HTA1_1001 |
| HTAN Biospecimen ID | `^(HTA([1-9]\|1[0-6]))_((EXT)?([0-9]\d*\|0000))_([0-9]\d*\|0000)$` | HTA1_1001_001 |
| HTAN Data File ID | `^(HTA([1-9]\|1[0-6]))_((EXT)?([0-9]\d*\|0000))_([0-9]\d*\|0000)$` | HTA9_1_19512 |
| Filename | `^.+\/\S*$` | path/to/file.fastq.gz |

### Center Numbering

| Number | Center | Phase |
|---|---|---|
| HTA1 | HTAPP | 1 |
| HTA2 | HMS | 1 |
| HTA3 | OHSU | 1 |
| HTA4 | MSK | 1 |
| HTA5 | Stanford | 1 |
| HTA6 | Vanderbilt | 1 |
| HTA7 | WUSTL | 1 |
| HTA8 | CHOP | 1 |
| HTA9 | Duke | 1 |
| HTA10 | BU | 1 |
| HTA11 | DFCI | 1 |
| HTA12 | TNP SARDANA | 2 |
| HTA13 | TNP SRRS | 2 |
| HTA14 | TNP TMA | 2 |

---

## Clinical Tiers

### Tier 1 (Required)

Minimum clinical annotations required for all HTAN participants:

| Component | Key Attributes |
|---|---|
| **Demographics** | Age at Diagnosis, Gender, Race, Ethnicity, Vital Status, Days to Birth, Year of Birth, Year of Death, Country of Residence |
| **Diagnosis** | Primary Diagnosis (ICD-O-3), Site of Resection or Biopsy, Tissue or Organ of Origin, Tumor Grade, AJCC Pathologic Stage, Morphology, Days to Diagnosis |
| **Exposure** | Tobacco Smoking Status, Pack Years Smoked, Alcohol History, BMI |
| **Follow Up** | Days to Follow Up, Disease Status, Progression or Recurrence, Vital Status at Follow Up |
| **Therapy** | Treatment Type, Therapeutic Agents, Treatment Outcome, Days to Treatment Start/End |
| **Molecular Test** | Gene Symbol, Molecular Analysis Method, Test Result |

### Tier 2 (Recommended)

Additional detail recommended for atlas-level annotation. Extended fields for each Tier 1 component plus Family History.

### Tier 3 (Disease-Specific)

Custom attributes for specific cancer types:
- **Breast**: ER Status, PR Status, HER2 Status, Oncotype DX Score, Ki-67
- **Colorectal**: MSI Status, KRAS Mutation, BRAF V600E, APC Mutation
- **Lung**: EGFR Mutation, ALK Rearrangement, ROS1 Rearrangement, PD-L1 Expression
- **Sarcoma**: FNCLCC Grade, Tumor Depth, Tumor Size

---

## Biospecimen Metadata

Key attributes tracked in the Biospecimen manifest:

| Attribute | Description |
|---|---|
| HTAN Biospecimen ID | Unique biospecimen identifier |
| HTAN Parent ID | Parent participant or biospecimen ID |
| Biospecimen Type | Tissue, Blood, Cell Line, Organoid, Xenograft |
| Site of Resection or Biopsy | Anatomical site (ICD-O-3 topography) |
| Preservation Method | Fresh Frozen, FFPE, OCT, etc. |
| Tumor Tissue Type | Tumor, Normal, Pre-cancer, Metastatic |
| Collection Days from Index | Days from index date to collection |
| Analyte Type | DNA, RNA, Protein, etc. |
| Adjacent Biospecimen IDs | Related biospecimens from same participant |

### Biospecimen Hierarchy

```
Participant (HTAN_Participant_ID)
  └── Biospecimen (HTAN_Biospecimen_ID)
        └── Derived biospecimen (sectioning, dissociation, etc.)
              └── Analyte (DNA, RNA, protein, etc.)
```

---

## Assay Data Levels

| Level | Description | Access Tier | Examples |
|---|---|---|---|
| **Level 1** | Raw data | Controlled | FASTQ, raw BAM, raw images |
| **Level 2** | Aligned/processed | Controlled | Aligned BAM, segmented images |
| **Level 3** | Derived quantification | Open | Gene expression matrices, cell segmentation |
| **Level 4** | Interpreted results | Open | Cell type annotations, spatial maps |

Each assay type defines level-specific manifests with attributes appropriate to that processing stage (e.g., Level 1 includes sequencing platform; Level 3 includes analysis pipeline version).

---

## Controlled Vocabularies (Ontologies)

| Domain | Standard |
|---|---|
| Diagnosis | ICD-O-3 (International Classification of Diseases for Oncology) |
| Anatomical site | Uberon |
| Cell type | Cell Ontology (CL) |
| Disease | NCIT (NCI Thesaurus) |
| Species | NCBI Taxonomy |
| Assay | OBI (Ontology for Biomedical Investigations) |
| Data format | EDAM |

---

## Using the Data Model Script

```bash
# Download/refresh model (no auth needed, stdlib only)
python3 scripts/htan_data_model.py fetch
python3 scripts/htan_data_model.py fetch --dry-run

# List all 64 components
python3 scripts/htan_data_model.py components
python3 scripts/htan_data_model.py components --format json

# List attributes for a component
python3 scripts/htan_data_model.py attributes "scRNA-seq Level 1"
python3 scripts/htan_data_model.py attributes "Biospecimen"
python3 scripts/htan_data_model.py attributes "Demographics"

# Full detail for one attribute
python3 scripts/htan_data_model.py describe "Library Construction Method"
python3 scripts/htan_data_model.py describe "File Format"

# List valid values
python3 scripts/htan_data_model.py valid-values "Preservation Method"
python3 scripts/htan_data_model.py valid-values "Single Cell Isolation Method"

# Search by keyword
python3 scripts/htan_data_model.py search "barcode"
python3 scripts/htan_data_model.py search "tumor"

# Required fields for a component
python3 scripts/htan_data_model.py required "Biospecimen"

# Dependency chain (e.g., scRNA-seq L1 → Biospecimen → Patient)
python3 scripts/htan_data_model.py deps "scRNA-seq Level 1"

# Use a different model version
python3 scripts/htan_data_model.py components --tag v24.9.1
```

Cache: `~/.cache/htan-skill/HTAN.model.csv` (auto-downloaded on first use)

---

## Phase 2 Note

Phase 2 of the HTAN data model uses **LinkML** (Linked Data Modeling Language) and is maintained at [ncihtan/htan-linkml](https://github.com/ncihtan/htan-linkml). The Phase 1 model (this document) covers all currently released HTAN data.
