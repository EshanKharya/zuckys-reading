import os
import json
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import config
from src.common.models import StaticAnalysisReport, MemberStats
from src.semantic.agents.event_summarizer import EventReport
from src.semantic.agents.personality_roaster import PersonalityReport
from src.semantic.agents.relationship_guru import RelationshipReport
from src.semantic.agents.group_therapist import GroupReport
from src.reporting.sanitizer import ReportSanitizer
from src.static.html_report import generate_distinct_colors, get_icon_base64, generate_wordcloud_svg

class ReportGenerator:
    """
    Dedicated Report Generator Engine compiling Static & Semantic analysis
    into a unified, interactive 5-tab dark-mode HTML dossier.
    """

    def __init__(self, sanitizer: ReportSanitizer):
        self.sanitizer = sanitizer

    def generate(
        self,
        group_name: str,
        static_report: Optional[StaticAnalysisReport],
        event_reports: List[EventReport],
        personality_reports: List[PersonalityReport],
        relationship_reports: List[RelationshipReport],
        group_report: Optional[GroupReport],
        output_file: Optional[str] = None,
        release_version: Optional[str] = None,
    ) -> str:
        version = release_version or getattr(config, "APP_VERSION", "v2.0")
        out_path = output_file or os.path.join(config.REPORTS_DIR, f"Zucky_read_{group_name}.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        icon_base64 = get_icon_base64()
        now_str = datetime.now().strftime("%d %b %Y at %I:%M %p")

        # Compile HTML components for each tab
        tab1_html = self._render_tab1_group_therapy(group_name, group_report)
        tab2_html, chart_js_scripts = self._render_tab2_static_stats(static_report, out_path)
        tab3_html = self._render_tab3_member_dossiers(personality_reports, static_report)
        tab4_html = self._render_tab4_relationship_matrix(relationship_reports)
        tab5_html = self._render_tab5_canon_events(event_reports)

        full_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zucky's Reading - {group_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
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
        }};
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
        .tab-btn.active {{
            background: linear-gradient(135deg, rgba(6, 182, 212, 0.25), rgba(139, 92, 246, 0.25));
            border-color: rgba(6, 182, 212, 0.6);
            color: #FFFFFF;
            font-weight: 700;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
    </style>
</head>
<body class="min-h-screen py-8 px-4 sm:px-8 font-sans antialiased selection:bg-cyan-500 selection:text-black">
    <div class="max-w-7xl mx-auto space-y-8">

        <!-- HEADER BANNER -->
        <header class="glass-panel rounded-3xl p-6 sm:p-10 relative overflow-hidden glow-cyan border border-cyan-500/20">
            <div class="absolute -right-16 -top-16 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -left-16 -bottom-16 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>
            
            <div class="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div class="flex items-center gap-5">
                    {f'<img src="{icon_base64}" alt="Zucky Icon" class="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl shadow-xl shadow-cyan-500/30 border-2 border-cyan-400/50 object-cover flex-shrink-0" />' if icon_base64 else ''}
                    <div>
                        <div class="flex items-center gap-3 mb-1">
                            <span class="px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full bg-gradient-to-r from-cyan-500 to-indigo-600 text-white font-mono shadow-md">
                                Forensic Chat Dossier
                            </span>
                            <span class="px-2.5 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono text-xs font-bold">{version}</span>
                        </div>
                        <h1 class="text-3xl sm:text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-400">
                            {group_name}
                        </h1>
                        <p class="text-gray-400 text-xs sm:text-sm mt-1 font-medium">
                            Private multi-agent psychological dissection & deterministic statistics.
                        </p>
                    </div>
                </div>

                <div class="bg-gray-900/90 border border-gray-700/80 rounded-2xl px-5 py-3.5 flex items-center gap-4 text-center shadow-lg">
                    <div>
                        <div class="text-[11px] text-gray-400 font-medium">Report Engine</div>
                        <div class="text-sm font-bold text-cyan-400 font-mono">Dual Static/Semantic</div>
                    </div>
                    <div class="border-r border-gray-800 h-8"></div>
                    <div>
                        <div class="text-[11px] text-gray-400 font-medium">Privacy</div>
                        <div class="text-sm font-bold text-emerald-400 font-mono">100% Offline Local</div>
                    </div>
                </div>
            </div>
        </header>

        <!-- 5-TAB NAVIGATION BAR -->
        <nav class="glass-panel p-2 rounded-2xl flex flex-wrap gap-2 border border-gray-800" id="tabsNav">
            <button onclick="switchTab('tab-therapy')" class="tab-btn active px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-gray-400 hover:text-white border border-transparent transition-all flex items-center gap-2">
                <span>🛋️</span> Group Therapy & Identity
            </button>
            <button onclick="switchTab('tab-stats')" class="tab-btn px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-gray-400 hover:text-white border border-transparent transition-all flex items-center gap-2">
                <span>📊</span> Static Stats & Visuals
            </button>
            <button onclick="switchTab('tab-members')" class="tab-btn px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-gray-400 hover:text-white border border-transparent transition-all flex items-center gap-2">
                <span>👤</span> Member Dossiers
            </button>
            <button onclick="switchTab('tab-relationships')" class="tab-btn px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-gray-400 hover:text-white border border-transparent transition-all flex items-center gap-2">
                <span>🤝</span> Relationship Matrix
            </button>
            <button onclick="switchTab('tab-events')" class="tab-btn px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-gray-400 hover:text-white border border-transparent transition-all flex items-center gap-2">
                <span>📜</span> Canon Events Archive
            </button>
        </nav>

        <!-- TAB CONTENTS -->
        <main>
            <!-- TAB 1: GROUP THERAPY -->
            <div id="tab-therapy" class="tab-content active space-y-6">
                {tab1_html}
            </div>

            <!-- TAB 2: STATIC STATS & VISUALS -->
            <div id="tab-stats" class="tab-content space-y-6">
                {tab2_html}
            </div>

            <!-- TAB 3: MEMBER DOSSIERS -->
            <div id="tab-members" class="tab-content space-y-6">
                {tab3_html}
            </div>

            <!-- TAB 4: RELATIONSHIP MATRIX -->
            <div id="tab-relationships" class="tab-content space-y-6">
                {tab4_html}
            </div>

            <!-- TAB 5: CANON EVENTS ARCHIVE -->
            <div id="tab-events" class="tab-content space-y-6">
                {tab5_html}
            </div>
        </main>

        <!-- FOOTER -->
        <footer class="text-center text-sm text-gray-500 py-8 border-t border-gray-800/80 space-y-1.5">
            <div class="flex items-center justify-center gap-2">
                <span>Generated by <b class="text-gray-300">Zucky's Reading</b></span>
                <span class="px-2 py-0.5 rounded-full bg-cyan-950/60 text-cyan-400 border border-cyan-800/50 font-mono text-xs font-semibold">{version}</span>
                <span>• Local, Private & Uncensored</span>
            </div>
            <div class="text-xs text-gray-400 font-mono">Report generated on {now_str}</div>
        </footer>

    </div>

    <!-- TAB SWITCHING SCRIPT -->
    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            
            const targetContent = document.getElementById(tabId);
            if (targetContent) targetContent.classList.add('active');

            // Find matching button
            const btns = document.querySelectorAll('.tab-btn');
            btns.forEach(btn => {{
                if (btn.getAttribute('onclick').includes(tabId)) {{
                    btn.classList.add('active');
                }}
            }});
        }}
    </script>

    <!-- CHART.JS SCRIPTS -->
    {chart_js_scripts}
</body>
</html>
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        return out_path

    # ==========================================
    # TAB 1: GROUP THERAPY & IDENTITY
    # ==========================================
    def _render_tab1_group_therapy(self, group_name: str, group_report: Optional[GroupReport]) -> str:
        if not group_report:
            return """
            <div class="glass-panel p-8 rounded-3xl text-center space-y-2">
                <div class="text-3xl">🛋️</div>
                <h3 class="text-lg font-bold text-white">Group Therapy Inactive</h3>
                <p class="text-sm text-gray-400">Run semantic analysis to generate macro group diagnosis.</p>
            </div>
            """

        clean_identity = self.sanitizer.sanitize(group_report.group_identity)
        clean_timeline = self.sanitizer.sanitize(group_report.group_timeline)
        clean_roast = self.sanitizer.sanitize(group_report.master_group_roast)

        return f"""
        <div class="glass-panel p-8 sm:p-12 rounded-3xl border-l-4 border-l-indigo-500 space-y-8">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <span class="text-xs font-mono text-indigo-400 uppercase tracking-widest font-bold">Macro Group Identity</span>
                    <h2 class="text-3xl sm:text-4xl font-black text-white mt-1">
                        {clean_identity} {group_report.group_apt_emoji}
                    </h2>
                </div>
            </div>

            <!-- TIMELINE -->
            <div class="bg-gray-900/60 p-6 rounded-2xl border border-gray-800 space-y-2">
                <h4 class="text-sm font-bold uppercase tracking-wider text-cyan-400 font-mono">Evolution Timeline</h4>
                <p class="text-sm sm:text-base text-gray-200 leading-relaxed">
                    {clean_timeline}
                </p>
            </div>

            <!-- MASTER ROAST -->
            <div class="bg-gradient-to-br from-purple-950/30 to-indigo-950/20 p-6 sm:p-8 rounded-2xl border border-purple-800/40 space-y-3">
                <h4 class="text-sm font-bold uppercase tracking-wider text-rose-400 font-mono flex items-center gap-2">
                    <span>🔥</span> The Master Group Roast
                </h4>
                <div class="text-sm sm:text-base text-gray-200 leading-relaxed space-y-3">
                    {clean_roast.replace(chr(10), '<br><br>')}
                </div>
            </div>
        </div>
        """

    # ==========================================
    # TAB 2: STATIC STATS & VISUALS
    # ==========================================
    def _render_tab2_static_stats(self, static_report: Optional[StaticAnalysisReport], output_file: str) -> Tuple[str, str]:
        if not static_report:
            return """
            <div class="glass-panel p-8 rounded-3xl text-center space-y-2">
                <div class="text-3xl">📊</div>
                <h3 class="text-lg font-bold text-white">Static Analysis Inactive</h3>
                <p class="text-sm text-gray-400">Run static analysis to generate chart metrics.</p>
            </div>
            """, ""

        grp = static_report.group_stats
        members = [m for m in static_report.member_stats if m.name != "Meta AI"]

        # Word cloud SVG
        wc_svg_path = os.path.join(os.path.dirname(output_file), "..", "assets", "wordcloud.svg")
        generate_wordcloud_svg(grp.top_20_words, output_path=wc_svg_path)
        wc_base64 = ""
        if os.path.exists(wc_svg_path):
            with open(wc_svg_path, "rb") as f:
                wc_base64 = base64.b64encode(f.read()).decode("utf-8")
        wc_img_src = f"data:image/svg+xml;base64,{wc_base64}" if wc_base64 else "../assets/wordcloud.svg"

        # Colors & Chart Data
        member_colors = generate_distinct_colors(len(members))
        member_names = [m.name for m in members]
        member_msgs = [m.total_messages for m in members]

        hours_labels = [f"{h:02d}:00" for h in range(24)]
        hours_data = [grp.hourly_distribution.get(h, 0) for h in range(24)]
        max_hour_val = max(hours_data) if hours_data else 0
        hours_colors = ["rgba(244, 63, 94, 0.95)" if v == max_hour_val else "rgba(6, 182, 212, 0.55)" for v in hours_data]

        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_data = [grp.weekday_distribution.get(d, 0) for d in days_order]
        max_day_val = max(days_data) if days_data else 0
        days_colors = ["rgba(244, 63, 94, 0.95)" if v == max_day_val else "rgba(139, 92, 246, 0.55)" for v in days_data]

        month_keys = sorted(list(grp.monthly_distribution.keys()))
        month_data = [grp.monthly_distribution[k] for k in month_keys]

        # Top words chips
        chips_html = "".join([f'<span class="px-2.5 py-1 rounded-lg bg-gray-800/80 border border-gray-700/60 text-xs font-mono text-cyan-300">{w} <span class="text-gray-500">({c})</span></span>' for w, c in grp.top_20_words[:15]])

        html = f"""
        <!-- KPIS -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div class="glass-panel p-4 rounded-2xl text-center">
                <div class="text-xs text-gray-400 font-mono">Total Messages</div>
                <div class="text-xl sm:text-2xl font-black text-cyan-400 font-mono mt-1">{grp.total_messages:,}</div>
            </div>
            <div class="glass-panel p-4 rounded-2xl text-center">
                <div class="text-xs text-gray-400 font-mono">Total Words</div>
                <div class="text-xl sm:text-2xl font-black text-indigo-400 font-mono mt-1">{grp.total_words:,}</div>
            </div>
            <div class="glass-panel p-4 rounded-2xl text-center">
                <div class="text-xs text-gray-400 font-mono">Conversations</div>
                <div class="text-xl sm:text-2xl font-black text-purple-400 font-mono mt-1">{grp.total_events:,}</div>
            </div>
            <div class="glass-panel p-4 rounded-2xl text-center">
                <div class="text-xs text-gray-400 font-mono">Vocab Size</div>
                <div class="text-xl sm:text-2xl font-black text-emerald-400 font-mono mt-1">{grp.vocabulary_size:,}</div>
            </div>
            <div class="glass-panel p-4 rounded-2xl text-center">
                <div class="text-xs text-gray-400 font-mono">Active Streak</div>
                <div class="text-xl sm:text-2xl font-black text-amber-400 font-mono mt-1">{grp.longest_active_streak_days}d</div>
            </div>
            <div class="glass-panel p-4 rounded-2xl text-center">
                <div class="text-xs text-gray-400 font-mono">Media Shared</div>
                <div class="text-xl sm:text-2xl font-black text-rose-400 font-mono mt-1">{grp.total_media:,}</div>
            </div>
        </div>

        <!-- CHARTS GRID -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="glass-panel p-6 rounded-3xl space-y-3">
                <h4 class="text-sm font-bold text-white font-mono uppercase tracking-wider">Traffic Share Distribution</h4>
                <div class="h-64 flex items-center justify-center">
                    <canvas id="trafficDonutChart"></canvas>
                </div>
            </div>
            <div class="glass-panel p-6 rounded-3xl space-y-3">
                <h4 class="text-sm font-bold text-white font-mono uppercase tracking-wider">24-Hour Activity Distribution</h4>
                <div class="h-64 flex items-center justify-center">
                    <canvas id="hourlyBarChart"></canvas>
                </div>
            </div>
            <div class="glass-panel p-6 rounded-3xl space-y-3">
                <h4 class="text-sm font-bold text-white font-mono uppercase tracking-wider">Weekday Activity</h4>
                <div class="h-64 flex items-center justify-center">
                    <canvas id="weekdayBarChart"></canvas>
                </div>
            </div>
            <div class="glass-panel p-6 rounded-3xl space-y-3">
                <h4 class="text-sm font-bold text-white font-mono uppercase tracking-wider">Monthly Progression Trajectory</h4>
                <div class="h-64 flex items-center justify-center">
                    <canvas id="monthlyLineChart"></canvas>
                </div>
            </div>
        </div>

        <!-- WORD CLOUD -->
        <div class="glass-panel p-6 sm:p-8 rounded-3xl space-y-4">
            <h4 class="text-sm font-bold text-white font-mono uppercase tracking-wider">Top 20 Most Frequent Words</h4>
            <div class="flex flex-col md:flex-row items-center gap-6">
                <div class="w-full md:w-1/2 flex justify-center">
                    <img src="{wc_img_src}" alt="Word Cloud" class="max-h-64 object-contain" />
                </div>
                <div class="w-full md:w-1/2 flex flex-wrap gap-2">
                    {chips_html}
                </div>
            </div>
        </div>
        """

        scripts = f"""
        <script>
            // 1. Donut Chart
            new Chart(document.getElementById('trafficDonutChart'), {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(member_names)},
                    datasets: [{{
                        data: {json.dumps(member_msgs)},
                        backgroundColor: {json.dumps(member_colors)},
                        borderColor: '#FFFFFF',
                        borderWidth: 1.5,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ labels: {{ color: '#94A3B8', font: {{ size: 10 }} }} }} }}
                }}
            }});

            // 2. Hourly Chart
            new Chart(document.getElementById('hourlyBarChart'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(hours_labels)},
                    datasets: [{{
                        label: 'Messages',
                        data: {json.dumps(hours_data)},
                        backgroundColor: {json.dumps(hours_colors)},
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748B', maxRotation: 0, font: {{ size: 9 }} }} }},
                        y: {{ ticks: {{ color: '#64748B' }} }}
                    }}
                }}
            }});

            // 3. Weekday Chart
            new Chart(document.getElementById('weekdayBarChart'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(days_order)},
                    datasets: [{{
                        label: 'Messages',
                        data: {json.dumps(days_data)},
                        backgroundColor: {json.dumps(days_colors)},
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }} }},
                        y: {{ ticks: {{ color: '#64748B' }} }}
                    }}
                }}
            }});

            // 4. Monthly Chart
            new Chart(document.getElementById('monthlyLineChart'), {{
                type: 'line',
                data: {{
                    labels: {json.dumps(month_keys)},
                    datasets: [{{
                        label: 'Volume',
                        data: {json.dumps(month_data)},
                        borderColor: '#38BDF8',
                        backgroundColor: 'rgba(56, 189, 248, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#F43F5E'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }} }},
                        y: {{ ticks: {{ color: '#64748B' }} }}
                    }}
                }}
            }});
        </script>
        """

        return html, scripts

    # ==========================================
    # TAB 3: MEMBER DOSSIERS
    # ==========================================
    def _render_tab3_member_dossiers(
        self,
        personality_reports: List[PersonalityReport],
        static_report: Optional[StaticAnalysisReport],
    ) -> str:
        stats_map: Dict[str, MemberStats] = {}
        if static_report:
            stats_map = {m.name: m for m in static_report.member_stats}

        cards = []
        for p in personality_reports:
            clean_name = p.member_name
            clean_title = self.sanitizer.sanitize(p.title)
            clean_roast = self.sanitizer.sanitize(p.roast)
            clean_strengths = [self.sanitizer.sanitize(s) for s in p.strengths]
            clean_weaknesses = [self.sanitizer.sanitize(w) for w in p.weaknesses]

            stats = stats_map.get(p.member_name)
            stat_badges = ""
            if stats:
                stat_badges = f"""
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-center text-xs font-mono">
                    <div class="bg-gray-900/80 p-2 rounded-xl border border-gray-800">
                        <div class="text-gray-400 text-[10px]">Verbosity</div>
                        <div class="text-cyan-400 font-bold mt-0.5">{stats.words_per_message:.1f} w/m</div>
                    </div>
                    <div class="bg-gray-900/80 p-2 rounded-xl border border-gray-800">
                        <div class="text-gray-400 text-[10px]">Response Speed</div>
                        <div class="text-indigo-400 font-bold mt-0.5">{stats.median_response_time_seconds / 60:.1f}m</div>
                    </div>
                    <div class="bg-gray-900/80 p-2 rounded-xl border border-gray-800">
                        <div class="text-gray-400 text-[10px]">Yap Streak</div>
                        <div class="text-amber-400 font-bold mt-0.5">{stats.longest_yap_streak} msgs</div>
                    </div>
                    <div class="bg-gray-900/80 p-2 rounded-xl border border-gray-800">
                        <div class="text-gray-400 text-[10px]">Dry Rate</div>
                        <div class="text-rose-400 font-bold mt-0.5">{stats.dry_text_percentage:.1f}%</div>
                    </div>
                </div>
                """

            strengths_html = "".join([f'<li class="flex items-start gap-1.5"><span class="text-emerald-400">✓</span><span>{s}</span></li>' for s in clean_strengths])
            weaknesses_html = "".join([f'<li class="flex items-start gap-1.5"><span class="text-rose-400">✗</span><span>{w}</span></li>' for w in clean_weaknesses])

            cards.append(f"""
            <div class="glass-panel p-6 sm:p-8 rounded-3xl border border-gray-800/80 flex flex-col justify-between space-y-5">
                <div class="space-y-4">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <span class="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">{clean_title}</span>
                            <h3 class="text-2xl font-black text-white mt-0.5 flex items-center gap-2">
                                <span>{clean_name}</span>
                                <span class="text-2xl">{p.apt_emoji}</span>
                            </h3>
                        </div>
                    </div>

                    {stat_badges}

                    <div class="bg-purple-950/20 border border-purple-800/30 p-4 rounded-2xl text-xs sm:text-sm text-gray-300 leading-relaxed">
                        <div class="text-[10px] uppercase font-bold text-purple-400 font-mono mb-1">Character Roast</div>
                        {clean_roast.replace(chr(10), '<br><br>')}
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-2">
                    <div class="bg-gray-900/70 p-3 rounded-xl border border-gray-800/70">
                        <div class="font-bold text-emerald-400 font-mono mb-1.5">Conversational Superpowers</div>
                        <ul class="space-y-1 text-gray-300">
                            {strengths_html}
                        </ul>
                    </div>
                    <div class="bg-gray-900/70 p-3 rounded-xl border border-gray-800/70">
                        <div class="font-bold text-rose-400 font-mono mb-1.5">Fatal Character Flaws</div>
                        <ul class="space-y-1 text-gray-300">
                            {weaknesses_html}
                        </ul>
                    </div>
                </div>
            </div>
            """)

        return f'<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">{"".join(cards)}</div>'

    # ==========================================
    # TAB 4: RELATIONSHIP MATRIX
    # ==========================================
    def _render_tab4_relationship_matrix(self, relationship_reports: List[RelationshipReport]) -> str:
        # Sort by strength score descending
        sorted_reports = sorted(relationship_reports, key=lambda r: r.strength_score, reverse=True)
        cards = []

        for r in sorted_reports:
            clean_title = self.sanitizer.sanitize(r.couple_title)
            clean_timeline = self.sanitizer.sanitize(r.timeline)
            clean_traits = [self.sanitizer.sanitize(t) for t in r.traits]

            # Strength progress bar color
            score = max(1, min(10, r.strength_score))
            pct = score * 10
            bar_color = "bg-rose-500" if score >= 8 else ("bg-cyan-500" if score >= 5 else "bg-gray-600")

            traits_html = "".join([f'<li class="text-xs text-gray-300 flex items-start gap-1"><span class="text-indigo-400">•</span><span>{t}</span></li>' for t in clean_traits])

            cards.append(f"""
            <div class="glass-panel p-5 rounded-2xl border border-gray-800 space-y-4 flex flex-col justify-between">
                <div class="space-y-3">
                    <div class="flex items-start justify-between gap-2">
                        <div>
                            <span class="text-[10px] font-mono text-cyan-400 uppercase tracking-widest font-bold">Couple Profile</span>
                            <h4 class="text-lg font-black text-white mt-0.5">
                                {r.member_name_1} & {r.member_name_2}
                            </h4>
                            <div class="text-xs text-purple-300 font-medium italic mt-0.5 flex items-center gap-1.5">
                                <span>{r.apt_emoji}</span>
                                <span>"{clean_title}"</span>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs font-mono text-gray-400">Strength</div>
                            <div class="text-lg font-black text-cyan-400 font-mono">{score}/10</div>
                        </div>
                    </div>

                    <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                        <div class="{bar_color} h-full rounded-full" style="width: {pct}%"></div>
                    </div>

                    <p class="text-xs text-gray-300 leading-relaxed bg-gray-900/60 p-3 rounded-xl border border-gray-800/80">
                        {clean_timeline}
                    </p>
                </div>

                <div class="pt-2 border-t border-gray-800/60">
                    <div class="text-[10px] font-mono uppercase tracking-wider text-gray-400 mb-1">Dynamic Traits</div>
                    <ul class="space-y-1">
                        {traits_html}
                    </ul>
                </div>
            </div>
            """)

        return f'<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">{"".join(cards)}</div>'

    # ==========================================
    # TAB 5: CANON EVENTS ARCHIVE
    # ==========================================
    def _render_tab5_canon_events(self, event_reports: List[EventReport]) -> str:
        # Filter top events (impact >= 5) or sort by impact descending
        sorted_events = sorted(event_reports, key=lambda e: (e.impact_strength, int(e.event_id.replace("E", ""))), reverse=True)
        top_events = sorted_events[:25]

        cards = []
        for ev in top_events:
            clean_name = self.sanitizer.sanitize(ev.event_name)
            clean_happened = self.sanitizer.sanitize(ev.what_happened)
            clean_who = self.sanitizer.sanitize(ev.who_said_what)
            clean_banter = self.sanitizer.sanitize(ev.banter_analysis)

            impact_badge_color = "bg-rose-500/20 text-rose-400 border-rose-500/40" if ev.impact_strength >= 7 else "bg-amber-500/20 text-amber-400 border-amber-500/40"

            quotes_html = ""
            if ev.notable_quotes:
                sanitized_quotes = [self.sanitizer.sanitize(q) for q in ev.notable_quotes]
                q_items = "".join([f'<li class="italic text-xs text-cyan-200">{q}</li>' for q in sanitized_quotes])
                quotes_html = f"""
                <div class="bg-cyan-950/20 border border-cyan-800/30 p-3 rounded-xl mt-2">
                    <div class="text-[10px] uppercase font-mono font-bold text-cyan-400 mb-1">Notable Quotes</div>
                    <ul class="space-y-1">{q_items}</ul>
                </div>
                """

            cards.append(f"""
            <div class="glass-panel p-6 rounded-2xl border border-gray-800 space-y-3">
                <div class="flex items-start justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-bold">{ev.event_id}</span>
                            <span class="text-xs font-mono text-gray-400">Topics: {', '.join(ev.topics)}</span>
                        </div>
                        <h4 class="text-xl font-bold text-white mt-1">{clean_name}</h4>
                    </div>
                    <span class="px-2.5 py-1 rounded-full text-xs font-mono font-bold border {impact_badge_color} flex-shrink-0">
                        Impact: {ev.impact_strength}/10
                    </span>
                </div>

                <div class="text-xs sm:text-sm text-gray-300 leading-relaxed space-y-2">
                    <p><b>What Happened:</b> {clean_happened}</p>
                    <p><b>Who Said What:</b> {clean_who}</p>
                    {f'<p><b>Banter:</b> {clean_banter}</p>' if clean_banter and clean_banter != 'None' else ''}
                </div>

                {quotes_html}
            </div>
            """)

        return f'<div class="space-y-4">{"".join(cards)}</div>'
