"""
tests/test_parallel_and_portability.py
--------------------------------------
Unit and integration tests for:
1. Parallel Fan-out / Fan-in LangGraph execution (Track 1 & Track 2).
2. Evidence-based Portability and continuous coverage history calculation.
3. Emergency accidental trauma statutory exceptions (Initial 30-day and specific disease waiver).
4. Multi-tranche sequential sum-insured allocation with individual 60-month moratorium clocks.
5. Incomplete / missing policy dates fail-closed security.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import pytest

from schemas.pre_auth_request import (
    PreAuthRequest,
    Patient,
    Policy,
    Hospital,
    Diagnosis,
    Procedure,
    CostEstimate,
    CostLineItem,
    Gender,
    PlanType,
    NetworkTier,
    HospitalCategory,
    AdmissionType,
    SourceFormat,
    CostCategory,
    PortabilityRecord,
    EnhancementEvent,
    SpecificDiseaseWaitingPeriod,
    Endorsement,
)
from orchestration.nodes import call_policy_api, apply_rules_engine, llm_reasoning
from orchestration.graph import run_pipeline


class TestParallelAndPortabilityFeatures:
    def test_emergency_accident_waivers_initial_and_specific_wp(self):
        """Accidental emergency trauma waives initial 30-day and specific disease waiting periods."""
        # Policy is only 10 days old and diagnosis is knee trauma
        req = PreAuthRequest(
            submitted_at=date(2025, 6, 10),
            admission_date=date(2025, 6, 10),
            source_format=SourceFormat.JSON,
            patient=Patient(full_name="Arun Verma", age=30, gender=Gender.MALE, policy_number="POL-ACC-001"),
            policy=Policy(
                policy_number="POL-ACC-001",
                plan_type=PlanType.INDIVIDUAL,
                sum_insured=Decimal("300000.00"),
                policy_start_date=date(2025, 6, 1),  # Only 9 days old
            ),
            hospital=Hospital(
                name="Trauma Care Hospital",
                city="Chennai",
                network_tier=NetworkTier.CASHLESS_NETWORK,
                category=HospitalCategory.MULTI_SPECIALTY,
            ),
            diagnosis=Diagnosis(
                icd10_code="S82.1",
                description="Fracture of upper end of tibia from vehicular accident trauma",
                is_pre_existing=False,
            ),
            procedure=Procedure(
                procedure_code="CPT-27535",
                description="Open reduction internal fixation tibia",
                admission_type=AdmissionType.EMERGENCY,
            ),
            cost_estimate=CostEstimate(
                line_items=[
                    CostLineItem(item="Trauma Surgery", amount=Decimal("65000.00"), category=CostCategory.SURGEON_FEE),
                    CostLineItem(item="Implants", amount=Decimal("25000.00"), category=CostCategory.OTHER),
                ],
                total_amount=Decimal("90000.00"),
            ),
        )

        res = run_pipeline({"is_success": True, "request": req.model_dump()})
        assert res["recommendation"] == "RECOMMEND_AUTHORISE"
        adj = res["adjudication_result"]
        wp_deductions = [d for d in adj.get("deductions", []) if d.get("category") == "waiting_period"]
        assert len(wp_deductions) == 0

    def test_portability_history_continuous_coverage(self):
        """Continuous prior coverage across multiple insurers is accurately credited towards PED."""
        req = PreAuthRequest(
            submitted_at=date(2025, 6, 1),
            admission_date=date(2025, 6, 1),
            source_format=SourceFormat.JSON,
            patient=Patient(full_name="Pooja Rao", age=45, gender=Gender.FEMALE, policy_number="POL-PORT-2025"),
            policy=Policy(
                policy_number="POL-PORT-2025",
                plan_type=PlanType.INDIVIDUAL,
                sum_insured=Decimal("500000.00"),
                policy_start_date=date(2024, 12, 1),  # 6 months with current insurer
                portability_history=[
                    PortabilityRecord(
                        previous_insurer="National Insurance",
                        previous_policy_number="POL-PREV-01",
                        previous_policy_start_date=date(2022, 11, 1),
                        previous_policy_end_date=date(2024, 11, 1),  # 24 months
                        continuity_break_days=10,
                        transferred_sum_insured=Decimal("500000.00"),
                        is_portability_approved=True,
                    )
                ],
            ),
            hospital=Hospital(
                name="Apollo Hospital",
                city="Bengaluru",
                network_tier=NetworkTier.CASHLESS_NETWORK,
                category=HospitalCategory.MULTI_SPECIALTY,
            ),
            diagnosis=Diagnosis(
                icd10_code="E11.9",
                description="Type 2 Diabetes Mellitus with chronic microvascular complication",
                is_pre_existing=True,
            ),
            procedure=Procedure(
                procedure_code="CPT-99223",
                description="Inpatient medical management and stabilization",
                admission_type=AdmissionType.PLANNED,
            ),
            cost_estimate=CostEstimate(
                line_items=[
                    CostLineItem(item="Consultation & Monitoring", amount=Decimal("30000.00"), category=CostCategory.OTHER),
                ],
                total_amount=Decimal("30000.00"),
            ),
        )

        api_out = call_policy_api({"pre_auth_request": req.model_dump()})
        wp_info = api_out["waiting_period_info"]
        # Total continuous coverage = 24 months previous + 6 months current = 30 months
        assert wp_info["continuity_credit_months"] >= 24

    def test_multi_tranche_moratorium_allocation(self):
        """Sequential claim allocation across base SI and enhancement with separate moratoriums."""
        req = PreAuthRequest(
            submitted_at=date(2025, 1, 1),
            admission_date=date(2025, 1, 1),
            source_format=SourceFormat.JSON,
            patient=Patient(full_name="Deepak Joshi", age=50, gender=Gender.MALE, policy_number="POL-TRANCHE-01"),
            policy=Policy(
                policy_number="POL-TRANCHE-01",
                plan_type=PlanType.INDIVIDUAL,
                sum_insured=Decimal("400000.00"),
                policy_start_date=date(2018, 1, 1),  # 7 years old -> moratorium clear
                enhancements=[
                    EnhancementEvent(
                        enhancement_id="ENH-01",
                        enhancement_date=date(2023, 1, 1),  # 2 years old -> moratorium pending
                        additional_sum_insured=Decimal("300000.00"),
                    )
                ],
            ),
            hospital=Hospital(
                name="Fortis Hospital",
                city="Delhi",
                network_tier=NetworkTier.CASHLESS_NETWORK,
                category=HospitalCategory.MULTI_SPECIALTY,
            ),
            diagnosis=Diagnosis(
                icd10_code="I25.1",
                description="Atherosclerotic heart disease",
                is_pre_existing=False,
            ),
            procedure=Procedure(
                procedure_code="CPT-92928",
                description="Percutaneous transcatheter placement of stent",
                admission_type=AdmissionType.PLANNED,
            ),
            cost_estimate=CostEstimate(
                line_items=[
                    CostLineItem(item="Stent Angioplasty", amount=Decimal("500000.00"), category=CostCategory.SURGEON_FEE),
                ],
                total_amount=Decimal("500000.00"),  # ₹5 Lakh > ₹4 Lakh base SI
            ),
        )

        api_out = call_policy_api({"pre_auth_request": req.model_dump()})
        wp_info = api_out["waiting_period_info"]
        tranches = wp_info["tranches"]
        assert len(tranches) == 2
        # Base tranche (₹400,000) is clear
        assert tranches[0]["is_moratorium_clear"] is True
        assert tranches[0]["utilised_amount"] == 400000.0
        # Enhancement tranche (₹100,000 of ₹300,000 utilised) is pending moratorium
        assert tranches[1]["is_moratorium_clear"] is False
        assert tranches[1]["utilised_amount"] == 100000.0
        # Claim touched an uncleared tranche, so overall claim moratorium_clear is False
        assert wp_info["moratorium_clear"] is False

    def test_missing_policy_dates_fails_closed_and_escalates(self):
        """Missing policy start date must fail closed and trigger escalation."""
        bad_req = {
            "policy": {"policy_number": "POL-NODATE-01"},  # missing start date
            "submitted_at": "2025-01-01",
        }
        res = call_policy_api({"pre_auth_request": bad_req})
        assert res["policy_status"]["status"] == "UNVERIFIED_DATES"
        assert res["needs_escalation"] is True
        assert res["waiting_period_info"]["ped_wp_clear"] is False

    def test_parallel_graph_fan_out_execution(self):
        """Verify that LangGraph executes Track 1 and Track 2 in parallel branches and joins state."""
        from orchestration.graph import build_graph
        graph = build_graph()
        edges = [(e.source, e.target) for e in graph.get_graph().edges]
        assert ("call_hospital_api", "apply_rules_engine") in edges
        assert ("call_hospital_api", "llm_reasoning") in edges
        assert ("apply_rules_engine", "join_tracks") in edges
        assert ("llm_reasoning", "join_tracks") in edges

