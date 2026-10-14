# Generates the WikiPulse overall architecture diagram as SVG.
# Render to PNG with:  msedge --headless --force-device-scale-factor=2 --window-size=1400,1120 \n#     --screenshot=architecture.png architecture.svg

W, H = 1400, 1120
FONT = "Arial, Helvetica, sans-serif"

BLUE = ("#dae8fc", "#6c8ebf")
PINK = ("#f8cecc", "#b85450")
PURPLE = ("#e1d5e7", "#9673a6")
GREEN = ("#d5e8d4", "#82b366")
BRONZE = ("#f4b183", "#c55a11")
SILVER = ("#d9d9d9", "#7f7f7f")
GOLD = ("#fff2cc", "#d6b656")
WHITE_RED = ("#ffffff", "#e53935")
GREY = ("#f5f5f5", "#999999")

out = []


def text(x, y, s, size=14, weight="normal", anchor="middle", color="#000", italic=False):
    style = ' font-style="italic"' if italic else ""
    out.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
               f'font-weight="{weight}" text-anchor="{anchor}" fill="{color}"{style}>{s}</text>')


def box(x, y, w, h, colors, lines, size=14, rx=8, dashed=False):
    fill, stroke = colors
    dash = ' stroke-dasharray="6,4"' if dashed else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')
    n = len(lines)
    line_h = size + 5
    start = y + h / 2 - (n - 1) * line_h / 2 + size * 0.35
    for i, ln in enumerate(lines):
        bold = "bold" if i == 0 else "normal"
        sz = size if i == 0 else size - 2
        text(x + w / 2, start + i * line_h, ln, sz, bold)


def cylinder(x, y, w, h, colors, lines, size=15, ry=13):
    fill, stroke = colors
    rx = w / 2
    out.append(f'<path d="M {x},{y+ry} L {x},{y+h-ry} A {rx},{ry} 0 0 0 {x+w},{y+h-ry} '
               f'L {x+w},{y+ry} A {rx},{ry} 0 0 0 {x},{y+ry} Z" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    out.append(f'<ellipse cx="{x+rx}" cy="{y+ry}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    n = len(lines)
    line_h = size + 4
    start = y + ry + (h - ry) / 2 - (n - 1) * line_h / 2 + size * 0.35
    for i, ln in enumerate(lines):
        bold = "bold" if i == 0 else "normal"
        sz = size if i == 0 else size - 2
        text(x + rx, start + i * line_h, ln, sz, bold)


def arrow(points, label=None, label_pos=None, both=False):
    d = " ".join(f"{px},{py}" for px, py in points)
    start = ' marker-start="url(#arrow-start)"' if both else ""
    out.append(f'<polyline points="{d}" fill="none" stroke="#333" stroke-width="1.4" '
               f'marker-end="url(#arrow)"{start}/>')
    if label:
        lx, ly = label_pos
        w = len(label) * 6.6 + 10
        out.append(f'<rect x="{lx - w/2}" y="{ly - 12}" width="{w}" height="17" fill="#fff"/>')
        text(lx, ly, label, 12.5)


# ---------- canvas ----------
out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(W / 2, 48, "WIKIPULSE  —  OVERALL ARCHITECTURE", 28, "bold")

# ---------- sources ----------
box(60, 90, 330, 70, BLUE, ["Wikipedia REST APIs", "Pageviews (top-read) · Page Summary"])
box(410, 90, 330, 70, BLUE, ["Wikimedia EventStreams", "/v2/stream/recentchange (SSE)"])

# ---------- GitHub Actions container ----------
out.append('<rect x="40" y="215" width="720" height="495" fill="#fff" stroke="#e53935" stroke-width="1.5"/>')
out.append('<rect x="40" y="215" width="720" height="32" fill="#f44336"/>')
text(400, 237, "GitHub Actions  (scheduled jobs · free for public repos)", 16, "bold", color="#fff")

text(225, 275, "daily.yml  ·  cron daily 06:00 UTC", 14, "bold", color="#c62828")
text(575, 275, "pipeline.yml  ·  cron every 15 min", 14, "bold", color="#c62828")

# daily column
box(60, 305, 330, 60, WHITE_RED, ["daily_batch.py", "top-read pageviews · daily digest"])
box(60, 385, 330, 60, WHITE_RED, ["enrich.py", "summaries for digest articles"])
box(60, 465, 330, 60, WHITE_RED, ["retention.py", "expire old lake files + database rows"])

# pipeline column
box(410, 305, 330, 60, WHITE_RED, ["collect.py", "resume from checkpoint · filter articles + wikis"])
box(410, 385, 330, 60, WHITE_RED, ["transform.py · sql/silver.sql  (DuckDB)", "parse · type-cast · dedupe · quarantine"])
box(410, 465, 330, 60, WHITE_RED, ["transform.py · sql/gold.sql  (DuckDB)", "15-min page buckets · hourly wiki activity"])
box(410, 545, 330, 60, WHITE_RED, ["quality.py", "duplicates · quarantine rate · future dates"])
box(410, 625, 330, 60, WHITE_RED, ["db.py publish + enrich.py", "upsert gold · refresh_trending() · summaries"])

# ---------- checkpoint + storage group ----------
box(840, 205, 520, 52, PINK, ["Checkpoint State Store", "Postgres pipeline_state (Last-Event-ID) · saved with gold"])
out.append('<rect x="820" y="275" width="560" height="240" rx="10" fill="#fafafa" '
           'stroke="#999" stroke-width="1.2" stroke-dasharray="7,5"/>')
text(836, 296, "Supabase Storage  ·  bucket \"lake\" via Storage API (free 1 GB)", 14, "bold", anchor="start", color="#555")

cylinder(840, 310, 520, 85, BRONZE, ["Bronze Layer", "lake/bronze/date=…/  ·  raw events, Parquet  ·  3 days"])
cylinder(840, 410, 520, 92, SILVER, ["Silver Layer", "lake/silver/  +  lake/quarantine/  ·  clean, typed  ·  14 days"])

# ---------- Gold ----------
cylinder(840, 535, 520, 150, GOLD, [
    "Gold Layer  (Supabase Postgres)",
    "page_activity_15m · wiki_activity_hourly · trending_now",
    "breaking_alerts · page_summaries · daily_top_read",
    "daily_digest · pipeline_runs (monitoring)",
])

# ---------- Website ----------
box(880, 765, 480, 80, PURPLE, [
    "Next.js Website on Vercel",
    "/  ·  /topic  ·  /india  ·  /stats  ·  /digest  ·  /about",
    "use cache · refreshes every 5 min",
], size=16)

# ---------- arrows: sources ----------
arrow([(575, 160), (575, 213)], "live edits (SSE)", (575, 190))
arrow([(575, 284), (575, 305)])
arrow([(225, 160), (225, 213)], "REST calls", (225, 190))
arrow([(225, 284), (225, 305)])

# column flows
for y in (365, 445):
    arrow([(225, y), (225, y + 20)])
for y in (365, 445, 525, 605):
    arrow([(575, y), (575, y + 20)])

# pipeline → storage
arrow([(740, 322), (795, 322), (795, 231), (840, 231)], both=True)
arrow([(740, 350), (840, 350)])
arrow([(740, 415), (805, 415), (805, 458), (840, 458)])
arrow([(740, 655), (840, 655)])

# daily → gold
arrow([(225, 525), (225, 730), (900, 730), (900, 682)], "daily gold tables + cleanup", (560, 734))

# gold → website
arrow([(1120, 685), (1120, 765)], "read-only (anon key + RLS)", (1230, 734))

# ---------- CI/CD ----------
out.append('<rect x="40" y="875" width="1320" height="105" rx="10" fill="#f6fbf4" stroke="#82b366" stroke-width="1.5"/>')
text(56, 898, "DEVELOPER WORKFLOW (CI/CD)", 14, "bold", anchor="start", color="#2e7d32")
cx = [60, 390, 720, 1050]
box(cx[0], 910, 290, 55, GREEN, ["git push to GitHub", "pipeline / web code changes"])
box(cx[1], 910, 290, 55, GREEN, ["ci.yml", "pytest · lint on every push"])
box(cx[2], 910, 290, 55, GREEN, ["Scheduled jobs run code on main", "pipeline.yml · daily.yml"])
box(cx[3], 910, 290, 55, GREEN, ["Vercel auto-deploy", "web/ → live site"])
for i in range(3):
    arrow([(cx[i] + 290, 937), (cx[i + 1], 937)])

# ---------- local learning mode ----------
out.append('<rect x="40" y="1000" width="1320" height="100" rx="10" fill="#fff" stroke="#999" '
           'stroke-width="1.3" stroke-dasharray="7,5"/>')
text(56, 1022, "LOCAL LEARNING MODE  (streaming_local/)  —  same silver/gold logic, true streaming",
     14, "bold", anchor="start", color="#555")
lx = [60, 390, 720, 1050]
box(lx[0], 1033, 290, 55, BLUE, ["EventStreams producer", "streaming_local/producer.py"])
box(lx[1], 1033, 290, 55, BLUE, ["Kafka (Docker, KRaft)", "topic: wiki_recentchange"])
box(lx[2], 1033, 290, 55, BLUE, ["Spark Structured Streaming", "watermarks · windows · checkpoints"])
box(lx[3], 1033, 290, 55, GREY, ["Delta Lake (local)", "bronze → silver → gold"])
for i in range(3):
    arrow([(lx[i] + 290, 1060), (lx[i + 1], 1060)])

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       '<defs>'
       '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
       '<path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker>'
       '<marker id="arrow-start" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
       '<path d="M10,0 L0,5 L10,10 z" fill="#333"/></marker>'
       '</defs>' + "\n".join(out) + "</svg>")

from pathlib import Path

with open(Path(__file__).with_name("architecture.svg"), "w", encoding="utf-8") as f:
    f.write(svg)
print("wrote architecture.svg")
