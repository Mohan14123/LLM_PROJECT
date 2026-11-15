"""
orchestration/mock_api/app.py
-----------------------------
FastAPI application simulating the insurer's core systems.

Provides mock endpoints that the LangGraph agent calls as "tools":
    - Policy Admin System (PAS): policy status, waiting periods, sub-limits
    - Hospital Empanelment: network tier, agreed tariffs

These stubs return synthetic data derived from the pre-auth request fields,
simulating what a real core system would respond with.

Usage:
    # Start the mock server
    uvicorn orchestration.mock_api.app:app --port 8100

    # Or run programmatically in tests
    from orchestration.mock_api.app import app
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "fastapi is required for mock APIs. "
        "Install with: pip install fastapi>=0.110.0 uvicorn>=0.27.0"
    )


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="A1 Pre-Auth Mock Core Systems",
    description=(
        "Mock Policy Admin System (PAS) and Hospital Empanelment APIs "
        "for the Cashless Pre-Authorisation Agent pipeline."
    ),
    version="1.0.0",
)


# ============================================================================
# Response Models
# ============================================================================


class PolicyStatusResponse(BaseModel):
    """Response from the Policy Admin System for policy status lookup."""
    policy_number: str
    status: str  # "ACTIVE", "LAPSED", "EXPIRED"
    is_active: bool
    remaining_sum_insured: str  # Decimal as string
    co_pay_pct: str
    days_since_inception: int


class WaitingPeriodResponse(BaseModel):
    """Response from PAS for waiting period evaluation."""
    policy_number: str
    initial_wp_clear: bool
    specific_disease_wp_clear: bool
    ped_wp_clear: bool
    days_elapsed: int
    applicable_wp_months: int
    continuity_credit_months: int = 0
    moratorium_clear: bool = False
    moratorium_base_clear: bool = False
    moratorium_enhanced_clear: bool = False
    moratorium_months: int = 60
    is_legacy_policy: bool = False
    ped_anniversary_date: Optional[str] = None
    moratorium_base_date: Optional[str] = None
    moratorium_enhanced_date: Optional[str] = None


class SubLimitBalanceResponse(BaseModel):
    """Response from PAS for sub-limit balance lookup."""
    policy_number: str
    limits: dict[str, str]
    consumed: dict[str, str]


class HospitalEmpanelmentResponse(BaseModel):
    """Response from the Hospital Empanelment API."""
    hospital_id: str
    is_empanelled: bool
    tier: str
    agreed_room_rate: str
    tariff_package: str


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/api/policy/{policy_number}/status", response_model=PolicyStatusResponse)
async def get_policy_status(policy_number: str) -> PolicyStatusResponse:
    """Look up policy status from the mock Policy Admin System.

    Mock Logic:
        - Policies starting with "POL-" are ACTIVE by default.
        - Policy numbers containing "LAPSED" return LAPSED status.
        - Policy numbers containing "EXPIRED" return EXPIRED status.
        - Default sum insured: ₹5,00,000 remaining.
    """
    status = "ACTIVE"
    is_active = True

    if "LAPSED" in policy_number.upper():
        status = "LAPSED"
        is_active = False
    elif "EXPIRED" in policy_number.upper():
        status = "EXPIRED"
        is_active = False

    return PolicyStatusResponse(
        policy_number=policy_number,
        status=status,
        is_active=is_active,
        remaining_sum_insured="500000.00",
        co_pay_pct="0.00",
        days_since_inception=365,
    )


@app.get("/api/policy/{policy_number}/waiting-period", response_model=WaitingPeriodResponse)
async def get_waiting_period(
    policy_number: str,
    days_since_inception: int = 365,
    continuity_credit_months: int = 0,
    policy_start_date: Optional[str] = None,
    admission_date: Optional[str] = None,
    enhancement_date: Optional[str] = None,
    ped_waiting_period_months: Optional[int] = None,
    is_group_policy: bool = False,
    claim_amount: float = 0.0,
    base_sum_insured: float = 500000.0,
) -> WaitingPeriodResponse:
    """Evaluate waiting period and moratorium status for a policy using continuous calendar arithmetic.

    Logic per IRDAI (Insurance Products) Regulations, 2024 (Schedule III):
        - Initial 30-day WP: clear if days >= 30 (waived for group corporate policies).
        - Specific disease 2-year WP: clear on 24-calendar-month anniversary.
        - PED WP: clear on statutory 36-calendar-month anniversary (48 months for legacy pre-2024 policies).
        - Continuity Credits: Portability / migration credits reduce the effective elapsed period.
        - Statutory Moratorium: 60 continuous calendar months against non-disclosure / misrepresentation,
          tracked separately for base sum insured and subsequent sum-insured enhancement.
    """
    is_legacy = "LEGACY" in policy_number.upper() or ped_waiting_period_months == 48

    # Determine reference and start dates
    today = date.today()
    if policy_start_date:
        try:
            start_dt = date.fromisoformat(policy_start_date)
        except ValueError:
            start_dt = today - timedelta(days=days_since_inception)
    else:
        start_dt = today - timedelta(days=days_since_inception)

    if admission_date:
        try:
            ref_dt = date.fromisoformat(admission_date)
        except ValueError:
            ref_dt = today
    else:
        ref_dt = today

    # Effective start after continuity credit
    effective_start = start_dt - relativedelta(months=continuity_credit_months)
    effective_days = max((ref_dt - effective_start).days, 0)

    # 1. Initial 30-day WP
    initial_clear = ref_dt >= (effective_start + timedelta(days=30))

    # 2. Specific disease 24-month WP
    spec_anniversary = effective_start + relativedelta(months=24)
    specific_clear = ref_dt >= spec_anniversary

    # 3. PED WP (36 vs 48 calendar months)
    ped_wp_months = ped_waiting_period_months if ped_waiting_period_months is not None else (48 if is_legacy else 36)
    ped_anniversary = effective_start + relativedelta(months=ped_wp_months)
    ped_clear = ref_dt >= ped_anniversary

    # 4. Moratorium (60 calendar months split by base and enhanced)
    base_moratorium_dt = effective_start + relativedelta(months=60)
    moratorium_base_clear = ref_dt >= base_moratorium_dt

    if enhancement_date:
        try:
            enh_dt = date.fromisoformat(enhancement_date)
            enhanced_moratorium_dt = enh_dt + relativedelta(months=60)
            moratorium_enhanced_clear = ref_dt >= enhanced_moratorium_dt
            enhanced_dt_str = enhanced_moratorium_dt.isoformat()
        except ValueError:
            enhanced_moratorium_dt = None
            moratorium_enhanced_clear = moratorium_base_clear
            enhanced_dt_str = None
    else:
        enhanced_dt_str = None
        moratorium_enhanced_clear = moratorium_base_clear

    if claim_amount <= base_sum_insured:
        moratorium_clear = moratorium_base_clear
    else:
        moratorium_clear = bool(moratorium_base_clear and moratorium_enhanced_clear)

    return WaitingPeriodResponse(
        policy_number=policy_number,
        initial_wp_clear=initial_clear,
        specific_disease_wp_clear=specific_clear,
        ped_wp_clear=ped_clear,
        days_elapsed=effective_days,
        applicable_wp_months=ped_wp_months,
        continuity_credit_months=continuity_credit_months,
        moratorium_clear=moratorium_clear,
        moratorium_base_clear=moratorium_base_clear,
        moratorium_enhanced_clear=moratorium_enhanced_clear,
        moratorium_months=60,
        is_legacy_policy=is_legacy,
        ped_anniversary_date=ped_anniversary.isoformat(),
        moratorium_base_date=base_moratorium_dt.isoformat(),
        moratorium_enhanced_date=enhanced_dt_str,
    )


@app.get("/api/policy/{policy_number}/sub-limit-balance", response_model=SubLimitBalanceResponse)
async def get_sub_limit_balance(policy_number: str) -> SubLimitBalanceResponse:
    """Look up sub-limit balances for a policy.

    Mock Logic:
        Returns default sub-limits with zero consumed.
    """
    return SubLimitBalanceResponse(
        policy_number=policy_number,
        limits={
            "room_rent_per_day": "5000.00",
            "icu_per_day": "10000.00",
            "ambulance": "2000.00",
        },
        consumed={
            "room_rent_per_day": "0.00",
            "icu_per_day": "0.00",
            "ambulance": "0.00",
        },
    )


@app.get("/api/hospital/{hospital_id}/empanelment", response_model=HospitalEmpanelmentResponse)
async def get_hospital_empanelment(hospital_id: str) -> HospitalEmpanelmentResponse:
    """Look up hospital empanelment status.

    Mock Logic:
        - All hospitals are empanelled by default.
        - Hospital IDs containing "NON" return non-network status.
    """
    is_empanelled = "NON" not in hospital_id.upper()
    tier = "cashless_network" if is_empanelled else "non_network"

    return HospitalEmpanelmentResponse(
        hospital_id=hospital_id,
        is_empanelled=is_empanelled,
        tier=tier,
        agreed_room_rate="5000.00",
        tariff_package="standard_metro",
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-core-systems"}
