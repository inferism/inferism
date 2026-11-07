#!/usr/bin/env python3
"""Builds assets/profile.svg: one cyberpunk-HUD container with all profile sections.

Needs: gh CLI + GH_TOKEN, and USERNAME. Set PROFILE_FAKE=<json file> to test offline.
"""
import json
import math
import os
import base64
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
# palette sampled from the pfp (black / white halftone greys)
BG, PANEL, LINE, EDGE = "#060606", "#0e0e0f", "#2b2b2d", "#5c5c5e"
TEXT, DIM, BRIGHT = "#c1c1c3", "#767678", "#ffffff"
PFP = "assets/pfp.jpg"

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


def cut(x, y, w, h, c, fill, stroke, sw=1.5, tl=False, tr=True, br=False, bl=True):
    """Polygon with chamfered corners (the HUD panel shape)."""
    pts = []
    pts += [(x, y + c), (x + c, y)] if tl else [(x, y)]
    pts += [(x + w - c, y), (x + w, y + c)] if tr else [(x + w, y)]
    pts += [(x + w, y + h - c), (x + w - c, y + h)] if br else [(x + w, y + h)]
    pts += [(x + c, y + h), (x, y + h - c)] if bl else [(x, y + h)]
    d = " ".join(f"{px:g},{py:g}" for px, py in pts)
    return f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="miter"/>'


def corner(x, y, dx, dy, color=BRIGHT):
    return f'<path d="M{x} {y + dy}V{y}H{x + dx}" fill="none" stroke="{color}" stroke-width="2"/>'


def heading(name, cmd, num):
    return (
        '<rect x="28" y="20" width="12" height="30" fill="url(#hz)"/>'
        f'<text x="54" y="44" class="hi" font-size="28" font-weight="700" letter-spacing="4">{esc(name.upper())}</text>'
        f'<text x="972" y="44" text-anchor="end" class="dim" font-size="16" letter-spacing="2">// {num}</text>'
        f'<text x="28" y="72" class="dim" font-size="15">&gt; {esc(cmd)}</text>'
    )


def portrait(x, y, s):
    """Operator portrait in a chamfered HUD frame (skipped if assets/pfp.jpg is missing)."""
    if not os.path.exists(PFP):
        return ""
    with open(PFP, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    c = 24
    return (
        f'<image xlink:href="data:image/jpeg;base64,{b64}" x="{x}" y="{y}" width="{s}" height="{s}" '
        'preserveAspectRatio="xMidYMid slice" clip-path="url(#pf)"/>'
        f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="url(#scan)" clip-path="url(#pf)"/>'
        + cut(x, y, s, s, c, "none", EDGE)
        + corner(x - 6, y - 6, 22, 22)
        + corner(x + s + 6, y + s + 6, -22, -22)
        + f'<text x="{x}" y="{y + s + 26}" class="dim" font-size="13" letter-spacing="2">OPERATOR // {USER.upper()}</text>'
        + f'<text x="{x}" y="{y + s + 46}" class="dim" font-size="13" letter-spacing="2">STATUS <tspan class="hi">ACTIVE</tspan><tspan class="hi blink"> _</tspan></text>'
    )


def sec_whoami():
    t = USER.upper()
    tx, ty = 270, 150
    title = f'font-size="72" font-weight="700" letter-spacing="5"'
    body = (
        '<rect x="28" y="16" width="84" height="18" fill="url(#hz)"/>'
        f'<text x="128" y="31" class="dim" font-size="14" letter-spacing="2">SYS://{t} // NODE:BSIT</text>'
        '<rect x="648" y="19" width="10" height="10" fill="#ffffff" class="blink"/>'
        '<text x="972" y="31" text-anchor="end" class="hi" font-size="14" letter-spacing="2">ONLINE - ALL SYSTEMS NOMINAL</text>'
        f'<line x1="1" y1="48" x2="{W - 1}" y2="48" stroke="{LINE}" stroke-width="1.5"/>'
        + portrait(32, 82, 200)
        + f'<text x="{tx + 4}" y="{ty + 2}" {title} fill="{EDGE}" opacity="0.8">{t}</text>'
        f'<text x="{tx}" y="{ty}" class="hi" {title} filter="url(#glow)">{t}</text>'
        f'<g clip-path="url(#slice)"><text class="gl" x="{tx}" y="{ty}" {title} fill="{TEXT}">{t}</text></g>'
        f'<g fill="none" stroke="{EDGE}" stroke-width="1.2"><circle cx="905" cy="128" r="46"/>'
        f'<circle cx="905" cy="128" r="32" stroke-dasharray="3 5"/><line x1="845" y1="128" x2="870" y2="128"/>'
        '<line x1="940" y1="128" x2="965" y2="128"/><line x1="905" y1="68" x2="905" y2="84"/><line x1="905" y1="172" x2="905" y2="188"/></g>'
        '<circle cx="905" cy="128" r="5" fill="#ffffff" class="blink"/>'
        f'<line x1="{tx}" y1="172" x2="{W - 28}" y2="172" stroke="{LINE}" stroke-width="1.5"/>'
        f'<text x="{tx}" y="206" class="txt" font-size="19"><tspan class="hi">&gt;&gt;</tspan> 2nd-year BSIT student</text>'
        f'<text x="{tx}" y="238" class="txt" font-size="19"><tspan class="hi">&gt;&gt;</tspan> building web apps and games, learning front-end and back-end</text>'
        f'<text x="{tx}" y="270" class="txt" font-size="19"><tspan class="hi">&gt;&gt;</tspan> shipping personal projects I could actually use<tspan class="hi blink"> _</tspan></text>'
    )
    return body, 352


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
        ruler = "".join(
            f'<line x1="{x + 16 + k * 10}" y1="{top + h - 9}" x2="{x + 16 + k * 10}" y2="{top + h - (4 if k % 3 == 0 else 6)}" stroke="{EDGE}" stroke-width="1"/>'
            for k in range(15)
        )
        out.append(
            cut(x, top, 170, h, 16, PANEL, EDGE)
            + f'<rect x="{x}" y="{top}" width="170" height="{h}" fill="url(#dots)"/>'
            + f'<rect x="{x}" y="{top + 12}" width="4" height="18" fill="#ffffff"/>'
            + f'<text x="{x + 16}" y="{top + 28}" class="dim" font-size="12" letter-spacing="1.5">{label}</text>'
            f'<text x="{x + 16}" y="{top + 82}" class="hi" font-size="44" font-weight="700" filter="url(#ng)">{value}<tspan font-size="20" class="dim">{unit}</tspan></text>'
            f'<text x="{x + 16}" y="{top + 106}" class="dim" font-size="13">{sub}</text>'
            + ruler
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
    out = [stars(h_gal), heading("contribution-radar", "scan --last 365d  # one blip per day", "02")]
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="105" ry="62" fill="url(#gcore)"/>')
    for r in (40, 85, 130, 168):  # radar rings + crosshair
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r * 1.95:.1f}" ry="{r * 1.12:.1f}" fill="none" stroke="{EDGE}" stroke-width="1" stroke-opacity="0.55" stroke-dasharray="3 6"/>')
    out.append(f'<line x1="28" y1="{cy}" x2="{W - 28}" y2="{cy}" stroke="{EDGE}" stroke-width="1" stroke-opacity="0.5"/>')
    out.append(f'<line x1="{cx}" y1="96" x2="{cx}" y2="{h_gal - 40}" stroke="{EDGE}" stroke-width="1" stroke-opacity="0.5"/>')
    for k in range(-12, 13):
        tl = 7 if k % 4 == 0 else 3
        out.append(f'<line x1="{cx + k * 40}" y1="{cy - tl}" x2="{cx + k * 40}" y2="{cy + tl}" stroke="{EDGE}" stroke-width="1"/>')
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
            sz = 2.6 + lv * 1.7
            out.append(f'<rect x="{x - sz / 2:.1f}" y="{y - sz / 2:.1f}" width="{sz:.1f}" height="{sz:.1f}" fill="#fff" fill-opacity="{0.5 + lv * 0.12:.2f}"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="0.8" fill="#fff" fill-opacity="0.16"/>')
    total = sum(d["contributionCount"] for d in days)
    out.append(f'<text x="28" y="{h_gal - 22}" class="dim" font-size="15">{total:,} contributions · peak {peak}/day · one blip per day · core = 365d ago, rim = today</text>')

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
    out.append(f'<text x="28" y="{y0 + 44}" class="dim" font-size="15">&gt; htop --contributions  # monthly load</text>')
    ticks, pitch, bx = 40, 14, 124
    for r, (k, v) in enumerate(zip(keys, tot)):
        y = y0 + 96 + r * 32
        filled = round(v / mx * ticks)
        out.append(
            f'<text x="28" y="{y}" class="txt" font-size="18">{MONTHS[int(k[5:7]) - 1]}</text>'
            f'<path d="M{bx - 6} {y - 16}H{bx - 14}V{y + 6}H{bx - 6}" fill="none" stroke="{DIM}" stroke-width="1.5"/>'
            + "".join(
                f'<rect x="{bx + i * pitch}" y="{y - 14}" width="3" height="18" fill="{BRIGHT if i < filled else "#1b1b1e"}"/>'
                for i in range(ticks)
            )
            + f'<path d="M{bx + ticks * pitch - 3} {y - 16}H{bx + ticks * pitch + 5}V{y + 6}H{bx + ticks * pitch - 3}" fill="none" stroke="{DIM}" stroke-width="1.5"/>'
            f'<text x="{W - 190}" y="{y}" text-anchor="end" class="hi" font-size="18" font-weight="700">{round(v / mx * 100)}%</text>'
            f'<text x="{W - 40}" y="{y}" text-anchor="end" class="txt" font-size="18">{v}</text>'
        )
    ye = y0 + 96 + len(keys) * 32 + 14
    active = sum(1 for d in days if d["contributionCount"])
    out.append(f'<text x="28" y="{ye + 20}" class="dim" font-size="16">TASKS: {active} active days, {n} total</text>')
    out.append(f'<text x="28" y="{ye + 46}" class="dim" font-size="16">UPTIME: {n} days</text>')
    return "".join(out), ye + 76


def sec_stack():
    out = [heading("stack", "cat stack.json", "03")]
    y0, pitch = 104, 60
    for i, (label, chips) in enumerate(STACK):
        y = y0 + i * pitch
        out.append(
            f'<text x="28" y="{y + 23}" class="dim" font-size="18" letter-spacing="2">{label.upper()}</text>'
            f'<line x1="28" y1="{y + 46}" x2="972" y2="{y + 46}" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="2 5"/>'
        )
        x = 205.0
        for c in chips:
            w = len(c) * 9.7 + 30
            out.append(
                cut(x, y, w, 36, 9, PANEL, EDGE, 1.2, tr=True, bl=False)
                + f'<rect x="{x:.1f}" y="{y}" width="3" height="36" fill="#ffffff"/>'
                f'<text x="{x + w / 2:.1f}" y="{y + 24}" text-anchor="middle" class="hi" font-size="16">{esc(c)}</text>'
            )
            x += w + 12
    return "".join(out), y0 + len(STACK) * pitch + 20


def sec_exit():
    body = (
        '<rect x="28" y="30" width="84" height="18" fill="url(#hz)"/>'
        '<text x="128" y="45" class="dim" font-size="14" letter-spacing="2">LINK // TERMINATING</text>'
        '<text x="28" y="88" class="txt" font-size="18"><tspan class="hi">&gt;</tspan> logout</text>'
        '<text x="28" y="120" class="txt" font-size="18"><tspan class="hi">&gt;</tspan> [session closed] see you in the next commit<tspan class="hi blink"> _</tspan></text>'
        f'<text x="972" y="150" text-anchor="end" class="dim" font-size="14" letter-spacing="1">CONNECTION TO {USER.upper()} CLOSED.</text>'
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
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}" role="img" '
        f'aria-label="{esc(USER)} profile: operator card, stats, contribution radar, stack">\n'
        "<defs>"
        '<pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="0.9" fill="#ffffff" fill-opacity="0.07"/></pattern>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#ffffff" fill-opacity="0.07"/></pattern>'
        f'<pattern id="hz" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="8" fill="{TEXT}"/></pattern>'
        '<clipPath id="pf"><polygon points="32,82 208,82 232,106 232,282 56,282 32,258"/></clipPath>'
        '<clipPath id="slice"><rect x="250" y="104" width="520" height="9"/><rect x="250" y="130" width="520" height="5"/></clipPath>'
        '<filter id="glow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="ng" x="-40%" y="-60%" width="180%" height="220%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="wide"/>'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="tight"/>'
        '<feMerge><feMergeNode in="wide"/><feMergeNode in="tight"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<radialGradient id="gcore"><stop offset="0" stop-color="#fff" stop-opacity="0.4"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        "</defs>\n"
        f"<style>text {{ font-family: {FONT}; }} .dim {{ fill: {DIM}; }} .txt {{ fill: {TEXT}; }} .hi {{ fill: {BRIGHT}; }} "
        ".gl { animation: gl 5s steps(1) infinite; } @keyframes gl { 0%, 90%, 100% { transform: translateX(0); } 92% { transform: translateX(-9px); } 95% { transform: translateX(8px); } } "
        ".blink { animation: blink 1.1s steps(1) infinite; } @keyframes blink { 50% { opacity: 0; } } "
        ".tw { animation: tw 4s ease-in-out infinite; } @keyframes tw { 50% { opacity: 0.25; } }</style>\n"
        + cut(1, 1, W - 2, total_h - 2, 28, BG, "none", 0) + "\n"
        + cut(1, 1, W - 2, total_h - 2, 28, "url(#dots)", "none", 0) + "\n"
        + "\n".join(parts) + "\n"
        + f'<rect x="1" y="1" width="{W - 2}" height="{total_h - 2}" fill="url(#scan)" opacity="0.5" pointer-events="none"/>\n'
        + cut(1, 1, W - 2, total_h - 2, 28, "none", EDGE, 2) + "\n"
        + corner(1, 1, 18, 18)
        + f'<line x1="{W - 29}" y1="1" x2="{W - 1}" y2="29" stroke="{BRIGHT}" stroke-width="3"/>'
        + f'<line x1="1" y1="{total_h - 29}" x2="29" y2="{total_h - 1}" stroke="{BRIGHT}" stroke-width="3"/>'
        + corner(W - 1, total_h - 1, -18, -18)
        + "\n</svg>\n"
    )
    os.makedirs("assets", exist_ok=True)
    with open("assets/profile.svg", "w", encoding="utf8", newline="\n") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
