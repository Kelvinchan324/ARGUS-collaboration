"""Regression guard: internal research must not enter the website artifact."""
import tempfile
import unittest
from pathlib import Path

from build_pages import build


class PagesPrivacyTests(unittest.TestCase):
    def test_private_reference_is_not_published(self):
        root = Path(__file__).resolve().parents[1]
        private = root / "docs/private-reference"
        self.assertTrue(private.is_dir())
        private_names = {p.name for p in private.rglob("*.pdf")}
        self.assertTrue(private_names)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "control/index.html").is_file())
            self.assertFalse(list(output.rglob("private-reference")))
            published_names = {p.name for p in output.rglob("*") if p.is_file()}
            self.assertFalse(private_names & published_names)


if __name__ == "__main__":
    unittest.main()
