"""
tests/test_financial_math.py
----------------------------
Unit tests verifying deterministic financial calculation, co-pay application on
admissible amount post sub-limits, and prevention of negative approved amounts.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from schemas import PreAuthRequest
from rules.copay_deductible import apply_copay_deductible
from rules.engine import apply_rules
from rules.models import PolicyStatusInfo, WaitingPeriodInfo


class TestFinancialAdjudicationMath:
    def test_copay_calculated_on_admissible_amount(self):
        """Co-pay must be calculated on the amount remaining after sub-limit deductions."""
        # Simulated claim: Total claimed ₹25,000, but sub-limit caps allowable to ₹2,000.
        # Co-pay 20% should be ₹400 (20% of ₹2,000), NOT ₹5,000 (20% of ₹25,000).
        from schemas.pre_auth_request import (
            Patient, Policy, Hospital, Diagnosis, Procedure, CostEstimate, CostLineItem,
            Gender, PlanType, NetworkTier, HospitalCategory, AdmissionType, SourceFormat, CostCategory
        )

        req = PreAuthRequest(
            submitted_at="2026-11-15",
            source_format=SourceFormat.JSON,
            patient=Patient(full_name="Anil Verma", age=48, gender=Gender.MALE, policy_number="POL-COP-01"),
            policy=Policy(
                policy_number="POL-COP-01",
                plan_type=PlanType.INDIVIDUAL,
                sum_insured=Decimal("500000.00"),
                policy_start_date="2024-01-01",
                co_pay_pct=Decimal("20.00"),
            ),
            hospital=Hospital(
                name="Care Hospital",
                city="Hyderabad",
                network_tier=NetworkTier.CASHLESS_NETWORK,
                category=HospitalCategory.MULTI_SPECIALTY,
            ),
            diagnosis=Diagnosis(
                icd10_code="N18.6",
                description="End stage renal disease on maintenance hemodialysis",
            ),
            procedure=Procedure(
                procedure_code="CPT-90935",
                description="Maintenance hemodialysis session",
                admission_type=AdmissionType.DAY_CARE,
            ),
            cost_estimate=CostEstimate(
                line_items=[
                    CostLineItem(item="Dialysis Procedure", amount=Decimal("25000.00"), category=CostCategory.OTHER)
                ],
                total_amount=Decimal("25000.00"),
            )
        )

        # Admissible amount after sub-limit is ₹2,000
        admissible = Decimal("2000.00")
        res = apply_copay_deductible(req, [], admissible_amount=admissible)

        assert len(res["deductions"]) == 1
        deduction = res["deductions"][0]
        assert deduction.deducted_amount == Decimal("400.00")
        assert deduction.allowed_amount == Decimal("1600.00")

    def test_end_to_end_dialysis_sublimit_and_copay_approval(self):
        """Verify that an end-stage renal disease dialysis claim produces AUTHORISE rather than false DENY."""
        from schemas.pre_auth_request import (
            Patient, Policy, Hospital, Diagnosis, Procedure, CostEstimate, CostLineItem,
            Gender, PlanType, NetworkTier, HospitalCategory, AdmissionType, SourceFormat, CostCategory
        )

        req = PreAuthRequest(
            submitted_at="2026-11-15",
            source_format=SourceFormat.JSON,
            patient=Patient(full_name="Rajiv Nambiar", age=56, gender=Gender.MALE, policy_number="POL-DIAL-02"),
            policy=Policy(
                policy_number="POL-DIAL-02",
                plan_type=PlanType.INDIVIDUAL,
                sum_insured=Decimal("500000.00"),
                policy_start_date="2023-01-01",
                co_pay_pct=Decimal("20.00"),
            ),
            hospital=Hospital(
                name="Apollo Dialysis Center",
                city="Chennai",
                network_tier=NetworkTier.CASHLESS_NETWORK,
                category=HospitalCategory.MULTI_SPECIALTY,
            ),
            diagnosis=Diagnosis(
                icd10_code="N18.6",
                description="End stage renal disease on maintenance hemodialysis",
            ),
            procedure=Procedure(
                procedure_code="CPT-90935",
                description="Maintenance hemodialysis session with vascular access monitoring",
                admission_type=AdmissionType.DAY_CARE,
            ),
            cost_estimate=CostEstimate(
                line_items=[
                    CostLineItem(item="Dialysis Fee", amount=Decimal("21517.00"), category=CostCategory.OTHER)
                ],
                total_amount=Decimal("21517.00"),
            )
        )

        pol_status = PolicyStatusInfo(is_active=True, status="ACTIVE", remaining_sum_insured=Decimal("500000.00"), days_since_inception=1000)
        wp_info = WaitingPeriodInfo(initial_wp_clear=True, specific_disease_wp_clear=True, ped_wp_clear=True, days_elapsed=1000)

        result = apply_rules(req, [], pol_status, wp_info)

        # Must recommend AUTHORISE with ₹1,600 approved, NOT false DENY!
        assert result.recommendation.value == "RECOMMEND_AUTHORISE"
        assert result.total_approved == Decimal("1600.00")
        assert result.total_claimed == Decimal("21517.00")
        assert result.total_deducted == Decimal("19917.00")
