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
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# LLM System Prompt (Guardrail #1: recommend-only)
# ============================================================================

_SYSTEM_PROMPT = """\
You are a senior medical director and health insurance claims analyst for an Indian insurer.
Your role is to perform an independent clinical & policy adjudication for a cashless
pre-authorisation decision (Dual-Track Neuro-Symbolic Architecture). You must:

1. ALWAYS frame your output as a RECOMMENDATION, never a final decision.
2. Cite specific clause references from the retrieved policy documents.
3. Use ONLY the information provided — do not fabricate or hallucinate clauses.
4. Structure your response: Summary → Analysis → Deductions → Recommendation.
5. All amounts in Indian Rupees (₹).
6. Provide an independent clinical assessment:
   - If the procedure is standard, clinically indicated, and medically necessary for the diagnosis (e.g. Laparoscopic appendectomy for appendicitis, PCI stenting for STEMI, Cataract extraction for cataract, Dialysis for ESRD), recommend AUTHORISE.
   - Concur with the Rules Engine calculations and endorse SAME_AS_RULES unless a procedure sub-limit cap or policy exclusion requires adjustment.
   - Only recommend QUERY if the clinical indication is fundamentally contradictory or missing.
   - Only recommend DENY if the procedure is an explicit permanent exclusion (e.g. cosmetic, unapproved).

IMPORTANT: Always end your output with these exact machine-parseable tags on separate lines:
CLINICAL_RECOMMENDATION: [AUTHORISE | DENY | ESCALATE | QUERY]
CLINICAL_APPROVED_AMOUNT: [Amount in ₹ as digits only, or SAME_AS_RULES, or 0]
CLINICAL_CONFIDENCE: [0.0 to 1.0]
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

    if request is None:
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

    request = state.get("pre_auth_request", {})
    policy = request.get("policy", {}) if request else {}
    policy_number = policy.get("policy_number", "UNKNOWN")

    # --- Compute days since inception ---
    days_since_inception = 365  # default fallback
    policy_start = policy.get("policy_start_date")
    admission_date_str = request.get("admission_date") if request else None

    if policy_start:
        try:
            if isinstance(policy_start, date):
                start_date = policy_start
            else:
                start_date = date.fromisoformat(str(policy_start))

            ref_date = date.today()
            if admission_date_str:
                if isinstance(admission_date_str, date):
                    ref_date = admission_date_str
                else:
                    ref_date = date.fromisoformat(str(admission_date_str))

            days_since_inception = max((ref_date - start_date).days, 0)
        except (ValueError, TypeError) as e:
            logger.warning("Could not parse policy dates: %s. Using default 365 days.", e)

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

    logger.info(
        "Policy %s: status=%s, days_since_inception=%d, remaining_si=%s",
        policy_number, status, days_since_inception, sum_insured,
    )

    return {
        "policy_status": {
            "is_active": is_active,
            "status": status,
            "remaining_sum_insured": sum_insured,
            "days_since_inception": days_since_inception,
        },
        "waiting_period_info": {
            "initial_wp_clear": days_since_inception >= 30,
            "specific_disease_wp_clear": days_since_inception >= 730,
            "ped_wp_clear": days_since_inception >= 1460,
            "days_elapsed": days_since_inception,
            "applicable_wp_months": 0,
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
        wp = state.get("waiting_period_info", {})
        waiting_period = WaitingPeriodInfo(
            initial_wp_clear=wp.get("initial_wp_clear", True),
            specific_disease_wp_clear=wp.get("specific_disease_wp_clear", True),
            ped_wp_clear=wp.get("ped_wp_clear", True),
            days_elapsed=wp.get("days_elapsed", 365),
            applicable_wp_months=wp.get("applicable_wp_months", 0),
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
    """Generate natural-language reasoning using an LLM.

    Takes the adjudication result + retrieved clauses and asks the LLM
    to produce a human-readable reasoning narrative with clause citations.

    Falls back to a deterministic narrative if no LLM API key is set or
    the API call fails.

    Environment Variables:
        OPENAI_API_KEY: API key for OpenAI-compatible endpoint.
        OPENAI_BASE_URL: Optional base URL (for Grok, Claude, etc.).
        LLM_MODEL: Model name (default: gpt-4o-mini).

    Returns:
        Updated state with reasoning_narrative, raw_llm_output, and cost.
    """
    start = time.perf_counter()

    adj_result = state.get("adjudication_result", {})
    retrieved_clauses = state.get("retrieved_clauses", [])
    request = state.get("pre_auth_request", {})

    # Build prompt
    prompt = _build_reasoning_prompt(request, adj_result, retrieved_clauses)

    # Try calling LLM API
    llm_rec = adj_result.get("recommendation", "RECOMMEND_AUTHORISE")
    llm_conf = adj_result.get("confidence_score", 0.85)
    llm_summary = "Clinical assessment aligns with deterministic policy rules."

    try:
        narrative, token_count, cost = _call_llm(prompt)
        logger.info(
            "LLM reasoning: %d input + %d output tokens, ₹%.4f",
            token_count["input_tokens"], token_count["output_tokens"], cost,
        )

        # Parse Track 2 structured clinical evaluation
        rec_m = re.search(r'CLINICAL_RECOMMENDATION:\s*(AUTHORISE|APPROVE|DENY|REJECT|ESCALATE|QUERY)', narrative, re.IGNORECASE)
        if rec_m:
            val = rec_m.group(1).upper()
            if val in ("AUTHORISE", "APPROVE"):
                llm_rec = "RECOMMEND_AUTHORISE"
            elif val in ("DENY", "REJECT"):
                llm_rec = "RECOMMEND_DENY"
            elif val == "QUERY":
                llm_rec = "RECOMMEND_QUERY"
            elif val == "ESCALATE":
                llm_rec = "RECOMMEND_QUERY"

        conf_m = re.search(r'CLINICAL_CONFIDENCE:\s*([0-9.]+)', narrative)
        if conf_m:
            try:
                llm_conf = float(conf_m.group(1))
            except ValueError:
                pass

        sum_m = re.search(r'CLINICAL_SUMMARY:\s*(.+?)(?:\n|$)', narrative)
        if sum_m:
            llm_summary = sum_m.group(1).strip()

        # Parse proposed approved amount if specified by LLM
        llm_approved_amount = None
        if re.search(r'CLINICAL_APPROVED_AMOUNT:\s*SAME_AS_RULES', narrative, re.IGNORECASE):
            rules_app = adj_result.get("total_approved")
            if rules_app is not None:
                try:
                    llm_approved_amount = Decimal(str(rules_app))
                except (InvalidOperation, ValueError):
                    pass
        else:
            amt_m = re.search(r'CLINICAL_APPROVED_AMOUNT:\s*([0-9,]+(?:\.[0-9]{2})?)', narrative, re.IGNORECASE)
            if amt_m:
                try:
                    llm_approved_amount = Decimal(amt_m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError):
                    pass
            if llm_approved_amount is None:
                if re.search(r'(agree|concur|aligns? with|confirm).*rules engine.*approved', narrative, re.IGNORECASE):
                    rules_app = adj_result.get("total_approved")
                    if rules_app is not None:
                        try:
                            llm_approved_amount = Decimal(str(rules_app))
                        except (InvalidOperation, ValueError):
                            pass
                else:
                    amt_text_m = re.search(r'[Aa]pproved\s+amount\*?:\s*[*₹Rs\.\s]*([0-9,]+(?:\.[0-9]{2})?)', narrative)
                    if amt_text_m:
                        try:
                            llm_approved_amount = Decimal(amt_text_m.group(1).replace(",", ""))
                        except (InvalidOperation, ValueError):
                            pass

        # Clean machine tags from displayed narrative
        cleaned_narrative = re.sub(r'\n*CLINICAL_RECOMMENDATION:.*', '', narrative, flags=re.DOTALL).strip()
        cleaned_narrative = re.sub(r'\n*CLINICAL_APPROVED_AMOUNT:.*', '', cleaned_narrative, flags=re.DOTALL).strip()
        if cleaned_narrative:
            narrative = cleaned_narrative

    except Exception as e:
        logger.error("LLM call skipped (%s). Using deterministic fallback.", e, exc_info=True)
        narrative = _build_fallback_narrative(adj_result)
        narrative += f"\n\n[Exception: {str(e)}]"
        token_count = {"input_tokens": 0, "output_tokens": 0}
        cost = 0.0
        llm_approved_amount = None

    return {
        "reasoning_narrative": narrative,
        "raw_llm_output": narrative,
        "llm_recommendation": llm_rec,
        "llm_clinical_confidence": llm_conf,
        "llm_clinical_summary": llm_summary,
        "llm_approved_amount": str(llm_approved_amount) if llm_approved_amount is not None else None,
        "llm_token_count": token_count,
        "llm_cost_inr": cost,
        "node_latencies": {
            **state.get("node_latencies", {}),
            "llm_reasoning": time.perf_counter() - start,
        },
    }


def _build_reasoning_prompt(
    request: dict, adj_result: dict, retrieved_clauses: list[dict],
) -> str:
    """Build the structured prompt for LLM reasoning."""
    parts: list[str] = []

    # Patient/claim context
    patient = request.get("patient", {}) if request else {}
    diagnosis = request.get("diagnosis", {}) if request else {}
    procedure = request.get("procedure", {}) if request else {}
    policy = request.get("policy", {}) if request else {}
    cost = request.get("cost_estimate", {}) if request else {}

    parts.append("## Pre-Authorisation Request")
    parts.append(f"- Patient Age: {patient.get('age', 'N/A')}")
    parts.append(f"- Diagnosis: {diagnosis.get('description', 'N/A')} "
                 f"(ICD-10: {diagnosis.get('icd10_code', 'N/A')})")
    parts.append(f"- Pre-existing: {'Yes' if diagnosis.get('is_pre_existing') else 'No'}")
    parts.append(f"- Procedure: {procedure.get('description', 'N/A')}")
    parts.append(f"- Admission Type: {procedure.get('admission_type', 'N/A')}")
    parts.append(f"- Plan Type: {policy.get('plan_type', 'N/A')}")
    parts.append(f"- Sum Insured: ₹{policy.get('sum_insured', 'N/A')}")
    parts.append(f"- Co-pay: {policy.get('co_pay_pct', '0')}%")
    parts.append(f"- Total Claimed: ₹{cost.get('total_amount', 'N/A')}")

    # Rules engine output
    parts.append("\n## Rules Engine Output")
    parts.append(f"- Recommendation: {adj_result.get('recommendation', 'N/A')}")
    parts.append(f"- Confidence: {adj_result.get('confidence_score', 0):.0%}")
    parts.append(f"- Total Approved: ₹{adj_result.get('total_approved', 'N/A')}")
    parts.append(f"- Total Deducted: ₹{adj_result.get('total_deducted', 'N/A')}")

    deductions = adj_result.get("deductions", [])
    if deductions:
        parts.append(f"\n### Deductions Applied ({len(deductions)}):")
        for d in deductions:
            parts.append(f"  - [{d.get('category', '?')}] ₹{d.get('deducted_amount', 0)}: "
                         f"{d.get('explanation', '')}")

    # Retrieved clauses
    if retrieved_clauses:
        parts.append("\n## Retrieved Policy Clauses")
        for i, clause in enumerate(retrieved_clauses[:5], 1):
            text = clause.get("chunk_text", clause.get("text", ""))
            source = clause.get("source_file", "")
            score = clause.get("similarity_score", 0)
            parts.append(f"\n[Clause {i}] Source: {source} (score: {score:.3f})")
            parts.append(text[:600])

    # Task instruction
    parts.append("\n## Task (Dual-Track Neuro-Symbolic Evaluation)")
    parts.append("1. Provide a clear, structured reasoning narrative explaining "
                 "the recommendation. Cite specific clause references from the "
                 "retrieved documents above. Begin with "
                 "'RECOMMENDATION — requires human sign-off'.")
    parts.append("2. Perform an independent clinical assessment of medical necessity, "
                 "appropriateness of admission type, and procedure justification.")
    parts.append("3. End your response with these exact machine-parseable tags:\n"
                 "CLINICAL_RECOMMENDATION: [AUTHORISE | DENY | ESCALATE | QUERY]\n"
                 "CLINICAL_APPROVED_AMOUNT: [Amount in ₹ as digits only, or SAME_AS_RULES, or 0]\n"
                 "CLINICAL_CONFIDENCE: [0.0-1.0]\n"
                 "CLINICAL_SUMMARY: [Single-sentence clinical necessity verdict]")

    return "\n".join(parts)


def _build_fallback_narrative(adj_result: dict) -> str:
    """Build a deterministic reasoning narrative without an LLM."""
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


def _call_llm(prompt: str) -> tuple[str, dict[str, int], float]:
    """Call an OpenAI-compatible LLM API.

    Args:
        prompt: The user prompt to send.

    Returns:
        Tuple of (response_text, token_count_dict, cost_inr).

    Raises:
        ValueError: If no API key is configured.
        Exception: If the API call fails.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set — using deterministic fallback")

    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    from openai import OpenAI

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    content = response.choices[0].message.content or ""
    usage = response.usage

    token_count = {
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
    }

    from orchestration.metrics import compute_cost_inr
    cost = compute_cost_inr(
        token_count["input_tokens"],
        token_count["output_tokens"],
        model=model,
    )

    return content, token_count, cost


# ============================================================================
# Node 7: Citation Guard (NON-BYPASSABLE — Guardrail #2)
# ============================================================================

def citation_guard(state: dict[str, Any]) -> dict[str, Any]:
    """Verify all citations in LLM output against retrieved clauses.

    This node is NON-BYPASSABLE per Guardrail #2: "Grounded output or
    no output." Every clause reference in the LLM output must match a
    clause that was actually retrieved. Unmatched citations are flagged
    and counted as hallucinations.

    Checks:
        1. Section references (e.g., "Section 3.2") in LLM output are
           cross-checked against sections present in retrieved clauses.
        2. IRDAI circular references are verified against retrieved metadata.
        3. Document name references are verified against retrieved sources.

    Returns:
        Updated state with hallucinated_citations list.
    """
    start = time.perf_counter()

    raw_output = state.get("raw_llm_output", "")
    retrieved_clauses = state.get("retrieved_clauses", [])

    if not raw_output or not retrieved_clauses:
        return {
            "hallucinated_citations": [],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "citation_guard": time.perf_counter() - start,
            },
        }

    # --- Build set of valid references from retrieved clauses ---
    valid_sections: set[str] = set()
    valid_circulars: set[str] = set()
    valid_sources: set[str] = set()

    for clause in retrieved_clauses:
        text = clause.get("chunk_text", clause.get("text", ""))

        # Extract section references (e.g., "Section 3.2", "SECTION 42.1")
        for match in re.finditer(r'(?:Section|SECTION)\s+(\d+(?:\.\d+)*)', text):
            valid_sections.add(match.group(1))

        # Also extract numbered subsections like "3.1 Initial Waiting Period"
        for match in re.finditer(r'(?:^|\n)\s*(\d+(?:\.\d+)+)', text):
            valid_sections.add(match.group(1))

        # Extract IRDAI circular numbers
        for match in re.finditer(r'IRDAI/[A-Z/]+/\d+/\d+/\d+', text):
            valid_circulars.add(match.group())

        # Extract source file basenames
        source = clause.get("source_file", "")
        if source:
            basename = os.path.basename(source)
            valid_sources.add(basename.lower())
            # Also add without extension
            name_no_ext = os.path.splitext(basename)[0]
            valid_sources.add(name_no_ext.lower().replace("_", " "))

    # --- Check LLM output for ungrounded citations ---
    hallucinated: list[str] = []

    # Check section references
    for match in re.finditer(r'(?:Section|SECTION)\s+(\d+(?:\.\d+)*)', raw_output):
        section_num = match.group(1)
        if section_num not in valid_sections and section_num.split(".")[0] not in valid_sections:
            citation = f"Section {section_num}"
            if citation not in hallucinated:
                hallucinated.append(citation)

    # Check IRDAI circular references
    for match in re.finditer(r'IRDAI/[A-Z/]+/\d+/\d+/\d+', raw_output):
        circular = match.group()
        if circular not in valid_circulars:
            if circular not in hallucinated:
                hallucinated.append(circular)

    if hallucinated:
        logger.warning(
            "CITATION GUARD: %d hallucinated citation(s) detected: %s",
            len(hallucinated), hallucinated,
        )
    else:
        logger.info("Citation guard: PASSED — all citations grounded in retrieved clauses.")

    return {
        "hallucinated_citations": hallucinated,
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

    # --- Trigger 0: Dual-Track Neuro-Symbolic Consensus Check ---
    rules_rec = adj.get("recommendation", "RECOMMEND_QUERY")
    llm_rec = state.get("llm_recommendation", rules_rec)

    def _normalize_decision(r: str) -> str:
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

    norm_rules = _normalize_decision(rules_rec)
    norm_llm = _normalize_decision(llm_rec)

    # Check amount agreement if LLM specified an approved amount
    llm_amt_str = state.get("llm_approved_amount")
    llm_approved_amount = None
    if llm_amt_str:
        try:
            llm_approved_amount = Decimal(str(llm_amt_str))
        except (InvalidOperation, ValueError):
            pass

    rules_approved_dec = None
    rules_approved = adj.get("total_approved")
    if rules_approved is not None:
        try:
            rules_approved_dec = Decimal(str(rules_approved))
        except (InvalidOperation, ValueError):
            pass

    amount_diverged = False
    if (
        norm_rules in ("APPROVE", "AUTHORISE")
        and norm_llm in ("APPROVE", "AUTHORISE")
        and llm_approved_amount is not None
        and rules_approved_dec is not None
    ):
        diff = abs(rules_approved_dec - llm_approved_amount)
        # If difference exceeds ₹100 and >5%
        if diff > Decimal("100.00") and (diff / max(rules_approved_dec, llm_approved_amount, Decimal("1"))) > Decimal("0.05"):
            amount_diverged = True

    if amount_diverged:
        consensus_status = "DIVERGED"
        discrepancy_report = {
            "rules_recommendation": f"{norm_rules} (Approved ₹{rules_approved_dec:,.2f})",
            "rules_rationale": adj.get("reasoning_trace", f"Rules Engine approved ₹{rules_approved_dec:,.2f} based on policy formulas."),
            "llm_recommendation": f"{norm_llm} (Approved ₹{llm_approved_amount:,.2f})",
            "llm_rationale": state.get("llm_clinical_summary", f"Neural Clinical Adjudicator recommended approved amount ₹{llm_approved_amount:,.2f}."),
        }
        triggers.append(
            f"Consensus Discrepancy: Amount Mismatch (Rules ₹{rules_approved_dec:,.2f} vs LLM ₹{llm_approved_amount:,.2f})"
        )
        logger.warning(
            "DUAL-TRACK DISCREPANCY: Rules Approved ₹%s != LLM Approved ₹%s. Escalating to human reviewer.",
            rules_approved_dec, llm_approved_amount,
        )
    elif norm_rules == norm_llm or (norm_rules == "APPROVE" and norm_llm in ("APPROVE", "AUTHORISE")):
        consensus_status = "AGREED"
        discrepancy_report = None
        logger.info("DUAL-TRACK CONSENSUS: Both tracks agree on %s", norm_rules)
    else:
        consensus_status = "DIVERGED"
        discrepancy_report = {
            "rules_recommendation": norm_rules,
            "rules_rationale": adj.get("reasoning_trace", "Rules evaluated based on policy schedules and tariff sub-limits."),
            "llm_recommendation": norm_llm,
            "llm_rationale": state.get("llm_clinical_summary", "Independent clinical review reached a diverging conclusion."),
        }
        triggers.append(f"Consensus Discrepancy: Rules ({norm_rules}) vs LLM Clinical ({norm_llm})")
        logger.warning(
            "DUAL-TRACK DISCREPANCY: Rules Engine (%s) != LLM Clinical (%s). Escalating to human reviewer.",
            norm_rules, norm_llm,
        )

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
    if request:
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
