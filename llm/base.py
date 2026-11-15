"""
llm/base.py
-----------
Abstract base classes and contracts for LLM providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    content: str = Field(..., description="Assistant text response.")
    reasoning: Optional[str] = Field(default=None, description="Reasoning trace if returned by reasoning model.")
    token_count: dict[str, int] = Field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0},
        description="Input and output token count."
    )
    cost_inr: float = Field(default=0.0, description="Estimated cost in INR.")
    latency_seconds: float = Field(default=0.0, description="End-to-end call latency in seconds.")
    model_name: str = Field(..., description="Model name executed.")
    provider: str = Field(default="openai_compatible", description="Provider identifier.")
    llm_mode: str = Field(default="LIVE", description="Execution mode: LIVE, FALLBACK, or ERROR.")
    fallback_used: bool = Field(default=False, description="Whether fallback narrative was substituted.")
    fallback_reason: Optional[str] = Field(default=None, description="Reason for fallback if used.")


class BaseLLMProvider(ABC):
    """Abstract interface for LLM client providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate a response for the given user prompt.

        Args:
            prompt: User prompt content.
            system_prompt: Optional system instruction.
            **kwargs: Dynamic overrides for model parameters.

        Returns:
            LLMResponse object.
        """
        pass

    @abstractmethod
    def check_health(self) -> dict[str, Any]:
        """Verify endpoint connectivity, authentication, and model availability.

        Returns:
            Dict containing status ('ok', 'error'), available models, and latency.
        """
        pass
