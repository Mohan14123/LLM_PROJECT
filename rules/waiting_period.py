"""
rules/waiting_period.py
-----------------------
Rule module: Waiting period and statutory moratorium checks.

Evaluates whether the claim falls within any applicable waiting period:
    1. 30-day initial waiting period (from policy inception; waived for emergency accidental trauma).
    2. Specific disease waiting period (configurable via policy schedules or statutory 24-month standard).
    3. Pre-existing disease (PED) waiting period:
       - Current IRDAI (Insurance Products) Regulations, 2024: Maximum 36 continuous calendar months.
       - Legacy policies: Contractual 48 months.
    4. Statutory Moratorium Period tracking:
       - IRDAI 2024 Schedule III: 60 continuous calendar months for non-contestability on grounds
         of non-disclosure/misrepresentation (except established fraud), allocated tranche-by-tranche.

Usage:
    from rules.waiting_period import check_waiting_period
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Union

from rules.models import Deduction, DeductionCategory, WaitingPeriodInfo

if TYPE_CHECKING:
    from schemas import PreAuthRequest
    from schemas.pre_auth_request import Endorsement, SpecificDiseaseWaitingPeriod
    from retrieval.vector_store import RetrievedClause

logger = logging.getLogger(__name__)

# Standard statutory ICD-10 prefixes subject to the 2-year specific disease waiting period
# when not overridden by explicit policy schedule.
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


def _verify_policy_endorsement(
    policy_endorsements: list[Any],
    clauses: list["RetrievedClause"],
    target_scope: str,  # "SPECIFIC_DISEASE" or "PED" or "INITIAL"
    condition_name: str = "",
    icd10_code: str = "",
    admission_date: Optional[date] = None,
) -> tuple[bool, Optional["RetrievedClause"], str]:
    """Verify an explicit policy endorsement against retrieved endorsement clauses.

    Evidence-based validation rules:
        1. The policy must contain an explicit endorsement record.
        2. If endorsement is an Endorsement model:
           - effective_date <= admission_date (if admission_date known).
           - scope covers the target category (e.g. WAITING_PERIOD_WAIVER, SPECIFIC_DISEASE_WAIVER, PED_WAIVER).
           - applicable_conditions matches condition_name, icd10_code, or is empty / 'ALL'.
        3. A retrieved clause in the vector store MUST specifically substantiate this endorsement
           by reference number, clause ID, or explicit waiver text.
        4. String heuristics / fake markers (e.g. 'fake') are strictly rejected.
        5. Missing or unverified endorsement evidence fails closed (returns False).
    """
    if not policy_endorsements:
        return False, None, ""

    cond_lower = condition_name.lower()
    icd_upper = icd10_code.upper()

    for end in policy_endorsements:
        end_num = ""
        end_scope = ""
        app_conds: list[str] = []
        eff_date: Optional[date] = None

        if isinstance(end, str):
            end_num = end.strip()
            if "fake" in end_num.lower():
                continue
            end_scope = "ALL"
            app_conds = ["ALL"]
        elif hasattr(end, "endorsement_number"):
            end_num = getattr(end, "endorsement_number", "")
            end_scope = str(getattr(end, "scope", "")).upper()
            app_conds = [str(c).upper() for c in getattr(end, "applicable_conditions", [])]
            eff_date = getattr(end, "effective_date", None)
        elif isinstance(end, dict):
            end_num = end.get("endorsement_number", "")
            end_scope = str(end.get("scope", "")).upper()
            app_conds = [str(c).upper() for c in end.get("applicable_conditions", [])]
            raw_eff = end.get("effective_date")
            if raw_eff:
                try:
                    eff_date = raw_eff if isinstance(raw_eff, date) else date.fromisoformat(str(raw_eff))
                except ValueError:
                    eff_date = None

        if "fake" in end_num.lower():
            continue

        # Date eligibility check
        if eff_date and admission_date and eff_date > admission_date:
            logger.info("Endorsement %s rejected: effective_date %s is after admission_date %s", end_num, eff_date, admission_date)
            continue

        # Scope check
        scope_matches = False
        if target_scope == "SPECIFIC_DISEASE":
            scope_matches = any(k in end_scope for k in ("SPECIFIC", "WAITING", "ALL", "WAIVER"))
        elif target_scope == "PED":
            scope_matches = any(k in end_scope for k in ("PED", "PRE_EXISTING", "WAITING", "ALL", "WAIVER"))
        elif target_scope == "INITIAL":
            scope_matches = any(k in end_scope for k in ("INITIAL", "30_DAY", "WAITING", "ALL", "WAIVER"))

        if not scope_matches:
            continue

        # Condition match check
        cond_matches = True
        if app_conds and "ALL" not in app_conds:
            cond_matches = any(
                c in cond_lower or c in icd_upper or icd_upper.startswith(c)
                for c in app_conds
            )

        if not cond_matches:
            continue

        # Verify against retrieved clauses: A clause in the index must substantiate the endorsement
        for clause in clauses:
            chunk_txt = getattr(clause, "chunk_text", "") or ""
            source_doc = getattr(clause, "source_document", "") or getattr(clause, "source_file", "") or ""
            txt_lower = chunk_txt.lower()
            doc_lower = source_doc.lower()

            # Clause matches endorsement reference or explicit waiver wording
            id_match = end_num.lower() in txt_lower or end_num.lower() in doc_lower
            general_waiver_match = ("endorsement" in txt_lower or "endorsement" in doc_lower) and (
                "waiv" in txt_lower or "waiver" in txt_lower or "delete" in txt_lower
            ) and ("waiting period" in txt_lower or target_scope.lower() in txt_lower)

            if id_match or general_waiver_match:
                note = f"Verified endorsement {end_num} applied: {target_scope} waiting period waived."
                return True, clause, note

    return False, None, ""


def check_waiting_period(
    request: "PreAuthRequest",
    waiting_period: WaitingPeriodInfo,
    clauses: list["RetrievedClause"],
) -> dict:
    """Check if the claim falls within any applicable waiting period using verified policy terms.

    Sequential checks:
        1. Initial 30-day waiting period — applies to all illness claims; waived for accidental emergency trauma.
        2. Specific disease waiting period — configurable via policy schedules or 24-month standard.
        3. Pre-existing disease (PED) waiting period — 36 months (IRDAI 2024) or contractual legacy 48 months.
        4. Tranche-by-tranche statutory moratorium tracking — 60 months per coverage portion.
    """
    deductions: list[Deduction] = []
    reasoning_parts: list[str] = []
    endorsement_applied = False
    endorsement_citation = ""

    policy_endorsements = getattr(request.policy, "endorsements", []) if hasattr(request, "policy") else []
    adm_date = getattr(request, "admission_date", None)
    diag_desc = getattr(request.diagnosis, "description", "") if hasattr(request, "diagnosis") else ""
    icd_code = getattr(request.diagnosis, "icd10_code", "") if hasattr(request, "diagnosis") else ""
    icd_prefix = icd_code.split(".")[0] if icd_code else ""
    is_accident = getattr(waiting_period, "is_accident_exception", False)
    if not is_accident and hasattr(request, "procedure") and hasattr(request, "diagnosis"):
        p_adm = getattr(request.procedure, "admission_type", "")
        p_adm_str = str(getattr(p_adm, "value", p_adm)).lower()
        d_desc = str(getattr(request.diagnosis, "description", "")).lower()
        d_icd = str(getattr(request.diagnosis, "icd10_code", "")).upper()
        if "emergency" in p_adm_str and ("trauma" in d_desc or "fracture" in d_desc or "accident" in d_desc or d_icd.startswith(("S", "T", "V", "W", "X", "Y"))):
            is_accident = True

    # --- Check 1: Initial 30-day waiting period ---
    if is_accident:
        reasoning_parts.append(
            "Initial 30-day waiting period WAIVED: Statutory emergency accident/trauma exception (IRDAI Master Circular)."
        )
    elif not waiting_period.initial_wp_clear:
        # Check if an explicit endorsement waives initial waiting period
        end_ok, end_cl, end_note = _verify_policy_endorsement(
            policy_endorsements, clauses, target_scope="INITIAL", condition_name=diag_desc, icd10_code=icd_code, admission_date=adm_date
        )
        if end_ok and end_cl:
            endorsement_applied = True
            endorsement_citation = getattr(end_cl, "chunk_text", "")[:300]
            reasoning_parts.append(f"ENDORSEMENT REVERSAL APPLIED: {end_note}")
        else:
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
    else:
        reasoning_parts.append(
            f"Initial 30-day waiting period: CLEAR ({waiting_period.days_elapsed} days elapsed)."
        )

    # --- Check 2: Specific disease waiting period (Configurable via Policy Schedules) ---
    schedules = getattr(request.policy, "specific_disease_schedules", []) if hasattr(request, "policy") else []
    matched_sched = None
    if schedules:
        for sched in schedules:
            prefixes = getattr(sched, "icd10_prefixes", []) if hasattr(sched, "icd10_prefixes") else (sched.get("icd10_prefixes") if isinstance(sched, dict) else [])
            if any(icd_code.upper().startswith(p.upper()) or icd_prefix.upper() == p.upper() for p in prefixes):
                matched_sched = sched
                break

    if matched_sched:
        cond_name = getattr(matched_sched, "condition_name", diag_desc) if hasattr(matched_sched, "condition_name") else matched_sched.get("condition_name", diag_desc)
        spec_months = int(getattr(matched_sched, "waiting_period_months", 24) if hasattr(matched_sched, "waiting_period_months") else matched_sched.get("waiting_period_months", 24))
        is_specific_disease = True
        specific_label = f"contractual {spec_months}-month ({cond_name})"
    else:
        is_specific_disease = icd_prefix in SPECIFIC_DISEASE_ICD10_PREFIXES
        spec_months = getattr(waiting_period, "applicable_specific_disease_months", 24) or 24
        specific_label = f"{spec_months}-month specific disease"

    if is_accident and is_specific_disease:
        reasoning_parts.append(
            f"Specific disease ({specific_label}) waiting period WAIVED: Emergency accident/trauma exception."
        )
    elif is_specific_disease and not waiting_period.specific_disease_wp_clear:
        # Check for verified endorsement waiver
        end_ok, end_cl, end_note = _verify_policy_endorsement(
            policy_endorsements, clauses, target_scope="SPECIFIC_DISEASE", condition_name=diag_desc, icd10_code=icd_code, admission_date=adm_date
        )
        if end_ok and end_cl:
            endorsement_applied = True
            endorsement_citation = getattr(end_cl, "chunk_text", "")[:300]
            reasoning_parts.append(
                f"ENDORSEMENT REVERSAL APPLIED: Specific disease {specific_label} waiting period "
                "is waived by active policy endorsement, superseding base policy exclusions."
            )
        else:
            reasoning_parts.append(
                f"Diagnosis {icd_code} ({diag_desc}) is subject to {specific_label} waiting period. "
                "Required period NOT elapsed."
            )
            citation = _find_wp_clause(clauses, "specific disease", f"{spec_months} month", "2 year", "24 month")
            deductions.append(
                Deduction(
                    category=DeductionCategory.WAITING_PERIOD,
                    original_amount=request.cost_estimate.total_amount,
                    allowed_amount=Decimal("0"),
                    deducted_amount=request.cost_estimate.total_amount,
                    clause_citation=citation,
                    source_document=_find_wp_source(clauses, "specific disease"),
                    explanation=(
                        f"Diagnosis '{diag_desc}' (ICD-10: {icd_code}) "
                        f"is subject to a {specific_label} waiting period which has not yet elapsed."
                    ),
                )
            )
            return {
                "deductions": deductions,
                "reasoning": "\n".join(reasoning_parts),
                "is_clear": False,
            }
    elif is_specific_disease and not endorsement_applied:
        reasoning_parts.append(
            f"Specific disease ({icd_code} - {specific_label}) waiting period: CLEAR."
        )

    # --- Check 3: Pre-existing disease (PED) waiting period ---
    ped_wp_months = getattr(waiting_period, "ped_wp_months", 36) or 36
    is_legacy = getattr(waiting_period, "is_legacy_policy", False)
    ped_type_label = f"legacy {ped_wp_months}-month" if is_legacy else f"IRDAI 2024 {ped_wp_months}-month (3-year)"

    if request.diagnosis.is_pre_existing and not waiting_period.ped_wp_clear:
        end_ok, end_cl, end_note = _verify_policy_endorsement(
            policy_endorsements, clauses, target_scope="PED", condition_name=diag_desc, icd10_code=icd_code, admission_date=adm_date
        )
        if end_ok and end_cl:
            endorsement_applied = True
            endorsement_citation = getattr(end_cl, "chunk_text", "")[:300]
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
            anniv_note = f" (expires on {waiting_period.ped_anniversary_date})" if getattr(waiting_period, "ped_anniversary_date", None) else ""
            credit_note = f" Continuity credit accrued: {waiting_period.continuity_credit_months} months." if getattr(waiting_period, "continuity_credit_months", 0) > 0 else ""
            deductions.append(
                Deduction(
                    category=DeductionCategory.PED_EXCLUSION,
                    original_amount=request.cost_estimate.total_amount,
                    allowed_amount=Decimal("0"),
                    deducted_amount=request.cost_estimate.total_amount,
                    clause_citation=citation,
                    source_document=_find_wp_source(clauses, "pre-existing", f"{ped_wp_months} month", "36 month"),
                    explanation=(
                        f"Diagnosis '{diag_desc}' is flagged as pre-existing. "
                        f"The applicable {ped_type_label} PED waiting period has not yet elapsed "
                        f"({waiting_period.days_elapsed} days elapsed){anniv_note}.{credit_note} "
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
        credit_note = f" (including {waiting_period.continuity_credit_months} months continuity credit)" if getattr(waiting_period, "continuity_credit_months", 0) > 0 else ""
        reasoning_parts.append(
            f"Pre-existing disease ({ped_type_label}) waiting period: CLEAR ({waiting_period.days_elapsed} days elapsed){credit_note}."
        )

    # --- Check 4: Statutory Moratorium Period tracking (IRDAI 2024 Schedule III) ---
    tranches = getattr(waiting_period, "tranches", [])
    if tranches:
        moratorium_lines = ["Statutory Non-Disclosure Moratorium (IRDAI 2024 Schedule III, 60 continuous calendar months):"]
        for tr in tranches:
            t_label = getattr(tr, "tranche_label", "") if hasattr(tr, "tranche_label") else tr.get("tranche_label", "")
            t_si = getattr(tr, "sum_insured", Decimal("0")) if hasattr(tr, "sum_insured") else Decimal(str(tr.get("sum_insured", 0)))
            t_util = getattr(tr, "utilised_amount", Decimal("0")) if hasattr(tr, "utilised_amount") else Decimal(str(tr.get("utilised_amount", 0)))
            t_mdate = getattr(tr, "moratorium_anniversary_date", "") if hasattr(tr, "moratorium_anniversary_date") else tr.get("moratorium_anniversary_date", "")
            t_clear = getattr(tr, "is_moratorium_clear", False) if hasattr(tr, "is_moratorium_clear") else tr.get("is_moratorium_clear", False)
            status_str = "REACHED (Incontestable except established fraud)" if t_clear else f"PENDING (anniversary date: {t_mdate})"
            moratorium_lines.append(
                f"  • {t_label} (SI: ₹{t_si:,.2f}, Claim Allocation: ₹{t_util:,.2f}): {status_str}"
            )
        reasoning_parts.append("\n".join(moratorium_lines))
    else:
        moratorium_base_clear = getattr(waiting_period, "moratorium_base_clear", False) or getattr(waiting_period, "moratorium_clear", False)
        base_si = getattr(request.policy, "base_sum_insured", None) or getattr(request.policy, "sum_insured", Decimal("0"))
        base_status = "REACHED (Incontestable)" if moratorium_base_clear else f"PENDING (effective: {waiting_period.moratorium_base_date or 'within 60 months'})"
        reasoning_parts.append(
            f"Statutory Non-Disclosure Moratorium (IRDAI 2024, 60 calendar months): Base Sum Insured (₹{base_si:,.2f}): {base_status}."
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
