"""
rules/waiting_period.py
-----------------------
Rule module: Waiting period and statutory moratorium checks.

Evaluates whether the claim falls within any applicable waiting period:
    1. 30-day initial waiting period (from policy inception).
    2. 2-year specific disease waiting period (cataract, hernia, etc.).
    3. Pre-existing disease (PED) waiting period:
       - Current IRDAI (Insurance Products) Regulations, 2024: Maximum 36 months (3 years / 1,095 days).
       - Legacy policies (pre-2024): 48 months (4 years / 1,460 days).
    4. Statutory Moratorium Period tracking:
       - IRDAI 2024: 60 continuous months (5 years / 1,825 days) for non-contestability on grounds
         of non-disclosure/misrepresentation, distinct from the PED waiting period.

Mandatory adversarial case: Claim inside a waiting period (Metrics.md).

Usage:
    from rules.waiting_period import check_waiting_period
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from rules.models import Deduction, DeductionCategory, WaitingPeriodInfo

if TYPE_CHECKING:
    from schemas import PreAuthRequest
    from retrieval.vector_store import RetrievedClause

logger = logging.getLogger(__name__)

# ICD-10 codes subject to the 2-year specific disease waiting period.
# These are diseases that insurers commonly place under specific waiting
# periods per IRDAI guidelines.
SPECIFIC_DISEASE_ICD10_PREFIXES = {
    "H25", "H26",  # Cataract
    "K40", "K41", "K42", "K43", "K44", "K45", "K46",  # Hernia
    "N40",  # Benign prostatic hypertrophy
    "K80",  # Gallstones / Cholelithiasis
    "H40",  # Glaucoma
    "M17",  # Gonarthrosis (knee)
    "I84",  # Haemorrhoids
    "J34",  # Nasal septum deviation / Sinusitis
    "N20", "N21",  # Urolithiasis (kidney/ureter stones)
}


def check_waiting_period(
    request: "PreAuthRequest",
    waiting_period: WaitingPeriodInfo,
    clauses: list["RetrievedClause"],
) -> dict:
    """Check if the claim falls within any applicable waiting period.

    Sequential checks:
        1. Initial 30-day waiting period — applies to all claims.
        2. Specific disease 2-year waiting period — applies to listed conditions.
        3. PED 4-year waiting period — applies if diagnosis is flagged pre-existing.

    Args:
        request: The PreAuthRequest to evaluate.
        waiting_period: Waiting period info from the mock API.
        clauses: Retrieved clauses for citation.

    Returns:
        Dict with:
        - "deductions": list[Deduction]
        - "reasoning": str
        - "is_clear": bool — True if all waiting periods have elapsed
    """
    deductions: list[Deduction] = []
    reasoning_parts: list[str] = []
    endorsement_applied = False
    endorsement_citation = ""

    # Check if this policy has an active corporate / specific endorsement waiver.
    # An endorsement document in the general corpus only applies to policies that
    # qualify (e.g., Corporate Group policies or explicitly endorsed policy numbers/schedules).
    policy_num = getattr(request.policy, "policy_number", "") if hasattr(request, "policy") else ""
    plan_type = getattr(request.policy, "plan_type", None) if hasattr(request, "policy") else None
    plan_type_val = plan_type.value if hasattr(plan_type, "value") else str(plan_type or "")
    diag_desc = getattr(request.diagnosis, "description", "").lower() if hasattr(request, "diagnosis") else ""

    is_endorsed_policy = (
        "endors" in policy_num.lower()
        or "end-" in policy_num.lower()
        or "endorsement" in diag_desc
        or "waiver" in policy_num.lower()
    )
    endorsement_clause = _find_endorsement_waiver(clauses) if is_endorsed_policy else None

    # --- Check 1: Initial 30-day waiting period ---
    # Applies to all illness claims; standard corporate endorsements waive specific disease/PED,
    # not the statutory 30-day window from inception.
    if not waiting_period.initial_wp_clear:
        reasoning_parts.append(
            f"Initial 30-day waiting period NOT elapsed. "
            f"Days since inception: {waiting_period.days_elapsed}. "
            "Claim is within the initial waiting period."
        )

        citation = _find_wp_clause(clauses, "initial waiting period", "30 day")

        deductions.append(
            Deduction(
                category=DeductionCategory.WAITING_PERIOD,
                original_amount=request.cost_estimate.total_amount,
                allowed_amount=Decimal("0"),
                deducted_amount=request.cost_estimate.total_amount,
                clause_citation=citation,
                source_document=_find_wp_source(clauses, "initial waiting period"),
                explanation=(
                    f"Claim is within the initial 30-day waiting period. "
                    f"Only {waiting_period.days_elapsed} days have elapsed "
                    "since policy inception."
                ),
            )
        )

        return {
            "deductions": deductions,
            "reasoning": "\n".join(reasoning_parts),
            "is_clear": False,
        }

    reasoning_parts.append(
        f"Initial 30-day waiting period: CLEAR ({waiting_period.days_elapsed} days elapsed)."
    )

    # --- Check 2: Specific disease 2-year waiting period ---
    icd_code = request.diagnosis.icd10_code or ""
    icd_prefix = icd_code.split(".")[0] if icd_code else ""

    is_specific_disease = icd_prefix in SPECIFIC_DISEASE_ICD10_PREFIXES

    if is_specific_disease and not waiting_period.specific_disease_wp_clear:
        if endorsement_clause:
            endorsement_applied = True
            endorsement_citation = getattr(endorsement_clause, "chunk_text", "")[:300]
            reasoning_parts.append(
                "ENDORSEMENT REVERSAL APPLIED: Specific disease 2-year waiting period "
                "is waived by active policy endorsement, superseding base policy exclusions."
            )
        else:
            reasoning_parts.append(
                f"Diagnosis {icd_code} ({request.diagnosis.description}) is on the "
                "specific disease list. 2-year waiting period NOT elapsed."
            )

            citation = _find_wp_clause(clauses, "specific disease", "2 year", "24 month")

            deductions.append(
                Deduction(
                    category=DeductionCategory.WAITING_PERIOD,
                    original_amount=request.cost_estimate.total_amount,
                    allowed_amount=Decimal("0"),
                    deducted_amount=request.cost_estimate.total_amount,
                    clause_citation=citation,
                    source_document=_find_wp_source(clauses, "specific disease"),
                    explanation=(
                        f"Diagnosis '{request.diagnosis.description}' (ICD-10: {icd_code}) "
                        "is subject to a 2-year specific disease waiting period which "
                        "has not yet elapsed."
                    ),
                )
            )

            return {
                "deductions": deductions,
                "reasoning": "\n".join(reasoning_parts),
                "is_clear": False,
            }

    if is_specific_disease and not endorsement_applied:
        reasoning_parts.append(
            f"Specific disease ({icd_code}) 2-year waiting period: CLEAR."
        )

    # --- Check 3: Pre-existing disease (PED) waiting period ---
    # Current IRDAI 2024 regulations enforce a maximum 36-month (3-year) waiting period.
    # Legacy policies may specify 48 months (4 years).
    ped_wp_months = getattr(waiting_period, "ped_wp_months", 36) or 36
    is_legacy = getattr(waiting_period, "is_legacy_policy", False)
    ped_type_label = f"legacy {ped_wp_months}-month" if is_legacy else f"IRDAI 2024 {ped_wp_months}-month (3-year)"

    if request.diagnosis.is_pre_existing and not waiting_period.ped_wp_clear:
        if endorsement_clause:
            endorsement_applied = True
            endorsement_citation = getattr(endorsement_clause, "chunk_text", "")[:300]
            reasoning_parts.append(
                f"ENDORSEMENT REVERSAL APPLIED: Pre-Existing Disease (PED) {ped_wp_months}-month waiting period "
                "is waived by active policy endorsement, superseding base policy exclusions."
            )
        else:
            reasoning_parts.append(
                f"Diagnosis flagged as pre-existing. {ped_type_label} PED waiting period NOT elapsed "
                f"({waiting_period.days_elapsed} days elapsed)."
            )

            citation = _find_wp_clause(
                clauses,
                f"{ped_wp_months} month",
                "36 month",
                "3 year",
                "pre-existing",
                "48 month",
                "4 year",
                "PED",
            )

            deductions.append(
                Deduction(
                    category=DeductionCategory.PED_EXCLUSION,
                    original_amount=request.cost_estimate.total_amount,
                    allowed_amount=Decimal("0"),
                    deducted_amount=request.cost_estimate.total_amount,
                    clause_citation=citation,
                    source_document=_find_wp_source(clauses, "pre-existing", f"{ped_wp_months} month", "36 month"),
                    explanation=(
                        f"Diagnosis '{request.diagnosis.description}' is flagged as pre-existing. "
                        f"The applicable {ped_type_label} PED waiting period has not yet elapsed "
                        f"({waiting_period.days_elapsed} days elapsed). "
                        "Note: Pre-existing disease waiting period is distinct from the 60-month statutory moratorium on contestability."
                    ),
                )
            )

            return {
                "deductions": deductions,
                "reasoning": "\n".join(reasoning_parts),
                "is_clear": False,
            }

    if request.diagnosis.is_pre_existing:
        reasoning_parts.append(
            f"Pre-existing disease ({ped_type_label}) waiting period: CLEAR ({waiting_period.days_elapsed} days elapsed)."
        )

    # --- Check 4: Statutory Moratorium Period tracking ---
    # Under IRDAI 2024 regulations, 60 continuous months (1,825 days) grants policy non-contestability
    # on non-disclosure grounds (except established fraud).
    moratorium_clear = getattr(waiting_period, "moratorium_clear", False)
    moratorium_months = getattr(waiting_period, "moratorium_months", 60)
    if moratorium_clear:
        reasoning_parts.append(
            f"Statutory Non-Contestability Moratorium: REACHED ({waiting_period.days_elapsed} days >= 1,825 days / {moratorium_months} months per IRDAI 2024). Policy is incontestable except for established fraud."
        )
    else:
        days_to_moratorium = max(1825 - waiting_period.days_elapsed, 0)
        reasoning_parts.append(
            f"Statutory Non-Contestability Moratorium: PENDING ({waiting_period.days_elapsed}/1,825 days elapsed; {days_to_moratorium} days remaining until 60-month threshold)."
        )

    reasoning_parts.append("All applicable waiting periods: CLEAR.")

    return {
        "deductions": deductions,
        "reasoning": "\n".join(reasoning_parts),
        "is_clear": True,
        "endorsement_applied": endorsement_applied,
        "endorsement_citation": endorsement_citation,
    }


def _find_wp_clause(clauses: list["RetrievedClause"], *keywords: str) -> str:
    """Find the most relevant waiting-period clause."""
    for clause in clauses:
        text_lower = clause.chunk_text.lower()
        if any(kw.lower() in text_lower for kw in keywords):
            return clause.chunk_text[:500]
    if clauses:
        return clauses[0].chunk_text[:500]
    return "Policy terms specify applicable waiting periods from date of inception."


def _find_wp_source(clauses: list["RetrievedClause"], *keywords: str) -> str:
    """Find source document for waiting period clause."""
    for clause in clauses:
        text_lower = clause.chunk_text.lower()
        if any(kw.lower() in text_lower for kw in keywords):
            doc = clause.source_file
            if clause.circular_date:
                doc += f" (dated {clause.circular_date})"
            return doc
    if clauses:
        return clauses[0].source_file
    return "policy_wording_general.txt"


def _find_endorsement_waiver(clauses: list["RetrievedClause"]) -> Optional["RetrievedClause"]:
    """Check if retrieved clauses include an endorsement waiving waiting periods."""
    for clause in clauses:
        text = getattr(clause, "chunk_text", "") or ""
        doc = getattr(clause, "source_document", "") or getattr(clause, "source_file", "") or ""
        text_lower = text.lower()
        doc_lower = doc.lower()
        if ("endorsement" in text_lower or "endorsement" in doc_lower) and (
            "waiv" in text_lower or "waiver" in text_lower or "delete" in text_lower
        ) and ("waiting period" in text_lower or "specific disease" in text_lower or "ped" in text_lower):
            return clause
    return None
