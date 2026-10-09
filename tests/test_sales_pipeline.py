"""Tests for the Sprint 1B candidate comparable-sales pipeline (research only).

Records built here are test fixtures, not sales evidence.
"""

import copy
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sales_pipeline as sp  # noqa: E402

RIGHT_OK = {"status": "PERMITTED_WITH_CONDITIONS", "basis_type": "WRITTEN_PERMISSION",
            "basis": "Fixture: written permission from the venue for storage and modelling.",
            "reference": "fixture-permission-001"}
RIGHT_UNKNOWN = {"status": "NOT_ESTABLISHED", "basis_type": "NONE",
                 "basis": "Fixture: no licence, permission or documented lawful basis recorded.", "reference": None}


def record(tid="SOH-TX-900001", domain="example-one.com", amount=4200, date="2025-03-14", **over):
    """A reviewed, single-domain, cash, rights-cleared completed sale (fixture)."""
    r = {
        "transaction_id": tid, "domain": domain, "sale_price": amount, "currency": "USD",
        "price_scope": "SINGLE_DOMAIN", "bundle": None, "sale_date": date, "sale_date_precision": "DAY",
        "report_date": date, "venue": "MARKETPLACE", "transaction_type": "DOMAIN_ONLY",
        "consideration_type": "CASH", "market_side": "INVESTOR_TRADE",
        "source_name": "Fixture venue report", "source_url": f"https://venue.example/report/{tid}",
        "source_type": "MARKETPLACE_RECORD", "source_access_method": "DOCUMENT_REVIEWED",
        "source_accessed_at": "2026-10-09", "review_method": "RAW_TEXT_CHECKED",
        "document_locator": "Weekly report table, row 3", "checked_quote": f"{domain} sold for ${amount}",
        "document_sha256": "0" * 64, "additional_sources": [], "leads": [],
        "price_disclosure_status": "EXACT", "price_claims": [], "conflicts": [], "valuation_caveats": [],
        "evidence_status": "VERIFIED", "verification_basis": "Fixture", "verified_at": "2026-10-09",
        "attesting_party": "VENUE", "settlement_evidence": "PARTY_ATTESTATION_ONLY",
        "rights": {"citation": dict(RIGHT_OK), "storage": dict(RIGHT_OK),
                   "commercial_modelling": dict(RIGHT_OK), "redistribution": dict(RIGHT_UNKNOWN)},
        "calibration_role": "UNDETERMINED", "notes": "fixture",
    }
    r = sp.pipeline_from_registry(r)
    for key, value in over.items():
        if key in r["pipeline"]:
            r["pipeline"][key] = value
        else:
            r[key] = value
    return r


def assessed(*records):
    return {r["transaction_id"]: r for r in sp.assess_all(list(records))}


class StateAssessment(unittest.TestCase):
    def test_clean_record_is_eligible(self):
        r = assessed(record())["SOH-TX-900001"]["pipeline"]
        self.assertEqual((r["state"], r["blockers"], r["rejection_reasons"]), ("ELIGIBLE", [], []))

    def test_asking_prices_and_bids_are_rejected(self):
        for kind in ("ASKING_PRICE", "AUCTION_BID", "AUCTION_RESULT_UNCONFIRMED"):
            r = assessed(record(price_type=kind))["SOH-TX-900001"]["pipeline"]
            self.assertEqual(r["state"], "REJECTED")
            self.assertIn("NOT_A_COMPLETED_SALE", r["rejection_reasons"])

    def test_undisclosed_and_imprecise_prices_are_rejected(self):
        r = assessed(record(price_disclosure_status="UNDISCLOSED", sale_price=None, original_amount=None,
                            amount_usd=None))["SOH-TX-900001"]["pipeline"]
        self.assertIn("PRICE_NOT_DISCLOSED", r["rejection_reasons"])
        r = assessed(record(price_disclosure_status="APPROXIMATE"))["SOH-TX-900001"]["pipeline"]
        self.assertIn("IMPRECISE_PRICE", r["rejection_reasons"])

    def test_bundles_and_businesses_are_rejected(self):
        r = assessed(record(transaction_type="MULTIPLE_DOMAINS", price_scope="BUNDLE_TOTAL"))["SOH-TX-900001"]
        self.assertIn("NOT_SINGLE_DOMAIN", r["pipeline"]["rejection_reasons"])
        r = assessed(record(transaction_type="UNKNOWN", price_scope="UNKNOWN"))["SOH-TX-900001"]
        self.assertEqual(r["pipeline"]["state"], "SOURCE_REVIEWED")
        self.assertIn("SCOPE_UNKNOWN", r["pipeline"]["blockers"])

    def test_non_cash_consideration_is_rejected(self):
        r = assessed(record(consideration_type="CASH_AND_STOCK"))["SOH-TX-900001"]["pipeline"]
        self.assertIn("NON_CASH_CONSIDERATION", r["rejection_reasons"])

    def test_rights_block_or_reject(self):
        r = record()
        r["rights"]["commercial_modelling"] = dict(RIGHT_UNKNOWN)
        p = assessed(r)["SOH-TX-900001"]["pipeline"]
        self.assertEqual(p["state"], "SOURCE_REVIEWED")
        self.assertIn("RIGHTS_NOT_ESTABLISHED", p["blockers"])
        r["rights"]["commercial_modelling"] = dict(RIGHT_UNKNOWN, status="NOT_PERMITTED")
        self.assertIn("RIGHTS_NOT_PERMITTED", assessed(r)["SOH-TX-900001"]["pipeline"]["rejection_reasons"])

    def test_unreviewed_record_stays_discovered(self):
        p = assessed(record(evidence_status="UNVERIFIED"))["SOH-TX-900001"]["pipeline"]
        self.assertEqual(p["state"], "DISCOVERED")
        self.assertIn("NO_REVIEWED_SOURCE", p["blockers"])

    def test_disputed_record_is_blocked(self):
        p = assessed(record(evidence_status="DISPUTED"))["SOH-TX-900001"]["pipeline"]
        self.assertIn("MATERIAL_CONFLICT_UNRESOLVED", p["blockers"])

    def test_non_usd_needs_fx_basis(self):
        r = record(currency="EUR", original_currency="EUR", amount_usd=None)
        p = assessed(r)["SOH-TX-900001"]["pipeline"]
        self.assertIn("FX_BASIS_MISSING", p["blockers"])
        r = record(currency="EUR", original_currency="EUR", amount_usd=4500, fx_basis="ECB reference rate 2025-03-14")
        self.assertEqual(assessed(r)["SOH-TX-900001"]["pipeline"]["state"], "ELIGIBLE")


class Duplicates(unittest.TestCase):
    def test_duplicate_reports_block_until_resolved(self):
        a = record("SOH-TX-900001", "dupe.com", 5000, "2025-03-14")
        b = record("SOH-TX-900002", "DUPE.com", 5050, "2025-04-01")
        self.assertEqual(sp.find_relationships([a, b])[0][2], "DUPLICATE_REPORT")
        out = assessed(a, b)
        self.assertTrue(all("DUPLICATE_UNRESOLVED" in r["pipeline"]["blockers"] for r in out.values()))
        b["pipeline"]["duplicate_of"] = "SOH-TX-900001"
        out = assessed(a, b)
        self.assertEqual(out["SOH-TX-900001"]["pipeline"]["state"], "ELIGIBLE")
        self.assertEqual(out["SOH-TX-900002"]["pipeline"]["rejection_reasons"], ["DUPLICATE_REPORT"])

    def test_repeat_sales_are_separate_once_linked(self):
        a = record("SOH-TX-900001", "repeat.com", 3000, "2019-06-01")
        b = record("SOH-TX-900002", "repeat.com", 9000, "2024-02-10")
        self.assertEqual(sp.find_relationships([a, b])[0][2], "REPEAT_SALE")
        self.assertIn("DUPLICATE_UNRESOLVED", assessed(a, b)["SOH-TX-900002"]["pipeline"]["blockers"])
        b["pipeline"]["repeat_sale_of"] = ["SOH-TX-900001"]
        self.assertEqual({r["pipeline"]["state"] for r in assessed(a, b).values()}, {"ELIGIBLE"})

    def test_adjacent_years_are_ambiguous(self):
        a = record("SOH-TX-900001", "late.com", 3000, "2023", sale_date_precision="YEAR")
        b = record("SOH-TX-900002", "late.com", 3000, "2024", sale_date_precision="YEAR")
        self.assertEqual(sp.find_relationships([a, b])[0][2], "AMBIGUOUS")

    def test_shared_passage_and_amount_flags_bundle(self):
        a = record("SOH-TX-900001", "alpha.com", 12000)
        b = record("SOH-TX-900002", "beta.com", 12000)
        b["source_url"], b["document_locator"] = a["source_url"], a["document_locator"]
        out = assessed(a, b)
        self.assertTrue(all("BUNDLE_SUSPECTED" in r["pipeline"]["blockers"] for r in out.values()))


class Validation(unittest.TestCase):
    def errors(self, records):
        return sp.validate(records, [])

    def test_assessed_records_validate(self):
        self.assertEqual(self.errors(list(assessed(record()).values())), [])

    def test_overstated_state_fails(self):
        r = record()
        r["rights"]["storage"] = dict(RIGHT_UNKNOWN)
        r = sp.assess_all([r])[0]
        r["pipeline"]["state"], r["pipeline"]["blockers"] = "ELIGIBLE", []
        self.assertTrue(any("evidence supports SOURCE_REVIEWED" in e for e in self.errors([r])))

    def test_admission_is_closed(self):
        r = sp.assess_all([record()])[0]
        r["pipeline"]["state"] = "CALIBRATION_ADMITTED"
        r["pipeline"]["second_review"] = {"reviewer": "fixture", "at": "2026-10-09"}
        r["pipeline"]["admission"] = {"batch_id": "fixture", "approved_by": "fixture", "decision_ref": "fixture"}
        self.assertTrue(any("admission is closed" in e for e in self.errors([r])))

    def test_holdout_reserved_refused_in_public_files(self):
        r = sp.assess_all([record()])[0]
        r["pipeline"]["state"] = "HOLDOUT_RESERVED"
        self.assertTrue(any("never be stored in the public repository" in e for e in self.errors([r])))

    def test_illegal_transition_fails(self):
        r = sp.assess_all([record()])[0]
        r["pipeline"]["state_history"].append({"state": "CALIBRATION_ADMITTED", "at": "2026-10-09", "note": "x"})
        self.assertTrue(any("illegal transition" in e for e in self.errors([r])))

    def test_engine_labels_cannot_be_naming_class(self):
        r = sp.assess_all([record(naming_class="brandable", naming_class_basis="ENGINE")])[0]
        self.assertTrue(any("naming_class" in e for e in self.errors([r])))

    def test_citation_only_rights_cannot_clear_storage(self):
        r = record()
        r["rights"]["storage"] = dict(RIGHT_OK, basis_type="PUBLIC_FACT_CITATION")
        r = sp.assess_all([r])[0]
        self.assertTrue(any("public accessibility or citation alone" in e for e in self.errors([r])))


class Pilot(unittest.TestCase):
    def test_pilot_is_valid_and_has_no_eligible_records(self):
        records = sp.pilot_records()
        self.assertEqual(sp.validate(records, []), [])
        q = sp.quality_report(records, {"record_count": None})
        self.assertEqual(q["records"], 49)
        self.assertEqual(q["funnel"]["directly_reviewed"], 29)
        self.assertEqual(q["funnel"]["rights_cleared"], 0)
        self.assertEqual(q["funnel"]["calibration_eligible"], 0)

    def test_pilot_does_not_modify_registry_records(self):
        before = copy.deepcopy(sp.reg.load(sp.reg.REGISTRY_PATH))
        sp.pilot_records()
        self.assertEqual(before, sp.reg.load(sp.reg.REGISTRY_PATH))

    def test_committed_quality_report_is_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "sales_pipeline.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class EngineBiasBaseline(unittest.TestCase):
    def test_committed_baseline_matches_engine(self):
        committed = json.loads((ROOT / "research" / "valuation-evidence" / "sprint-1b" /
                                "engine-bias-baseline.v1.json").read_text(encoding="utf-8"))
        result = subprocess.run(["node", str(ROOT / "scripts" / "assess_comparable_selection.mjs"), "--json", "-"],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        fresh = json.loads(result.stdout[result.stdout.index("{"):])
        self.assertEqual(committed, fresh)


if __name__ == "__main__":
    unittest.main()
