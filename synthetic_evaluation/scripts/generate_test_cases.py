"""
synthetic_evaluation/scripts/generate_test_cases.py
---------------------------------------------------
Phase 4 Generator: Generates exactly 300 unique logical test cases
fully aligned with schemas.pre_auth_request, covering:
  - Happy Path (100 cases, TC-001 to TC-100)
  - Valid Edge Cases (80 cases, TC-101 to TC-180)
  - Invalid Schema Cases (45 cases, TC-181 to TC-225)
  - Cross-Field Conflicts (30 cases, TC-226 to TC-255)
  - OCR & Extraction Stress (25 cases, TC-256 to TC-280)
  - Missing & Ambiguous Info (20 cases, TC-281 to TC-300)
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from schemas import PreAuthRequest, SourceFormat, RequestStatus, PlanType


def load_scenarios_and_policies(base_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    scenarios_file = base_dir / "patient_scenarios" / "scenarios.jsonl"
    scenarios: list[dict[str, Any]] = []
    with open(scenarios_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                scenarios.append(json.loads(line))

    policies: dict[str, dict[str, Any]] = {}
    canonical_dir = base_dir / "policies" / "canonical"
    for pf in canonical_dir.glob("POL-*.json"):
        with open(pf, "r", encoding="utf-8") as f:
            p = json.load(f)
            policies[p["policy_id"]] = p

    return scenarios, policies


def build_preauth_dict(scn: dict[str, Any], pol: dict[str, Any], case_id: str, source_format: str = "json") -> dict[str, Any]:
    """Assemble a standard pre-auth dictionary strictly conforming to PreAuthRequest schema."""
    sub_limits_dict = {}
    for k, v in pol.get("disease_sublimits", {}).items():
        sub_limits_dict[k] = v["cap_inr"]

    endorsements = []
    if pol.get("waiting_periods", {}).get("waiver_endorsement"):
        endorsements.append("WAITING_PERIOD_WAIVER_SCHEDULE_01")

    return {
        "request_id": str(uuid.uuid4()),
        "submitted_at": scn["admission_date"],
        "admission_date": scn["admission_date"],
        "source_format": source_format,
        "status": RequestStatus.PENDING.value,
        "patient": {
            "patient_id": scn["patient_id"],
            "full_name": scn["patient_name"],
            "age": scn["patient_age"],
            "gender": scn["patient_gender"],
            "policy_number": pol["policy_id"],
        },
        "policy": {
            "policy_number": pol["policy_id"],
            "plan_type": pol["policy_type"],
            "sum_insured": pol["sum_insured"]["amount"],
            "policy_start_date": pol["policy_start_date"],
            "waiting_period_months": pol["waiting_periods"].get("specific_disease_months", 24),
            "ped_waiting_period_months": pol["waiting_periods"].get("ped_months", 36),
            "sub_limits": {"limits": sub_limits_dict},
            "co_pay_pct": pol["co_payment"].get("mandatory_pct", "0.00"),
            "product_uin": pol.get("product_uin"),
            "product_version": pol.get("product_version", "2024.1"),
            "endorsements": endorsements,
        },
        "hospital": {
            "hospital_id": str(uuid.uuid4()),
            "name": scn["hospital_name"],
            "city": scn["hospital_city"],
            "network_tier": scn["hospital_tier"],
            "category": scn["hospital_category"],
        },
        "diagnosis": {
            "description": scn["primary_diagnosis"]["description"],
            "icd10_code": scn["primary_diagnosis"]["icd10_code"],
            "is_pre_existing": scn["primary_diagnosis"]["is_pre_existing"],
        },
        "procedure": {
            "description": scn["proposed_procedure"]["description"],
            "procedure_code": scn["proposed_procedure"]["procedure_code"],
            "admission_type": scn["proposed_procedure"]["admission_type"],
        },
        "cost_estimate": {
            "total_amount": scn["cost_estimate"]["total_amount"],
            "line_items": scn["cost_estimate"]["line_items"],
        },
        "clinical_notes": f"Admitted for elective/emergency management. Medical history: {scn['relevant_medical_history']}.",
    }


def generate_all_300_cases(base_dir: Path) -> list[dict[str, Any]]:
    scenarios, policies = load_scenarios_and_policies(base_dir)
    canonical_cases_dir = base_dir / "canonical_cases"
    canonical_cases_dir.mkdir(parents=True, exist_ok=True)

    all_cases: list[dict[str, Any]] = []

    for i in range(1, 301):
        cid = f"TC-{i:03d}"
        scn = scenarios[i - 1]
        pol = policies[scn["policy_id"]]

        # -------------------------------------------------------------
        # Category 1: HAPPY PATH (TC-001 to TC-100)
        # -------------------------------------------------------------
        if 1 <= i <= 100:
            category = "happy_path"
            data = build_preauth_dict(scn, pol, cid)
            pol_start = date.fromisoformat(pol["policy_start_date"])
            safe_adm = pol_start + timedelta(days=1200)
            data["admission_date"] = str(safe_adm)
            data["submitted_at"] = str(safe_adm)
            data["diagnosis"]["is_pre_existing"] = False
            data["hospital"]["network_tier"] = "cashless_network"

            case_meta = {
                "test_case_id": cid,
                "category": category,
                "scenario_id": scn["scenario_id"],
                "policy_id": pol["policy_id"],
                "policy_version": pol["policy_version"],
                "description": f"Happy path: {scn['primary_diagnosis']['description']} at {data['hospital']['name']}",
                "expected_schema_valid": True,
                "expected_policy_outcome": "AUTHORISE",
                "rules_tested": [r["rule_id"] for r in pol.get("rules", [])],
                "payload": data,
            }

        # -------------------------------------------------------------
        # Category 2: VALID EDGE CASES (TC-101 to TC-180)
        # -------------------------------------------------------------
        elif 101 <= i <= 180:
            category = "valid_edge_cases"
            data = build_preauth_dict(scn, pol, cid)
            edge_type = i % 8

            if edge_type == 0:
                data["cost_estimate"]["line_items"][0]["amount"] = "55000.00"
                total = sum(Decimal(it["amount"]) for it in data["cost_estimate"]["line_items"])
                data["cost_estimate"]["total_amount"] = str(total)
                exp_outcome = "AUTHORISE"
                desc = "Cost exceeds disease sub-limit cap; test sub-limit reduction"
            elif edge_type == 1:
                data["cost_estimate"]["line_items"][0]["amount"] = "350000.00"
                total = sum(Decimal(it["amount"]) for it in data["cost_estimate"]["line_items"])
                data["cost_estimate"]["total_amount"] = str(total)
                exp_outcome = "AUTHORISE"
                desc = "High financial claim amount within high sum insured"
            elif edge_type == 2:
                data["cost_estimate"]["line_items"][0]["amount"] = "12500.75"
                data["cost_estimate"]["line_items"][1]["amount"] = "15000.25"
                total = sum(Decimal(it["amount"]) for it in data["cost_estimate"]["line_items"])
                data["cost_estimate"]["total_amount"] = str(total)
                exp_outcome = "AUTHORISE"
                desc = "Paise decimal precision calculations"
            elif edge_type == 3:
                data["patient"]["full_name"] = "Dr. Venkata Satyanarayana Ramakrishna Murthy-Venkateshwaran"
                exp_outcome = "AUTHORISE"
                desc = "Long patient name boundary string"
            elif edge_type == 4:
                pol_start = date.fromisoformat(pol["policy_start_date"])
                adm = pol_start + timedelta(days=32)
                data["admission_date"] = str(adm)
                data["submitted_at"] = str(adm)
                exp_outcome = "AUTHORISE"
                desc = "Admission exactly after 30-day initial waiting period expires"
            elif edge_type == 5:
                data["hospital"]["network_tier"] = "non_network"
                exp_outcome = "ESCALATE"
                desc = "Non-network hospital pre-auth trigger"
            elif edge_type == 6:
                orig_items = data["cost_estimate"]["line_items"]
                more_items = copy.deepcopy(orig_items[:4])
                for idx, it in enumerate(more_items, start=7):
                    it["item"] = f"Specialist Consultation Add-on #{idx}"
                    it["amount"] = "2500.00"
                    it["category"] = "diagnostic"
                data["cost_estimate"]["line_items"].extend(more_items)
                total = sum(Decimal(it["amount"]) for it in data["cost_estimate"]["line_items"])
                data["cost_estimate"]["total_amount"] = str(total)
                exp_outcome = "AUTHORISE"
                desc = "Extended 10-line-item billing reconciliation"
            else:
                data["policy"]["co_pay_pct"] = "20.00"
                exp_outcome = "AUTHORISE"
                desc = "Mandatory 20% co-payment computation"

            case_meta = {
                "test_case_id": cid,
                "category": category,
                "scenario_id": scn["scenario_id"],
                "policy_id": pol["policy_id"],
                "policy_version": pol["policy_version"],
                "description": desc,
                "expected_schema_valid": True,
                "expected_policy_outcome": exp_outcome,
                "rules_tested": [r["rule_id"] for r in pol.get("rules", [])],
                "payload": data,
            }

        # -------------------------------------------------------------
        # Category 3: INVALID SCHEMA CASES (TC-181 to TC-225, 45 cases)
        # -------------------------------------------------------------
        elif 181 <= i <= 225:
            category = "invalid_schema"
            data = build_preauth_dict(scn, pol, cid)
            inv_type = i % 9

            if inv_type == 0:
                data["patient"]["full_name"] = ""
                err = "String should have at least 1 character"
                desc = "Empty patient full_name string"
            elif inv_type == 1:
                data["patient"]["gender"] = "NON_BINARY_UNREGISTERED"
                err = "Input should be 'male', 'female', 'other' or 'prefer_not_to_say'"
                desc = "Invalid Gender enum"
            elif inv_type == 2:
                data["cost_estimate"]["total_amount"] = "-45000.00"
                err = "Input should be greater than or equal to 0"
                desc = "Negative financial cost amount"
            elif inv_type == 3:
                data["admission_date"] = "31-02-2024"
                err = "Input should be a valid date or date-time"
                desc = "Malformed non-ISO admission date format"
            elif inv_type == 4:
                data["cost_estimate"]["total_amount"] = "999999.00"
                err = "exceeds the +/- 1 INR reconciliation tolerance"
                desc = "Cost estimate reconciliation discrepancy > 1 INR"
            elif inv_type == 5:
                data["policy"]["plan_type"] = "COMMUNITY_POOL"
                err = "Input should be 'individual', 'family_floater', 'group', 'senior_citizen', 'critical_illness', 'top_up' or 'super_top_up'"
                desc = "Invalid PlanType enum value"
            elif inv_type == 6:
                data["diagnosis"]["icd10_code"] = ""
                err = "String should have at least 1 character"
                desc = "Missing mandatory diagnosis ICD-10 code"
            elif inv_type == 7:
                data["cost_estimate"]["line_items"][0]["amount"] = "-1500.00"
                err = "Input should be greater than or equal to 0"
                desc = "Negative line-item amount"
            else:
                data["cost_estimate"]["line_items"] = []
                err = "List should have at least 1 item"
                desc = "Empty cost estimate line items list"

            case_meta = {
                "test_case_id": cid,
                "category": category,
                "scenario_id": scn["scenario_id"],
                "policy_id": pol["policy_id"],
                "policy_version": pol["policy_version"],
                "description": desc,
                "expected_schema_valid": False,
                "expected_error_substring": err,
                "expected_policy_outcome": "REJECT_INVALID_SCHEMA",
                "rules_tested": ["SCHEMA_VALIDATION_GATE"],
                "payload": data,
            }

        # -------------------------------------------------------------
        # Category 4: CROSS-FIELD CONFLICTS (TC-226 to TC-255, 30 cases)
        # -------------------------------------------------------------
        elif 226 <= i <= 255:
            category = "cross_field_conflicts"
            data = build_preauth_dict(scn, pol, cid)
            cf_type = i % 3

            if cf_type == 0:
                data["patient"]["policy_number"] = "POL-CONFLICT-999"
                err = "patient.policy_number ('POL-CONFLICT-999') does not match policy.policy_number"
                desc = "Referential integrity conflict: patient policy number does not match policy"
            elif cf_type == 1:
                pol_start = date.fromisoformat(pol["policy_start_date"])
                data["admission_date"] = str(pol_start - timedelta(days=60))
                err = "is before policy.policy_start_date"
                desc = "Temporal coverage conflict: admission date precedes policy inception"
            else:
                orig_total = Decimal(data["cost_estimate"]["total_amount"])
                data["cost_estimate"]["total_amount"] = str(orig_total + Decimal("500.00"))
                err = "exceeds the +/- 1 INR reconciliation tolerance"
                desc = "Financial cross-field contradiction between line items and total"

            case_meta = {
                "test_case_id": cid,
                "category": category,
                "scenario_id": scn["scenario_id"],
                "policy_id": pol["policy_id"],
                "policy_version": pol["policy_version"],
                "description": desc,
                "expected_schema_valid": False,
                "expected_error_substring": err,
                "expected_policy_outcome": "REJECT_CROSS_FIELD_CONFLICT",
                "rules_tested": ["CROSS_FIELD_INTEGRITY"],
                "payload": data,
            }

        # -------------------------------------------------------------
        # Category 5: OCR & EXTRACTION STRESS (TC-256 to TC-280, 25 cases)
        # -------------------------------------------------------------
        elif 256 <= i <= 280:
            category = "ocr_stress"
            data = build_preauth_dict(scn, pol, cid, source_format="scanned_image")
            stress_types = ["gaussian_blur", "downsample_low_res", "rotation_skew", "noise_speckle", "contrast_fade"]
            chosen_stress = stress_types[(i - 256) % len(stress_types)]

            case_meta = {
                "test_case_id": cid,
                "category": category,
                "scenario_id": scn["scenario_id"],
                "policy_id": pol["policy_id"],
                "policy_version": pol["policy_version"],
                "ocr_distortion": chosen_stress,
                "description": f"OCR degradation stress test: {chosen_stress}",
                "expected_schema_valid": True,
                "expected_policy_outcome": "AUTHORISE",
                "rules_tested": ["OCR_EXTRACTION_ROBUSTNESS"],
                "payload": data,
            }

        # -------------------------------------------------------------
        # Category 6: MISSING & AMBIGUOUS INFO (TC-281 to TC-300, 20 cases)
        # -------------------------------------------------------------
        else:
            category = "missing_and_ambiguous"
            data = build_preauth_dict(scn, pol, cid)
            amb_type = i % 4

            if amb_type == 0:
                data["diagnosis"]["description"] = "Unspecified abdominal pain, etiology under investigation"
                data["diagnosis"]["icd10_code"] = "R10.9"
                desc = "Ambiguous symptom-only diagnostic code (R10.9) lacking definitive etiology"
            elif amb_type == 1:
                data["procedure"]["description"] = "Diagnostic laparoscopy and possible therapeutic intervention"
                desc = "Ambiguous exploratory surgical indication without confirmed therapeutic procedure"
            elif amb_type == 2:
                data["clinical_notes"] = ""
                desc = "Missing clinical examination notes and history"
            else:
                data["hospital"]["network_tier"] = "non_network"
                data["clinical_notes"] = "Unclear whether emergency life-saving or elective observation"
                desc = "Ambiguous level of care at non-network facility"

            case_meta = {
                "test_case_id": cid,
                "category": category,
                "scenario_id": scn["scenario_id"],
                "policy_id": pol["policy_id"],
                "policy_version": pol["policy_version"],
                "description": desc,
                "expected_schema_valid": True,
                "expected_policy_outcome": "RECOMMEND_QUERY",
                "rules_tested": ["CLINICAL_AMBIGUITY_GATE"],
                "payload": data,
            }

        with open(canonical_cases_dir / f"{cid}.json", "w", encoding="utf-8") as f:
            json.dump(case_meta, f, indent=2)

        all_cases.append(case_meta)

    print("\n--- 300 CANONICAL TEST CASES UPDATED ---")
    print(f"Total Cases: {len(all_cases)}")
    return all_cases


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    generate_all_300_cases(base_dir)


if __name__ == "__main__":
    main()
