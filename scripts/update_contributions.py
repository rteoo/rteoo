"""Refresh only the marked README sections from public merged PRs."""

from collections import Counter
from html import escape
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
AUTHOR = "rteoo"
START = "<!-- CONTRIBUTIONS:START -->"
END = "<!-- CONTRIBUTIONS:END -->"
FILES = {"README.md": "pt", "README.pt-BR.md": "pt", "README.en-US.md": "en"}
PT_DESCRIPTIONS = {
    "tobi/disktree": "Visualizador de uso do disco em mapa de árvore, feito em Rust e GPUI para Omarchy.",
    "openclaw/clawdex": "Catálogo local de contatos para agentes de IA.",
    "openclaw/discrawl": "CLI para Discord com armazenamento local em SQLite.",
    "codigoquant/b3fileparser": "Leitor de arquivos de dados da B3 em Python.",
}
EN_DESCRIPTIONS = {
    "openclaw/clawdex": "A local contact catalog for AI agents.",
    "codigoquant/b3fileparser": "A Python parser for B3 historical market data files.",
}


def fetch_page(page):
    query = " ".join([
        f"author:{AUTHOR}", "is:pr", "is:merged", "is:public",
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


def fetch_repository(repo):
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}"], capture_output=True, text=True,
        encoding="utf-8", check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Could not fetch public metadata for {repo}.")
    data = json.loads(result.stdout)
    if data["private"] or data["full_name"].lower() != repo.lower():
        raise ValueError(f"Unexpected or non-public repository: {repo}.")
    return data.get("description")


def render(descriptions, language):
    if not descriptions:
        raise ValueError("No contributions found; refusing to erase the existing list.")
    lines = []
    for repo, description in sorted(descriptions.items(), key=lambda pair: pair[0].lower()):
        if language == "pt" and repo.lower() in PT_DESCRIPTIONS:
            description = PT_DESCRIPTIONS[repo.lower()]
        elif language == "en" and repo.lower() in EN_DESCRIPTIONS:
            description = EN_DESCRIPTIONS[repo.lower()]
        if not description:
            description = "Sem descrição pública." if language == "pt" else "No public description."
        description = " ".join(description.split())
        if len(description) > 180:
            description = description[:177].rsplit(" ", 1)[0] + "…"
        description = re.sub(r"([\\`*_[\]{}()!|])", r"\\\1", escape(description))
        lines.append(f"- **[{repo}](https://github.com/{repo})** — {description}")
    return "\n".join(lines)


def replace_section(text, body):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("Expected exactly one contributions marker pair.")
    before, rest = text.split(START)
    _, after = rest.split(END)
    if END in before:
        raise ValueError("Contributions markers are out of order.")
    return before + START + "\n" + body + "\n" + END + after


def update(root=ROOT, fetch=fetch_page, fetch_repo=fetch_repository):
    counts = collect_contributions(fetch)
    descriptions = {repo: fetch_repo(repo) for repo in sorted(counts)}
    planned = []
    # Validate every file before changing any of them.
    for name, language in FILES.items():
        path = root / name
        original = path.read_text(encoding="utf-8")
        replacement = replace_section(original, render(descriptions, language))
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
