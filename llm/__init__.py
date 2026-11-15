"""
llm package
-----------
Production-grade LLM provider subsystem with multi-mode execution semantics,
exponential backoff, circuit breaking, and structured clinical evaluation parsing.
"""

from __future__ import annotations

from llm.base import BaseLLMProvider, LLMResponse
from llm.config import LLMConfig, LLMExecutionMode
from llm.exceptions import (
    LLMError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMModeViolationError,
    LLMResponseParseError,
)
from llm.health import check_llm_health
from llm.openai_provider import OpenAICompatibleProvider
from llm.response_parser import parse_clinical_tags

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMConfig",
    "LLMExecutionMode",
    "OpenAICompatibleProvider",
    "LLMError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMAuthenticationError",
    "LLMTimeoutError",
    "LLMModeViolationError",
    "LLMResponseParseError",
    "check_llm_health",
    "parse_clinical_tags",
]
