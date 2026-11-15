import os
import json
import base64
import math
import random
from datetime import datetime, date
from typing import List, Tuple
from src.models import StaticAnalysisReport, MemberStats, GroupStats

def generate_distinct_colors(n: int) -> List[str]:
    """
    Generates n distinct, aesthetically pleasing HSL colors using the golden angle.
    """
    colors = []
    golden_ratio_conjugate = 0.618033988749895
    h = 0.55
    for i in range(n):
        h = (h + golden_ratio_conjugate) % 1.0
        hue_deg = int(h * 360)
        sat = 80 if i % 2 == 0 else 88
        light = 55 if i % 2 == 0 else 64
        colors.append(f"hsl({hue_deg}, {sat}%, {light}%)")
    return colors

def get_icon_base64() -> str:
    icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.webp")
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/webp;base64,{encoded}"
    return ""

def generate_wordcloud_svg(top_words: List[Tuple[str, int]], output_path: str = "assets/wordcloud.svg") -> str:
    """
    Generates a dark-mode Word Cloud image (SVG) where the most used word is biggest,
    randomly spiraled outward with collision avoidance.
    """
    if not top_words:
        return ""

    width, height = 960, 440
    center_x, center_y = width // 2, height // 2

    max_count = top_words[0][1]
    min_count = top_words[-1][1] if len(top_words) > 1 else 1

    def calc_font_size(count: int) -> int:
        ratio = (math.sqrt(count) - math.sqrt(min_count)) / max(1e-5, (math.sqrt(max_count) - math.sqrt(min_count)))
        return int(20 + ratio * (76 - 20))

    colors = ["#38BDF8", "#22D3EE", "#818CF8", "#A78BFA", "#C084FC", "#F472B6", "#FB7185", "#34D399", "#FBBF24", "#F43F5E"]

    placed_boxes = []
    def collides(box):
        x, y, w, h = box
        for ex, ey, ew, eh in placed_boxes:
            if not (x + w < ex or x > ex + ew or y + h < ey or y > ey + eh):
                return True
        return False

    svg_texts = []
    random.seed(42)

    for idx, (word, count) in enumerate(top_words):
        fs = calc_font_size(count)
        w_est = int(len(word) * fs * 0.62) + 14
        h_est = int(fs * 1.1) + 6

        placed_box = None
        angle = (idx * 137.5) * (math.pi / 180)
        radius = 0
        step = 0

        while step < 450:
            tx = center_x + radius * math.cos(angle) - (w_est // 2)
            ty = center_y + radius * math.sin(angle) - (h_est // 2)

            if 20 <= tx <= width - w_est - 20 and 30 <= ty <= height - h_est - 20:
                box = (tx, ty, w_est, h_est)
                if not collides(box):
                    placed_box = box
                    placed_boxes.append(box)
                    break
            radius += 4
            angle += 0.35
            step += 1

        if not placed_box:
            placed_box = (center_x - w_est // 2, center_y - h_est // 2, w_est, h_est)
            placed_boxes.append(placed_box)

        x, y, bw, bh = placed_box
        color = "#22D3EE" if idx == 0 else colors[idx % len(colors)]
        weight = "900" if idx == 0 else ("800" if idx < 5 else "600")

        svg_texts.append(
            f'<text x="{int(x + bw//2)}" y="{int(y + fs * 0.86)}" font-size="{fs}" font-family="Plus Jakarta Sans, sans-serif" font-weight="{weight}" fill="{color}" text-anchor="middle" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.5))">{word}</text>'
        )

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
    <defs>
        <radialGradient id="wcbg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#1E293B" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="#0F172A" stop-opacity="0.95"/>
        </radialGradient>
    </defs>
    <rect width="{width}" height="{height}" rx="24" fill="url(#wcbg)" stroke="#334155" stroke-width="1.5"/>
    {''.join(svg_texts)}
</svg>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return svg_content

def generate_html_report(report: StaticAnalysisReport, output_file: str = "reports/static_report_mock.html") -> str:
    grp = report.group_stats
    members = [m for m in report.member_stats if m.name != "Meta AI"]

    # 1. Colors generated dynamically for any number of members
    member_colors = generate_distinct_colors(len(members))
    member_names = [m.name for m in members]
    member_msg_counts = [m.total_messages for m in members]
    member_pcts = [m.percentage_of_total for m in members]

    # 2. Charts Data & Peak Highlighting
    hours_labels = [f"{h:02d}:00" for h in range(24)]
    hours_data = [grp.hourly_distribution.get(h, 0) for h in range(24)]
    max_hour_val = max(hours_data) if hours_data else 0
    hours_colors = [
        "rgba(244, 63, 94, 0.95)" if val == max_hour_val else "rgba(6, 182, 212, 0.55)"
        for val in hours_data
    ]

    weekdays_labels = list(grp.weekday_distribution.keys())
    weekdays_data = list(grp.weekday_distribution.values())
    max_weekday_val = max(weekdays_data) if weekdays_data else 0
    weekdays_colors = [
        "rgba(245, 158, 11, 0.95)" if val == max_weekday_val else "rgba(139, 92, 246, 0.55)"
        for val in weekdays_data
    ]

    months_labels = list(grp.monthly_distribution.keys())
    months_data = list(grp.monthly_distribution.values())
    max_month_val = max(months_data) if months_data else 0
    month_point_colors = [
        "#F43F5E" if val == max_month_val else "#10B981"
        for val in months_data
    ]
    month_point_radii = [
        10 if val == max_month_val else 5
        for val in months_data
    ]

    # 3. Bigger Zucky Icon base64
    icon_src = get_icon_base64()
    icon_html = f'<img src="{icon_src}" alt="Zucky Icon" class="w-28 h-28 sm:w-36 sm:h-36 rounded-3xl shadow-2xl shadow-cyan-500/30 border-4 border-cyan-400/50 object-cover flex-shrink-0" />' if icon_src else ''

    # 4. Generate Top 20 Word Cloud SVG Image
    wc_svg_path = os.path.join(os.path.dirname(output_file), "..", "assets", "wordcloud.svg")
    wc_svg = generate_wordcloud_svg(grp.top_20_words, wc_svg_path)
    wc_base64 = base64.b64encode(wc_svg.encode("utf-8")).decode("utf-8") if wc_svg else ""
    wc_img_src = f"data:image/svg+xml;base64,{wc_base64}" if wc_base64 else "../assets/wordcloud.svg"

    # Top words chips HTML
    top_words_chips = "".join([
        f'<span class="px-3 py-1 bg-gray-800/90 hover:bg-gray-700/90 border border-gray-700 rounded-lg text-xs font-mono text-gray-200 flex items-center gap-1.5 transition-colors">'
        f'<span class="text-cyan-400 font-bold">{w}</span>'
        f'<span class="text-gray-400 text-[10px]">({c:,})</span>'
        f'</span>'
        for w, c in grp.top_20_words
    ])

    # 5. Format Streaks with dates
    active_streak_str = f"{grp.longest_active_streak_days}d 🔥"
    if grp.longest_active_streak_start and grp.longest_active_streak_end:
        active_streak_dates = f"{grp.longest_active_streak_start.strftime('%d %b %Y')} – {grp.longest_active_streak_end.strftime('%d %b %Y')}"
    else:
        active_streak_dates = "N/A"

    inactive_streak_str = f"{grp.longest_inactive_streak_days}d 💤"
    if grp.longest_inactive_streak_start and grp.longest_inactive_streak_end:
        inactive_streak_dates = f"{grp.longest_inactive_streak_start.strftime('%d %b %Y')} – {grp.longest_inactive_streak_end.strftime('%d %b %Y')}"
    else:
        inactive_streak_dates = "None"

    # 6. Member Cards HTML (2 cards per row, larger fonts, bigger layout, includes individual vocab size)
    member_cards_html = ""
    for idx, m in enumerate(members):
        emojis_str = " ".join([f"<span class='text-xl'>{e}</span> <span class='text-sm text-gray-400 font-mono'>({c})</span>" for e, c in m.top_3_emojis]) if m.top_3_emojis else "<span class='text-gray-500 italic text-sm'>None (Devoid of emotion)</span>"
        color_dot = member_colors[idx]

        member_cards_html += f"""
        <div class="glass-panel rounded-3xl p-7 hover:border-cyan-500/60 transition-all duration-300 hover:shadow-2xl hover:shadow-cyan-500/10 flex flex-col justify-between">
            <div>
                <!-- Top Header -->
                <div class="flex items-start justify-between gap-4 mb-4">
                    <div class="flex items-start gap-3">
                        <span class="w-4 h-4 rounded-full mt-1.5 flex-shrink-0 shadow-md" style="background-color: {color_dot};"></span>
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">Rank #{idx+1}</span>
                                <h3 class="font-extrabold text-2xl sm:text-3xl text-white tracking-tight">{m.name}</h3>
                            </div>
                            <div class="text-base sm:text-lg font-bold text-amber-400 mt-1 flex items-center gap-1.5">
                                {m.roast_title}
                            </div>
                        </div>
                    </div>
                    <div class="text-right flex-shrink-0">
                        <div class="text-3xl sm:text-4xl font-black text-white font-mono">{m.total_messages:,}</div>
                        <div class="text-sm font-semibold text-cyan-400">{m.percentage_of_total}% share</div>
                    </div>
                </div>

                <!-- Roast Tagline -->
                <div class="bg-gray-900/80 border border-gray-700/50 rounded-2xl p-4 mb-6 shadow-inner">
                    <p class="text-base text-gray-200 italic leading-relaxed">
                        "{m.roast_tagline}"
                    </p>
                </div>

                <!-- Primary Metric Badges (Now includes Vocab Size!) -->
                <div class="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mb-6">
                    <div class="bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-center">
                        <div class="text-xs text-gray-400 font-medium">Vocabulary</div>
                        <div class="font-bold text-amber-300 text-base mt-0.5">{m.vocab_size:,} <span class="text-[10px] text-gray-400">words</span></div>
                    </div>
                    <div class="bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-center">
                        <div class="text-xs text-gray-400 font-medium">Avg Verbosity</div>
                        <div class="font-bold text-cyan-300 text-base mt-0.5">{m.avg_words_per_message} <span class="text-[10px] text-gray-400">w/m</span></div>
                    </div>
                    <div class="bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-center">
                        <div class="text-xs text-gray-400 font-medium">Avg Response</div>
                        <div class="font-bold text-emerald-300 text-base mt-0.5">{int(m.avg_response_time_seconds//60)}m {int(m.avg_response_time_seconds%60)}s</div>
                    </div>
                    <div class="bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-center">
                        <div class="text-xs text-gray-400 font-medium">Yap Streak</div>
                        <div class="font-bold text-pink-400 text-base mt-0.5">{m.max_consecutive_messages} <span class="text-[10px] text-gray-400">texts</span></div>
                    </div>
                    <div class="bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-center">
                        <div class="text-xs text-gray-400 font-medium">Night Owl</div>
                        <div class="font-bold text-purple-400 text-base mt-0.5">{m.night_owl_percentage}%</div>
                    </div>
                </div>
            </div>

            <!-- Deep Dive List -->
            <div class="space-y-3 text-sm text-gray-300 border-t border-gray-800/80 pt-4">
                <div class="flex justify-between items-center py-1">
                    <span class="text-gray-400 font-medium">Conversation Impact:</span>
                    <div class="flex gap-4">
                        <span class="font-semibold text-emerald-400">Started: <b>{m.conversations_started}</b></span>
                        <span class="text-gray-600">|</span>
                        <span class="font-semibold text-rose-400">Killed: <b>{m.conversations_ended}</b></span>
                    </div>
                </div>
                <div class="flex justify-between items-center py-1 border-t border-gray-800/50">
                    <span class="text-gray-400 font-medium">Sahara Desert Index (Dry %):</span>
                    <span class="font-bold { 'text-amber-400' if m.dry_text_percentage > 12 else 'text-gray-200' }">{m.dry_text_percentage}% monosyllabic replies</span>
                </div>
                <div class="flex justify-between items-center py-1 border-t border-gray-800/50">
                    <span class="text-gray-400 font-medium">Media Dropped:</span>
                    <span class="font-bold text-gray-200">{m.media_count:,} items ({round((m.media_count/max(1,m.total_messages))*100, 1)}%)</span>
                </div>
                <div class="flex justify-between items-center py-1 border-t border-gray-800/50">
                    <span class="text-gray-400 font-medium">Signature Emojis:</span>
                    <div>{emojis_str}</div>
                </div>
            </div>
        </div>
        """

    # Superlatives (Top yapper strictly by pure text volume, excluding media)
    top_yapper = max(members, key=lambda m: m.text_messages)
    top_monologue = max(members, key=lambda m: m.max_consecutive_messages)
    top_night = max(members, key=lambda m: m.night_owl_percentage)
    top_killer = max(members, key=lambda m: m.conversations_ended)
    top_dry = max(members, key=lambda m: m.dry_text_percentage)
    top_media = max(members, key=lambda m: m.media_count)

    formatted_start = grp.date_start.strftime('%d %b %Y')
    formatted_end = grp.date_end.strftime('%d %b %Y')
    generated_at_str = report.generated_at.strftime('%d %b %Y at %I:%M %p')

    html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zucky's Reading - {grp.group_name} Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            background: radial-gradient(circle at top center, #1E1B4B 0%, #0B0F19 45%, #030712 100%);
            color: #F3F4F6;
        }}
        .glass-panel {{
            background: rgba(17, 24, 39, 0.75);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .glow-cyan {{
            box-shadow: 0 0 35px -5px rgba(6, 182, 212, 0.25);
        }}
    </style>
</head>
<body class="min-h-screen py-10 px-4 sm:px-8 font-sans antialiased selection:bg-cyan-500 selection:text-black">
    <div class="max-w-7xl mx-auto space-y-12">

        <!-- HEADER BANNER -->
        <header class="glass-panel rounded-3xl p-8 sm:p-12 relative overflow-hidden glow-cyan border border-cyan-500/20">
            <div class="absolute -right-16 -top-16 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -left-16 -bottom-16 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>
            
            <div class="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
                <div class="flex items-center gap-6">
                    <!-- ENLARGED ZUCKY ICON -->
                    {icon_html}
                    <div>
                        <!-- APP TITLE -->
                        <h1 class="text-5xl sm:text-7xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-400">
                            Zucky's Reading
                        </h1>
                        <!-- GC TITLE -->
                        <h2 class="text-2xl sm:text-3xl font-bold text-gray-200 mt-2 flex items-center gap-2">
                            <span>{grp.group_name}</span>
                        </h2>
                        <!-- CUSTOM SUBTITLE -->
                        <p class="text-gray-300 text-sm sm:text-base mt-2 font-medium">
                            Be careful, Zucky is reading your chats. Every single one of your <span class="text-cyan-400 font-bold font-mono">{grp.total_messages:,}</span> messages from <span class="text-cyan-400 font-mono">{formatted_start}</span> to <span class="text-cyan-400 font-mono">{formatted_end}</span>.
                        </p>
                    </div>
                </div>
                
                <div class="bg-gray-900/90 border border-gray-700/80 rounded-2xl p-5 flex flex-wrap gap-5 text-center shadow-lg flex-shrink-0">
                    <div>
                        <div class="text-xs text-gray-400 font-medium">Total Days</div>
                        <div class="text-2xl sm:text-3xl font-black text-cyan-400 font-mono">{grp.total_days}</div>
                    </div>
                    <div class="border-r border-gray-800"></div>
                    <div>
                        <div class="text-xs text-gray-400 font-medium">Active Days</div>
                        <div class="text-2xl sm:text-3xl font-black text-emerald-400 font-mono">{grp.active_days_count}</div>
                    </div>
                    <div class="border-r border-gray-800"></div>
                    <div>
                        <div class="text-xs text-gray-400 font-medium">Active Streak</div>
                        <div class="text-2xl sm:text-3xl font-black text-amber-400 font-mono">{active_streak_str}</div>
                    </div>
                </div>
            </div>
        </header>

        <!-- KPI STATS CARDS (Now includes Vocab Size & Exact Streak Dates) -->
        <section class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="glass-panel p-6 rounded-2xl">
                <div class="text-xs text-gray-400 font-semibold uppercase tracking-wider">Total Messages</div>
                <div class="text-4xl font-black text-white mt-2 font-mono">{grp.total_messages:,}</div>
                <div class="text-xs text-gray-400 mt-1">~{int(grp.total_messages / max(1, grp.total_days))} msgs / day</div>
            </div>
            
            <div class="glass-panel p-6 rounded-2xl">
                <div class="text-xs text-gray-400 font-semibold uppercase tracking-wider">Group Vocabulary Size</div>
                <div class="text-4xl font-black text-amber-400 mt-2 font-mono">{grp.group_vocab_size:,}</div>
                <div class="text-xs text-gray-400 mt-1">Distinct words used across chat</div>
            </div>

            <div class="glass-panel p-6 rounded-2xl">
                <div class="text-xs text-gray-400 font-semibold uppercase tracking-wider">Longest Active Streak</div>
                <div class="text-3xl font-black text-emerald-400 mt-2 font-mono">{active_streak_str}</div>
                <div class="text-xs text-gray-300 font-mono mt-1">{active_streak_dates}</div>
            </div>

            <div class="glass-panel p-6 rounded-2xl">
                <div class="text-xs text-gray-400 font-semibold uppercase tracking-wider">Longest Inactivity Streak</div>
                <div class="text-3xl font-black text-rose-400 mt-2 font-mono">{inactive_streak_str}</div>
                <div class="text-xs text-gray-300 font-mono mt-1">{inactive_streak_dates}</div>
            </div>
        </section>

        <!-- TOP 20 WORDS WORD CLOUD (IMAGE OF RANDOMLY DISTRIBUTED WORDS) -->
        <section class="glass-panel p-8 rounded-3xl space-y-6">
            <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                <div>
                    <h2 class="text-2xl sm:text-3xl font-black text-white flex items-center gap-2">
                        ☁️ Group Vocabulary: Top 20 Most Used Words
                    </h2>
                    <p class="text-sm text-gray-400 mt-1">
                        Visualizing the group's linguistic fingerprint — the bigger the word, the more obsessed the group is with it.
                    </p>
                </div>
                <div class="text-right">
                    <span class="text-xs text-cyan-400 font-mono bg-cyan-500/10 px-3 py-1.5 rounded-full border border-cyan-500/20 font-bold">
                        {grp.group_vocab_size:,} Unique Words
                    </span>
                </div>
            </div>

            <!-- Single Image Word Cloud -->
            <div class="w-full flex items-center justify-center rounded-2xl overflow-hidden border border-gray-700/60 shadow-2xl">
                <img src="{wc_img_src}" alt="Top 20 Words Word Cloud" class="w-full h-auto object-contain max-h-[440px]" />
            </div>

            <!-- Word Frequency Chips -->
            <div class="flex flex-wrap gap-2 pt-2">
                {top_words_chips}
            </div>
        </section>

        <!-- HALL OF SHAME / SUPERLATIVES -->
        <section class="space-y-4">
            <div>
                <h2 class="text-3xl font-black text-white flex items-center gap-2">
                    🏆 The Hall of Shame & Superlatives
                </h2>
                <p class="text-base text-gray-400 mt-1">Honoring the group's most egregious statistical offenders.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div class="glass-panel p-6 rounded-2xl border-l-4 border-l-cyan-500">
                    <div class="flex justify-between items-center">
                        <span class="text-3xl">👑</span>
                        <span class="text-xs uppercase tracking-wider font-bold text-cyan-400 font-mono">Volume Monopolist</span>
                    </div>
                    <div class="font-extrabold text-xl text-white mt-3">{top_yapper.name.split()[0]}</div>
                    <div class="text-sm text-cyan-300 font-semibold">Chief Yap Officer</div>
                    <p class="text-sm text-gray-300 mt-2 leading-relaxed">
                        Fired off <b>{top_yapper.text_messages:,}</b> text messages (excluding media). Roughly 1 out of every 3 texts was sent by this individual.
                    </p>
                </div>

                <div class="glass-panel p-6 rounded-2xl border-l-4 border-l-purple-500">
                    <div class="flex justify-between items-center">
                        <span class="text-3xl">📢</span>
                        <span class="text-xs uppercase tracking-wider font-bold text-purple-400 font-mono">Yapathon Champion</span>
                    </div>
                    <div class="font-extrabold text-xl text-white mt-3">{top_monologue.name.split()[0]}</div>
                    <div class="text-sm text-purple-300 font-semibold">The Radio Broadcaster</div>
                    <p class="text-sm text-gray-300 mt-2 leading-relaxed">
                        Fired off <b>{top_monologue.max_consecutive_messages}</b> consecutive text messages in a row without a single reply. Truly the definition of talking to a brick wall.
                    </p>
                </div>

                <div class="glass-panel p-6 rounded-2xl border-l-4 border-l-indigo-500">
                    <div class="flex justify-between items-center">
                        <span class="text-3xl">🦇</span>
                        <span class="text-xs uppercase tracking-wider font-bold text-indigo-400 font-mono">Vampire Award</span>
                    </div>
                    <div class="font-extrabold text-xl text-white mt-3">{top_night.name.split()[0]}</div>
                    <div class="text-sm text-indigo-300 font-semibold">The 3 AM Demon</div>
                    <p class="text-sm text-gray-300 mt-2 leading-relaxed">
                        <b>{top_night.night_owl_percentage}%</b> of all their messages are fired off between midnight and 5:00 AM. Sunlight is clearly considered an occupational hazard.
                    </p>
                </div>

                <div class="glass-panel p-6 rounded-2xl border-l-4 border-l-rose-500">
                    <div class="flex justify-between items-center">
                        <span class="text-3xl">🪦</span>
                        <span class="text-xs uppercase tracking-wider font-bold text-rose-400 font-mono">Serial Buzzkill</span>
                    </div>
                    <div class="font-extrabold text-xl text-white mt-3">{top_killer.name.split()[0]}</div>
                    <div class="text-sm text-rose-300 font-semibold">The Conversation Assassin</div>
                    <p class="text-sm text-gray-300 mt-2 leading-relaxed">
                        Murdered <b>{top_killer.conversations_ended}</b> conversations. Whenever they speak, the group chat enters an involuntary 2-hour coma.
                    </p>
                </div>

                <div class="glass-panel p-6 rounded-2xl border-l-4 border-l-amber-500">
                    <div class="flex justify-between items-center">
                        <span class="text-3xl">🌵</span>
                        <span class="text-xs uppercase tracking-wider font-bold text-amber-400 font-mono">Emotional Flatline</span>
                    </div>
                    <div class="font-extrabold text-xl text-white mt-3">{top_dry.name.split()[0]}</div>
                    <div class="text-sm text-amber-300 font-semibold">The Sahara Desert</div>
                    <p class="text-sm text-gray-300 mt-2 leading-relaxed">
                        <b>{top_dry.dry_text_percentage}%</b> of replies are monosyllabic grunts like 'k', 'cool', 'haan'. Texting them is equivalent to talking to a decorative cushion.
                    </p>
                </div>

                <div class="glass-panel p-6 rounded-2xl border-l-4 border-l-pink-500">
                    <div class="flex justify-between items-center">
                        <span class="text-3xl">📸</span>
                        <span class="text-xs uppercase tracking-wider font-bold text-pink-400 font-mono">Bandwidth Bandit</span>
                    </div>
                    <div class="font-extrabold text-xl text-white mt-3">{top_media.name.split()[0]}</div>
                    <div class="text-sm text-pink-300 font-semibold">Meme Hoarder</div>
                    <p class="text-sm text-gray-300 mt-2 leading-relaxed">
                        Shared <b>{top_media.media_count:,}</b> media files. Responsible for filling everyone's phone storage with dubious reels and screenshots.
                    </p>
                </div>
            </div>
        </section>

        <!-- CHARTS SECTION -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Share of Messages Pie Chart (Bigger, White Border, White Legend) -->
            <div class="glass-panel p-7 rounded-3xl flex flex-col justify-between">
                <div>
                    <h3 class="text-xl font-bold text-white mb-1">Message Share Distribution</h3>
                    <p class="text-sm text-gray-400 mb-4">Hover over slices to inspect message volume and percentage share.</p>
                </div>
                <div class="h-[430px] w-full flex items-center justify-center">
                    <canvas id="shareChart"></canvas>
                </div>
            </div>

            <!-- 24h Hourly Activity Bar Chart with Peak Highlight -->
            <div class="glass-panel p-7 rounded-3xl flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center">
                        <h3 class="text-xl font-bold text-white mb-1">Activity by Hour of Day (24h)</h3>
                        <span class="text-xs font-mono text-rose-400 bg-rose-500/10 px-2.5 py-1 rounded-md border border-rose-500/20">Peak: {hours_labels[hours_data.index(max_hour_val)]}</span>
                    </div>
                    <p class="text-sm text-gray-400 mb-4">Peak hours highlighted in vivid red.</p>
                </div>
                <div class="h-[430px] w-full">
                    <canvas id="hourlyChart"></canvas>
                </div>
            </div>

            <!-- Day of Week Distribution with Peak Highlight -->
            <div class="glass-panel p-7 rounded-3xl flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center">
                        <h3 class="text-xl font-bold text-white mb-1">Weekly Activity Pattern</h3>
                        <span class="text-xs font-mono text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-md border border-amber-500/20">Peak: {weekdays_labels[weekdays_data.index(max_weekday_val)]}</span>
                    </div>
                    <p class="text-sm text-gray-400 mb-4">Busiest day highlighted in amber.</p>
                </div>
                <div class="h-[360px] w-full">
                    <canvas id="weekdayChart"></canvas>
                </div>
            </div>

            <!-- Monthly Progression with Peak Highlight -->
            <div class="glass-panel p-7 rounded-3xl flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center">
                        <h3 class="text-xl font-bold text-white mb-1">Monthly Message Volume</h3>
                        <span class="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/20">Peak: {months_labels[months_data.index(max_month_val)]}</span>
                    </div>
                    <p class="text-sm text-gray-400 mb-4">Trajectory over time with peak month highlighted.</p>
                </div>
                <div class="h-[360px] w-full">
                    <canvas id="monthlyChart"></canvas>
                </div>
            </div>
        </section>

        <!-- MEMBER STATS (2 CARDS PER ROW, INCLUDES VOCABULARY SIZE) -->
        <section class="space-y-6">
            <div>
                <h2 class="text-3xl sm:text-4xl font-black text-white">Member Stats</h2>
                <p class="text-base text-gray-400 mt-1 font-medium">Zucky shall not spare any of you</p>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {member_cards_html}
            </div>
        </section>

        <!-- FOOTER -->
        <footer class="text-center text-sm text-gray-500 py-8 border-t border-gray-800/80 space-y-1.5">
            <div>Generated by <b class="text-gray-300">Zucky's Reading</b> • Local, Private & Uncensored</div>
            <div class="text-xs text-gray-400 font-mono">Report generated on {generated_at_str}</div>
        </footer>

    </div>

    <!-- CHART.JS SCRIPTS -->
    <script>
        const memberFullNames = {json.dumps(member_names)};
        const memberData = {json.dumps(member_msg_counts)};
        const memberPcts = {json.dumps(member_pcts)};
        const memberColors = {json.dumps(member_colors)};

        // 1. Share of Messages (Pie Chart with White Border and High-Contrast White Legend)
        new Chart(document.getElementById('shareChart'), {{
            type: 'pie',
            data: {{
                labels: memberFullNames,
                datasets: [{{
                    data: memberData,
                    backgroundColor: memberColors,
                    borderWidth: 2,
                    borderColor: '#FFFFFF' // WHITE BORDER AS REQUESTED
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{
                            color: '#F9FAFB', // LIGHTER / WHITE COLOR (NOT BLACK)
                            font: {{ size: 12, weight: '700' }},
                            padding: 12,
                            generateLabels: function(chart) {{
                                const data = chart.data;
                                return data.labels.map((label, i) => {{
                                    const count = data.datasets[0].data[i];
                                    const pct = memberPcts[i];
                                    return {{
                                        text: `${{label}} (${{pct}}%)`,
                                        fillStyle: memberColors[i],
                                        strokeStyle: '#FFFFFF',
                                        lineWidth: 1.5,
                                        fontColor: '#F9FAFB',
                                        hidden: isNaN(data.datasets[0].data[i]) || chart.getDatasetMeta(0).data[i].hidden,
                                        index: i
                                    }};
                                }});
                            }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const idx = context.dataIndex;
                                const val = context.raw;
                                const pct = memberPcts[idx];
                                return ` ${{context.label}}: ${{val.toLocaleString()}} messages (${{pct}}%)`;
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 2. Hourly Activity (Bar with peak highlighted)
        new Chart(document.getElementById('hourlyChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(hours_labels)},
                datasets: [{{
                    label: 'Messages',
                    data: {json.dumps(hours_data)},
                    backgroundColor: {json.dumps(hours_colors)},
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ ticks: {{ color: '#9CA3AF', maxRotation: 45, font: {{ size: 11 }} }}, grid: {{ color: '#1F2937' }} }},
                    y: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 11 }} }}, grid: {{ color: '#1F2937' }} }}
                }},
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return ` ${{context.raw.toLocaleString()}} messages`;
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 3. Weekday Activity (Bar with peak highlighted)
        new Chart(document.getElementById('weekdayChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(weekdays_labels)},
                datasets: [{{
                    label: 'Messages',
                    data: {json.dumps(weekdays_data)},
                    backgroundColor: {json.dumps(weekdays_colors)},
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 12, weight: '500' }} }}, grid: {{ color: '#1F2937' }} }},
                    y: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 11 }} }}, grid: {{ color: '#1F2937' }} }}
                }},
                plugins: {{ legend: {{ display: false }} }}
            }}
        }});

        // 4. Monthly Activity (Line with peak highlighted)
        new Chart(document.getElementById('monthlyChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(months_labels)},
                datasets: [{{
                    label: 'Volume',
                    data: {json.dumps(months_data)},
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointBackgroundColor: {json.dumps(month_point_colors)},
                    pointBorderColor: '#FFFFFF',
                    pointBorderWidth: 1.5,
                    pointRadius: {json.dumps(month_point_radii)},
                    pointHoverRadius: 12
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 12 }} }}, grid: {{ color: '#1F2937' }} }},
                    y: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 11 }} }}, grid: {{ color: '#1F2937' }} }}
                }},
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return ` ${{context.raw.toLocaleString()}} messages`;
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_file
