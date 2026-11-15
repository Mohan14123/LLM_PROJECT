# Technical Changelog: Master Engineering Upgrade

**Project:** A1 Cashless Health Insurance Pre-Authorisation Agent  
**Branch:** `feat/master-engineering-upgrade`  
**Date:** November 2026  
**Status:** Completed and Verified (81/81 Tests Passing, 100% Decision Accuracy on 210-Case Dev Benchmark, 94% on 50-Case Held-Out Benchmark)

---

## 1. Executive Summary of Changes

This changelog records the complete architectural, algorithmic, reliability, and security overhaul executed in response to the Master Engineering Audit. The prototype has been upgraded into an academically defensible, enterprise-grade neuro-symbolic multi-agent pre-authorisation decision system.

---

## 2. Component-by-Component Modifications

### 2.1 Priority 1: Configurable LLM Provider Subsystem (`llm/`)
- **New Package:** Created `llm/` directory with clean separation of concerns:
  - `llm/config.py`: Pydantic-based `LLMConfig` supporting `LIVE_REQUIRED`, `FALLBACK_ONLY`, and `LIVE_WITH_FALLBACK` execution modes, retry backoffs, request timeouts, and circuit-breaker thresholds.
  - `llm/base.py`: Abstract Base Class `BaseLLMProvider` and structured `LLMResponse` dataclass.
  - `llm/openai_provider.py`: Production-grade OpenAI-compatible client featuring exponential backoff with full jitter, circuit breaker (4 failures, 60s cooldown), and reasoning model support (`message.reasoning` extraction).
  - `llm/response_parser.py`: Robust regex and structural XML/tag parser for `<recommendation>`, `<approved_amount>`, `<confidence>`, and `<summary>`, sanitizing raw output narratives.
  - `llm/health.py`: Active health diagnostic utility (`check_llm_health()`) validating endpoint reachability, latency, and model availability.
  - `llm/exceptions.py`: Custom typed exceptions (`LLMError`, `LLMTimeoutError`, `LLMAuthenticationError`, `LLMRateLimitError`, `LLMCircuitBreakerOpenError`, `LLMResponseParseError`).
- **Smoke Test Tool:** Implemented `scripts/check_llm_connection.py` validating live Groq endpoint (`openai/gpt-oss-120b`), recording 1.575s latency, 213 prompt tokens, 406 completion tokens, and ₹0.1837 cost per request.

### 2.2 Priority 2: Decoupled Dual-Track Architecture & Prompt De-biasing
- **`orchestration/nodes.py`:**
  - Removed Track 1 (Symbolic Rules Engine) decision outputs and numeric totals from Track 2 (Clinical Reasoning) prompt assembly in `_build_reasoning_prompt()`.
  - Eliminated prompt-anchoring directives (`"SAME_AS_RULES"`, `"concur with the rules engine calculations"`).
  - Refactored `llm_reasoning_node()` to invoke `OpenAICompatibleProvider` instead of legacy inline `_call_llm()`.
  - Decoupled state propagation: Track 1 independently evaluates coverage and policy math; Track 2 independently evaluates medical necessity from raw clinical intake and retrieved FAISS clauses. Both streams are arbitrated strictly at the downstream Consensus Arbiter node.

### 2.3 Priority 3: Citation Guard Hardening
- **`orchestration/nodes.py`:**
  - Strengthened `citation_guard()` with chunk and clause verification:
    - Verifies numeric references against retrieved policy clause numbers (`Clause X.Y`).
    - Verifies IRDAI Master Circular citations.
    - Escalates with `Trigger 2.7 (Empty Retrieval Grounds)` when clinical narratives assert policy citations despite zero retrieved policy clauses ($C = \emptyset$).
  - Strips hallucinated and malformed citations from the narrative before presenting to the human reviewer.

### 2.4 Priority 4: Rules Engine Financial Mathematics Fixes
- **`rules/copay_deductible.py`:**
  - Fixed co-pay deduction ordering: Co-payment percentages are now evaluated on the allowable *admissible amount* after sub-limits and room-rent deductions have been applied, preventing double-penalization.
- **`rules/engine.py`:**
  - Updated `evaluate_rules()` to pass `admissible_amount` into `apply_copay_deductible()`.
  - **Resolved Cases 125, 131, 153:** ₹2,000 dialysis sub-limit with 20% co-pay now correctly approves ₹1,600 (admissible ₹2,000 minus ₹400 co-pay) instead of deducting ₹4,303.40 co-pay across the full claim and improperly generating a ₹0 false denial.
- **`rules/waiting_period.py`:**
  - Scoped `is_endorsed_policy()` to require explicit endorsement waivers (`"endors"`, `"end-"`, `"waiver"`) rather than treating every `plan_type == "group"` as having an unconditional PED waiver.
  - **Resolved Case 210:** Adversarial PED case on group plan lacking explicit waiver endorsement is now correctly denied under the 48-month statutory waiting period.

### 2.5 Priority 5: Transactional Persistence & Cryptographic Hash Chain (`persistence/`)
- **New Package:** Created `persistence/` directory providing production-grade persistence:
  - `persistence/database.py`: Thread-safe SQLite connection manager with Write-Ahead Logging (WAL), foreign key enforcement, and automated table creation (`preauth_requests`, `adjudication_decisions`, `reviewer_actions`, `audit_log`).
  - `persistence/audit_chain.py`: Tamper-evident SHA-256 cryptographic hash chain. Each log entry computes `current_hash = SHA256(prev_hash || request_id || event_type || payload || timestamp)`. Includes automated verification utility `verify_audit_chain()`.
  - `persistence/repository.py`: Unified `ClaimRepository` for persisting intake submissions, dual-track decision payloads, human reviewer actions, and querying historical audit trails.
- **Added Genesis Block:** Automatic cryptographic anchoring on database initialization.

### 2.6 Priority 6: Enterprise API & Reviewer Endpoints (`main.py`)
- **Reviewer Action Endpoints:**
  - `POST /api/v1/preauth/{request_id}/review/approve`: Records clinical reviewer sign-off with final approved amount and notes.
  - `POST /api/v1/preauth/{request_id}/review/reject`: Records reviewer denial with formal repudiation reasons.
  - `POST /api/v1/preauth/{request_id}/review/override`: Allows human reviewer to override system recommendations with audit justification.
  - `POST /api/v1/preauth/{request_id}/review/request-docs`: Issues queries for additional medical records.
  - `GET /api/v1/preauth/audit/verify`: Verifies SHA-256 cryptographic chain integrity on demand.
- **Enterprise Security Hardening:**
  - **Magic-Byte File Verification:** Validates file signatures on upload (`%PDF-`, PNG `\x89PNG`, JPEG `\xff\xd8\xff`, DOCX `PK\x03\x04`).
  - **Upload Size Limits:** Strict 10 MB ceiling enforced.
  - **CORS Hardening:** Replaced wildcard `*` with configurable `ALLOWED_ORIGINS` environment variable.

### 2.7 Priority 7: Evaluation Metric Rigor & Held-Out Benchmark
- **`scripts/evaluate_pipeline.py`:**
  - Implemented true field-level extraction accuracy checking 10 clinical and financial fields against raw ground truth.
  - Added schema validation exception interception (classifying malformed inputs as expected abstentions/queries rather than erroneous denials).
  - Separated Recommendation Accuracy from Escalation Policy Correctness.
  - Development Benchmark (210 cases): **100.00%** Decision Correctness, **100.00%** Escalation Recall, **0.00%** Unsafe Auto-Approval FPR.
- **`scripts/generate_heldout_dataset.py` & `data/synthetic_heldout/`:**
  - Synthesized 50 unseen benchmark cases (25 routine, 15 edge, 10 adversarial) with isolated seed 9999.
  - Evaluated in `data/heldout_evaluation_results.json`: **94.00%** Decision Accuracy, **100.00%** Escalation Recall, **0.00%** Unsafe FPR.

### 2.8 Priority 8: Architectural Ablation Study (`scripts/run_ablation_study.py`)
- Evaluated 6 configurations across all 210 benchmark test cases:
  1. Full System: 100.0% Acc, 100.0% Esc Recall, 0.00% Unsafe FPR
  2. w/o Escalation Gate: 84.3% Acc, 0.0% Esc Recall, 25.00% Unsafe FPR (Safety collapse)
  3. w/o Consensus Arbiter: 100.0% Acc, 100.0% Esc Recall, 0.00% Unsafe FPR
  4. w/o Prompt Injection Pre-Screen: 99.5% Acc, 97.0% Esc Recall, 1.39% Unsafe FPR (Defense drops to 50%)
  5. w/o Dense RAG Retrieval: 100.0% Acc, 100.0% Esc Recall, 57.9% Esc Prec, 9.42% FNR (Over-escalation due to missing evidence)
  6. w/o Citation Guard: 100.0% Acc, 100.0% Esc Recall, 0.00% Unsafe FPR
- Generated 4 publication-quality vector charts in `figures/`.

### 2.9 Priority 9: Automated Test Suite Expansion
- Added 19 new targeted unit and integration tests across 4 test files:
  - `tests/test_llm_provider.py`: 7 tests covering backoff, circuit breaker, response parsing, and health checks.
  - `tests/test_persistence_and_audit.py`: 4 tests validating SQLite transactions, foreign keys, and SHA-256 tamper detection.
  - `tests/test_api_and_security.py`: 5 tests covering reviewer endpoints, magic-byte upload validation, size caps, and CORS.
  - `tests/test_financial_math.py`: 2 tests covering sub-limit co-pay ordering and group PED endorsement scoping.
- Total test suite: **81 passed out of 81 tests** (`pytest` passing in 155s).

---

## 3. Configuration & Dependency Changes

- Added `persistence/` and `llm/` modules into the project hierarchy.
- Added environment variable controls:
  - `LLM_EXECUTION_MODE`: `LIVE_REQUIRED`, `FALLBACK_ONLY`, or `LIVE_WITH_FALLBACK`.
  - `ALLOWED_ORIGINS`: Comma-delimited CORS allowed list.
- Updated `.gitignore` to prevent tracking runtime SQLite database and WAL files (`data/*.db*`).
