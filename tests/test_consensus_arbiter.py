"""
tests/test_consensus_arbiter.py
--------------------------------
Unit tests for the Dual-Track Neuro-Symbolic Consensus Architecture.

Verifies:
1. Unanimous Agreement: Track 1 (Symbolic) == Track 2 (Neural) -> AGREED, no discrepancy trigger.
2. Discrepancy Escalation: Track 1 != Track 2 -> DIVERGED, triggers human review escalation.
"""

from orchestration.nodes import escalation_gate, format_recommendation


def test_consensus_unanimous_agreement():
    """When deterministic rules and LLM clinical evaluation agree, consensus is reached."""
    state = {
        "adjudication_result": {
            "recommendation": "RECOMMEND_AUTHORISE",
            "confidence_score": 0.90,
            "total_claimed": "50000.00",
            "reasoning_trace": "All policy rules satisfied.",
            "escalation_triggers": [],
        },
        "llm_recommendation": "RECOMMEND_AUTHORISE",
        "llm_clinical_summary": "Emergency procedure is medically justified.",
        "pre_auth_request": {
            "diagnosis": {"is_pre_existing": False},
        },
        "hospital_empanelment": {"is_empanelled": True},
        "hallucinated_citations": [],
    }

    gate_out = escalation_gate(state)
    assert gate_out["consensus_status"] == "AGREED"
    assert gate_out["discrepancy_report"] is None
    assert gate_out["needs_escalation"] is False

    final_state = {**state, **gate_out}
    fmt_out = format_recommendation(final_state)
    assert fmt_out["consensus_status"] == "AGREED"
    assert fmt_out["pipeline_status"] == "completed"


def test_consensus_discrepancy_escalation():
    """When deterministic rules and LLM clinical evaluation diverge, automatic escalation is triggered."""
    state = {
        "adjudication_result": {
            "recommendation": "RECOMMEND_AUTHORISE",
            "confidence_score": 0.85,
            "total_claimed": "45000.00",
            "reasoning_trace": "Rules indicate claim is payable under sum insured.",
            "escalation_triggers": [],
        },
        # LLM flags clinical mismatch / upcoding / denial
        "llm_recommendation": "RECOMMEND_DENY",
        "llm_clinical_summary": "Hospitalization not medically necessary for this minor non-emergency symptom.",
        "pre_auth_request": {
            "diagnosis": {"is_pre_existing": False},
        },
        "hospital_empanelment": {"is_empanelled": True},
        "hallucinated_citations": [],
    }

    gate_out = escalation_gate(state)
    assert gate_out["consensus_status"] == "DIVERGED"
    assert gate_out["needs_escalation"] is True
    assert gate_out["discrepancy_report"] is not None
    assert gate_out["discrepancy_report"]["rules_recommendation"] == "APPROVE"
    assert gate_out["discrepancy_report"]["llm_recommendation"] == "DENY"
    assert any("Consensus Discrepancy" in t for t in gate_out["escalation_triggers"])

    final_state = {**state, **gate_out}
    fmt_out = format_recommendation(final_state)
    assert fmt_out["consensus_status"] == "DIVERGED"
    assert fmt_out["pipeline_status"] == "escalated"


def test_consensus_amount_mismatch_escalation():
    """When both tracks nominally recommend APPROVE but differ on approved amount, consensus diverges."""
    state = {
        "adjudication_result": {
            "recommendation": "RECOMMEND_AUTHORISE",
            "confidence_score": 0.85,
            "total_claimed": "29921.00",
            "total_approved": "29921.00",
            "reasoning_trace": "Rules approved 100%.",
            "escalation_triggers": [],
        },
        "llm_recommendation": "RECOMMEND_AUTHORISE",
        "llm_approved_amount": "2000.00",
        "llm_clinical_summary": "Hemodialysis capped at ₹2,000 per session under Clause 2.1.",
        "pre_auth_request": {
            "diagnosis": {"is_pre_existing": False},
        },
        "hospital_empanelment": {"is_empanelled": True},
        "hallucinated_citations": [],
    }

    gate_out = escalation_gate(state)
    assert gate_out["consensus_status"] == "DIVERGED"
    assert gate_out["needs_escalation"] is True
    assert gate_out["discrepancy_report"] is not None
    assert "₹29,921.00" in gate_out["discrepancy_report"]["rules_recommendation"]
    assert "₹2,000.00" in gate_out["discrepancy_report"]["llm_recommendation"]
    assert any("Amount Mismatch" in t for t in gate_out["escalation_triggers"])

