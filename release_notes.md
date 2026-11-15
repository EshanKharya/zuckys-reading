# Release Notes - v1.0

## Features Supported

### WhatsApp Chat Parser
- Auto-detection of 12-hour (AM/PM) and 24-hour timestamp formats.
- Directional Unicode and invisible control character normalization (`\u200e`, `\u202f`).
- Multi-line message continuation parsing.
- Automated WhatsApp system notification filtering.

### Deterministic Static Metrics Engine
- Member verbosity analysis (words per message, characters per message).
- Pure text response speed tracking (average and median; excludes media).
- Yap Streak calculation (longest consecutive text message run by a single sender).
- Sahara Desert Index (dry text message percentage).
- Night Owl activity percentage (12:00 AM – 5:00 AM).
- Vocabulary size calculation for individuals and the group.
- Longest active and inactive streaks with exact start and end dates.
- Conversation initiation and termination tracking (2.0-hour silence threshold).

### Visualizations & Reporting
- Standalone, dark-mode interactive HTML report generated at `reports/Zucky_read_<chat_name>.html`.
- 4 interactive Chart.js visualizations:
  - Traffic Share donut chart with white sector borders.
  - 24-hour activity distribution with peak hour highlight.
  - Weekday distribution with peak day highlight.
  - Monthly progression trajectory with peak volume beacon.
- Top 20 Word Cloud vector SVG with golden-angle spiral placement.
- Automated superlative awards and member roast taglines.
