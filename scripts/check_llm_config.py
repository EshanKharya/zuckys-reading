#!/usr/bin/env python3
"""
Test script to verify LLM connection and configuration for Zucky's Reading.
Sends a test 'hello' message and reports connection status, latency, and model output.
"""
import sys
import os
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from src.llm import get_llm_client

def main():
    print("=" * 60)
    print("  ZUCKY'S READING - LLM CONFIGURATION & CONNECTIVITY CHECK")
    print("=" * 60)
    print(f"[*] Provider       : {config.LLM_PROVIDER}")
    print(f"[*] Model Name     : {config.MODEL_NAME}")
    print(f"[*] Ollama Base URL: {config.OLLAMA_BASE_URL}")
    print(f"[*] Temperature    : {config.MODEL_TEMPERATURE}")
    print(f"[*] Context Window : {config.MODEL_CONTEXT_WINDOW}")
    print("-" * 60)

    try:
        client = get_llm_client()
    except Exception as e:
        print(f"[❌] Error initializing LLM client: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Testing provider reachability ({config.LLM_PROVIDER})...")
    is_healthy = client.health_check()

    if not is_healthy:
        print(f"[❌] Health check FAILED: Cannot reach {config.LLM_PROVIDER} at {config.OLLAMA_BASE_URL}.")
        print("\n[ℹ️] Troubleshooting Checklist:")
        print("    1. Make sure Ollama is installed and running: run `ollama serve`")
        print(f"    2. Verify the model is downloaded: run `ollama pull {config.MODEL_NAME}`")
        print("    3. Check your OLLAMA_BASE_URL in .env (default: http://localhost:11434)")
        print("    4. If you wish to test offline without an active LLM, set LLM_PROVIDER=mock in .env")
        sys.exit(1)

    print(f"[✅] Service is REACHABLE at {config.OLLAMA_BASE_URL}")
    print(f"[*] Sending test hello prompt to model '{config.MODEL_NAME}'...")

    test_prompt = "Hello! Please reply in one short sentence confirming that Zucky's Reading LLM connection is working."
    start_time = time.time()

    try:
        response = client.generate(
            prompt=test_prompt,
            system_prompt="You are a helpful test assistant for Zucky's Reading. Be concise.",
            json_mode=False,
            temperature=0.1,
        )
        latency = time.time() - start_time
        print(f"[🎉] Response received in {latency:.2f} seconds!")
        print("-" * 60)
        print(f"Model Reply: {response.strip()}")
        print("-" * 60)
        print("[✅] LLM configuration and connection verified successfully!")
    except Exception as e:
        latency = time.time() - start_time
        print(f"[❌] Failed to receive response from model ({latency:.2f}s): {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
