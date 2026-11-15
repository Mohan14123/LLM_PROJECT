"""
tests/test_llm_provider.py
--------------------------
Unit tests for the modular LLM provider subsystem, execution modes, circuit breaker,
and clinical response parsing.
"""

from __future__ import annotations

from decimal import Decimal
import pytest
from unittest.mock import MagicMock, patch

from llm import (
    LLMConfig,
    LLMExecutionMode,
    OpenAICompatibleProvider,
    LLMModeViolationError,
    parse_clinical_tags,
)


class TestLLMConfig:
    def test_default_config_loading(self):
        config = LLMConfig.from_env()
        assert config.temperature == 0.0
        assert config.max_retries >= 1
        assert config.execution_mode in (
            LLMExecutionMode.LIVE_REQUIRED,
            LLMExecutionMode.FALLBACK_ONLY,
            LLMExecutionMode.LIVE_WITH_FALLBACK,
        )

    def test_fallback_only_mode(self):
        config = LLMConfig(execution_mode=LLMExecutionMode.FALLBACK_ONLY)
        provider = OpenAICompatibleProvider(config=config)
        resp = provider.generate("test prompt")
        assert resp.fallback_used is True
        assert resp.llm_mode == "FALLBACK"
        assert resp.cost_inr == 0.0


class TestLLMExecutionModes:
    def test_live_required_raises_on_missing_api_key(self):
        config = LLMConfig(
            api_key=None,
            execution_mode=LLMExecutionMode.LIVE_REQUIRED,
        )
        provider = OpenAICompatibleProvider(config=config)
        with pytest.raises(LLMModeViolationError):
            provider.generate("test prompt")

    def test_live_with_fallback_substitutes_gracefully(self):
        config = LLMConfig(
            api_key=None,
            execution_mode=LLMExecutionMode.LIVE_WITH_FALLBACK,
        )
        provider = OpenAICompatibleProvider(config=config)
        resp = provider.generate("test prompt")
        assert resp.fallback_used is True
        assert resp.llm_mode == "FALLBACK"
        assert "missing" in (resp.fallback_reason or "").lower()

    def test_circuit_breaker_tripping(self):
        config = LLMConfig(
            api_key="mock-key",
            execution_mode=LLMExecutionMode.LIVE_WITH_FALLBACK,
            max_retries=1,
            timeout_seconds=1.0,
        )
        provider = OpenAICompatibleProvider(config=config)

        # Force consecutive failures
        with patch.object(provider, "_get_client", side_effect=Exception("Connection refused")):
            for _ in range(4):
                provider.generate("test prompt")

            # 5th call should encounter tripped circuit breaker
            resp = provider.generate("test prompt")
            assert resp.llm_mode == "CIRCUIT_OPEN"
            assert "Circuit breaker OPEN" in (resp.fallback_reason or "")


class TestClinicalResponseParser:
    def test_parses_standard_machine_tags(self):
        narrative = (
            "Clinical Assessment:\n"
            "The laparoscopic appendectomy is standard of care for acute appendicitis.\n\n"
            "CLINICAL_RECOMMENDATION: AUTHORISE\n"
            "CLINICAL_APPROVED_AMOUNT: 45000.00\n"
            "CLINICAL_CONFIDENCE: 0.95\n"
            "CLINICAL_SUMMARY: Procedure is medically indicated and necessary."
        )
        rec, conf, summary, amt, clean = parse_clinical_tags(narrative)
        assert rec == "RECOMMEND_AUTHORISE"
        assert conf == 0.95
        assert summary == "Procedure is medically indicated and necessary."
        assert amt == Decimal("45000.00")
        assert "CLINICAL_RECOMMENDATION" not in clean

    def test_handles_denial_and_query_tags(self):
        narrative = (
            "Clinical Assessment:\n"
            "Elective cosmetic rhinoplasty lacks functional clinical indication.\n\n"
            "CLINICAL_RECOMMENDATION: DENY\n"
            "CLINICAL_APPROVED_AMOUNT: 0\n"
            "CLINICAL_CONFIDENCE: 0.99\n"
            "CLINICAL_SUMMARY: Excluded cosmetic procedure."
        )
        rec, conf, summary, amt, clean = parse_clinical_tags(narrative)
        assert rec == "RECOMMEND_DENY"
        assert conf == 0.99
        assert amt == Decimal("0")
