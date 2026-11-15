import os
import sys
from typing import Optional

import config
from src.common import WhatsAppParser
from src.static import StaticAnalyzer, generate_html_report

def run_pipeline():
    chat_file = config.CHAT_EXPORT_PATH
    print("=" * 60)
    print("  ZUCKY'S READING - WHATSAPP FORENSIC DOSSIER PIPELINE")
    print("=" * 60)
    print(f"[*] Chat Export Path : {chat_file}")
    print(f"[*] Static Analysis  : {'ENABLED' if config.ENABLE_STATIC_ANALYSIS else 'DISABLED'}")
    print(f"[*] Semantic Analysis: {'ENABLED' if config.ENABLE_SEMANTIC_ANALYSIS else 'DISABLED'}")
    print("-" * 60)

    if not os.path.exists(chat_file):
        print(f"[!] Error: Chat export file not found at: '{chat_file}'", file=sys.stderr)
        print("[!] Please check CHAT_EXPORT_PATH in your .env file.", file=sys.stderr)
        sys.exit(1)

    if not config.ENABLE_STATIC_ANALYSIS and not config.ENABLE_SEMANTIC_ANALYSIS:
        print("[!] Notice: Both Static and Semantic analyses are disabled in .env.")
        print("[!] Set ENABLE_STATIC_ANALYSIS=true or ENABLE_SEMANTIC_ANALYSIS=true to run.")
        return

    # 1. Parse Chat Export
    print(f"[*] Parsing chat file...")
    parser = WhatsAppParser()
    group_name, messages = parser.parse_file(chat_file)
    print(f"[+] Successfully parsed {len(messages):,} messages for group: '{group_name}'")

    # 2. Static Analysis Subsystem
    if config.ENABLE_STATIC_ANALYSIS:
        print("\n--- [Stage: Deterministic Static Analysis] ---")
        analyzer = StaticAnalyzer(inactivity_gap_hours=config.INACTIVITY_GAP_HOURS)
        static_report = analyzer.analyze(group_name, messages)
        print(f"[+] Static analysis complete: {static_report.group_stats.total_events} distinct conversations identified.")

        os.makedirs(config.REPORTS_DIR, exist_ok=True)
        output_report = os.path.join(config.REPORTS_DIR, f"Zucky_read_{group_name}.html")
        report_path = generate_html_report(static_report, output_report, release_version=config.APP_VERSION)
        print(f"[🎉] Interactive HTML Report generated at: {report_path}")

    # 3. Semantic Analysis Subsystem (Multi-Agent Pipeline)
    if config.ENABLE_SEMANTIC_ANALYSIS:
        print("\n--- [Stage: Multi-Agent Semantic Analysis] ---")
        print(f"[*] Target Model: {config.MODEL_NAME} via {config.LLM_PROVIDER}")
        print("[ℹ️] Semantic analysis subsystem is scheduled for release in Phase 3 & 4.")

    print("\n" + "=" * 60)
    print("  PIPELINE EXECUTION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_pipeline()
