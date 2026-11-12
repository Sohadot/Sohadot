#!/usr/bin/env python3
"""Chromium end-to-end smoke tests for AEC-UAT-ENG-001.

Run after installing Playwright and the Chromium browser:
python3 -m unittest tests.test_engineering_evaluation_browser -v
"""
from __future__ import annotations

import functools
import http.server
import json
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


@unittest.skipUnless(sync_playwright is not None, "Playwright is required for the mandatory browser gate")
class EngineeringEvaluationBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadedServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/validation/aec-engineering/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 900})
        self.page = self.context.new_page()
        self.requests = []
        self.errors = []
        self.page.on("request", lambda request: self.requests.append((request.method, request.url)))
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.url, wait_until="networkidle")

    def tearDown(self):
        self.context.close()

    def choose(self, name: str, value: str):
        self.page.locator(f'input[name="{name}"][value="{value}"]').check()

    def next(self, step: int):
        self.page.locator(f'.stage[data-stage="{step}"] .next').click()

    def test_full_user_journey_validation_export_and_reset(self):
        self.assertTrue(self.page.locator('.stage[data-stage="0"]').is_visible())
        self.next(0)
        self.assertTrue(self.page.locator('.stage[data-stage="0"]').is_visible())
        self.assertIn("required choices", self.page.locator("#form-status").inner_text())

        self.choose("role", "electrical_engineering")
        self.choose("experience", "6_10")
        self.choose("prior_exposure", "no")
        self.next(0)

        self.choose("power_completion", "completed")
        self.page.locator("#power_observation").fill('=HYPERLINK("https://example.com","example")')
        self.next(1)

        self.choose("acceptance_completion", "completed")
        self.choose("acceptance_distinction", "partial")
        self.next(2)

        self.choose("access_completion", "completed")
        self.choose("access_boundary", "yes")
        self.next(3)

        self.choose("rating_terminology", "4")
        self.choose("rating_boundaries", "3")
        self.choose("rating_document_requests", "5")
        self.choose("rating_ease_of_use", "4")
        self.choose("rating_export_utility", "4")
        self.choose("rating_professional_value", "4")
        self.choose("issue_flag", "yes")
        self.choose("professional_intent", "with_improvements")
        self.next(4)
        self.assertTrue(self.page.locator('.stage[data-stage="4"]').is_visible())
        self.assertIn("required choices", self.page.locator("#form-status").inner_text())
        self.page.locator("#issue_text").fill('The row labelled <script>alert("x")</script> needs review.')
        self.page.locator("#improvement").fill("Explain when a test record is insufficient for formal acceptance.")
        self.next(4)

        preview = self.page.locator("#report-preview").inner_text()
        self.assertIn("<script>alert", preview)
        self.assertEqual(self.page.locator("#report-preview script").count(), 0)
        with tempfile.TemporaryDirectory() as tempdir:
            with self.page.expect_download() as d:
                self.page.locator("#export-json").click()
            downloaded = d.value
            name = Path(tempdir) / downloaded.suggested_filename
            downloaded.save_as(name)
            report = json.loads(name.read_text(encoding="utf-8"))
            self.assertEqual(report["protocol"], "AEC-UAT-ENG-001")
            self.assertEqual(report["evaluation"]["ratings_1_to_5"]["terminology"], 4)
            self.assertEqual(report["evaluation"]["potentially_misleading_wording"], "yes")
            self.assertEqual(report["tasks"]["formal_acceptance_rc12"]["distinction_observed"], "partial")
            self.assertIsNone(report["boundaries"]["evidence_state_established"])
            self.assertFalse(report["boundaries"]["engineering_or_scientific_review_certified"])
            with self.page.expect_download() as d:
                self.page.locator("#export-csv").click()
            csvfile = Path(tempdir) / d.value.suggested_filename
            d.value.save_as(csvfile)
            csvtext = csvfile.read_text(encoding="utf-8")
            self.assertIn("'=HYPERLINK", csvtext)
            self.assertIn("formal_acceptance_rc12", csvtext)

        self.page.once("dialog", lambda dialog: dialog.accept())
        self.page.locator("#clear-evaluation").click()
        self.assertTrue(self.page.locator('.stage[data-stage="0"]').is_visible())
        self.assertEqual(self.page.locator('input[name="role"]:checked').count(), 0)
        self.assertEqual(self.errors, [])
        self.assertFalse(any(method not in {"GET"} for method, _ in self.requests))
        self.assertFalse(any("aielectronicchips.com" in url for _, url in self.requests))
        self.assertEqual(self.page.evaluate("localStorage.length"), 0)
        self.assertEqual(self.page.evaluate("sessionStorage.length"), 0)
        self.assertEqual(self.context.cookies(), [])

    def test_mobile_layout_and_fresh_reload(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.choose("role", "other_or_undisclosed")
        self.choose("prior_exposure", "unsure")
        self.next(0)
        self.assertTrue(self.page.locator('.stage[data-stage="1"]').is_visible())
        self.page.reload(wait_until="networkidle")
        self.assertTrue(self.page.locator('.stage[data-stage="0"]').is_visible())
        self.assertEqual(self.page.locator('input[name="role"]:checked').count(), 0)
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)
        self.assertEqual(self.errors, [])

    def test_no_javascript_still_exposes_instructions(self):
        other = self.browser.new_context(java_script_enabled=False)
        page = other.new_page()
        page.goto(self.url, wait_until="domcontentloaded")
        self.assertEqual(page.locator(".stage").count(), 6)
        self.assertIn("Electrical redundancy documentation", page.locator("body").inner_text())
        other.close()
