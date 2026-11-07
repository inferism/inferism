#!/usr/bin/env python3
"""Builds assets/profile.svg: one terminal-style container with all profile sections.

Needs: gh CLI + GH_TOKEN, and USERNAME. Set PROFILE_FAKE=<json file> to test offline.
"""
import json
import math
import os
import random
import subprocess
from datetime import datetime, timezone

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


def stars(h):
    """Plain space backdrop with a light starfield."""
    rnd = random.Random(7)
    out = [f'<rect x="1" y="0" width="{W - 2}" height="{h}" fill="#050507"/>']
    for i in range(170):
        x, y = rnd.uniform(14, W - 14), rnd.uniform(10, h - 10)
        if y < 90 and (x < 430 or x > 880):  # keep the heading readable
            continue
        r = rnd.choice([0.5, 0.6, 0.7, 0.9, 1.1])
        tw = f' class="tw" style="animation-delay:-{rnd.uniform(0, 4):.1f}s"' if i % 9 == 0 else ""
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" fill-opacity="{rnd.uniform(0.2, 0.65):.2f}"{tw}/>')
    return "".join(out)


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def sec_galaxy(cal):
    days = sorted_days(cal)
    n = len(days)
    peak = max((d["contributionCount"] for d in days), default=0) or 1
    rnd = random.Random(8)
    h_gal, cx, cy = 480, W / 2, 278
    out = [stars(h_gal), heading("contribution-galaxy", "render-galaxy --last 365d  # one star per day", "02")]
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="105" ry="62" fill="url(#gcore)"/>')
    for _ in range(300):  # faint dust around the arm
        a, d = rnd.uniform(0, math.tau), math.sqrt(rnd.random()) * 175
        out.append(f'<circle cx="{cx + math.cos(a) * d * 1.95:.1f}" cy="{cy + math.sin(a) * d * 1.12:.1f}" r="0.6" fill="#fff" fill-opacity="{rnd.uniform(0.08, 0.3):.2f}"/>')
    for i, d in enumerate(days):
        t = i / max(1, n - 1)
        ang, rad = t * math.tau * 3 + 0.6, 14 + t * 150 + (rnd.random() - 0.5) * 7
        c = d["contributionCount"]
        x, y = cx + math.cos(ang) * rad * 1.95, cy + math.sin(ang) * rad * 1.12
        if c:
            lv = min(4, max(1, math.ceil(4 * c / peak)))
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.3 + lv * 0.85:.1f}" fill="#fff" fill-opacity="{0.45 + lv * 0.13:.2f}"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="0.8" fill="#fff" fill-opacity="0.16"/>')
    total = sum(d["contributionCount"] for d in days)
    out.append(f'<text x="28" y="{h_gal - 22}" class="dim" font-size="15">{total:,} contributions · peak {peak}/day · one star per day</text>')

    # monitor: the same year, month by month
    by_month = {}
    for d in days:
        k = d["date"][:7]
        by_month[k] = by_month.get(k, 0) + d["contributionCount"]
    keys = sorted(by_month)[-12:]
    tot = [by_month[k] for k in keys]
    mx = max(tot) or 1
    y0 = h_gal
    out.append(f'<line x1="28" y1="{y0}" x2="{W - 28}" y2="{y0}" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="2 5"/>')
    out.append(f'<text x="28" y="{y0 + 44}" class="dim" font-size="15">$ htop --contributions</text>')
    ticks, pitch, bx = 40, 14, 124
    for r, (k, v) in enumerate(zip(keys, tot)):
        y = y0 + 96 + r * 32
        filled = round(v / mx * ticks)
        out.append(
            f'<text x="28" y="{y}" class="txt" font-size="18">{MONTHS[int(k[5:7]) - 1]}</text>'
            f'<text x="{bx - 16}" y="{y}" class="dim" font-size="20">[</text>'
            + "".join(
                f'<rect x="{bx + i * pitch}" y="{y - 14}" width="3" height="18" fill="{BRIGHT if i < filled else "#1b1b1e"}"/>'
                for i in range(ticks)
            )
            + f'<text x="{bx + ticks * pitch}" y="{y}" class="dim" font-size="20">]</text>'
            f'<text x="{W - 190}" y="{y}" text-anchor="end" class="hi" font-size="18" font-weight="700">{round(v / mx * 100)}%</text>'
            f'<text x="{W - 40}" y="{y}" text-anchor="end" class="txt" font-size="18">{v}</text>'
        )
    ye = y0 + 96 + len(keys) * 32 + 14
    active = sum(1 for d in days if d["contributionCount"])
    out.append(f'<text x="28" y="{ye + 20}" class="dim" font-size="16">Tasks: {active} active days, {n} total</text>')
    out.append(f'<text x="28" y="{ye + 46}" class="dim" font-size="16">Uptime: {n} days</text>')
    return "".join(out), ye + 76


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
        sec_galaxy(cc["contributionCalendar"]),
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
        f'aria-label="{esc(USER)} profile: whoami, stats, contribution galaxy, stack">\n'
        "<defs>"
        '<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#ffffff" fill-opacity="0.05"/></pattern>'
        '<filter id="glow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="ng" x="-40%" y="-60%" width="180%" height="220%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="wide"/>'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="tight"/>'
        '<feMerge><feMergeNode in="wide"/><feMergeNode in="tight"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<radialGradient id="gcore"><stop offset="0" stop-color="#fff" stop-opacity="0.4"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
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
