import os
from itertools import combinations
from typing import List, Dict, Optional, Tuple

import config
from src.common.models import Message, StaticAnalysisReport
from src.semantic.preprocessor import SemanticPreprocessor, CompressedEvent
from src.semantic.memory import generate_static_baseline, GroupMemoryManager
from src.semantic.agents import (
    EventSummarizerAgent,
    EventReport,
    PersonalityRoasterAgent,
    PersonalityReport,
    RelationshipGuruAgent,
    RelationshipReport,
    GroupTherapistAgent,
    GroupReport,
)
from src.reporting import ReportSanitizer, ReportGenerator

class SemanticOrchestrator:
    """
    Coordinates the multi-agent semantic pipeline:
    1. Preprocesses and compresses events into artifacts/{chat}/events/E{id}.txt
    2. Builds purely objective mathematical baseline anchor & dynamic decay memory manager
    3. Executes Agent 1 (Event Summarizer) with adaptive rolling lore updates
    4. Executes Agent 2 (Personality Roaster) with trait marking gating
    5. Executes Agent 3 (Relationship Guru) with pairwise interaction gating and pruning
    6. Executes Agent 4 (Group Therapist) for macro diagnosis
    7. Compiles sanitized 5-tab HTML dossier via dedicated Report Generator Engine
    """

    def __init__(self, chat_name: str, outputs_dir: Optional[str] = None):
        self.chat_name = chat_name
        self.outputs_dir = outputs_dir or os.path.join(config.OUTPUTS_DIR, chat_name)
        os.makedirs(self.outputs_dir, exist_ok=True)

    def run(
        self,
        messages: List[Message],
        static_report: Optional[StaticAnalysisReport] = None,
        max_events_to_analyze: Optional[int] = None,
    ) -> str:
        print(f"\n[*] Starting Semantic Analysis Pipeline for '{self.chat_name}'...")

        # -------------------------------------------------------------
        # Stage 1: Semantic Preprocessing & Event Chunking
        # -------------------------------------------------------------
        print("[1/6] Running Semantic Preprocessor...")
        preprocessor = SemanticPreprocessor(inactivity_gap_hours=config.INACTIVITY_GAP_HOURS)
        compressed_events = preprocessor.process_and_save(self.chat_name, messages)
        print(f"      [+] Compressed {len(compressed_events)} events into 'artifacts/{self.chat_name}/events/'")

        if not compressed_events:
            print("      [!] No conversation events identified for analysis.")
            return ""

        compressed_map = {e.event_id: e for e in compressed_events}
        name_to_code, code_to_name = preprocessor.build_user_maps(messages)

        # -------------------------------------------------------------
        # Stage 2: Objective Baseline Anchor & Memory Schedule Setup
        # -------------------------------------------------------------
        print("[2/6] Initializing Dynamic Decay Memory Manager & Statistical Baseline...")
        group_baseline = generate_static_baseline(static_report) if static_report else "No static baseline."
        memory_manager = GroupMemoryManager(self.chat_name, len(messages))

        print(f"      [i] Chat Size Class: {memory_manager.size_class}")
        print(f"      [i] Bootstrap Budget: {memory_manager.alpha_messages:,} msgs | Calibration: {memory_manager.beta_messages:,} msgs")

        # -------------------------------------------------------------
        # Stage 3: Agent 1 - Event Summarizer with Adaptive Memory
        # -------------------------------------------------------------
        events_to_process = compressed_events[:max_events_to_analyze] if max_events_to_analyze else compressed_events
        print(f"[3/6] Running Agent 1: Event Summarizer across {len(events_to_process)} events...")

        agent1 = EventSummarizerAgent(self.chat_name)
        event_reports: List[EventReport] = []
        cumulative_msgs = 0

        for idx, ev in enumerate(events_to_process, start=1):
            cumulative_msgs += ev.message_count
            memory_str = memory_manager.get_memory_context_string()

            # Summarize event
            report = agent1.summarize_event(ev, group_baseline, memory_str)
            event_reports.append(report)

            # Check dynamic schedule update trigger
            if memory_manager.should_update(cumulative_msgs, report.impact_strength):
                phase_name, req_thresh = memory_manager.get_phase_and_threshold(cumulative_msgs)
                print(f"      [⚡] Lore Update ({phase_name} Phase): Event {report.event_id} (Impact: {report.impact_strength}) -> Updating group memory...")
                memory_manager.update_with_event(report.report_md)

        event_id_to_name = {r.event_id: r.event_name for r in event_reports}
        print(f"      [+] Agent 1 complete: {len(event_reports)} event reports generated in 'outputs/{self.chat_name}/event_reports/'")

        # -------------------------------------------------------------
        # Stage 4: Agent 2 - Personality Roaster
        # -------------------------------------------------------------
        sorted_members = sorted(code_to_name.items(), key=lambda x: x[0])
        print(f"[4/6] Running Agent 2: Personality Roaster for {len(sorted_members)} members...")

        agent2 = PersonalityRoasterAgent(self.chat_name)
        personality_reports: List[PersonalityReport] = []
        static_stats_map = {m.name: m for m in static_report.member_stats} if static_report else {}

        for user_code, member_name in sorted_members:
            m_stats = static_stats_map.get(member_name)
            p_report = agent2.generate_dossier(
                user_code=user_code,
                member_name=member_name,
                member_stats=m_stats,
                event_reports=event_reports,
                compressed_events_map=compressed_map,
                group_baseline=group_baseline,
                group_memory_str=memory_manager.get_memory_context_string(),
            )
            personality_reports.append(p_report)

        print(f"      [+] Agent 2 complete: {len(personality_reports)} personality dossiers compiled.")

        # -------------------------------------------------------------
        # Stage 5: Agent 3 - Relationship Guru
        # -------------------------------------------------------------
        all_codes = sorted(list(code_to_name.keys()))
        pairs = list(combinations(all_codes, 2))
        print(f"[5/6] Running Agent 3: Relationship Guru for {len(pairs)} member pairs...")

        agent3 = RelationshipGuruAgent(self.chat_name)
        relationship_reports: List[RelationshipReport] = []

        for u1, u2 in pairs:
            u1_name = code_to_name[u1]
            u2_name = code_to_name[u2]
            r_report = agent3.evaluate_pair(
                u1_code=u1,
                u1_name=u1_name,
                u2_code=u2,
                u2_name=u2_name,
                event_reports=event_reports,
                compressed_events_map=compressed_map,
                group_baseline=group_baseline,
                group_memory_str=memory_manager.get_memory_context_string(),
            )
            relationship_reports.append(r_report)

        active_pairs_count = len([r for r in relationship_reports if r.strength_score > 1])
        print(f"      [+] Agent 3 complete: {len(relationship_reports)} pair profiles evaluated ({active_pairs_count} active, {len(relationship_reports) - active_pairs_count} pruned).")

        # -------------------------------------------------------------
        # Stage 6: Agent 4 - Group Therapist & Dedicated Report Compiler
        # -------------------------------------------------------------
        print("[6/6] Running Agent 4: Group Therapist & Report Generator...")
        agent4 = GroupTherapistAgent(self.chat_name)
        group_report = agent4.synthesize(
            group_name=self.chat_name,
            event_reports=event_reports,
            personality_reports=personality_reports,
            relationship_reports=relationship_reports,
            compressed_events_map=compressed_map,
            group_baseline=group_baseline,
            group_memory_str=memory_manager.get_memory_context_string(),
        )
        print(f"      [+] Agent 4 complete: Master group diagnosis formulated ({group_report.group_identity} {group_report.group_apt_emoji}).")

        # Compile Dedicated 5-Tab HTML Report
        print("      [*] Compiling unified 5-tab HTML report with token & formula sanitization...")
        sanitizer = ReportSanitizer(code_to_name=code_to_name, event_id_to_name=event_id_to_name)
        generator = ReportGenerator(sanitizer)
        final_html_path = generator.generate(
            group_name=self.chat_name,
            static_report=static_report,
            event_reports=event_reports,
            personality_reports=personality_reports,
            relationship_reports=relationship_reports,
            group_report=group_report,
        )

        print(f"[🎉] UNIFIED TABBED HTML DOSSIER READY: {final_html_path}")
        return final_html_path
