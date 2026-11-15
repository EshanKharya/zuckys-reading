import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==========================================
# Runtime Environment Settings (.env)
# ==========================================
APP_VERSION: str = os.getenv("APP_VERSION", "v1.0")
CHAT_EXPORT_PATH: str = os.getenv("CHAT_EXPORT_PATH", "chats/WhatsApp Chat with BTC sher 🦁.txt")
ENABLE_STATIC_ANALYSIS: bool = os.getenv("ENABLE_STATIC_ANALYSIS", "true").strip().lower() in ("true", "1", "yes")
ENABLE_SEMANTIC_ANALYSIS: bool = os.getenv("ENABLE_SEMANTIC_ANALYSIS", "false").strip().lower() in ("true", "1", "yes")

# LLM Configuration
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen2.5:7b")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.7"))
MODEL_CONTEXT_WINDOW: int = int(os.getenv("MODEL_CONTEXT_WINDOW", "8192"))

# ==========================================
# Computational Thresholds & Limits
# ==========================================
# Event Delimitation: silence gap in hours to mark separate conversations
INACTIVITY_GAP_HOURS: float = 2.0

# Multi-Agent Gating Thresholds
TIER_1_PERCENTILE: float = 0.20          # Top 20% by trait/interaction score (Full raw event + report)
TIER_2_PERCENTILE: float = 0.50          # Top 20%-50%
TIER_2_MIN_SCORE: float = 50.0           # Or absolute score > 50

# Payload Constraints (RTX 5050 8GB VRAM envelope safety)
TIER_2_BATCH_MAX_REPORTS: int = 10       # Max reports per batched LLM prompt
TIER_2_BATCH_MAX_TOKENS: int = 4000      # Max payload tokens per batch

# Group Memory Update Trigger
GROUP_CANON_IMPACT_THRESHOLD: int = 7    # Impact score >= 7 triggers rolling memory update

# Relationship Matrix Optimization
MIN_SHARED_CONVERSATIONS: int = 1        # Pairs with < 1 shared event bypass LLM calls

# Directory Paths
REPORTS_DIR: str = "reports"
OUTPUTS_DIR: str = "outputs"
ARTIFACTS_DIR: str = "artifacts"
ASSETS_DIR: str = "assets"
PROMPTS_DIR: str = "prompts"

