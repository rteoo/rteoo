from collections import Counter
from pathlib import Path
import tempfile
import unittest

from update_contributions import (
    END, FILES, START, collect_contributions, render, replace_section, update,
)


def item(number, repo="tobi/disktree"):
    return {"number": number, "repository_url": f"https://api.github.com/repos/{repo}",
            "user": {"login": "rteoo"}, "pull_request": {}, "state": "closed"}


def page(items, total=None, incomplete=False):
    return {"items": items, "total_count": len(items) if total is None else total,
            "incomplete_results": incomplete}


class ContributionsTest(unittest.TestCase):
    def test_pagination_and_repository_grouping(self):
        pages = [page([item(n) for n in range(100)], 101),
                 page([item(101, "openclaw/clawdex")], 101)]
        self.assertEqual(collect_contributions(lambda n: pages[n - 1]),
                         Counter({"tobi/disktree": 100, "openclaw/clawdex": 1}))

    def test_rejects_incomplete_truncated_duplicate_and_excluded_results(self):
        cases = [page([item(1)], incomplete=True), page([], 1001),
                 page([item(1), item(1)]), page([item(1, "rteoo/own")]),
                 page([item(1, "strateo/own")]), page([], 1)]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                collect_contributions(lambda n: data)

    def test_localized_counts_and_safe_links(self):
        counts = Counter({"tobi/disktree": 2, "openclaw/clawdex": 1})
        self.assertIn("2 PRs integrados", render(counts, "pt"))
        self.assertIn("1 merged PR", render(counts, "en"))
        self.assertIn("is%3Amerged+author%3Arteoo", render(counts, "en"))
        with self.assertRaises(ValueError):
            render(Counter(), "en")

    def test_only_marked_content_changes(self):
        text = f"intro\n{START}\nold\n{END}\nfooter"
        self.assertEqual(replace_section(text, "new"),
                         f"intro\n{START}\nnew\n{END}\nfooter")
        for invalid in ["no markers", f"{END}\n{START}", f"{START}{START}{END}"]:
            with self.assertRaises(ValueError):
                replace_section(invalid, "new")

    def test_idempotent_update_and_validation_before_writes(self):
        with tempfile.TemporaryDirectory(prefix="profile-contributions-") as scratch:
            root = Path(scratch)
            original = f"intro\n{START}\nold\n{END}\nfooter\n"
            for name in FILES:
                (root / name).write_text(original, encoding="utf-8")
            fetch = lambda n: page([item(1)])
            self.assertEqual(update(root, fetch), 3)
            self.assertEqual(update(root, fetch), 0)
            for name in FILES:
                (root / name).write_text(original, encoding="utf-8")
            (root / "README.en-US.md").write_text("no markers", encoding="utf-8")
            with self.assertRaises(ValueError):
                update(root, fetch)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
