# What attributes are required for an scRNA-seq Level 1 manifest? Show valid values for Library Construction Method.

---

## scRNA-seq Level 1 Manifest — Required Attributes

There are **23 required** attributes (plus 2 optional) for a total of 25:

| # | Attribute | Notes |
|---|-----------|-------|
| 1 | Component | |
| 2 | Filename | regex: `^.+\/\S*$` |
| 3 | File Format | |
| 4 | HTAN Parent Biospecimen ID | |
| 5 | HTAN Data File ID | e.g. `HTA9_1_19512` |
| 6 | Nucleic Acid Source | |
| 7 | Cryopreserved Cells in Sample | |
| 8 | Single Cell Isolation Method | |
| 9 | Dissociation Method | |
| 10 | **Library Construction Method** | see below |
| 11 | Read Indicator | |
| 12 | Read1 | |
| 13 | Read2 | |
| 14 | End Bias | |
| 15 | Reverse Transcription Primer | |
| 16 | Spike In | |
| 17 | Sequencing Platform | |
| 18 | Total Number of Input Cells | |
| 19 | Input Cells and Nuclei | |
| 20 | Single Cell Dissociation Days from Index | |
| 21 | Sequencing Library Construction Days from Index | |
| 22 | Nucleic Acid Capture Days from Index | |
| 23 | Protocol Link | |

## Valid Values for Library Construction Method (18)

| Value |
|-------|
| Smart-seq2 |
| Smart-SeqV4 |
| 10xV1.0 |
| 10xV1.1 |
| 10xV2 |
| 10xV3 |
| 10xV3.1 |
| CEL-seq2 |
| Drop-seq |
| inDropsV2 |
| inDropsV3 |
| TruDrop |
| sci-ATAC-seq |
| Nextera XT |
| 10x Multiome |
| 10x FLEX |
| 10x GEM 3' |
| 10x GEM 5' |

The 10x Chromium family (V1–V3.1, Multiome, FLEX, GEM 3'/5') dominates the options, with Smart-seq, Drop-seq, CEL-seq2, inDrops, and a few others also supported.
