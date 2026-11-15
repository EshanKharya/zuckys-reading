import os
import argparse
from typing import Optional
from src.parser import WhatsAppParser
from src.static_analyzer import StaticAnalyzer
from src.html_report import generate_html_report

def run_static_analysis(chat_file: str, output_report: Optional[str] = None):
    print(f"[*] Parsing chat file: {chat_file}")
    parser = WhatsAppParser()
    group_name, messages = parser.parse_file(chat_file)
    print(f"[+] Successfully parsed {len(messages):,} messages for group: '{group_name}'")

    print("[*] Running Static Analysis & banter roast calculations...")
    analyzer = StaticAnalyzer(inactivity_gap_hours=2.0)
    report = analyzer.analyze(group_name, messages)
    print(f"[+] Static analysis complete: {report.group_stats.total_events} distinct conversations identified.")

    if not output_report:
        output_report = os.path.join("reports", f"Zucky_read_{group_name}.html")

    os.makedirs(os.path.dirname(output_report), exist_ok=True)
    report_path = generate_html_report(report, output_report)
    print(f"[🎉] HTML Report generated successfully at: {report_path}")
    return report, report_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zucky's Reading - WhatsApp Chat Analyzer")
    parser.add_argument("--chat", type=str, default="chats/WhatsApp Chat with BTC sher 🦁.txt", help="Path to WhatsApp chat export .txt file")
    parser.add_argument("--out", type=str, default=None, help="Output HTML report path")
    args = parser.parse_args()

    run_static_analysis(args.chat, args.out)
