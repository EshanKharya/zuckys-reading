from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field

class Message(BaseModel):
    timestamp: datetime
    sender: str
    content: str
    is_media: bool = False
    is_system: bool = False

class MemberStats(BaseModel):
    name: str
    alias: str = ""
    total_messages: int = 0
    text_messages: int = 0  # Actual text messages sent (excluding media)
    percentage_of_total: float = 0.0
    total_words: int = 0
    total_chars: int = 0
    media_count: int = 0
    vocab_size: int = 0
    
    @property
    def vocabulary_size(self) -> int:
        return self.vocab_size  # Count of distinct words used by this member

    @property
    def words_per_message(self) -> float:
        return self.avg_words_per_message

    @property
    def longest_yap_streak(self) -> int:
        return self.max_consecutive_messages
    
    # Verbosity
    avg_words_per_message: float = 0.0
    avg_chars_per_message: float = 0.0
    
    # Response Time (in seconds/minutes)
    avg_response_time_seconds: float = 0.0
    median_response_time_seconds: float = 0.0
    
    # Emojis
    total_emojis: int = 0
    emoji_to_word_ratio: float = 0.0
    top_3_emojis: List[Tuple[str, int]] = Field(default_factory=list)
    
    # Conversation dynamics (2-hour inactivity boundary)
    conversations_started: int = 0
    conversations_ended: int = 0
    
    # Extra Banter Metrics
    max_consecutive_messages: int = 0  # "Yap streak"
    night_owl_percentage: float = 0.0   # % of messages between 12 AM - 5 AM
    dry_text_percentage: float = 0.0    # % of 1-word or short responses
    conversation_kill_rate: float = 0.0 # conversations_ended / total conversations
    laughter_count: int = 0            # hahaha, lol, lmao, emojis
    roast_title: str = ""
    roast_tagline: str = ""

class GroupStats(BaseModel):
    group_name: str
    total_messages: int = 0
    total_words: int = 0
    total_media: int = 0
    total_events: int = 0
    date_start: datetime
    date_end: datetime
    total_days: int = 0
    active_days_count: int = 0
    
    # Streaks with dates
    longest_active_streak_days: int = 0
    longest_active_streak_start: Optional[date] = None
    longest_active_streak_end: Optional[date] = None
    
    longest_inactive_streak_days: int = 0
    longest_inactive_streak_start: Optional[date] = None
    longest_inactive_streak_end: Optional[date] = None
    
    # Vocabulary & Top Words
    group_vocab_size: int = 0  # Count of distinct words used across the entire group
    
    @property
    def vocabulary_size(self) -> int:
        return self.group_vocab_size

    @property
    def top_words(self) -> list:
        return self.top_20_words
    top_20_words: List[Tuple[str, int]] = Field(default_factory=list)
    
    # Distributions
    hourly_distribution: Dict[int, int] = Field(default_factory=dict)     # 0-23
    weekday_distribution: Dict[str, int] = Field(default_factory=dict)   # Mon-Sun
    monthly_distribution: Dict[str, int] = Field(default_factory=dict)   # Apr 2026, May 2026...

class StaticAnalysisReport(BaseModel):
    group_stats: GroupStats
    member_stats: List[MemberStats]
    generated_at: datetime = Field(default_factory=datetime.now)
