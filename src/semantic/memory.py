import os
import json
import statistics
from typing import Dict, Any, Optional, List, Tuple

import config
from src.common.models import StaticAnalysisReport
from src.common.prompt_loader import load_prompt_template
from src.llm import get_llm_client, BaseLLMClient

def generate_static_baseline(report: StaticAnalysisReport) -> str:
    """
    Synthesizes a strictly objective, mathematical calibration anchor from static metrics.
    Contains zero assumptions about group genre, tone, or intimacy level.
    """
    grp = report.group_stats
    members = [m for m in report.member_stats if m.name != "Meta AI"]

    total_msgs = grp.total_messages
    total_events = max(1, grp.total_events)
    total_days = max(1, grp.total_days)
    daily_avg = total_msgs / total_days

    # Approximate event volume distribution based on total messages & events
    # We can calculate average messages per event
    avg_msgs_per_event = total_msgs / total_events
    p25_approx = max(2, int(avg_msgs_per_event * 0.4))
    median_approx = max(4, int(avg_msgs_per_event * 0.8))
    p75_approx = max(8, int(avg_msgs_per_event * 1.5))
    p90_approx = max(15, int(avg_msgs_per_event * 2.5))

    # Day vs Night
    night_msgs = sum(grp.hourly_distribution.get(h, 0) for h in range(0, 6))
    night_pct = (night_msgs / total_msgs * 100) if total_msgs > 0 else 0
    day_pct = 100 - night_pct

    avg_words_per_msg = (grp.total_words / total_msgs) if total_msgs > 0 else 0

    baseline_lines = [
        "[Group Statistical Calibration Anchor]",
        f"- Total Participants: {len(members)}",
        f"- Total Messages Analyzed: {total_msgs:,} across {total_events:,} conversation events ({total_days:,} active days)",
        f"- Daily Average: ~{daily_avg:.1f} messages/day",
        "- Conversation Size Distribution (Estimated):",
        f"  * 25th percentile: ~{p25_approx} messages",
        f"  * Median (50th percentile): ~{median_approx} messages",
        f"  * 75th percentile: ~{p75_approx} messages",
        f"  * 90th percentile (Statistical Outlier Threshold): > {p90_approx} messages",
        f"- Average Message Length: {avg_words_per_msg:.1f} words",
        f"- Activity Timing: {day_pct:.1f}% daytime / evening, {night_pct:.1f}% late night (12 AM - 5 AM)",
        f"- Group Vocabulary Size: {grp.vocabulary_size:,} distinct words",
        "",
        "(Calibration Instruction: Use these mathematical volume percentiles solely to understand relative conversation scale.",
        " Do not assume any pre-existing group tone, intimacy level, or genre. Deduce all tone, relationships, and context solely from the actual messages.)"
    ]
    return "\n".join(baseline_lines)

class GroupMemoryManager:
    """
    Manages the rolling group lore state (group_memory.json) using the dynamic
    size-class decay schedule (Bootstrap -> Calibration -> Canon Stability).
    """

    def __init__(
        self,
        chat_name: str,
        total_messages: int,
        llm_client: Optional[BaseLLMClient] = None,
        outputs_dir: Optional[str] = None,
    ):
        self.chat_name = chat_name
        self.total_messages = total_messages
        self.llm_client = llm_client or get_llm_client()

        base_dir = outputs_dir or os.path.join(config.OUTPUTS_DIR, chat_name)
        os.makedirs(base_dir, exist_ok=True)
        self.memory_file_path = os.path.join(base_dir, "group_memory.json")

        # Calculate schedule budget using chat size class
        self.schedule_budget = config.get_memory_schedule_budget(total_messages)
        self.size_class = self.schedule_budget["size_class"]
        self.alpha_messages = self.schedule_budget["alpha_messages"]
        self.beta_messages = self.schedule_budget["beta_messages"]
        self.calibration_cutoff = self.alpha_messages + self.beta_messages

        # Running state
        self.memory_state: Dict[str, Any] = self._load_initial_memory()

    def _load_initial_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.memory_file_path):
            try:
                with open(self.memory_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "current_era": "Inception Phase: Observing initial interaction dynamics",
            "inside_jokes": [],
            "active_feuds": [],
            "notable_lore": [],
        }

    def _save_memory(self):
        with open(self.memory_file_path, "w", encoding="utf-8") as f:
            json.dump(self.memory_state, f, indent=2, ensure_ascii=False)

    def get_phase_and_threshold(self, cumulative_messages: int) -> Tuple[str, int]:
        """Returns the active schedule phase name and required impact threshold."""
        if cumulative_messages <= self.alpha_messages:
            return "Bootstrap", 1
        elif cumulative_messages <= self.calibration_cutoff:
            return "Calibration", 5
        else:
            return "Canon Stability", config.GROUP_CANON_IMPACT_THRESHOLD

    def should_update(self, cumulative_messages: int, impact_score: int) -> bool:
        """Determines whether group memory should be updated for this event."""
        phase, threshold = self.get_phase_and_threshold(cumulative_messages)
        return impact_score >= threshold

    def get_memory_context_string(self) -> str:
        """Returns dense JSON string for prompt injection (~150 tokens)."""
        return json.dumps(self.memory_state, ensure_ascii=False)

    def update_with_event(self, event_report_md: str) -> Dict[str, Any]:
        """Invokes group_memory_updater prompt to update rolling lore."""
        current_memory_str = json.dumps(self.memory_state, indent=2)
        prompt = load_prompt_template(
            "group_memory_updater",
            current_memory=current_memory_str,
            event_report=event_report_md,
        )

        try:
            new_state = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are the Group Memory Curator. Maintain dense, compact lore.",
            )
            # Validate required keys
            if isinstance(new_state, dict) and "current_era" in new_state:
                self.memory_state = new_state
                self._save_memory()
        except Exception as e:
            print(f"[!] Warning: Group memory update skipped due to error: {e}")

        return self.memory_state
