#!/usr/bin/env python3
"""Builds assets/profile.svg: one terminal-style container with all profile sections.

Needs: gh CLI + GH_TOKEN, and USERNAME. Set PROFILE_FAKE=<json file> to test offline.
"""
import json
import math
import os
import subprocess
from datetime import date, datetime, timezone

USER = os.environ.get("USERNAME", "inferism")
W = 1000

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


def languages(repos):
    sizes = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    total = sum(sizes.values())
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:6]
    return [(n, s / total * 100) for n, s in top] if total else []


def heading(name, cmd, num):
    return (
        f'<text x="28" y="40" class="hi" font-size="24" font-weight="700"><tspan class="dim">~/</tspan>{name}</text>'
        f'<text x="972" y="40" text-anchor="end" class="dim" font-size="12">// {num}</text>'
        f'<text x="28" y="62" class="dim" font-size="12">$ {esc(cmd)}</text>'
    )


def corner(x, y, dx, dy):
    return f'<path d="M{x} {y + dy}V{y}H{x + dx}" fill="none" stroke="#ffffff" stroke-width="2"/>'


def sec_whoami():
    h = 300
    body = (
        f'<text x="28" y="28" class="dim" font-size="11" letter-spacing="2.5">SYS://{USER.upper()} // NODE:BSIT</text>'
        '<circle cx="700" cy="24" r="4" fill="#ffffff" class="blink"/>'
        '<text x="972" y="28" text-anchor="end" class="hi" font-size="11" letter-spacing="2.5">ONLINE - ALL SYSTEMS NOMINAL</text>'
        f'<line x1="1" y1="44" x2="{W - 1}" y2="44" stroke="{LINE}" stroke-width="1.5"/>'
        '<text x="28" y="76" class="dim" font-size="12">~/boot</text>'
        '<text x="972" y="76" text-anchor="end" class="dim" font-size="12">// 00</text>'
        '<text x="28" y="102" class="dim" font-size="14">$ whoami</text>'
        f'<text x="28" y="176" class="hi" font-size="72" font-weight="700" letter-spacing="5" filter="url(#glow)">{USER.upper()}</text>'
        '<text x="28" y="218" class="txt" font-size="16"><tspan class="hi">&gt;&gt;</tspan> 2nd-year BSIT student</text>'
        '<text x="28" y="244" class="txt" font-size="16"><tspan class="hi">&gt;&gt;</tspan> building web apps and games, learning front-end and back-end</text>'
        '<text x="28" y="270" class="txt" font-size="16"><tspan class="hi">&gt;&gt;</tspan> shipping personal projects I could actually use<tspan class="hi blink"> _</tspan></text>'
    )
    return body, h


def sec_stats(cc, repos):
    cal = cc["contributionCalendar"]
    current, longest = streaks(sorted_days(cal))
    cards = [
        ("CONTRIBUTIONS", f"{cal['totalContributions']:,}", "", "last 12 months"),
        ("COMMITS", f"{cc['totalCommitContributions']:,}", "", "last 12 months"),
        ("PULL REQUESTS", f"{cc['totalPullRequestContributions']:,}", "", "last 12 months"),
        ("CURRENT STREAK", current, "d", "days in a row"),
        ("LONGEST STREAK", longest, "d", "within last 12 months"),
    ]
    out = [heading("stats", f"gh stats --user {USER}", "01")]
    top = 84
    for i, (label, value, unit, sub) in enumerate(cards):
        x = 25 + i * 195
        out.append(
            f'<rect x="{x}" y="{top}" width="170" height="116" rx="6" fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>'
            + corner(x, top, 14, 14)
            + f'<path d="M{x + 170} {top + 102}V{top + 116}H{x + 156}" fill="none" stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{x + 18}" y="{top + 32}" class="dim" font-size="10" letter-spacing="2">{label}</text>'
            f'<text x="{x + 18}" y="{top + 80}" class="hi" font-size="40" font-weight="700">{value}<tspan font-size="18" class="dim">{unit}</tspan></text>'
            f'<text x="{x + 18}" y="{top + 102}" class="dim" font-size="11">{sub}</text>'
        )

    py = top + 132  # languages panel
    out.append(
        f'<rect x="25" y="{py}" width="950" height="170" rx="6" fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>'
        + corner(25, py, 14, 14)
        + f'<path d="M975 {py + 156}V{py + 170}H961" fill="none" stroke="#ffffff" stroke-width="2"/>'
        f'<text x="45" y="{py + 30}" class="dim" font-size="10" letter-spacing="2">TOP LANGUAGES</text>'
    )
    langs = languages(repos)
    if langs:
        total = sum(p for _, p in langs)
        bar_y, x = py + 46, 45.0
        out.append(f'<clipPath id="barclip"><rect x="45" y="{bar_y}" width="910" height="14" rx="3"/></clipPath><g clip-path="url(#barclip)">')
        for i, (_, pct) in enumerate(langs):
            w = 910 * pct / total
            out.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w + 0.5:.1f}" height="14" fill="{SHADES[i]}"/>')
            x += w
        out.append("</g>")
        for i, (name, pct) in enumerate(langs):
            cx, cy = 45 + (i % 3) * 305, py + 100 + (i // 3) * 36
            out.append(
                f'<rect x="{cx}" y="{cy - 10}" width="12" height="12" rx="2" fill="{SHADES[i]}"/>'
                f'<text x="{cx + 22}" y="{cy}" class="txt" font-size="15">{esc(name)}</text>'
                f'<text x="{cx + 270}" y="{cy}" text-anchor="end" class="hi" font-size="15" font-weight="700">{pct:.0f}%</text>'
            )
    else:
        out.append(f'<text x="45" y="{py + 90}" class="dim" font-size="14">no language data yet</text>')
    now = datetime.now(timezone.utc)
    out.append(
        f'<text x="972" y="{py + 196}" text-anchor="end" class="dim" font-size="10">updated {now.day} {now.strftime("%b %Y")}</text>'
    )
    return "".join(out), py + 210


def sec_skyline(cal):
    days = sorted_days(cal)
    first = date.fromisoformat(days[0]["date"])
    first_sunday = first.toordinal() - ((first.weekday() + 1) % 7)
    peak = max((d["contributionCount"] for d in days), default=0) or 1
    dx, dy, ox, oy, m = 15.0, 6.2, 155.0, 175.0, 0.07

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
        heading("contribution-skyline", "render-skyline --last 365d  # one building per day", "02")
        + f'<g stroke="{BG}" stroke-width="0.4" stroke-linejoin="round">' + "".join(bld) + "</g>"
        f'<text x="28" y="562" class="dim" font-size="11">{total:,} contributions · peak {peak}/day · one building per day</text>'
    )
    return body, 586


def sec_stack():
    out = [heading("stack", "cat stack.json", "03")]
    y0 = 90
    for i, (label, chips) in enumerate(STACK):
        y = y0 + i * 50
        out.append(
            f'<text x="28" y="{y + 19}" class="dim" font-size="14">{label}</text>'
            f'<line x1="28" y1="{y + 38}" x2="972" y2="{y + 38}" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="2 5"/>'
        )
        x = 190.0
        for c in chips:
            w = len(c) * 7.9 + 28
            out.append(
                f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="28" rx="3" fill="{PANEL}" stroke="#a1a1a6" stroke-width="1.2"/>'
                f'<text x="{x + w / 2:.1f}" y="{y + 19}" text-anchor="middle" class="hi" font-size="13">{esc(c)}</text>'
            )
            x += w + 10
    return "".join(out), y0 + len(STACK) * 50 + 24


def sec_exit():
    body = (
        '<text x="28" y="44" class="dim" font-size="14">$ <tspan class="hi">exit</tspan></text>'
        '<text x="28" y="78" class="txt" font-size="14">logout</text>'
        '<text x="28" y="104" class="txt" font-size="14">[session closed] see you in the next commit<tspan class="hi blink"> _</tspan></text>'
        f'<text x="972" y="132" text-anchor="end" class="dim" font-size="11">Connection to {USER} closed.</text>'
    )
    return body, 150


def main():
    user = fetch()["data"]["user"]
    cc = user["contributionsCollection"]
    sections = [
        sec_whoami(),
        sec_stats(cc, user["repositories"]["nodes"]),
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
        '<defs>'
        '<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#ffffff" fill-opacity="0.05"/></pattern>'
        '<filter id="glow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>\n'
        f'<style>text {{ font-family: {FONT}; }} .dim {{ fill: {DIM}; }} .txt {{ fill: {TEXT}; }} .hi {{ fill: {BRIGHT}; }} '
        '.blink { animation: blink 1.1s steps(1) infinite; } @keyframes blink { 50% { opacity: 0; } }</style>\n'
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
