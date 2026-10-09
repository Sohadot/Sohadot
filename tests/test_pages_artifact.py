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

    def test_manifest_has_no_publish_globs(self):
        for path in pages.publish_inventory(MANIFEST):
            self.assertFalse(any(ch in path for ch in "*?["), path)
        self.assertNotIn("publish", MANIFEST)

    def test_unused_seed_data_is_not_published(self):
        for path in ("data/valuation_comps_seed.json", "data/keywords_seed.json", "data/drops_candidates.csv", "data/site-navigation.json"):
            self.assertNotIn(path, self.files)
        for path in MANIFEST["runtime_data"]:
            self.assertIn(path, self.files)

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


def small_manifest(**changes):
    m = {"version": 2, "pages": ["index.html", "about.html"], "site_files": ["sitemap.xml"], "assets": [],
         "javascript": [], "runtime_data": ["data/app.json"], "publish_exceptions": {},
         "exclude": ["scripts/**", "research/**", "data/seed.json"], "required": ["index.html"]}
    m.update(changes)
    return m


def small_site(tmp, extra=None):
    src = Path(tmp) / "src"
    for rel, text in {
        "index.html": '<a href="/about.html">a</a><script>fetch("/data/app.json")</script>',
        "about.html": "<p>about</p>",
        "sitemap.xml": "<urlset><url><loc>https://sohadot.com/about.html</loc></url></urlset>",
        "data/app.json": "{}",
        "data/seed.json": "{}",
        "scripts/tool.py": "print(1)",
        **(extra or {}),
    }.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(text)
    files = sorted(str(p.relative_to(src)) for p in src.rglob("*") if p.is_file())
    return src, files


class ManifestRules(unittest.TestCase):
    def build(self, tmp, manifest, extra=None, name="out"):
        src, files = small_site(tmp, extra)
        fails, report = pages.build(Path(tmp) / name, manifest=manifest, files=files, source_root=src)
        return fails, report, Path(tmp) / name

    def test_small_site_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            fails, _, out = self.build(tmp, small_manifest())
            self.assertEqual(fails, [])
            self.assertFalse((out / "data" / "seed.json").exists())

    def test_unexpected_root_html_cannot_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            fails, _, out = self.build(tmp, small_manifest(), {"internal-draft.html": "<p>draft</p>"})
            self.assertIn("internal-draft.html: not classified", "\n".join(fails))
            self.assertFalse((out / "internal-draft.html").exists())

    def test_unexpected_page_in_published_directory_cannot_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = small_manifest(pages=["index.html", "about.html", "kb/a.html"])
            fails, _, out = self.build(tmp, m, {"kb/a.html": "<p>a</p>", "kb/internal.html": "<p>x</p>"})
            self.assertIn("kb/internal.html: not classified", "\n".join(fails))
            self.assertFalse((out / "kb" / "internal.html").exists())

    def test_research_data_cannot_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            extra = {"research/valuation-evidence/registry/transactions.v1.json": "{}"}
            fails, _, out = self.build(tmp, small_manifest(), extra)
            self.assertEqual(fails, [])
            self.assertFalse((out / "research").exists())
            m = small_manifest(runtime_data=["data/app.json", "research/valuation-evidence/registry/transactions.v1.json"])
            fails, _, _ = self.build(tmp, m, extra, name="out2")
            text = "\n".join(fails)
            self.assertIn("'runtime_data' may only list files under data/", text)
            self.assertIn("also matches exclude", text)

    def test_unlisted_data_file_cannot_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            fails, _, out = self.build(tmp, small_manifest(), {"data/new-internal.json": "{}"})
            self.assertIn("data/new-internal.json: not classified", "\n".join(fails))
            self.assertFalse((out / "data" / "new-internal.json").exists())

    def test_publication_entries_must_be_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            fails, _, _ = self.build(tmp, small_manifest(pages=["*.html"]))
            self.assertIn("must be exact paths", "\n".join(fails))

    def test_double_listing_and_listed_but_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            fails, _, _ = self.build(tmp, small_manifest(site_files=["sitemap.xml", "index.html"]))
            self.assertIn("listed more than once", "\n".join(fails))
            fails, _, _ = self.build(tmp, small_manifest(runtime_data=["data/app.json", "data/seed.json"]), name="o2")
            self.assertIn("also matches exclude", "\n".join(fails))

    def test_link_regression_and_stale_exception_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            extra = {"index.html": '<a href="/scripts/tool.py">t</a><a href="/about.html">a</a><script>fetch("/data/app.json")</script>',
                     "scripts/other.py": "print(2)"}
            fails, _, _ = self.build(tmp, small_manifest(), extra)
            self.assertIn("link regression", "\n".join(fails))
            m = small_manifest(publish_exceptions={"scripts/tool.py": "linked", "scripts/other.py": "not linked"})
            fails, _, _ = self.build(tmp, m, extra, name="o2")
            text = "\n".join(fails)
            self.assertNotIn("link regression", text)
            self.assertIn("scripts/other.py is no longer referenced", text)

    def test_removing_runtime_data_is_a_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            fails, _, _ = self.build(tmp, small_manifest(runtime_data=[], exclude=["scripts/**", "research/**", "data/**"]))
            self.assertIn("/data/app.json", "\n".join(fails))

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
