# HTAN Atlas Centers

The Human Tumor Atlas Network (HTAN) is organized into atlas centers that focus on specific cancer types. HTAN has two phases of funding.

---

## Phase 1 Centers

| Atlas | HTAN_Center Value | Cancer Type(s) | Grant Number |
|-------|-------------------|----------------|--------------|
| HTAN HTAPP | `HTAN HTAPP` | Multiple (pan-cancer) | CA233303 |
| HTAN HMS | `HTAN HMS` | Melanoma, breast, colorectal | CA233262 |
| HTAN OHSU | `HTAN OHSU` | Breast | CA233280 |
| HTAN MSK | `HTAN MSK` | Colorectal, pancreatic | CA233311 |
| HTAN Stanford | `HTAN Stanford` | Breast | CA233195 |
| HTAN Vanderbilt | `HTAN Vanderbilt` | Colorectal | CA233291 |
| HTAN WUSTL | `HTAN WUSTL` | Breast, pancreatic | CA233238 |
| HTAN CHOP | `HTAN CHOP` | Pediatric cancers | CA233285 |
| HTAN Duke | `HTAN Duke` | Breast | CA233243 |
| HTAN BU | `HTAN BU` | Lung (pre-cancer) | CA233254 |
| HTAN DFCI | `HTAN DFCI` | Multiple myeloma | CA233284 |

## Phase 2 Centers (Translational Network Projects)

| Atlas | HTAN_Center Value | Cancer Type(s) | Grant Number |
|-------|-------------------|----------------|--------------|
| HTAN TNP SARDANA | `HTAN TNP SARDANA` | Multiple | CA294459 |
| HTAN TNP SRRS | `HTAN TNP SRRS` | Multiple | CA294507 |
| HTAN TNP TMA | `HTAN TNP TMA` | Multiple | CA294514 |

---

## Grant Numbers

### Phase 1 (CA233xxx Series)

CA233195, CA233238, CA233243, CA233254, CA233262, CA233280, CA233284, CA233285, CA233291, CA233303, CA233311

### Phase 2 (CA294xxx Series)

CA294459, CA294507, CA294514, CA294518, CA294527, CA294532, CA294536, CA294548, CA294551, CA294552

### Data Coordinating Center (DCC)

HHSN261201500003I

---

## BigQuery HTAN_Center Values

When querying HTAN data in BigQuery, use the `HTAN_Center` column to filter by atlas. The values match the "HTAN_Center Value" column above exactly.

Example query:

```sql
SELECT DISTINCT HTAN_Center
FROM `isb-cgc-bq.HTAN_versioned.clinical_tier1_demographics_r5`
ORDER BY HTAN_Center
```

---

## Cancer Types Studied

| Cancer Type | Centers |
|-------------|---------|
| Breast | HMS, OHSU, Stanford, WUSTL, Duke |
| Colorectal | HMS, MSK, Vanderbilt |
| Pancreatic | MSK, WUSTL |
| Melanoma | HMS |
| Lung (pre-cancer) | BU |
| Multiple myeloma | DFCI |
| Pediatric | CHOP |
| Pan-cancer / Multiple | HTAPP, TNP SARDANA, TNP SRRS, TNP TMA |
