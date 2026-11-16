"""
intake/pii_scrubber.py
----------------------
Data privacy and PII protection utilities. Redacts sensitive personal information
(Aadhaar numbers, phone numbers, email addresses) from log messages, external traces,
and plain-text audits to comply with the Digital Personal Data Protection (DPDP) Act, 2023.
"""

from __future__ import annotations

import logging
import re
from typing import Any

# Regex patterns for Indian identifiers
_AADHAAR_PATTERN = re.compile(r'\b(\d{4})[\s-](\d{4})[\s-](\d{4})\b|\b(\d{12})\b')
_PHONE_PATTERN = re.compile(r'\b(?:\+91[-\s]?)?([6-9]\d{9})\b')
_EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')


def scrub_pii(text: str) -> str:
    """Scrub sensitive PII identifiers from text."""
    if not isinstance(text, str):
        return text

    # Redact Aadhaar: retain only last 4 digits
    def _redact_aadhaar(match: re.Match) -> str:
        raw = match.group().replace(" ", "").replace("-", "")
        return f"XXXX-XXXX-{raw[-4:]}"

    # Redact Mobile: retain only last 3 digits
    def _redact_phone(match: re.Match) -> str:
        raw = match.group(1) if match.group(1) else match.group()
        return f"+91-XXXXX-{raw[-3:]}"

    scrubbed = _AADHAAR_PATTERN.sub(_redact_aadhaar, text)
    scrubbed = _PHONE_PATTERN.sub(_redact_phone, scrubbed)
    scrubbed = _EMAIL_PATTERN.sub("[EMAIL_REDACTED]", scrubbed)
    return scrubbed


class PIIRedactingFilter(logging.Filter):
    """Logging filter that scrubs PII from log record messages and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_pii(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: scrub_pii(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(scrub_pii(str(v)) if isinstance(v, str) else v for v in record.args)
        return True
