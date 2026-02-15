# Give me an overview of what data is available in HTAN

---

Here's an overview of HTAN data:

## HTAN Data Overview

**Database snapshot:** `htan_2026_01_08` — **221,285 files** across **2,890 participants**

### Atlas Centers (14 centers)

The largest data contributors are:
| Atlas | Files | Participants |
|---|---|---|
| HTAN OHSU | 116,657 | 33 |
| HTAN HTAPP | 41,631 | 205 |
| HTAN DFCI | 17,560 | 156 |
| HTAN Duke | 7,035 | 828 |
| HTAN WUSTL | 7,176 | 287 |
| HTAN Stanford | 5,913 | 40 |
| HTAN MSK | 5,381 | 202 |
| HTAN BU | 5,319 | 484 |

### Assay Types (31 assays)

**Imaging** dominates by file count:
- **Electron Microscopy** — 110,398 files
- **MERFISH** — 18,626
- **ExSEQ** — 21,156
- **CyCIF / CODEX / MxIF / MIBI / IMC** — multiplexed imaging

**Single-cell genomics:**
- **scRNA-seq** — 25,533 files
- **scATAC-seq** — 4,116
- **scDNA-seq** — 3,056

**Spatial transcriptomics:**
- **10X Visium** — 2,921
- **Slide-seq** — 383
- **NanoString GeoMx DSP** — 395
- **10X Xenium ISS** — 33

**Bulk genomics:**
- **Bulk DNA** — 9,660
- **Bulk RNA-seq** — 6,696

**Proteomics / metabolomics:**
- **LC-MS/MS & LC-MS3** — 972
- **RPPA** — 78

### Organs / Cancer Types (20+)

| Organ | Files |
|---|---|
| Breast | 157,186 |
| Skin | 10,878 |
| Colorectal | 10,847 |
| Brain | 10,601 |
| Lung | 6,960 |
| Pancreas | 2,291 |
| Bone Marrow | 1,228 |
| Ovary | 945 |

Plus liver, kidney, cervix, stomach, head & neck, and more.

### Portal Database Tables

7 queryable tables: **files**, **cases**, **demographics**, **diagnosis**, **specimen**, **atlases**, and **publication_manifest**.

### What You Can Do Next

- **Find specific files**: `uv run htan query portal files --organ Breast --assay "scRNA-seq"`
- **Query clinical data**: `uv run htan query portal demographics --atlas "HTAN OHSU"`
- **Search publications**: `uv run htan pubs search --keyword "spatial transcriptomics"`
- **Deep metadata queries via BigQuery**: file sizes, cell counts, library methods

Let me know if you'd like to drill into a specific atlas, organ, or assay type!
