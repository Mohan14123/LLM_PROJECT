"""
synthetic_evaluation/scripts/generate_ground_truth.py
-----------------------------------------------------
Phase 6 & 7: Canonical Ground Truth Generation.
Generates comprehensive ground truth records for all 300 logical test cases:
  - Expected extracted fields & normalized values
  - Missing, inferred, ambiguous, and conflicting fields
  - Schema validity and expected validation error substrings
  - Policy eligibility, coverage conditions, and rules tested
  - Financial calculations (sub-limits, co-pays, approved amounts)
  - End-to-end pipeline expected outcomes and failure stages
Outputs:
  - synthetic_evaluation/ground_truth/ground_truth.jsonl
  - synthetic_evaluation/ground_truth/field_mapping.json
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def generate_ground_truth(base_dir: Path):
    canonical_cases_dir = base_dir / "canonical_cases"
    case_files = sorted(canonical_cases_dir.glob("TC-*.json"))

    gt_dir = base_dir / "ground_truth"
    gt_dir.mkdir(parents=True, exist_ok=True)

    # Load policies coverage matrix
    cov_matrix_path = base_dir / "policy_ground_truth" / "coverage_matrix.json"
    with open(cov_matrix_path, "r", encoding="utf-8") as f:
        coverage_matrix = json.load(f)

    gt_records: list[dict[str, Any]] = []

    for cf in case_files:
        with open(cf, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        cid = cdata["test_case_id"]
        cat = cdata["category"]
        pid = cdata["policy_id"]
        payload = cdata["payload"]
        pol_cov = coverage_matrix.get(pid, {})

        pat = payload.get("patient", {})
        hosp = payload.get("hospital", {})
        diag = payload.get("diagnosis", {})
        proc = payload.get("procedure", {})
        cost = payload.get("cost_estimate", {})

        is_schema_valid = cdata.get("expected_schema_valid", True)
        exp_outcome = cdata.get("expected_policy_outcome", "AUTHORISE")

        # Financial logic
        claimed = Decimal(str(cost.get("total_amount", "0"))) if cost.get("total_amount") and not str(cost.get("total_amount")).startswith("-") else Decimal("0.00")
        sublimit_ded = Decimal("0.00")
        copay_ded = Decimal("0.00")

        # Check sub-limit on procedure/diagnosis
        sublimits = pol_cov.get("disease_sublimits", {})
        for cond_name, sub_info in sublimits.items():
            if cond_name.lower() in diag.get("description", "").lower() or cond_name.lower() in proc.get("description", "").lower():
                cap = Decimal(sub_info["cap_inr"])
                if claimed > cap:
                    sublimit_ded = claimed - cap
                break

        admissible_before_copay = max(claimed - sublimit_ded, Decimal("0.00"))
        copay_pct = Decimal(str(pol_cov.get("copay_percentage", "0.00")))
        if copay_pct > Decimal("0.00") and admissible_before_copay > Decimal("0.00"):
            copay_ded = (admissible_before_copay * (copay_pct / Decimal("100"))).quantize(Decimal("0.01"))

        approved = max(admissible_before_copay - copay_ded, Decimal("0.00"))

        # Missing / ambiguous / conflicting field tracking
        missing_fields = []
        if not pat.get("full_name"):
            missing_fields.append("patient.full_name")
        if not diag.get("icd10_code"):
            missing_fields.append("diagnosis.icd10_code")
        if not cost.get("line_items"):
            missing_fields.append("cost_estimate.line_items")

        ambiguous_fields = []
        if cat == "missing_and_ambiguous":
            if "R10.9" in str(diag.get("icd10_code", "")):
                ambiguous_fields.append("diagnosis.icd10_code")
            if "possible" in str(proc.get("description", "")).lower():
                ambiguous_fields.append("procedure.description")
            if not payload.get("clinical_notes"):
                ambiguous_fields.append("clinical_notes")

        conflicting_fields = []
        if cat == "cross_field_conflicts":
            if pat.get("policy_number") != payload.get("policy", {}).get("policy_number"):
                conflicting_fields.append("patient.policy_number != policy.policy_number")
            if payload.get("admission_date") and payload.get("policy", {}).get("policy_start_date") and payload["admission_date"] < payload["policy"]["policy_start_date"]:
                conflicting_fields.append("admission_date < policy.policy_start_date")
            if "discrepancy" in cdata.get("description", "").lower():
                conflicting_fields.append("cost_estimate.total_amount != sum(line_items)")

        failure_stage = "NONE"
        if not is_schema_valid:
            failure_stage = "SCHEMA_VALIDATION" if cat == "invalid_schema" else "CROSS_FIELD_VALIDATION"
        elif cat == "missing_and_ambiguous":
            failure_stage = "CLINICAL_QUERY_GATE"

        record = {
            "test_case_id": cid,
            "policy_id": pid,
            "policy_version": cdata.get("policy_version", "1.0"),
            "scenario_id": cdata.get("scenario_id", "SCN-001"),
            "category": cat,
            "ground_truth": {
                "expected_extracted_fields": {
                    "patient_name": pat.get("full_name"),
                    "age": pat.get("age"),
                    "gender": pat.get("gender"),
                    "policy_number": pat.get("policy_number"),
                    "hospital_name": hosp.get("name"),
                    "hospital_network_tier": hosp.get("network_tier"),
                    "diagnosis_description": diag.get("description"),
                    "icd10_code": diag.get("icd10_code"),
                    "procedure_description": proc.get("description"),
                    "procedure_code": proc.get("procedure_code"),
                    "admission_type": proc.get("admission_type"),
                    "total_claimed_inr": str(claimed),
                },
                "normalized_values": {
                    "gender": pat.get("gender"),
                    "admission_date": payload.get("admission_date"),
                    "total_amount_inr": str(claimed),
                },
                "missing_fields": missing_fields,
                "inferred_fields": ["hospital.facility_category", "procedure.admission_type"] if not missing_fields else [],
                "ambiguous_fields": ambiguous_fields,
                "conflicting_fields": conflicting_fields,
                "schema_valid": is_schema_valid,
                "expected_validation_errors": [cdata.get("expected_error_substring")] if cdata.get("expected_error_substring") else [],
                "patient_eligibility": is_schema_valid and cat != "cross_field_conflicts",
                "policy_eligibility": is_schema_valid and "REJECT" not in exp_outcome,
                "coverage_applicability": is_schema_valid and exp_outcome in ("AUTHORISE", "ESCALATE"),
                "policy_rules_tested": cdata.get("rules_tested", []),
                "financial_calculations": {
                    "claimed_amount_inr": str(claimed),
                    "sublimit_deduction_inr": str(sublimit_ded),
                    "copay_deduction_inr": str(copay_ded),
                    "expected_approved_inr": str(approved) if is_schema_valid and exp_outcome == "AUTHORISE" else "0.00",
                },
                "expected_policy_outcome": exp_outcome,
                "expected_clarification": cat in ("missing_and_ambiguous", "invalid_schema"),
                "expected_query_notice": cat == "missing_and_ambiguous",
                "expected_pipeline_stage_failure": failure_stage,
            },
        }
        gt_records.append(record)

    # Save to ground_truth.jsonl
    gt_file = gt_dir / "ground_truth.jsonl"
    with open(gt_file, "w", encoding="utf-8") as f:
        for r in gt_records:
            f.write(json.dumps(r) + "\n")

    # Generate field_mapping.json
    field_mapping = {
        "critical_fields": [
            {"field": "patient.full_name", "description": "Legal name of the insured patient", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
            {"field": "patient.policy_number", "description": "Unique insurance policy contract ID", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
            {"field": "hospital.name", "description": "Treating hospital healthcare facility", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
            {"field": "diagnosis.icd10_code", "description": "WHO ICD-10 diagnostic condition code", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
            {"field": "procedure.procedure_code", "description": "Clinical procedure / intervention code", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
            {"field": "cost_estimate.total_amount", "description": "Total estimated hospital claimed cost", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
            {"field": "admission_date", "description": "Date of hospital admission", "criticality": "HIGH", "fabrication_penalty": "FATAL"},
        ],
        "non_critical_fields": [
            {"field": "patient.age", "description": "Age in completed years", "criticality": "MEDIUM"},
            {"field": "patient.gender", "description": "Gender as recorded on policy", "criticality": "MEDIUM"},
            {"field": "hospital.facility_category", "description": "Hospital infrastructure category", "criticality": "LOW"},
            {"field": "procedure.admission_type", "description": "Emergency, Planned, or Day-Care", "criticality": "MEDIUM"},
            {"field": "clinical_notes", "description": "Physician clinical observations", "criticality": "LOW"},
        ],
    }

    with open(gt_dir / "field_mapping.json", "w", encoding="utf-8") as f:
        json.dump(field_mapping, f, indent=2)

    print(f"\n--- GROUND TRUTH GENERATION COMPLETE ---")
    print(f"Generated {len(gt_records)} records in {gt_file}")
    print(f"Saved field mapping schema in {gt_dir / 'field_mapping.json'}")


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    generate_ground_truth(base_dir)


if __name__ == "__main__":
    main()
