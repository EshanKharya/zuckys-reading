# Zucky's Reading

An unfiltered WhatsApp chat analyzer that parses exported group chats (`.txt`) and generates a dark-mode interactive HTML dossier featuring deterministic statistical metrics, roasts, superlatives, and charts.

## Features
- **Deterministic Static Metrics:** Verbosity, response speeds (text only), Yap Streak (consecutive text runs, media excluded), Sahara Desert Index (dry text percentage), and vocabulary sizes.
- **Group Analytics:** 24-hour hourly distribution, weekday patterns, monthly volume progression, and active/inactive streaks with exact dates.
- **Word Cloud:** Top 20 most frequent words placed via golden-angle spiral vector SVG.
- **Semantic Preprocessing Engine:** 2-hour conversational event chunking, alphabetical `%U#%` user anonymization, `%%` message merging, and contiguous emoji compression (`%{emoji}x{count}%`). Saves dense event chunks to `artifacts/<group>/events/E<id>.txt`.
- **Editable Markdown Prompts:** Agent definitions externalized into runtime-loaded markdown files in `prompts/`.
- **Interactive Report:** Single-file responsive dashboard (`reports/Zucky_read_<chat_name>.html`) powered by Tailwind CSS and Chart.js.

## Requirements
- Python 3.10+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Configuration
Copy `.env.example` to `.env` and set your chat export path and subsystem toggles:
```bash
cp .env.example .env
```

Key variables in `.env`:
- `CHAT_EXPORT_PATH`: Path to WhatsApp chat export `.txt` file
- `ENABLE_STATIC_ANALYSIS`: Enable/disable static analysis (`true`/`false`)
- `ENABLE_SEMANTIC_ANALYSIS`: Enable/disable semantic analysis (`true`/`false`)
- `MODEL_NAME`: Local LLM model (default: `qwen2.5:7b`)

## How to Run
Run the pipeline with zero arguments:
```bash
python main.py
```
Reports are automatically generated and saved to `reports/Zucky_read_<chat_name>.html`.

## License & Copyright
Copyright © 2026 Eshan Kharya. All rights reserved.  
This project is proprietary and confidential. Not open source. Commercial or public distribution without explicit written permission is strictly prohibited.

