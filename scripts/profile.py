#!/usr/bin/env python3
"""Builds assets/profile.svg: a dark bento-grid profile card (greys sampled from the pfp).

Needs: gh CLI + GH_TOKEN, and PROFILE_USER (defaults to inferism). Set PROFILE_FAKE=<json file> to test offline.
"""
import json
import math
import os
import subprocess
import textwrap
from datetime import date, datetime, timezone

USER = os.environ.get("PROFILE_USER", "inferism")  # not USERNAME: that's the OS account on Windows
W = 1000

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes { ... on Repository { name description isPrivate stargazerCount pushedAt primaryLanguage { name } } }
    }
  }
}"""

SANS = "'Segoe UI Variable Display','Segoe UI',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
# the pfp's tones: black ink, five halftone greys, paper
K, G1, G2, G3, G4, G5, P = "#0a0a0a", "#4c4c4c", "#676767", "#7a7a7a", "#9c9c9c", "#c4c4c4", "#f2f2f0"
LANG_TONES = [P, G5, G4, G3, G2, G1, "#333333"]
HEAT = ["#1a1a1a", G1, G3, G5, P]

BIO = "2nd-year BSIT student building web apps, CLIs and desktop tools I'd actually use."
TAGS = ["Web apps", "CLIs", "Desktop tools"]
STACK = [  # label, chips (the first chip of each row is drawn as the primary one)
    ("languages", ["TypeScript", "JavaScript", "Python", "HTML", "CSS"]),
    ("frameworks", ["Next.js", "React"]),
    ("backend", ["Firebase Auth", "Firestore", "Security Rules"]),
    ("deploy", ["Vercel"]),
    ("testing", ["Firebase Emulators", "tsx tests"]),
    ("automation", ["Python", "GitHub Actions", "GraphQL API", "SVG"]),
]
LANG_NAMES = {"Visual Basic .NET": "VB.NET"}
FILE_FOR = {"JavaScript": "main.js", "TypeScript": "index.ts", "Python": "main.py", "Rust": "main.rs",
            "CSS": "style.css", "HTML": "index.html", "Go": "main.go", "Java": "Main.java"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fetch():
    fake = os.environ.get("PROFILE_FAKE")
    if fake:
        with open(fake, encoding="utf8") as f:
            return json.load(f)
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"login={USER}", "-f", f"query={QUERY}"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def sorted_days(cal):
    return sorted(
        (d for w in cal["weeks"] for d in w["contributionDays"]),
        key=lambda d: d["date"],
    )


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    if counts and counts[-1] == 0:  # today may not have activity yet
        counts = counts[:-1]
    current = 0
    for c in reversed(counts):
        if c == 0:
            break
        current += 1
    return current, longest


def top_languages(repos, n=6):
    """Public-repo language totals as [(name, share)], plus the share left in 'other'."""
    totals = {}
    for r in (repos or {}).get("nodes", []):
        for e in r["languages"]["edges"]:
            totals[e["node"]["name"]] = totals.get(e["node"]["name"], 0) + e["size"]
    whole = sum(totals.values())
    if not whole:
        return [], 0.0
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    top = [(LANG_NAMES.get(k, k), v / whole) for k, v in ranked[:n]]
    return top, 1 - sum(s for _, s in top)


# ── drawing helpers ──
def t(x, y, s, size=14, fill=P, weight="normal", anchor="start", font=None, ls=None, extra=""):
    e = f' letter-spacing="{ls}"' if ls is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font or SANS}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{e}{extra}>{esc(s)}</text>')


def R(x, y, w, h, fill, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" {extra}/>'


def tile(x, y, w, h):
    return R(x, y, w, h, "url(#tf)", 'rx="24" stroke="url(#edge)" stroke-width="1.2"')


def label(x, y, s, right=None):
    r = t(x, y, s, 13, G4, "bold", ls=2.2)
    return r + (t(right[0], y, right[1], 13, G3, anchor="end", ls=1.5) if right else "")


def chip_w(s, px=12):
    return len(s) * px * 0.58 + 22


def fmt_day(d):
    return f"{d:%b} {d.day}"


def ring(cx, cy, r0, r1, parts):
    """Segmented donut: parts = [(share, colour)]."""
    out, a = [], -90.0
    for share, col in parts:
        a1 = a + 360 * share
        if a1 - a > 1.8:
            A0, A1 = math.radians(a + 0.8), math.radians(a1 - 0.8)
            big = 1 if a1 - a > 180 else 0
            out.append(f'<path d="M{cx + r1 * math.cos(A0):.2f} {cy + r1 * math.sin(A0):.2f} A{r1} {r1} 0 {big} 1 '
                       f'{cx + r1 * math.cos(A1):.2f} {cy + r1 * math.sin(A1):.2f} L{cx + r0 * math.cos(A1):.2f} {cy + r0 * math.sin(A1):.2f} '
                       f'A{r0} {r0} 0 {big} 0 {cx + r0 * math.cos(A0):.2f} {cy + r0 * math.sin(A0):.2f}Z" fill="{col}"/>')
        a = a1
    return "".join(out)


# ── sections ──
def hero(now):
    o = [tile(24, 24, 620, 300)]
    dots = []  # halftone screentone bleeding in from the top-right corner, like the pfp's shading
    for gy in range(24, 330, 11):
        for gx in range(24, 650, 11):
            off = 5.5 if (gy // 11) % 2 else 0
            r = 3.6 * (1 - math.hypot(gx + off - 650, gy - 10) / 430)
            if r > 0.35:
                dots.append(f'<circle cx="{gx + off}" cy="{gy}" r="{r:.2f}"/>')
    o.append(f'<g clip-path="url(#hero)"><g fill="#fff" fill-opacity="0.085">{"".join(dots)}</g>'
             '<circle cx="640" cy="30" r="320" fill="url(#glow)"/></g>')
    pill = f"Shipping in public · {now:%b %Y}"
    pw = len(pill) * 7.3 + 44
    o.append(R(52, 52, pw, 28, "#141414", 'rx="14" stroke="#2e2e2e"'))
    o.append(f'<circle cx="69" cy="66" r="7" fill="{P}" fill-opacity="0.15" class="pulse"/><circle cx="69" cy="66" r="3.5" fill="{P}"/>')
    o.append(t(82, 71, pill, 13, G5))
    size = min(110, 560 / (len(USER) * 0.56))
    o.append(t(46, 192, USER, round(size), P, "bold", ls=-5.5))
    for i, ln in enumerate(textwrap.wrap(BIO, 50)[:2]):
        o.append(t(52, 236 + i * 26, ln, 19, G4))
    x = 52
    for s in TAGS:
        w = chip_w(s, 14)
        o.append(R(x, 282, w, 30, "none", f'rx="15" stroke="{G2}"') + t(x + w / 2, 302, s, 14, G5, anchor="middle"))
        x += w + 8
    o.append(t(616, 302, f"github.com/{USER} ↗", 14, G3, anchor="end", font=MONO))
    return "".join(o)


def headline(total, weekly, months):
    o = [tile(660, 24, 316, 300), label(688, 62, "CONTRIBUTIONS", (948, "LAST 12 MO"))]
    num = f"{total:,}"
    o.append(t(682, 168, num, 112 if len(num) <= 3 else 92 if len(num) <= 5 else 76, P, "bold", ls=-5))
    (pm, pc), (cm, cc) = months[-2], months[-1]
    if pc:
        d = round(100 * (cc - pc) / pc)
        chip = f"{'▲' if d >= 0 else '▼'} {abs(d)}% vs {pm}"
    else:
        chip = f"▲ {cc} this month" if cc else "quiet month"
    cw = len(chip) * 7.9 + 28
    o.append(R(688, 184, cw, 28, "url(#chipP)", 'rx="14"') + t(688 + cw / 2, 203, chip, 13, K, "bold", "middle"))
    mx = max(weekly) or 1
    n = len(weekly)
    pts = [(661 + i * 314 / max(n - 1, 1), 322 - 92 * (v / mx) ** 0.7) for i, v in enumerate(weekly)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    o.append(f'<g clip-path="url(#big)"><polygon points="661,324 {line} 975,324" fill="url(#ag)"/>'
             f'<polyline class="dr" points="{line}" fill="none" stroke="{P}" stroke-width="1.8" stroke-linejoin="round"/></g>')
    ex, ey = pts[-1]
    o.append(f'<circle cx="{ex - 6:.1f}" cy="{ey:.1f}" r="4" fill="{P}" class="pulse"/>')
    return "".join(o)


def stat_row(total, commits, prs, current, longest, peak, last30):
    o = []

    def head(x, lab, num, foot):
        s = tile(x, 340, 226, 170) + label(x + 24, 376, lab)
        s += t(x + 21, 456, f"{num:,}", 68 if num < 1000 else 56, P, "bold", ls=-3)
        return s + (t(x + 24, 490, foot, 15, G4) if foot else "")

    pct = commits / total if total else 0
    o.append(head(24, "COMMITS", commits, f"{round(100 * pct)}% of all activity"))
    cx, cy, r = 206, 418, 24
    circ = 2 * math.pi * r
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#242424" stroke-width="7"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{P}" stroke-width="7" stroke-linecap="round" '
             f'stroke-dasharray="{circ * pct:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>')

    o.append(head(266, "PULL REQUESTS", prs, "last 12 months"))
    gx, gy = 442, 398  # merge glyph
    o.append(f'<g fill="none" stroke="{G4}" stroke-width="2.4" stroke-linecap="round"><circle cx="{gx}" cy="{gy}" r="5"/>'
             f'<circle cx="{gx}" cy="{gy + 42}" r="5"/><circle cx="{gx + 26}" cy="{gy + 24}" r="5" stroke="{P}"/>'
             f'<path d="M{gx} {gy + 5}V{gy + 37}"/><path d="M{gx} {gy + 6}C{gx} {gy + 20} {gx + 26} {gy + 8} {gx + 26} {gy + 19}"/></g>')

    o.append(head(508, "DAY STREAK", current, None if current else "no streak yet"))
    o.append(t(710, 376, f"longest {longest}", 13, G4, anchor="end"))
    bars = min(current, 19)
    for k in range(bars):
        last = k == bars - 1
        h = 4 + k * 0.9
        o.append(R(532 + k * 9.6, 480 - h, 6, h, P if last else G2, 'rx="2"' + (' class="pulse"' if last else "")))

    pd, pc = peak
    o.append(head(750, "PEAK DAY", pc, f"contributions on {fmt_day(pd)}"))
    m = max(last30) or 1
    sp = [(900 + i * 52 / max(len(last30) - 1, 1), 436 - 44 * c / m) for i, c in enumerate(last30)]
    o.append(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in sp)}" fill="none" stroke="{G3}" stroke-width="1.6" stroke-linejoin="round"/>')
    if any(last30):
        px, py = min(sp, key=lambda p: p[1])
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{P}"/>')
    return "".join(o)


def level(c, mx):
    if c == 0:
        return 0
    f = c / mx
    return 1 if f < 0.1 else 2 if f < 0.3 else 3 if f < 0.55 else 4


def heatmap(cal, days, active):
    weeks = cal["weeks"]
    n = len(weeks)
    step = min(17.0, 900 / n)
    cell = step - 4
    mx = max(d["contributionCount"] for d in days) or 1
    first, last = date.fromisoformat(days[0]["date"]), date.fromisoformat(days[-1]["date"])
    o = [tile(24, 526, 952, 240), t(52, 566, "Contribution activity", 18, P, "bold"),
         t(52, 586, f"{first:%b %Y} – {last:%b %Y} · {active} active days", 14, G4),
         t(838, 567, "Less", 13, G3, anchor="end"), t(932, 567, "More", 13, G3)]
    o += [R(848 + k * 16, 556, 11, 11, c, 'rx="2.5"') for k, c in enumerate(HEAT)]
    seen, last_x = set(), -99
    for w, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            dd = date.fromisoformat(d["date"])
            wd = (dd.weekday() + 1) % 7  # Sunday first, like GitHub
            x, y = 52 + w * step, 604 + wd * step
            today = d["date"] == days[-1]["date"]
            o.append(R(x, y, cell, cell, HEAT[level(d["contributionCount"], mx)], 'rx="3"' + (' class="pulse"' if today else "")))
            if dd.day <= 7 and (dd.year, dd.month) not in seen and w > 0:
                seen.add((dd.year, dd.month))
                if x - last_x > 40:
                    o.append(t(x, 746, f"{dd:%b}", 13, G4))
                    last_x = x
    return "".join(o)


def languages(y, h, langs, other):
    o = [tile(24, y, 360, h), t(52, y + 40, "Languages", 18, P, "bold"), t(356, y + 40, "by bytes", 14, G4, anchor="end")]
    parts = [(s, LANG_TONES[i]) for i, (_, s) in enumerate(langs)]
    if other > 0.0005:
        parts.append((other, "#2a2a2a"))
    cy = y + 60 + (h - 60) / 2
    o.append(ring(118, cy, 44, 64, parts))
    o.append(t(118, cy + 6, len(langs), 24, P, "bold", "middle") + t(118, cy + 22, "langs", 12, G3, anchor="middle"))
    rows = [(n, s, LANG_TONES[i]) for i, (n, s) in enumerate(langs)]
    if other > 0.0005:
        rows.append(("Other", other, "#2a2a2a"))
    y0 = cy - (len(rows) - 1) * 14 + 5
    for i, (n, s, col) in enumerate(rows):
        yy = y0 + i * 28
        o.append(R(200, yy - 10, 10, 10, col, 'rx="2.5"') + t(218, yy, n, 16, G5) + t(358, yy, f"{100 * s:.1f}%", 14, G4, anchor="end", font=MONO))
    return "".join(o)


def stack(y, h, x0=400):
    o = [tile(x0, y, 976 - x0, h), t(x0 + 28, y + 40, "Stack", 18, P, "bold"), t(948, y + 40, "daily drivers", 14, G4, anchor="end")]
    for i, (cat, items) in enumerate(STACK):
        yy = y + 64 + i * 44
        o.append(t(x0 + 28, yy + 20, cat, 13, G4, font=MONO))
        cx = x0 + 120
        for k, it in enumerate(items):
            cw = chip_w(it, 14)
            if k == 0:
                o.append(R(cx, yy, cw, 30, "url(#chipP)", 'rx="15"') + t(cx + cw / 2, yy + 20, it, 14, K, "bold", "middle"))
            else:
                o.append(R(cx, yy, cw, 30, "#171717", 'rx="15" stroke="#333"') + t(cx + cw / 2, yy + 20, it, 14, G5, anchor="middle"))
            cx += cw + 8
    return "".join(o)


def repo_info(r, now):
    pushed = datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))
    age = (now - pushed).days
    return dict(name=r["name"], desc=r.get("description") or "", stars=r.get("stargazerCount") or 0,
                lang=((r.get("primaryLanguage") or {}).get("name") or ""),
                status="ACTIVE" if age <= 3 else "IDLE" if age <= 30 else "DORMANT",
                pushed=f"pushed {pushed.day} {pushed:%b}")


def projects(y, pinned, now):
    repos = [repo_info(r, now) for r in (pinned or {}).get("nodes", []) if r and r.get("name") and not r.get("isPrivate")][:5]
    if not repos:
        return "", 0
    o = []
    f, rest = repos[0], repos[1:]
    fw = 468 if rest else 952
    o.append(tile(24, y, fw, 300))
    o.append(R(52, y + 28, 100, 28, "url(#chipP)", 'rx="14"') + t(102, y + 46.5, "FEATURED", 12, K, "bold", "middle", ls=1.5))
    wx, wy = 24 + fw - 202, y + 24  # tiny editor window
    o.append(R(wx, wy, 178, 104, "#0b0b0b", 'rx="10" stroke="#2a2a2a"') + R(wx, wy, 178, 22, "#151515", 'rx="10"') + R(wx, wy + 12, 178, 10, "#151515"))
    o += [f'<circle cx="{wx + 13 + k * 11}" cy="{wy + 11}" r="3" fill="{G1}"/>' for k in range(3)]
    o.append(t(wx + 168, wy + 15, FILE_FOR.get(f["lang"], "README.md"), 9.5, G2, anchor="end", font=MONO))
    for k, (ind, w1, c1, w2, c2) in enumerate([(0, 34, G4, 52, G2), (12, 26, G3, 70, G1), (12, 44, G5, 30, G2), (0, 14, G4, 0, G1)]):
        yy = wy + 34 + k * 15
        o.append(t(wx + 10, yy + 6, k + 1, 8.5, "#3a3a3a", font=MONO) + R(wx + 26 + ind, yy, w1, 6, c1, 'rx="3"'))
        if w2:
            o.append(R(wx + 30 + ind + w1, yy, w2, 6, c2, 'rx="3"'))
    o.append(R(wx + 44, wy + 79, 2, 10, P, 'class="cur"'))
    nsize = min(54, 400 / max(len(f["name"]) * 0.55, 1))
    o.append(t(50, y + 130, f["name"], round(nsize), P, "bold", ls=-1.5))
    for i, ln in enumerate(textwrap.wrap(f["desc"], 40 if rest else 80, max_lines=2, placeholder="…")):
        o.append(t(52, y + 166 + i * 25, ln, 17, G5))
    o.append(R(24, y + 242, fw, 1, "#1e1e1e"))
    if f["lang"]:
        o.append(f'<circle cx="58" cy="{y + 271}" r="5" fill="{G5}"/>' + t(70, y + 276, f["lang"], 15, G5))
    o.append(t(180, y + 276, f"★ {f['stars']}  ·  {f['pushed']}", 15, G4))
    act = f["status"] == "ACTIVE"
    o.append((f'<circle cx="{24 + fw - 100}" cy="{y + 271}" r="3.5" fill="{P}" class="pulse"/>' if act else "")
             + t(24 + fw - 28, y + 276, f["status"], 14, P if act else G3, anchor="end", font=MONO, ls=1.5))

    # the rest fill the right half: 2 columns, rows share the 300px height
    k = len(rest)
    rows = (k + 1) // 2
    th = (300 - 16 * (rows - 1)) / rows if rows else 0
    for i, r in enumerate(rest):
        col, row = i % 2, i // 2
        span = k % 2 == 1 and i == k - 1  # odd one out spans both columns
        x = 508 + (0 if span else col * 242)
        tw = 468 if span else 226
        ty = y + row * (th + 16)
        a = r["status"] == "ACTIVE"
        o.append(tile(x, ty, tw, th))
        o.append(t(x + 22, ty + 40, r["name"], 21 if len(r["name"]) <= 15 else 18, P if a else G5, "bold"))
        o.append(t(x + tw - 22, ty + 39, f"0{i + 2}", 12, G2, anchor="end", font=MONO))
        nl = max(1, min(3, int((th - 110) // 20) + 1))  # keep clear of the language row
        for j, ln in enumerate(textwrap.wrap(r["desc"], 25 if not span else 54, max_lines=nl, placeholder="…")):
            o.append(t(x + 22, ty + 68 + j * 20, ln, 15, G4))
        if r["lang"]:
            o.append(f'<circle cx="{x + 26}" cy="{ty + th - 25}" r="4" fill="{G4}"/>' + t(x + 36, ty + th - 20, r["lang"], 14, G5))
        if a:
            o.append(R(x + tw - 94, ty + th - 37, 76, 24, "#222", 'rx="12"') + t(x + tw - 56, ty + th - 20.5, "ACTIVE", 11.5, P, "bold", "middle", MONO, ls=1))
        else:
            o.append(t(x + tw - 22, ty + th - 20.5, r["status"], 12, G3, anchor="end", font=MONO, ls=1))
    return "".join(o), 300


def main():
    user = fetch()["data"]["user"]
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = sorted_days(cal)
    now = datetime.now(timezone.utc)
    current, longest = streaks(days)
    counts = [d["contributionCount"] for d in days]
    peak_d = max(days, key=lambda d: d["contributionCount"])
    weekly = [sum(d["contributionCount"] for d in wk["contributionDays"]) for wk in cal["weeks"]]
    months = {}
    for d in days:
        dd = date.fromisoformat(d["date"])
        months[(dd.year, dd.month)] = months.get((dd.year, dd.month), 0) + d["contributionCount"]
    mlist = [(date(y, m, 1).strftime("%b"), c) for (y, m), c in sorted(months.items())]
    langs, other = top_languages(user.get("repositories"))

    o = [hero(now), headline(cal["totalContributions"], weekly, mlist),
         stat_row(cal["totalContributions"], cc["totalCommitContributions"], cc["totalPullRequestContributions"],
                  current, longest, (date.fromisoformat(peak_d["date"]), peak_d["contributionCount"]), counts[-30:]),
         heatmap(cal, days, sum(1 for c in counts if c))]
    y = 782
    rh = max(260, 80 + len(STACK) * 44)
    if langs:
        o.append(languages(y, rh, langs, other))
    o.append(stack(y, rh, 400 if langs else 24))
    y += rh + 16
    body, ph = projects(y, user.get("pinnedItems"), now)
    o.append(body)
    y += ph + 16 if ph else 0
    o.append(t(500, y + 26, f"auto-generated daily via GitHub Actions · last sync {now.day} {now:%b %Y}", 14, G3, anchor="middle", font=MONO))
    H = int(y + 56)

    defs = ('<linearGradient id="tf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#161616"/><stop offset="1" stop-color="#0e0e0e"/></linearGradient>'
            '<linearGradient id="edge" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3a3a"/><stop offset="0.35" stop-color="#1f1f1f"/><stop offset="1" stop-color="#181818"/></linearGradient>'
            '<linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.32"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            '<radialGradient id="glow"><stop offset="0" stop-color="#fff" stop-opacity="0.10"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="chipP" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#cfcfcd"/></linearGradient>'
            '<clipPath id="hero"><rect x="24" y="24" width="620" height="300" rx="24"/></clipPath>'
            '<clipPath id="big"><rect x="660" y="24" width="316" height="300" rx="24"/></clipPath>')
    css = ('.pulse{animation:p 2.4s ease-in-out infinite}@keyframes p{50%{opacity:.25}}'
           '.dr{stroke-dasharray:900;stroke-dashoffset:900;animation:dr 2.4s ease-out forwards}@keyframes dr{to{stroke-dashoffset:0}}'
           '.cur{animation:c 1.1s steps(1) infinite}@keyframes c{50%{opacity:0}}'
           '@media (prefers-reduced-motion:reduce){.pulse,.cur{animation:none}.dr{animation:none;stroke-dashoffset:0}}')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="{esc(USER)}: {esc(BIO)} Contribution stats, activity heatmap, languages, stack and pinned projects.">\n'
           f'<defs>{defs}</defs>\n<style>{css}</style>\n'
           f'<rect width="{W}" height="{H}" rx="28" fill="#060606"/>\n' + "\n".join(o) + "\n</svg>\n")
    os.makedirs("assets", exist_ok=True)
    with open("assets/profile.svg", "w", encoding="utf8", newline="\n") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
