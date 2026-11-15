# Zucky's Reading

An unfiltered WhatsApp chat analyzer that parses exported group chats (`.txt`) and generates a dark-mode interactive HTML dossier featuring deterministic statistical metrics, roasts, superlatives, and charts.

## Features
- **Deterministic Static Metrics:** Verbosity, response speeds (text only), Yap Streak (consecutive text runs, media excluded), Sahara Desert Index (dry text percentage), and vocabulary sizes.
- **Group Analytics:** 24-hour hourly distribution, weekday patterns, monthly volume progression, and active/inactive streaks with exact dates.
- **Word Cloud:** Top 20 most frequent words placed via golden-angle spiral vector SVG.
- **Interactive Report:** Single-file responsive dashboard (`reports/Zucky_read_<chat_name>.html`) powered by Tailwind CSS and Chart.js.

## Requirements
- Python 3.10+
- Dependencies: `pydantic`, `emoji`

## How to Run
```bash
python main.py --chat "chats/<chat_export_file>.txt"
```
Or specify a custom output path:
```bash
python main.py --chat "chats/<chat_export_file>.txt" --out "reports/custom_report.html"
```
