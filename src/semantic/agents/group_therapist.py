import os
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import config
from src.common.prompt_loader import load_prompt_template
from src.llm import get_llm_client, BaseLLMClient
from src.semantic.agents.event_summarizer import EventReport
from src.semantic.agents.personality_roaster import PersonalityReport
from src.semantic.agents.relationship_guru import RelationshipReport
from src.semantic.preprocessor import CompressedEvent

@dataclass
class GroupReport:
    group_identity: str
    group_apt_emoji: str
    group_timeline: str
    master_group_roast: str
    top_10_event_ids: List[str]
    report_md: str
    file_path: str

class GroupTherapistAgent:
    """Agent 4: Master group psychoanalyst synthesizing group identity, macro timeline, and unfiltered group roast."""

    def __init__(self, chat_name: str, llm_client: Optional[BaseLLMClient] = None, outputs_dir: Optional[str] = None):
        self.chat_name = chat_name
        self.llm_client = llm_client or get_llm_client()
        self.base_dir = outputs_dir or os.path.join(config.OUTPUTS_DIR, chat_name)
        self.report_path = os.path.join(self.base_dir, "group_report.md")

    def synthesize(
        self,
        group_name: str,
        event_reports: List[EventReport],
        personality_reports: List[PersonalityReport],
        relationship_reports: List[RelationshipReport],
        compressed_events_map: Dict[str, CompressedEvent],
        group_baseline: str,
        group_memory_str: str,
    ) -> GroupReport:
        # 1. Calculate Group Impact Score for each event: Mean(involvement) * impact_strength
        scored_events: List[Tuple[float, EventReport, Optional[CompressedEvent]]] = []
        for rep in event_reports:
            inv_vals = list(rep.involvement_scores.values())
            mean_inv = (sum(inv_vals) / len(inv_vals)) if inv_vals else 1.0
            group_impact = mean_inv * rep.impact_strength
            comp_ev = compressed_events_map.get(rep.event_id)
            scored_events.append((group_impact, rep, comp_ev))

        scored_events.sort(key=lambda x: x[0], reverse=True)
        total_ev = len(scored_events)

        t1_cutoff = max(1, int(total_ev * config.TIER_1_PERCENTILE))
        t2_cutoff = max(t1_cutoff, int(total_ev * config.TIER_2_PERCENTILE))

        top_events = scored_events[:t1_cutoff]
        mid_events = [x for x in scored_events[t1_cutoff:t2_cutoff] if x[0] >= config.TIER_2_MIN_SCORE or len(scored_events[:t2_cutoff]) <= 10][:8]

        selected = top_events + mid_events
        selected.sort(key=lambda x: int(x[1].event_id.replace("E", "")))

        # Assemble Canon Events Summary
        canon_blocks = []
        for g_score, rep, comp_ev in selected:
            b = [
                f"* **Event {rep.event_id} ({rep.event_name})**: Impact {rep.impact_strength}/10",
                f"  Summary: {rep.what_happened}",
                f"  Banter Dynamics: {rep.banter_analysis}",
            ]
            canon_blocks.append("\n".join(b))
        canon_events_str = "\n\n".join(canon_blocks)

        # Assemble Personality Summaries
        persona_blocks = []
        for p in personality_reports:
            persona_blocks.append(f"* **{p.member_name} ({p.user_code})**: {p.title} {p.apt_emoji} - Strengths: {', '.join(p.strengths[:2])}; Weaknesses: {', '.join(p.weaknesses[:2])}")
        persona_str = "\n".join(persona_blocks)

        # Assemble Relationship Summaries (top 5 active pairs)
        rel_blocks = []
        active_rels = [r for r in relationship_reports if r.strength_score > 1]
        active_rels.sort(key=lambda x: x.strength_score, reverse=True)
        for r in active_rels[:8]:
            rel_blocks.append(f"* **{r.member_name_1} & {r.member_name_2}**: '{r.couple_title}' {r.apt_emoji} (Strength: {r.strength_score}/10) - {r.timeline[:120]}...")
        rel_str = "\n".join(rel_blocks) if rel_blocks else "No prominent dyadic alliances."

        prompt = load_prompt_template(
            "group_therapist",
            group_baseline=group_baseline,
            group_memory=group_memory_str,
            personality_summaries=persona_str,
            relationship_summaries=rel_str,
            canon_events=canon_events_str,
        )

        try:
            data = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are the Group Therapist for Zucky's Reading. Conduct a brutal, unfiltered group macro diagnosis.",
            )
        except Exception as e:
            print(f"[!] Warning: Agent 4 failed: {e}")
            data = {
                "group_identity": f"The Collective Fellowship of {group_name}",
                "group_apt_emoji": "🎪",
                "group_timeline": f"A self-sustaining social ecosystem bonded through mutual habit and routine exchanges.",
                "master_group_roast": f"This group exists in a permanent state of conversational tension, balancing periodic outbursts with comfortable coexistence.",
                "top_10_event_ids": [x[1].event_id for x in selected[:10]],
            }

        identity = data.get("group_identity", f"The Fellowship of {group_name}")
        emoji_char = data.get("group_apt_emoji", "🎪")
        timeline = data.get("group_timeline", "A resilient, evolving conversational collective.")
        roast = data.get("master_group_roast", "No master roast recorded.")
        top_events = data.get("top_10_event_ids", [x[1].event_id for x in selected[:10]])

        report_md = self._render_group_markdown(group_name, identity, emoji_char, timeline, roast, top_events)
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        return GroupReport(
            group_identity=identity,
            group_apt_emoji=emoji_char,
            group_timeline=timeline,
            master_group_roast=roast,
            top_10_event_ids=top_events,
            report_md=report_md,
            file_path=self.report_path,
        )

    def _render_group_markdown(
        self,
        group_name: str,
        identity: str,
        emoji_char: str,
        timeline: str,
        roast: str,
        top_events: List[str],
    ) -> str:
        lines = [
            f"# Group Therapy & Collective Diagnosis: {group_name}",
            "",
            f"### **{identity}** {emoji_char}",
            "",
            "## Group Evolution Timeline",
            timeline,
            "",
            "## The Master Group Roast",
            roast,
            "",
            "## Defining Canon Group Milestones",
            ", ".join(top_events) if top_events else "None",
        ]
        return "\n".join(lines)
