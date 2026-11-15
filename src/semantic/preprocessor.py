import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import emoji

import config
from src.common.models import Message

@dataclass
class CompressedEvent:
    event_id: str
    start_time: datetime
    end_time: datetime
    duration_str: str
    involved_user_map: Dict[str, str]   # %U#% -> Full Name (only participants in this event)
    all_user_map: Dict[str, str]        # %U#% -> Full Name (all group members)
    compressed_text: str
    message_count: int
    word_count: int
    file_path: Optional[str] = None

class SemanticPreprocessor:
    """
    Compresses WhatsApp chat exports into dense, anonymized event chunks for LLM ingestion.
    Enforces 2h boundary, alphabetical %U#% codes, %% message merging, and emoji compression.
    """

    SYSTEM_PATTERNS = [
        re.compile(r"<Media omitted>", re.IGNORECASE),
        re.compile(r"This message was deleted", re.IGNORECASE),
        re.compile(r"You deleted this message", re.IGNORECASE),
        re.compile(r".*added.*", re.IGNORECASE),
        re.compile(r".*left.*", re.IGNORECASE),
        re.compile(r".*changed the subject.*", re.IGNORECASE),
        re.compile(r".*changed group (icon|description|settings).*", re.IGNORECASE),
        re.compile(r".*security code changed.*", re.IGNORECASE),
    ]

    def __init__(self, inactivity_gap_hours: float = 2.0):
        self.inactivity_gap_hours = inactivity_gap_hours

    @staticmethod
    def build_user_maps(messages: List[Message]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Builds alphabetical user code mappings: %U1%, %U2%, ... based on member names.
        Returns:
            name_to_code: {"Aryan Srivastav": "%U1%", ...}
            code_to_name: {"%U1%": "Aryan Srivastav", ...}
        """
        all_senders = {m.sender for m in messages if m.sender and m.sender != "Meta AI"}
        sorted_senders = sorted(list(all_senders), key=lambda s: s.lower())

        name_to_code: Dict[str, str] = {}
        code_to_name: Dict[str, str] = {}
        for idx, name in enumerate(sorted_senders, start=1):
            code = f"%U{idx}%"
            name_to_code[name] = code
            code_to_name[code] = name

        return name_to_code, code_to_name

    @staticmethod
    def compress_emojis(text: str) -> str:
        """
        Compresses contiguous runs of identical emojis >= 3 to %{emoji}x{count}%.
        E.g., 😂😂😂😂😂 -> %😂x5%
        """
        if not text:
            return text

        # Helper to compress runs of the same character if it's an emoji
        def _replace_emoji_runs(m):
            char = m.group(1)
            count = len(m.group(0))
            if emoji.is_emoji(char):
                return f"%{char}x{count}%"
            return m.group(0)

        # Matches 3 or more repeating identical characters
        return re.sub(r"(.)\1{2,}", _replace_emoji_runs, text)

    def is_noise_or_system(self, text: str) -> bool:
        """Checks if a message text is system noise, deleted, or media omitted."""
        stripped = text.strip()
        if not stripped:
            return True
        for pattern in self.SYSTEM_PATTERNS:
            if pattern.fullmatch(stripped):
                return True
        return False

    def anonymize_text(self, text: str, name_to_code: Dict[str, str]) -> str:
        """
        Replaces contact names and @mentions with their respective %U#% codes.
        Names are replaced in order of descending length to prevent partial matching.
        """
        result = text
        # Clean WhatsApp bracketed mentions: ⁨+91 98765 43210⁩ or ⁨Name⁩
        result = re.sub(r"[\u2066\u2067\u2068\u2069]", "", result)

        # Sort by descending length so longer full names are replaced before shorter nicknames
        sorted_names = sorted(name_to_code.keys(), key=lambda n: len(n), reverse=True)
        for name in sorted_names:
            code = name_to_code[name]
            # Match @Name or @+91... or exact name
            pattern = re.compile(rf"@?{re.escape(name)}", re.IGNORECASE)
            result = pattern.sub(code, result)

        return result

    def format_duration(self, start: datetime, end: datetime) -> str:
        """Returns human-readable duration, e.g. '1h 24m' or '45m' or '< 1m'."""
        delta = end - start
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return "< 1m"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes:02d}m"
        return f"{minutes}m"

    def segment_into_events(self, messages: List[Message]) -> List[List[Message]]:
        """Groups messages into events separated by inactivity >= inactivity_gap_hours."""
        events: List[List[Message]] = []
        current_event: List[Message] = []
        last_dt: Optional[datetime] = None
        gap_delta = timedelta(hours=self.inactivity_gap_hours)

        for msg in messages:
            if msg.sender == "Meta AI":
                continue

            if last_dt is None or (msg.timestamp - last_dt) >= gap_delta:
                if current_event:
                    events.append(current_event)
                current_event = [msg]
            else:
                current_event.append(msg)
            last_dt = msg.timestamp

        if current_event:
            events.append(current_event)

        return events

    def compress_single_event(
        self,
        event_id: str,
        event_messages: List[Message],
        name_to_code: Dict[str, str],
        code_to_name: Dict[str, str],
    ) -> Optional[CompressedEvent]:
        """Compresses a single event chunk following all compression rules."""
        if not event_messages:
            return None

        start_time = event_messages[0].timestamp
        end_time = event_messages[-1].timestamp
        duration_str = self.format_duration(start_time, end_time)

        # 1. Filter noise & merge consecutive messages by the same sender
        merged_turns: List[Tuple[str, str]] = []  # [(sender_code, merged_text), ...]
        current_sender_code: Optional[str] = None
        current_texts: List[str] = []
        total_raw_words = 0
        valid_message_count = 0
        involved_codes: Set[str] = set()

        for msg in event_messages:
            if self.is_noise_or_system(msg.content):
                continue

            sender_code = name_to_code.get(msg.sender, msg.sender)
            involved_codes.add(sender_code)
            valid_message_count += 1

            # Clean and compress emojis
            clean_content = self.compress_emojis(msg.content.strip())
            # Anonymize mentions in message content
            clean_content = self.anonymize_text(clean_content, name_to_code)

            words = clean_content.split()
            total_raw_words += len(words)

            if current_sender_code == sender_code:
                current_texts.append(clean_content)
            else:
                if current_sender_code is not None and current_texts:
                    merged_content = " %% ".join(current_texts)
                    merged_turns.append((current_sender_code, merged_content))
                current_sender_code = sender_code
                current_texts = [clean_content]

        if current_sender_code is not None and current_texts:
            merged_content = " %% ".join(current_texts)
            merged_turns.append((current_sender_code, merged_content))

        # If after filtering all messages were noise (e.g. only media omitted)
        if not merged_turns:
            return None

        # 2. Build Involved Users map
        involved_user_map = {
            code: code_to_name[code]
            for code in sorted(list(involved_codes))
            if code in code_to_name
        }

        # 3. Assemble Header
        header_lines = [
            f"=== EVENT {event_id} ===",
            f"Start: {start_time.strftime('%Y-%m-%d %H:%M')}",
            f"Duration: {duration_str}",
            f"Messages: {valid_message_count} | Words: {total_raw_words}",
            f"Active Participants: {len(involved_user_map)}",
            "Involved Users:",
        ]
        for code, name in involved_user_map.items():
            header_lines.append(f"- {code}: {name}")
        header_lines.append("=========================")
        header_lines.append("")

        # 4. Assemble Body
        body_lines = [f"{sender}: {text}" for sender, text in merged_turns]
        full_text = "\n".join(header_lines + body_lines)

        return CompressedEvent(
            event_id=event_id,
            start_time=start_time,
            end_time=end_time,
            duration_str=duration_str,
            involved_user_map=involved_user_map,
            all_user_map=code_to_name,
            compressed_text=full_text,
            message_count=valid_message_count,
            word_count=total_raw_words,
        )

    def process_and_save(
        self,
        group_name: str,
        messages: List[Message],
        output_dir: Optional[str] = None,
    ) -> List[CompressedEvent]:
        """
        Segments messages, applies full compression, and writes artifacts to
        artifacts/{group_name}/events/E{id}.txt.
        """
        name_to_code, code_to_name = self.build_user_maps(messages)
        raw_events = self.segment_into_events(messages)

        base_output_dir = output_dir or os.path.join(config.ARTIFACTS_DIR, group_name, "events")
        os.makedirs(base_output_dir, exist_ok=True)

        compressed_events: List[CompressedEvent] = []
        event_counter = 1

        for raw_event in raw_events:
            event_id = f"E{event_counter}"
            comp_event = self.compress_single_event(
                event_id=event_id,
                event_messages=raw_event,
                name_to_code=name_to_code,
                code_to_name=code_to_name,
            )
            if comp_event is not None:
                file_path = os.path.join(base_output_dir, f"{event_id}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(comp_event.compressed_text)
                comp_event.file_path = file_path
                compressed_events.append(comp_event)
                event_counter += 1

        return compressed_events
