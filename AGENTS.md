# Repository guide

This is the public GitHub profile repository for `rteoo`. The root `README.md` appears on the account profile.

- Keep the profile in English, concise, and grounded in public sources.
- Verify repository visibility and descriptions before adding project links. Do not disclose private projects or operational details.
- Keep this repository dependency-free. Use GitHub-compatible Markdown and descriptive link and image text.
- Before a commit, run `git diff --check` and inspect the complete staged diff. Verify changed project links against GitHub.
- Use a task branch for changes. The initial scaffold is published as the first commit on remote `main`; later publication requires the user's authorization.

## Contributions automation

The user requested automatic updates from merged PRs. The `Update contributions` workflow in this repository may commit and push only `README.md` and `README.en-US.md` to `rteoo/rteoo` remote `main`, as `github-actions[bot]`, weekly on Sunday at 22:00 America/Sao_Paulo (Monday 01:00 UTC), on manual dispatch, or after updater/workflow changes land on `main`. It replaces only the `CONTRIBUTIONS` marker blocks. This does not authorize other pushes or repository changes.

- Run `python -B -m unittest discover -s scripts -p 'test_*.py' -v` for updater regression coverage.
- Run `python -B scripts/update_contributions.py` to refresh locally with the existing authenticated `gh` CLI.
- Include merged public upstream PRs by `rteoo`; exclude all repositories owned by `rteoo` or `strateo`, including personal forks such as `rteoo/audio-tray`. User-curated personal projects belong outside the generated contributions block. Display repository links and brief descriptions only, without PR counts or citations. Fetch public descriptions automatically; use curated Portuguese descriptions where available and retain the upstream language for new projects until translated.
- Refuse incomplete, inconsistent, empty, or over-1,000-result searches. Beyond the search ceiling, partition by date before refreshing.
