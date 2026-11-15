"""
llm/response_parser.py
----------------------
Parsing utilities for extracting structured clinical assessments from LLM narrative outputs.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


def parse_clinical_tags(
    narrative: str,
    default_rec: str = "RECOMMEND_AUTHORISE",
    default_conf: float = 0.85,
) -> Tuple[str, float, str, Optional[Decimal], str]:
    """Parse structured tags from LLM clinical reasoning narrative.

    Expected tags:
        CLINICAL_RECOMMENDATION: [AUTHORISE | DENY | ESCALATE | QUERY]
        CLINICAL_APPROVED_AMOUNT: [Digits | SAME_AS_RULES | 0]
        CLINICAL_CONFIDENCE: [0.0 - 1.0]
        CLINICAL_SUMMARY: [Single sentence verdict]

    Returns:
        Tuple of (recommendation, confidence, summary, approved_amount, cleaned_narrative)
    """
    rec = default_rec
    conf = default_conf
    summary = "Clinical assessment aligns with medical indications."
    approved_amount: Optional[Decimal] = None

    if not narrative:
        return rec, conf, summary, approved_amount, narrative

    # 1. Recommendation tag
    rec_match = re.search(
        r'CLINICAL_RECOMMENDATION:\s*(AUTHORISE|APPROVE|DENY|REJECT|ESCALATE|QUERY)',
        narrative,
        re.IGNORECASE,
    )
    if rec_match:
        val = rec_match.group(1).upper()
        if val in ("AUTHORISE", "APPROVE"):
            rec = "RECOMMEND_AUTHORISE"
        elif val in ("DENY", "REJECT"):
            rec = "RECOMMEND_DENY"
        elif val == "QUERY":
            rec = "RECOMMEND_QUERY"
        elif val == "ESCALATE":
            rec = "RECOMMEND_QUERY"

    # 2. Confidence tag
    conf_match = re.search(r'CLINICAL_CONFIDENCE:\s*([0-9.]+)', narrative)
    if conf_match:
        try:
            parsed_conf = float(conf_match.group(1))
            conf = max(0.0, min(1.0, parsed_conf))
        except ValueError:
            pass

    # 3. Clinical summary tag
    sum_match = re.search(r'CLINICAL_SUMMARY:\s*(.+?)(?:\n|$)', narrative)
    if sum_match:
        summary = sum_match.group(1).strip()

    # 4. Approved amount tag
    amt_match = re.search(r'CLINICAL_APPROVED_AMOUNT:\s*([0-9,]+(?:\.[0-9]{2})?)', narrative, re.IGNORECASE)
    if amt_match:
        try:
            approved_amount = Decimal(amt_match.group(1).replace(",", ""))
        except (InvalidOperation, ValueError):
            pass

    # 5. Clean machine tags from displayed narrative
    cleaned = narrative
    cleaned = re.sub(r'\n*CLINICAL_RECOMMENDATION:.*', '', cleaned, flags=re.DOTALL).strip()
    cleaned = re.sub(r'\n*CLINICAL_APPROVED_AMOUNT:.*', '', cleaned, flags=re.DOTALL).strip()
    cleaned = re.sub(r'\n*CLINICAL_CONFIDENCE:.*', '', cleaned, flags=re.DOTALL).strip()
    cleaned = re.sub(r'\n*CLINICAL_SUMMARY:.*', '', cleaned, flags=re.DOTALL).strip()

    return rec, conf, summary, approved_amount, (cleaned if cleaned else narrative)
