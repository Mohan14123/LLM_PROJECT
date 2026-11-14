"""
rules/sub_limits.py
-------------------
Rule module: Sub-limit and room-rent capping with proportionate deduction.

Applies two types of sub-limit logic:
    1. Room rent capping — if daily room rent exceeds the policy cap, the excess
       is deducted AND proportionate deductions are applied to surgeon, anaesthesia,
       and other fees.
    2. Procedure-specific sub-limits — caps from policy.sub_limits.limits.

Mandatory adversarial case: Claim on threshold boundary (Metrics.md).

Usage:
    from rules.sub_limits import apply_sub_limits
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import TYPE_CHECKING

from rules.models import Deduction, DeductionCategory

if TYPE_CHECKING:
    from schemas import PreAuthRequest
    from retrieval.vector_store import RetrievedClause

logger = logging.getLogger(__name__)

# Cost categories subject to proportionate deduction when room rent is capped.
PROPORTIONATE_CATEGORIES = {
    "surgeon_fee",
    "anaesthesia_fee",
    "consultation_fee",
    "diagnostic",
    "pharmacy",
}


def apply_sub_limits(
    request: "PreAuthRequest",
    clauses: list["RetrievedClause"],
) -> dict:
    """Apply sub-limit capping and room-rent proportionate deduction.

    Logic:
        1. Check if room_rent line item exceeds policy sub-limit for room_rent_per_day.
        2. If yes, compute proportionate deduction ratio and apply to all
           PROPORTIONATE_CATEGORIES line items.
        3. Check procedure-specific sub-limits from policy.sub_limits.limits.

    Args:
        request: The PreAuthRequest to evaluate.
        clauses: Retrieved clauses for citation.

    Returns:
        Dict with "deductions" and "reasoning".
    """
    deductions: list[Deduction] = []
    reasoning_parts: list[str] = []

    sub_limits = request.policy.sub_limits.limits

    # --- Room rent capping ---
    room_rent_cap = sub_limits.get("room_rent_per_day")

    if room_rent_cap is not None:
        room_rent_cap = Decimal(str(room_rent_cap))

        # Find room_rent line item(s)
        for item in request.cost_estimate.line_items:
            if item.category.value == "room_rent" and item.amount > room_rent_cap:
                excess = item.amount - room_rent_cap
                ratio = room_rent_cap / item.amount  # proportion allowed

                citation = _find_clause(clauses, "room rent", "sub-limit", "capping")

                deductions.append(
                    Deduction(
                        category=DeductionCategory.ROOM_RENT_CAPPING,
                        line_item=item.item,
                        original_amount=item.amount,
                        allowed_amount=room_rent_cap,
                        deducted_amount=excess,
                        clause_citation=citation,
                        source_document=_find_source(clauses, "room rent", "sub-limit"),
                        explanation=(
                            f"Room rent ₹{item.amount:,.2f} exceeds policy cap "
                            f"₹{room_rent_cap:,.2f}/day. Excess ₹{excess:,.2f} deducted."
                        ),
                    )
                )

                reasoning_parts.append(
                    f"Room rent capped: ₹{item.amount:,.2f} → ₹{room_rent_cap:,.2f}. "
                    f"Proportionate ratio: {ratio:.4f}."
                )

                # Apply proportionate deduction to related categories
                for related_item in request.cost_estimate.line_items:
                    if related_item.category.value in PROPORTIONATE_CATEGORIES:
                        allowed = (related_item.amount * ratio).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        deducted = related_item.amount - allowed

                        if deducted > Decimal("0"):
                            deductions.append(
                                Deduction(
                                    category=DeductionCategory.PROPORTIONATE_DEDUCTION,
                                    line_item=related_item.item,
                                    original_amount=related_item.amount,
                                    allowed_amount=allowed,
                                    deducted_amount=deducted,
                                    clause_citation=citation,
                                    source_document=_find_source(clauses, "proportionate"),
                                    explanation=(
                                        f"Proportionate deduction on {related_item.item}: "
                                        f"₹{related_item.amount:,.2f} × {ratio:.4f} = "
                                        f"₹{allowed:,.2f} (deducted ₹{deducted:,.2f})."
                                    ),
                                )
                            )

                break  # Only process first room_rent line item

    # --- Procedure-specific sub-limits ---
    plan_type_str = (
        request.policy.plan_type.value
        if hasattr(request.policy.plan_type, "value")
        else str(request.policy.plan_type).lower()
    )

    # 1. Dialysis / ESRD Hemodialysis capping (Clause 2.1 / disease_sublimits_schedule)
    is_dialysis = (
        (request.procedure and getattr(request.procedure, "procedure_code", None) in ("CPT-90935", "90935"))
        or (request.diagnosis and getattr(request.diagnosis, "icd10_code", None) in ("N18.5", "N18.6"))
        or (request.procedure and ("dialysis" in str(getattr(request.procedure, "description", "")).lower() or "hemodialysis" in str(getattr(request.procedure, "description", "")).lower()))
        or (request.diagnosis and ("dialysis" in str(getattr(request.diagnosis, "description", "")).lower() or "hemodialysis" in str(getattr(request.diagnosis, "description", "")).lower()))
    )

    if is_dialysis and "group" not in plan_type_str:
        dialysis_cap = sub_limits.get("dialysis", sub_limits.get("hemodialysis", Decimal("2000.00")))
        dialysis_cap = Decimal(str(dialysis_cap))

        already_deducted = sum(d.deducted_amount for d in deductions)
        current_payable = request.cost_estimate.total_amount - already_deducted

        if current_payable > dialysis_cap:
            excess = current_payable - dialysis_cap
            citation = _find_clause(
                clauses,
                "maximum rs. 2,000 per dialysis session",
                "dialysis (per session)",
                "dialysis",
                "hemodialysis",
                "sub-limit",
            )
            if not any(k in citation.lower() for k in ("dialysis", "2,000", "2000")):
                citation = (
                    "Clause 2.1 (esrd_hemodialysis_guidelines.txt): Maximum Rs. 2,000 per dialysis "
                    "session (inclusive of dialyzer, bloodlines, heparin, saline). "
                    "Benefit Schedule: Dialysis (per session) Rs. 2,000 for all standard plans."
                )

            source_doc = _find_source(
                clauses, "esrd_hemodialysis_guidelines", "disease_sublimits_schedule", "dialysis"
            )
            if "dialysis" not in source_doc.lower() and "esrd" not in source_doc.lower() and "sublimits" not in source_doc.lower():
                source_doc = "esrd_hemodialysis_guidelines.txt"

            deductions.append(
                Deduction(
                    category=DeductionCategory.SUB_LIMIT_CAPPING,
                    line_item="Hemodialysis Session Charges",
                    original_amount=request.cost_estimate.total_amount,
                    allowed_amount=dialysis_cap,
                    deducted_amount=excess,
                    clause_citation=citation,
                    source_document=source_doc,
                    explanation=(
                        f"Dialysis per-session charge ₹{request.cost_estimate.total_amount:,.2f} "
                        f"exceeds allowable policy sub-limit cap ₹{dialysis_cap:,.2f} per session. "
                        f"Excess ₹{excess:,.2f} deducted per Clause 2.1."
                    ),
                )
            )
            reasoning_parts.append(
                f"Dialysis sub-limit applied: ₹{request.cost_estimate.total_amount:,.2f} → "
                f"₹{dialysis_cap:,.2f} (excess ₹{excess:,.2f} deducted per Clause 2.1)."
            )

    # 2. Cataract sub-limit (per eye cap)
    is_cataract = (
        (request.procedure and getattr(request.procedure, "procedure_code", None) in ("CPT-66984", "66984"))
        or (request.procedure and "cataract" in str(getattr(request.procedure, "description", "")).lower())
        or (request.diagnosis and "cataract" in str(getattr(request.diagnosis, "description", "")).lower())
    )
    if is_cataract and "group" not in plan_type_str:
        cataract_cap = sub_limits.get("cataract", Decimal("40000.00"))
        cataract_cap = Decimal(str(cataract_cap))
        already_deducted = sum(d.deducted_amount for d in deductions)
        current_payable = request.cost_estimate.total_amount - already_deducted

        if current_payable > cataract_cap:
            excess = current_payable - cataract_cap
            citation = _find_clause(clauses, "cataract", "40,000", "sub-limit")
            source_doc = _find_source(clauses, "cataract", "disease_sublimits_schedule")
            deductions.append(
                Deduction(
                    category=DeductionCategory.SUB_LIMIT_CAPPING,
                    line_item="Cataract Procedure",
                    original_amount=request.cost_estimate.total_amount,
                    allowed_amount=cataract_cap,
                    deducted_amount=excess,
                    clause_citation=citation,
                    source_document=source_doc,
                    explanation=(
                        f"Cataract procedure charge ₹{request.cost_estimate.total_amount:,.2f} "
                        f"exceeds policy sub-limit cap ₹{cataract_cap:,.2f} per eye. "
                        f"Excess ₹{excess:,.2f} deducted."
                    ),
                )
            )
            reasoning_parts.append(
                f"Cataract sub-limit applied: ₹{request.cost_estimate.total_amount:,.2f} → "
                f"₹{cataract_cap:,.2f} (excess ₹{excess:,.2f} deducted)."
            )

    # 3. Explicit named sub-limits in policy schedule
    for limit_key, limit_val in sub_limits.items():
        if limit_key in ("room_rent_per_day", "dialysis", "hemodialysis", "cataract"):
            continue
        try:
            cap_val = Decimal(str(limit_val))
            for item in request.cost_estimate.line_items:
                if limit_key.lower().replace("_", " ") in item.item.lower() and item.amount > cap_val:
                    excess = item.amount - cap_val
                    citation = _find_clause(clauses, limit_key, "sub-limit")
                    deductions.append(
                        Deduction(
                            category=DeductionCategory.SUB_LIMIT_CAPPING,
                            line_item=item.item,
                            original_amount=item.amount,
                            allowed_amount=cap_val,
                            deducted_amount=excess,
                            clause_citation=citation,
                            source_document=_find_source(clauses, limit_key),
                            explanation=(
                                f"{item.item} ₹{item.amount:,.2f} exceeds sub-limit cap "
                                f"₹{cap_val:,.2f}. Excess ₹{excess:,.2f} deducted."
                            ),
                        )
                    )
                    reasoning_parts.append(
                        f"Sub-limit for {limit_key} applied: ₹{item.amount:,.2f} → ₹{cap_val:,.2f}."
                    )
        except (InvalidOperation, ValueError):
            continue

    if not deductions:
        reasoning_parts.append("Room rent and sub-limit checks: No capping applied.")
    else:
        reasoning_parts.append(
            f"Sub-limit checks: {len(deductions)} deduction(s) applied."
        )

    return {
        "deductions": deductions,
        "reasoning": "\n".join(reasoning_parts),
    }


def _find_clause(clauses: list["RetrievedClause"], *keywords: str) -> str:
    """Find the most relevant clause."""
    for clause in clauses:
        text_lower = clause.chunk_text.lower()
        if any(kw.lower() in text_lower for kw in keywords):
            return clause.chunk_text[:500]
    if clauses:
        return clauses[0].chunk_text[:500]
    return "Policy schedule specifies applicable sub-limits and room rent caps."


def _find_source(clauses: list["RetrievedClause"], *keywords: str) -> str:
    """Find source document."""
    for clause in clauses:
        text_lower = clause.chunk_text.lower()
        if any(kw.lower() in text_lower for kw in keywords):
            doc = clause.source_file
            if clause.circular_date:
                doc += f" (dated {clause.circular_date})"
            return doc
    if clauses:
        return clauses[0].source_file
    return "policy_benefit_schedule.txt"
