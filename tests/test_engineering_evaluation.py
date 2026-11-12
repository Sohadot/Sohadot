#!/usr/bin/env python3
"""Contract checks for AEC-UAT-ENG-001, a non-tracking engineer evaluation pilot."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "validation/aec-engineering/index.html"
SCRIPT = ROOT / "validation/aec-engineering/evaluation.js"
STYLE = ROOT / "validation/aec-engineering/evaluation.css"
MANIFEST = ROOT / "deploy/pages-manifest.json"
PROTOCOL = "AEC-UAT-ENG-001"

class StudyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.steps = []
        self.names = []
        self.links = []
        self.external_scripts = []
        self.current_form = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section" and a.get("data-stage") is not None:
            self.steps.append(a["data-stage"])
        if tag in {"input", "textarea"} and a.get("name"):
            self.names.append(a["name"])
        if tag == "a" and a.get("href"):
            self.links.append(a)
        if tag == "script" and a.get("src", "").startswith("http"):
            self.external_scripts.append(a["src"])

class EngineeringEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.js = SCRIPT.read_text(encoding="utf-8")
        cls.css = STYLE.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.parsed = StudyParser()
        cls.parsed.feed(cls.html)

    def test_explicit_publication_inventory(self):
        for category, path in (
            ("pages", "validation/aec-engineering/index.html"),
            ("assets", "validation/aec-engineering/evaluation.css"),
            ("javascript", "validation/aec-engineering/evaluation.js"),
        ):
            self.assertIn(path, self.manifest[category])
        self.assertNotIn("https://sohadot.com/validation/aec-engineering/", (ROOT / "sitemap.xml").read_text())

    def test_unindexed_standalone_page_and_protocol(self):
        self.assertIn('name="robots" content="noindex,nofollow,noarchive,noimageindex"', self.html)
        self.assertIn('name="referrer" content="no-referrer"', self.html)
        self.assertIn("connect-src 'self' https://aec-evaluation.sohadot.com", self.html)
        self.assertIn("frame-src https://challenges.cloudflare.com", self.html)
        self.assertIn("script-src 'self'", self.html)
        self.assertIn("form-action 'none'", self.html)
        self.assertIn(PROTOCOL, self.html)
        self.assertNotIn("googletagmanager", self.html.lower())
        self.assertNotIn("google-analytics", self.html.lower())
        self.assertEqual(self.parsed.external_scripts, [])

    def test_six_ordered_accessible_stages(self):
        self.assertEqual(self.parsed.steps, list(map(str, range(6))))
        for step in range(6):
            self.assertIn(f'id="stage-{step}-title"', self.html)
        for label in ("role", "prior_exposure", "power_completion", "acceptance_completion",
                      "acceptance_distinction", "access_completion", "access_boundary",
                      "issue_flag", "professional_intent"):
            self.assertIn(label, self.parsed.names)
        for k in ("terminology", "boundaries", "document_requests", "ease_of_use", "export_utility", "professional_value"):
            self.assertIn(f'data-rating="{k}"', self.html)

    def test_three_exact_engineering_scenarios(self):
        for phrase in ("rc-03", "rc-12", "rc-15", "acceptance criteria are missing",
                       "signed formal acceptance", "transaction-specific determination"):
            self.assertIn(phrase, self.html)
        links = [a for a in self.parsed.links if "aielectronicchips.com" in a.get("href", "")]
        self.assertEqual(len(links), 3)
        for a in links:
            self.assertEqual(a.get("target"), "_blank")
            self.assertIn("noreferrer", a.get("rel", ""))

    def test_opt_in_collection_only_and_no_surveillance(self):
        for forbidden in ("XMLHttpRequest", "sendBeacon", "WebSocket(",
                          "localStorage", "sessionStorage", "indexedDB", "document.cookie",
                          "innerHTML", "eval(", "navigator.geolocation"):
            self.assertNotIn(forbidden, self.js)
        # Only the three explicitly scoped requests may be made after opt-in.
        self.assertEqual(self.js.count("fetch("), 3)
        for permitted in ('fetch("./submission-config.json"', 'fetch(apiOrigin+"/v1/status"',
                          'fetch(apiOrigin+"/v1/evaluations"'):
            self.assertIn(permitted, self.js)
        cfg = json.loads((ROOT / "validation/aec-engineering/submission-config.json").read_text())
        self.assertEqual(cfg["enabled"], False)
        self.assertIsNone(cfg["apiBase"])
        self.assertIn("mailto:agent@sohadot.com", self.js)
        self.assertIn('getElementById("compose-email").addEventListener("click"', self.js)
        self.assertIn('submitButton.addEventListener("click"', self.js)
        self.assertIn('if(!consent.checked)', self.js)
        self.assertIn("Nothing was sent", self.js)
        self.assertIn("window.confirm", self.js)
        self.assertIn("Clearing this form does not delete any stored submission", self.html)

    def test_no_certification_or_report_score(self):
        for phrase in ("respondent_self_reported:true", "evidence_state_established:null",
                       "engineering_or_scientific_review_certified:false",
                       "tool_activity_observed_by_survey:false"):
            self.assertIn(phrase, self.js)
        self.assertNotIn("readiness_score", self.js)
        self.assertNotIn("risk_rating", self.js)
        self.assertIn("issue_text", self.js)
        self.assertIn('selected("issue_flag")==="yes"', self.js)

    def test_export_actions_and_csv_formula_safety(self):
        for field in ("export-json", "export-csv", "copy-summary", "compose-email", "submit-review"):
            self.assertIn(f'id="{field}"', self.html)
            self.assertIn(f'getElementById("{field}")', self.js)
        for s in ("JSON.stringify(report(),null,2)", "URL.createObjectURL", "s.replace(/", "csvCell", "document.createTextNode"):
            self.assertIn(s, self.js)
        self.assertIn("maxlength=\"900\"", self.html)
        self.assertIn("maxlength=\"700\"", self.html)

    def test_mobile_and_keyboard_focus(self):
        self.assertIn("@media(max-width:630px)", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("prefers-reduced-motion", self.css) 
        self.assertIn("aria-live=\"polite\"", self.html)
        self.assertIn('tabindex="-1"', self.html)
        self.assertIn('h2")', self.js)

if __name__ == "__main__":
    unittest.main()
