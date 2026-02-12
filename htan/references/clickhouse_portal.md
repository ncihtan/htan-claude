# HTAN Portal ClickHouse Reference

The HTAN data portal (data.humantumoratlas.org) uses a **ClickHouse cloud database** as its runtime query backend. Public read-only credentials are embedded in the portal's browser JavaScript, enabling direct SQL queries via the ClickHouse HTTP interface.

## Connection Details

| Setting | Value |
|---|---|
| Host | `REDACTED_HOST` |
| Port | `8443` (HTTPS) |
| User | `REDACTED_USER` |
| Password | `REDACTED_PASSWORD` |
| Database | `htan_2026_01_08` (changes with portal releases) |
| Protocol | HTTP POST with Basic Auth |

### HTTP Interface

```bash
curl -s "https://REDACTED_HOST:8443/" \
  -u "REDACTED_USER:REDACTED_PASSWORD" \
  --data-urlencode "query=SELECT count() FROM files" \
  --data-urlencode "default_format=JSONEachRow" \
  --data-urlencode "database=htan_2026_01_08"
```

## Database Schema

The database contains 7 tables:

### `files` (primary table, ~67K rows)

The most important table — contains file metadata AND download coordinates.

| Column | Type | Description |
|---|---|---|
| `DataFileID` | String | HTAN_Data_File_ID (e.g., `HTA9_1_19512`) |
| `Filename` | String | Original filename |
| `FileFormat` | String | File format (e.g., fastq, bam, h5ad, ome.tif) |
| `assayName` | String | Assay type (e.g., scRNA-seq, CyCIF, CODEX, Bulk RNA-seq) |
| `level` | String | Data level (Level 1, Level 2, Level 3, Level 4, Auxiliary, Other) |
| `organType` | **Array(String)** | Organ type (e.g., `['Breast']`, `['Colon']`) |
| `atlas_name` | String | Atlas center (e.g., HTAN HMS, HTAN WUSTL) |
| `synapseId` | String | Synapse entity ID for open-access download |
| `viewers` | String | JSON with nested download coordinates (contains DRS URI for Gen3) |
| `downloadSource` | String | Download platform indicator (e.g., `dbGaP`) |
| `Gender` | **Array(String)** | Patient gender |
| `Race` | **Array(String)** | Patient race |
| `PrimaryDiagnosis` | **Array(String)** | Diagnosis |
| `TissueorOrganofOrigin` | **Array(String)** | Organ of origin |
| `biospecimenIds` | **Array(String)** | Related biospecimen IDs |
| `Component` | String | Data component type |
| `isRawSequencing` | String | Whether file is raw sequencing data |

Note: Several columns in the `files` table are `Array(String)` and require `arrayExists()` for filtering. Use `DESCRIBE files` for the full 34-column schema.

**Extracting DRS URIs from `viewers`:**
```sql
JSONExtractString(viewers, 'crdcGc', 'drs_uri') as drs_uri
```

### `demographics` (~2,890 rows)

| Column | Type | Description |
|---|---|---|
| `HTANParticipantID` | String | Participant identifier |
| `Gender` | String | Patient gender (male, female) |
| `Race` | String | Patient race |
| `Ethnicity` | String | Patient ethnicity |
| `VitalStatus` | String | Alive, Dead |
| `DaystoBirth` | String | Days to birth (for age calculation) |
| `atlas_name` | String | Atlas center |
| `ParticipantID` | String | Short participant ID |

### `diagnosis` (~2,700 rows)

| Column | Type | Description |
|---|---|---|
| `HTANParticipantID` | String | Participant identifier |
| `PrimaryDiagnosis` | String | ICD-O-3 diagnosis (e.g., `Ductal carcinoma NOS`) |
| `TissueorOrganofOrigin` | String | Organ of origin (e.g., `Breast NOS`) |
| `SiteofResectionorBiopsy` | String | Resection site |
| `TumorGrade` | String | G1, G2, G3 |
| `AgeatDiagnosis` | String | Age at diagnosis in days |
| `Morphology` | String | ICD-O-3 morphology code |
| `atlas_name` | String | Atlas center |
| `organType` | **Array(String)** | Organ type |

### `cases` (~2,900 rows)

Merged view of demographics + diagnosis. Contains columns from both tables.

| Column | Type | Description |
|---|---|---|
| `HTANParticipantID` | String | Participant identifier |
| `Gender` | String | Patient gender |
| `Race` | String | Patient race |
| `PrimaryDiagnosis` | String | Diagnosis |
| `TissueorOrganofOrigin` | String | Organ of origin |
| `atlas_name` | String | Atlas center |
| `organType` | **Array(String)** | Organ type |

### `specimen` (~18,500 rows)

| Column | Type | Description |
|---|---|---|
| `HTANBiospecimenID` | String | Biospecimen identifier |
| `BiospecimenType` | String | Type (e.g., Tissue Biospecimen Type) |
| `PreservationMethod` | String | e.g., `Formalin fixed paraffin embedded - FFPE`, `Fresh` |
| `TumorTissueType` | String | Tumor, Normal, Premalignant |
| `atlas_name` | String | Atlas center |
| `AcquisitionMethodType` | String | Biopsy, Surgical Resection, etc. |

### `atlases`

Atlas center metadata.

| Column | Type | Description |
|---|---|---|
| `atlas_id` | String | Atlas identifier |
| `atlas_name` | String | Full atlas name |

### `publication_manifest`

HTAN publications.

| Column | Type | Description |
|---|---|---|
| `PMID` | String | PubMed ID |
| `DOI` | String | Digital Object Identifier |

## Column Quick Reference

### `files` Table Columns

| Column | Type | Notes |
|---|---|---|
| `DataFileID` | String | HTAN_Data_File_ID (e.g., `HTA9_1_19512`) |
| `Filename` | String | Original filename |
| `FileFormat` | String | Format (fastq, bam, hdf5, ome.tif). Note: `.h5ad` files are stored as `hdf5` |
| `assayName` | String | Assay type (scRNA-seq, CyCIF, CODEX, Bulk RNA-seq, etc.) |
| `level` | String | Data level (Level 1–4, Auxiliary, Other). **Lowercase `level`**, not `Level` |
| `atlas_name` | String | Atlas center (HTAN HMS, HTAN WUSTL, etc.) |
| `synapseId` | String | Synapse entity ID for open-access download |
| `viewers` | String | JSON containing nested download coordinates |
| `downloadSource` | String | Download platform indicator |
| `Component` | String | Data component type |
| `isRawSequencing` | String | Whether file is raw sequencing data |
| `organType` | **[ARRAY]** Array(String) | Organ type |
| `Gender` | **[ARRAY]** Array(String) | Patient gender |
| `Race` | **[ARRAY]** Array(String) | Patient race |
| `Ethnicity` | **[ARRAY]** Array(String) | Patient ethnicity |
| `VitalStatus` | **[ARRAY]** Array(String) | Vital status |
| `TreatmentType` | **[ARRAY]** Array(String) | Treatment type |
| `PrimaryDiagnosis` | **[ARRAY]** Array(String) | Diagnosis |
| `TissueorOrganofOrigin` | **[ARRAY]** Array(String) | Organ of origin |
| `biospecimenIds` | **[ARRAY]** Array(String) | Related biospecimen IDs |
| `demographicsIds` | **[ARRAY]** Array(String) | Related demographics/participant IDs |
| `diagnosisIds` | **[ARRAY]** Array(String) | Related diagnosis IDs |
| `publicationIds` | **[ARRAY]** Array(String) | Related publication IDs |
| `therapyIds` | **[ARRAY]** Array(String) | Related therapy IDs |

### `demographics` Table Columns

| Column | Type |
|---|---|
| `HTANParticipantID` | String |
| `ParticipantID` | String |
| `Gender` | String |
| `Race` | String |
| `Ethnicity` | String |
| `VitalStatus` | String |
| `DaystoBirth` | String (may contain 'unknown', 'NaN') |
| `atlas_name` | String |

### `diagnosis` Table Columns

| Column | Type |
|---|---|
| `HTANParticipantID` | String |
| `PrimaryDiagnosis` | String |
| `TissueorOrganofOrigin` | String |
| `SiteofResectionorBiopsy` | String |
| `TumorGrade` | String |
| `AgeatDiagnosis` | String (may contain 'unknown', 'NaN') |
| `Morphology` | String |
| `atlas_name` | String |
| `organType` | **[ARRAY]** Array(String) |

### `cases` Table Columns

| Column | Type |
|---|---|
| `HTANParticipantID` | String |
| `Gender` | String |
| `Race` | String |
| `PrimaryDiagnosis` | String |
| `TissueorOrganofOrigin` | String |
| `atlas_name` | String |
| `organType` | **[ARRAY]** Array(String) |

### `specimen` Table Columns

| Column | Type |
|---|---|
| `HTANBiospecimenID` | String |
| `BiospecimenType` | String |
| `PreservationMethod` | String |
| `TumorTissueType` | String |
| `AcquisitionMethodType` | String |
| `atlas_name` | String |

### Common Mistakes

- **`organ` is not a column** — use `organType` (Array) in `files`, or `TissueorOrganofOrigin` (String) in `diagnosis`/`cases`
- **`participant_id` is not in `files`** — use `arrayJoin(demographicsIds)` to get participant IDs, or join via `demographics`/`cases`
- **`drs_uri` is not a column** — use `JSONExtractString(viewers, 'crdcGc', 'drs_uri')`
- **`Level` vs `level`** — the column is lowercase `level`
- **`FileFormat` for h5ad** — `.h5ad` files are stored as `hdf5`; use `Filename LIKE '%.h5ad'` instead
- **`DaystoBirth` / `AgeatDiagnosis` are String** — contain non-numeric values; use `toInt32OrNull()` with `IS NOT NULL` filtering
- **`!=` is not valid in ClickHouse** — use `<>` for not-equal comparisons (the script auto-normalizes this)
- **Array columns need special handling** — use `arrayExists()` for filtering, `arrayJoin()` for expansion, `arrayStringConcat()` for display

## Common Query Patterns

### File Discovery

```sql
-- Count files by assay type
SELECT assayName, COUNT(*) as n
FROM files
GROUP BY assayName
ORDER BY n DESC

-- Find scRNA-seq breast cancer files (organType is Array, use arrayExists)
SELECT DataFileID, Filename, FileFormat, synapseId, level
FROM files
WHERE arrayExists(x -> x = 'Breast', organType) AND assayName = 'scRNA-seq'
LIMIT 20

-- Files with download coordinates
SELECT DataFileID, synapseId,
       JSONExtractString(viewers, 'crdcGc', 'drs_uri') as drs_uri
FROM files
WHERE DataFileID = 'HTA9_1_19512'

-- Count files per atlas
SELECT atlas_name, COUNT(*) as n
FROM files
GROUP BY atlas_name
ORDER BY n DESC
```

### Clinical Queries

```sql
-- Demographics by atlas
SELECT atlas_name, Gender, COUNT(*) as n
FROM demographics
GROUP BY atlas_name, Gender
ORDER BY atlas_name

-- Diagnosis distribution
SELECT TissueorOrganofOrigin, COUNT(*) as n
FROM diagnosis
GROUP BY TissueorOrganofOrigin
ORDER BY n DESC

-- Breast cancer cases
SELECT *
FROM cases
WHERE TissueorOrganofOrigin ILIKE '%Breast%'
LIMIT 50
```

### Biospecimen Queries

```sql
-- Preservation methods
SELECT PreservationMethod, COUNT(*) as n
FROM specimen
GROUP BY PreservationMethod
ORDER BY n DESC

-- FFPE specimens by atlas
SELECT atlas_name, COUNT(*) as n
FROM specimen
WHERE PreservationMethod ILIKE '%FFPE%'
GROUP BY atlas_name
ORDER BY n DESC
```

## ClickHouse SQL Notes

ClickHouse SQL is mostly standard but has some differences from BigQuery/standard SQL:

- **`ILIKE`** for case-insensitive LIKE (vs. `LOWER(x) LIKE`)
- **`JSONExtractString(col, key1, key2)`** for JSON field extraction
- **`count()`** instead of `COUNT(*)` (both work, but `count()` is idiomatic)
- **`LIMIT`** is always recommended (no cost estimation like BigQuery dry run)
- **No backtick quoting** needed for table names (unlike BigQuery)

## Portal vs. BigQuery Comparison

| Feature | Portal (ClickHouse) | BigQuery (ISB-CGC) |
|---|---|---|
| **Auth required** | None (public read-only) | Google Cloud credentials + billing project |
| **Setup complexity** | Zero — works immediately | `gcloud auth` + project setup |
| **Dependencies** | None (stdlib urllib) | `google-cloud-bigquery`, `pandas` |
| **Clinical depth** | Basic (7 tables) | Deep (408+ tables, multi-tier clinical) |
| **File download info** | Included (synapseId, DRS URI in same table) | Requires separate file mapping step |
| **Workflow steps** | 2 (query → download) | 3 (query → file mapping → download) |
| **Join complexity** | Simple (mostly single-table) | Complex (multi-table clinical joins) |
| **SLA / stability** | No SLA — public credentials could change | Google Cloud SLA |
| **Data freshness** | Portal release cadence (database name changes) | ISB-CGC release cadence |

### When to Use Each

**Use Portal (ClickHouse)** for:
- Quick file discovery by organ, assay, atlas
- Getting download coordinates (synapseId, DRS URI) directly
- Basic clinical/demographic queries
- Cases where GCP billing is not available

**Use BigQuery** for:
- Complex clinical queries (multi-tier joins, follow-up data)
- Assay-level metadata (library construction, cell counts, read length)
- Queries requiring specific BigQuery features (UDFs, ML, etc.)
- Production workflows requiring SLA guarantees

## Limitations and Risks

1. **No SLA**: Public credentials could be rotated without notice
2. **Database name changes**: The database name includes a date (e.g., `htan_2026_01_08`) and changes with portal releases. The script auto-discovers the latest database.
3. **Read-only**: The `REDACTED_USER` account has SELECT-only permissions
4. **Simpler schema**: Fewer tables than BigQuery — no assay-level metadata (cell counts, library methods, etc.)
5. **Rate limits**: Unknown public rate limits — use reasonable query patterns
6. **JSON column**: DRS URIs are nested in a JSON string column (`viewers`), requiring `JSONExtractString()` for extraction
