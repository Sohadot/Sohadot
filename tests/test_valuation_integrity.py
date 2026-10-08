#!/usr/bin/env python3
"""Sprint 0B regression tests: valuation public integrity and data freshness.

Run: python3 -m unittest discover -s tests -v

Clock-independent: every generator test passes an explicit `now`.
"""
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = load_module("generate_valuation_data")
disclosures = load_module("validate_valuation_disclosures")

T1 = datetime(2030, 1, 6, 8, 0, tzinfo=timezone.utc)
T2 = datetime(2030, 1, 13, 8, 0, tzinfo=timezone.utc)
T3 = datetime(2030, 1, 20, 8, 0, tzinfo=timezone.utc)

SEED = {
    "sales": [
        {"domain": "alpha.com", "price": 5000, "year": 2024, "tld": ".com",
         "classification": "dictionary_word", "keywords": [], "notes": "fixture"},
        {"domain": "betapay.com", "price": 12000, "year": 2025, "tld": ".com",
         "classification": "commercial_keyword", "keywords": ["pay"], "notes": "fixture"},
    ]
}


def run_cli(seed_path, out_path, now, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_valuation_data.py"),
         "--seed", str(seed_path), "--output", str(out_path), "--now", now, *extra],
        check=True, capture_output=True, text=True,
    )


class GeneratorDeterminism(unittest.TestCase):
    def test_identical_input_is_a_fixed_point(self):
        first = gen.build_payload(SEED, None, T1)
        second = gen.build_payload(SEED, json.loads(gen.serialize(first)), T2)
        self.assertEqual(gen.serialize(first), gen.serialize(second))

    def test_unchanged_source_keeps_content_and_generation_time(self):
        first = gen.build_payload(SEED, None, T1)
        later = gen.build_payload(SEED, json.loads(gen.serialize(first)), T3)
        self.assertEqual(later["content_updated"], "2030-01-06T08:00:00Z")
        self.assertEqual(later["generated_at"], "2030-01-06T08:00:00Z")
        self.assertEqual(later["last_updated"], later["content_updated"])

    def test_seed_reordering_is_not_a_content_change(self):
        first = gen.build_payload(SEED, None, T1)
        reordered = {"sales": list(reversed(SEED["sales"]))}
        later = gen.build_payload(reordered, json.loads(gen.serialize(first)), T2)
        self.assertEqual(later["content_updated"], first["content_updated"])

    def test_real_change_advances_content_timestamp(self):
        first = gen.build_payload(SEED, None, T1)
        changed = copy.deepcopy(SEED)
        changed["sales"][0]["price"] = 6000
        later = gen.build_payload(changed, json.loads(gen.serialize(first)), T2)
        self.assertEqual(later["content_updated"], "2030-01-13T08:00:00Z")
        self.assertEqual(later["content_updated_basis"], "sales content changed")
        self.assertNotEqual(later["content_sha256"], first["content_sha256"])

    def test_metadata_only_change_does_not_advance_content_timestamp(self):
        first = gen.build_payload(SEED, None, T1)
        previous = json.loads(gen.serialize(first))
        previous["methodology_version"] = "older"
        later = gen.build_payload(SEED, previous, T2)
        self.assertEqual(later["content_updated"], "2030-01-06T08:00:00Z")
        self.assertEqual(later["generated_at"], "2030-01-13T08:00:00Z")

    def test_legacy_build_time_is_never_reused_as_content_date(self):
        sales = gen.sort_sales([gen.normalize_sale(s) for s in SEED["sales"]])
        legacy = {"version": "2.5", "last_updated": "2030-01-01T00:00:00Z", "count": 2, "sales": sales}
        migrated = gen.build_payload(SEED, legacy, T2)
        self.assertIsNone(migrated["content_updated"])
        self.assertEqual(migrated["last_updated_human"], "Not recorded")

        boot = gen.build_payload(SEED, legacy, T2, ("2029-06-01T00:00:00Z", "repository history"))
        self.assertEqual(boot["content_updated"], "2029-06-01T00:00:00Z")
        self.assertEqual(boot["content_updated_basis"], "repository history")

    def test_running_never_marks_sources_verified(self):
        payload = gen.build_payload(SEED, None, T1)
        self.assertEqual(payload["source_verification"]["status"], "not_verified")
        self.assertIsNone(payload["source_verification"]["last_verified"])


    def test_cli_twice_produces_byte_identical_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_path, out_path = Path(tmp) / "seed.json", Path(tmp) / "out.json"
            seed_path.write_text(json.dumps(SEED), encoding="utf-8")
            run_cli(seed_path, out_path, "2030-01-06T08:00:00Z")
            first = out_path.read_bytes()
            result = run_cli(seed_path, out_path, "2030-01-13T08:00:00Z")
            self.assertEqual(first, out_path.read_bytes())
            self.assertIn("not rewritten", result.stdout)

    def test_published_file_is_a_fixed_point_of_the_published_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "valuation_comps.json"
            shutil.copy(ROOT / "data" / "valuation_comps.json", out_path)
            before = out_path.read_bytes()
            run_cli(ROOT / "data" / "valuation_comps_seed.json", out_path, "2099-01-01T00:00:00Z")
            self.assertEqual(before, out_path.read_bytes())


PROVENANCE = {
    "source_name": "Example Report",
    "source_url": "https://example.invalid/sale",
    "sale_date": "2025-03-01",
    "price_status": "confirmed",
    "venue": "marketplace",
}


class VerificationCannotBeInferred(unittest.TestCase):
    """Verification is earned per record, never inferred from a timestamp."""

    def assert_unverified(self, payload):
        self.assertEqual(payload["source_verification"]["status"], "not_verified")
        self.assertIsNone(payload["source_verification"]["last_verified"])
        self.assertIn(disclosures.PROVENANCE_DISCLOSURE, payload["source_verification"]["note"])

    def test_a_global_date_without_record_evidence(self):
        seed = dict(copy.deepcopy(SEED), last_source_verification="2030-01-02")
        self.assert_unverified(gen.build_payload(seed, None, T1))

    def test_b_partial_provenance_does_not_verify_the_dataset(self):
        seed = copy.deepcopy(SEED)
        seed["sales"][0].update(PROVENANCE)
        seed["last_source_verification"] = "2030-01-02"
        self.assert_unverified(gen.build_payload(seed, None, T1))

    def test_b2_full_provenance_fields_still_do_not_verify_in_sprint_0(self):
        seed = copy.deepcopy(SEED)
        for sale in seed["sales"]:
            sale.update(PROVENANCE)
        seed["last_source_verification"] = "2030-01-02"
        self.assert_unverified(gen.build_payload(seed, None, T1))

    def test_c_validator_rejects_a_claimed_verified_dataset(self):
        payload = gen.build_payload(SEED, None, T1)
        forged = copy.deepcopy(payload)
        forged["source_verification"]["status"] = "verified"
        forged["source_verification"]["last_verified"] = "2030-01-02"
        errors = []
        disclosures.check_comps(errors, forged)
        joined = "\n".join(errors)
        self.assertIn("must be 'not_verified'", joined)
        self.assertIn("last_verified must be null", joined)

        partial = copy.deepcopy(payload)
        partial["source_verification"]["status"] = "partially_verified"
        errors = []
        disclosures.check_comps(errors, partial)
        self.assertTrue(errors)

        clean = []
        disclosures.check_comps(clean, payload)
        self.assertEqual(clean, [])

    def test_d_published_dataset_is_unverified(self):
        published = json.loads((ROOT / "data" / "valuation_comps.json").read_text(encoding="utf-8"))
        self.assertEqual(published["count"], 45)
        self.assert_unverified(published)

    def test_e_global_date_does_not_cause_rewrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_path, out_path = Path(tmp) / "seed.json", Path(tmp) / "out.json"
            seed_path.write_text(json.dumps(SEED), encoding="utf-8")
            run_cli(seed_path, out_path, "2030-01-06T08:00:00Z")
            first = out_path.read_bytes()
            seed_path.write_text(json.dumps(dict(SEED, last_source_verification="2030-01-02")), encoding="utf-8")
            result = run_cli(seed_path, out_path, "2030-01-13T08:00:00Z")
            self.assertEqual(first, out_path.read_bytes())
            self.assertIn("not rewritten", result.stdout)


class PublicDisclosures(unittest.TestCase):
    def test_disclosure_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_valuation_disclosures.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_bare_confidence_label_and_missing_notice(self):
        errors = []
        original = disclosures.UI_PATH
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "valuation-ui.js"
            text = original.read_text(encoding="utf-8")
            text = text.replace("Classification confidence:", "Confidence:")
            text = text.replace("${renderEstimateNotice(compsStatus)}", "")
            bad.write_text(text, encoding="utf-8")
            disclosures.UI_PATH = bad
            try:
                disclosures.check_result_card(errors)
            finally:
                disclosures.UI_PATH = original
        joined = "\n".join(errors)
        self.assertIn("Classification confidence", joined)
        self.assertIn("immediately before the price grid", joined)

    def test_validator_rejects_documented_sales_claim(self):
        self.assertIn("documented landmark sales", disclosures.FORBIDDEN_CLAIMS)


@unittest.skipUnless(shutil.which("node"), "node is required for engine checks")
class EngineBehaviourPreserved(unittest.TestCase):
    def test_engine_output_matches_baseline(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "valuation_engine_snapshot.mjs")],
            check=True, capture_output=True, text=True,
        )
        baseline = json.loads((ROOT / "tests" / "fixtures" / "valuation_engine_baseline.json").read_text())
        self.assertEqual(json.loads(result.stdout), baseline)


class EvidenceGapsStayVisible(unittest.TestCase):
    def run_audit(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "audit_valuation_evidence.py"), "--quiet", "--as-of-year", "2026", *args],
            capture_output=True, text=True,
        )

    def test_structural_audit_passes(self):
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("FAIL:", result.stdout)

    def test_strict_gate_still_fails_on_missing_provenance(self):
        result = self.run_audit("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("records_with_full_provenance: 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
