"""
synthetic_evaluation/scripts/generate_patient_scenarios.py
---------------------------------------------------------
Phase 3 Generator: Generates 300 unique, policy-linked patient scenarios
against the 35 synthetic insurance policies, fully aligned with schemas.pre_auth_request.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Reproducibility seed
RANDOM_SEED = 42


def get_clinical_catalogue() -> list[dict[str, Any]]:
    return [
        {
            "condition": "Cataract",
            "icd10": "H25.1",
            "diag_desc": "Senile nuclear cataract, bilateral grade 3",
            "procedure": "Phacoemulsification with foldable intraocular lens (IOL) implantation",
            "proc_code": "PROC-CAT-01",
            "category": "day_care_center",
            "typical_cost": "42000.00",
            "admission_type": "day_care",
            "is_ped": False,
            "specific_disease": True,
        },
        {
            "condition": "Gallstones",
            "icd10": "K80.20",
            "diag_desc": "Calculus of gallbladder without cholecystitis without obstruction",
            "procedure": "Laparoscopic cholecystectomy",
            "proc_code": "PROC-SURG-LAP-02",
            "category": "multi_specialty",
            "typical_cost": "95000.00",
            "admission_type": "planned",
            "is_ped": False,
            "specific_disease": True,
        },
        {
            "condition": "Hernia",
            "icd10": "K40.90",
            "diag_desc": "Unilateral inguinal hernia, without obstruction or gangrene",
            "procedure": "Laparoscopic total extraperitoneal (TEP) hernioplasty with mesh repair",
            "proc_code": "PROC-SURG-HER-01",
            "category": "multi_specialty",
            "typical_cost": "68000.00",
            "admission_type": "planned",
            "is_ped": False,
            "specific_disease": True,
        },
        {
            "condition": "Knee Osteoarthritis",
            "icd10": "M17.11",
            "diag_desc": "Primary unilateral osteoarthritis, right knee grade 4",
            "procedure": "Total knee replacement (TKR) unilateral right with cruciate retaining implant",
            "proc_code": "PROC-ORTHO-TKR-01",
            "category": "multi_specialty",
            "typical_cost": "240000.00",
            "admission_type": "planned",
            "is_ped": False,
            "specific_disease": True,
        },
        {
            "condition": "Acute Appendicitis",
            "icd10": "K35.80",
            "diag_desc": "Unspecified acute appendicitis with localized peritonitis",
            "procedure": "Emergency laparoscopic appendectomy",
            "proc_code": "PROC-SURG-APP-01",
            "category": "multi_specialty",
            "typical_cost": "78000.00",
            "admission_type": "emergency",
            "is_ped": False,
            "specific_disease": False,
        },
        {
            "condition": "Coronary Artery Disease",
            "icd10": "I21.09",
            "diag_desc": "Acute anterior myocardial infarction (STEMI)",
            "procedure": "Primary percutaneous transluminal coronary angioplasty (PTCA) with drug-eluting stent",
            "proc_code": "PROC-CARD-PTCA-01",
            "category": "multi_specialty",
            "typical_cost": "285000.00",
            "admission_type": "emergency",
            "is_ped": True,
            "specific_disease": False,
        },
        {
            "condition": "Kidney Stones",
            "icd10": "N20.1",
            "diag_desc": "Calculus of ureter with moderate hydronephrosis",
            "procedure": "Ureteroscopic lithotripsy (URSL) with DJ stenting",
            "proc_code": "PROC-URO-LITH-01",
            "category": "day_care_center",
            "typical_cost": "52000.00",
            "admission_type": "planned",
            "is_ped": False,
            "specific_disease": True,
        },
        {
            "condition": "End-Stage Renal Disease",
            "icd10": "N18.6",
            "diag_desc": "End stage renal disease on maintenance hemodialysis",
            "procedure": "Hemodialysis single session via AV fistula",
            "proc_code": "PROC-MED-HEMO-01",
            "category": "day_care_center",
            "typical_cost": "4500.00",
            "admission_type": "day_care",
            "is_ped": True,
            "specific_disease": False,
        },
        {
            "condition": "Pneumonia",
            "icd10": "J18.9",
            "diag_desc": "Pneumonia, unspecified organism with acute respiratory distress",
            "procedure": "Inpatient medical management with intravenous antibiotics and oxygen therapy",
            "proc_code": "PROC-MED-CON-01",
            "category": "multi_specialty",
            "typical_cost": "87000.00",
            "admission_type": "emergency",
            "is_ped": False,
            "specific_disease": False,
        },
        {
            "condition": "Accidental Bone Fracture",
            "icd10": "S82.201A",
            "diag_desc": "Closed fracture of shaft of right tibia due to road traffic collision",
            "procedure": "Open reduction and internal fixation (ORIF) with interlocking intramedullary nail",
            "proc_code": "PROC-ORTHO-ORIF-01",
            "category": "multi_specialty",
            "typical_cost": "115000.00",
            "admission_type": "emergency",
            "is_ped": False,
            "specific_disease": False,
        },
        {
            "condition": "Cosmetic Rhinoplasty",
            "icd10": "Z41.1",
            "diag_desc": "Encounter for cosmetic aesthetic rhinoplasty",
            "procedure": "Elective cosmetic rhinoplasty and septal reshaping",
            "proc_code": "PROC-COSM-01",
            "category": "private",
            "typical_cost": "120000.00",
            "admission_type": "planned",
            "is_ped": False,
            "specific_disease": False,
            "is_excluded": True,
        },
    ]


FIRST_NAMES = [
    "Aarav", "Ananya", "Rajesh", "Pooja", "Vikram", "Sunita", "Suresh", "Lakshmi",
    "Amit", "Divya", "Anil", "Meena", "Deepak", "Shweta", "Karthik", "Sneha",
    "Arjun", "Kavita", "Ramesh", "Neha", "Manoj", "Anita", "Vijay", "Aarti",
    "Rohan", "Priya", "Sunil", "Geeta", "Sanjay", "Rekha"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Iyer", "Nair",
    "Reddy", "Rao", "Deshmukh", "Joshi", "Kulkarni", "Banerjee", "Mehta", "Shah"
]

HOSPITALS = [
    {"name": "Apollo Multispeciality Hospital", "tier": "cashless_network", "category": "multi_specialty", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "Fortis Memorial Research Institute", "tier": "cashless_network", "category": "multi_specialty", "city": "Gurugram", "state": "Haryana"},
    {"name": "Max Super Speciality Hospital", "tier": "cashless_network", "category": "multi_specialty", "city": "New Delhi", "state": "Delhi"},
    {"name": "Manipal Hospital", "tier": "cashless_network", "category": "multi_specialty", "city": "Chennai", "state": "Tamil Nadu"},
    {"name": "Narayana Health City", "tier": "cashless_network", "category": "multi_specialty", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "Sunshine Community Nursing Home", "tier": "non_network", "category": "private", "city": "Lucknow", "state": "Uttar Pradesh"},
    {"name": "Lifeline Day Care Surgery Centre", "tier": "cashless_network", "category": "day_care_center", "city": "Pune", "state": "Maharashtra"},
    {"name": "Care & Cure Rural Hospital", "tier": "non_network", "category": "trust", "city": "Ahmedabad", "state": "Gujarat"},
]


def generate_scenarios(base_dir: Path, num_scenarios: int = 300) -> list[dict[str, Any]]:
    random.seed(RANDOM_SEED)

    canonical_dir = base_dir / "policies" / "canonical"
    policy_files = sorted(canonical_dir.glob("POL-*.json"))
    policies: list[dict[str, Any]] = []
    for pf in policy_files:
        with open(pf, "r", encoding="utf-8") as f:
            policies.append(json.load(f))

    catalogue = get_clinical_catalogue()
    scenarios: list[dict[str, Any]] = []

    for i in range(1, num_scenarios + 1):
        scn_id = f"SCN-{i:03d}"
        assigned_policy = policies[(i - 1) % len(policies)]
        pid = assigned_policy["policy_id"]
        pversion = assigned_policy.get("policy_version", "1.0")

        clin = catalogue[(i - 1) % len(catalogue)]
        hosp = HOSPITALS[(i - 1) % len(HOSPITALS)]

        patient_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        gender = "male" if random.random() > 0.48 else "female"
        age = random.randint(22, 75) if "Senior" not in assigned_policy["policy_name"] else random.randint(61, 82)

        pol_start = date.fromisoformat(assigned_policy["policy_start_date"])
        if i % 10 == 0:
            adm_date = pol_start + timedelta(days=random.randint(5, 25))
        elif i % 7 == 0:
            adm_date = pol_start + timedelta(days=random.randint(200, 500))
        elif i % 5 == 0:
            adm_date = pol_start + timedelta(days=random.randint(600, 900))
        else:
            adm_date = pol_start + timedelta(days=random.randint(1100, 1500))

        room_categories = ["Single Private A/C Room", "Twin Sharing", "General Ward", "Deluxe Suite"]
        room_cat = room_categories[i % len(room_categories)]

        base_cost = Decimal(clin["typical_cost"])
        room_days = 1 if clin["admission_type"] == "day_care" else random.randint(2, 5)
        room_rate = Decimal("4000.00") if "General" in room_cat else (Decimal("6500.00") if "Private" in room_cat else Decimal("12000.00"))
        room_total = (room_rate * room_days).quantize(Decimal("0.01"))

        surgeon_fee = (base_cost * Decimal("0.35")).quantize(Decimal("0.01"))
        ot_charges = (base_cost * Decimal("0.20")).quantize(Decimal("0.01"))
        pharmacy = (base_cost * Decimal("0.15")).quantize(Decimal("0.01"))
        investigations = (base_cost * Decimal("0.10")).quantize(Decimal("0.01"))
        remaining_cost = (base_cost - (surgeon_fee + ot_charges + pharmacy + investigations)).quantize(Decimal("0.01"))
        total_estimate = (room_total + surgeon_fee + ot_charges + pharmacy + investigations + remaining_cost).quantize(Decimal("0.01"))

        line_items = [
            {"item": f"Room & Nursing Charges ({room_cat}, {room_days} days)", "amount": str(room_total), "category": "room_rent"},
            {"item": "Professional Surgeon & Anesthetist Consultation", "amount": str(surgeon_fee), "category": "surgeon_fee"},
            {"item": "Operation Theatre & Equipment Consumables", "amount": str(ot_charges), "category": "consumables"},
            {"item": "Inpatient Pharmacy & Surgical Implants", "amount": str(pharmacy), "category": "pharmacy"},
            {"item": "Pre-operative Diagnostic Investigations & Pathology", "amount": str(investigations), "category": "diagnostic"},
            {"item": "Miscellaneous Consumables & Monitoring", "amount": str(remaining_cost), "category": "other"},
        ]

        scn_entry = {
            "scenario_id": scn_id,
            "test_case_id": f"TC-{i:03d}",
            "policy_id": pid,
            "policy_version": pversion,
            "policy_name": assigned_policy["policy_name"],
            "patient_id": str(uuid.uuid4()),
            "policyholder_id": f"PH-{random.randint(100000, 999999)}",
            "patient_name": patient_name,
            "patient_age": age,
            "patient_gender": gender,
            "hospital_name": hosp["name"],
            "hospital_tier": hosp["tier"],
            "hospital_category": hosp["category"],
            "hospital_city": hosp["city"],
            "hospital_state": hosp["state"],
            "admission_date": str(adm_date),
            "admission_type": clin["admission_type"],
            "room_category": room_cat,
            "room_days": room_days,
            "primary_diagnosis": {
                "description": clin["diag_desc"],
                "icd10_code": clin["icd10"],
                "is_pre_existing": clin["is_ped"],
            },
            "proposed_procedure": {
                "description": clin["procedure"],
                "procedure_code": clin["proc_code"],
                "admission_type": clin["admission_type"],
            },
            "cost_estimate": {
                "total_amount": str(total_estimate),
                "currency": "INR",
                "line_items": line_items,
            },
            "relevant_medical_history": "Hypertension under medical control" if clin["is_ped"] else "Nil significant medical history",
            "pre_existing_diseases": ["Hypertension (Grade 1)", "Type 2 Diabetes Mellitus"] if clin["is_ped"] else [],
            "supporting_documents": [
                f"Physician consultation referral for {clin['condition']}",
                "Diagnostic ultrasound / clinical blood chemistry panel",
                "Hospital pre-authorization itemized proforma invoice",
            ],
            "is_excluded_condition": clin.get("is_excluded", False),
        }
        scenarios.append(scn_entry)

    out_file = base_dir / "patient_scenarios" / "scenarios.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps(s) + "\n")

    print(f"\n--- PATIENT SCENARIOS GENERATED ---")
    print(f"Total Scenarios: {len(scenarios)} saved in {out_file}")
    return scenarios


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    generate_scenarios(base_dir, 300)


if __name__ == "__main__":
    main()
