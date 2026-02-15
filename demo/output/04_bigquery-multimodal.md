# Using BigQuery, how many unique participants per cancer type have both scRNA-seq and imaging data?

---

Here are the results. **190 unique participants** have both scRNA-seq and imaging data, broken down by cancer type (ICD-O-3 `Primary_Diagnosis`):

| Cancer Type | Participants |
|---|---|
| Not Reported | 63 |
| Adenocarcinoma NOS | 27 |
| Ductal carcinoma NOS | 25 |
| Pancreatobiliary-type carcinoma | 21 |
| Carcinoma NOS | 12 |
| Neuroblastoma NOS | 11 |
| Infiltrating duct carcinoma NOS | 7 |
| Familial adenomatous polyposis | 6 |
| Squamous cell carcinoma NOS | 5 |
| Duct carcinoma NOS | 4 |
| Malignant melanoma NOS | 2 |
| Central neuroblastoma | 2 |
| Lobular carcinoma NOS | 2 |
| Adenocarcinoma intestinal type | 1 |
| Intraductal carcinoma NOS | 1 |
| Lobular and ductal carcinoma | 1 |
| Ductal carcinoma in situ NOS | 1 |

**Key notes:**
- The query joins scRNAseq level 1 metadata (via `HTAN_Parent_Biospecimen_ID`) with imaging level 2 metadata (via `HTAN_Participant_ID`), then maps to `Primary_Diagnosis` from the clinical diagnosis table.
- Participant IDs are extracted from biospecimen IDs using the HTAN ID pattern (`HTAx_participant`).
- 63 participants with both modalities have "Not Reported" as their diagnosis — these could potentially be resolved with deeper clinical tier data.
- Breast-related cancers (ductal, lobular, infiltrating duct) collectively represent ~40 participants, making breast the most represented organ with both data types.
