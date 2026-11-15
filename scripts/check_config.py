#!/usr/bin/env python3
"""
Comprehensive configuration & connectivity validator for Zucky's Reading.
Validates:
1. Mathematical config parameters (alpha, beta, k ratios, thresholds)
2. Environment variables & chat file availability
3. Local LLM connectivity and latency
"""
import sys
import os
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from src.llm import get_llm_client

def validate_config_coefficients() -> bool:
    print("[*] Validating algorithmic thresholds & memory coefficients...")
    k = config.MESSAGE_RATIO_K
    if k <= 0 or k > 1.0:
        print(f"    [❌] Invalid MESSAGE_RATIO_K: {k}. Must be between 0 and 1.0.")
        return False

    max_combined = 1.0 / k  # e.g. 1 / 0.05 = 20
    print(f"    [i] Message Ratio k = {k:.3f} | Maximum Combined Multiplier (1/k) = {max_combined:.1f}")

    all_valid = True
    size_classes = ["XS", "S", "M", "L", "XL"]

    for sc in size_classes:
        alpha = config.BOOTSTRAP_ALPHA.get(sc, 0.0)
        beta = config.CALIBRATION_BETA.get(sc, 0.0)
        combined = alpha + beta
        combined_pct = (alpha * k) + ((1.0 - (alpha * k)) * (beta * k)) if alpha * k < 1.0 else 1.0
        simple_pct = (alpha + beta) * k

        print(f"    • Class {sc:<2}: alpha={alpha:<4.1f} | beta={beta:<4.1f} | alpha+beta={combined:<4.1f} (<= {max_combined:.1f})")

        # Validation condition: (alpha + beta) * k <= 1.0 (or alpha + beta <= 100 * k in scale where 100% = 1.0 / k)
        if simple_pct > 1.0001:
            print(f"      [❌] ERROR: alpha ({alpha}) + beta ({beta}) exceeds 100% of messages ({(alpha+beta)*k*100:.1f}%) for size class {sc}!")
            all_valid = False

    if not all_valid:
        return False

    # Check percentile ordering
    if not (0 < config.TIER_1_PERCENTILE <= config.TIER_2_PERCENTILE <= 1.0):
        print(f"    [❌] Invalid percentile ordering: TIER_1 ({config.TIER_1_PERCENTILE}) must be <= TIER_2 ({config.TIER_2_PERCENTILE}).")
        return False

    # Check batch safety limits
    if config.TIER_2_BATCH_MAX_REPORTS <= 0 or config.TIER_2_BATCH_MAX_TOKENS <= 0:
        print("    [❌] Batch limits must be positive integers.")
        return False

    print("    [✅] Memory coefficients and threshold math validated successfully!")
    return True

def validate_environment_paths() -> bool:
    print("[*] Validating environment settings & file paths...")
    chat_path = config.CHAT_EXPORT_PATH
    if not os.path.exists(chat_path):
        print(f"    [⚠️] Chat export file not found at: '{chat_path}'")
        print("        (Check CHAT_EXPORT_PATH in .env when you are ready to analyze)")
    else:
        print(f"    [✅] Target chat export found ({os.path.getsize(chat_path):,} bytes): '{chat_path}'")

    if not os.path.exists(config.PROMPTS_DIR):
        print(f"    [❌] Prompts directory missing at: '{config.PROMPTS_DIR}'")
        return False
    else:
        prompts = [f for f in os.listdir(config.PROMPTS_DIR) if f.endswith(".md")]
        print(f"    [✅] Prompts directory verified ({len(prompts)} markdown templates detected).")

    return True

def validate_llm_connection() -> bool:
    print(f"[*] Validating LLM connectivity ({config.LLM_PROVIDER} / {config.MODEL_NAME})...")
    try:
        client = get_llm_client()
    except Exception as e:
        print(f"    [❌] Failed to initialize client: {e}")
        return False

    if not client.health_check():
        print(f"    [❌] Service UNREACHABLE at {config.OLLAMA_BASE_URL}.")
        print("        Troubleshooting: Ensure Ollama is running (`ollama serve`).")
        return False

    print(f"    [✅] Service is REACHABLE at {config.OLLAMA_BASE_URL}")
    print(f"    [*] Sending test probe to '{config.MODEL_NAME}'...")

    start_time = time.time()
    try:
        resp = client.generate(
            prompt="Hello! Please confirm operational status in 5 words.",
            system_prompt="Be extremely brief.",
            json_mode=False,
            temperature=0.1,
        )
        latency = time.time() - start_time
        print(f"    [🎉] Response received in {latency:.2f}s!")
        print(f"    Model Reply: \"{resp.strip()}\"")
        return True
    except Exception as e:
        latency = time.time() - start_time
        print(f"    [❌] Generation error ({latency:.2f}s): {e}")
        return False

def main():
    print("=" * 65)
    print("  ZUCKY'S READING - SYSTEM & CONFIGURATION DIAGNOSTICS")
    print("=" * 65)

    coeff_ok = validate_config_coefficients()
    print("-" * 65)
    env_ok = validate_environment_paths()
    print("-" * 65)
    llm_ok = validate_llm_connection()
    print("=" * 65)

    if coeff_ok and env_ok and llm_ok:
        print("  [✅] ALL SYSTEM CHECKS PASSED - READY FOR EXECUTION")
        print("=" * 65)
        sys.exit(0)
    else:
        print("  [⚠️] SOME CHECKS REPORTED ISSUES (See details above)")
        print("=" * 65)
        sys.exit(1)

if __name__ == "__main__":
    main()
