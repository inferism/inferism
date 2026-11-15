#!/usr/bin/env python3
"""Builds assets/profile-dark.svg and assets/profile-light.svg: a student ID style profile card.

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

BIO = "2nd-year BSIT student building apps and tools that'll make my life easier"
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
        okBg="#1f2a05", okLine="#5c7314", idleBg="#1a1a1a", idleLine="#2c2c2c", ring="#2f2f2f", idLine="#2c2c2c", idShadow=".55",
        tones=["#f2f2f0", "#c4c4c4", "#9c9c9c", "#7a7a7a", "#5a5a5a", "#404040"],
    ),
    "light": dict(
        bg="#f4f4f2", bar="#ffffff", card="#ffffff", line="#e0e0dc", rule="#ececea", grid="#ececea",
        ink="#111111", sub="#3d3d3d", mute="#666666", faint="#8a8a8a", chip="#f3f3f0", chipLine="#dcdcd8",
        acc="#9fd40f", accLine="#5d8c00", accText="#3f6212", areaOp=".45", tagBg="#111111", tagInk="#ffffff",
        okBg="#effad0", okLine="#a6d62a", idleBg="#f3f3f0", idleLine="#dcdcd8", ring="#dcdcd8", idLine="#c8c8c2", idShadow=".16",
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


# ── student ID card ──
# GitHub shows the 1000px card at ~690px, so source sizes here are ~1.45x what readers actually see.
HEAT = {"dark": ["#171717", "#2e3a0c", "#56710f", "#93bd1c", "#d7ff3a"],
        "light": ["#e9e9e5", "#dcf2a2", "#b3df45", "#80b20f", "#4a7500"]}
ACC_INK = "#0a0a0a"  # text on the lime strip, both themes
ID_FIELDS = [("NAME", USER), ("YEAR", "2nd"), ("PROGRAM", "BS InfoTech"), ("STATUS", "Alive")]


def wrap(s, n, lines=None):
    return textwrap.wrap(s or "", n, max_lines=lines, placeholder="…") if lines else textwrap.wrap(s or "", n)


def lang_of(r):
    n = (r.get("primaryLanguage") or {}).get("name", "")
    return LANG_NAMES.get(n, n)


def pushed(r):
    return datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))


def level(n, mx):
    if not n:
        return 0
    return min(4, 1 + int(3 * n / max(mx, 1) + 0.5)) if mx > 3 else 4


def repo_rows(pinned):
    return [r for r in (pinned or {}).get("nodes", []) if r and r.get("name") and not r.get("isPrivate")][:6]


def barcode(days, x, y, w, h, fill, n=60):
    """One bar per day for the last n days; busier days get thicker bars."""
    window = [d["contributionCount"] for d in days[-n:]]
    mx = max(window) or 1
    step = w / n
    o = []
    for i, v in enumerate(window):
        bw = 1.2 + (step - 2) * min(1, v / mx * 1.6) if v else 0.8
        o.append(R(x + i * step, y, bw, h, fill, 0, f'opacity="{1 if v else .35}"'))
    return o


def badge(c, right, y, active):
    if active:
        w = 92
        return [R(right - w, y, w, 30, c["okBg"], 15, f'stroke="{c["okLine"]}"'),
                f'<circle class="pulse" cx="{right - w + 18}" cy="{y + 15}" r="4" fill="{c["accLine"]}"/>',
                t(right - w + 29, y + 21, "Active", 15, c["accText"], 600)]
    w = 70
    return [R(right - w, y, w, 30, c["idleBg"], 15, f'stroke="{c["idleLine"]}"'),
            t(right - w / 2, y + 21, "Idle", 15, c["mute"], 600, "middle")]


def id_card(c, days, total, current, longest):
    cx, cy, cw, ch = 32, 40, 360, 600
    o = [R(cx, cy, cw, ch, c["card"], 26, f'stroke="{c["idLine"]}" stroke-width="1.5" filter="url(#sh)"'),
         R(cx + cw / 2 - 34, cy - 22, 68, 40, "none", 12, f'stroke="{c["mute"]}" stroke-width="4"'),  # lanyard clip
         R(cx + cw / 2 - 30, cy + 22, 60, 10, c["bg"], 5, f'stroke="{c["line"]}"'),  # slot
         R(cx, cy + 70, cw, 52, c["acc"]),
         t(cx + 24, cy + 103, "STUDENT DEVELOPER", 17, ACC_INK, 800, font=MONO, ls=2),
         t(cx + cw - 24, cy + 103, "BSIT", 17, ACC_INK, 800, "end", font=MONO, ls=2)]
    py = cy + 150
    o += [R(cx + 24, py, 140, 168, c["chip"], 14),
          f'<clipPath id="ph"><rect x="{cx + 24}" y="{py}" width="140" height="168" rx="14"/></clipPath>',
          f'<g clip-path="url(#ph)"><use href="#pfp" transform="translate({cx + 10} {py}) scale(168)"/></g>']
    for i, (k, v) in enumerate(ID_FIELDS):
        yy = py + 16 + i * 42
        o += [t(cx + 186, yy, k, 12, c["faint"], 700, font=MONO, ls=1.6),
              t(cx + 186, yy + 22, v, 19, c["accText"] if k == "STATUS" else c["ink"], 700)]
    by = py + 196
    for i, ln in enumerate(wrap(BIO, 32)):
        o.append(t(cx + 24, by + i * 26, ln, 18, c["sub"]))
    sy = by + 70
    o.append(hline(cx + 24, cx + cw - 24, sy, c["line"], 'stroke-dasharray="4 5"'))
    for i, (n, lab) in enumerate([(total, "contrib."), (current, "streak"), (longest, "longest")]):
        x = cx + 24 + i * 110
        o += [t(x, sy + 46, str(n), 30, c["accText"] if i == 1 else c["ink"], 800, ls=-1), t(x, sy + 70, lab, 14, c["mute"])]
    o += barcode(days, cx + 24, cy + ch - 84, cw - 48, 46, c["ink"])
    o.append(t(cx + cw / 2, cy + ch - 20, f"{USER.upper()} · LAST 60 DAYS · {sum(x['contributionCount'] for x in days[-60:])}",
               13, c["faint"], 600, "middle", font=MONO, ls=1.4))
    return o, cy + ch


def transcript(c, theme, repos, days, now):
    X, RX = 432, W - 32
    o = [t(X, 64, "TRANSCRIPT OF RECORDS", 15, c["faint"], 700, font=MONO, ls=2.2),
         t(X, 104, "Projects this term", 32, c["ink"], 800, ls=-1),
         t(X, 148, "CODE", 13, c["faint"], 700, font=MONO, ls=1.4), t(X + 70, 148, "PROJECT", 13, c["faint"], 700, font=MONO, ls=1.4),
         t(RX, 148, "STATUS", 13, c["faint"], 700, "end", font=MONO, ls=1.4), hline(X, RX, 162, c["line"])]
    for i, r in enumerate(repos):
        y = 162 + i * 66
        if i:
            o.append(hline(X, RX, y, c["rule"]))
        code = (lang_of(r)[:2] or "··").upper() + f"{101 + i * 10}"
        o += [t(X, y + 30, code, 15, c["mute"], 600, font=MONO),
              t(X + 70, y + 30, r["name"], 19, c["ink"], 700),
              t(X + 70, y + 53, (wrap(r.get("description"), 40, 1) or [""])[0], 15, c["mute"])]
        o += badge(c, RX, y + 15, (now - pushed(r)).days < ACTIVE_DAYS)
    # attendance: the last 16 weeks, one column per week
    ay = 162 + len(repos) * 66 + 36
    win = days[-112:]
    o += [t(X, ay, "ATTENDANCE", 15, c["faint"], 700, font=MONO, ls=2.2),
          t(RX, ay, f"{sum(1 for x in win if x['contributionCount'])}/{len(win)} days present", 15, c["mute"],
            anchor="end", font=MONO)]
    mx = sorted(x["contributionCount"] for x in win)[int(len(win) * .95)] or 1
    cell = (RX - X - 15 * 4) / 16
    for i, x in enumerate(win):
        col, row = divmod(i, 7)
        o.append(R(X + col * (cell + 4), ay + 18 + row * 16, cell, 12, HEAT[theme][level(x["contributionCount"], mx)], 3))
    return o, ay + 18 + 7 * 16


def render(theme, data, now, pfp):
    c = THEMES[theme]
    user = data["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = sorted_days(cal)
    current, longest = streaks(days)
    card, card_end = id_card(c, days, cal["totalContributions"], current, longest)
    rec, rec_end = transcript(c, theme, repo_rows(user.get("pinnedItems")), days, now)
    H = int(max(card_end + 40, rec_end + 32))
    css = ('.pulse{animation:p 2.4s ease-in-out infinite}@keyframes p{50%{opacity:.25}}'
           '@media (prefers-reduced-motion:reduce){.pulse{animation:none}}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(USER)}: {esc(BIO)}. Student ID card with contribution stats, a transcript of pinned '
            f'projects and 16 weeks of activity.">\n'
            f'<defs><image id="pfp" width="1" height="1" preserveAspectRatio="xMidYMid slice" '
            f'href="data:image/jpeg;base64,{pfp}"/><filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#000" flood-opacity="{c["idShadow"]}"/></filter></defs>\n<style>{css}</style>\n'
            f'<rect width="{W}" height="{H}" rx="28" fill="{c["bg"]}" stroke="{c["line"]}"/>\n'
            + "\n".join(card + rec) + "\n</svg>\n")


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
