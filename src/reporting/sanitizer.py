import re
from typing import Dict, Optional

class ReportSanitizer:
    """
    Sanitizes raw forensic reports for end-user presentation:
    1. Replaces user codes (%U1%, %U2%) with actual contact display names.
    2. Replaces raw event IDs (E14, E42) with human-readable event titles.
    3. Strips internal intermediate mathematical scoring parameters.
    """

    def __init__(self, code_to_name: Dict[str, str], event_id_to_name: Dict[str, str]):
        self.code_to_name = code_to_name
        self.event_id_to_name = event_id_to_name

    def sanitize_user_codes(self, text: str) -> str:
        """Replaces all occurrences of %U#% with the real contact display name."""
        if not text:
            return ""
        result = text
        # Replace in descending order of code length if needed
        for code, name in self.code_to_name.items():
            result = result.replace(code, name)
        return result

    def sanitize_event_ids(self, text: str) -> str:
        """Replaces standalone E# identifiers with descriptive event titles."""
        if not text:
            return ""

        def _replace_id(match):
            ev_id = match.group(0)
            if ev_id in self.event_id_to_name:
                title = self.event_id_to_name[ev_id]
                return f"\"{title}\""
            return ev_id

        # Replace standalone event tokens like E1, E14, E245
        return re.sub(r"\bE\d+\b", _replace_id, text)

    def sanitize_internal_math(self, text: str) -> str:
        """Removes algorithmic formula artifacts and internal intermediate metrics."""
        if not text:
            return ""
        patterns = [
            r"trait_marking_score\s*=\s*[^,\n\)]+",
            r"interaction_score\s*=\s*[^,\n\)]+",
            r"group_impact_score\s*=\s*[^,\n\)]+",
            r"Geometric mean[^,\n\)]+",
        ]
        result = text
        for pat in patterns:
            result = re.sub(pat, "", result, flags=re.IGNORECASE)
        return result

    def sanitize(self, text: str) -> str:
        """Applies full sanitization pipeline to a string."""
        if not text:
            return ""
        clean = self.sanitize_internal_math(text)
        clean = self.sanitize_event_ids(clean)
        clean = self.sanitize_user_codes(clean)
        return clean
