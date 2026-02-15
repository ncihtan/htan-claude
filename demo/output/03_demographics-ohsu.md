# What clinical demographics are available for HTAN OHSU patients?

---

Here's a summary of the clinical demographics available for **HTAN OHSU** patients:

### Cohort Overview
- **33 participants** (HTA9_1 through HTA9_45, not all sequential)
- **All female** patients
- **Ethnicity**: All "not hispanic or latino"
- **Race**: Predominantly white, with 1 Black or African American (HTA9_13), 1 "Not Reported" (HTA9_15), and 1 "unknown" (HTA9_42)

### Vital Status
- **Dead**: 27 patients (~82%)
- **Alive**: 6 patients (HTA9_17, HTA9_23, HTA9_28, HTA9_29, HTA9_42, HTA9_45)

### Available Demographic Fields
| Field | Status |
|---|---|
| **Gender** | Populated (all Female) |
| **Ethnicity** | Populated |
| **Race** | Populated |
| **Vital Status** | Populated (Alive/Dead) |
| **Cause of Death** | "Not Reported" for deceased patients |
| **Cause of Death Source** | "Medical Record" |
| **Days to Birth** | 0 (obfuscated) |
| **Age Is Obfuscated** | false |
| **Year of Birth** | Not available |
| **Premature at Birth** | "unknown" |
| **Country of Residence** | Not reported |

### Notes
- HTAN OHSU focuses on **breast cancer** (high-grade serous ovarian cancer as well). The all-female cohort is consistent with this focus.
- Age/birth data appears obfuscated (DaystoBirth = 0). For more detailed clinical information (diagnosis, staging, treatment), you can query the **diagnosis** or **cases** tables, or use **BigQuery** for deeper clinical metadata.

Would you like me to pull diagnosis or treatment data for these patients?
