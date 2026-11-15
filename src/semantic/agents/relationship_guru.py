import os
import math
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import config
from src.common.prompt_loader import load_prompt_template
from src.llm import get_llm_client, BaseLLMClient
from src.semantic.agents.event_summarizer import EventReport
from src.semantic.preprocessor import CompressedEvent

@dataclass
class RelationshipReport:
    pair_key: str              # e.g. "%U1%_%U2%"
    user_code_1: str
    user_code_2: str
    member_name_1: str
    member_name_2: str
    couple_title: str
    apt_emoji: str
    timeline: str
    traits: List[str]
    strength_score: int
    top_shared_event_ids: List[str]
    report_md: str
    file_path: str

class RelationshipGuruAgent:
    """Agent 3: Evaluates pairwise dyadic relationships, dynamic timelines, and strength scores."""

    def __init__(self, chat_name: str, llm_client: Optional[BaseLLMClient] = None, outputs_dir: Optional[str] = None):
        self.chat_name = chat_name
        self.llm_client = llm_client or get_llm_client()
        self.base_dir = outputs_dir or os.path.join(config.OUTPUTS_DIR, chat_name)
        self.reports_dir = os.path.join(self.base_dir, "relationship_reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def evaluate_pair(
        self,
        u1_code: str,
        u1_name: str,
        u2_code: str,
        u2_name: str,
        event_reports: List[EventReport],
        compressed_events_map: Dict[str, CompressedEvent],
        group_baseline: str,
        group_memory_str: str,
    ) -> RelationshipReport:
        pair_key = f"{u1_code}_{u2_code}"

        # 1. Identify shared events where BOTH users participated
        shared_events: List[Tuple[float, EventReport, Optional[CompressedEvent]]] = []
        for rep in event_reports:
            inv1 = rep.involvement_scores.get(u1_code, 0)
            inv2 = rep.involvement_scores.get(u2_code, 0)
            if inv1 > 0 and inv2 > 0:
                # Interaction score = Geometric mean of trait marking scores
                score1 = inv1 * rep.impact_strength
                score2 = inv2 * rep.impact_strength
                interaction_score = math.sqrt(score1 * score2)
                comp_ev = compressed_events_map.get(rep.event_id)
                shared_events.append((interaction_score, rep, comp_ev))

        # 2. Pair Pruning: if zero shared conversations, bypass LLM
        if len(shared_events) < config.MIN_SHARED_CONVERSATIONS:
            return self._build_pruned_report(pair_key, u1_code, u1_name, u2_code, u2_name)

        # 3. Sort by interaction score to determine cutoffs
        shared_events.sort(key=lambda x: x[0], reverse=True)
        total_shared = len(shared_events)

        t1_cutoff = max(1, int(total_shared * config.TIER_1_PERCENTILE))
        t2_cutoff = max(t1_cutoff, int(total_shared * config.TIER_2_PERCENTILE))

        tier_1 = shared_events[:t1_cutoff]
        tier_2 = [
            item for item in shared_events[t1_cutoff:t2_cutoff]
            if item[0] >= config.TIER_2_MIN_SCORE or len(shared_events[:t2_cutoff]) <= 10
        ][:config.TIER_2_BATCH_MAX_REPORTS]

        selected = tier_1 + tier_2
        # Sort chronologically by event integer
        selected.sort(key=lambda x: int(x[1].event_id.replace("E", "")))

        # 4. Assemble Event Inputs Text
        event_blocks = []
        for int_score, rep, comp_ev in selected:
            block = [
                f"### Event {rep.event_id}: {rep.event_name}",
                f"* Co-Involvement: {u1_code} ({rep.involvement_scores.get(u1_code)}/10) & {u2_code} ({rep.involvement_scores.get(u2_code)}/10)",
                f"* What Happened: {rep.what_happened}",
                f"* Banter & Dynamics: {rep.banter_analysis}",
            ]
            if comp_ev and (int_score, rep, comp_ev) in tier_1:
                dialog = comp_ev.compressed_text.split("=========================\n")[-1][:1000]
                block.append(f"* Dialogue Excerpt:\n{dialog}")
            event_blocks.append("\n".join(block))

        shared_event_inputs_str = "\n\n".join(event_blocks)

        prompt = load_prompt_template(
            "relationship_guru",
            user_code_1=u1_code,
            user_code_2=u2_code,
            group_baseline=group_baseline,
            group_memory=group_memory_str,
            current_relationship="None (Initial Evaluation)",
            shared_event_inputs=shared_event_inputs_str,
        )

        try:
            data = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are the Relationship Guru for Zucky's Reading. Be cynical, sharp, and humorous.",
            )
        except Exception as e:
            print(f"[!] Warning: Agent 3 failed for pair {pair_key}: {e}")
            data = {
                "couple_title": "Circumstantial Sparring Partners",
                "apt_emoji": "🤝",
                "timeline": f"{u1_code} and {u2_code} interact when group debates heat up, maintaining a civil coexistence.",
                "traits": ["Pragmatic conversational alliance", "Occasional banter back-and-forth"],
                "strength_score": 5,
                "top_shared_event_ids": [x[1].event_id for x in selected[:3]],
            }

        title = data.get("couple_title", "Unlikely Companions")
        emoji_char = data.get("apt_emoji", "⚖️")
        timeline = data.get("timeline", "Consistent shared interaction.")
        traits = data.get("traits", ["Shared conversation history"])
        strength = int(data.get("strength_score", 5))
        top_events = data.get("top_shared_event_ids", [x[1].event_id for x in selected[:3]])

        report_md = self._render_markdown_pair(
            pair_key, u1_code, u1_name, u2_code, u2_name, title, emoji_char, timeline, traits, strength, top_events
        )
        file_path = os.path.join(self.reports_dir, f"{pair_key}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        return RelationshipReport(
            pair_key=pair_key,
            user_code_1=u1_code,
            user_code_2=u2_code,
            member_name_1=u1_name,
            member_name_2=u2_name,
            couple_title=title,
            apt_emoji=emoji_char,
            timeline=timeline,
            traits=traits,
            strength_score=strength,
            top_shared_event_ids=top_events,
            report_md=report_md,
            file_path=file_path,
        )

    def _render_markdown_pair(
        self,
        pair_key: str,
        u1_code: str,
        u1_name: str,
        u2_code: str,
        u2_name: str,
        title: str,
        emoji_char: str,
        timeline: str,
        traits: List[str],
        strength: int,
        top_events: List[str],
    ) -> str:
        lines = [
            f"# Relationship Profile: {u1_name} & {u2_name} ({pair_key})",
            "",
            f"### **{title}** {emoji_char}",
            f"* **Relationship Strength Score:** {strength}/10",
            "",
            "## Relationship Evolution Timeline",
            timeline,
            "",
            "## Dynamic Traits & Characteristics",
        ]
        for t in traits:
            lines.append(f"* {t}")

        lines.extend([
            "",
            "## Key Shared Milestone Events",
            ", ".join(top_events) if top_events else "None recorded",
        ])
        return "\n".join(lines)

    def _build_pruned_report(
        self,
        pair_key: str,
        u1_code: str,
        u1_name: str,
        u2_code: str,
        u2_name: str,
    ) -> RelationshipReport:
        title = "Total Strangers in the Same Room"
        emoji_char = "🧊"
        timeline = f"{u1_name} ({u1_code}) and {u2_name} ({u2_code}) have zero recorded direct interaction across the analyzed history."
        traits = ["Parallel existence", "Zero recorded dialogue exchange"]
        strength = 1
        top_events = []
        md = self._render_markdown_pair(pair_key, u1_code, u1_name, u2_code, u2_name, title, emoji_char, timeline, traits, strength, top_events)
        path = os.path.join(self.reports_dir, f"{pair_key}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

        return RelationshipReport(
            pair_key, u1_code, u2_code, u1_name, u2_name, title, emoji_char, timeline, traits, strength, top_events, md, path
        )
