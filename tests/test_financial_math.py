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


class TestPEDWaitingPeriodAndMoratorium:
    """Verifies compliance with IRDAI (Insurance Products) Regulations, 2024.

    1. Maximum statutory PED waiting period is 36 months (1,095 days), down from 48 months.
    2. Legacy pre-2024 policies retain up to 48 months (1,460 days).
    3. Statutory non-disclosure moratorium is 60 continuous months (1,825 days).
    """

    def _build_ped_request(self, days_since_inception: int, is_legacy: bool = False, wp_months: int = 36):
        from schemas.pre_auth_request import (
            Patient, Policy, Hospital, Diagnosis, Procedure, CostEstimate, CostLineItem,
            Gender, PlanType, NetworkTier, HospitalCategory, AdmissionType, SourceFormat, CostCategory
        )

        pol_num = "POL-LEGACY-01" if is_legacy else "POL-2024-01"
        start_date = "2020-01-01" if is_legacy else "2024-05-01"

        return PreAuthRequest(
            submitted_at="2026-11-15",
            source_format=SourceFormat.JSON,
            patient=Patient(full_name="Kavita Rao", age=52, gender=Gender.FEMALE, policy_number=pol_num),
            policy=Policy(
                policy_number=pol_num,
                plan_type=PlanType.INDIVIDUAL,
                sum_insured=Decimal("500000.00"),
                policy_start_date=start_date,
                waiting_period_months=wp_months,
                co_pay_pct=Decimal("0.00"),
            ),
            hospital=Hospital(
                name="Apollo Speciality Hospital",
                city="Bengaluru",
                network_tier=NetworkTier.CASHLESS_NETWORK,
                category=HospitalCategory.MULTI_SPECIALTY,
            ),
            diagnosis=Diagnosis(
                icd10_code="I25.10",
                description="Atherosclerotic heart disease of native coronary artery (Pre-existing CAD)",
                is_pre_existing=True,
            ),
            procedure=Procedure(
                procedure_code="CPT-92928",
                description="Percutaneous coronary intervention (stent placement)",
                admission_type=AdmissionType.EMERGENCY,
            ),
            cost_estimate=CostEstimate(
                line_items=[
                    CostLineItem(item="Angioplasty Stent Package", amount=Decimal("150000.00"), category=CostCategory.SURGEON_FEE)
                ],
                total_amount=Decimal("150000.00"),
            )
        )

    def test_ped_denied_under_36_month_irdai_2024_rule(self):
        """Pre-existing disease claim under 36-month IRDAI rule is denied at 900 days (< 1095 days)."""
        from rules.waiting_period import check_waiting_period
        from rules.models import DeductionCategory

        req = self._build_ped_request(days_since_inception=900, is_legacy=False, wp_months=36)
        wp_info = WaitingPeriodInfo(
            initial_wp_clear=True,
            specific_disease_wp_clear=True,
            ped_wp_clear=False,
            days_elapsed=900,
            ped_wp_months=36,
            is_legacy_policy=False,
            moratorium_clear=False,
            moratorium_months=60,
        )

        res = check_waiting_period(req, wp_info, [])
        assert res["is_clear"] is False
        assert len(res["deductions"]) == 1
        d = res["deductions"][0]
        assert d.category == DeductionCategory.PED_EXCLUSION
        assert "36-month" in d.explanation
        assert "60-month" in d.explanation

    def test_ped_cleared_under_36_month_irdai_2024_rule(self):
        """Pre-existing disease claim under 36-month IRDAI rule is CLEARED at 1150 days (> 1095 days)."""
        from rules.waiting_period import check_waiting_period

        req = self._build_ped_request(days_since_inception=1150, is_legacy=False, wp_months=36)
        wp_info = WaitingPeriodInfo(
            initial_wp_clear=True,
            specific_disease_wp_clear=True,
            ped_wp_clear=True,
            days_elapsed=1150,
            ped_wp_months=36,
            is_legacy_policy=False,
            moratorium_clear=False,
            moratorium_months=60,
        )

        res = check_waiting_period(req, wp_info, [])
        assert res["is_clear"] is True
        assert len(res["deductions"]) == 0
        assert "36-month" in res["reasoning"]

    def test_legacy_policy_enforces_48_month_ped_waiting_period(self):
        """Legacy pre-2024 policy with 48-month PED is denied at 1200 days (< 1460 days)."""
        from rules.waiting_period import check_waiting_period
        from rules.models import DeductionCategory

        req = self._build_ped_request(days_since_inception=1200, is_legacy=True, wp_months=48)
        wp_info = WaitingPeriodInfo(
            initial_wp_clear=True,
            specific_disease_wp_clear=True,
            ped_wp_clear=False,
            days_elapsed=1200,
            ped_wp_months=48,
            is_legacy_policy=True,
            moratorium_clear=False,
            moratorium_months=60,
        )

        res = check_waiting_period(req, wp_info, [])
        assert res["is_clear"] is False
        assert len(res["deductions"]) == 1
        d = res["deductions"][0]
        assert d.category == DeductionCategory.PED_EXCLUSION
        assert "legacy 48-month" in d.explanation

    def test_moratorium_status_tracking(self):
        """60-month (1,825 days) statutory moratorium status is correctly tracked in reasoning."""
        from rules.waiting_period import check_waiting_period

        # Case A: Moratorium pending (< 1825 days)
        req_pending = self._build_ped_request(days_since_inception=1200, is_legacy=False, wp_months=36)
        wp_pending = WaitingPeriodInfo(
            initial_wp_clear=True,
            specific_disease_wp_clear=True,
            ped_wp_clear=True,
            days_elapsed=1200,
            ped_wp_months=36,
            moratorium_clear=False,
            moratorium_months=60,
        )
        res_pending = check_waiting_period(req_pending, wp_pending, [])
        assert "Statutory Non-Contestability Moratorium: PENDING" in res_pending["reasoning"]
        assert "625 days remaining" in res_pending["reasoning"]

        # Case B: Moratorium reached (>= 1825 days)
        req_reached = self._build_ped_request(days_since_inception=1900, is_legacy=False, wp_months=36)
        wp_reached = WaitingPeriodInfo(
            initial_wp_clear=True,
            specific_disease_wp_clear=True,
            ped_wp_clear=True,
            days_elapsed=1900,
            ped_wp_months=36,
            moratorium_clear=True,
            moratorium_months=60,
        )
        res_reached = check_waiting_period(req_reached, wp_reached, [])
        assert "Statutory Non-Contestability Moratorium: REACHED" in res_reached["reasoning"]
