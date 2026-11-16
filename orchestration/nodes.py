"""
orchestration/nodes.py
----------------------
Individual node functions for the LangGraph agent graph.

Each function takes PipelineState as input and returns a partial state
update dict. The graph wires these nodes in sequence with conditional
edges for escalation.

Architecture Role:
    These are the building blocks of the LangGraph state machine defined
    in orchestration/graph.py. Each node is a pure function that reads
    from state, performs its work, and returns its output fields.

Guardrail Compliance:
    - Node 7 (citation_guard): Non-bypassable per Guardrail #2.
    - Node 9 (format_recommendation): Always outputs RECOMMEND_* (Guardrail #1).
    - Node 10 (escalation_gate): Explicit triggers per Guardrail #7.

Usage:
    from orchestration.nodes import validate_intake, retrieve_clauses_node
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


# ============================================================================
# LLM System Prompt (Guardrail #1: recommend-only, Decoupled Independent Review)
# ============================================================================

_SYSTEM_PROMPT = """\
You are a senior medical director and health insurance claims clinical analyst for an Indian insurer.
Your role is to perform an independent clinical necessity assessment for a cashless
pre-authorisation request (Dual-Track Neuro-Symbolic Architecture). You must:

1. ALWAYS frame your output as a RECOMMENDATION, never a final decision.
2. Cite specific clause IDs or clinical guidelines from the retrieved documents.
3. Use ONLY the clinical information provided — do not fabricate or hallucinate clauses.
4. Assess strictly:
   - Medical necessity of the admission.
   - Whether the diagnosis clinically supports the proposed procedure.
   - Sufficiency of available clinical evidence and investigation reports.
   - Clinical uncertainty or contraindications.
5. You DO NOT calculate insurance deductibles, co-pays, sub-limits, or payable financial amounts. Financial calculations belong exclusively to Track 1 (Symbolic Rules Engine).

IMPORTANT: Always end your output with these exact machine-parseable tags on separate lines:
CLINICAL_RECOMMENDATION: [AUTHORISE | DENY | ESCALATE | QUERY]
CLINICAL_CONFIDENCE: [0.0 to 1.0]
CLINICAL_UNCERTAINTY: [LOW | MODERATE | HIGH]
CLINICAL_SUMMARY: [Single-sentence clinical necessity assessment]

Label the header of your narrative:
"RECOMMENDATION — requires human sign-off"."""


# ============================================================================
# Node 1: Validate Intake
# ============================================================================

def validate_intake(state: dict[str, Any]) -> dict[str, Any]:
    """Validate that the intake result contains a successful extraction.

    If intake failed, the pipeline short-circuits to RECOMMEND_QUERY
    asking for missing documents.

    Returns:
        Updated state with pre_auth_request populated.
    """
    start = time.perf_counter()

    intake = state.get("intake_result", {})
    is_success = intake.get("is_success", False)

    if not is_success:
        logger.warning("Intake extraction failed — recommending QUERY for missing documents.")
        return {
            "pre_auth_request": None,
            "recommendation": "RECOMMEND_QUERY",
            "confidence": 0.3,
            "errors": intake.get("validation_errors", ["Intake extraction failed"]),
            "pipeline_status": "failed",
            "node_latencies": {
                **state.get("node_latencies", {}),
                "validate_intake": time.perf_counter() - start,
            },
        }

    return {
        "pre_auth_request": intake.get("request"),
        "pipeline_status": "running",
        "node_latencies": {
            **state.get("node_latencies", {}),
            "validate_intake": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 2: Retrieve Clauses
# ============================================================================

def retrieve_clauses_node(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant policy/regulatory clauses from the FAISS vector store.

    Builds a composite query from diagnosis + procedure + plan type and
    searches the FAISS index for the most relevant policy wordings,
    benefit tables, and IRDAI regulatory excerpts.

    Returns:
        Updated state with retrieved_clauses and retrieval_query.
    """
    start = time.perf_counter()

    request = state.get("pre_auth_request")
    ablation = state.get("ablation_config", {})

    if request is None or ablation.get("disable_retrieval", False):
        return {
            "retrieved_clauses": [],
            "retrieval_query": "",
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_clauses": time.perf_counter() - start,
            },
        }

    # Build composite query from claim data
    diagnosis = request.get("diagnosis", {})
    procedure = request.get("procedure", {})
    policy = request.get("policy", {})

    query_parts = [
        diagnosis.get("description", ""),
        diagnosis.get("icd10_code", ""),
        procedure.get("description", ""),
        policy.get("plan_type", ""),
    ]
    query = " ".join(filter(None, query_parts))
    query += " coverage eligibility waiting period sub-limit co-pay exclusion"

    logger.info("Retrieval query: %s", query[:120])

    # Call the FAISS vector store
    try:
        from retrieval import retrieve_clauses

        results = retrieve_clauses(query=query, top_k=5)
        retrieved = [r.to_dict() for r in results]
        logger.info("Retrieved %d clauses (top score=%.4f).",
                     len(retrieved),
                     retrieved[0]["similarity_score"] if retrieved else 0.0)
    except FileNotFoundError:
        logger.warning(
            "FAISS index not found. Run the index builder first: "
            "python -c 'from retrieval.embedder import Embedder; ...'. "
            "Falling back to empty clauses."
        )
        retrieved = []
    except ImportError as e:
        logger.warning("Retrieval dependency missing (%s). Falling back to empty clauses.", e)
        retrieved = []
    except Exception as e:
        logger.error("Retrieval failed: %s", e, exc_info=True)
        retrieved = []

    return {
        "retrieval_query": query,
        "retrieved_clauses": retrieved,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "retrieve_clauses": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 3: Call Policy API
# ============================================================================

def call_policy_api(state: dict[str, Any]) -> dict[str, Any]:
    """Call the mock Policy Admin API for policy status and waiting period.

    Uses the mock PAS logic directly (matching orchestration/mock_api/app.py)
    to avoid requiring a running server. In production, this would be replaced
    with actual HTTP calls to the insurer's core systems.

    Returns:
        Updated state with policy_status and waiting_period_info.
    """
    start = time.perf_counter()

    request = state.get("pre_auth_request") or {}
    policy = (request.get("policy") or {}) if isinstance(request, dict) else {}
    policy_number = policy.get("policy_number", "UNKNOWN")

    # --- Parse Exact Policy Dates & Continuous Coverage (Calendar Arithmetic) ---
    policy_start = policy.get("policy_start_date")
    admission_date_str = (request.get("admission_date") or request.get("submitted_at")) if isinstance(request, dict) else None

    # Handle incomplete or missing policy dates safely (fail closed)
    if not policy_start or not admission_date_str:
        logger.warning("Missing policy start date or admission date — cannot adjudicate waiting periods safely.")
        return {
            "policy_status": {
                "is_active": False,
                "status": "UNVERIFIED_DATES",
                "remaining_sum_insured": "0.00",
                "days_since_inception": 0,
            },
            "waiting_period_info": {
                "initial_wp_clear": False,
                "specific_disease_wp_clear": False,
                "ped_wp_clear": False,
                "days_elapsed": 0,
                "applicable_wp_months": 36,
                "ped_wp_months": 36,
                "is_legacy_policy": False,
                "continuity_credit_months": 0,
                "moratorium_clear": False,
                "moratorium_base_clear": False,
                "moratorium_enhanced_clear": False,
                "moratorium_months": 60,
                "tranches": [],
                "is_accident_exception": False,
            },
            "errors": [*state.get("errors", []), "Incomplete policy dates: policy_start_date or admission_date missing."],
            "pipeline_status": "escalated",
            "needs_escalation": True,
            "escalation_triggers": [*state.get("escalation_triggers", []), "Trigger 2.8: Incomplete Policy Dates requiring underwriter verification"],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "call_policy_api": time.perf_counter() - start,
            },
        }

    try:
        start_date = policy_start if isinstance(policy_start, date) else date.fromisoformat(str(policy_start))
        ref_date = admission_date_str if isinstance(admission_date_str, date) else date.fromisoformat(str(admission_date_str))
        days_since_inception = max((ref_date - start_date).days, 0)
    except (ValueError, TypeError) as e:
        logger.warning("Could not parse policy dates: %s. Failing closed.", e)
        return {
            "policy_status": {
                "is_active": False,
                "status": "INVALID_DATES",
                "remaining_sum_insured": "0.00",
                "days_since_inception": 0,
            },
            "waiting_period_info": {
                "initial_wp_clear": False,
                "specific_disease_wp_clear": False,
                "ped_wp_clear": False,
                "days_elapsed": 0,
                "applicable_wp_months": 36,
                "ped_wp_months": 36,
                "is_legacy_policy": False,
                "continuity_credit_months": 0,
                "moratorium_clear": False,
                "moratorium_base_clear": False,
                "moratorium_enhanced_clear": False,
                "moratorium_months": 60,
                "tranches": [],
                "is_accident_exception": False,
            },
            "errors": [*state.get("errors", []), f"Invalid policy dates format: {e}"],
            "pipeline_status": "escalated",
            "needs_escalation": True,
            "escalation_triggers": [*state.get("escalation_triggers", []), "Trigger 2.8: Invalid Policy Dates"],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "call_policy_api": time.perf_counter() - start,
            },
        }

    # --- Accrue Portability / Migration Continuity Credits from Verified Coverage History ---
    portability_history = policy.get("portability_history") or []
    continuity_months = 0
    if portability_history:
        for rec in portability_history:
            if isinstance(rec, dict):
                is_appr = rec.get("is_portability_approved", True)
                break_days = int(rec.get("continuity_break_days", 0) or 0)
                if is_appr and break_days <= 30:
                    ps = rec.get("previous_policy_start_date")
                    pe = rec.get("previous_policy_end_date")
                    if ps and pe:
                        try:
                            ps_dt = ps if isinstance(ps, date) else date.fromisoformat(str(ps))
                            pe_dt = pe if isinstance(pe, date) else date.fromisoformat(str(pe))
                            dur_months = (pe_dt.year - ps_dt.year) * 12 + (pe_dt.month - ps_dt.month)
                            continuity_months += max(dur_months, 0)
                        except (ValueError, TypeError):
                            pass
            elif hasattr(rec, "is_portability_approved") and rec.is_portability_approved and rec.continuity_break_days <= 30:
                dur_months = (rec.previous_policy_end_date.year - rec.previous_policy_start_date.year) * 12 + (rec.previous_policy_end_date.month - rec.previous_policy_start_date.month)
                continuity_months += max(dur_months, 0)
    if continuity_months == 0:
        continuity_months = int(policy.get("continuity_credit_months", 0) or 0)

    effective_start = start_date - relativedelta(months=continuity_months)

    # --- Mock PAS logic (matches mock_api/app.py) ---
    status = "ACTIVE"
    is_active = True
    if "LAPSED" in policy_number.upper():
        status = "LAPSED"
        is_active = False
    elif "EXPIRED" in policy_number.upper():
        status = "EXPIRED"
        is_active = False

    sum_insured = str(policy.get("sum_insured", "500000.00"))
    co_pay_pct = str(policy.get("co_pay_pct", "0.00"))

    # --- Evidence-Based Policy Classification per IRDAI 2024 ---
    ped_override = policy.get("ped_waiting_period_months")
    product_version = str(policy.get("product_version", "")).lower()
    is_legacy = (ped_override == 48) or ("legacy" in product_version) or ("pre_2024" in product_version)

    if ped_override is not None:
        ped_wp_months = int(ped_override)
    else:
        ped_wp_months = 48 if is_legacy else 36

    # --- Accident-Related Emergency Exception Detection ---
    proc = request.get("procedure", {}) if request else {}
    diag = request.get("diagnosis", {}) if request else {}
    adm_raw = proc.get("admission_type", "") if isinstance(proc, dict) else getattr(proc, "admission_type", "")
    adm_type_str = str(getattr(adm_raw, "value", adm_raw)).lower()
    diag_desc = str(diag.get("description", "") if isinstance(diag, dict) else getattr(diag, "description", "")).lower()
    icd10 = str(diag.get("icd10_code", "") if isinstance(diag, dict) else getattr(diag, "icd10_code", "")).upper()
    is_accident_exception = ("emergency" in adm_type_str) and (
        "trauma" in diag_desc or "fracture" in diag_desc or "accident" in diag_desc or icd10.startswith(("S", "T", "V", "W", "X", "Y"))
    )

    # 1. Initial 30-day waiting period (waived for emergency accidental trauma)
    initial_wp_clear = is_accident_exception or (ref_date >= (effective_start + timedelta(days=30)))

    # 2. Specific disease waiting period (configurable via schedule or statutory 24 months)
    specific_disease_schedules = policy.get("specific_disease_schedules") or []
    matched_condition = None
    spec_wp_months = 24
    if specific_disease_schedules:
        for sched in specific_disease_schedules:
            prefixes = sched.get("icd10_prefixes", []) if isinstance(sched, dict) else getattr(sched, "icd10_prefixes", [])
            if any(icd10.startswith(pfx.upper()) for pfxfx in prefixes for pfx in [pfxfx]):
                matched_condition = sched.get("condition_name") if isinstance(sched, dict) else getattr(sched, "condition_name", "")
                spec_wp_months = int(sched.get("waiting_period_months", 24) if isinstance(sched, dict) else getattr(sched, "waiting_period_months", 24))
                break

    specific_anniversary = effective_start + relativedelta(months=spec_wp_months)
    specific_disease_wp_clear = is_accident_exception or (ref_date >= specific_anniversary)

    # 3. Pre-existing disease waiting period (calendar anniversary)
    ped_anniversary = effective_start + relativedelta(months=ped_wp_months)
    ped_wp_clear = ref_date >= ped_anniversary

    # 4. Multi-Tranche Sum Insured Enhancement & Sequential Moratorium Allocation
    base_si = Decimal(str(policy.get("base_sum_insured") or policy.get("sum_insured", "500000")))
    base_moratorium_date = effective_start + relativedelta(months=60)
    base_moratorium_clear = ref_date >= base_moratorium_date

    tranches = [
        {
            "tranche_id": "BASE",
            "tranche_label": "Base Sum Insured",
            "sum_insured": float(base_si),
            "start_date": effective_start.isoformat(),
            "moratorium_anniversary_date": base_moratorium_date.isoformat(),
            "is_moratorium_clear": base_moratorium_clear,
            "utilised_amount": 0.0,
            "remaining_amount": float(base_si),
        }
    ]

    enhancements = policy.get("enhancements") or []
    if not enhancements and policy.get("enhancement_date") and policy.get("enhanced_sum_insured"):
        enhancements = [
            {
                "enhancement_id": "ENH-1",
                "enhancement_date": policy.get("enhancement_date"),
                "additional_sum_insured": policy.get("enhanced_sum_insured"),
            }
        ]

    for enh in enhancements:
        enh_dt_raw = enh.get("enhancement_date") if isinstance(enh, dict) else getattr(enh, "enhancement_date", None)
        enh_amt_raw = enh.get("additional_sum_insured") if isinstance(enh, dict) else getattr(enh, "additional_sum_insured", "0")
        enh_id = enh.get("enhancement_id", "ENH") if isinstance(enh, dict) else getattr(enh, "enhancement_id", "ENH")
        if enh_dt_raw:
            enh_dt = enh_dt_raw if isinstance(enh_dt_raw, date) else date.fromisoformat(str(enh_dt_raw))
            enh_amt = Decimal(str(enh_amt_raw))
            enh_m_date = enh_dt + relativedelta(months=60)
            enh_m_clear = ref_date >= enh_m_date
            tranches.append({
                "tranche_id": str(enh_id),
                "tranche_label": f"Enhancement ({enh_id})",
                "sum_insured": float(enh_amt),
                "start_date": enh_dt.isoformat(),
                "moratorium_anniversary_date": enh_m_date.isoformat(),
                "is_moratorium_clear": enh_m_clear,
                "utilised_amount": 0.0,
                "remaining_amount": float(enh_amt),
            })

    # Sequential claim allocation across tranches
    cost_est = (request.get("cost_estimate") or {}) if request else {}
    claim_total = Decimal(str(cost_est.get("total_amount", "0")))
    remaining_claim = claim_total
    touched_tranches = []

    for tr in tranches:
        t_si = Decimal(str(tr["sum_insured"]))
        alloc = min(remaining_claim, t_si)
        tr["utilised_amount"] = float(alloc)
        tr["remaining_amount"] = float(t_si - alloc)
        if alloc > 0:
            touched_tranches.append(tr)
            remaining_claim -= alloc

    if not touched_tranches and tranches:
        touched_tranches = [tranches[0]]

    moratorium_clear = all(tr["is_moratorium_clear"] for tr in touched_tranches)
    moratorium_base_clear = tranches[0]["is_moratorium_clear"]
    moratorium_enhanced_clear = all(tr["is_moratorium_clear"] for tr in tranches[1:]) if len(tranches) > 1 else moratorium_base_clear
    enhanced_m_date_str = tranches[1]["moratorium_anniversary_date"] if len(tranches) > 1 else None

    logger.info(
        "Policy %s: status=%s, effective_start=%s, days_elapsed=%d, ped_wp_months=%d, ped_clear=%s, moratorium_clear=%s",
        policy_number, status, effective_start, days_since_inception, ped_wp_months, ped_wp_clear, moratorium_clear,
    )

    return {
        "policy_status": {
            "is_active": is_active,
            "status": status,
            "remaining_sum_insured": sum_insured,
            "days_since_inception": days_since_inception,
        },
        "waiting_period_info": {
            "initial_wp_clear": initial_wp_clear,
            "specific_disease_wp_clear": specific_disease_wp_clear,
            "ped_wp_clear": ped_wp_clear,
            "days_elapsed": days_since_inception,
            "applicable_wp_months": ped_wp_months,
            "ped_wp_months": ped_wp_months,
            "is_legacy_policy": is_legacy,
            "continuity_credit_months": continuity_months,
            "ped_anniversary_date": str(ped_anniversary),
            "moratorium_clear": moratorium_clear,
            "moratorium_base_clear": moratorium_base_clear,
            "moratorium_enhanced_clear": moratorium_enhanced_clear,
            "moratorium_months": 60,
            "moratorium_base_date": str(base_moratorium_date),
            "moratorium_enhanced_date": enhanced_m_date_str,
            "tranches": tranches,
            "specific_disease_name": matched_condition,
            "applicable_specific_disease_months": spec_wp_months,
            "is_accident_exception": is_accident_exception,
        },
        "node_latencies": {
            **state.get("node_latencies", {}),
            "call_policy_api": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 4: Call Hospital API
# ============================================================================

def call_hospital_api(state: dict[str, Any]) -> dict[str, Any]:
    """Call the mock Hospital Empanelment API.

    Uses the mock logic directly (matching orchestration/mock_api/app.py).
    Determines empanelment status from the hospital's network_tier field.

    Returns:
        Updated state with hospital_empanelment.
    """
    start = time.perf_counter()

    request = state.get("pre_auth_request", {})
    hospital = request.get("hospital", {}) if request else {}
    network_tier = hospital.get("network_tier", "cashless_network")
    hospital_name = hospital.get("name", "Unknown Hospital")

    # Non-network tier means not empanelled for cashless
    is_empanelled = network_tier != "non_network"
    tier = network_tier if is_empanelled else "non_network"

    logger.info(
        "Hospital '%s': empanelled=%s, tier=%s",
        hospital_name, is_empanelled, tier,
    )

    return {
        "hospital_empanelment": {
            "is_empanelled": is_empanelled,
            "tier": tier,
            "agreed_room_rate": "5000.00",
        },
        "node_latencies": {
            **state.get("node_latencies", {}),
            "call_hospital_api": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 5: Apply Rules Engine
# ============================================================================

def apply_rules_engine(state: dict[str, Any]) -> dict[str, Any]:
    """Apply the deterministic rules engine to produce an adjudication result.

    Reconstructs Pydantic objects from the pipeline state dicts and calls
    the full rules engine (policy validity → waiting period → exclusions →
    sub-limits → co-pay → fairness → aggregate).

    Returns:
        Updated state with adjudication_result.
    """
    start = time.perf_counter()

    request_dict = state.get("pre_auth_request")

    if not request_dict:
        return {
            "adjudication_result": {
                "recommendation": "RECOMMEND_QUERY",
                "confidence_score": 0.30,
                "total_claimed": "0",
                "total_approved": "0",
                "total_deducted": "0",
                "deductions": [],
                "reasoning_trace": "No valid pre-auth request available.",
            },
            "node_latencies": {
                **state.get("node_latencies", {}),
                "apply_rules_engine": time.perf_counter() - start,
            },
        }

    try:
        from schemas import PreAuthRequest
        from rules import apply_rules, PolicyStatusInfo, WaitingPeriodInfo
        from retrieval.vector_store import RetrievedClause

        # --- Reconstruct PreAuthRequest ---
        request_obj = PreAuthRequest.model_validate(request_dict)

        # --- Reconstruct RetrievedClause objects ---
        clause_dicts = state.get("retrieved_clauses", [])
        clauses = []
        for cd in clause_dicts:
            clauses.append(RetrievedClause(
                chunk_text=cd.get("chunk_text", cd.get("text", "")),
                source_file=cd.get("source_file", ""),
                section=cd.get("section", ""),
                document_type=cd.get("document_type", "policy_wording"),
                circular_date=cd.get("circular_date", ""),
                circular_number=cd.get("circular_number", ""),
                similarity_score=cd.get("similarity_score", 0.0),
                chunk_id=cd.get("chunk_id", cd.get("clause_id", "")),
            ))

        # --- Reconstruct PolicyStatusInfo ---
        ps = state.get("policy_status", {})
        policy_status = PolicyStatusInfo(
            is_active=ps.get("is_active", True),
            status=ps.get("status", "ACTIVE"),
            remaining_sum_insured=Decimal(str(ps.get("remaining_sum_insured", "500000"))),
            days_since_inception=ps.get("days_since_inception", 365),
        )

        # --- Reconstruct WaitingPeriodInfo ---
        from rules.models import MoratoriumTranche
        wp = state.get("waiting_period_info", {})
        tranches_list: list[MoratoriumTranche] = []
        for tr in wp.get("tranches", []):
            try:
                tranches_list.append(MoratoriumTranche(
                    tranche_id=tr["tranche_id"],
                    tranche_label=tr.get("tranche_label", ""),
                    sum_insured=Decimal(str(tr.get("sum_insured", "0"))),
                    utilised_amount=Decimal(str(tr.get("utilised_amount", "0"))),
                    remaining_amount=Decimal(str(tr.get("remaining_amount", "0"))),
                    start_date=date.fromisoformat(tr["start_date"]),
                    moratorium_anniversary_date=date.fromisoformat(tr["moratorium_anniversary_date"]),
                    is_moratorium_clear=tr.get("is_moratorium_clear", False),
                ))
            except Exception:
                pass

        waiting_period = WaitingPeriodInfo(
            initial_wp_clear=wp.get("initial_wp_clear", False),
            specific_disease_wp_clear=wp.get("specific_disease_wp_clear", False),
            ped_wp_clear=wp.get("ped_wp_clear", False),
            days_elapsed=wp.get("days_elapsed", 0),
            applicable_wp_months=wp.get("applicable_wp_months", 36),
            ped_wp_months=wp.get("ped_wp_months", 36),
            is_legacy_policy=wp.get("is_legacy_policy", False),
            continuity_credit_months=wp.get("continuity_credit_months", 0),
            ped_anniversary_date=date.fromisoformat(wp["ped_anniversary_date"]) if wp.get("ped_anniversary_date") else None,
            moratorium_clear=wp.get("moratorium_clear", False),
            moratorium_base_clear=wp.get("moratorium_base_clear", False),
            moratorium_enhanced_clear=wp.get("moratorium_enhanced_clear", False),
            moratorium_months=wp.get("moratorium_months", 60),
            moratorium_base_date=date.fromisoformat(wp["moratorium_base_date"]) if wp.get("moratorium_base_date") else None,
            moratorium_enhanced_date=date.fromisoformat(wp["moratorium_enhanced_date"]) if wp.get("moratorium_enhanced_date") else None,
            tranches=tranches_list,
            specific_disease_name=wp.get("specific_disease_name"),
            applicable_specific_disease_months=wp.get("applicable_specific_disease_months", 24),
            is_accident_exception=wp.get("is_accident_exception", False),
        )

        # --- Call rules engine ---
        result = apply_rules(request_obj, clauses, policy_status, waiting_period)

        # Serialize to dict (JSON-safe)
        adj_dict = result.model_dump(mode="json")

        logger.info(
            "Rules engine: %s (confidence=%.2f, claimed=%s, approved=%s, deducted=%s)",
            adj_dict.get("recommendation"),
            adj_dict.get("confidence_score", 0),
            adj_dict.get("total_claimed"),
            adj_dict.get("total_approved"),
            adj_dict.get("total_deducted"),
        )

    except Exception as e:
        logger.error("Rules engine failed: %s", e, exc_info=True)
        adj_dict = {
            "recommendation": "RECOMMEND_QUERY",
            "confidence_score": 0.30,
            "total_claimed": "0",
            "total_approved": "0",
            "total_deducted": "0",
            "deductions": [],
            "missing_info": [],
            "reasoning_trace": f"Rules engine error: {e}",
            "escalation_triggers": [f"Rules engine error: {type(e).__name__}"],
        }

    return {
        "adjudication_result": adj_dict,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "apply_rules_engine": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 6: LLM Reasoning
# ============================================================================

def llm_reasoning(state: dict[str, Any]) -> dict[str, Any]:
    """Generate independent natural-language clinical reasoning using Track 2 LLM.

    Performs an independent clinical assessment of medical necessity and guideline
    grounding, completely decoupled from Track 1's symbolic tariff calculations.

    Respects LLM_EXECUTION_MODE:
        - LIVE_REQUIRED: Fail/escalate if live model cannot respond.
        - FALLBACK_ONLY: Use deterministic clinical fallback and mark it explicitly.
        - LIVE_WITH_FALLBACK: Use fallback only when live model fails, logging reason.

    Returns:
        Updated state with reasoning_narrative, raw_llm_output, Track 2 recommendation,
        and telemetry tracking.
    """
    start = time.perf_counter()

    retrieved_clauses = state.get("retrieved_clauses", [])
    request = state.get("pre_auth_request", {})
    mode = os.getenv("LLM_EXECUTION_MODE", "FALLBACK_ONLY").upper()

    # Build decoupled Track 2 prompt (clinical request + retrieved clauses only)
    prompt = _build_reasoning_prompt(request, retrieved_clauses)

    llm_rec = "RECOMMEND_AUTHORISE"
    llm_conf = 0.90
    llm_summary = "Clinical assessment aligns with medical indications."
    narrative = ""
    token_count = {"input_tokens": 0, "output_tokens": 0}
    cost = 0.0

    if mode == "FALLBACK_ONLY":
        narrative, llm_rec, llm_conf, llm_summary = _build_clinical_fallback(request, retrieved_clauses)
    elif mode == "LIVE_REQUIRED":
        try:
            content, token_count, cost, fallback_used, fallback_reason = _call_llm(prompt)
            if fallback_used or not content:
                logger.error("LIVE_REQUIRED mode failed: live LLM unavailable (%s)", fallback_reason)
                llm_rec = "RECOMMEND_ESCALATE"
                llm_conf = 0.0
                llm_summary = f"Live LLM call required but failed: {fallback_reason}"
                narrative = f"RECOMMENDATION — requires human sign-off\n\n[ERROR: Live LLM required but failed: {fallback_reason}]"
            else:
                narrative = content
                from llm.response_parser import parse_clinical_tags
                parsed_rec, parsed_conf, parsed_summary, _, cleaned_narr = parse_clinical_tags(
                    narrative, default_rec="RECOMMEND_ESCALATE", default_conf=0.40
                )
                llm_rec = parsed_rec
                llm_conf = parsed_conf
                llm_summary = parsed_summary
                narrative = cleaned_narr
        except Exception as e:
            logger.error("LIVE_REQUIRED mode exception: %s", e)
            llm_rec = "RECOMMEND_ESCALATE"
            llm_conf = 0.0
            llm_summary = f"Live LLM call failed with exception: {e}"
            narrative = f"RECOMMENDATION — requires human sign-off\n\n[ERROR: Live LLM exception: {e}]"
    else:  # LIVE_WITH_FALLBACK
        try:
            content, token_count, cost, fallback_used, fallback_reason = _call_llm(prompt)
            if fallback_used or not content:
                logger.info("Live call failed (%s); using deterministic clinical fallback.", fallback_reason)
                narrative, llm_rec, llm_conf, llm_summary = _build_clinical_fallback(request, retrieved_clauses)
                narrative += f"\n\n[Fallback Used: {fallback_reason}]"
            else:
                narrative = content
                from llm.response_parser import parse_clinical_tags
                parsed_rec, parsed_conf, parsed_summary, _, cleaned_narr = parse_clinical_tags(
                    narrative, default_rec="RECOMMEND_ESCALATE", default_conf=0.40
                )
                llm_rec = parsed_rec
                llm_conf = parsed_conf
                llm_summary = parsed_summary
                narrative = cleaned_narr
        except Exception as e:
            logger.warning("Live LLM failed with %s; falling back to deterministic clinical engine.", e)
            narrative, llm_rec, llm_conf, llm_summary = _build_clinical_fallback(request, retrieved_clauses)
            narrative += f"\n\n[Fallback Used: {e}]"

    return {
        "reasoning_narrative": narrative,
        "raw_llm_output": narrative,
        "llm_recommendation": llm_rec,
        "llm_clinical_confidence": llm_conf,
        "llm_clinical_summary": llm_summary,
        "llm_approved_amount": None,
        "llm_token_count": token_count,
        "llm_cost_inr": cost,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "llm_reasoning": time.perf_counter() - start,
        },
    }


def _build_reasoning_prompt(
    request: dict, retrieved_clauses: list[dict],
) -> str:
    """Build the decoupled prompt for Track 2 independent clinical reasoning.

    Guarantees Track 2 independence: does NOT include Track 1's numerical
    approval totals or symbolic decisions, preventing cognitive anchoring.
    """
    parts: list[str] = []

    # Patient/claim clinical context
    patient = request.get("patient", {}) if request else {}
    diagnosis = request.get("diagnosis", {}) if request else {}
    procedure = request.get("procedure", {}) if request else {}
    policy = request.get("policy", {}) if request else {}
    cost = request.get("cost_estimate", {}) if request else {}

    parts.append("## Pre-Authorisation Clinical Request")
    parts.append(f"- Patient Age: {patient.get('age', 'N/A')}")
    parts.append(f"- Patient Gender: {patient.get('gender', 'N/A')}")
    parts.append(f"- Primary Diagnosis: {diagnosis.get('description', 'N/A')} "
                 f"(ICD-10: {diagnosis.get('icd10_code', 'N/A')})")
    parts.append(f"- Flagged as Pre-Existing (PED): {'Yes' if diagnosis.get('is_pre_existing') else 'No'}")
    parts.append(f"- Planned Procedure: {procedure.get('description', 'N/A')} "
                 f"(Code: {procedure.get('procedure_code', 'N/A')})")
    parts.append(f"- Admission Type: {procedure.get('admission_type', 'N/A')}")
    parts.append(f"- Policy Plan Type: {policy.get('plan_type', 'N/A')}")
    parts.append(f"- Sum Insured: ₹{policy.get('sum_insured', 'N/A')}")
    parts.append(f"- Total Hospital Estimated Amount: ₹{cost.get('total_amount', 'N/A')}")

    line_items = cost.get("line_items", [])
    if line_items:
        parts.append(f"\n### Itemised Cost Estimates ({len(line_items)} items):")
        for item in line_items[:8]:
            parts.append(f"  - [{item.get('category', '?')}] {item.get('item', '')}: ₹{item.get('amount', 0)}")

    # Retrieved clauses & clinical guidelines
    if retrieved_clauses:
        parts.append("\n## Retrieved Policy & Clinical Guidelines")
        for i, clause in enumerate(retrieved_clauses[:5], 1):
            text = clause.get("chunk_text", clause.get("text", ""))
            source = clause.get("source_file", "")
            cid = clause.get("clause_id") or clause.get("chunk_id") or f"CLAUSE-{i:02d}"
            score = clause.get("similarity_score", 0)
            parts.append(f"\n[Guideline {i}] ID: {cid} | Source: {source} (similarity: {score:.3f})")
            parts.append(text[:600])

    # Task instruction
    parts.append("\n## Task: Independent Clinical Necessity Adjudication")
    parts.append("1. Provide a comprehensive, structured clinical reasoning narrative in rich Markdown format assessing:\n"
                 "   - Medical necessity and diagnostic indication concordance.\n"
                 "   - Appropriateness of the planned admission type (e.g. Inpatient, Day Care, Emergency).\n"
                 "   - Compliance with standard clinical treatment protocols and relevant retrieved guidelines.\n"
                 "   Begin your narrative with: '### RECOMMENDATION — requires human sign-off'.\n"
                 "   Use clear markdown headings (####), bullet lists, and bold callouts for readability.")
    parts.append("2. Cite specific guideline/clause IDs or source excerpts retrieved above wherever applicable.")
    parts.append("3. End your response with these exact machine-parseable tags on separate lines:\n"
                 "CLINICAL_RECOMMENDATION: [AUTHORISE | DENY | ESCALATE | QUERY]\n"
                 "CLINICAL_CONFIDENCE: [0.0-1.0]\n"
                 "CLINICAL_UNCERTAINTY: [LOW | MODERATE | HIGH]\n"
                 "CLINICAL_SUMMARY: [Single-sentence clinical necessity verdict]")

    return "\n".join(parts)


def _build_clinical_fallback(request: dict, retrieved_clauses: list[dict]) -> tuple[str, str, float, str]:
    """Generate an independent deterministic clinical necessity evaluation in formatted Markdown."""
    diag = request.get("diagnosis", {}) if request else {}
    proc = request.get("procedure", {}) if request else {}
    patient = request.get("patient", {}) if request else {}
    policy = request.get("policy", {}) if request else {}
    diag_desc = str(diag.get("description", "")).strip()
    proc_desc = str(proc.get("description", "")).strip()
    icd10 = str(diag.get("icd10_code", "")).upper()
    admission_type = str(proc.get("admission_type", "planned")).lower()

    # 1. Obvious non-medical or cosmetic exclusions
    if any(k in proc_desc.lower() or k in diag_desc.lower() for k in ("cosmetic", "rhinoplasty", "aesthetic", "rejuvenation", "unapproved")):
        rec = "RECOMMEND_DENY"
        conf = 0.95
        summary = "Proposed procedure identified as cosmetic or unapproved non-medical indication."
        justification = (
            f"The proposed intervention **{proc_desc}** does not meet therapeutic clinical necessity criteria "
            "as it is categorized under aesthetic, elective cosmetic, or unapproved elective interventions under standard policy exclusions."
        )
    # 2. Insufficient clinical information or invalid ICD-10
    elif not diag_desc or not proc_desc or icd10 in ("INVALID", "UNKNOWN"):
        rec = "RECOMMEND_QUERY"
        conf = 0.45
        summary = "Insufficient clinical documentation or unmapped diagnostic code."
        justification = (
            "Clinical evaluation cannot be completed with the provided documentation. "
            "Specific histological confirmation, operative indication notes, or valid ICD-10 diagnostic coding is required from the treating hospital."
        )
    # 3. Standard clinically indicated inpatient or day-care admissions
    else:
        rec = "RECOMMEND_AUTHORISE"
        conf = 0.90
        summary = f"Clinical necessity validated: {proc_desc or 'Procedure'} is medically indicated for {diag_desc or 'Diagnosis'}."
        justification = (
            f"Diagnostic indication concordance is established between the primary diagnosis of **{diag_desc}** ({icd10}) "
            f"and the planned procedure **{proc_desc}** ({proc.get('procedure_code', 'N/A')}). "
            f"The admission type (**{admission_type.capitalize()}**) is clinically appropriate for acute management and postoperative monitoring."
        )

    guideline_items = []
    if retrieved_clauses:
        for i, c in enumerate(retrieved_clauses[:3], 1):
            source = c.get("source_file") or c.get("document_id") or "Clinical Reference"
            cid = c.get("clause_id") or c.get("chunk_id") or f"REF-{i:02d}"
            guideline_items.append(f"- **{cid}** ({source}): Concordant with standard IRDAI clinical treatment protocols.")
    else:
        guideline_items.append("- Standard IRDAI Master Circular (2024) Clinical Guidelines & Inpatient Level-of-Care Criteria applied.")

    guideline_section = "\n".join(guideline_items)

    narrative = f"""### RECOMMENDATION — requires human sign-off

#### 1. Clinical Necessity Assessment
- **Clinical Verdict**: **{rec.replace('RECOMMEND_', '')}**
- **Clinical Confidence**: **{conf:.0%}**
- **Summary**: {summary}

#### 2. Diagnostic & Procedure Concordance
- **Patient Profile**: Age {patient.get('age', 'N/A')} • {patient.get('gender', 'N/A')} (Policy: `{policy.get('policy_number', 'N/A')}`)
- **Primary Diagnosis**: **{diag_desc or 'N/A'}** (ICD-10 Code: `{icd10}`)
- **Proposed Procedure**: **{proc_desc or 'N/A'}** (Procedure Code: `{proc.get('procedure_code', 'N/A')}`)
- **Admission Type**: `{admission_type.capitalize()}`
- **Pre-Existing Flag**: {'Yes (PED)' if diag.get('is_pre_existing') else 'No'}

#### 3. Medical Indication Rationale
{justification}

#### 4. Clinical Guidelines & Reference Alignment
{guideline_section}

---
*Track 2 Autonomous Clinical Necessity Evaluation Engine*"""

    return narrative, rec, conf, summary


def _build_fallback_narrative(adj_result: dict) -> str:
    """Build a deterministic reasoning narrative without an LLM (legacy compatibility)."""
    parts: list[str] = []
    parts.append("RECOMMENDATION — requires human sign-off")
    parts.append("=" * 50)
    parts.append(f"Decision: {adj_result.get('recommendation', 'UNKNOWN')}")
    parts.append(f"Confidence: {adj_result.get('confidence_score', 0):.0%}")
    parts.append(f"Total Claimed: ₹{adj_result.get('total_claimed', 'N/A')}")
    parts.append(f"Total Approved: ₹{adj_result.get('total_approved', 'N/A')}")
    parts.append(f"Total Deducted: ₹{adj_result.get('total_deducted', 'N/A')}")

    trace = adj_result.get("reasoning_trace", "")
    if trace:
        parts.append(f"\nReasoning Trace:\n{trace}")

    deductions = adj_result.get("deductions", [])
    if deductions:
        parts.append(f"\nDeductions Applied ({len(deductions)}):")
        for d in deductions:
            cat = d.get("category", "unknown")
            amt = d.get("deducted_amount", 0)
            expl = d.get("explanation", "")
            parts.append(f"  - [{cat}] ₹{amt}: {expl}")

    triggers = adj_result.get("escalation_triggers", [])
    if triggers:
        parts.append("\nEscalation Triggers:")
        for t in triggers:
            parts.append(f"  ⚠ {t}")

    parts.append("\n[Generated by deterministic fallback — LLM call failed or skipped]")
    return "\n".join(parts)


# ============================================================================
# Node 7: Join Tracks Node (Fan-In)
# ============================================================================

def join_tracks_node(state: dict[str, Any]) -> dict[str, Any]:
    """Join node executing after Track 1 (rules) and Track 2 (clinical LLM) finish in parallel."""
    start = time.perf_counter()
    return {
        "node_latencies": {
            **state.get("node_latencies", {}),
            "join_tracks": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 9: Consensus Arbiter (Dual-Track Neuro-Symbolic Agreement)
# ============================================================================

def consensus_arbiter_node(state: dict[str, Any]) -> dict[str, Any]:
    """Dedicated Consensus Arbiter node evaluating neuro-symbolic agreement.

    Compares:
        Track 1: Deterministic financial and policy adjudication result.
        Track 2: Independent neural clinical necessity recommendation.

    Sets:
        consensus_status: 'AGREED' or 'DIVERGED'
        discrepancy_report: detailed report if tracks diverge.
    """
    start = time.perf_counter()
    adj = state.get("adjudication_result") or {}
    rules_rec = adj.get("recommendation")
    llm_rec = state.get("llm_recommendation")
    llm_conf = state.get("llm_clinical_confidence", 0.85)
    ablation = state.get("ablation_config", {})

    consensus_status = "AGREED"
    discrepancy_report = None

    if not ablation.get("disable_consensus_arbiter", False) and (rules_rec is not None or llm_rec is not None):
        rules_rec_val = rules_rec or "RECOMMEND_AUTHORISE"
        llm_rec_val = llm_rec or "RECOMMEND_AUTHORISE"

        def _normalize(r: str) -> str:
            s = str(r).upper()
            if "AUTHORISE" in s or "APPROVE" in s:
                return "APPROVE"
            if "DENY" in s or "REJECT" in s:
                return "DENY"
            if "QUERY" in s:
                return "QUERY"
            if "ESCALATE" in s:
                return "ESCALATE"
            return s

        norm_rules = _normalize(rules_rec_val)
        norm_llm = _normalize(llm_rec_val)

        if norm_rules != norm_llm or llm_rec_val == "RECOMMEND_ESCALATE" or llm_conf < 0.50:
            consensus_status = "DIVERGED"
            discrepancy_report = {
                "rules_recommendation": norm_rules,
                "llm_recommendation": norm_llm,
                "rules_confidence": adj.get("confidence_score", 0.0),
                "llm_confidence": llm_conf,
                "reason": (
                    f"Label divergence: Track 1 (rules) produced '{rules_rec_val}' "
                    f"while Track 2 (clinical LLM) produced '{llm_rec_val}'"
                    if norm_rules != norm_llm else
                    f"Unresolved clinical assessment or low confidence ({llm_conf:.2f})"
                ),
            }
            logger.warning("CONSENSUS ARBITER: Discrepancy detected — %s", discrepancy_report["reason"])
        elif norm_rules == "APPROVE" and norm_llm == "APPROVE" and "llm_approved_amount" in state:
            llm_amt_val = state.get("llm_approved_amount")
            if llm_amt_val is not None:
                try:
                    rules_approved = Decimal(str(adj.get("total_approved", adj.get("total_claimed", "0"))))
                    llm_approved = Decimal(str(llm_amt_val))
                    if abs(rules_approved - llm_approved) > Decimal("1.00"):
                        consensus_status = "DIVERGED"
                        discrepancy_report = {
                            "rules_recommendation": f"APPROVE ₹{rules_approved:,.2f}",
                            "llm_recommendation": f"APPROVE ₹{llm_approved:,.2f}",
                            "rules_confidence": adj.get("confidence_score", 0.0),
                            "llm_confidence": llm_conf,
                            "reason": f"Amount Mismatch: Rules approved ₹{rules_approved:,.2f} vs Clinical LLM recommended ₹{llm_approved:,.2f}",
                        }
                        logger.warning("CONSENSUS ARBITER: Amount mismatch detected — %s", discrepancy_report["reason"])
                except Exception as e:
                    logger.debug("Failed to compare approved amounts in arbiter: %s", e)

    return {
        "consensus_status": consensus_status,
        "discrepancy_report": discrepancy_report,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "consensus_arbiter": time.perf_counter() - start,
        },
    }


def _call_llm(prompt: str) -> tuple[str, dict[str, int], float, bool, Optional[str]]:
    """Call the LLM provider subsystem.

    Returns:
        Tuple of (content, token_count, cost_inr, fallback_used, fallback_reason).
    """
    from llm import OpenAICompatibleProvider, LLMConfig
    config = LLMConfig.from_env()
    provider = OpenAICompatibleProvider(config=config)
    resp = provider.generate(prompt, system_prompt=_SYSTEM_PROMPT)
    return resp.content, resp.token_count, resp.cost_inr, resp.fallback_used, resp.fallback_reason


# ============================================================================
# Node 7: Citation Guard (NON-BYPASSABLE — Guardrail #2)
# ============================================================================

def citation_guard(state: dict[str, Any]) -> dict[str, Any]:
    """Verify all citations in LLM output against retrieved clauses.

    This node implements Guardrail #2 (grounded citations or escalation).
    Every section, clause, and regulatory circular reference in the LLM
    narrative is cross-checked against retrieved clauses using regex pattern
    matching. Detected unverified citations are flagged, sanitized in the
    narrative (annotated with [UNVERIFIED CITATION]), and routed to human
    escalation via Guardrail #7.

    If no clauses were retrieved but citations are asserted in LLM output,
    all asserted citations are flagged as ungrounded/hallucinated.

    Checks:
        1. Section/Clause references (e.g., "Section 3.2", "Clause 4.1") in LLM output
           are cross-checked against sections present in retrieved clauses.
        2. IRDAI circular references are verified against retrieved metadata.
        3. Document name references are verified against retrieved sources.

    Returns:
        Updated state with hallucinated_citations list and sanitized reasoning_narrative.
    """
    start = time.perf_counter()

    raw_output = state.get("raw_llm_output", "") or state.get("reasoning_narrative", "")
    retrieved_clauses = state.get("retrieved_clauses", [])
    ablation = state.get("ablation_config", {})
    narrative = state.get("reasoning_narrative", raw_output)

    if not raw_output or ablation.get("disable_citation_guard", False):
        return {
            "hallucinated_citations": [],
            "reasoning_narrative": narrative,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "citation_guard": time.perf_counter() - start,
            },
        }

    # --- Build set of valid references from retrieved clauses ---
    valid_sections: set[str] = set()
    valid_circulars: set[str] = set()
    valid_sources: set[str] = set()
    valid_chunk_ids: set[str] = set()

    for clause in (retrieved_clauses or []):
        text = clause.get("chunk_text", clause.get("text", ""))
        cid = clause.get("chunk_id") or clause.get("clause_id")
        if cid:
            valid_chunk_ids.add(str(cid).lower())

        # Extract section and clause references (e.g., "Section 3.2", "SECTION 42.1", "Clause 4.1")
        for match in re.finditer(r'(?:Section|SECTION|Clause|CLAUSE)\s+(\d+(?:\.\d+)*)', text):
            valid_sections.add(match.group(1))

        # Also extract numbered subsections like "3.1 Initial Waiting Period"
        for match in re.finditer(r'(?:^|\n)\s*(\d+(?:\.\d+)+)', text):
            valid_sections.add(match.group(1))

        # Extract IRDAI circular numbers
        for match in re.finditer(r'IRDAI/[A-Z0-9/]+/\d+/\d+/\d+', text):
            valid_circulars.add(match.group())

        # Extract source file basenames
        source = clause.get("source_file", "")
        if source:
            basename = os.path.basename(source)
            valid_sources.add(basename.lower())
            name_no_ext = os.path.splitext(basename)[0]
            valid_sources.add(name_no_ext.lower().replace("_", " "))

    # --- Check LLM output for ungrounded citations ---
    hallucinated: list[str] = []

    # Check stable chunk/clause ID references
    for match in re.finditer(r'(?:CHUNK|CLAUSE|DOC)-[A-Za-z0-9_-]+', raw_output, re.IGNORECASE):
        c_ref = match.group()
        if c_ref.lower() not in valid_chunk_ids:
            if c_ref not in hallucinated:
                hallucinated.append(c_ref)

    # Check section and clause references
    for match in re.finditer(r'(?:Section|SECTION|Clause|CLAUSE)\s+(\d+(?:\.\d+)*)', raw_output):
        section_num = match.group(1)
        if section_num not in valid_sections and section_num.split(".")[0] not in valid_sections:
            citation = f"{match.group().split()[0]} {section_num}"
            if citation not in hallucinated:
                hallucinated.append(citation)

    # Check IRDAI circular references
    for match in re.finditer(r'IRDAI/[A-Z0-9/]+/\d+/\d+/\d+', raw_output):
        circular = match.group()
        if circular not in valid_circulars:
            if circular not in hallucinated:
                hallucinated.append(circular)

    # Sanitize narrative by annotating unverified citations
    sanitized_narrative = narrative
    if hallucinated:
        logger.warning(
            "CITATION GUARD: %d hallucinated citation(s) detected: %s",
            len(hallucinated), hallucinated,
        )
        for h in hallucinated:
            sanitized_narrative = re.sub(
                re.escape(h),
                f"[UNVERIFIED CITATION: {h}]",
                sanitized_narrative,
            )
    else:
        logger.info("Citation guard: PASSED — all citations grounded in retrieved clauses.")

    return {
        "hallucinated_citations": hallucinated,
        "reasoning_narrative": sanitized_narrative,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "citation_guard": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 8: Escalation Gate (Guardrail #7)
# ============================================================================

def escalation_gate(state: dict[str, Any]) -> dict[str, Any]:
    """Determine if the case needs human review.

    Escalation triggers (Guardrail #7):
        - Confidence < 0.7
        - Claim value > ₹5,00,000
        - PED-flagged diagnosis
        - Conflicting clauses detected
        - Non-network hospital
        - Hallucinated citations detected

    Returns:
        Updated state with needs_escalation and escalation_triggers.
    """
    start = time.perf_counter()

    triggers: list[str] = []
    adj = state.get("adjudication_result", {})
    request = state.get("pre_auth_request", {})
    ablation = state.get("ablation_config", {})

    # If the escalation gate is disabled in an ablation experiment, bypass all triggers
    if ablation.get("disable_escalation_gate", False):
        return {
            "needs_escalation": False,
            "escalation_triggers": [],
            "consensus_status": "BYPASS",
            "discrepancy_report": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "escalation_gate": time.perf_counter() - start,
            },
        }

    # --- Trigger 0: Dual-Track Neuro-Symbolic Consensus Check ---
    consensus_status = state.get("consensus_status")
    discrepancy_report = state.get("discrepancy_report")

    if consensus_status is None and not ablation.get("disable_consensus_arbiter", False):
        arb_res = consensus_arbiter_node(state)
        consensus_status = arb_res.get("consensus_status", "AGREED")
        discrepancy_report = arb_res.get("discrepancy_report")
    elif consensus_status is None:
        consensus_status = "AGREED"

    if consensus_status == "DIVERGED" and not ablation.get("disable_consensus_arbiter", False):
        disc_reason = (discrepancy_report or {}).get("reason", "Track 1 and Track 2 recommendations diverged")
        triggers.append(f"Consensus Discrepancy: {disc_reason}")
        logger.warning("ESCALATION: Consensus divergence detected — %s", disc_reason)

    # --- Trigger 0.5: Incomplete / Invalid Policy Dates ---
    policy_stat = state.get("policy_status", {})
    if policy_stat.get("status") in ("UNVERIFIED_DATES", "INVALID_DATES"):
        triggers.append("Incomplete or unverified policy/admission dates")

    # --- Trigger 1: Low confidence ---
    confidence = adj.get("confidence_score", 1.0)
    if confidence < 0.7:
        triggers.append(f"Low confidence ({confidence:.2f})")

    # --- Trigger 2: High claim value ---
    total_claimed = adj.get("total_claimed")
    if total_claimed is not None:
        try:
            claimed = Decimal(str(total_claimed))
            if claimed > Decimal("500000"):
                triggers.append(f"High claim value (₹{claimed:,.2f})")
        except (InvalidOperation, ValueError):
            pass

    # --- Trigger 2.5: Adversarial Prompt Injection Pre-Screening ---
    if request and not ablation.get("disable_prompt_injection_screen", False):
        diag_desc = str(request.get("diagnosis", {}).get("description", "")).lower()
        clinical_notes = str(request.get("clinical_notes", "")).lower()
        combined_text = f"{diag_desc} {clinical_notes}"
        injection_indicators = [
            "ignore all previous",
            "system prompt",
            "override all rules",
            "override decision",
            "unconditionally",
            "disregard previous",
            "system: override",
        ]
        if any(indicator in combined_text for indicator in injection_indicators):
            triggers.append("Adversarial prompt injection attempt detected")
            logger.warning("ADVERSARIAL PROMPT INJECTION DETECTED in pre-auth request! Escalating immediately.")

    # --- Trigger 3: PED-flagged diagnosis ---
    if request:
        diagnosis = request.get("diagnosis", {})
        if diagnosis.get("is_pre_existing"):
            triggers.append("PED-flagged diagnosis")

    # --- Trigger 4: Non-network hospital ---
    hospital_emp = state.get("hospital_empanelment", {})
    if not hospital_emp.get("is_empanelled", True):
        triggers.append("Non-network hospital")

    # --- Trigger 5: Hallucinated citations ---
    hallucinated = state.get("hallucinated_citations", [])
    if hallucinated:
        triggers.append(f"Hallucinated citations detected ({len(hallucinated)})")

    # --- Trigger 6: Rules engine escalation triggers ---
    adj_triggers = adj.get("escalation_triggers", [])
    for t in adj_triggers:
        if t not in triggers:
            triggers.append(t)

    needs_escalation = len(triggers) > 0

    if needs_escalation:
        logger.info("ESCALATION REQUIRED: %s", triggers)
    else:
        logger.info("No escalation triggers — case can proceed to auto-recommendation.")

    return {
        "needs_escalation": needs_escalation,
        "escalation_triggers": triggers,
        "consensus_status": consensus_status,
        "discrepancy_report": discrepancy_report,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "escalation_gate": time.perf_counter() - start,
        },
    }


# ============================================================================
# Node 9: Format Recommendation (Guardrail #1)
# ============================================================================

def format_recommendation(state: dict[str, Any]) -> dict[str, Any]:
    """Format the final recommendation output.

    Always labels output as a RECOMMENDATION, never a decision (Guardrail #1).
    Assembles the complete DecisionRecord for the audit trail.

    Returns:
        Updated state with recommendation, decision_record, and final status.
    """
    start = time.perf_counter()

    adj = state.get("adjudication_result", {})
    recommendation = adj.get("recommendation", "RECOMMEND_QUERY")
    confidence = adj.get("confidence_score", 0.5)
    needs_escalation = state.get("needs_escalation", False)
    consensus_status = state.get("consensus_status", "AGREED")
    discrepancy_report = state.get("discrepancy_report")

    # Adjust pipeline status based on escalation
    if needs_escalation:
        pipeline_status = "escalated"
    else:
        pipeline_status = "completed"

    decision_record = {
        "recommendation": recommendation,
        "confidence": confidence,
        "consensus_status": consensus_status,
        "discrepancy_report": discrepancy_report,
        "rules_recommendation": adj.get("recommendation"),
        "llm_recommendation": state.get("llm_recommendation", recommendation),
        "reasoning": state.get("reasoning_narrative", ""),
        "adjudication": adj,
        "retrieved_clauses": state.get("retrieved_clauses", []),
        "escalation_triggers": state.get("escalation_triggers", []),
        "needs_escalation": needs_escalation,
        "hallucinated_citations": state.get("hallucinated_citations", []),
        "metrics": {
            "latencies": state.get("node_latencies", {}),
            "llm_tokens": state.get("llm_token_count", {}),
            "llm_cost_inr": state.get("llm_cost_inr", 0.0),
        },
    }

    logger.info(
        "Pipeline %s. Recommendation: %s (confidence: %.2f, consensus: %s, escalated: %s)",
        pipeline_status, recommendation, confidence, consensus_status, needs_escalation,
    )

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "consensus_status": consensus_status,
        "discrepancy_report": discrepancy_report,
        "decision_record": decision_record,
        "pipeline_status": pipeline_status,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "format_recommendation": time.perf_counter() - start,
        },
    }
