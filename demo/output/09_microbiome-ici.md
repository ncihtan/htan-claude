# Are there any data that might be interesting for retrospective study about microbiome mediated effects for ICIs?

---

Here's what I found:

## Short Answer: HTAN doesn't have direct microbiome data, but has rich datasets that could support microbiome-ICI retrospective studies

### No Dedicated Microbiome Assays
HTAN does **not** include 16S rRNA sequencing, shotgun metagenomics, or any microbiome-specific assay type. The data model has no microbiome-related attributes. So you won't find direct microbial profiling data here.

### What IS Available for Microbiome-ICI Research

**1. Colorectal cancer — richest opportunity** (HTAN MSK, Stanford, WUSTL, HMS)
- **scRNA-seq** (MSK: 2,333 files; Stanford: 640; WUSTL: 132) — tumor microenvironment immune cell profiling
- **Multiplexed imaging** (MSK MxIF: 1,213; Stanford CODEX: 1,392; HMS CyCIF: 370) — spatial immune contexture
- **10X Visium** spatial transcriptomics (WUSTL: 315 files) — spatially resolved gene expression including at the mucosal interface
- **Bulk DNA** (Stanford: 801) — MSI status, mutational signatures relevant to ICI response

CRC is one of the strongest microbiome-ICI cancer types (e.g., *Fusobacterium nucleatum*, MSI-H/dMMR and pembrolizumab response). The HTAN Vanderbilt atlas is specifically focused on colorectal progression, and there's an HTAN-affiliated publication on **spatial analysis of colonic biofilms** (Macedonia et al., 2020, PMID: 32973205) that developed methods for simultaneous imaging of host tissue and microbes.

**2. Lung cancer** (HTAN BU, MSK, HTAPP)
- **HTAN BU**: 2,225 Bulk RNA-seq + 597 scRNA-seq + 546 Bulk DNA — focused on **lung pre-cancer**, ideal for studying microbiome effects on early immune surveillance
- **MSK**: 1,326 scRNA-seq files for lung — deep immune phenotyping
- **HTAPP**: Spatial transcriptomics (10X Visium, 427 files)

Lung is a key ICI cancer type where the airway microbiome has been linked to treatment outcomes.

**3. Melanoma** (HTAN HMS, Stanford, TNP SARDANA)
- **CyCIF** multiplexed imaging (HMS: 370 + TNP SARDANA: 152) — spatial immune profiling
- Melanoma was the first cancer type to show ICI benefit, and gut microbiome composition has been linked to anti-PD-1 response.

### Practical Strategy for a Retrospective Study

Since HTAN lacks direct microbiome data, the most productive approach would be:

1. **Computational microbial inference from bulk RNA-seq** — Tools like PathSeq, Kraken2, or TCGA-microbiome pipelines can extract microbial reads from bulk RNA-seq data. HTAN BU's **2,225 bulk RNA-seq files** from lung pre-cancer would be a strong candidate.

2. **Immune microenvironment characterization** — Use the scRNA-seq and spatial data to characterize the immune contexture, then integrate with external microbiome cohorts (e.g., from curatedMetagenomicData or TCGA-microbiome studies) via shared clinical features.

3. **MSI/immune signatures as a proxy** — Use the bulk DNA data to identify MSI-H tumors (linked to both microbiome alterations and ICI response), then characterize the immune landscape around them with spatial assays.

### Relevant HTAN Publication

- **PMID 32973205** — A method for simultaneous spatial analysis of colonic tissues and microbial biofilms, developed by HTAN Vanderbilt investigators. This could be a methodological starting point.
- **PMID 40389599** — MSI prediction from histology with immunotherapy response modeling, using deep learning on HTAN-related data.

Would you like me to dig deeper into any of these angles — for example, querying the specific file counts and clinical metadata available for a particular atlas/cancer type?