"""
llm/config.py
-------------
Configuration models and execution modes for the LLM subsystem.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LLMExecutionMode(str, Enum):
    """Execution mode governing LLM interaction.

    LIVE_REQUIRED: Strict mode. Raises LLMModeViolationError if live LLM fails.
                   Guarantees zero silent fallback during benchmark evaluations.
    FALLBACK_ONLY: Offline mode. Uses deterministic fallback logic directly
                   without making network calls. Ideal for hermetic unit testing.
    LIVE_WITH_FALLBACK: Resilient mode. Attempts live LLM call with retries;
                        falls back to deterministic narrative only upon complete
                        failure, recording explicit fallback telemetry.
    """
    LIVE_REQUIRED = "LIVE_REQUIRED"
    FALLBACK_ONLY = "FALLBACK_ONLY"
    LIVE_WITH_FALLBACK = "LIVE_WITH_FALLBACK"


class LLMConfig(BaseModel):
    """Validated configuration for the LLM provider."""

    api_key: Optional[str] = Field(
        default=None,
        description="API key for OpenAI-compatible endpoint."
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for the provider (e.g. Groq, OpenRouter, OpenAI)."
    )
    model: str = Field(
        default="openai/gpt-oss-120b",
        description="Model identifier to request."
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 for deterministic evaluation)."
    )
    max_tokens: int = Field(
        default=1024,
        ge=64,
        le=8192,
        description="Maximum tokens in generated response."
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability."
    )
    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Request timeout in seconds."
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum bounded retries with exponential backoff."
    )
    execution_mode: LLMExecutionMode = Field(
        default=LLMExecutionMode.LIVE_WITH_FALLBACK,
        description="Operating execution mode."
    )

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables with sensible defaults."""
        mode_str = os.environ.get("LLM_EXECUTION_MODE", "LIVE_WITH_FALLBACK").upper()
        try:
            mode = LLMExecutionMode(mode_str)
        except ValueError:
            mode = LLMExecutionMode.LIVE_WITH_FALLBACK

        return cls(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
            model=os.environ.get("LLM_MODEL", "openai/gpt-oss-120b"),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "1024")),
            top_p=float(os.environ.get("LLM_TOP_P", "1.0")),
            timeout_seconds=float(os.environ.get("LLM_TIMEOUT", "30.0")),
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", "3")),
            execution_mode=mode,
        )
