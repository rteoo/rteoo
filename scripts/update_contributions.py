"""Refresh only the marked README sections from public merged upstream PRs."""

from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
AUTHOR = "rteoo"
EXCLUDED_OWNERS = {AUTHOR, "strateo"}
START = "<!-- CONTRIBUTIONS:START -->"
END = "<!-- CONTRIBUTIONS:END -->"
FILES = {"README.md": "pt", "README.pt-BR.md": "pt", "README.en-US.md": "en"}


def fetch_page(page):
    query = " ".join([
        f"author:{AUTHOR}", "is:pr", "is:merged", "is:public",
        *(f"-user:{owner}" for owner in sorted(EXCLUDED_OWNERS)),
    ])
    result = subprocess.run(
        ["gh", "api", "--method", "GET", "search/issues", "-f", f"q={query}",
         "-f", "sort=created", "-f", "order=asc", "-F", "per_page=100",
         "-F", f"page={page}"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if result.returncode:
        raise RuntimeError("GitHub search failed; check gh authentication and API limits.")
    return json.loads(result.stdout)


def collect_contributions(fetch=fetch_page):
    counts = Counter()
    seen = set()
    total = None
    for page in range(1, 11):
        data = fetch(page)
        if data.get("incomplete_results") is not False:
            raise ValueError("Incomplete GitHub search; keeping existing README content.")
        current_total = data["total_count"]
        if not isinstance(current_total, int) or current_total < 0:
            raise ValueError("Invalid GitHub search count.")
        # ceiling: Search returns at most 1,000 PRs; partition by date beyond this limit.
        if current_total > 1000:
            raise ValueError("Over 1,000 PRs: partition the search by date before updating.")
        if total is not None and total != current_total:
            raise ValueError("Search changed during pagination; retry the refresh.")
        total = current_total
        items = data["items"]
        for item in items:
            match = re.fullmatch(
                r"https://api\.github\.com/repos/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)",
                item["repository_url"],
            )
            if (not match or item["user"]["login"].lower() != AUTHOR
                    or "pull_request" not in item or item["state"] != "closed"):
                raise ValueError("Unexpected result in merged public PR search.")
            owner, name = match.groups()
            if owner.lower() in EXCLUDED_OWNERS:
                raise ValueError("Search returned an excluded repository.")
            identity = (owner.lower(), name.lower(), item["number"])
            if identity in seen:
                raise ValueError("Duplicate PR during pagination; retry the refresh.")
            seen.add(identity)
            counts[f"{owner}/{name}"] += 1
        if len(seen) == total:
            return counts
        if not items or len(seen) > total:
            raise ValueError("GitHub search returned a partial or inconsistent result.")
    raise ValueError("Could not retrieve all PRs; keeping existing README content.")


def render(counts, language):
    if not counts:
        raise ValueError("No contributions found; refusing to erase the existing list.")
    lines = []
    for repo, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0].lower())):
        if language == "pt":
            label = f"{count} PR integrado" if count == 1 else f"{count} PRs integrados"
        else:
            label = f"{count} merged PR" if count == 1 else f"{count} merged PRs"
        url = f"https://github.com/{repo}/pulls?" + urlencode(
            {"q": f"is:pr is:merged author:{AUTHOR}"}
        )
        lines.append(f"- **[{repo}](https://github.com/{repo})** — [{label}]({url})")
    return "\n".join(lines)


def replace_section(text, body):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("Expected exactly one contributions marker pair.")
    before, rest = text.split(START)
    _, after = rest.split(END)
    if END in before:
        raise ValueError("Contributions markers are out of order.")
    return before + START + "\n" + body + "\n" + END + after


def update(root=ROOT, fetch=fetch_page):
    counts = collect_contributions(fetch)
    planned = []
    # Validate every file before changing any of them.
    for name, language in FILES.items():
        path = root / name
        original = path.read_text(encoding="utf-8")
        replacement = replace_section(original, render(counts, language))
        if original != replacement:
            planned.append((path, replacement))
    for path, replacement in planned:
        path.write_text(replacement, encoding="utf-8", newline="\n")
    return len(planned)


if __name__ == "__main__":
    try:
        print(f"Updated {update()} README file(s).")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        raise SystemExit(f"Contribution refresh failed: {error}") from None
