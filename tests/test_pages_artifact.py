#!/usr/bin/env python3
"""Regression tests for the filtered GitHub Pages artifact.

Run: python3 -m unittest tests.test_pages_artifact -v
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_pages_artifact", ROOT / "scripts" / "build_pages_artifact.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

MANIFEST = json.loads(pages.MANIFEST_PATH.read_text(encoding="utf-8"))


class RealArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "_site"
        cls.fails, cls.report = pages.build(cls.out)
        cls.files = {str(p.relative_to(cls.out)).replace("\\", "/") for p in cls.out.rglob("*") if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build_passes(self):
        self.assertEqual(self.fails, [])
        self.assertEqual(self.report["link_regressions"], [])

    def test_repository_only_material_is_not_published(self):
        exceptions = set(MANIFEST["publish_exceptions"])
        for path in self.files:
            self.assertFalse(path.startswith((".github/", "tests/", "research/", "deploy/")), path)
            if path.startswith(("scripts/", "docs/")):
                self.assertIn(path, exceptions)
        for path in ("README.md", "DECISION_LOG.md", "LICENSE", ".gitignore"):
            self.assertNotIn(path, self.files)

    def test_required_site_files_and_routes_are_published(self):
        for path in MANIFEST["required"]:
            self.assertIn(path, self.files)
        tracked_html = [f for f in pages.tracked_files() if f.endswith(".html") and not f.startswith(("docs/", "research/", "tests/"))]
        for path in tracked_html:
            self.assertIn(path, self.files)
        self.assertEqual((self.out / "CNAME").read_bytes(), (ROOT / "CNAME").read_bytes())
        self.assertIn(".well-known/security.txt", self.files)
        self.assertIn(".nojekyll", self.files)

    def test_published_files_are_byte_identical(self):
        for path in self.files:
            self.assertEqual((self.out / path).read_bytes(), (ROOT / path).read_bytes(), path)

    def test_every_sitemap_url_resolves(self):
        self.assertGreater(self.report["sitemap_urls_checked"], 0)

    def test_every_exception_is_linked_from_a_published_page(self):
        refs = {site_path.lstrip("/") for _, _, site_path in pages.check_links(sorted(self.files), self.out)}
        for path in MANIFEST["publish_exceptions"]:
            self.assertIn(path, refs)


class ManifestRules(unittest.TestCase):
    def test_unclassified_file_fails(self):
        _, _, problems = pages.classify(["index.html", "new-folder/page.html"], MANIFEST)
        self.assertIn("not classified", "\n".join(problems))

    def test_research_and_tests_are_excluded(self):
        files = ["research/valuation-evidence/registry/transactions.v1.json", "tests/test_x.py",
                 "docs/valuation-evidence/SPRINT_1A_FINDINGS.md", "scripts/validate_evidence_registry.py"]
        published, excluded, problems = pages.classify(files, MANIFEST)
        self.assertEqual(published, [])
        self.assertEqual(sorted(excluded), sorted(files))
        self.assertEqual(problems, [])

    def test_double_classification_fails(self):
        manifest = dict(MANIFEST, exclude=MANIFEST["exclude"] + ["kb/**"])
        _, _, problems = pages.classify(["kb/domain-development.html"], manifest)
        self.assertIn("matches both", "\n".join(problems))

    def test_link_regression_and_stale_exception_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            (src / "scripts").mkdir(parents=True)
            (src / "index.html").write_text('<a href="/scripts/tool.py">tool</a><a href="/about.html">a</a>')
            (src / "about.html").write_text("<p>about</p>")
            (src / "scripts" / "tool.py").write_text("print(1)")
            (src / "scripts" / "other.py").write_text("print(2)")
            (src / "sitemap.xml").write_text("<urlset><url><loc>https://sohadot.com/about.html</loc></url></urlset>")
            files = ["about.html", "index.html", "scripts/other.py", "scripts/tool.py", "sitemap.xml"]
            manifest = {"version": 1, "publish": ["*.html", "sitemap.xml"], "exclude": ["scripts/**"],
                        "publish_exceptions": {}, "required": ["index.html"]}
            fails, _ = pages.build(Path(tmp) / "out1", manifest=manifest, files=files, source_root=src)
            self.assertIn("link regression", "\n".join(fails))
            manifest["publish_exceptions"] = {"scripts/tool.py": "linked", "scripts/other.py": "not linked"}
            fails, _ = pages.build(Path(tmp) / "out2", manifest=manifest, files=files, source_root=src)
            text = "\n".join(fails)
            self.assertNotIn("link regression", text)
            self.assertIn("scripts/other.py is no longer referenced", text)

    def test_resolution_rules(self):
        files = {"index.html", "kb/index.html", "kb/page.html", "data/x.json"}
        self.assertTrue(pages.exists_in("/", files))
        self.assertTrue(pages.exists_in("/kb/", files))
        self.assertTrue(pages.exists_in("/kb/page", files))
        self.assertTrue(pages.exists_in(pages.resolve("../data/x.json", "kb/page.html"), files))
        self.assertTrue(pages.exists_in(pages.resolve("https://sohadot.com/kb/page.html", "index.html"), files))
        self.assertIsNone(pages.resolve("https://github.com/Sohadot/Sohadot", "index.html"))
        self.assertIsNone(pages.resolve("mailto:agent@sohadot.com", "index.html"))
        self.assertFalse(pages.exists_in("/missing.html", files))


if __name__ == "__main__":
    unittest.main()
