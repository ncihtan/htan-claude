# HTAN BigQuery Table Reference

HTAN metadata is available in Google BigQuery via the ISB-CGC (Institute for Systems Biology - Cancer Genomics Cloud) project.

---

## Datasets

| Dataset | Description | Usage |
|---------|-------------|-------|
| `isb-cgc-bq.HTAN` | `_current` tables that always point to the latest release | General queries (default) |
| `isb-cgc-bq.HTAN_versioned` | Versioned snapshots with `_rN` suffixes (e.g., `_r7`) | Reproducible analyses |

### Current vs Versioned

- **Default (`isb-cgc-bq.HTAN`)**: Use `_current` suffix (e.g., `clinical_tier1_demographics_current`). These tables always point to the latest data release, so queries stay up-to-date without code changes.
- **Versioned (`isb-cgc-bq.HTAN_versioned`)**: Use `_rN` suffix (e.g., `clinical_tier1_demographics_r7`). Pin to a specific release for reproducible analyses. Use `python3 scripts/htan_bigquery.py tables --versioned` to list available versions.

---

## Table Naming Convention

```
{category}_{suffix}
```

For the current dataset:
```
isb-cgc-bq.HTAN.{category}_current
```

For the versioned dataset:
```
isb-cgc-bq.HTAN_versioned.{category}_{version}
```

Example: `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`
Example: `isb-cgc-bq.HTAN_versioned.clinical_tier1_demographics_r7`

---

## Clinical Tables

### Demographics

**Table**: `clinical_tier1_demographics_current`

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `HTAN_Participant_ID` | STRING | Participant identifier | `HTA1_1001` |
| `HTAN_Center` | STRING | Atlas center | `HTAN HTAPP`, `HTAN HMS` |
| `Age_at_Diagnosis` | INTEGER | Age in days at diagnosis | 18250 |
| `Gender` | STRING | Gender | `male`, `female` |
| `Race` | STRING | Race | `white`, `black or african american` |
| `Ethnicity` | STRING | Ethnicity | `not hispanic or latino` |
| `Vital_Status` | STRING | Vital status | `Alive`, `Dead` |

### Diagnosis

**Table**: `clinical_tier1_diagnosis_current`

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `HTAN_Participant_ID` | STRING | Participant identifier | `HTA1_1001` |
| `HTAN_Center` | STRING | Atlas center | `HTAN HMS` |
| `Primary_Diagnosis` | STRING | ICD-O-3 diagnosis | `Infiltrating duct carcinoma, NOS` |
| `Site_of_Resection_or_Biopsy` | STRING | Anatomical site | `Breast, NOS` |
| `Tumor_Grade` | STRING | Tumor grade | `G2`, `G3` |
| `AJCC_Pathologic_Stage` | STRING | AJCC stage | `Stage IIA`, `Stage IIIC` |
| `Morphology` | STRING | ICD-O-3 morphology code | `8500/3` |
| `Tissue_or_Organ_of_Origin` | STRING | Origin tissue/organ | `Breast` |

### Follow-up

**Table**: `clinical_tier1_followup_current`

| Column | Type | Description |
|--------|------|-------------|
| `HTAN_Participant_ID` | STRING | Participant identifier |
| `Days_to_Follow_Up` | INTEGER | Days from index to follow-up |
| `Disease_Status` | STRING | Disease status at follow-up |
| `Progression_or_Recurrence` | STRING | Whether progression occurred |

---

## Biospecimen Tables

**Table**: `biospecimen_current`

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `HTAN_Biospecimen_ID` | STRING | Biospecimen identifier | `HTA1_1001_001` |
| `HTAN_Participant_ID` | STRING | Parent participant | `HTA1_1001` |
| `HTAN_Center` | STRING | Atlas center | `HTAN HTAPP` |
| `Biospecimen_Type` | STRING | Specimen type | `Tissue Biospecimen Type` |
| `Site_of_Resection` | STRING | Anatomical site | `Breast` |
| `Preservation_Method` | STRING | Preservation | `Fresh Frozen`, `FFPE` |
| `Tumor_Tissue_Type` | STRING | Tissue classification | `Tumor`, `Normal` |
| `Collection_Days_from_Index` | INTEGER | Days from index to collection | 0 |

---

## Assay Metadata Tables

**Note:** All assay metadata tables include `File_Size` (INTEGER, bytes) and `entityId` (STRING, Synapse ID).

### Single-Cell RNA-seq

**Table**: `scRNAseq_current` (or `scRNA-seq_current`)

| Column | Type | Description |
|--------|------|-------------|
| `HTAN_Biospecimen_ID` | STRING | Source biospecimen |
| `HTAN_Data_File_ID` | STRING | File identifier |
| `scRNAseq_Workflow_Type` | STRING | Analysis workflow |
| `Library_Construction_Method` | STRING | Library prep (e.g., `10x 3' v3`) |
| `Dissociation_Method` | STRING | Tissue dissociation method |
| `Cell_Total` | INTEGER | Total cells sequenced |
| `File_Size` | INTEGER | File size in bytes |
| `entityId` | STRING | Synapse ID for download |

### Single-Cell ATAC-seq

**Table**: `scATACseq_current` (or `scATAC-seq_current`)

| Column | Type | Description |
|--------|------|-------------|
| `HTAN_Biospecimen_ID` | STRING | Source biospecimen |
| `HTAN_Data_File_ID` | STRING | File identifier |
| `Library_Construction_Method` | STRING | Library prep |
| `Cell_Total` | INTEGER | Total cells |

### Bulk RNA-seq

**Table**: `bulkRNAseq_current` (or `bulk_RNA-seq_current`)

| Column | Type | Description |
|--------|------|-------------|
| `HTAN_Biospecimen_ID` | STRING | Source biospecimen |
| `HTAN_Data_File_ID` | STRING | File identifier |
| `Library_Construction_Method` | STRING | Library prep |
| `Read_Length` | INTEGER | Sequencing read length |

### Imaging Level 2

**Table**: `imaging_level_2_current`

| Column | Type | Description |
|--------|------|-------------|
| `HTAN_Biospecimen_ID` | STRING | Source biospecimen |
| `HTAN_Data_File_ID` | STRING | File identifier |
| `Imaging_Assay_Type` | STRING | Assay (CyCIF, CODEX, etc.) |
| `Channel_Metadata_Filename` | STRING | Channel metadata reference |

---

## Discovering Available Tables and Versions

List all HTAN tables (current):

```sql
SELECT table_name
FROM `isb-cgc-bq.HTAN.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name
```

List all versioned tables:

```sql
SELECT table_name
FROM `isb-cgc-bq.HTAN_versioned.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name
```

Find all versions of a specific table:

```sql
SELECT table_name
FROM `isb-cgc-bq.HTAN_versioned.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE 'clinical_tier1_demographics%'
ORDER BY table_name DESC
```

---

## Example Queries

### Count participants by center

```sql
SELECT HTAN_Center, COUNT(DISTINCT HTAN_Participant_ID) as participant_count
FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current`
GROUP BY HTAN_Center
ORDER BY participant_count DESC
```

### Breast cancer patients with demographics

```sql
SELECT d.HTAN_Participant_ID, d.Gender, d.Age_at_Diagnosis,
       dx.Primary_Diagnosis, dx.AJCC_Pathologic_Stage
FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current` d
JOIN `isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current` dx
  ON d.HTAN_Participant_ID = dx.HTAN_Participant_ID
WHERE dx.Tissue_or_Organ_of_Origin = 'Breast'
LIMIT 100
```

### Biospecimens by preservation method

```sql
SELECT Preservation_Method, COUNT(*) as count
FROM `isb-cgc-bq.HTAN.biospecimen_current`
WHERE Preservation_Method IS NOT NULL
GROUP BY Preservation_Method
ORDER BY count DESC
```

### scRNA-seq datasets by center

```sql
SELECT b.HTAN_Center, COUNT(DISTINCT s.HTAN_Data_File_ID) as file_count,
       SUM(CAST(s.Cell_Total AS INT64)) as total_cells
FROM `isb-cgc-bq.HTAN.scRNAseq_current` s
JOIN `isb-cgc-bq.HTAN.biospecimen_current` b
  ON s.HTAN_Biospecimen_ID = b.HTAN_Biospecimen_ID
GROUP BY b.HTAN_Center
ORDER BY total_cells DESC
```

### Find 10 smallest open-access scRNA-seq breast files

```sql
SELECT s.HTAN_Data_File_ID, s.Filename, s.File_Size, s.entityId
FROM `isb-cgc-bq.HTAN.scRNAseq_level3_metadata_current` s
WHERE s.File_Size > 0
ORDER BY s.File_Size ASC
LIMIT 10
```

### Available imaging assay types

```sql
SELECT Imaging_Assay_Type, COUNT(*) as count
FROM `isb-cgc-bq.HTAN.imaging_level_2_current`
WHERE Imaging_Assay_Type IS NOT NULL
GROUP BY Imaging_Assay_Type
ORDER BY count DESC
```

### Full participant profile (demographics + diagnosis + biospecimens)

```sql
SELECT d.HTAN_Participant_ID, d.HTAN_Center, d.Gender,
       dx.Primary_Diagnosis, dx.AJCC_Pathologic_Stage,
       COUNT(DISTINCT b.HTAN_Biospecimen_ID) as biospecimen_count
FROM `isb-cgc-bq.HTAN.clinical_tier1_demographics_current` d
LEFT JOIN `isb-cgc-bq.HTAN.clinical_tier1_diagnosis_current` dx
  ON d.HTAN_Participant_ID = dx.HTAN_Participant_ID
LEFT JOIN `isb-cgc-bq.HTAN.biospecimen_current` b
  ON d.HTAN_Participant_ID = b.HTAN_Participant_ID
GROUP BY d.HTAN_Participant_ID, d.HTAN_Center, d.Gender,
         dx.Primary_Diagnosis, dx.AJCC_Pathologic_Stage
ORDER BY biospecimen_count DESC
LIMIT 100
```
