#!/usr/bin/env python3
"""
scripts/check_llm_connection.py
-------------------------------
Diagnostic utility to smoke-test LLM connectivity, verify API key authentication,
inspect available models, and validate live response generation.

Usage:
    python scripts/check_llm_connection.py
"""

import sys
import os
import json
import time

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from llm import LLMConfig, OpenAICompatibleProvider, check_llm_health


def main():
    print("=" * 65)
    print("       A1 CASHLESS PRE-AUTH: LLM CONNECTIVITY SMOKE TEST")
    print("=" * 65)

    config = LLMConfig.from_env()
    print(f"Provider Endpoint : {config.base_url or 'https://api.openai.com/v1'}")
    print(f"Configured Model  : {config.model}")
    print(f"Execution Mode    : {config.execution_mode.value}")
    print(f"Max Retries       : {config.max_retries}")
    print(f"Timeout (s)       : {config.timeout_seconds}")
    key_display = f"{config.api_key[:8]}...{config.api_key[-4:]}" if config.api_key and len(config.api_key) > 12 else ("SET" if config.api_key else "NOT SET")
    print(f"API Key Status    : {key_display}")
    print("-" * 65)

    # 1. Diagnostic health check
    print("[*] Running provider health check...")
    health = check_llm_health(config)
    print(f"  Health Status : {health.get('status').upper()}")
    print(f"  Latency       : {health.get('latency_seconds', 0):.3f}s")

    if health.get("status") == "healthy":
        print(f"  Models Count  : {health.get('available_models_count', 0)}")
        print(f"  Target Model Available: {'YES' if health.get('configured_model_available') else 'NO'}")
        sample = health.get("available_models_sample", [])
        if sample:
            print("  Available Models Sample:")
            for m in sample[:6]:
                print(f"    - {m}")
    else:
        print(f"  [!] Diagnostic Error: {health.get('error_type')} - {health.get('error_message')}")
        print("\nRecommendations:")
        print("  1. Check if OPENAI_API_KEY in .env is valid.")
        print("  2. Verify OPENAI_BASE_URL corresponds to your key provider.")
        print("  3. Ensure LLM_MODEL matches an allowed model for your provider.")
        sys.exit(1)

    # 2. Test generation with structured tags
    print("\n[*] Testing live clinical generation prompt...")
    provider = OpenAICompatibleProvider(config=config)
    test_prompt = (
        "Pre-Auth Request: 45M diagnosed with Acute Appendicitis (ICD-10: K35.8). "
        "Planned procedure: Emergency Laparoscopic Appendectomy. "
        "Estimated cost: Rs 65,000. Sum insured: Rs 5,00,000. Network tier: cashless_network.\n"
        "Evaluate medical necessity and provide structured recommendation tags."
    )
    system_prompt = (
        "You are a clinical reviewer. End your response with:\n"
        "CLINICAL_RECOMMENDATION: [AUTHORISE | DENY | QUERY]\n"
        "CLINICAL_APPROVED_AMOUNT: [Amount in digits]\n"
        "CLINICAL_CONFIDENCE: [0.0 - 1.0]\n"
        "CLINICAL_SUMMARY: [Single sentence verdict]"
    )

    t0 = time.perf_counter()
    resp = provider.generate(test_prompt, system_prompt=system_prompt)
    elapsed = time.perf_counter() - t0

    print(f"  Call Duration : {elapsed:.3f}s")
    print(f"  Execution Mode: {resp.llm_mode}")
    print(f"  Fallback Used : {resp.fallback_used}")
    print(f"  Input Tokens  : {resp.token_count.get('input_tokens')}")
    print(f"  Output Tokens : {resp.token_count.get('output_tokens')}")
    print(f"  Cost Estimate : Rs {resp.cost_inr:.4f}")

    print("\n[-] Generated Narrative Preview:")
    preview = resp.content[:400] + ("..." if len(resp.content) > 400 else "")
    print(preview)

    if resp.reasoning:
        print("\n[-] Reasoning Trace Preview:")
        r_preview = resp.reasoning[:300] + ("..." if len(resp.reasoning) > 300 else "")
        print(r_preview)

    print("\n" + "=" * 65)
    print("       RESULT: LLM CONNECTIVITY SMOKE TEST PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    main()
