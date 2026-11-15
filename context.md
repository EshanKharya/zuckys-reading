# What we are building - Zucky's Reading

An application that takes a WhatsApp chat export (.txt) as input and generates comprehensive analytical dossiers. Analysis is bifurcated into two strictly segregated engines: **Static Analysis** and **Semantic Analysis**.

---

## 1. Static Analysis (Release v1.0)

Generates deterministic statistical metrics and renders an interactive HTML report (`Zucky_read_<chat>.html`).

### Member-wise Analysis:
- Total messages sent & text messages (excluding media)
- Percentage share of group traffic
- Average verbosity (words/message, chars/message)
- Average & median response time (active conversation turns)
- Emoji-to-word ratio and top 3 emojis
- Number of conversations started (first message after $\ge$ 2h silence)
- Number of conversations ended / killed (last message before $\ge$ 2h silence)
- Media count shared (<Media omitted>)
- Vocabulary size (count of unique words used by individual)
- Yap Streak (longest consecutive run of text messages without reply; media excluded)
- Night Owl percentage (12 AM - 5 AM)
- Sahara Desert Index (dry text percentage on pure text messages)
- Unfiltered banter title and roast tagline

### Group-wise Analysis:
- Total messages, words, media, and unique conversations
- Active days and total days
- Group vocabulary size (total distinct words)
- Top 20 most used words rendered as a golden-angle Word Cloud image
- Longest active streak (days + exact start/end dates)
- Longest inactive streak (days + exact start/end dates)
- 24-hour activity distribution with peak hour highlighted
- Weekday distribution with peak day highlighted
- Monthly progression trajectory with peak volume beacon

---

## 2. Semantic Analysis (Release v2.0)

Runs an agentic multi-stage pipeline utilizing local LLM inference on an NVIDIA RTX 5050 (8GB VRAM).

### Event Chunking & Preprocessing:
1. **Event Delimitation:** 2-hour inactivity boundary (`INACTIVITY_GAP_HOURS = 2.0`).
2. **User Code Anonymization:** Replace full names and `@` mentions with alphabetical `%U1%`, `%U2%` tokens. Include mapping table in event headers.
3. **Message Merging:** Merge uninterrupted consecutive messages from the same author using `%%` demarcation.
4. **Emoji & Noise Compression:** Contiguous emoji runs $\ge 3$ become `%{emoji}x{count}%`. Strip system notices, deleted message tags, and media omitted placeholders.
5. **Storage:** Save compressed chunks to `artifacts/{chat_name}/events/E{id}.txt`.

### Multi-Agent Pipeline:
1. **Agent 1: Event Summarizer (Stateless):** Evaluates event topic, who said what, hot takes, banter, emotional disturbances, and verbatim notable quotes. Assigns `impact_strength` (1–10) and `individual_involvement_scores` (1–10). Outputs `outputs/{chat_name}/event_reports/E{id}.md` with user mapping table and appends to `outputs/{chat_name}/event_map.csv`.
2. **Agent 2: Personality Roaster (Stateful Accumulator):** Processes events gated by `trait_marking_score = involvement * impact`. Top 20% receives raw event + report; Tier 2 (20–50% or score > 50) receives batched reports (up to 10 reports / 4k tokens). Sorted chronologically. Progressively builds persona, callbacks, strengths/weaknesses, and top 5 event IDs.
3. **Agent 3: Relationship Guru (Stateful Accumulator):** Evaluates pairs gated by `interaction_score = sqrt(score_U1 * score_U2)`. Pairs with 0 co-involvement bypass LLM. Evaluates relationship timeline, traits, and strength score (1–10).
4. **Agent 4: Group Therapist:** Synthesizes top 20% group impact events + Personality + Relationship reports into group identity, group timeline, and master group roast with top 10 event IDs.

---

## 3. Dedicated Report Generator Engine & Unified Tabbed HTML Report (`src/reporting/`)

A dedicated report generation subsystem located under **`src/reporting/`** reads the structured outputs from both the Static Analysis and Semantic Analysis engines, sanitizes all internal identifiers, and compiles them into a single-file, interactive 5-tab dark-mode HTML report at `reports/Zucky_read_<chat_name>.html`.

### Strict Sanitization Contract:
- **Omit User Codes:** Every `%U1%`, `%U2%`, etc. token is mapped back to the member's friendly contact display name.
- **Omit Raw Event IDs:** Raw event keys like `E14` or `E42` are transformed into descriptive, readable event titles (e.g., *"The Great RCB Banter on 12 Apr 2026"*).
- **Omit Internal Scoring Parameters:** Internal calculation metrics (`trait_marking_score`, geometric mean formulas, raw percentile cutoffs) are strictly omitted from the report. Only intuitive, user-friendly indicators (Relationship Strength 1–10, Involvement Level, Impact Rating) are displayed.

### Interactive 5-Tab Navigation Structure:
1. **🛋️ Group Therapy & Identity:** Group Identity title, apt emoji, Group Evolution Timeline, and Unfiltered Master Group Roast (from Agent 4).
2. **📊 Static Analysis & Hall of Shame:** High-level KPIs, 6 Superlative awards, 4 interactive Chart.js charts (with peak highlights & white pie borders), and the Top 20 Word Cloud image.
3. **👤 Member Stats & Personality Dossiers:** Side-by-side member cards (2 per row on desktop) combining static stats (verbosity, response speed, yap streak, dry rate, vocab size) with Agent 2's character roasts, strengths/weaknesses, and top 5 event callbacks.
4. **🤝 Relationship Guru Matrix:** Interactive dyadic cards showing pair dynamics, couple titles, evolution timelines, and strength scores (from Agent 3). Pruned pairs show *"Zero recorded interaction"*.
5. **📜 Canon Events Archive:** Chronological showcase of high-impact events with summaries, participant mapping, hot takes, banter, and notable quotes (from Agent 1).
6. **Footer:** Generation timestamp and private local inference badge.

---

## 4. Version Control Structure & Branching Lifecycle

```
main (Latest LTS Production)
 ├── release-1.0 (Static Analysis Engine v1.0 Archive)
 └── develop (Active Integration & Experimentation Ground)
      ├── f-modular-refactor
      ├── f-semantic-prep
      └── f-semantic-agents
```

### Branch Rules:
1. **`main`:** Stable LTS. Direct commits forbidden. Holds production releases merged from verified `release-*` branches. Auto-delete on merge: **DISABLED**.
2. **`release-<version>`:** Milestone archive branches cut from `develop`. Must contain a strictly non-verbose **`release_notes.md`** describing features in that specific version only. Auto-delete on merge: **DISABLED**.
3. **`develop`:** Integration ground cut from `main`. All feature branches branch from and merge back into `develop`. Auto-delete on merge: **DISABLED**.
4. **`f-<feature_name>`:** Isolated feature branches cut from `develop`. Merged only upon passing all checks and receiving user authorization.

---

## 5. Hard Gates & Project Invariants

> [!CAUTION]
> ### 1. Strict Merge Gate (Zero Autonomous Merges)
> The assistant will **never merge any branch autonomously** (`f-*` into `develop`, `develop` into `release-*`, or `release-*` into `main`). Work remains isolated on its respective branch. Merges occur **only after the user personally tests the branch and gives explicit written instruction**.

> [!IMPORTANT]
> ### 2. Data Privacy Gate
> User chat transcripts (`chats/*.txt`) and sensitive personal files must **never be tracked or committed to Git**. `.gitignore` must strictly exclude `chats/`, `.env`, `.venv/`, `artifacts/`, `outputs/`, and `reports/`.

> [!IMPORTANT]
> ### 3. Hardware & VRAM Safety Gate
> All local LLM inference is strictly bound to the **NVIDIA GeForce RTX 5050 8GB VRAM envelope**:
> - Only **one LLM instance** loaded in memory at any time (e.g. `qwen2.5:7b-instruct-q4_K_M` ~4.7 GB).
> - Never run parallel LLM worker processes.
> - Context adaptation is achieved via **Two-Pass Baseline + Rolling Memory (`group_memory.json`)**, keeping prompt sizes constant and bounded.
> - Batch payload sizes capped at **10 reports or 4,000 tokens**.

> [!NOTE]
> ### 4. Architectural Decoupling Gate
> - **Static and Semantic engines must be strictly segregated** under `src/static/` and `src/semantic/`. Changes in one must never break or depend on the other.
> - **Agent definitions must live in editable markdown files** under `prompts/*.md`, loaded at runtime.
> - **LLM provider must be isolated** in `src/llm/client.py`. Changing models or providers must have zero impact on orchestration or agents.
> - **Zero CLI Arguments:** `python main.py` runs with zero arguments, reading runtime parameters from `.env` and thresholds from `config.py`.
