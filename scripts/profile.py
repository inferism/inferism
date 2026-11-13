#!/usr/bin/env python3
"""Builds assets/profile-dark.svg and assets/profile-light.svg: a dashboard-style profile card.

The README picks one per visitor with <picture> + prefers-color-scheme, which follows their GitHub theme.
Needs: gh CLI + GH_TOKEN, and PROFILE_USER (defaults to inferism). Set PROFILE_FAKE=<json file> to test offline.
"""
import base64
import json
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

BIO = "2nd-year BSIT student building web apps, CLIs and desktop tools I'd actually use."
ROLE = "BSIT · 2nd year"
FOCUS = ["Web apps", "CLIs", "Desktop tools"]
STACK = ["TypeScript", "Next.js", "React", "Firebase", "Vercel", "Python", "Rust", "GitHub Actions"]
LANG_NAMES = {"Visual Basic .NET": "VB.NET"}
ACTIVE_DAYS = 3  # a pinned repo pushed within this many days shows as Active

THEMES = {
    "dark": dict(
        bg="#080808", bar="#101010", card="#111111", line="#232323", rule="#1c1c1c", grid="#1f1f1f",
        ink="#f2f2f0", sub="#c4c4c4", mute="#8a8a8a", faint="#6a6a6a", chip="#1a1a1a", chipLine="#2c2c2c",
        acc="#d7ff3a", accLine="#d7ff3a", accText="#d7ff3a", areaOp=".35", tagBg="#f2f2f0", tagInk="#0a0a0a",
        okBg="#1f2a05", okLine="#5c7314", idleBg="#1a1a1a", idleLine="#2c2c2c", ring="#2f2f2f",
        tones=["#f2f2f0", "#c4c4c4", "#9c9c9c", "#7a7a7a", "#5a5a5a", "#404040"],
    ),
    "light": dict(
        bg="#f4f4f2", bar="#ffffff", card="#ffffff", line="#e0e0dc", rule="#ececea", grid="#ececea",
        ink="#111111", sub="#3d3d3d", mute="#666666", faint="#8a8a8a", chip="#f3f3f0", chipLine="#dcdcd8",
        acc="#9fd40f", accLine="#5d8c00", accText="#3f6212", areaOp=".45", tagBg="#111111", tagInk="#ffffff",
        okBg="#effad0", okLine="#a6d62a", idleBg="#f3f3f0", idleLine="#dcdcd8", ring="#dcdcd8",
        tones=["#111111", "#3d3d3d", "#666666", "#8a8a8a", "#adadad", "#cdcdc9"],
    ),
}


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


def top_languages(repos, n=4):
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


def fmt_day(d):
    return f"{d:%b} {d.day}"


# ── drawing helpers ──
def t(x, y, s, size=14, fill="#000", weight=400, anchor="start", font=SANS, ls=None):
    e = f' letter-spacing="{ls}"' if ls is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{e}>{esc(s)}</text>')


def R(x, y, w, h, fill, rx=0, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" {extra}/>'


def hline(x1, x2, y, stroke, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{stroke}" {extra}/>'


def chip_w(s, px):
    return len(s) * px * 0.56 + 20


def smooth(pts, floor):
    """Catmull-Rom spline through pts as cubic beziers; control points never dip below the baseline."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(floor, p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(floor, p2[1] - (p3[1] - p1[1]) / 6))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def avatar(cx, cy, r, cid):
    """Circular crop of the shared #pfp image (a 1x1 unit image defined once in <defs>)."""
    return (f'<clipPath id="{cid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
            f'<g clip-path="url(#{cid})"><use href="#pfp" transform="translate({cx - r} {cy - r}) scale({2 * r})"/></g>')


# ── sections ──
# GitHub shows the 1000px card at ~690px, so source sizes here are ~1.45x what readers actually see.
SX, SW = 44, 228  # sidebar content x and width
MX, MW = 308, 668  # main column x and width


def topbar(c, now):
    return [R(0, 0, W, 72, c["bar"], 28), R(0, 36, W, 36, c["bar"]), hline(0, W, 72, c["line"]),
            t(32, 45, USER, 21, c["ink"], 700), t(32 + len(USER) * 11.6 + 12, 45, "/  overview", 21, c["faint"]),
            R(724, 18, 252, 36, c["chip"], 18, f'stroke="{c["chipLine"]}"'),
            f'<circle class="pulse" cx="746" cy="36" r="5.5" fill="{c["accLine"]}"/>',
            t(760, 42, f"Live · synced {fmt_day(now)}", 17, c["sub"], 500)]


def sidebar(c, langs, y0):
    o = [avatar(SX + 50, y0 + 68, 50, "avb"),
         f'<circle cx="{SX + 50}" cy="{y0 + 68}" r="54" fill="none" stroke="{c["ring"]}" stroke-width="2"/>',
         t(SX, y0 + 164, USER, 32, c["ink"], 700, ls=-0.8), t(SX, y0 + 192, ROLE, 17, c["mute"])]
    y = y0 + 230
    for ln in textwrap.wrap(BIO, 24):
        o.append(t(SX, y, ln, 17, c["sub"]))
        y += 25
    y += 4

    def section(y, title):
        return [hline(SX, SX + SW, y, c["line"]), t(SX, y + 34, title, 15, c["faint"], 600, ls=1.4)]

    o += section(y, "FOCUS")
    for i, s in enumerate(FOCUS):
        yy = y + 52 + i * 36
        o += [R(SX, yy, 24, 24, c["chip"], 7, f'stroke="{c["chipLine"]}"'),
              t(SX + 12, yy + 18, "›", 18, c["accText"], 700, "middle"), t(SX + 36, yy + 18, s, 18, c["ink"])]
    y += 52 + len(FOCUS) * 36 + 12
    o += section(y, "STACK")
    x, yy = SX, y + 50
    for s in STACK:
        w = chip_w(s, 15)
        if x + w > SX + SW:
            x, yy = SX, yy + 36
        o += [R(x, yy, w, 29, c["chip"], 8, f'stroke="{c["chipLine"]}"'),
              t(x + w / 2, yy + 20, s, 15, c["sub"], 500, "middle")]
        x += w + 7
    y = yy + 29 + 24
    if langs:
        o += section(y, "LANGUAGES")
        x, total = float(SX), sum(s for _, s in langs)
        for i, (n, s) in enumerate(langs):
            w = SW * s / total
            o.append(R(x, y + 50, max(w - 2, 1), 10, c["tones"][i], 4))
            x += w
        for i, (n, s) in enumerate(langs):
            yy = y + 92 + i * 28
            o += [R(SX, yy - 12, 12, 12, c["tones"][i], 3), t(SX + 22, yy, n, 17, c["sub"]),
                  t(SX + SW, yy, f"{s * 100:.0f}%", 16, c["mute"], anchor="end", font=MONO)]
        y += 92 + (len(langs) - 1) * 28
    return o, y


def kpis(c, total, commits, current, longest, peak, y):
    items = [("Contributions", f"{total:,}", "last 12 months", False),
             ("Commits", f"{commits:,}", f"{commits * 100 // max(total, 1)}% of activity", False),
             ("Day streak", str(current), f"longest {longest}", True),
             ("Peak day", str(peak[1]), f"on {fmt_day(peak[0])}", False)]
    cw = (MW - 36) / 4
    o = []
    for i, (lab, n, sub, acc) in enumerate(items):
        x = MX + i * (cw + 12)
        o.append(R(x, y, cw, 128, c["card"], 16, f'stroke="{c["line"]}"'))
        o.append(t(x + 18, y + 34, lab, 17, c["mute"], 600))
        o.append(t(x + 16, y + 84, n, 44, c["accText"] if acc else c["ink"], 700, ls=-1.4))
        o.append(t(x + 18, y + 112, sub, 16, c["mute"]))
    return o


def chart(c, days, prs, y, h):
    o = [R(MX, y, MW, h, c["card"], 16, f'stroke="{c["line"]}"'),
         t(MX + 24, y + 40, "Contributions", 22, c["ink"], 600)]
    window = days[-30:]
    counts = [d["contributionCount"] for d in window]
    o.append(t(MX + 24, y + 68, f"last 30 days · {sum(counts)} total · {prs} PRs this year", 17, c["mute"]))
    active = sum(1 for n in counts if n)
    o += [R(MX + MW - 160, y + 20, 136, 34, c["chip"], 17, f'stroke="{c["chipLine"]}"'),
          t(MX + MW - 92, y + 43, f"{active}/30 active", 16, c["sub"], 600, "middle")]
    mx = max(counts) or 1
    x0, x1, top, base = MX + 62, MX + MW - 24, y + 112, y + h - 52
    for g in range(4):
        gy = base - (base - top) * g / 3
        o.append(hline(x0, x1, gy, c["grid"], 'stroke-dasharray="3 4"'))
        o.append(t(x0 - 12, gy + 5, round(mx * g / 3), 15, c["faint"], anchor="end", font=MONO))
    n = len(window)
    pts = [(x0 + (x1 - x0) * i / max(n - 1, 1), base - (base - top) * v / mx) for i, v in enumerate(counts)]
    path = smooth(pts, base)
    o.append(f'<path d="{path} L{x1:.1f},{base:.1f} L{x0:.1f},{base:.1f} Z" fill="url(#area)"/>')
    o.append(f'<path class="dr" pathLength="1" d="{path}" fill="none" stroke="{c["accLine"]}" stroke-width="2.8" stroke-linejoin="round"/>')
    if any(counts):
        pi = max(range(n), key=lambda i: counts[i])
        px, py = pts[pi]
        tag = f"{counts[pi]} · {fmt_day(date.fromisoformat(window[pi]['date']))}"
        tw = len(tag) * 9.2 + 24
        tx = min(max(px, x0 + tw / 2), x1 - tw / 2)
        o += [f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6.5" fill="{c["card"]}" stroke="{c["accLine"]}" stroke-width="3"/>',
              R(tx - tw / 2, py - 44, tw, 30, c["tagBg"], 8), t(tx, py - 23, tag, 16, c["tagInk"], 700, "middle")]
    for i in range(0, n - 5, 7):
        o.append(t(pts[i][0], base + 32, fmt_day(date.fromisoformat(window[i]["date"])), 15, c["faint"],
                   anchor="middle", font=MONO))
    o.append(t(x1, base + 32, "today", 15, c["faint"], anchor="end", font=MONO))
    return o


def repo_rows(pinned):
    return [r for r in (pinned or {}).get("nodes", []) if r and r.get("name") and not r.get("isPrivate")][:6]


RH = 70  # table row height


def table_height(repos):
    return 112 + len(repos) * RH if repos else 0


def repo_table(c, repos, now, y):
    if not repos:
        return []
    cl, cu, cs = 648, 778, MX + MW - 24  # language, updated, status (right edge) columns
    o = [R(MX, y, MW, table_height(repos), c["card"], 16, f'stroke="{c["line"]}"'),
         t(MX + 24, y + 40, "Pinned repositories", 22, c["ink"], 600)]
    for x, lab, anc in [(MX + 24, "REPOSITORY", "start"), (cl, "LANGUAGE", "start"), (cu, "UPDATED", "start"),
                        (cs, "STATUS", "end")]:
        o.append(t(x, y + 80, lab, 14, c["faint"], 600, anc, ls=1.2))
    o.append(hline(MX, MX + MW, y + 96, c["line"]))
    for i, r in enumerate(repos):
        ry = y + 96 + i * RH
        if i:
            o.append(hline(MX + 24, cs, ry, c["rule"]))
        pushed = datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))
        desc = textwrap.wrap(r.get("description") or "", 38, max_lines=1, placeholder="…")
        o.append(t(MX + 24, ry + 30, r["name"], 20, c["ink"], 600))
        if desc:
            o.append(t(MX + 24, ry + 54, desc[0], 16, c["mute"]))
        lang = (r.get("primaryLanguage") or {}).get("name", "")
        if lang:
            o += [f'<circle cx="{cl + 5}" cy="{ry + 37}" r="5" fill="{c["sub"]}"/>',
                  t(cl + 18, ry + 43, LANG_NAMES.get(lang, lang), 17, c["sub"])]
        o.append(t(cu, ry + 43, fmt_day(pushed), 17, c["mute"], font=MONO))
        if (now - pushed).days < ACTIVE_DAYS:
            o += [R(cs - 92, ry + 20, 92, 32, c["okBg"], 16, f'stroke="{c["okLine"]}"'),
                  f'<circle class="pulse" cx="{cs - 74}" cy="{ry + 36}" r="4" fill="{c["accLine"]}"/>',
                  t(cs - 64, ry + 42, "Active", 16, c["accText"], 600)]
        else:
            o += [R(cs - 76, ry + 20, 76, 32, c["idleBg"], 16, f'stroke="{c["idleLine"]}"'),
                  t(cs - 38, ry + 42, "Idle", 16, c["mute"], 600, "middle")]
    return o


def render(theme, data, now, pfp):
    c = THEMES[theme]
    user = data["data"]["user"]
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = sorted_days(cal)
    current, longest = streaks(days)
    peak_d = max(days, key=lambda d: d["contributionCount"])
    langs, _ = top_languages(user.get("repositories"))
    repos = repo_rows(user.get("pinnedItems"))

    top, gap = 96, 16
    side, side_end = sidebar(c, langs, top + 16)
    side_end += 28  # sidebar card's bottom padding
    th = table_height(repos)
    # the chart takes whatever height keeps both columns ending on the same line
    ch = max(330, side_end - (top + 128 + gap) - (th + gap if th else 0))
    chart_y = top + 128 + gap
    table_y = chart_y + ch + gap
    bottom = max(side_end, table_y - gap + (th + gap if th else 0))
    H = int(bottom + 24)

    o = topbar(c, now)
    o.append(R(24, top, SW + 40, bottom - top, c["card"], 16, f'stroke="{c["line"]}"'))
    o += side
    o += kpis(c, cal["totalContributions"], cc["totalCommitContributions"], current, longest,
              (date.fromisoformat(peak_d["date"]), peak_d["contributionCount"]), top)
    o += chart(c, days, cc["totalPullRequestContributions"], chart_y, ch)
    o += repo_table(c, repos, now, table_y)

    defs = (f'<image id="pfp" width="1" height="1" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{pfp}"/>'
            f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["acc"]}" '
            f'stop-opacity="{c["areaOp"]}"/><stop offset="1" stop-color="{c["acc"]}" stop-opacity="0"/></linearGradient>')
    css = ('.pulse{animation:p 2.4s ease-in-out infinite}@keyframes p{50%{opacity:.25}}'
           '.dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr 2.4s ease-out forwards}@keyframes dr{to{stroke-dashoffset:0}}'
           '@media (prefers-reduced-motion:reduce){.pulse{animation:none}.dr{animation:none;stroke-dashoffset:0}}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(USER)}: {esc(BIO)} Contribution stats, 30-day activity, stack, languages and pinned repositories.">\n'
            f'<defs>{defs}</defs>\n<style>{css}</style>\n'
            f'<rect width="{W}" height="{H}" rx="28" fill="{c["bg"]}" stroke="{c["line"]}"/>\n' + "\n".join(o) + "\n</svg>\n")


def main():
    data = fetch()
    now = datetime.now(timezone.utc)
    with open("assets/pfp.jpg", "rb") as f:
        pfp = base64.b64encode(f.read()).decode()
    os.makedirs("assets", exist_ok=True)
    for theme in THEMES:
        with open(f"assets/profile-{theme}.svg", "w", encoding="utf8", newline="\n") as f:
            f.write(render(theme, data, now, pfp))


if __name__ == "__main__":
    main()
