import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "Aaravpp"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path("assets")
OUT.mkdir(exist_ok=True)

def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
            "User-Agent": "Aaravpp-profile-readme"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

user = api(f"/users/{USERNAME}")
repos = api(f"/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated")
repos = [r for r in repos if not r.get("fork")]

stars = sum(r.get("stargazers_count", 0) for r in repos)
forks = sum(r.get("forks_count", 0) for r in repos)
language_bytes = {}
for repo in repos:
    if repo.get("language"):
        language_bytes[repo["language"]] = language_bytes.get(repo["language"], 0) + 1
    # Pull per-repository language byte counts for a more useful language distribution.
    try:
        langs = api(f"/repos/{USERNAME}/{repo['name']}/languages")
        for name, count in langs.items():
            language_bytes[name] = language_bytes.get(name, 0) + count
    except Exception:
        pass


def graphql(query):
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "Aaravpp-profile-readme"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))
    return result["data"]["user"]["contributionsCollection"]

from datetime import date, datetime, timedelta, timezone

today = datetime.now(timezone.utc).date()
start_date = date(2008, 1, 1)
query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalContributions
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""
contribution_total = None
current_streak = None
longest_streak = None

try:
    variables = {
        "login": USERNAME,
        "from": f"{start_date.isoformat()}T00:00:00Z",
        "to": f"{(today + timedelta(days=1)).isoformat()}T00:00:00Z"
    }
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "Aaravpp-profile-readme"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))
    collection = result["data"]["user"]["contributionsCollection"]
    contribution_total = collection["totalContributions"]
    days = []
    for week in collection["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            days.append((date.fromisoformat(day["date"]), day["contributionCount"]))
    days.sort(key=lambda item: item[0])

    longest = 0
    run = 0
    for _, count in days:
        if count > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    longest_streak = longest

    counts = {d: count for d, count in days}
    check_day = today if counts.get(today, 0) else today - timedelta(days=1)
    current = 0
    while counts.get(check_day, 0) > 0:
        current += 1
        check_day -= timedelta(days=1)
    current_streak = current
except Exception as error:
    print(f"Could not fetch contribution streak metrics: {error}")

def streak_card(theme, filename):
    c = palette(theme)
    total_text = f"{contribution_total:,}" if contribution_total is not None else "—"
    current_text = str(current_streak) if current_streak is not None else "—"
    longest_text = str(longest_streak) if longest_streak is not None else "—"
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="205" viewBox="0 0 720 205" role="img" aria-label="GitHub contribution statistics">',
        f'<rect x="1" y="1" width="718" height="203" rx="8" fill="{c["bg"]}" stroke="{c["line"]}"/>',
        f'<path d="M240 28 V176 M480 28 V176" stroke="{c["line"]}" stroke-width="1"/>',
        f'<text x="120" y="79" text-anchor="middle" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="38" font-weight="700">{total_text}</text>',
        f'<text x="120" y="112" text-anchor="middle" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="14">Total Contributions</text>',
        f'<text x="120" y="143" text-anchor="middle" fill="{c["muted"]}" font-family="Arial,sans-serif" font-size="12">All-time public activity</text>',
        f'<circle cx="360" cy="91" r="51" fill="none" stroke="{c["line"]}" stroke-width="7"/>',
        f'<circle cx="360" cy="91" r="51" fill="none" stroke="#f0883e" stroke-width="7" stroke-linecap="round" stroke-dasharray="250 321" transform="rotate(-90 360 91)"/>',
        f'<text x="360" y="101" text-anchor="middle" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="34" font-weight="700">{current_text}</text>',
        f'<text x="360" y="168" text-anchor="middle" fill="#f0883e" font-family="Arial,sans-serif" font-size="14" font-weight="700">Current Streak</text>',
        f'<text x="600" y="79" text-anchor="middle" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="38" font-weight="700">{longest_text}</text>',
        f'<text x="600" y="112" text-anchor="middle" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="14">Longest Streak</text>',
        f'<text x="600" y="143" text-anchor="middle" fill="{c["muted"]}" font-family="Arial,sans-serif" font-size="12">Consecutive active days</text>',
        '</svg>'
    ]
    (OUT / filename).write_text("\\n".join(pieces), encoding="utf-8")


def palette(theme):
    if theme == "dark":
        return {"bg":"#0d1117","fg":"#e6edf3","muted":"#8b949e","line":"#30363d","bar":"#8b949e"}
    return {"bg":"#ffffff","fg":"#24292f","muted":"#57606a","line":"#d0d7de","bar":"#57606a"}

for theme in ("light", "dark"):
    streak_card(theme, f"contribution-stats-{theme}.svg")

def svg_card(title, rows, theme, filename, width=500, height=210):
    c = palette(theme)
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{width}" height="{height}" rx="8" fill="{c["bg"]}"/>',
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="8" fill="none" stroke="{c["line"]}"/>',
        f'<text x="24" y="34" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="18" font-weight="600">{escape(title)}</text>',
        f'<path d="M24 49 H{width-24}" stroke="{c["line"]}"/>'
    ]
    y = 82
    for label, value in rows:
        pieces += [
            f'<text x="26" y="{y}" fill="{c["muted"]}" font-family="Arial,sans-serif" font-size="13">{escape(str(label))}</text>',
            f'<text x="{width-26}" y="{y}" text-anchor="end" fill="{c["fg"]}" font-family="Arial,sans-serif" font-size="14" font-weight="600">{escape(str(value))}</text>'
        ]
        y += 29
    pieces.append("</svg>")
    (OUT / filename).write_text("\n".join(pieces), encoding="utf-8")

stats = [
    ("Public repositories", user.get("public_repos", 0)),
    ("Followers", user.get("followers", 0)),
    ("Total stars", stars),
    ("Total forks", forks),
]
for theme in ("light", "dark"):
    svg_card("GitHub Stats", stats, theme, f"github-stats-{theme}.svg")

total = sum(language_bytes.values()) or 1
ranked = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:6]
lang_rows = [(name, f"{count / total * 100:.1f}%") for name, count in ranked]
if not lang_rows:
    lang_rows = [("No public language data yet", "—")]
for theme in ("light", "dark"):
    svg_card("Most Used Languages", lang_rows, theme, f"top-languages-{theme}.svg")
