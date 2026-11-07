#!/usr/bin/env python3
"""Builds the profile SVGs in assets/: whoami banner, stats, skyline, stack, exit.

Needs: gh CLI + GH_TOKEN, and USERNAME. Set PROFILE_FAKE=<json file> to test offline.
"""
import json
import math
import os
import subprocess
from datetime import date, datetime, timezone

USER = os.environ.get("USERNAME", "inferism")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""

FONT = 'ui-monospace, "SF Mono", Menlo, Consolas, "Courier New", monospace'
BG, PANEL, LINE = "#0b0b0c", "#111113", "#2a2a2d"
TEXT, DIM, BRIGHT = "#d4d4d8", "#85858b", "#ffffff"
SHADES = ["#ffffff", "#d4d4d8", "#a1a1a6", "#7a7a80", "#55555a", "#3a3a3e"]

STYLE = f"""<style>
    text {{ font-family: {FONT}; }}
    .dim {{ fill: {DIM}; }}
    .txt {{ fill: {TEXT}; }}
    .hi  {{ fill: {BRIGHT}; }}
    .blink {{ animation: blink 1.1s steps(1) infinite; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
  </style>"""

DOTS = """<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#ffffff" fill-opacity="0.055"/>
    </pattern>"""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def languages(repos):
    sizes = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    total = sum(sizes.values())
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:6]
    return [(n, s / total * 100) for n, s in top] if total else []


def fill(template, **kw):
    for k, v in kw.items():
        template = template.replace(f"@{k}@", str(v))
    return template


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8", newline="\n") as f:
        f.write(text)


COMMON = dict(STYLE=STYLE, DOTS=DOTS, BG=BG, PANEL=PANEL, LINE=LINE)

BANNER = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="290" viewBox="0 0 1000 290" role="img" aria-label="@USER@, 2nd-year BSIT student">
  <defs>
    @DOTS@
    <filter id="glow" x="-20%" y="-40%" width="140%" height="180%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  @STYLE@
  <rect x="1" y="1" width="998" height="288" rx="14" fill="@BG@" stroke="@LINE@" stroke-width="2"/>
  <rect x="1" y="1" width="998" height="288" rx="14" fill="url(#dots)"/>
  <line x1="1" y1="44" x2="999" y2="44" stroke="@LINE@" stroke-width="2"/>
  <text x="28" y="28" class="dim" font-size="11" letter-spacing="2.5">SYS://@UPPER@ // NODE:BSIT</text>
  <circle cx="700" cy="24" r="4" fill="#ffffff" class="blink"/>
  <text x="972" y="28" text-anchor="end" class="hi" font-size="11" letter-spacing="2.5">ONLINE - ALL SYSTEMS NOMINAL</text>

  <text x="28" y="84" class="dim" font-size="14">$ whoami</text>
  <text x="28" y="156" class="hi" font-size="72" font-weight="700" letter-spacing="5" filter="url(#glow)">@UPPER@</text>
  <text x="28" y="196" class="txt" font-size="16"><tspan class="hi">&gt;&gt;</tspan> 2nd-year BSIT student</text>
  <text x="28" y="222" class="txt" font-size="16"><tspan class="hi">&gt;&gt;</tspan> building web apps and games, learning front-end and back-end</text>
  <text x="28" y="248" class="txt" font-size="16"><tspan class="hi">&gt;&gt;</tspan> shipping personal projects I could actually use<tspan class="hi blink"> _</tspan></text>
</svg>
"""

HEADING = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="58" viewBox="0 0 1000 58" role="img" aria-label="@NAME@">
  @STYLE@
  <text x="6" y="14" class="dim" font-size="11">$ @CMD@</text>
  <text x="6" y="42" class="hi" font-size="26" font-weight="700"><tspan class="dim">~/</tspan>@NAME@</text>
  <text x="994" y="42" text-anchor="end" class="dim" font-size="12">// @NUM@</text>
  <line x1="6" y1="53" x2="994" y2="53" stroke="@LINE@" stroke-width="2"/>
</svg>
"""

CARD = """  <g>
    <rect x="@X@" y="12" width="170" height="116" rx="6" fill="@PANEL@" stroke="@LINE@" stroke-width="1.5"/>
    <path d="M@X@ 26V12H@X2@" fill="none" stroke="#ffffff" stroke-width="2"/>
    <path d="M@XR@ 114V128H@XR2@" fill="none" stroke="#ffffff" stroke-width="2"/>
    <text x="@XT@" y="44" class="dim" font-size="10" letter-spacing="2">@LABEL@</text>
    <text x="@XT@" y="92" class="hi" font-size="40" font-weight="700">@VALUE@<tspan font-size="18" class="dim">@UNIT@</tspan></text>
    <text x="@XT@" y="114" class="dim" font-size="11">@SUB@</text>
  </g>
"""

STATS = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="340" viewBox="0 0 1000 340" role="img" aria-label="@ARIA@">
  @STYLE@
@CARDS@  <rect x="25" y="144" width="950" height="170" rx="6" fill="@PANEL@" stroke="@LINE@" stroke-width="1.5"/>
  <path d="M25 158V144H39" fill="none" stroke="#ffffff" stroke-width="2"/>
  <path d="M975 300V314H961" fill="none" stroke="#ffffff" stroke-width="2"/>
  <text x="45" y="174" class="dim" font-size="10" letter-spacing="2">TOP LANGUAGES</text>
@LANGS@  <text x="975" y="332" text-anchor="end" class="dim" font-size="10">@UPDATED@</text>
</svg>
"""


def build_stats(cc, repos):
    cal = cc["contributionCalendar"]
    days = sorted(
        (d for w in cal["weeks"] for d in w["contributionDays"]),
        key=lambda d: d["date"],
    )
    current, longest = streaks(days)
    cards = [
        ("CONTRIBUTIONS", f"{cal['totalContributions']:,}", "", "last 12 months"),
        ("COMMITS", f"{cc['totalCommitContributions']:,}", "", "last 12 months"),
        ("PULL REQUESTS", f"{cc['totalPullRequestContributions']:,}", "", "last 12 months"),
        ("CURRENT STREAK", current, "d", "days in a row"),
        ("LONGEST STREAK", longest, "d", "within last 12 months"),
    ]
    parts = []
    for i, (label, value, unit, sub) in enumerate(cards):
        x = 25 + i * 195
        parts.append(fill(
            CARD, X=x, X2=x + 14, XR=x + 170, XR2=x + 156, XT=x + 18,
            LABEL=label, VALUE=value, UNIT=unit, SUB=sub, **COMMON,
        ))

    langs = languages(repos)
    lp = []
    if langs:
        bar_x, bar_w, x = 45, 910, 45.0
        total = sum(p for _, p in langs)
        lp.append('  <clipPath id="barclip"><rect x="45" y="190" width="910" height="14" rx="3"/></clipPath>\n  <g clip-path="url(#barclip)">\n')
        for i, (_, pct) in enumerate(langs):
            w = bar_w * pct / total
            lp.append(f'    <rect x="{x:.1f}" y="190" width="{w + 0.5:.1f}" height="14" fill="{SHADES[i]}"/>\n')
            x += w
        lp.append("  </g>\n")
        for i, (name, pct) in enumerate(langs):
            cx = 45 + (i % 3) * 305
            cy = 244 + (i // 3) * 36
            lp.append(
                f'  <rect x="{cx}" y="{cy - 10}" width="12" height="12" rx="2" fill="{SHADES[i]}"/>\n'
                f'  <text x="{cx + 22}" y="{cy}" class="txt" font-size="15">{esc(name)}</text>\n'
                f'  <text x="{cx + 270}" y="{cy}" text-anchor="end" class="hi" font-size="15" font-weight="700">{pct:.0f}%</text>\n'
            )
    else:
        lp.append('  <text x="45" y="230" class="dim" font-size="14">no language data yet</text>\n')

    now = datetime.now(timezone.utc)
    updated = f"updated {now.day} {now.strftime('%b %Y')}"
    aria = ", ".join(f"{c[0].lower()} {c[1]}{c[2]}" for c in cards)
    return fill(STATS, CARDS="".join(parts), LANGS="".join(lp), ARIA=esc(aria), UPDATED=updated, **COMMON)


LEVEL = [  # top, left, right
    ("#1b1b1e", "#131315", "#0f0f11"),
    ("#3a3a3f", "#2a2a2e", "#212124"),
    ("#66666c", "#4a4a50", "#3a3a3f"),
    ("#a6a6ac", "#7a7a80", "#5e5e64"),
    ("#ffffff", "#c4c4ca", "#8e8e94"),
]


def build_skyline(cal):
    days = sorted(
        (d for w in cal["weeks"] for d in w["contributionDays"]),
        key=lambda d: d["date"],
    )
    first = date.fromisoformat(days[0]["date"])
    first_sunday = first.toordinal() - ((first.weekday() + 1) % 7)
    peak = max((d["contributionCount"] for d in days), default=0) or 1
    dx, dy, ox, oy, m = 15.0, 6.2, 155.0, 130.0, 0.07

    def p(a, b, z):
        return f"{ox + (a - b) * dx:.1f},{oy + (a + b) * dy - z:.1f}"

    cells = []
    for d in days:
        o = date.fromisoformat(d["date"]).toordinal() - first_sunday
        gx, gy = o // 7, o % 7
        n = d["contributionCount"]
        level = 0 if n == 0 else min(4, max(1, math.ceil(4 * n / peak)))
        h = 3 if n == 0 else 10 + 110 * math.sqrt(n / peak)
        cells.append((gx + gy, gx, gy, level, h))
    cells.sort()

    out = []
    for _, gx, gy, level, h in cells:
        top, left, right = LEVEL[level]
        a0, a1, b0, b1 = gx + m, gx + 1 - m, gy + m, gy + 1 - m
        out.append(
            f'<path d="M{p(a0, b1, 0)}L{p(a1, b1, 0)}L{p(a1, b1, h)}L{p(a0, b1, h)}Z" fill="{left}"/>'
            f'<path d="M{p(a1, b1, 0)}L{p(a1, b0, 0)}L{p(a1, b0, h)}L{p(a1, b1, h)}Z" fill="{right}"/>'
            f'<path d="M{p(a0, b0, h)}L{p(a1, b0, h)}L{p(a1, b1, h)}L{p(a0, b1, h)}Z" fill="{top}"/>'
        )

    total = sum(d["contributionCount"] for d in days)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="540" viewBox="0 0 1000 540" role="img" '
        f'aria-label="3D skyline of {total} contributions over the last year, peak {peak} in a day">\n'
        f"  <defs>\n    {DOTS}\n  </defs>\n  {STYLE}\n"
        f'  <rect x="1" y="1" width="998" height="538" rx="14" fill="{BG}" stroke="{LINE}" stroke-width="2"/>\n'
        f'  <rect x="1" y="1" width="998" height="538" rx="14" fill="url(#dots)"/>\n'
        f'  <g stroke="{BG}" stroke-width="0.4" stroke-linejoin="round">\n    '
        + "\n    ".join(out)
        + "\n  </g>\n"
        f'  <text x="28" y="516" class="dim" font-size="11">{total:,} contributions · peak {peak}/day · one building per day</text>\n'
        "</svg>\n"
    )
    return svg


STACK_CARD = """  <g>
    <rect x="@X@" y="@Y@" width="@W@" height="92" rx="6" fill="@PANEL@" stroke="@LINE@" stroke-width="1.5"/>
    <path d="M@X@ @Y1@V@Y@H@X2@" fill="none" stroke="#ffffff" stroke-width="2"/>
    <text x="@XT@" y="@YL@" class="dim" font-size="10" letter-spacing="2">@LABEL@</text>
    <text x="@XT@" y="@YV@" class="hi" font-size="18" font-weight="700">@VALUE@</text>
    <text x="@XT@" y="@YS@" class="dim" font-size="12">@SUB@</text>
  </g>
"""

STACK_ITEMS = [
    # x, y, w, label, value, sub
    (25, 12, 950, "FEATURED PROJECT", "Iskolance",
     "a community for QCU students to share skills and services at student-friendly prices"),
    (25, 116, 470, "FRONT-END", "Next.js 15 · React 19 · TypeScript", "app router, typed components"),
    (505, 116, 470, "BACKEND", "Firebase · Auth · Firestore · Storage", "Cloud Functions, security rules"),
    (25, 220, 470, "DESIGN", "Custom design tokens · HTML & CSS", "screen mockups before the build"),
    (505, 220, 470, "TESTING", "Firebase Emulators · tsx tests", "rules and payment flows checked locally"),
    (25, 324, 950, "AUTOMATION", "Python · GitHub Actions · GraphQL API · SVG",
     "this profile: generated daily, no outside services"),
]


def build_stack():
    parts = []
    for x, y, w, label, value, sub in STACK_ITEMS:
        parts.append(fill(
            STACK_CARD, X=x, Y=y, W=w, Y1=y + 14, X2=x + 14, XT=x + 18,
            YL=y + 30, YV=y + 58, YS=y + 78,
            LABEL=label, VALUE=esc(value), SUB=esc(sub), **COMMON,
        ))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430" role="img" '
        'aria-label="Tech stack: Next.js, React, TypeScript, Firebase, Python, GitHub Actions">\n'
        f"  {STYLE}\n" + "".join(parts) + "</svg>\n"
    )


EXIT = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="150" viewBox="0 0 1000 150" role="img" aria-label="exit: session closed">
  <defs>
    @DOTS@
  </defs>
  @STYLE@
  <rect x="1" y="1" width="998" height="148" rx="14" fill="@BG@" stroke="@LINE@" stroke-width="2"/>
  <rect x="1" y="1" width="998" height="148" rx="14" fill="url(#dots)"/>
  <text x="28" y="44" class="dim" font-size="14">$ <tspan class="hi">exit</tspan></text>
  <text x="28" y="78" class="txt" font-size="14">logout</text>
  <text x="28" y="102" class="txt" font-size="14">[session closed] see you in the next commit<tspan class="hi blink"> _</tspan></text>
  <text x="972" y="126" text-anchor="end" class="dim" font-size="11">Connection to @USER@ closed.</text>
</svg>
"""


def main():
    user = fetch()["data"]["user"]
    cc = user["contributionsCollection"]

    write("assets/banner.svg", fill(BANNER, USER=USER, UPPER=USER.upper(), **COMMON))
    write("assets/stats.svg", build_stats(cc, user["repositories"]["nodes"]))
    write("assets/skyline.svg", build_skyline(cc["contributionCalendar"]))
    write("assets/stack.svg", build_stack())
    write("assets/exit.svg", fill(EXIT, USER=USER, **COMMON))
    for slug, name, cmd, num in [
        ("stats", "stats", f"gh stats --user {USER}", "01"),
        ("skyline", "contribution-skyline", "render-skyline --last 365d  # one building per day", "02"),
        ("stack", "stack", "cat stack.json", "03"),
    ]:
        write(f"assets/h-{slug}.svg", fill(HEADING, NAME=name, CMD=esc(cmd), NUM=num, **COMMON))


if __name__ == "__main__":
    main()
