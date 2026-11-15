"""
llm/health.py
-------------
Health check and diagnostic utilities for LLM provider subsystem.
"""

from __future__ import annotations

from typing import Any
from llm.config import LLMConfig
from llm.openai_provider import OpenAICompatibleProvider


def check_llm_health(config: LLMConfig | None = None) -> dict[str, Any]:
    """Run health diagnostic check against configured LLM provider."""
    provider = OpenAICompatibleProvider(config=config)
    return provider.check_health()
