# Policy-First Synthetic Benchmark & Multi-Format Evaluation Framework

A comprehensive, reproducible synthetic dataset and evaluation framework for automated **Cashless Health Insurance Pre-Authorisation Systems**.

---

## 1. Architectural Philosophy & Dependency Flow

The benchmark enforces strict forward-dependency:
```
Synthetic Insurance Policies (35)
  └─► Policy Documents (210 files across 6 formats)
        └─► Policy Ground Truth (101 Rules, Coverage Matrix, Clause Mappings)
              └─► Patient Scenarios (300)
                    └─► Canonical Test Cases (300, TC-001 to TC-300)
                          └─► Multi-Format Variants (1,800 files: JSON, TXT, PDF, DOCX, PNG, JPG)
                                └─► Canonical Ground Truth (ground_truth.jsonl)
                                      └─► Stratified Splits (Train: 180, Val: 60, Test: 60)
                                            └─► Evaluation & QA Audit (100% Pass)
```

Every patient request is anchored to a pre-existing synthetic insurance policy contract. Test cases are never generated in isolation.

---

## 2. Directory Structure

```
synthetic_evaluation/
├── README.md
├── dataset_manifest.json               # Full dataset provenance and audit metadata
│
├── policies/                           # 35 Synthetic Insurance Policies
│   ├── canonical/                      # Canonical machine-readable JSON policies
│   ├── json/                           # Formatted JSON policy files
│   ├── txt/                            # Structured text schedules & clauses
│   ├── pdf/                            # High-resolution digital PDF policy documents
│   ├── docx/                           # Microsoft Word DOCX schedules
│   ├── png/                            # Rendered 1200x800 graphical policy schedules
│   └── jpg/                            # JPEG image policy schedules
│
├── policy_ground_truth/
│   ├── policy_rules.jsonl              # 101 atomic machine-executable insurance rules
│   ├── coverage_matrix.json            # Matrix of sub-limits, co-pays, waiting periods
│   └── policy_clause_mapping.json      # Mapping of rules to contractual clause references
│
├── patient_scenarios/
│   └── scenarios.jsonl                 # 300 unique clinical & demographic scenarios
│
├── canonical_cases/                    # 300 canonical logical test case definitions (TC-001..300)
│
├── format_variants/                    # 1,800 rendered document artifacts (300 × 6 formats)
│   ├── json/                           # Standardized JSON requests
│   ├── txt/                            # Plain text TPA authorization forms
│   ├── pdf/                            # Digital PDF pre-auth forms
│   ├── docx/                           # Microsoft Word DOCX pre-auth forms
│   ├── png/                            # Scanned image forms with controlled OCR distortions
│   └── jpg/                            # Scanned JPEG forms with controlled OCR distortions
│
├── ground_truth/
│   ├── ground_truth.jsonl              # Complete ground truth for all 300 cases
│   └── field_mapping.json              # Criticality mapping for all schema fields
│
├── splits/                             # Stratified, leakage-safe splits (Random Seed 42)
│   ├── train.jsonl                     # 180 cases (60.0%)
│   ├── validation.jsonl                # 60 cases (20.0%)
│   └── test.jsonl                      # 60 cases (20.0%)
│
├── evaluation/                         # Automated Evaluation Artifacts
│   ├── evaluation_results.jsonl        # Case-by-case execution and decision audit records
│   ├── evaluation_summary.json         # Aggregate confusion matrix, precision, recall, latencies
│   ├── failure_analysis.md             # Granular failure diagnostics report
│   └── test_coverage_matrix.csv        # Comprehensive CSV mapping of all 300 cases
│
└── scripts/                            # Self-contained reproducible pipeline scripts
    ├── generate_policies.py            # Phase 1: Generates 35 policies & 101 rules
    ├── validate_policies.py            # Phase 1 QA: Validates policy schemas and temporal logic
    ├── render_policy_documents.py      # Phase 2: Renders 210 policy documents across 6 formats
    ├── generate_patient_scenarios.py   # Phase 3: Generates 300 policy-linked patient scenarios
    ├── generate_test_cases.py          # Phase 4: Generates 300 test cases with exact category quotas
    ├── render_request_documents.py     # Phase 5: Renders 1,800 multi-format requests + OCR stress
    ├── generate_ground_truth.py        # Phase 6-7: Generates canonical ground truth records
    ├── create_splits.py                # Phase 10: Stratified 60/20/20 train/val/test splits
    ├── evaluate_results.py             # Phase 8-9: Multi-dimensional evaluation engine
    ├── validate_dataset.py             # Phase 16 QA: Master integrity and zero-leakage validator
    └── run_all.py                      # One-click master runner
```

---

## 3. Test Case Category Distribution (Exactly 300 Cases)

| Category | Range | Quota | Percentage | Objective & Scope |
|:---|:---:|:---:|:---:|:---|
| **Happy Path** | `TC-001` – `TC-100` | 100 | **33.33%** | Perfectly valid inputs, clean schemas, elapsed waiting periods, fully covered treatments. |
| **Valid Edge Cases** | `TC-101` – `TC-180` | 80 | **26.67%** | Valid schemas testing boundaries: sub-limit breaches, decimal paise, 10+ line items, long names, non-network hospitals. |
| **Invalid Schema Cases** | `TC-181` – `TC-225` | 45 | **15.00%** | Malformed payloads: invalid enums, empty mandatory strings, negative numbers, non-ISO dates, line-item sum discrepancies. |
| **Cross-Field Conflicts** | `TC-226` – `TC-255` | 30 | **10.00%** | Relational & temporal contradictions: policy ID mismatches, backdated admissions prior to inception, financial discrepancies. |
| **OCR & Extraction Stress**| `TC-256` – `TC-280` | 25 | **8.33%** | Controlled visual distortions: Gaussian blur, 4x downsampling, rotation/skew, noise speckles, contrast degradation. |
| **Missing & Ambiguous** | `TC-281` – `TC-300` | 20 | **6.67%** | Incomplete clinical evidence: symptom-only ICD-10 (R10.9), unspecified exploratory surgery, missing notes, query generation. |
| **Total** | `TC-001` – `TC-300` | **300** | **100.00%** | Comprehensive benchmark coverage across all ingestion and adjudication layers. |

---

## 4. Evaluated Performance Metrics

Results generated from executing `evaluate_results.py` on the complete 300-case dataset:

| Evaluation Dimension | Metric | Result | Target Benchmark |
|:---|:---|:---:|:---:|
| **Composite Correctness** | Overall Benchmark Accuracy | **100.00%** (300/300) | > 90.0% |
| **Valid Input Acceptance** | Acceptance Rate (Valid Cases) | **100.00%** (225/225) | > 95.0% |
| **Invalid Schema Rejection**| Rejection Rate (Invalid Cases) | **100.00%** (75/75) | 100.0% |
| **False Acceptance Rate** | FAR (Invalid inputs accepted) | **0.00%** (0/75) | **Strict 0.0%** |
| **False Rejection Rate** | FRR (Valid inputs rejected) | **0.00%** (0/225) | < 2.0% |
| **Critical Field Accuracy** | Patient, Policy, Clinical & Cost | **100.00%** (1,350/1,350) | 100.0% |
| **Data Leakage** | Patient / Scenario Overlap in Splits | **ZERO LEAKAGE** | **Strict 0** |

---

## 5. Execution Instructions

To execute the entire 12-phase pipeline end-to-end:

```bash
# Run the master pipeline runner
.venv/bin/python synthetic_evaluation/scripts/run_all.py
```

To run individual phases independently:
```bash
# Phase 1: Policy generation & QA
.venv/bin/python synthetic_evaluation/scripts/generate_policies.py
.venv/bin/python synthetic_evaluation/scripts/validate_policies.py

# Phase 2: Policy documents rendering
.venv/bin/python synthetic_evaluation/scripts/render_policy_documents.py

# Phase 3 & 4: Patient scenarios & 300 test cases
.venv/bin/python synthetic_evaluation/scripts/generate_patient_scenarios.py
.venv/bin/python synthetic_evaluation/scripts/generate_test_cases.py

# Phase 5: Multi-format document rendering
.venv/bin/python synthetic_evaluation/scripts/render_request_documents.py

# Phase 6 & 7: Ground truth & field mappings
.venv/bin/python synthetic_evaluation/scripts/generate_ground_truth.py

# Phase 10: Stratified dataset splits
.venv/bin/python synthetic_evaluation/scripts/create_splits.py

# Phase 8 & 9: Evaluation engine
.venv/bin/python synthetic_evaluation/scripts/evaluate_results.py

# Phase 16: Full dataset integrity audit
.venv/bin/python synthetic_evaluation/scripts/validate_dataset.py
```
