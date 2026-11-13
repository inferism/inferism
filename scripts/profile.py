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
def topbar(c, now):
    return [R(0, 0, W, 64, c["bar"], 28), R(0, 32, W, 32, c["bar"]), hline(0, W, 64, c["line"]),
            avatar(44, 32, 16, "avs"),
            t(72, 38, USER, 17, c["ink"], 700), t(72 + len(USER) * 9.6 + 10, 38, "/  overview", 17, c["faint"]),
            R(762, 18, 214, 28, c["chip"], 14, f'stroke="{c["chipLine"]}"'),
            f'<circle class="pulse" cx="780" cy="32" r="4.5" fill="{c["accLine"]}"/>',
            t(792, 37, f"Live · synced {fmt_day(now)}", 14, c["sub"], 500)]


def sidebar(c, langs, y0):
    o = [avatar(88, y0 + 66, 44, "avb"),
         f'<circle cx="88" cy="{y0 + 66}" r="48" fill="none" stroke="{c["ring"]}" stroke-width="2"/>',
         t(44, y0 + 150, USER, 28, c["ink"], 700, ls=-0.8), t(44, y0 + 174, ROLE, 14, c["mute"])]
    y = y0 + 208
    for ln in textwrap.wrap(BIO, 27):
        o.append(t(44, y, ln, 15, c["sub"]))
        y += 22
    y += 4
    o.append(hline(44, 248, y, c["line"]))
    o.append(t(44, y + 32, "FOCUS", 13, c["faint"], 600, ls=1.4))
    for i, s in enumerate(FOCUS):
        yy = y + 50 + i * 32
        o += [R(44, yy, 20, 20, c["chip"], 6, f'stroke="{c["chipLine"]}"'),
              t(54, yy + 15, "›", 15, c["accText"], 700, "middle"), t(74, yy + 15, s, 15, c["ink"])]
    y += 50 + len(FOCUS) * 32 + 10
    o.append(hline(44, 248, y, c["line"]))
    o.append(t(44, y + 32, "STACK", 13, c["faint"], 600, ls=1.4))
    x, yy = 44, y + 46
    for s in STACK:
        w = chip_w(s, 13)
        if x + w > 248:
            x, yy = 44, yy + 32
        o += [R(x, yy, w, 25, c["chip"], 7, f'stroke="{c["chipLine"]}"'),
              t(x + w / 2, yy + 17, s, 13, c["sub"], 500, "middle")]
        x += w + 6
    y = yy + 25 + 22
    if langs:
        o.append(hline(44, 248, y, c["line"]))
        o.append(t(44, y + 32, "LANGUAGES", 13, c["faint"], 600, ls=1.4))
        x, total = 44.0, sum(s for _, s in langs)
        for i, (n, s) in enumerate(langs):
            w = 204 * s / total
            o.append(R(x, y + 46, max(w - 2, 1), 8, c["tones"][i], 3))
            x += w
        for i, (n, s) in enumerate(langs):
            yy = y + 82 + i * 24
            o += [R(44, yy - 10, 10, 10, c["tones"][i], 3), t(62, yy, n, 14, c["sub"]),
                  t(248, yy, f"{s * 100:.0f}%", 13, c["mute"], anchor="end", font=MONO)]
        y += 82 + len(langs) * 24
    return o, y


def kpis(c, total, commits, current, longest, peak, y):
    items = [("Contributions", f"{total:,}", "last 12 months", False),
             ("Commits", f"{commits:,}", f"{commits * 100 // max(total, 1)}% of activity", False),
             ("Day streak", str(current), f"longest {longest}", True),
             ("Peak day", str(peak[1]), f"on {fmt_day(peak[0])}", False)]
    o = []
    for i, (lab, n, sub, acc) in enumerate(items):
        x = 296 + i * 172
        o.append(R(x, y, 160, 112, c["card"], 16, f'stroke="{c["line"]}"'))
        o.append(t(x + 18, y + 30, lab.upper(), 13, c["mute"], 600, ls=1.2))
        o.append(t(x + 16, y + 74, n, 38, c["accText"] if acc else c["ink"], 700, ls=-1.2))
        o.append(t(x + 18, y + 98, sub, 14, c["mute"]))
    return o


def chart(c, days, prs, y):
    x0c, wc, h = 296, 680, 280
    o = [R(x0c, y, wc, h, c["card"], 16, f'stroke="{c["line"]}"'),
         t(x0c + 24, y + 36, "Contributions", 18, c["ink"], 600)]
    window = days[-30:]
    counts = [d["contributionCount"] for d in window]
    o.append(t(x0c + 24, y + 60, f"last 30 days · {sum(counts)} contributions · {prs} PRs this year", 14, c["mute"]))
    active = sum(1 for n in counts if n)
    o += [R(x0c + wc - 136, y + 22, 112, 28, c["chip"], 14, f'stroke="{c["chipLine"]}"'),
          t(x0c + wc - 80, y + 41, f"{active}/30 active", 13, c["sub"], 600, "middle")]
    mx = max(counts) or 1
    x0, x1, top, base = x0c + 52, x0c + wc - 24, y + 96, y + h - 46
    for g in range(4):
        gy = base - (base - top) * g / 3
        o.append(hline(x0, x1, gy, c["grid"], 'stroke-dasharray="3 4"'))
        o.append(t(x0 - 10, gy + 4, round(mx * g / 3), 12, c["faint"], anchor="end", font=MONO))
    n = len(window)
    pts = [(x0 + (x1 - x0) * i / max(n - 1, 1), base - (base - top) * v / mx) for i, v in enumerate(counts)]
    path = smooth(pts, base)
    o.append(f'<path d="{path} L{x1:.1f},{base:.1f} L{x0:.1f},{base:.1f} Z" fill="url(#area)"/>')
    o.append(f'<path class="dr" d="{path}" fill="none" stroke="{c["accLine"]}" stroke-width="2.4" stroke-linejoin="round"/>')
    if any(counts):
        pi = max(range(n), key=lambda i: counts[i])
        px, py = pts[pi]
        tag = f"{counts[pi]} · {fmt_day(date.fromisoformat(window[pi]['date']))}"
        tw = len(tag) * 7.6 + 20
        tx = min(max(px, x0 + tw / 2), x1 - tw / 2)
        o += [f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5.5" fill="{c["card"]}" stroke="{c["accLine"]}" stroke-width="2.5"/>',
              R(tx - tw / 2, py - 38, tw, 24, c["tagBg"], 7), t(tx, py - 21, tag, 13, c["tagInk"], 700, "middle")]
    for i in range(0, n - 4, 7):
        o.append(t(pts[i][0], base + 26, fmt_day(date.fromisoformat(window[i]["date"])), 12, c["faint"], anchor="middle", font=MONO))
    o.append(t(x1, base + 26, "today", 12, c["faint"], anchor="end", font=MONO))
    return o


def repo_table(c, pinned, now, y):
    repos = [r for r in (pinned or {}).get("nodes", []) if r and r.get("name") and not r.get("isPrivate")][:6]
    if not repos:
        return [], 0
    rh = 58
    h = 104 + len(repos) * rh
    o = [R(296, y, 680, h, c["card"], 16, f'stroke="{c["line"]}"'),
         t(320, y + 36, "Pinned repositories", 18, c["ink"], 600)]
    for x, lab, anc in [(320, "REPOSITORY", "start"), (676, "LANGUAGE", "start"), (806, "UPDATED", "start"),
                        (952, "STATUS", "end")]:
        o.append(t(x, y + 72, lab, 12, c["faint"], 600, anc, ls=1.2))
    o.append(hline(296, 976, y + 88, c["line"]))
    for i, r in enumerate(repos):
        ry = y + 88 + i * rh
        if i:
            o.append(hline(320, 952, ry, c["rule"]))
        pushed = datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))
        desc = textwrap.wrap(r.get("description") or "", 50, max_lines=1, placeholder="…")
        o.append(t(320, ry + 25, r["name"], 16, c["ink"], 600))
        if desc:
            o.append(t(320, ry + 45, desc[0], 13, c["mute"]))
        lang = (r.get("primaryLanguage") or {}).get("name", "")
        if lang:
            o += [f'<circle cx="681" cy="{ry + 31}" r="4.5" fill="{c["sub"]}"/>',
                  t(693, ry + 36, LANG_NAMES.get(lang, lang), 14, c["sub"])]
        o.append(t(806, ry + 36, fmt_day(pushed), 14, c["mute"], font=MONO))
        if (now - pushed).days < ACTIVE_DAYS:
            o += [R(874, ry + 17, 78, 26, c["okBg"], 13, f'stroke="{c["okLine"]}"'),
                  f'<circle class="pulse" cx="890" cy="{ry + 30}" r="3.5" fill="{c["accLine"]}"/>',
                  t(899, ry + 35, "Active", 13, c["accText"], 600)]
        else:
            o += [R(884, ry + 17, 68, 26, c["idleBg"], 13, f'stroke="{c["idleLine"]}"'),
                  t(918, ry + 35, "Idle", 13, c["mute"], 600, "middle")]
    return o, h


def render(theme, data, now, pfp):
    c = THEMES[theme]
    user = data["data"]["user"]
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = sorted_days(cal)
    current, longest = streaks(days)
    peak_d = max(days, key=lambda d: d["contributionCount"])
    langs, _ = top_languages(user.get("repositories"))

    top = 88
    side, side_end = sidebar(c, langs, top + 12)
    main = kpis(c, cal["totalContributions"], cc["totalCommitContributions"], current, longest, (date.fromisoformat(peak_d["date"]), peak_d["contributionCount"]), top)
    main += chart(c, days, cc["totalPullRequestContributions"], top + 128)
    table, th = repo_table(c, user.get("pinnedItems"), now, top + 424)
    main += table
    main_end = top + 424 + th if th else top + 408
    H = int(max(side_end + 36, main_end) + 24 + 32)
    o = topbar(c, now)
    o.append(R(24, top, 248, H - top - 56, c["card"], 16, f'stroke="{c["line"]}"'))
    o += side + main
    o.append(t(W / 2, H - 22, f"auto-generated daily via GitHub Actions · last sync {now.day} {now:%b %Y}", 13,
               c["faint"], anchor="middle", font=MONO))

    defs = (f'<image id="pfp" width="1" height="1" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{pfp}"/>'
            f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["acc"]}" '
            f'stop-opacity="{c["areaOp"]}"/><stop offset="1" stop-color="{c["acc"]}" stop-opacity="0"/></linearGradient>')
    css = ('.pulse{animation:p 2.4s ease-in-out infinite}@keyframes p{50%{opacity:.25}}'
           '.dr{stroke-dasharray:2400;stroke-dashoffset:2400;animation:dr 2.4s ease-out forwards}@keyframes dr{to{stroke-dashoffset:0}}'
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
