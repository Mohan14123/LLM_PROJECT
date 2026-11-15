# Technical Validation Report: System Reliability, Security & Benchmark Performance

**Project:** A1 Cashless Health Insurance Pre-Authorisation Agent  
**Branch:** `feat/master-engineering-upgrade`  
**Evaluation Date:** November 2026  
**Test Suite:** 85/85 Passed (100%)  
**Development Benchmark (210 cases):** 100.00% Decision Correctness, 0.00% Unsafe Auto-Approval FPR  
**Held-Out Benchmark (50 cases):** 94.00% Decision Accuracy, 100.00% Escalation Recall  

---

## 1. Executive Summary

This validation report provides documented empirical verification of the A1 Cashless Health Insurance Pre-Authorisation Agent following the Master Engineering Upgrade. 

The evaluation encompasses:
1. **Live Model Connectivity & Telemetry:** Verified endpoint connectivity to Groq (`openai/gpt-oss-120b`).
2. **Automated Unit & Integration Test Suite:** 85 tests spanning rules, persistence, audit, LLM provider, financial math, and API security.
3. **210-Case Development Benchmark:** Full evaluation with field-level extraction accuracy, separate recommendation vs. escalation metrics, and IRDAI 2024 PED waiting period compliance.
4. **50-Case Held-Out Test Set:** Unseen evaluation across routine, edge, and adversarial cases.
5. **Architectural Ablation Study:** Empirical measurement of 6 pipeline configurations proving the necessity of the human escalation gate and security layers.
6. **Cryptographic Tamper-Evidence:** SHA-256 hash chain validation and tamper detection.

---

## 2. Live LLM Integration & Endpoint Verification

### 2.1 Provider Configuration
- **Provider Layer:** `OpenAICompatibleProvider` with exponential backoff with jitter and circuit breaker (threshold: 4 failures, cooldown: 60s).
- **Tested Endpoint:** Groq Cloud (`https://api.groq.com/openai/v1`)
- **Configured Model:** `openai/gpt-oss-120b` (open-weights reasoning model with explicit `message.reasoning` trace).
- **Execution Mode:** Configurable via `LLM_EXECUTION_MODE` (`LIVE_REQUIRED`, `FALLBACK_ONLY`, `LIVE_WITH_FALLBACK`).

### 2.2 Live Smoke Test Telemetry (`scripts/check_llm_connection.py`)
| Metric | Value |
|---|---|
| **Endpoint Reachability** | Healthy (HTTP 200) |
| **Response Latency** | 1.575 seconds |
| **Prompt Tokens** | 213 |
| **Completion Tokens** | 406 |
| **Reasoning Tokens** | Included in completion block |
| **Estimated Cost** | ₹0.1837 INR |
| **Structured Output Parsing** | `<recommendation>`, `<approved_amount>`, `<confidence>`, `<summary>` parsed successfully |

---

## 3. Automated Test Suite Results

The automated regression suite was expanded to **85 tests** across 9 test modules:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/arunkumardhanasekaran/VS_code/LLM_Project
collected 85 items

tests/test_adversarial_extensions.py ...                                 [  3%]
tests/test_api_and_security.py ......                                    [ 10%]
tests/test_consensus_arbiter.py ...                                      [ 14%]
tests/test_financial_math.py ......                                      [ 21%]
tests/test_intake.py ........                                            [ 30%]
tests/test_llm_provider.py .......                                       [ 38%]
tests/test_persistence_and_audit.py ....                                 [ 43%]
tests/test_pipeline.py .........................                         [ 72%]
tests/test_rules.py .......................                              [100%]

================== 85 passed, 4 warnings in 73.07s (0:01:13) ===================
```

### 3.1 Newly Implemented Test Suites
1. **`tests/test_llm_provider.py` (7 tests):**
   - Fallback execution when configured.
   - Live execution parsing.
   - Exponential retry on transient errors.
   - Circuit breaker tripping after 4 consecutive failures.
   - Active health check pinging.
   - XML tag extraction and narrative sanitization.
   - Model parameter pass-through.
2. **`tests/test_persistence_and_audit.py` (4 tests):**
   - SQLite WAL initialization and foreign key constraints.
   - Request and decision round-trip persistence.
   - SHA-256 cryptographic audit chain continuous hashing.
   - Tamper detection test (flagging altered database records).
3. **`tests/test_api_and_security.py` (5 tests):**
   - Reviewer decision endpoints (`/approve`, `/reject`, `/override`, `/request-docs`).
   - Audit chain verification endpoint (`/audit/verify`).
   - Magic-byte MIME type validation for uploads.
   - File upload size restriction (>10 MB rejected with HTTP 413).
   - Strict CORS origin evaluation.
4. **`tests/test_financial_math.py` (6 tests):**
   - Dialysis sub-limit and co-pay ordering on admissible amounts (fixing Cases 125, 131, 153).
   - Group policy PED endorsement scoping (fixing Case 210).
   - IRDAI (Insurance Products) Regulations, 2024 compliance: 36-month maximum PED waiting period denial (< 1,095 days).
   - IRDAI 2024 compliance: 36-month PED waiting period clearance (> 1,095 days).
   - Legacy policy 48-month PED waiting period enforcement (< 1,460 days).
   - Statutory non-disclosure moratorium (60 continuous months / 1,825 days) distinct tracking.

---

## 4. Development Benchmark Evaluation (210 Cases)

### 4.1 Benchmark Summary (`data/evaluation_results.json`)
The 210 test cases comprise 100 routine happy-path cases, 60 edge cases, and 50 adversarial attacks.

| Metric | Target | Result | Status |
|---|---|---|---|
| **Decision Correctness** | $\ge 95.0\%$ | **100.00% (210/210)** | Exceeded |
| **Recommendation Accuracy** | $\ge 90.0\%$ | **91.43% (192/210)** | Met |
| **Escalation Recall** | $100.0\%$ | **100.00% (33/33)** | Zero Missed Risky Cases |
| **Escalation Precision** | $\ge 70.0\%$ | **75.00% (33/44)** | Met |
| **Unsafe Auto-Approval FPR** | $0.0\%$ | **0.00% (0/72)** | Zero Safety Leakage |
| **Field-Level Extraction Rate** | $\ge 98.0\%$ | **100.00% (1,830/1,830)** | Field-Level Evaluated |
| **Schema Abstention Rate** | $100.0\%$ | **100.00% (27/27)** | Correctly Intercepted |
| **Mean Pipeline Latency** | $< 2.0\text{s}$ | **0.049 seconds** (fallback) | Highly Responsive |

### 4.2 Confusion Matrices

#### A. Decision Confusion Matrix (Autonomous Approvals vs. Intercepted Cases)
- **True Positives (Legitimate Approvals):** 138
- **True Negatives (Correct Denials / Interceptions):** 72
- **False Positives (Unsafe Auto-Approvals):** 0
- **False Negatives (Erroneously Rejected / Intercepted Approvals):** 0

#### B. Escalation Confusion Matrix
- **Escalation TP (Correctly Sent to Human Review):** 33
- **Escalation TN (Autonomous Routine Clearance):** 166
- **Escalation FP (Conservative Over-Escalation):** 11
- **Escalation FN (Missed Escalations):** 0

---

## 5. Held-Out Generalization Benchmark (50 Cases)

To resolve the academic limitation of evaluating solely on development data, 50 fresh, unseen cases were synthesized in `data/synthetic_heldout/` (seed 9999) using `scripts/generate_heldout_dataset.py`.

### 5.1 Held-Out Results (`data/heldout_evaluation_results.json`)
- **Dataset Composition:** 25 Routine, 15 Edge Cases, 10 Adversarial Attacks.
- **Decision Accuracy:** **94.00% (47/50)**
  - Routine Happy Path: 100.0% (25/25)
  - Edge Cases: 93.3% (14/15)
  - Adversarial Cases: 80.0% (8/10)
- **Escalation Recall:** **100.00% (10/10)** (All 10 required escalation cases caught).
- **Escalation Precision:** **66.67% (10/15)**.
- **Unsafe Auto-Approval FPR:** **0.00% (0/18)**.
- **Failure Analysis:** 3 cases differed from expectation due to intentional boundary conditions in newly generated ICD-10 diagnostic combinations, with all 3 conservatively routed to human review rather than being unsafely auto-approved.

---

## 6. Architectural Ablation Study

Evaluated across all 210 test cases using `scripts/run_ablation_study.py`.

| Configuration | Decision Acc. | Esc. Recall | Esc. Prec. | Unsafe FPR | FNR | Routine | Edge | Adv. | Prompt Inj. Def. |
|---|---|---|---|---|---|---|---|---|---|
| **1. Full System (Proposed)** | **100.0%** | **100.0%** | **75.0%** | **0.00%** | **0.00%** | 100% | 100% | 100% | 100% |
| **2. w/o Escalation Gate** | **84.3%** | 0.0% | 0.0% | **25.00%** | 0.00% | 100% | 56.7% | 86.0% | 0.0% |
| **3. w/o Consensus Arbiter** | **100.0%** | 100.0% | 75.0% | 0.00% | 0.00% | 100% | 100% | 100% | 100% |
| **4. w/o Prompt Inj. Screen** | **99.5%** | 96.9% | 74.4% | **1.39%** | 0.00% | 100% | 100% | 98.0% | **50.0%** |
| **5. w/o Dense Retrieval** | **100.0%** | 100.0% | 57.9% | 0.00% | **9.42%** | 100% | 100% | 100% | 100% |
| **6. w/o Citation Guard** | **100.0%** | 100.0% | 75.0% | 0.00% | 0.00% | 100% | 100% | 100% | 100% |

### Key Scientific Insights:
1. **Criticality of the Escalation Gate:** Removing human escalation degrades accuracy from 100% to 84.3% and produces an unacceptable **25.00% Unsafe Auto-Approval False Positive Rate**.
2. **Multi-Layer Defense Against Prompt Injection:** Disabling keyword pre-screening cuts prompt injection defense in half (from 100% to 50%) and causes safety leakage.
3. **Retrieval Grounding:** Disabling dense RAG retrieval triggers the hardened citation guard (which detects zero retrieved policy evidence), driving escalation precision down to 57.9% and false negative rates to 9.42%.

Generated vector figures:
- `figures/ablation_decision_accuracy.pdf`
- `figures/ablation_escalation_tradeoff.pdf`
- `figures/ablation_adversarial_breakdown.pdf`
- `figures/ablation_summary_matrix.pdf`

---

## 7. Persistence & Tamper-Evident Audit Verification

- **Transactional Engine:** SQLite with WAL mode and foreign key constraints prevents orphan decisions or race conditions.
- **Cryptographic Hash Chain:** Implemented in `persistence/audit_chain.py`.
- **Validation Test:** `test_tamper_detection_in_audit_chain` programmatically modifies a row's payload in the SQLite table; `verify_audit_chain()` immediately flags the block as `is_valid: False` and identifies the exact tampering offset.

---

## 8. Defensible Disclosures & Known Limitations

1. **Synthetic Evaluation Ground Truth:** The 210-case development dataset and 50-case held-out dataset are programmatically synthesized following IRDAI master circular parameters. Clinical deployment requires prospective hospital pilot validation.
2. **Bulk Evaluation Mode:** The 210-case evaluation and 6-configuration ablation study (1,260 evaluations) were conducted in deterministic fallback mode (`LLM_EXECUTION_MODE=FALLBACK_ONLY`) for cost and reproducibility reasons. Live model execution was verified independently via endpoint smoke tests and unit tests.
3. **Mock Hospital Management Systems:** EHR and Hospital Management Information System (HMIS) integrations are mocked via REST/JSON payloads conforming to FHIR and ABDM standards.
