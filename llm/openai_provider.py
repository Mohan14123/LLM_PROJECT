"""
llm/openai_provider.py
----------------------
OpenAI-compatible LLM provider with exponential backoff, jitter, circuit breaker,
and multi-mode execution semantics.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Optional

from orchestration.metrics import compute_cost_inr
from llm.base import BaseLLMProvider, LLMResponse
from llm.config import LLMConfig, LLMExecutionMode
from llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMModeViolationError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Reliable LLM Provider connecting to OpenAI or any OpenAI-compatible API (Groq, vLLM, OpenRouter)."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        self.config = config or LLMConfig.from_env()
        self._circuit_open_until = 0.0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 4
        self._circuit_cooldown_seconds = 60.0

    def _get_client(self):
        """Instantiate openai.OpenAI client."""
        if not self.config.api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError:
            raise LLMConfigurationError(
                "openai package is not installed. Install via pip install openai>=1.30.0"
            )

        kwargs: dict[str, Any] = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout_seconds,
        }
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url

        return OpenAI(**kwargs)

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        return time.time() < self._circuit_open_until

    def _record_success(self) -> None:
        """Record successful call and reset failure counters."""
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def _record_failure(self) -> None:
        """Record failure and trip circuit breaker if threshold is exceeded."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures:
            self._circuit_open_until = time.time() + self._circuit_cooldown_seconds
            logger.error(
                "Circuit breaker TRIPPED! LLM calls will be paused for %.1f seconds.",
                self._circuit_cooldown_seconds,
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate LLM response adhering to configured execution mode."""
        start_time = time.perf_counter()

        # 1. Handle FALLBACK_ONLY mode
        if self.config.execution_mode == LLMExecutionMode.FALLBACK_ONLY:
            logger.info("LLMExecutionMode is FALLBACK_ONLY. Skipping network call.")
            return LLMResponse(
                content="",
                token_count={"input_tokens": 0, "output_tokens": 0},
                cost_inr=0.0,
                latency_seconds=time.perf_counter() - start_time,
                model_name=self.config.model,
                provider="fallback",
                llm_mode="FALLBACK",
                fallback_used=True,
                fallback_reason="Execution mode explicitly set to FALLBACK_ONLY.",
            )

        # 2. Check circuit breaker
        if self._is_circuit_open():
            reason = f"Circuit breaker OPEN until {time.ctime(self._circuit_open_until)}."
            logger.warning(reason)
            if self.config.execution_mode == LLMExecutionMode.LIVE_REQUIRED:
                raise LLMModeViolationError(f"LIVE_REQUIRED failed: {reason}")
            return LLMResponse(
                content="",
                token_count={"input_tokens": 0, "output_tokens": 0},
                cost_inr=0.0,
                latency_seconds=time.perf_counter() - start_time,
                model_name=self.config.model,
                provider="circuit_breaker",
                llm_mode="CIRCUIT_OPEN",
                fallback_used=True,
                fallback_reason=reason,
            )

        # 3. Check API key presence
        if not self.config.api_key:
            reason = "OPENAI_API_KEY environment variable is missing."
            logger.warning(reason)
            if self.config.execution_mode == LLMExecutionMode.LIVE_REQUIRED:
                raise LLMModeViolationError(f"LIVE_REQUIRED failed: {reason}")
            return LLMResponse(
                content="",
                token_count={"input_tokens": 0, "output_tokens": 0},
                cost_inr=0.0,
                latency_seconds=time.perf_counter() - start_time,
                model_name=self.config.model,
                provider="deterministic_fallback",
                llm_mode="FALLBACK",
                fallback_used=True,
                fallback_reason=reason,
            )

        # 4. Attempt live API call with bounded retries and exponential backoff
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Optional[Exception] = None
        client = None

        try:
            client = self._get_client()
        except Exception as e:
            last_error = e
            self._record_failure()

        if client:
            model = kwargs.get("model", self.config.model)
            temperature = kwargs.get("temperature", self.config.temperature)
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            top_p = kwargs.get("top_p", self.config.top_p)

            for attempt in range(1, self.config.max_retries + 1):
                try:
                    logger.debug("Executing LLM call attempt %d/%d (model=%s)...", attempt, self.config.max_retries, model)
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                    )

                    self._record_success()
                    elapsed = time.perf_counter() - start_time

                    choice = response.choices[0]
                    content = choice.message.content or ""
                    reasoning = getattr(choice.message, "reasoning", None)

                    # For reasoning models that exhaust max_tokens in reasoning phase
                    if not content and reasoning:
                        logger.warning("LLM response content was empty but reasoning was present.")
                        content = f"[Reasoning Summary]: {reasoning[:500]}"

                    usage = response.usage
                    in_toks = usage.prompt_tokens if usage else 0
                    out_toks = usage.completion_tokens if usage else 0
                    cost = compute_cost_inr(in_toks, out_toks, model=model)

                    return LLMResponse(
                        content=content,
                        reasoning=reasoning,
                        token_count={"input_tokens": in_toks, "output_tokens": out_toks},
                        cost_inr=cost,
                        latency_seconds=elapsed,
                        model_name=model,
                        provider="openai_compatible",
                        llm_mode="LIVE",
                        fallback_used=False,
                        fallback_reason=None,
                    )

                except Exception as exc:
                    last_error = exc
                    self._record_failure()
                    logger.warning(
                        "LLM call attempt %d failed with error (%s: %s).",
                        attempt, type(exc).__name__, exc,
                    )

                    # Do not retry on authentication failure
                    if "401" in str(exc) or "authentication" in str(exc).lower():
                        break

                    # Exponential backoff with jitter
                    if attempt < self.config.max_retries:
                        backoff = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                        logger.info("Backing off for %.2fs before retrying...", backoff)
                        time.sleep(backoff)

        # 5. Handle post-retry failure
        elapsed = time.perf_counter() - start_time
        err_msg = f"{type(last_error).__name__}: {str(last_error)}" if last_error else "Unknown LLM error"

        if self.config.execution_mode == LLMExecutionMode.LIVE_REQUIRED:
            raise LLMModeViolationError(
                f"LIVE_REQUIRED failed after {self.config.max_retries} attempts: {err_msg}"
            )

        logger.error("Live LLM failed (%s). Falling back to deterministic narrative.", err_msg)
        return LLMResponse(
            content="",
            token_count={"input_tokens": 0, "output_tokens": 0},
            cost_inr=0.0,
            latency_seconds=elapsed,
            model_name=self.config.model,
            provider="fallback",
            llm_mode="FALLBACK",
            fallback_used=True,
            fallback_reason=err_msg,
        )

    def check_health(self) -> dict[str, Any]:
        """Perform active diagnostic check on configured endpoint and model."""
        start = time.perf_counter()
        try:
            client = self._get_client()
            models = client.models.list()
            model_ids = [m.id for m in models.data]
            configured_model_available = self.config.model in model_ids

            # Send minimal test prompt
            test_resp = client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            elapsed = time.perf_counter() - start

            return {
                "status": "healthy",
                "latency_seconds": elapsed,
                "configured_model": self.config.model,
                "configured_model_available": configured_model_available,
                "available_models_count": len(model_ids),
                "available_models_sample": model_ids[:10],
                "endpoint": self.config.base_url or "https://api.openai.com/v1",
                "execution_mode": self.config.execution_mode.value,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "latency_seconds": time.perf_counter() - start,
                "configured_model": self.config.model,
                "endpoint": self.config.base_url or "https://api.openai.com/v1",
                "execution_mode": self.config.execution_mode.value,
            }
