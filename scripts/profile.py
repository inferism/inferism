#!/usr/bin/env python3
"""Builds assets/profile.svg: one terminal-style container with all profile sections.

Needs: gh CLI + GH_TOKEN, and USERNAME. Set PROFILE_FAKE=<json file> to test offline.
"""
import json
import math
import os
import random
import subprocess
from datetime import date, datetime, timezone

USER = os.environ.get("USERNAME", "inferism")
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
  }
}"""

FONT = 'ui-monospace, "SF Mono", Menlo, Consolas, "Courier New", monospace'
BG, PANEL, LINE = "#0b0b0c", "#111113", "#2a2a2d"
TEXT, DIM, BRIGHT = "#d4d4d8", "#85858b", "#ffffff"

STACK = [  # label, chips
    ("languages", ["TypeScript", "JavaScript", "Python", "HTML", "CSS"]),
    ("frameworks", ["Next.js", "React"]),
    ("backend", ["Firebase Auth", "Firestore", "Security Rules"]),
    ("deploy", ["Vercel"]),
    ("testing", ["Firebase Emulators", "tsx tests"]),
    ("automation", ["Python", "GitHub Actions", "GraphQL API", "SVG"]),
]

LEVEL = [  # top, left, right
    ("#1b1b1e", "#131315", "#0f0f11"),
    ("#3a3a3f", "#2a2a2e", "#212124"),
    ("#66666c", "#4a4a50", "#3a3a3f"),
    ("#a6a6ac", "#7a7a80", "#5e5e64"),
    ("#ffffff", "#c4c4ca", "#8e8e94"),
]


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


def heading(name, cmd, num):
    return (
        f'<text x="28" y="44" class="hi" font-size="30" font-weight="700"><tspan class="dim">~/</tspan>{name}</text>'
        f'<text x="972" y="44" text-anchor="end" class="dim" font-size="16">// {num}</text>'
        f'<text x="28" y="72" class="dim" font-size="15">$ {esc(cmd)}</text>'
    )


def corner(x, y, dx, dy):
    return f'<path d="M{x} {y + dy}V{y}H{x + dx}" fill="none" stroke="#ffffff" stroke-width="2"/>'


def sec_whoami():
    body = (
        f'<text x="28" y="30" class="dim" font-size="14" letter-spacing="2">SYS://{USER.upper()} // NODE:BSIT</text>'
        '<circle cx="652" cy="25" r="4.5" fill="#ffffff" class="blink"/>'
        '<text x="972" y="30" text-anchor="end" class="hi" font-size="14" letter-spacing="2">ONLINE - ALL SYSTEMS NOMINAL</text>'
        f'<line x1="1" y1="48" x2="{W - 1}" y2="48" stroke="{LINE}" stroke-width="1.5"/>'
        '<text x="28" y="82" class="dim" font-size="15">~/boot</text>'
        '<text x="972" y="82" text-anchor="end" class="dim" font-size="16">// 00</text>'
        '<text x="28" y="112" class="dim" font-size="17">$ whoami</text>'
        f'<text x="28" y="188" class="hi" font-size="72" font-weight="700" letter-spacing="5" filter="url(#glow)">{USER.upper()}</text>'
        '<text x="28" y="232" class="txt" font-size="19"><tspan class="hi">&gt;&gt;</tspan> 2nd-year BSIT student</text>'
        '<text x="28" y="264" class="txt" font-size="19"><tspan class="hi">&gt;&gt;</tspan> building web apps and games, learning front-end and back-end</text>'
        '<text x="28" y="296" class="txt" font-size="19"><tspan class="hi">&gt;&gt;</tspan> shipping personal projects I could actually use<tspan class="hi blink"> _</tspan></text>'
    )
    return body, 330


def sec_stats(cc):
    cal = cc["contributionCalendar"]
    current, longest = streaks(sorted_days(cal))
    cards = [
        ("CONTRIBUTIONS", f"{cal['totalContributions']:,}", "", "last 12 months"),
        ("COMMITS", f"{cc['totalCommitContributions']:,}", "", "last 12 months"),
        ("PULL REQUESTS", f"{cc['totalPullRequestContributions']:,}", "", "last 12 months"),
        ("CURRENT STREAK", current, "d", "days in a row"),
        ("LONGEST STREAK", longest, "d", "last 12 months"),
    ]
    out = [heading("stats", f"gh stats --user {USER}", "01")]
    top, h = 100, 132
    for i, (label, value, unit, sub) in enumerate(cards):
        x = 25 + i * 195
        out.append(
            f'<rect x="{x}" y="{top}" width="170" height="{h}" rx="6" fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>'
            + corner(x, top, 14, 14)
            + f'<path d="M{x + 170} {top + h - 14}V{top + h}H{x + 156}" fill="none" stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{x + 16}" y="{top + 34}" class="dim" font-size="12" letter-spacing="1.5">{label}</text>'
            f'<text x="{x + 16}" y="{top + 88}" class="hi" font-size="44" font-weight="700" filter="url(#ng)">{value}<tspan font-size="20" class="dim">{unit}</tspan></text>'
            f'<text x="{x + 16}" y="{top + 114}" class="dim" font-size="13">{sub}</text>'
        )
    now = datetime.now(timezone.utc)
    out.append(
        f'<text x="972" y="{top + h + 32}" text-anchor="end" class="dim" font-size="13">updated {now.day} {now.strftime("%b %Y")}</text>'
    )
    return "".join(out), top + h + 50


def space(h):
    """Starfield, nebula and a distant planet behind the skyline."""
    rnd = random.Random(7)
    out = [
        f'<rect x="1" y="0" width="{W - 2}" height="{h}" fill="#050507"/>',
        f'<ellipse cx="760" cy="{h - 190}" rx="420" ry="210" fill="url(#neb)" opacity="0.9"/>',
        f'<ellipse cx="170" cy="{h - 330}" rx="260" ry="150" fill="url(#neb)" opacity="0.5"/>',
    ]
    for i in range(150):
        x, y = rnd.uniform(14, W - 14), rnd.uniform(10, h - 10)
        if y < 90 and (x < 430 or x > 880):  # keep the heading readable
            continue
        r = rnd.choice([0.5, 0.6, 0.7, 0.9, 1.1])
        o = rnd.uniform(0.25, 0.75)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" fill-opacity="{o:.2f}"/>')
    for i in range(26):
        x, y = rnd.uniform(14, W - 14), rnd.uniform(10, h - 10)
        if y < 90 and (x < 430 or x > 880):
            continue
        r = rnd.uniform(1.2, 1.9)
        tw = ' class="tw" style="animation-delay:-%.1fs"' % rnd.uniform(0, 4) if i % 2 == 0 else ""
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#fff" fill-opacity="0.9"{tw}/>')
    for x, y in [(210, 130), (905, 305), (470, 520)]:
        out.append(
            f'<g class="tw" style="animation-delay:-{x % 3}s"><circle cx="{x}" cy="{y}" r="9" fill="#fff" fill-opacity="0.08"/>'
            f'<path d="M{x - 9} {y}H{x + 9}M{x} {y - 9}V{y + 9}" stroke="#fff" stroke-width="1" stroke-opacity="0.8"/>'
            f'<circle cx="{x}" cy="{y}" r="1.8" fill="#fff"/></g>'
        )
    out.append(
        '<g transform="translate(880 168) rotate(-18)">'
        '<ellipse rx="62" ry="12" fill="none" stroke="#6b6b72" stroke-width="2" stroke-opacity="0.5"/>'
        '<circle r="30" fill="url(#planet)"/>'
        '<path d="M-62 0A62 12 0 0 0 62 0" fill="none" stroke="#a1a1a6" stroke-width="2" stroke-opacity="0.7"/>'
        "</g>"
    )
    return "".join(out)


def sec_skyline(cal):
    days = sorted_days(cal)
    first = date.fromisoformat(days[0]["date"])
    first_sunday = first.toordinal() - ((first.weekday() + 1) % 7)
    peak = max((d["contributionCount"] for d in days), default=0) or 1
    dx, dy, ox, oy, m = 15.0, 6.2, 155.0, 195.0, 0.07
    h_sec = 620

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

    bld = []
    for _, gx, gy, level, h in cells:
        top, left, right = LEVEL[level]
        a0, a1, b0, b1 = gx + m, gx + 1 - m, gy + m, gy + 1 - m
        bld.append(
            f'<path d="M{p(a0, b1, 0)}L{p(a1, b1, 0)}L{p(a1, b1, h)}L{p(a0, b1, h)}Z" fill="{left}"/>'
            f'<path d="M{p(a1, b1, 0)}L{p(a1, b0, 0)}L{p(a1, b0, h)}L{p(a1, b1, h)}Z" fill="{right}"/>'
            f'<path d="M{p(a0, b0, h)}L{p(a1, b0, h)}L{p(a1, b1, h)}L{p(a0, b1, h)}Z" fill="{top}"/>'
        )
    total = sum(d["contributionCount"] for d in days)
    body = (
        space(h_sec)
        + heading("contribution-skyline", "render-skyline --last 365d  # one building per day", "02")
        + f'<g stroke="#050507" stroke-width="0.4" stroke-linejoin="round">' + "".join(bld) + "</g>"
        f'<text x="28" y="{h_sec - 24}" class="dim" font-size="15">{total:,} contributions · peak {peak}/day · one building per day</text>'
    )
    return body, h_sec


def sec_stack():
    out = [heading("stack", "cat stack.json", "03")]
    y0, pitch = 104, 60
    for i, (label, chips) in enumerate(STACK):
        y = y0 + i * pitch
        out.append(
            f'<text x="28" y="{y + 23}" class="dim" font-size="18">{label}</text>'
            f'<line x1="28" y1="{y + 46}" x2="972" y2="{y + 46}" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="2 5"/>'
        )
        x = 205.0
        for c in chips:
            w = len(c) * 9.7 + 30
            out.append(
                f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="36" rx="3" fill="{PANEL}" stroke="#a1a1a6" stroke-width="1.2"/>'
                f'<text x="{x + w / 2:.1f}" y="{y + 24}" text-anchor="middle" class="hi" font-size="16">{esc(c)}</text>'
            )
            x += w + 12
    return "".join(out), y0 + len(STACK) * pitch + 20


def sec_exit():
    body = (
        '<text x="28" y="48" class="dim" font-size="18">$ <tspan class="hi">exit</tspan></text>'
        '<text x="28" y="88" class="txt" font-size="18">logout</text>'
        '<text x="28" y="120" class="txt" font-size="18">[session closed] see you in the next commit<tspan class="hi blink"> _</tspan></text>'
        f'<text x="972" y="150" text-anchor="end" class="dim" font-size="14">Connection to {USER} closed.</text>'
    )
    return body, 172


def main():
    user = fetch()["data"]["user"]
    cc = user["contributionsCollection"]
    sections = [
        sec_whoami(),
        sec_stats(cc),
        sec_skyline(cc["contributionCalendar"]),
        sec_stack(),
        sec_exit(),
    ]

    parts, y = [], 0
    for i, (body, h) in enumerate(sections):
        parts.append(f'<g transform="translate(0 {y})">{body}</g>')
        y += h
        if i < len(sections) - 1:
            parts.append(f'<line x1="1" y1="{y}" x2="{W - 1}" y2="{y}" stroke="{LINE}" stroke-width="1.5"/>')
    total_h = y

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}" role="img" '
        f'aria-label="{esc(USER)} profile: whoami, stats, contribution skyline, stack">\n'
        "<defs>"
        '<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#ffffff" fill-opacity="0.05"/></pattern>'
        '<filter id="glow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="ng" x="-40%" y="-60%" width="180%" height="220%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="wide"/>'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="tight"/>'
        '<feMerge><feMergeNode in="wide"/><feMergeNode in="tight"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<radialGradient id="neb"><stop offset="0" stop-color="#9a9aa8" stop-opacity="0.22"/><stop offset="1" stop-color="#9a9aa8" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="planet" cx="0.3" cy="0.3" r="0.8"><stop offset="0" stop-color="#6c6c74"/><stop offset="1" stop-color="#0e0e10"/></radialGradient>'
        "</defs>\n"
        f"<style>text {{ font-family: {FONT}; }} .dim {{ fill: {DIM}; }} .txt {{ fill: {TEXT}; }} .hi {{ fill: {BRIGHT}; }} "
        ".blink { animation: blink 1.1s steps(1) infinite; } @keyframes blink { 50% { opacity: 0; } } "
        ".tw { animation: tw 4s ease-in-out infinite; } @keyframes tw { 50% { opacity: 0.25; } }</style>\n"
        f'<rect x="1" y="1" width="{W - 2}" height="{total_h - 2}" rx="14" fill="{BG}"/>\n'
        f'<rect x="1" y="1" width="{W - 2}" height="{total_h - 2}" rx="14" fill="url(#dots)"/>\n'
        + "\n".join(parts) + "\n"
        f'<rect x="1" y="1" width="{W - 2}" height="{total_h - 2}" rx="14" fill="none" stroke="{LINE}" stroke-width="2"/>\n'
        + corner(1, 1, 18, 18)
        + corner(W - 1, 1, -18, 18)
        + corner(1, total_h - 1, 18, -18)
        + corner(W - 1, total_h - 1, -18, -18)
        + "\n</svg>\n"
    )
    os.makedirs("assets", exist_ok=True)
    with open("assets/profile.svg", "w", encoding="utf8", newline="\n") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
