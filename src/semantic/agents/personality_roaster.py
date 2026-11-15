import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import config
from src.common.prompt_loader import load_prompt_template
from src.llm import get_llm_client, BaseLLMClient
from src.common.models import MemberStats
from src.semantic.agents.event_summarizer import EventReport
from src.semantic.preprocessor import CompressedEvent

@dataclass
class PersonalityReport:
    user_code: str
    member_name: str
    title: str
    apt_emoji: str
    roast: str
    strengths: List[str]
    weaknesses: List[str]
    top_5_event_ids: List[str]
    report_md: str
    file_path: str

class PersonalityRoasterAgent:
    """Agent 2: Builds and sharpens the unfiltered personality roast dossier for each member."""

    def __init__(self, chat_name: str, llm_client: Optional[BaseLLMClient] = None, outputs_dir: Optional[str] = None):
        self.chat_name = chat_name
        self.llm_client = llm_client or get_llm_client()
        self.base_dir = outputs_dir or os.path.join(config.OUTPUTS_DIR, chat_name)
        self.reports_dir = os.path.join(self.base_dir, "personality_reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_dossier(
        self,
        user_code: str,
        member_name: str,
        member_stats: Optional[MemberStats],
        event_reports: List[EventReport],
        compressed_events_map: Dict[str, CompressedEvent],
        group_baseline: str,
        group_memory_str: str,
    ) -> PersonalityReport:
        # 1. Filter events involving this member and calculate trait_marking_score
        scored_events: List[tuple] = []  # (trait_score, report, comp_event)
        for rep in event_reports:
            inv = rep.involvement_scores.get(user_code, 0)
            if inv > 0:
                trait_score = inv * rep.impact_strength
                comp_ev = compressed_events_map.get(rep.event_id)
                scored_events.append((trait_score, rep, comp_ev))

        if not scored_events:
            # Fallback if member had 0 involvement
            return self._build_empty_dossier(user_code, member_name, member_stats)

        # 2. Sort by trait score to determine Tier 1 and Tier 2 cutoffs
        scored_events.sort(key=lambda x: x[0], reverse=True)
        total_inv = len(scored_events)

        tier_1_cutoff = max(1, int(total_inv * config.TIER_1_PERCENTILE))
        tier_2_cutoff = max(tier_1_cutoff, int(total_inv * config.TIER_2_PERCENTILE))

        tier_1_items = scored_events[:tier_1_cutoff]
        tier_2_items = [
            item for item in scored_events[tier_1_cutoff:tier_2_cutoff]
            if item[0] >= config.TIER_2_MIN_SCORE or len(scored_events[:tier_2_cutoff]) <= 10
        ][:config.TIER_2_BATCH_MAX_REPORTS]

        # 3. Re-sort selected events CHRONOLOGICALLY before LLM ingestion
        selected_items = tier_1_items + tier_2_items
        # Sort chronologically by event_id integer
        selected_items.sort(key=lambda x: int(x[1].event_id.replace("E", "")))

        # 4. Assemble Event Inputs Text
        event_inputs_blocks = []
        for trait_score, rep, comp_ev in selected_items:
            block = [
                f"### Event {rep.event_id}: {rep.event_name}",
                f"* Member Involvement: {rep.involvement_scores.get(user_code, 5)}/10 | Impact: {rep.impact_strength}/10",
                f"* Topics: {', '.join(rep.topics)}",
                f"* What Happened: {rep.what_happened}",
                f"* Banter & Observations: {rep.banter_analysis}",
            ]
            # If Tier 1, include snippet of raw compressed dialog
            if comp_ev and (trait_score, rep, comp_ev) in tier_1_items:
                dialog_lines = comp_ev.compressed_text.split("=========================\n")[-1]
                # Truncate raw dialog to avoid token overflow
                dialog_snippet = dialog_lines[:1200]
                block.append(f"* Raw Event Dialog Snippet:\n{dialog_snippet}")
            event_inputs_blocks.append("\n".join(block))

        event_inputs_str = "\n\n".join(event_inputs_blocks)

        # 5. Format Member Static Stats
        static_str = "No static metrics available"
        if member_stats:
            static_str = (
                f"- Total Messages: {member_stats.total_messages:,} ({member_stats.percentage_of_total:.1f}% of group)\n"
                f"- Average Verbosity: {member_stats.words_per_message:.1f} words/msg\n"
                f"- Pure Text Response Speed: Median {member_stats.median_response_time_seconds / 60:.1f}m\n"
                f"- Yap Streak: {member_stats.longest_yap_streak} consecutive texts\n"
                f"- Sahara Desert Dry Rate: {member_stats.dry_text_percentage:.1f}%\n"
                f"- Night Owl Activity: {member_stats.night_owl_percentage:.1f}%\n"
                f"- Vocabulary Size: {member_stats.vocabulary_size:,} distinct words"
            )

        prompt = load_prompt_template(
            "personality_roaster",
            target_user_code=user_code,
            group_baseline=group_baseline,
            group_memory=group_memory_str,
            member_static_stats=static_str,
            current_persona="None (Initial Dossier Generation)",
            event_inputs=event_inputs_str,
        )

        try:
            data = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are the Personality Roaster for Zucky's Reading. Be brutally witty, sharp, and unfiltered.",
            )
        except Exception as e:
            print(f"[!] Warning: Agent 2 failed for {user_code}: {e}")
            data = {
                "user_code": user_code,
                "title": "The Elusive Group Observer",
                "apt_emoji": "🎭",
                "roast": f"{user_code} lurks in the shadows, chiming in just enough to remind everyone they exist.",
                "strengths": ["Low maintenance conversationalist"],
                "weaknesses": ["Rarely commits to high-stakes group debates"],
                "top_5_event_ids": [x[1].event_id for x in selected_items[:5]],
            }

        title = data.get("title", "The Group Enigma")
        emoji_char = data.get("apt_emoji", "👤")
        roast = data.get("roast", "No roast available.")
        strengths = data.get("strengths", ["Consistent participant"])
        weaknesses = data.get("weaknesses", ["Prone to overthinking"])
        top_events = data.get("top_5_event_ids", [x[1].event_id for x in selected_items[:5]])

        # 6. Render and Save Markdown Dossier
        report_md = self._render_markdown_dossier(user_code, member_name, title, emoji_char, roast, strengths, weaknesses, top_events, member_stats)
        file_path = os.path.join(self.reports_dir, f"{user_code}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        return PersonalityReport(
            user_code=user_code,
            member_name=member_name,
            title=title,
            apt_emoji=emoji_char,
            roast=roast,
            strengths=strengths,
            weaknesses=weaknesses,
            top_5_event_ids=top_events,
            report_md=report_md,
            file_path=file_path,
        )

    def _render_markdown_dossier(
        self,
        user_code: str,
        name: str,
        title: str,
        emoji_char: str,
        roast: str,
        strengths: List[str],
        weaknesses: List[str],
        top_events: List[str],
        stats: Optional[MemberStats],
    ) -> str:
        lines = [
            f"# Personality Dossier: {name} ({user_code})",
            "",
            f"### **{title}** {emoji_char}",
            "",
            "## The Unfiltered Roast",
            roast,
            "",
            "## Strengths",
        ]
        for s in strengths:
            lines.append(f"* {s}")

        lines.extend(["", "## Weaknesses"])
        for w in weaknesses:
            lines.append(f"* {w}")

        lines.extend([
            "",
            "## Top Defining Event Milestones",
            ", ".join(top_events) if top_events else "None",
        ])

        if stats:
            lines.extend([
                "",
                "## Statistical Behavioral Badges",
                f"* **Verbosity:** {stats.words_per_message:.1f} words/msg",
                f"* **Response Speed:** Median {stats.median_response_time_seconds / 60:.1f}m",
                f"* **Yap Streak:** {stats.longest_yap_streak} consecutive text messages",
                f"* **Sahara Desert Index:** {stats.dry_text_percentage:.1f}% dry texts",
                f"* **Vocabulary Size:** {stats.vocabulary_size:,} words",
            ])

        return "\n".join(lines)

    def _build_empty_dossier(self, user_code: str, name: str, stats: Optional[MemberStats]) -> PersonalityReport:
        title = "The Silent Observer"
        emoji_char = "👻"
        roast = f"{name} ({user_code}) has barely left a conversational footprint in this group."
        strengths = ["Zero drama"]
        weaknesses = ["Practically invisible"]
        top_events = []
        md = self._render_markdown_dossier(user_code, name, title, emoji_char, roast, strengths, weaknesses, top_events, stats)
        path = os.path.join(self.reports_dir, f"{user_code}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return PersonalityReport(user_code, name, title, emoji_char, roast, strengths, weaknesses, top_events, md, path)
