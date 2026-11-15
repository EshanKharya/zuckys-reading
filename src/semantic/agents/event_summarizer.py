import os
import csv
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import config
from src.common.prompt_loader import load_prompt_template
from src.llm import get_llm_client, BaseLLMClient
from src.semantic.preprocessor import CompressedEvent

@dataclass
class EventReport:
    event_id: str
    event_name: str
    impact_strength: int
    involvement_scores: Dict[str, int]
    topics: List[str]
    what_happened: str
    who_said_what: str
    hot_takes: str
    singling_out: str
    banter_analysis: str
    emotional_disturbances: str
    notable_quotes: List[str]
    report_md: str
    file_path: str

class EventSummarizerAgent:
    """Agent 1: Evaluates individual compressed events and produces structured event reports."""

    def __init__(self, chat_name: str, llm_client: Optional[BaseLLMClient] = None, outputs_dir: Optional[str] = None):
        self.chat_name = chat_name
        self.llm_client = llm_client or get_llm_client()
        self.base_dir = outputs_dir or os.path.join(config.OUTPUTS_DIR, chat_name)
        self.reports_dir = os.path.join(self.base_dir, "event_reports")
        self.csv_path = os.path.join(self.base_dir, "event_map.csv")

        os.makedirs(self.reports_dir, exist_ok=True)
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "event_id",
                    "event_name",
                    "impact_strength",
                    "messages",
                    "words",
                    "duration",
                    "participants_count",
                    "involvement_scores_json",
                ])

    def summarize_event(
        self,
        event: CompressedEvent,
        group_baseline: str,
        group_memory_str: str,
    ) -> EventReport:
        # Build user mapping string for prompt
        mapping_lines = [f"{code}: {name}" for code, name in event.involved_user_map.items()]
        user_mapping_str = "\n".join(mapping_lines)

        prompt = load_prompt_template(
            "event_summarizer",
            group_baseline=group_baseline,
            group_memory=group_memory_str,
            user_mapping=user_mapping_str,
        )

        full_prompt = f"{prompt}\n\n## Conversation Chunk to Analyze:\n{event.compressed_text}"

        try:
            data = self.llm_client.generate_json(
                prompt=full_prompt,
                system_prompt="You are the Event Summarizer for Zucky's Reading. Be forensic, sharp, and concise.",
            )
        except Exception as e:
            # Fallback deterministic structure on LLM error
            print(f"[!] Warning: Agent 1 failed on {event.event_id}: {e}")
            data = {
                "event_id": event.event_id,
                "event_name": f"Event {event.event_id} on {event.start_time.strftime('%d %b %Y')}",
                "impact_strength": 3,
                "involvement_scores": {code: 5 for code in event.involved_user_map.keys()},
                "topics": ["General Chatter"],
                "what_happened": "Routine conversation recorded.",
                "who_said_what": "Participants exchanged messages.",
                "hot_takes": "None",
                "singling_out": "None",
                "banter_analysis": "Neutral",
                "emotional_disturbances": "None",
                "notable_quotes": [],
            }

        event_id = data.get("event_id", event.event_id)
        event_name = data.get("event_name", f"Event {event.event_id} on {event.start_time.strftime('%d %b %Y')}")
        impact = int(data.get("impact_strength", 3))
        involvement = data.get("involvement_scores", {})
        if not isinstance(involvement, dict):
            involvement = {code: 5 for code in event.involved_user_map.keys()}

        # Render Markdown Report with User Mapping Table
        report_md = self._render_markdown_report(event, data, impact, involvement, event_name)

        # Save Markdown Report
        file_path = os.path.join(self.reports_dir, f"{event_id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        # Append to CSV
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                event_id,
                event_name,
                impact,
                event.message_count,
                event.word_count,
                event.duration_str,
                len(event.involved_user_map),
                json.dumps(involvement),
            ])

        return EventReport(
            event_id=event_id,
            event_name=event_name,
            impact_strength=impact,
            involvement_scores=involvement,
            topics=data.get("topics", []),
            what_happened=data.get("what_happened", ""),
            who_said_what=data.get("who_said_what", ""),
            hot_takes=data.get("hot_takes", ""),
            singling_out=data.get("singling_out", ""),
            banter_analysis=data.get("banter_analysis", ""),
            emotional_disturbances=data.get("emotional_disturbances", ""),
            notable_quotes=data.get("notable_quotes", []),
            report_md=report_md,
            file_path=file_path,
        )

    def _render_markdown_report(
        self,
        event: CompressedEvent,
        data: Dict[str, Any],
        impact: int,
        involvement: Dict[str, Any],
        event_name: str,
    ) -> str:
        lines = [
            f"# Event Report: {event.event_id} - {event_name}",
            "",
            "## Metadata",
            f"* **Impact Strength Score:** {impact}/10",
            f"* **Date & Time:** {event.start_time.strftime('%d %b %Y, %H:%M')}",
            f"* **Duration:** {event.duration_str} | **Messages:** {event.message_count:,} | **Words:** {event.word_count:,}",
            f"* **Active Participants:** {len(event.involved_user_map)}",
            "",
            "## User Mapping & Involvement",
            "| User Code | Member Contact Name | Involvement Score (1-10) |",
            "| :--- | :--- | :--- |",
        ]

        for code, name in sorted(event.involved_user_map.items()):
            score = involvement.get(code, "5")
            lines.append(f"| {code} | {name} | {score}/10 |")

        lines.extend([
            "",
            "## Topics Discussed",
            ", ".join(data.get("topics", ["General"])),
            "",
            "## What Happened",
            data.get("what_happened", "N/A"),
            "",
            "## Who Said What",
            data.get("who_said_what", "N/A"),
            "",
            "## Hot Takes",
            data.get("hot_takes", "None"),
            "",
            "## Singling Out",
            data.get("singling_out", "None"),
            "",
            "## Banter Analysis",
            data.get("banter_analysis", "None"),
            "",
            "## Emotional Disturbances",
            data.get("emotional_disturbances", "None"),
            "",
            "## Notable Quotes",
        ])

        quotes = data.get("notable_quotes", [])
        if quotes:
            for q in quotes:
                lines.append(f"* {q}")
        else:
            lines.append("* None recorded")

        return "\n".join(lines)
