# Find all scRNA-seq files from breast cancer, show me the 10 smallest open-access ones

---

Those are tiny barcode files. Let me get the smallest files that are more meaningful (matrices/h5ad), or show all types but include more context. Actually, the user asked for the 10 smallest, so let me present these but also note they're barcode index files. Let me also get the Synapse IDs to confirm they're downloadable.

Here are the **10 smallest open-access scRNA-seq files from breast cancer** in HTAN, sorted by file size:

| # | HTAN Data File ID | Filename | Format | Size | Atlas | Synapse ID |
|---|---|---|---|---|---|---|
| 1 | HTA6_2502_80 | HTA6_2502_4-barcodes.tsv.gz | tsv | 2.8 KB | HTAN Duke | syn64372046 |
| 2 | HTA6_2501_62 | HTA6_2501_2-barcodes.tsv.gz | tsv | 2.9 KB | HTAN Duke | syn64372042 |
| 3 | HTA6_2501_61 | HTA6_2501_1-barcodes.tsv.gz | tsv | 3.2 KB | HTAN Duke | syn64372040 |
| 4 | HTA6_2501_63 | HTA6_2501_3-barcodes.tsv.gz | tsv | 4.4 KB | HTAN Duke | syn64372041 |
| 5 | HTA6_2502_79 | HTA6_2502_3-barcodes.tsv.gz | tsv | 6.2 KB | HTAN Duke | syn64372045 |
| 6 | HTA6_2502_77 | HTA6_2502_1-barcodes.tsv.gz | tsv | 7.4 KB | HTAN Duke | syn64372043 |
| 7 | HTA6_2503_44 | HTA6_2503_1-barcodes.tsv.gz | tsv | 10.8 KB | HTAN Duke | syn64372047 |
| 8 | HTA6_2504_40 | HTA6_2504_1-barcodes.tsv.gz | tsv | 14.1 KB | HTAN Duke | syn64372049 |
| 9 | HTA6_2502_78 | HTA6_2502_2-barcodes.tsv.gz | tsv | 18.9 KB | HTAN Duke | syn64372044 |
| 10 | HTA6_2504_41 | HTA6_2504_2-barcodes.tsv.gz | tsv | 24.3 KB | HTAN Duke | syn64372050 |

All 10 are from **HTAN Duke** and are Level 3 barcode index files (companion files to expression matrices). They're all open-access on **Synapse** — downloadable with:

```bash
uv run synapse get syn64372046   # example: smallest file
```

**Note:** These are barcode TSV files (cell identifiers), not the expression matrices themselves. If you'd prefer the 10 smallest **matrix files** (mtx, h5ad, etc.) which contain actual expression data, I can filter for those instead.
