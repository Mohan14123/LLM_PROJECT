"""
llm/exceptions.py
-----------------
Custom exceptions for the LLM subsystem.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM errors."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is missing or invalid."""
    pass


class LLMConnectionError(LLMError):
    """Raised when the LLM endpoint is unreachable."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication with the LLM provider fails."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when the LLM call times out."""
    pass


class LLMModeViolationError(LLMError):
    """Raised when LIVE_REQUIRED is configured but live LLM call fails."""
    pass


class LLMResponseParseError(LLMError):
    """Raised when the LLM response cannot be parsed into expected structure."""
    pass
