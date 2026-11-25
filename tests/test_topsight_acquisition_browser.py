"""Browser regression for the TopSight acquisition UI; no real email sent."""
import functools
import http.server
import json
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

class TopSightAcquisitionBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/bundles/ai-ar-vr-sight/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def test_contact_and_submission_failure_then_success(self):
        for width in (390, 1280):
            with self.subTest(width=width):
                context = self.browser.new_context(viewport={"width": width, "height": 844})
                page = context.new_page()
                calls = []
                mock = """window.turnstile={render:(selector,options)=>{window.testChallenge=options;return 'mock';},reset:()=>{}}; window.sohadotTopSightTurnstile();"""
                page.route("https://challenges.cloudflare.com/**", lambda route: route.fulfill(content_type="application/javascript", body=mock))
                def answer(route):
                    calls.append(route.request.post_data_json)
                    ok = len(calls) == 2
                    route.fulfill(status=200 if ok else 503, content_type="application/json", body=json.dumps({"ok":ok,"reference":"mock-reference"} if ok else {"ok":False}))
                page.route("**/api/acquisition/topsight", answer)
                page.goto(self.url, wait_until="load")
                page.locator('a.btn-primary[href="#acquisition-contact"]').first.click()
                self.assertTrue(page.url.endswith("#acquisition-contact"))
                expect(page.locator("#bundle-inquiry")).to_be_visible()
                expect(page.locator("#inquiry-submit")).to_be_disabled()
                page.locator("#inquiry-name").fill("Test Buyer")
                page.locator("#inquiry-email").fill("buyer@example.com")
                page.locator("#inquiry-message").fill("Test only")
                page.evaluate("window.testChallenge.callback('mock-token')")
                page.locator("#inquiry-submit").click()
                expect(page.locator("#inquiry-status")).to_contain_text("could not confirm")
                expect(page.locator("#inquiry-message")).to_have_value("Test only")
                expect(page.locator("#inquiry-submit")).to_be_disabled()
                page.evaluate("window.testChallenge.callback('mock-token-2')")
                page.locator("#inquiry-submit").click()
                expect(page.locator("#inquiry-status")).to_contain_text("mock-reference")
                expect(page.locator("#inquiry-submit")).to_be_disabled()
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[0]["email"], "buyer@example.com")
                self.assertEqual(calls[1]["token"], "mock-token-2")
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                context.close()

    def test_no_javascript_contact_fallback(self):
        context = self.browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(self.url, wait_until="domcontentloaded")
        page.locator('a.btn-primary[href="#acquisition-contact"]').first.click()
        expect(page.locator("#bundle-inquiry")).to_be_hidden()
        expect(page.locator("#contact-address")).to_have_value("agent@sohadot.com")
        expect(page.get_by_role("link", name="Open Gmail (web)")).to_be_visible()
        context.close()
