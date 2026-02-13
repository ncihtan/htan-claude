# HTAN Documentation Manual Reference

The official HTAN Manual at **https://docs.humantumoratlas.org** provides comprehensive documentation for the Human Tumor Atlas Network. This reference summarizes its structure and key content so the skill can point users to the right pages.

## Site Map

The manual has 41 pages across 7 sections:

### Overview

| Page | URL | Summary |
|---|---|---|
| Introduction to HTAN | [/overview/introduction/](https://docs.humantumoratlas.org/overview/introduction/) | Network overview: NCI Cancer Moonshot initiative, ten Phase 2 research centers plus DCC, spatial profiling and scRNA-seq emphasis |
| HTAN Centers | [/overview/centers/](https://docs.humantumoratlas.org/overview/centers/) | Phase 2 centers (HTA200-HTA209): skin, pancreatic, glioma, gastric, myeloma, pediatric, prostate, colorectal, ovarian, lymphoma. Also lists 13 Phase 1 centers |
| Data Access and Data Releases | [/overview/data_access/](https://docs.humantumoratlas.org/overview/data_access/) | Two access tiers: open (de-identified clinical, biospecimen, processed genomics, images) and controlled (unprocessed genomic via dbGaP) |
| Tool Catalog | [/overview/tool_catalog/](https://docs.humantumoratlas.org/overview/tool_catalog/) | Computational tools, pipelines, and visualization methods developed by the HTAN network |

### Data Model

| Page | URL | Summary |
|---|---|---|
| Data Model Introduction | [/data_model/overview/](https://docs.humantumoratlas.org/data_model/overview/) | Common data model required for all centers. Phase 1 (2018-2025) and Phase 2 (2025-present). Aligns with GDC, Human Cell Atlas, HuBMAP, MITI standards |
| Identifiers | [/data_model/identifiers/](https://docs.humantumoratlas.org/data_model/identifiers/) | Unique ID system for participants, biospecimens ("B" prefix), and data files ("D" prefix). 50-character limit. Phase 2 regex patterns included |
| Relationship Model | [/data_model/relationships/](https://docs.humantumoratlas.org/data_model/relationships/) | Data traceability: participants -> biospecimens -> data files. ID Provenance BigQuery table for linkage |
| Data Levels | [/data_model/data_levels/](https://docs.humantumoratlas.org/data_model/data_levels/) | Clinical tiers (Tier 1: demographics/diagnosis/therapy/etc., Tier 2: center-specific). Assay levels 1-4 (raw -> processed). Levels 1-2 sequencing = controlled access |
| Specific Standards | [/data_model/standards/](https://docs.humantumoratlas.org/data_model/standards/) | Phase 1/2 file specs, scRNA-seq h5ad requirements aligned with CELLxGENE, metadata requirement summaries |

### Data Access

| Page | URL | Summary |
|---|---|---|
| Introduction | [/data_access/introduction/](https://docs.humantumoratlas.org/data_access/introduction/) | Data distribution overview: Synapse, dbGaP, BigQuery, IDC, SB-CGC, CELLxGENE, Xena, Minerva, cBioPortal |
| Citing HTAN | [/data_access/citing_htan/](https://docs.humantumoratlas.org/data_access/citing_htan/) | Two primary citations: Rozenblatt-Rosen et al. 2020 (Cell, DOI:10.1016/j.cell.2020.03.053) and de Bruijn et al. 2025 (Nature Methods, DOI:10.1038/s41592-025-02643-0). Plus dataset-specific citations on portal |
| Using the HTAN Data Portal | [/data_access/portal/](https://docs.humantumoratlas.org/data_access/portal/) | Interactive portal guide: filtering by Atlas/Assay/File type, metadata CSV downloads, open vs controlled access, download via Synapse/SB-CGC/Gen3/CELLxGENE |
| Requesting dbGaP Access | [/data_access/db_gap/](https://docs.humantumoratlas.org/data_access/db_gap/) | Step-by-step guide for dbGaP access to controlled data (study phs002371): research statement, institutional official, IT director, collaborator info |
| Google BigQuery | [/data_access/biq_query/](https://docs.humantumoratlas.org/data_access/biq_query/) | HTAN metadata in ISB-CGC BigQuery tables. Free tier: 1 TB/month. Access via portal or ISB-CGC UI. Single-cell and cell spatial tables. Community R/Python notebooks |
| Gen3-Client | [/data_access/cds_gen3/](https://docs.humantumoratlas.org/data_access/cds_gen3/) | CLI tool for downloading from NCI CRDC. Setup: get API key from nci-crdc.datacommons.io, configure profile, use `gen3-client download-multiple` with manifest |
| Accessing CRDC Data in SB-CGC | [/data_access/cds_cgc/](https://docs.humantumoratlas.org/data_access/cds_cgc/) | Transfer data to Seven Bridges Cancer Genomics Cloud: direct export or DRS manifest. Covers imaging and controlled-access sequencing |
| Synapse to SB-CGC | [/data_access/synapse_to_cds/](https://docs.humantumoratlas.org/data_access/synapse_to_cds/) | Loading Synapse open-access data into SB-CGC via JupyterLab Data Studio |

### Data Visualization

| Page | URL | Summary |
|---|---|---|
| CellxGene | [/data_visualization/cell_by_gene/](https://docs.humantumoratlas.org/data_visualization/cell_by_gene/) | CZI partnership for scRNA-seq visualization, accessible from portal |
| Xena | [/data_visualization/xena/](https://docs.humantumoratlas.org/data_visualization/xena/) | UCSC Xena for multiomics visualization (sc/snRNA-seq, t-CyCIF) |
| Minerva | [/data_visualization/minerva/](https://docs.humantumoratlas.org/data_visualization/minerva/) | Harvard tool for interactive multiplex imaging: zooming, channel selection, annotations |

### Data Submission (for HTAN centers)

| Page | URL | Summary |
|---|---|---|
| Overview | [/data_submission/overview/](https://docs.humantumoratlas.org/data_submission/overview/) | Authorized centers submit de-identified data through Synapse |
| New Centers | [/data_submission/information_new_centers/](https://docs.humantumoratlas.org/data_submission/information_new_centers/) | 8-step onboarding checklist |
| Checklist | [/data_submission/checklist/](https://docs.humantumoratlas.org/data_submission/checklist/) | 9-criterion data acceptance checklist |
| Data Liaisons | [/data_submission/data_liaisons/](https://docs.humantumoratlas.org/data_submission/data_liaisons/) | DCC liaison contacts per center |
| Creating IDs | [/data_submission/creating_ids/](https://docs.humantumoratlas.org/data_submission/creating_ids/) | Guide for creating participant/biospecimen/file IDs |
| De-identification | [/data_submission/data_deidentification/](https://docs.humantumoratlas.org/data_submission/data_deidentification/) | HIPAA compliance, IRB approval, file naming rules |
| Metadata | [/data_submission/metadata/](https://docs.humantumoratlas.org/data_submission/metadata/) | Metadata categories and Synapse-based submission |
| Index Date | [/data_submission/dates/](https://docs.humantumoratlas.org/data_submission/dates/) | Date-to-days conversion using birth as index date |
| Submitting Assay Data | [/data_submission/clin_biospec_assay/](https://docs.humantumoratlas.org/data_submission/clin_biospec_assay/) | 3-step submission via Synapse curator |
| Clinical Data | [/data_submission/clin_data_submission/](https://docs.humantumoratlas.org/data_submission/clin_data_submission/) | Phase 2 clinical metadata: Tier 1 (8 categories) and Tier 2 (flexible CSV) |
| sc/snRNA-seq Data | [/data_submission/scrnaseq_data_submission/](https://docs.humantumoratlas.org/data_submission/scrnaseq_data_submission/) | h5ad file requirements, CELLxGENE alignment, GENCODE v44, HTAN-h5ad-validator |

### Additional Information

| Page | URL | Summary |
|---|---|---|
| Tools and Protocols | [/addtnl_info/tool_protocol/](https://docs.humantumoratlas.org/addtnl_info/tool_protocol/) | Contributing tools to portal, protocols.io documentation |
| Publications | [/addtnl_info/publications/](https://docs.humantumoratlas.org/addtnl_info/publications/) | Linking publications to specimen files |
| Data Release | [/addtnl_info/data_release/](https://docs.humantumoratlas.org/addtnl_info/data_release/) | DCC releases every 4-6 months via portal, Cancer Data Service, ISB-CGC |
| Governance | [/addtnl_info/governance/](https://docs.humantumoratlas.org/addtnl_info/governance/) | Data sharing agreements, HIPAA, CC-BY 4.0 for imaging, 7 policy documents |
| Usage Analytics | [/addtnl_info/usage_analytics/](https://docs.humantumoratlas.org/addtnl_info/usage_analytics/) | Portal usage statistics and data submission trends |
| Working Groups | [/addtnl_info/wg_internal/](https://docs.humantumoratlas.org/addtnl_info/wg_internal/) | Internal communications (Synapse Wiki, restricted access) |
| RFC Process | [/addtnl_info/rfc/](https://docs.humantumoratlas.org/addtnl_info/rfc/) | Community-driven data model changes via RFC |
| TNPs | [/addtnl_info/tnps/](https://docs.humantumoratlas.org/addtnl_info/tnps/) | Trans-Network Projects: SARDANA, TMA, SRRS, CASI |

### FAQ

| Page | URL | Summary |
|---|---|---|
| FAQ | [/faq/](https://docs.humantumoratlas.org/faq/) | Common questions about HTAN mission, data types, access, privacy, and support |

## Key Facts for Quick Reference

### Citing HTAN

When users work with HTAN data, they should cite:

1. **Rozenblatt-Rosen et al.** "The Human Tumor Atlas Network: Charting Tumor Transitions across Space and Time at Single-Cell Resolution." *Cell* 181(2):236-249 (2020). DOI: [10.1016/j.cell.2020.03.053](https://doi.org/10.1016/j.cell.2020.03.053)
2. **de Bruijn et al.** "Sharing data from the Human Tumor Atlas Network through standards, infrastructure and community engagement." *Nature Methods* (2025). DOI: [10.1038/s41592-025-02643-0](https://doi.org/10.1038/s41592-025-02643-0)

Plus dataset-specific citations from the portal's Publications tab.

### Phase 2 Identifier Formats

| Entity | Pattern | Example |
|---|---|---|
| Participant | `HTA2XX_integer` | `HTA209_1` |
| Biospecimen | `HTA2XX_integer_Binteger` | `HTA209_1_B1` |
| Data File | `HTA2XX_integer_Dinteger` | `HTA209_1_D12` |
| Pooled | `HTA2XX_0000_B/Dinteger` | `HTA209_0000_B1` |
| Control | `HTA2XX_EXTn_B/Dinteger` | `HTA209_EXT1_B1` |

Phase 1 IDs use center prefixes HTA1-HTA14 with numeric suffixes (e.g., `HTA9_1_19512`).

### Data Levels

| Level | Content | Access |
|---|---|---|
| Level 1 | Raw data (FASTQ, raw images) | Controlled (sequencing), Open (some imaging) |
| Level 2 | Aligned/processed (BAM, segmented images) | Controlled (sequencing), Open (imaging) |
| Level 3 | Quantified (gene expression matrices, cell quantification) | Open |
| Level 4 | Analysis-ready (annotated h5ad, cell type labels) | Open |
| Auxiliary | Supporting files | Open |

### Clinical Metadata Tiers (Phase 2)

**Tier 1** (structured, standardized): Demographics, Diagnosis, Family History, Exposure, Molecular Test, Therapy, Follow Up, Vital Status

**Tier 2** (flexible): Center-specific CSV with HTAN Participant ID + custom columns

### Data Distribution Platforms

| Platform | Data Type | Auth Required |
|---|---|---|
| **HTAN Data Portal** | Browse/filter all data, download metadata CSVs | None (browsing), Synapse account (download) |
| **Synapse** | Open-access assay files | Synapse account + token |
| **dbGaP** | Controlled-access genomic data authorization | NIH eRA Commons + dbGaP application |
| **Gen3/CRDC** | Controlled-access file downloads | Gen3 credentials (after dbGaP approval) |
| **BigQuery (ISB-CGC)** | Metadata tables, single-cell tables | Google account (free tier: 1 TB/month) |
| **SB-CGC** | Cloud-based analysis of HTAN data | Seven Bridges account |
| **CELLxGENE** | scRNA-seq visualization and h5ad download | None |
| **UCSC Xena** | Multiomics visualization | None |
| **Minerva** | Multiplex imaging visualization | None |
| **cBioPortal** | Genomic data exploration | None |

### Key External URLs

| Resource | URL |
|---|---|
| HTAN Manual | https://docs.humantumoratlas.org |
| HTAN Data Portal | https://data.humantumoratlas.org |
| Portal Explore Page | https://data.humantumoratlas.org/explore |
| Portal Standards | https://data.humantumoratlas.org/standards |
| dbGaP Study | https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002371 |
| NCI CRDC Portal | https://nci-crdc.datacommons.io |
| ISB-CGC | https://isb-cgc.appspot.com |
| Synapse | https://www.synapse.org |
| Phase 2 Data Model Docs | https://htan2-data-model.readthedocs.io/en/main/ |
| Phase 1 Data Model (GitHub) | https://github.com/ncihtan/data-models |
| Phase 2 Data Model (GitHub) | https://github.com/ncihtan/htan2-data-model |
| HTAN Help Desk | Available via docs.humantumoratlas.org |

### Frequently Asked Questions

- **Who can use HTAN data?** Anyone — researchers, clinicians, students. Open to the public.
- **Do I need an account?** No for browsing; Synapse account for open-access downloads; dbGaP for controlled data.
- **What data types?** Genomic, transcriptomic, proteomic, single-cell, imaging/spatial across cancer stages.
- **Can I upload data?** No, the portal does not support user uploads.
- **Is there 3D data?** Yes — CyCIF serial sections and electron microscopy datasets.
- **Is there temporal data?** Yes — precancerous vs cancerous comparisons and longitudinal treatment info.
- **How often is data released?** Every 4-6 months.
- **BigQuery cost?** Free tier allows 1 TB/month of queries at no cost.
- **How to cite?** See the citing section above; also cite dataset-specific publications.
