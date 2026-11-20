"""
synthetic_evaluation/scripts/generate_policies.py
------------------------------------------------
Phase 1 Generator: Generates at least 30 diverse, highly realistic synthetic
health insurance policies with canonical machine-readable schemas, granular rule sets,
clause references, and coverage matrices.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas import PlanType


def build_synthetic_policies() -> list[dict[str, Any]]:
    """Build a comprehensive corpus of 35 diverse synthetic health insurance policies."""

    policies: list[dict[str, Any]] = [
        # 1. POL-001: Standard Individual Comprehensive
        {
            "policy_id": "POL-001",
            "policy_version": "1.0",
            "policy_name": "Apex Comprehensive Health Shield",
            "insurer_name": "Apex General Insurance Corp.",
            "policy_type": PlanType.INDIVIDUAL.value,
            "product_uin": "APEX-HLT-IND-2024-V01",
            "product_version": "2024.1",
            "policyholder_eligibility": {
                "min_entry_age": 18,
                "max_entry_age": 65,
                "renewable_for_life": True,
                "residency": "Indian Resident",
            },
            "policy_start_date": "2024-01-01",
            "policy_expiry_date": "2024-12-31",
            "sum_insured": {"amount": "500000.00", "currency": "INR"},
            "available_sum_insured": {"amount": "500000.00", "currency": "INR"},
            "room_rent_limits": {
                "type": "percentage_of_sum_insured",
                "percentage": 1.0,
                "daily_cap_inr": "5000.00",
                "clause_reference": "Section 3.1.A",
                "proportional_deduction_applies": True,
            },
            "icu_limits": {
                "type": "percentage_of_sum_insured",
                "percentage": 2.0,
                "daily_cap_inr": "10000.00",
                "clause_reference": "Section 3.1.B",
            },
            "disease_sublimits": {
                "Cataract": {"cap_inr": "40000.00", "per": "per_eye", "clause": "Schedule B, Item 1"},
                "Hernia": {"cap_inr": "50000.00", "per": "per_admission", "clause": "Schedule B, Item 2"},
                "Knee Replacement": {"cap_inr": "150000.00", "per": "per_knee", "clause": "Schedule B, Item 3"},
                "Kidney Stone / Lithotripsy": {"cap_inr": "45000.00", "per": "per_admission", "clause": "Schedule B, Item 4"},
            },
            "waiting_periods": {
                "initial_days": 30,
                "initial_accident_exempt": True,
                "specific_disease_months": 24,
                "ped_months": 36,
                "statutory_moratorium_months": 60,
            },
            "co_payment": {
                "mandatory_pct": "0.00",
                "senior_citizen_pct": "10.00",
                "zone_differential_pct": "0.00",
                "clause": "Section 4.1",
            },
            "deductible": {
                "amount": "0.00",
                "currency": "INR",
                "type": "none",
            },
            "restoration_benefit": {
                "is_available": True,
                "percentage": 100.0,
                "unrelated_illness_only": True,
            },
            "exclusions": {
                "permanent": [
                    "Cosmetic, plastic or aesthetic treatments",
                    "Experimental and unproven pharmacological treatments",
                    "Self-inflicted injuries or intentional suicide attempts",
                    "Active participation in hazardous sports or adventure activities",
                ],
                "conditional": [
                    "Maternity expenses excluded unless corporate endorsement attached",
                    "Robotic surgery restricted to pre-authorised tertiary centers",
                ],
            },
            "network_hospital_conditions": "Full cashless settlement applicable at all Tier-1 and Tier-2 empanelled network hospitals.",
            "rules": [
                {
                    "rule_id": "RULE-POL001-01",
                    "rule_type": "room_rent_limit",
                    "clause_reference": "Section 3.1.A",
                    "condition": "Room rent is capped at 1% of Sum Insured (₹5,000/day). If higher category selected, proportionate tariff deduction applies.",
                    "expected_interpretation": "proportionate_deduction",
                },
                {
                    "rule_id": "RULE-POL001-02",
                    "rule_type": "sub_limit_cataract",
                    "clause_reference": "Schedule B, Item 1",
                    "condition": "Cataract surgery payable up to ₹40,000 per eye.",
                    "expected_interpretation": "capped_at_sublimit",
                },
                {
                    "rule_id": "RULE-POL001-03",
                    "rule_type": "specific_disease_waiting_period",
                    "clause_reference": "Section 2.2",
                    "condition": "24-month waiting period for listed surgeries (Hernia, Cataract, Cholelithiasis, Joint Replacement).",
                    "expected_interpretation": "deny_if_tenure_under_24m",
                },
                {
                    "rule_id": "RULE-POL001-04",
                    "rule_type": "ped_waiting_period",
                    "clause_reference": "Section 2.3",
                    "condition": "Pre-existing diseases covered only after 36 months of continuous coverage.",
                    "expected_interpretation": "deny_if_ped_under_36m",
                },
            ],
        },

        # 2. POL-002: Family Floater Comprehensive
        {
            "policy_id": "POL-002",
            "policy_version": "1.0",
            "policy_name": "Vanguard Family Floater Health Security",
            "insurer_name": "Vanguard Health Insurance Ltd.",
            "policy_type": PlanType.FAMILY_FLOATER.value,
            "product_uin": "VANG-HLT-FF-2024-V02",
            "product_version": "2024.1",
            "policyholder_eligibility": {
                "min_entry_age": 18,
                "max_entry_age": 65,
                "dependent_child_age_limit": 25,
                "renewable_for_life": True,
            },
            "policy_start_date": "2023-06-01",
            "policy_expiry_date": "2024-05-31",
            "sum_insured": {"amount": "1000000.00", "currency": "INR"},
            "available_sum_insured": {"amount": "1000000.00", "currency": "INR"},
            "room_rent_limits": {
                "type": "category_based",
                "allowed_category": "Single Private A/C Room",
                "daily_cap_inr": None,
                "clause_reference": "Section 3.2",
                "proportional_deduction_applies": False,
            },
            "icu_limits": {
                "type": "actuals",
                "daily_cap_inr": None,
                "clause_reference": "Section 3.3",
            },
            "disease_sublimits": {
                "Cataract": {"cap_inr": "50000.00", "per": "per_eye", "clause": "Clause 5.1"},
                "Joint Replacement": {"cap_inr": "250000.00", "per": "per_joint", "clause": "Clause 5.2"},
            },
            "waiting_periods": {
                "initial_days": 30,
                "initial_accident_exempt": True,
                "specific_disease_months": 24,
                "ped_months": 36,
                "statutory_moratorium_months": 60,
            },
            "co_payment": {
                "mandatory_pct": "0.00",
                "senior_citizen_pct": "0.00",
                "clause": "Section 4.0",
            },
            "deductible": {"amount": "0.00", "currency": "INR", "type": "none"},
            "restoration_benefit": {"is_available": True, "percentage": 100.0, "unrelated_illness_only": False},
            "exclusions": {
                "permanent": ["Cosmetic surgery", "Stem cell therapy", "Rest cure / recuperation"],
                "conditional": ["Maternity covered up to ₹50,000 after 24 months continuous coverage"],
            },
            "network_hospital_conditions": "Cashless at all registered cashless hospitals nationwide.",
            "rules": [
                {
                    "rule_id": "RULE-POL002-01",
                    "rule_type": "room_rent_category",
                    "clause_reference": "Section 3.2",
                    "condition": "Eligible for Single Private A/C room with no proportional deduction.",
                    "expected_interpretation": "full_coverage_single_private",
                },
                {
                    "rule_id": "RULE-POL002-02",
                    "rule_type": "restoration_benefit",
                    "clause_reference": "Section 6.1",
                    "condition": "100% instant recharge of sum insured upon complete or partial exhaustion.",
                    "expected_interpretation": "reinstate_sum_insured",
                },
            ],
        },

        # 3. POL-003: Senior Citizen Specialized Plan
        {
            "policy_id": "POL-003",
            "policy_version": "1.0",
            "policy_name": "Paramount Senior Citizen Silver Care",
            "insurer_name": "Paramount Assurance Co.",
            "policy_type": PlanType.INDIVIDUAL.value,
            "product_uin": "PARA-HLT-SNR-2024-V01",
            "product_version": "2024.1",
            "policyholder_eligibility": {
                "min_entry_age": 60,
                "max_entry_age": 85,
                "renewable_for_life": True,
            },
            "policy_start_date": "2023-01-01",
            "policy_expiry_date": "2023-12-31",
            "sum_insured": {"amount": "300000.00", "currency": "INR"},
            "available_sum_insured": {"amount": "300000.00", "currency": "INR"},
            "room_rent_limits": {
                "type": "fixed_daily_amount",
                "daily_cap_inr": "3000.00",
                "clause_reference": "Section 2.1",
                "proportional_deduction_applies": True,
            },
            "icu_limits": {
                "type": "fixed_daily_amount",
                "daily_cap_inr": "6000.00",
                "clause_reference": "Section 2.2",
            },
            "disease_sublimits": {
                "Cataract": {"cap_inr": "25000.00", "per": "per_eye", "clause": "Section 4.1"},
                "Cardiac Stent Surgery": {"cap_inr": "120000.00", "per": "per_admission", "clause": "Section 4.2"},
                "Knee Replacement": {"cap_inr": "100000.00", "per": "per_knee", "clause": "Section 4.3"},
                "Cancer Chemotherapy": {"cap_inr": "80000.00", "per": "per_cycle", "clause": "Section 4.4"},
            },
            "waiting_periods": {
                "initial_days": 30,
                "initial_accident_exempt": True,
                "specific_disease_months": 12,
                "ped_months": 24,
                "statutory_moratorium_months": 60,
            },
            "co_payment": {
                "mandatory_pct": "20.00",
                "senior_citizen_pct": "20.00",
                "clause": "Section 5.1",
            },
            "deductible": {"amount": "0.00", "currency": "INR", "type": "none"},
            "restoration_benefit": {"is_available": False},
            "exclusions": {
                "permanent": ["Cosmetic treatments", "Experimental therapies", "Non-allopathic alternative medicine"],
                "conditional": ["Pre-existing cardiac disease covered after 24m"],
            },
            "network_hospital_conditions": "Network empanelled facilities only for cashless pre-auth.",
            "rules": [
                {
                    "rule_id": "RULE-POL003-01",
                    "rule_type": "mandatory_copay",
                    "clause_reference": "Section 5.1",
                    "condition": "Mandatory 20% co-payment applies on all admissible claims.",
                    "expected_interpretation": "deduct_20pct_copay",
                },
                {
                    "rule_id": "RULE-POL003-02",
                    "rule_type": "ped_reduced_waiting",
                    "clause_reference": "Section 3.2",
                    "condition": "Special 24-month reduced PED waiting period for senior citizens.",
                    "expected_interpretation": "ped_cleared_after_24m",
                },
            ],
        },

        # 4. POL-004: High Sum-Insured Super Top-Up Plan
        {
            "policy_id": "POL-004",
            "policy_version": "1.0",
            "policy_name": "Zenith Super Top-Up Premier",
            "insurer_name": "Zenith General Insurance Ltd.",
            "policy_type": PlanType.INDIVIDUAL.value,
            "product_uin": "ZEN-HLT-TOP-2024-V01",
            "product_version": "2024.1",
            "policyholder_eligibility": {"min_entry_age": 18, "max_entry_age": 70},
            "policy_start_date": "2024-01-01",
            "policy_expiry_date": "2024-12-31",
            "sum_insured": {"amount": "5000000.00", "currency": "INR"},
            "available_sum_insured": {"amount": "5000000.00", "currency": "INR"},
            "room_rent_limits": {"type": "actuals", "daily_cap_inr": None, "proportional_deduction_applies": False},
            "icu_limits": {"type": "actuals", "daily_cap_inr": None},
            "disease_sublimits": {},
            "waiting_periods": {
                "initial_days": 30,
                "initial_accident_exempt": True,
                "specific_disease_months": 24,
                "ped_months": 36,
                "statutory_moratorium_months": 60,
            },
            "co_payment": {"mandatory_pct": "0.00", "clause": "None"},
            "deductible": {
                "amount": "500000.00",
                "currency": "INR",
                "type": "aggregate_annual_deductible",
                "clause_reference": "Section 1.2",
            },
            "restoration_benefit": {"is_available": False},
            "exclusions": {"permanent": ["Cosmetic treatments", "Experimental therapies"], "conditional": []},
            "network_hospital_conditions": "Nationwide cashless empanelment.",
            "rules": [
                {
                    "rule_id": "RULE-POL004-01",
                    "rule_type": "annual_deductible",
                    "clause_reference": "Section 1.2",
                    "condition": "Claims become payable only once total medical expenses exceed the ₹5,00,000 threshold.",
                    "expected_interpretation": "deduct_500000_threshold",
                },
            ],
        },

        # 5. POL-005: Corporate Group Health Policy with Zero Waiting Period
        {
            "policy_id": "POL-005",
            "policy_version": "1.0",
            "policy_name": "Titan Corporate Group Mediclaim",
            "insurer_name": "Titan Insurance Co. Ltd.",
            "policy_type": PlanType.GROUP.value,
            "product_uin": "TITAN-GRP-MED-2024-V01",
            "product_version": "2024.1",
            "policyholder_eligibility": {"employee_status": "Active Full-time Employee and Dependents"},
            "policy_start_date": "2024-04-01",
            "policy_expiry_date": "2025-03-31",
            "sum_insured": {"amount": "500000.00", "currency": "INR"},
            "available_sum_insured": {"amount": "500000.00", "currency": "INR"},
            "room_rent_limits": {
                "type": "percentage_of_sum_insured",
                "percentage": 1.5,
                "daily_cap_inr": "7500.00",
                "proportional_deduction_applies": True,
                "clause_reference": "Endorsement Schedule A",
            },
            "icu_limits": {"type": "actuals", "daily_cap_inr": None},
            "disease_sublimits": {
                "Maternity Normal": {"cap_inr": "50000.00", "per": "per_delivery", "clause": "Maternity Endorsement"},
                "Maternity Caesarean": {"cap_inr": "75000.00", "per": "per_delivery", "clause": "Maternity Endorsement"},
                "Cataract": {"cap_inr": "40000.00", "per": "per_eye", "clause": "Schedule C"},
            },
            "waiting_periods": {
                "initial_days": 0,
                "initial_accident_exempt": True,
                "specific_disease_months": 0,
                "ped_months": 0,
                "statutory_moratorium_months": 60,
                "waiver_endorsement": "WAITING_PERIOD_WAIVER_ATTACHED",
            },
            "co_payment": {"mandatory_pct": "0.00"},
            "deductible": {"amount": "0.00", "type": "none"},
            "restoration_benefit": {"is_available": True, "percentage": 100.0},
            "exclusions": {"permanent": ["Cosmetic treatments"], "conditional": []},
            "network_hospital_conditions": "Preferred Provider Network (PPN) with Cashless Everywhere endorsement.",
            "rules": [
                {
                    "rule_id": "RULE-POL005-01",
                    "rule_type": "waiting_period_waiver",
                    "clause_reference": "Endorsement W-01",
                    "condition": "All initial, specific disease, and pre-existing disease waiting periods waived from Day 1.",
                    "expected_interpretation": "zero_waiting_period",
                },
                {
                    "rule_id": "RULE-POL005-02",
                    "rule_type": "maternity_benefit",
                    "clause_reference": "Endorsement M-02",
                    "condition": "Maternity covered from Day 1 up to ₹50,000 for normal and ₹75,000 for C-section.",
                    "expected_interpretation": "maternity_covered_with_sublimit",
                },
            ],
        },
    ]

    # Dynamically generate 30 additional policies (POL-006 to POL-035) to reach 35 total
    categories = [
        ("Economy Basic Care", "individual", "200000.00", 1.0, "2000.00", "10.00", 30, 24, 36, {"Cataract": "20000.00", "Hernia": "30000.00"}),
        ("Gold Family Floater", "family_floater", "750000.00", 1.5, "11250.00", "0.00", 30, 24, 36, {"Cataract": "45000.00", "Knee Replacement": "175000.00"}),
        ("Platinum Global Shield", "individual", "2500000.00", None, None, "0.00", 30, 12, 24, {}),
        ("Senior Citizen Vitality", "individual", "400000.00", 1.0, "4000.00", "20.00", 30, 12, 24, {"Cardiac": "150000.00", "Cataract": "30000.00"}),
        ("Corporate Executive Group", "group", "1000000.00", None, None, "0.00", 0, 0, 0, {"Maternity": "80000.00"}),
        ("Diabetes & Hypertension Care", "individual", "500000.00", 1.0, "5000.00", "15.00", 30, 12, 12, {"Dialysis": "50000.00"}),
        ("Cardiac & Cancer Protect", "individual", "1500000.00", 2.0, "30000.00", "10.00", 30, 24, 24, {"Chemotherapy": "100000.00"}),
        ("Youth Starter Health", "individual", "300000.00", 1.0, "3000.00", "5.00", 30, 24, 36, {"Appendicitis": "40000.00"}),
        ("Women Complete Wellness", "individual", "600000.00", 1.5, "9000.00", "0.00", 30, 24, 36, {"Maternity": "60000.00", "Hysterectomy": "70000.00"}),
        ("Metro Preferred Floater", "family_floater", "1200000.00", None, None, "0.00", 30, 24, 36, {"Joint Replacement": "200000.00"}),
        ("Rural Micro-Insurance", "individual", "100000.00", 1.0, "1000.00", "0.00", 30, 24, 36, {"Cataract": "15000.00"}),
        ("High-Deductible Top-Up 25k", "individual", "1000000.00", None, None, "0.00", 30, 24, 36, {}),
        ("High-Deductible Top-Up 50k", "family_floater", "2000000.00", None, None, "0.00", 30, 24, 36, {}),
        ("Legacy 48-Month PED Plan", "individual", "500000.00", 1.0, "5000.00", "0.00", 30, 24, 48, {"Cataract": "35000.00"}),
        ("Legacy Family Plan 48m", "family_floater", "600000.00", 1.0, "6000.00", "10.00", 30, 24, 48, {"Hernia": "45000.00"}),
        ("Arogya Sanjeevani Standard", "individual", "500000.00", 1.0, "5000.00", "5.00", 30, 24, 36, {"Cataract": "40000.00"}),
        ("Arogya Sanjeevani Floater", "family_floater", "500000.00", 1.0, "5000.00", "5.00", 30, 24, 36, {"Cataract": "40000.00"}),
        ("Day Care Special Plan", "individual", "300000.00", 1.5, "4500.00", "0.00", 30, 12, 36, {"Lithotripsy": "40000.00", "Cataract": "35000.00"}),
        ("Emergency Trauma Shield", "individual", "1000000.00", None, None, "0.00", 0, 0, 36, {}),
        ("Tier-2 City Advantage Plan", "individual", "400000.00", 1.0, "4000.00", "10.00", 30, 24, 36, {"Cataract": "25000.00"}),
        ("Tier-1 Corporate Gold", "group", "750000.00", None, None, "0.00", 0, 0, 0, {"Maternity": "70000.00"}),
        ("Armed Forces Veteran Care", "individual", "800000.00", None, None, "0.00", 0, 0, 12, {}),
        ("Critical Illness Lump-Sum Combo", "individual", "2000000.00", None, None, "0.00", 90, 0, 24, {}),
        ("Joint Replacement Plus", "individual", "500000.00", 1.0, "5000.00", "10.00", 30, 12, 24, {"Knee Replacement": "180000.00", "Hip Replacement": "180000.00"}),
        ("Ophthalmic & ENT Special", "individual", "250000.00", 1.0, "2500.00", "0.00", 30, 12, 24, {"Cataract": "30000.00", "Tympanoplasty": "35000.00"}),
        ("Pediatric & Family Floater", "family_floater", "800000.00", 1.5, "12000.00", "0.00", 30, 24, 36, {"Tonsillectomy": "30000.00"}),
        ("Executive Restoration Shield", "individual", "1500000.00", None, None, "0.00", 30, 24, 36, {}),
        ("Smart Deductible 100k", "individual", "2500000.00", None, None, "0.00", 30, 24, 36, {}),
        ("Portability Guaranteed Shield", "individual", "500000.00", 1.0, "5000.00", "0.00", 30, 24, 36, {"Cataract": "40000.00"}),
        ("Cashless Anywhere Elite", "individual", "1000000.00", None, None, "0.00", 30, 24, 36, {}),
    ]

    insurers = [
        "Apex General Insurance Corp.",
        "Vanguard Health Insurance Ltd.",
        "Paramount Assurance Co.",
        "Zenith General Insurance Ltd.",
        "Titan Insurance Co. Ltd.",
        "Reliant Health Underwriters",
        "National Care Assurance",
        "Metropolitan Health Insurance",
    ]

    for idx, cat in enumerate(categories, start=6):
        name, ptype, si, rr_pct, rr_cap, copay, init_days, spec_m, ped_m, sublimits = cat
        pol_id = f"POL-{idx:03d}"
        insurer = insurers[idx % len(insurers)]
        is_legacy = ped_m == 48

        disease_subs = {}
        for dname, dcap in sublimits.items():
            disease_subs[dname] = {
                "cap_inr": dcap,
                "per": "per_admission",
                "clause": f"Section 4 Sub-Limits Schedule Item ({dname})",
            }

        pol_data = {
            "policy_id": pol_id,
            "policy_version": "1.0",
            "policy_name": f"{insurer.split()[0]} {name}",
            "insurer_name": insurer,
            "policy_type": ptype,
            "product_uin": f"{insurer[:4].upper()}-HLT-{idx:03d}-2024",
            "product_version": "pre_2024.legacy" if is_legacy else "2024.1",
            "policyholder_eligibility": {
                "min_entry_age": 18,
                "max_entry_age": 65 if "Senior" not in name else 80,
                "renewable_for_life": True,
            },
            "policy_start_date": "2024-01-01",
            "policy_expiry_date": "2024-12-31",
            "sum_insured": {"amount": si, "currency": "INR"},
            "available_sum_insured": {"amount": si, "currency": "INR"},
            "room_rent_limits": {
                "type": "percentage_of_sum_insured" if rr_pct else "actuals",
                "percentage": rr_pct,
                "daily_cap_inr": rr_cap,
                "proportional_deduction_applies": bool(rr_pct),
                "clause_reference": "Section 3.1" if rr_pct else "Section 3.0 (No Cap)",
            },
            "icu_limits": {
                "type": "percentage_of_sum_insured" if rr_pct else "actuals",
                "percentage": (rr_pct * 2.0) if rr_pct else None,
                "daily_cap_inr": str(Decimal(rr_cap) * 2) if rr_cap else None,
            },
            "disease_sublimits": disease_subs,
            "waiting_periods": {
                "initial_days": init_days,
                "initial_accident_exempt": True,
                "specific_disease_months": spec_m,
                "ped_months": ped_m,
                "statutory_moratorium_months": 60,
                "waiver_endorsement": "DAY_1_COVERAGE" if init_days == 0 else None,
            },
            "co_payment": {
                "mandatory_pct": copay,
                "clause": f"Section 5.1 ({copay}% Co-Payment)" if Decimal(copay) > 0 else "None",
            },
            "deductible": {
                "amount": "25000.00" if "25k" in name else ("50000.00" if "50k" in name else ("100000.00" if "100k" in name else "0.00")),
                "currency": "INR",
                "type": "annual_aggregate" if "Deductible" in name or "Top-Up" in name else "none",
            },
            "restoration_benefit": {
                "is_available": "Restoration" in name or "Floater" in name or "Shield" in name,
                "percentage": 100.0,
            },
            "exclusions": {
                "permanent": [
                    "Aesthetic, cosmetic or plastic surgery",
                    "Self-inflicted injury or suicide attempts",
                    "Unproven or investigational procedures",
                ],
                "conditional": [
                    "Maternity expenses excluded unless corporate waiver applies",
                ],
            },
            "network_hospital_conditions": "Empanelled Network Hospitals for Cashless Facilities.",
            "rules": [
                {
                    "rule_id": f"RULE-{pol_id}-01",
                    "rule_type": "room_rent_limit" if rr_pct else "room_rent_unlimited",
                    "clause_reference": "Section 3.1",
                    "condition": f"Room rent limit: {rr_cap}/day" if rr_cap else "No room rent sub-limit applicable.",
                    "expected_interpretation": "proportionate_deduction" if rr_cap else "full_coverage",
                },
                {
                    "rule_id": f"RULE-{pol_id}-02",
                    "rule_type": "ped_waiting_period",
                    "clause_reference": "Section 2.3",
                    "condition": f"Pre-existing diseases subject to {ped_m}-month waiting period.",
                    "expected_interpretation": f"deny_if_ped_under_{ped_m}m",
                },
                {
                    "rule_id": f"RULE-{pol_id}-03",
                    "rule_type": "co_payment_check",
                    "clause_reference": "Section 5.1",
                    "condition": f"{copay}% co-payment applies to all eligible expenses." if Decimal(copay) > 0 else "No co-payment applies.",
                    "expected_interpretation": f"deduct_{copay}pct" if Decimal(copay) > 0 else "no_copay",
                },
            ],
        }
        policies.append(pol_data)

    return policies


def save_policies_and_metadata(policies: list[dict[str, Any]], base_dir: Path):
    """Save canonical policy JSONs and generate policy ground truth files."""
    canonical_dir = base_dir / "policies" / "canonical"
    ground_truth_dir = base_dir / "policy_ground_truth"
    canonical_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    rules_list: list[dict[str, Any]] = []
    coverage_matrix: dict[str, Any] = {}
    clause_mapping: dict[str, Any] = {}

    for pol in policies:
        pid = pol["policy_id"]
        # Save individual canonical policy JSON
        with open(canonical_dir / f"{pid}.json", "w", encoding="utf-8") as f:
            json.dump(pol, f, indent=2)

        # Collect rules
        for r in pol.get("rules", []):
            rule_entry = {
                "policy_id": pid,
                "policy_name": pol["policy_name"],
                **r,
            }
            rules_list.append(rule_entry)

        # Build coverage matrix entry
        coverage_matrix[pid] = {
            "policy_name": pol["policy_name"],
            "plan_type": pol["policy_type"],
            "sum_insured_inr": pol["sum_insured"]["amount"],
            "room_rent_cap_inr": pol["room_rent_limits"].get("daily_cap_inr"),
            "proportional_deduction": pol["room_rent_limits"].get("proportional_deduction_applies", False),
            "copay_percentage": pol["co_payment"].get("mandatory_pct", "0.00"),
            "deductible_amount_inr": pol["deductible"].get("amount", "0.00"),
            "initial_wp_days": pol["waiting_periods"].get("initial_days", 30),
            "specific_disease_wp_months": pol["waiting_periods"].get("specific_disease_months", 24),
            "ped_wp_months": pol["waiting_periods"].get("ped_months", 36),
            "restoration_benefit": pol["restoration_benefit"].get("is_available", False),
            "disease_sublimits": pol.get("disease_sublimits", {}),
        }

        # Build clause mapping
        clause_mapping[pid] = {
            "room_rent_clause": pol["room_rent_limits"].get("clause_reference"),
            "copay_clause": pol["co_payment"].get("clause"),
            "waiting_period_clauses": {
                "initial": "Section 2.1 (30-day initial waiting period)",
                "specific_disease": f"Section 2.2 ({pol['waiting_periods'].get('specific_disease_months')} months)",
                "ped": f"Section 2.3 ({pol['waiting_periods'].get('ped_months')} months PED)",
                "moratorium": "Section 2.4 (60-month statutory moratorium)",
            },
            "sublimit_clauses": {k: v.get("clause") for k, v in pol.get("disease_sublimits", {}).items()},
        }

    # Save policy_rules.jsonl
    with open(ground_truth_dir / "policy_rules.jsonl", "w", encoding="utf-8") as f:
        for r in rules_list:
            f.write(json.dumps(r) + "\n")

    # Save coverage_matrix.json
    with open(ground_truth_dir / "coverage_matrix.json", "w", encoding="utf-8") as f:
        json.dump(coverage_matrix, f, indent=2)

    # Save policy_clause_mapping.json
    with open(ground_truth_dir / "policy_clause_mapping.json", "w", encoding="utf-8") as f:
        json.dump(clause_mapping, f, indent=2)

    print(f"Generated {len(policies)} canonical policies in {canonical_dir}")
    print(f"Generated {len(rules_list)} policy rules in {ground_truth_dir / 'policy_rules.jsonl'}")
    print(f"Saved coverage matrix and clause mapping to {ground_truth_dir}")


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    policies = build_synthetic_policies()
    save_policies_and_metadata(policies, base_dir)


if __name__ == "__main__":
    main()
