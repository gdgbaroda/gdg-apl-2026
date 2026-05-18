#!/usr/bin/env python3
"""Mode-aware homepage builder.

Pre-event  (no <data_dir>/ranking.json): renders the challenge briefs from
event.config.json plus a reactions strip — what attendees see when they
scan the projector's QR.

Post-event (ranking.json exists): renders the celebration page with podium,
stats, commit-activity timeline, award highlights, and quotable lines.

Flip from one to the other by running the scoring pipeline (which produces
ranking.json) and re-running this script.

Flags:
  --preview   write to web/preview/ instead of web/ (review without disrupting prod)
"""
import json, pathlib, html, datetime as dt, sys
from collections import Counter
from event_config import (
    DATA_DIR, REPO_ROOT, EVENT_WINDOW_START, EVENT_WINDOW_END,
    CHAPTER_NAME, EVENT_TITLE, EVENT_YEAR, QUOTES, CHALLENGES, API_URL,
)

ROOT = pathlib.Path(__file__).parent
PREVIEW = '--preview' in sys.argv
OUT = REPO_ROOT / 'web' / ('preview' if PREVIEW else '')
OUT.mkdir(parents=True, exist_ok=True)
ASSET_PREFIX = '/preview' if PREVIEW else ''

RANKING_PATH = DATA_DIR / 'ranking.json'
POST_EVENT = RANKING_PATH.exists()
print(f'mode: {"POST_EVENT" if POST_EVENT else "PRE_EVENT"}')


def page_head(title):
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
    <meta name="theme-color" content="#000000" />
    <title>{html.escape(title)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@500;700&family=Google+Sans+Text:wght@400;500&display=swap" />
    <link rel="stylesheet" href="{ASSET_PREFIX}/styles.css" />
  </head>'''


def brand_row():
    return '<div class="brand-row"><span class="dot dot-blue"></span><span class="dot dot-red"></span><span class="dot dot-yellow"></span><span class="dot dot-green"></span></div>'


# ───────────────────────── PRE-EVENT MODE ─────────────────────────

def render_during_event():
    """Challenge briefs from config + a reactions strip wired to the API."""
    challenges_html = ''
    for i, c in enumerate(CHALLENGES, 1):
        challenges_html += f'''
      <article class="card card-{html.escape(c.get("color","blue"))}">
        <div class="pill">Challenge {i}</div>
        <h2>{html.escape(c.get("title",""))}</h2>
        <p>{html.escape(c.get("prompt",""))}</p>
      </article>'''

    # Reactions strip: ids must match the api emoji allowlist
    emoji_ids = [
        ('heart', '❤️'), ('fire', '🔥'), ('party', '🎉'), ('clap', '👏'), ('bat', '🏏'),
        ('six', '6️⃣'), ('four', '4️⃣'), ('laugh', '😂'), ('shock', '😱'), ('raise', '🙌'),
    ]
    btns = ''.join(
        f'<button class="btn" type="button" data-id="{i}" aria-label="{i}">{g}</button>'
        for i, g in emoji_ids
    )

    return f'''{page_head(f"{EVENT_TITLE} · {CHAPTER_NAME}")}
  <body data-mode="pre-event" data-api="{html.escape(API_URL)}">
    <main class="app">
      <header class="brand">
        {brand_row()}
        <h1>{html.escape(EVENT_TITLE)}</h1>
        <p class="subtitle">{html.escape(CHAPTER_NAME)}</p>
      </header>

      <section class="challenges" id="challenges">{challenges_html}
      </section>

      <section class="reactions">
        <div class="r-head">
          <span class="r-label">React</span>
          <span class="status live" id="status">live</span>
        </div>
        <div class="r-grid" id="grid">{btns}</div>
        <p class="r-note">Just for fun — tap to send to the big screen.</p>
      </section>

      <footer class="foot">{html.escape(CHAPTER_NAME)} · {EVENT_YEAR}</footer>
    </main>
    <script src="{ASSET_PREFIX}/app.js"></script>
  </body>
</html>
'''


# ───────────────────────── POST-EVENT MODE ─────────────────────────

def medal(rank):
    return '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else ''


def render_post_event():
    """Celebration page: podium, stats, timeline, awards, quotes, tap-to-celebrate."""
    subs_path = ROOT / 'submissions.json'
    subs = json.loads(subs_path.read_text()) if subs_path.exists() else []
    ranking = json.loads(RANKING_PATH.read_text())
    timing = json.loads((DATA_DIR / 'commit-timing.json').read_text())
    sub_by_slug = {s['_slug']: s for s in subs}

    def is_public(slug):
        return ((sub_by_slug.get(slug, {}) or {}).get('Can we share your submission publicly?') or '').strip().lower() == 'yes'

    public_ranking = [s for s in ranking if is_public(s['slug'])]
    public_ranking.sort(key=lambda x: (-x['total'], -(x['scores'].get('agentic', 0) + x['scores'].get('fit', 0))))
    for i, s in enumerate(public_ranking, 1):
        s['rank'] = i

    total_subs = len(ranking)
    empty_count = sum(1 for t in timing if t.get('verdict') in ('NO_COMMITS', 'POST_EVENT_ONLY'))

    WIN_START = EVENT_WINDOW_START
    WIN_END = EVENT_WINDOW_END
    in_window_commits = []
    score_by_slug = {s['slug']: s.get('total', 0) for s in public_ranking}
    for t in timing:
        for c in t.get('commits') or []:
            try:
                ts = dt.datetime.fromisoformat(c)
            except Exception:
                continue
            if WIN_START <= ts <= WIN_END:
                in_window_commits.append((ts, t['slug'], score_by_slug.get(t['slug'], 0)))
    total_window_commits = len(in_window_commits)

    def collect_text(s):
        return ' '.join((s.get(k) or '') for k in (
            'Stack & tools', 'How is it agentic / how did you use AI?',
            'What does it do?', 'One-line pitch',
        )).lower()
    texts = {s['_slug']: collect_text(s) for s in subs}
    def count_mentions(needles):
        if isinstance(needles, str): needles = [needles]
        return sum(1 for t in texts.values() if any(n in t for n in needles))
    gemini_n = count_mentions(['gemini', 'google-generative-ai', 'genai'])
    tool_pairs = [
        ('Gemini', gemini_n),
        ('OpenAI / GPT', count_mentions(['openai', 'gpt-', 'gpt ', 'azure openai', 'chatgpt api'])),
        ('Groq', count_mentions(['groq'])),
        ('CrewAI', count_mentions(['crewai', 'crew-ai'])),
        ('LangChain', count_mentions(['langchain'])),
        ('Cursor', count_mentions(['cursor'])),
        ('Lovable', count_mentions(['lovable'])),
        ('Firebase / Firestore', count_mentions(['firebase', 'firestore'])),
        ('React', count_mentions(['react'])),
        ('Next.js', count_mentions(['next.js', 'nextjs'])),
        ('Vite', count_mentions(['vite'])),
        ('FastAPI', count_mentions(['fastapi'])),
    ]
    tool_pairs = [(n, c) for n, c in tool_pairs if c >= 2]
    tool_pairs.sort(key=lambda x: -x[1])
    max_tool = max((c for _, c in tool_pairs), default=1)

    top3 = public_ranking[:3]

    perfect_agentic = next((s for s in public_ranking if s.get('scores', {}).get('agentic') == 10), None)
    commit_counts_in_window = Counter(c[1] for c in in_window_commits)
    most_commits_slug = max(commit_counts_in_window, key=commit_counts_in_window.get) if commit_counts_in_window else None
    most_commits = next((s for s in public_ranking if s['slug'] == most_commits_slug), None) if most_commits_slug else None
    most_commits_n = commit_counts_in_window.get(most_commits_slug, 0) if most_commits_slug else 0

    by_challenge = {}
    for s in public_ranking:
        by_challenge.setdefault(s.get('challenge') or '', s)
    challenge_top = []
    for c in CHALLENGES:
        t = by_challenge.get(c['title'])
        if t: challenge_top.append((c['title'], t))

    quotes = [(q['who'], q['text']) for q in QUOTES]

    # Podium HTML — middle (#1) is centered + tallest
    podium_html = ''
    if len(top3) >= 3:
        for s, pos in zip([top3[1], top3[0], top3[2]], ['second', 'first', 'third']):
            podium_html += f'''
        <a class="pod {pos}" href="/scoreboard/" aria-label="View scoreboard">
          <div class="pod-medal">{medal(s["rank"])}</div>
          <div class="pod-rank">#{s["rank"]}</div>
          <div class="pod-name">{html.escape(s.get("name") or "")}</div>
          <div class="pod-title">{html.escape(s.get("title") or "")}</div>
          <div class="pod-score">{s["total"]}<span class="of">/50</span></div>
        </a>'''

    cloud_html = ''.join(
        f'<span class="tool" style="font-size:{0.8 + (c / max_tool) * 1.4:.2f}rem">{html.escape(n)} <span class="tool-count">{c}</span></span>'
        for n, c in tool_pairs
    )

    _dur = (EVENT_WINDOW_END - EVENT_WINDOW_START).total_seconds()
    duration_label = f'{int(_dur//3600)}h {int((_dur%3600)//60)}m'

    award_cards = []
    if perfect_agentic:
        award_cards.append(('Perfect Agentic 10/10', perfect_agentic.get('name'), perfect_agentic.get('title'),
                            'Top agentic AI score across the field', '⚡'))
    if most_commits:
        award_cards.append((f'Most Commits · {most_commits_n}', most_commits.get('name'), most_commits.get('title'),
                            f'{most_commits_n} commits in the {duration_label} window — relentless', '🛠'))
    for title, t in challenge_top:
        award_cards.append((f'Top in {title}', t.get('name'), t.get('title'),
                            f'{t["total"]}/50', '📊' if 'Data' in title else '🎮'))
    awards_html = ''.join(
        f'''
        <article class="award">
          <div class="award-icon">{icon}</div>
          <div class="award-label">{html.escape(label)}</div>
          <div class="award-title">{html.escape(title or "")}</div>
          <div class="award-name">{html.escape(name or "")}</div>
          <div class="award-sub">{html.escape(sub)}</div>
        </article>''' for label, name, title, sub, icon in award_cards
    )

    quotes_html = ''.join(
        f'<blockquote class="quote{" active" if i == 0 else ""}" data-i="{i}"><p>“{html.escape(q)}”</p><cite>— {html.escape(who)}</cite></blockquote>'
        for i, (who, q) in enumerate(quotes)
    )

    # Commit timeline SVG
    tl_w, tl_h, tl_pad = 720, 100, 30
    bucket_min = 10
    n_buckets = int((WIN_END - WIN_START).total_seconds() // 60 // bucket_min) + 1
    buckets = [0] * n_buckets
    for ts, _, _ in in_window_commits:
        idx = int((ts - WIN_START).total_seconds() // 60 // bucket_min)
        if 0 <= idx < n_buckets:
            buckets[idx] += 1
    max_b = max(buckets) or 1
    bar_w = (tl_w - 2 * tl_pad) / max(len(buckets), 1)
    bars = ''
    for i, n in enumerate(buckets):
        if n == 0: continue
        h_px = (n / max_b) * (tl_h - 30)
        x = tl_pad + i * bar_w
        frac = i / max(len(buckets) - 1, 1)
        colour = '#4285F4' if frac < 0.4 else '#FBBC04' if frac < 0.8 else '#EA4335'
        bars += f'<rect x="{x:.1f}" y="{tl_h - 18 - h_px:.1f}" width="{max(bar_w-1, 1):.1f}" height="{h_px:.1f}" fill="{colour}" opacity="0.85"><title>{n} commits</title></rect>'

    hour_count = max(1, int(_dur // 3600))
    labels = ''
    for j in range(hour_count + 1):
        lbl = (WIN_START + dt.timedelta(hours=j)).strftime('%H:00')
        x = tl_pad + j * (tl_w - 2*tl_pad) / hour_count
        labels += f'<text x="{x:.0f}" y="{tl_h - 4}" fill="#9aa0a6" font-size="10">{lbl}</text>'

    win_start_lbl = EVENT_WINDOW_START.strftime('%H:%M')
    win_end_lbl   = EVENT_WINDOW_END.strftime('%H:%M')
    challenges_active = total_subs - empty_count

    return f'''{page_head(f"{EVENT_TITLE} · {EVENT_YEAR}")}
  <body data-mode="post-event">
    <canvas id="emoji-canvas" aria-hidden="true"></canvas>
    <main class="page">

      <section class="hero">
        {brand_row()}
        <h1>That's a wrap.</h1>
        <p class="lead">{html.escape(EVENT_TITLE)} · {html.escape(CHAPTER_NAME)}</p>
        <p class="tagline"><span class="tag-num">{total_subs}</span> builders · <span class="tag-num">{total_window_commits}</span> commits in <span class="tag-num">{duration_label}</span></p>
        <div class="hero-cta"><a class="primary" href="/scoreboard/">View full scoreboard →</a></div>
      </section>

      <section class="stats">
        <div class="stat"><div class="stat-num" data-target="{total_subs}">0</div><div class="stat-label">Submissions</div></div>
        <div class="stat"><div class="stat-num" data-target="{total_window_commits}">0</div><div class="stat-label">Commits in window</div></div>
        <div class="stat"><div class="stat-num" data-target="{gemini_n}">0</div><div class="stat-label">Built with Gemini</div></div>
        <div class="stat"><div class="stat-num" data-target="{challenges_active}">0</div><div class="stat-label">Projects shipped</div></div>
      </section>

      <section class="section">
        <h2>The Podium</h2>
        <div class="podium">{podium_html}</div>
        <p class="section-foot">Top three across all {total_subs} submissions. <a href="/scoreboard/">Full ranking →</a></p>
      </section>

      <section class="section">
        <h2>The {duration_label} Heartbeat</h2>
        <p class="section-lede">{total_window_commits} commits between {win_start_lbl} and {win_end_lbl}. Each bar = 10 min.</p>
        <svg class="timeline" viewBox="0 0 {tl_w} {tl_h}" preserveAspectRatio="none" aria-label="Commit activity timeline">
          <line x1="{tl_pad}" x2="{tl_w - tl_pad}" y1="{tl_h - 18}" y2="{tl_h - 18}" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
          {bars}
          {labels}
        </svg>
      </section>

      <section class="section quotes-section">
        <h2>In Their Words</h2>
        <div class="quotes-stage">{quotes_html}</div>
      </section>

      <section class="section">
        <h2>Award Highlights</h2>
        <div class="awards">{awards_html}</div>
      </section>

      <section class="section">
        <h2>The Stack</h2>
        <div class="tool-cloud">{cloud_html}</div>
      </section>

      <section class="section reactions-section">
        <h2>One More for the Room</h2>
        <p class="section-lede">A leftover from event night. Tap to send.</p>
        <div class="r-grid">
          <button class="rxn" data-glyph="❤️">❤️</button>
          <button class="rxn" data-glyph="🔥">🔥</button>
          <button class="rxn" data-glyph="🎉">🎉</button>
          <button class="rxn" data-glyph="👏">👏</button>
          <button class="rxn" data-glyph="🏏">🏏</button>
          <button class="rxn" data-glyph="6️⃣">6️⃣</button>
          <button class="rxn" data-glyph="4️⃣">4️⃣</button>
          <button class="rxn" data-glyph="😂">😂</button>
          <button class="rxn" data-glyph="😱">😱</button>
          <button class="rxn" data-glyph="🙌">🙌</button>
        </div>
      </section>

      <footer class="foot">
        <p>{html.escape(CHAPTER_NAME)} · {EVENT_YEAR}</p>
        <p><a href="/scoreboard/">Full scoreboard →</a></p>
      </footer>

    </main>

    <script src="{ASSET_PREFIX}/app.js"></script>
  </body>
</html>
'''


# ───────────────────────── dispatch ─────────────────────────

doc = render_post_event() if POST_EVENT else render_during_event()
(OUT / 'index.html').write_text(doc)
print(f'wrote {OUT / "index.html"}')
