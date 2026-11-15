import re
from datetime import datetime, timedelta, date
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Set, Optional
import emoji

from src.common.models import Message, MemberStats, GroupStats, StaticAnalysisReport

# Words/tokens indicating dry texting
DRY_WORDS = {"k", "ok", "okay", "haan", "han", "hmm", "hm", "cool", "ha", "achha", "accha", "shi", "sahi", "nice", "yes", "no", "nah"}

# Patterns indicating laughter
LAUGHTER_REGEX = re.compile(r"\b(ha(ha)+|he(he)+|lol|lmao|rofl|lmfao|xd)\b", re.IGNORECASE)
LAUGHTER_EMOJIS = {"😂", "🤣", "💀", "😭", "😹"}

# Common English & Hinglish grammatical stop words for the Word Cloud
STOPWORDS = {
    # English
    "the", "to", "and", "a", "i", "in", "it", "is", "of", "for", "that", "this", "my", "you", "me", "on", "with",
    "at", "by", "from", "be", "have", "has", "had", "do", "does", "did", "but", "not", "or", "as", "if", "so",
    "what", "when", "where", "who", "which", "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "some", "such", "no", "nor", "too", "very", "can", "will", "just", "should", "now", "are", "was", "were",
    "im", "dont", "cant", "wont", "didnt", "isnt", "arent", "hes", "shes", "its", "they", "them", "their", "we",
    "us", "our", "your", "ur", "u", "r", "n", "k", "ok", "haan", "han", "ha", "yes", "no", "nah", "omitted", "media",
    "message", "deleted", "edited", "null", "none",
    # Hinglish common fillers
    "hai", "hain", "ho", "hoon", "tha", "thi", "the", "hoga", "hogi", "hoge",
    "ka", "ki", "ke", "ko", "se", "me", "mein", "pe", "par", "bhi", "toh", "to", "hi", "aur", "ya",
    "ye", "yeh", "wo", "woh", "kya", "kyu", "kyun", "kaise", "kab", "kaha", "kahan",
    "ek", "koi", "kuch", "sab", "apna", "apne", "apni", "mera", "meri", "mere", "tera", "teri", "tere",
    "uske", "uski", "uska", "unka", "unki", "unke", "inhe", "unhe", "ise", "use",
    "kar", "karo", "karna", "karte", "karta", "karti", "kiya", "kiye", "raha", "rahi", "rahe",
    "gaya", "gayi", "gaye", "diya", "diye", "liya", "liye"
}

def assign_roasts(stats: MemberStats, group_stats: GroupStats, all_members: List[MemberStats]) -> Tuple[str, str]:
    """Generates an unfiltered roast title and description based on their actual numbers."""
    by_text_messages = sorted(all_members, key=lambda m: m.text_messages, reverse=True)
    by_yap = sorted(all_members, key=lambda m: m.max_consecutive_messages, reverse=True)
    by_night = sorted(all_members, key=lambda m: m.night_owl_percentage, reverse=True)
    by_dry = sorted(all_members, key=lambda m: m.dry_text_percentage, reverse=True)
    by_kills = sorted(all_members, key=lambda m: m.conversations_ended, reverse=True)
    by_media = sorted(all_members, key=lambda m: m.media_count, reverse=True)
    by_vocab = sorted(all_members, key=lambda m: m.vocab_size, reverse=True)
    by_speed = sorted([m for m in all_members if m.avg_response_time_seconds > 0], key=lambda m: m.avg_response_time_seconds)

    if stats == by_text_messages[0]:
        title = "👑 Chief Yap Officer (CYO)"
        tagline = f"Fired off {stats.text_messages:,} text messages ({stats.percentage_of_total:.1f}% of all traffic). Someone please check if this person has a job or outdoor hobbies."
    elif stats == by_yap[0]:
        title = "📢 The Radio Broadcaster"
        tagline = f"Sent {stats.max_consecutive_messages} text messages in a row without a single soul replying. Certified professional monologuer."
    elif stats == by_dry[0]:
        title = "🌵 The Sahara Desert"
        tagline = f"{stats.dry_text_percentage:.1f}% of messages are dry 1-word replies like 'k' or 'cool'. The emotional range of a boiled potato."
    elif stats == by_night[0] and stats.night_owl_percentage > 15:
        title = "🦇 The 3 AM Demon"
        tagline = f"{stats.night_owl_percentage:.1f}% of activity occurs between midnight and 5 AM. Sunlight is a foreign concept."
    elif stats == by_kills[0]:
        title = "🪦 The Buzzkill Reaper"
        tagline = f"Single-handedly murdered {stats.conversations_ended} group conversations. When they text, the group takes a 2-hour moment of silence."
    elif stats == by_media[0]:
        title = "📸 The Bandwidth Bandit"
        tagline = f"Dumped {stats.media_count:,} media files into the chat. Their photo gallery is probably 90% memes and questionable screenshots."
    elif stats == by_speed[0]:
        title = "⚡ Chronically Online Award"
        tagline = f"Average response time: {stats.avg_response_time_seconds:.1f}s. Phone is permanently glued to their retinas."
    elif stats.total_messages < (group_stats.total_messages / len(all_members) * 0.3):
        title = "👻 The Ghost Lurker"
        tagline = "Reads everything, contributes nothing. Only emerges from the shadows when drama is brewing."
    else:
        title = "🎭 The Professional Instigator"
        tagline = "Thrives in the chaos, drops a grenade in the conversation, and then watches the world burn."
        
    return title, tagline

class StaticAnalyzer:
    def __init__(self, inactivity_gap_hours: float = 2.0):
        self.inactivity_gap_threshold = timedelta(hours=inactivity_gap_hours)

    def analyze(self, group_name: str, messages: List[Message]) -> StaticAnalysisReport:
        user_msgs = [m for m in messages if not m.is_system]
        
        if not user_msgs:
            raise ValueError("No user messages to analyze.")

        total_messages = len(user_msgs)
        total_words = sum(len(m.content.split()) for m in user_msgs if not m.is_media)
        total_media = sum(1 for m in user_msgs if m.is_media)

        # Dates & Streaks
        date_start = user_msgs[0].timestamp
        date_end = user_msgs[-1].timestamp
        
        unique_dates = sorted(set(m.timestamp.date() for m in user_msgs))
        active_days_count = len(unique_dates)
        total_days = (date_end.date() - date_start.date()).days + 1

        # Calculate active streak with start & end dates
        longest_active_streak = 0
        longest_active_start = None
        longest_active_end = None
        
        if unique_dates:
            curr_start = unique_dates[0]
            curr_end = unique_dates[0]
            curr_len = 1
            max_active_len = 1
            max_active_start = unique_dates[0]
            max_active_end = unique_dates[0]

            for i in range(1, len(unique_dates)):
                if (unique_dates[i] - unique_dates[i-1]).days == 1:
                    curr_len += 1
                    curr_end = unique_dates[i]
                else:
                    if curr_len > max_active_len:
                        max_active_len = curr_len
                        max_active_start = curr_start
                        max_active_end = curr_end
                    curr_len = 1
                    curr_start = unique_dates[i]
                    curr_end = unique_dates[i]

            if curr_len > max_active_len:
                max_active_len = curr_len
                max_active_start = curr_start
                max_active_end = curr_end

            longest_active_streak = max_active_len
            longest_active_start = max_active_start
            longest_active_end = max_active_end

        # Calculate inactive streak with start & end dates
        longest_inactive_streak = 0
        longest_inactive_start = None
        longest_inactive_end = None

        if len(unique_dates) > 1:
            max_inactive_gap = 0
            for i in range(1, len(unique_dates)):
                gap = (unique_dates[i] - unique_dates[i-1]).days - 1
                if gap > max_inactive_gap:
                    max_inactive_gap = gap
                    longest_inactive_start = unique_dates[i-1] + timedelta(days=1)
                    longest_inactive_end = unique_dates[i] - timedelta(days=1)
            longest_inactive_streak = max_inactive_gap

        # Distributions
        hourly_dist = defaultdict(int)
        weekday_dist = {day: 0 for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
        monthly_dist = defaultdict(int)
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for m in user_msgs:
            hourly_dist[m.timestamp.hour] += 1
            weekday_dist[weekday_names[m.timestamp.weekday()]] += 1
            month_key = m.timestamp.strftime("%b %Y")
            monthly_dist[month_key] += 1

        # Conversation Segmentation (Event Starters & Enders)
        conversations_started_counter = Counter()
        conversations_ended_counter = Counter()
        
        total_events = 0
        if user_msgs:
            total_events = 1
            conversations_started_counter[user_msgs[0].sender] += 1
            
            for i in range(1, len(user_msgs)):
                prev_m = user_msgs[i - 1]
                curr_m = user_msgs[i]
                gap = curr_m.timestamp - prev_m.timestamp
                
                if gap >= self.inactivity_gap_threshold:
                    conversations_ended_counter[prev_m.sender] += 1
                    conversations_started_counter[curr_m.sender] += 1
                    total_events += 1
            
            conversations_ended_counter[user_msgs[-1].sender] += 1

        # Member-level groupings
        member_msgs = defaultdict(list)
        for m in user_msgs:
            member_msgs[m.sender].append(m)

        # Member name tokens to filter from Word Cloud
        member_name_tokens = set()
        for s in member_msgs.keys():
            for part in s.lower().split():
                member_name_tokens.add(part)
        combined_stopwords = STOPWORDS | member_name_tokens

        # Vocabulary & Word Frequency Calculation
        group_vocab = set()
        member_vocab = defaultdict(set)
        word_freq_counter = Counter()

        for m in user_msgs:
            if not m.is_media:
                # Strip links
                clean_txt = re.sub(r"https?://\S+", "", m.content.lower())
                # Extract clean words (letters only, >= 2 chars)
                all_tokens = re.findall(r"\b[a-zA-Z]{2,}\b", clean_txt)
                for w in all_tokens:
                    group_vocab.add(w)
                    member_vocab[m.sender].add(w)
                    if len(w) >= 3 and w not in combined_stopwords:
                        word_freq_counter[w] += 1

        top_20_words = word_freq_counter.most_common(20)

        # Consecutive text message streaks ("Yap streak") - media is explicitly EXCLUDED
        max_consecutive = defaultdict(int)
        curr_streak_sender = None
        curr_streak_count = 0
        for m in user_msgs:
            if m.is_media:
                # If someone else sends media, it interrupts the previous sender's streak
                if m.sender != curr_streak_sender:
                    curr_streak_sender = None
                    curr_streak_count = 0
                # Media itself NEVER increments the yap streak
                continue

            if m.sender == curr_streak_sender:
                curr_streak_count += 1
            else:
                curr_streak_sender = m.sender
                curr_streak_count = 1
            if curr_streak_count > max_consecutive[curr_streak_sender]:
                max_consecutive[curr_streak_sender] = curr_streak_count

        # Response times (within active conversational turns)
        member_response_times = defaultdict(list)
        for i in range(1, len(user_msgs)):
            prev_m = user_msgs[i - 1]
            curr_m = user_msgs[i]
            if curr_m.sender != prev_m.sender:
                gap = (curr_m.timestamp - prev_m.timestamp).total_seconds()
                if 0 < gap < (2 * 3600):
                    member_response_times[curr_m.sender].append(gap)

        # Build MemberStats
        raw_members: List[MemberStats] = []
        for sender, msgs in member_msgs.items():
            s_total_msgs = len(msgs)
            s_pct = (s_total_msgs / total_messages) * 100.0
            
            s_words = 0
            s_chars = 0
            s_media = 0
            s_emojis_counter = Counter()
            s_dry_count = 0
            s_night_count = 0
            s_laughter_count = 0

            for m in msgs:
                if m.is_media:
                    s_media += 1
                else:
                    words = m.content.split()
                    word_count = len(words)
                    s_words += word_count
                    s_chars += len(m.content)

                    content_clean = m.content.strip().lower()
                    if word_count == 1 or content_clean in DRY_WORDS or (len(content_clean) <= 4 and word_count <= 2):
                        s_dry_count += 1

                    if LAUGHTER_REGEX.search(content_clean):
                        s_laughter_count += 1

                    extracted_emojis = emoji.emoji_list(m.content)
                    for e in extracted_emojis:
                        ch = e["emoji"]
                        s_emojis_counter[ch] += 1
                        if ch in LAUGHTER_EMOJIS:
                            s_laughter_count += 1

                if 0 <= m.timestamp.hour < 5:
                    s_night_count += 1

            r_times = member_response_times.get(sender, [])
            avg_resp = (sum(r_times) / len(r_times)) if r_times else 0.0
            sorted_r = sorted(r_times)
            med_resp = sorted_r[len(sorted_r) // 2] if sorted_r else 0.0

            total_emojis = sum(s_emojis_counter.values())
            emoji_ratio = (total_emojis / max(1, s_words))
            top_3_emojis = s_emojis_counter.most_common(3)

            s_text_msgs = s_total_msgs - s_media
            avg_words = (s_words / max(1, s_text_msgs))
            avg_chars = (s_chars / max(1, s_text_msgs))

            night_pct = (s_night_count / s_total_msgs) * 100.0
            dry_pct = (s_dry_count / max(1, s_text_msgs)) * 100.0
            kill_rate = (conversations_ended_counter[sender] / max(1, total_events)) * 100.0

            member_stat = MemberStats(
                name=sender,
                total_messages=s_total_msgs,
                text_messages=s_text_msgs,
                percentage_of_total=round(s_pct, 2),
                total_words=s_words,
                total_chars=s_chars,
                media_count=s_media,
                vocab_size=len(member_vocab[sender]),
                avg_words_per_message=round(avg_words, 2),
                avg_chars_per_message=round(avg_chars, 2),
                avg_response_time_seconds=round(avg_resp, 1),
                median_response_time_seconds=round(med_resp, 1),
                total_emojis=total_emojis,
                emoji_to_word_ratio=round(emoji_ratio, 4),
                top_3_emojis=top_3_emojis,
                conversations_started=conversations_started_counter[sender],
                conversations_ended=conversations_ended_counter[sender],
                max_consecutive_messages=max_consecutive[sender],
                night_owl_percentage=round(night_pct, 2),
                dry_text_percentage=round(dry_pct, 2),
                conversation_kill_rate=round(kill_rate, 2),
                laughter_count=s_laughter_count
            )
            raw_members.append(member_stat)

        raw_members.sort(key=lambda m: m.total_messages, reverse=True)

        grp_stats = GroupStats(
            group_name=group_name,
            total_messages=total_messages,
            total_words=total_words,
            total_media=total_media,
            total_events=total_events,
            date_start=date_start,
            date_end=date_end,
            total_days=total_days,
            active_days_count=active_days_count,
            longest_active_streak_days=longest_active_streak,
            longest_active_streak_start=longest_active_start,
            longest_active_streak_end=longest_active_end,
            longest_inactive_streak_days=longest_inactive_streak,
            longest_inactive_streak_start=longest_inactive_start,
            longest_inactive_streak_end=longest_inactive_end,
            group_vocab_size=len(group_vocab),
            top_20_words=top_20_words,
            hourly_distribution=dict(sorted(hourly_dist.items())),
            weekday_distribution=weekday_dist,
            monthly_distribution=dict(monthly_dist)
        )

        for m in raw_members:
            title, tagline = assign_roasts(m, grp_stats, raw_members)
            m.roast_title = title
            m.roast_tagline = tagline

        return StaticAnalysisReport(
            group_stats=grp_stats,
            member_stats=raw_members
        )
