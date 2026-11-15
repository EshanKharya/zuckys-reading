import re
import os
from datetime import datetime
from typing import List, Tuple, Optional
from src.models import Message

# Matches standard WhatsApp export line:
# e.g.: "08/04/26, 8:45 pm - " or "11/11/2026, 10:33 PM - "
TIMESTAMP_REGEX = re.compile(
    r"^(\d{1,4}[/-]\d{1,2}[/-]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s*[ap]m)\s+-\s+(.*)$",
    re.IGNORECASE
)

# Invisible / Unicode formatting characters to clean up
UNICODE_CLEAN_REGEX = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")

def clean_unicode(text: str) -> str:
    """Removes directional formatting, non-standard zero-width characters."""
    return UNICODE_CLEAN_REGEX.sub("", text)

def normalize_time_str(time_str: str) -> str:
    """Replaces narrow no-break space and cleans time strings."""
    return time_str.replace("\u202f", " ").replace("\xa0", " ").strip().lower()

class WhatsAppParser:
    def __init__(self, date_format: Optional[str] = None):
        self.date_format = date_format

    def detect_date_format(self, lines: List[str]) -> str:
        """
        Auto-detects whether the date is DD/MM/YY or MM/DD/YY based on occurrences > 12.
        Default to %d/%m/%y.
        """
        first_field_gt_12 = 0
        second_field_gt_12 = 0
        
        for line in lines[:500]:
            m = TIMESTAMP_REGEX.match(line)
            if m:
                d_part = m.group(1).replace("-", "/")
                parts = d_part.split("/")
                if len(parts) == 3:
                    try:
                        v1, v2 = int(parts[0]), int(parts[1])
                        if v1 > 12:
                            first_field_gt_12 += 1
                        if v2 > 12:
                            second_field_gt_12 += 1
                    except ValueError:
                        pass
                        
        year_format = "%y"
        # Check year length
        for line in lines[:50]:
            m = TIMESTAMP_REGEX.match(line)
            if m:
                parts = m.group(1).replace("-", "/").split("/")
                if len(parts) == 3 and len(parts[2]) == 4:
                    year_format = "%Y"
                    break

        if first_field_gt_12 > second_field_gt_12:
            return f"%d/%m/{year_format}"
        elif second_field_gt_12 > first_field_gt_12:
            return f"%m/%d/{year_format}"
        else:
            # Default fallback for Indian/UK exports
            return f"%d/%m/{year_format}"

    def parse_file(self, file_path: str) -> Tuple[str, List[Message]]:
        """
        Parses a WhatsApp chat export file into structured Message objects.
        Returns (group_name, list_of_messages).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Chat export file not found: {file_path}")

        # Inferred group name from filename: e.g. "WhatsApp Chat with BTC sher 🦁.txt" -> "BTC sher 🦁"
        base_name = os.path.basename(file_path)
        group_name = base_name.replace("WhatsApp Chat with ", "").replace(".txt", "").strip()

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if not self.date_format:
            self.date_format = self.detect_date_format(lines)

        messages: List[Message] = []
        current_msg: Optional[Message] = None

        for raw_line in lines:
            line = clean_unicode(raw_line)
            match = TIMESTAMP_REGEX.match(line)
            
            if match:
                date_str, time_str, body = match.groups()
                time_clean = normalize_time_str(time_str)
                full_dt_str = f"{date_str} {time_clean}"
                
                try:
                    dt = datetime.strptime(full_dt_str, f"{self.date_format} %I:%M %p")
                except ValueError:
                    try:
                        # Try with seconds if present
                        dt = datetime.strptime(full_dt_str, f"{self.date_format} %I:%M:%S %p")
                    except ValueError:
                        # Skip unparseable timestamp
                        continue

                # Check if system message or user message
                # User messages have "Sender: Message"
                if ": " in body:
                    sender, content = body.split(": ", 1)
                    sender = sender.strip()
                    content = content.rstrip("\r\n")
                    is_media = (content.strip() == "<Media omitted>")
                    
                    current_msg = Message(
                        timestamp=dt,
                        sender=sender,
                        content=content,
                        is_media=is_media,
                        is_system=False
                    )
                    messages.append(current_msg)
                else:
                    # System message
                    sys_content = body.rstrip("\r\n")
                    # Check if group name change is mentioned
                    name_change = re.search(r'changed the group name (?:from ".*" )?to "(.*)"', sys_content)
                    if name_change:
                        group_name = name_change.group(1).strip()
                        
                    current_msg = Message(
                        timestamp=dt,
                        sender="System",
                        content=sys_content,
                        is_media=False,
                        is_system=True
                    )
                    messages.append(current_msg)
            else:
                # Continuation of multi-line message
                if current_msg:
                    current_msg.content += "\n" + line.rstrip("\r\n")

        return group_name, messages

