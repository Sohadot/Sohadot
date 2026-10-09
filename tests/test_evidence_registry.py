#!/usr/bin/env python3
"""Sprint 1A tests: Transaction Evidence Registry v1 (research only).

Run: python3 -m unittest discover -s tests -v

All synthetic records use reserved example domains and invented-for-test
values; they are fixtures, not market data.
"""
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reg = load_module("validate_evidence_registry")
render = load_module("render_seed_investigation")

AS_OF = date(2026, 10, 9)


def verified_fixture(tid="SOH-TX-900001", domain="example-alpha.com", sale_date="2020-03-15"):
    return {
        "transaction_id": tid, "domain": domain, "sale_price": 25000, "currency": "USD",
        "sale_date": sale_date, "sale_date_precision": "DAY", "report_date": "2020-04",
        "venue": "PRIVATE", "transaction_type": "DOMAIN_ONLY", "consideration_type": "CASH",
        "market_side": "END_USER_ACQUISITION", "source_name": "Example Corp Form 10-Q (fixture)",
        "source_url": "https://example.invalid/filing", "source_type": "REGULATORY_FILING",
        "source_access_method": "DOCUMENT_REVIEWED", "source_accessed_at": "2026-10-01",
        "additional_sources": [], "price_disclosure_status": "EXACT", "price_claims": [], "conflicts": [],
        "evidence_status": "VERIFIED", "verified_at": "2026-10-01",
        "verification_basis": "Fixture: filing note states the domain was purchased for $25,000 in cash on 2020-03-15.",
        "rights_status": "PUBLIC_RECORD", "rights_basis": "Fixture: regulatory filing, facts cited with attribution.",
        "rights_license": None, "calibration_role": "REFERENCE_ONLY", "notes": "Synthetic fixture.",
    }


def reported_fixture(**overrides):
    t = verified_fixture()
    t.update(source_type="TRADE_PUBLICATION", source_access_method="SEARCH_INDEX_ONLY",
             evidence_status="REPORTED", verified_at=None, verification_basis=None,
             rights_status="PUBLIC_VIEW_CITATION_ONLY",
             rights_basis="Fixture: public article; facts cited with attribution only.")
    t.update(overrides)
    return t


def registry_of(*txs):
    r = {"schema_version": reg.SCHEMA_VERSION, "registry_version": "test", "as_of": "2026-10-09",
         "dataset_status": reg.DATASET_STATUS, "transactions": list(txs)}
    header = reg.check_registry(r, [], AS_OF)
    r.update(header)
    return r


def errors_for(*txs, mutate_header=None):
    r = registry_of(*txs)
    if mutate_header:
        mutate_header(r)
    errors = []
    reg.check_registry(r, errors, AS_OF)
    return errors


def joined(errors):
    return "\n".join(errors)


class SchemaValidity(unittest.TestCase):
    def test_fixture_is_valid(self):
        self.assertEqual(errors_for(verified_fixture()), [])
        self.assertEqual(errors_for(reported_fixture()), [])

    def test_missing_and_malformed_ids(self):
        t = verified_fixture()
        del t["transaction_id"]
        self.assertIn("missing field", joined(errors_for(t)))
        self.assertIn("SOH-TX-NNNNNN", joined(errors_for(verified_fixture(tid="TX-1"))))

    def test_invalid_values(self):
        cases = {
            "domain": ("not a domain", "invalid domain"),
            "sale_price": (-5, "positive integer"),
            "currency": ("XYZ", "currency"),
            "venue": ("SOMEWHERE", "venue"),
            "evidence_status": ("CONFIRMED", "evidence_status"),
        }
        for field, (value, message) in cases.items():
            t = verified_fixture()
            t[field] = value
            self.assertIn(message, joined(errors_for(t)), field)

    def test_impossible_and_inconsistent_dates(self):
        self.assertIn("outside", joined(errors_for(verified_fixture(sale_date="2030-01-01"))))
        self.assertIn("outside", joined(errors_for(verified_fixture(sale_date="1970-01-01"))))
        self.assertIn("does not match precision", joined(errors_for(verified_fixture(sale_date="2020-02-31"))))
        t = verified_fixture()
        t["sale_date_precision"] = "YEAR"
        self.assertIn("does not match precision", joined(errors_for(t)))
        t = verified_fixture()
        t["report_date"] = "2019-12"
        self.assertIn("precedes sale_date", joined(errors_for(t)))

    def test_undisclosed_price_cannot_carry_a_number(self):
        t = reported_fixture(price_disclosure_status="UNDISCLOSED")
        self.assertIn("sale_price null", joined(errors_for(t)))


class EvidenceBoundaries(unittest.TestCase):
    def test_a_url_alone_never_verifies(self):
        t = verified_fixture()
        t.update(source_type="TRADE_PUBLICATION")
        self.assertIn("not primary evidence", joined(errors_for(t)))

    def test_primary_source_must_be_reviewed(self):
        t = verified_fixture()
        t["source_access_method"] = "SEARCH_INDEX_ONLY"
        self.assertIn("primary document not reviewed", joined(errors_for(t)))

    def test_verified_needs_basis_and_exact_price(self):
        t = verified_fixture()
        t["verification_basis"] = None
        self.assertIn("verification_basis", joined(errors_for(t)))
        t = verified_fixture()
        t["price_disclosure_status"] = "APPROXIMATE"
        self.assertIn("not verifiable", joined(errors_for(t)))

    def test_conflicting_sources(self):
        conflict = [{"field": "sale_price", "description": "Two outlets disagree.", "material": True}]
        t = verified_fixture()
        t["conflicts"] = conflict
        self.assertIn("material conflicts are unresolved", joined(errors_for(t)))
        self.assertIn("must be DISPUTED", joined(errors_for(reported_fixture(conflicts=conflict))))
        self.assertIn("requires at least one material conflict", joined(errors_for(reported_fixture(evidence_status="DISPUTED"))))
        self.assertEqual(errors_for(reported_fixture(evidence_status="DISPUTED", conflicts=conflict)), [])

    def test_reported_requires_a_source(self):
        t = reported_fixture(source_url=None, source_name=None, source_type="NONE", source_access_method="NOT_ACCESSED")
        self.assertIn("REPORTED requires a cited source", joined(errors_for(t)))

    def test_verified_at_only_on_verified_records(self):
        self.assertIn("verified_at set", joined(errors_for(reported_fixture(verified_at="2026-10-01"))))


class DatasetVerificationBoundary(unittest.TestCase):
    def test_header_cannot_claim_dataset_verification(self):
        e = errors_for(verified_fixture(), mutate_header=lambda r: r.update(dataset_verified=True))
        self.assertIn("dataset-level verification", joined(e))
        e = errors_for(verified_fixture(), mutate_header=lambda r: r.update(dataset_status="VERIFIED"))
        self.assertIn("dataset_status", joined(e))

    def test_partially_verified_dataset_is_not_verified(self):
        r = registry_of(verified_fixture(), reported_fixture(transaction_id="SOH-TX-900002", sale_date="2021-01-02", report_date="2021-02"))
        self.assertEqual(r["dataset_status"], reg.DATASET_STATUS)
        self.assertEqual(r["status_counts"]["VERIFIED"], 1)

    def test_header_counts_and_hash_must_match(self):
        e = errors_for(verified_fixture(), mutate_header=lambda r: r["status_counts"].update(VERIFIED=99))
        self.assertIn("status_counts", joined(e))
        e = errors_for(verified_fixture(), mutate_header=lambda r: r.update(content_sha256="0" * 64))
        self.assertIn("content_sha256", joined(e))


class RightsClassification(unittest.TestCase):
    def test_licence_must_be_named(self):
        t = verified_fixture()
        t["rights_status"] = "LICENSED_REUSE"
        self.assertIn("rights_license", joined(errors_for(t)))

    def test_basis_required(self):
        t = verified_fixture()
        t["rights_basis"] = ""
        self.assertIn("rights_basis", joined(errors_for(t)))

    def test_public_record_only_for_official_records(self):
        t = reported_fixture(rights_status="PUBLIC_RECORD")
        self.assertIn("PUBLIC_RECORD rights", joined(errors_for(t)))


class RolesAndIsolation(unittest.TestCase):
    def test_status_does_not_assign_a_role(self):
        # A verified landmark sale may stay reference-only; that is valid.
        self.assertEqual(errors_for(verified_fixture()), [])

    def test_calibration_candidate_preconditions(self):
        t = reported_fixture(evidence_status="UNVERIFIED", source_type="NONE", source_url=None, source_name=None,
                             source_access_method="NOT_ACCESSED", calibration_role="CALIBRATION_CANDIDATE")
        self.assertIn("evidence UNVERIFIED", joined(errors_for(t)))
        t = verified_fixture()
        t.update(transaction_type="WEBSITE_BUSINESS", calibration_role="CALIBRATION_CANDIDATE")
        self.assertIn("transaction_type WEBSITE_BUSINESS", joined(errors_for(t)))
        t = reported_fixture(rights_status="RESTRICTED_OR_UNKNOWN", calibration_role="CALIBRATION_CANDIDATE")
        self.assertIn("rights RESTRICTED_OR_UNKNOWN", joined(errors_for(t)))
        t = verified_fixture()
        t["calibration_role"] = "CALIBRATION_CANDIDATE"
        self.assertEqual(errors_for(t), [])

    def test_holdout_records_never_in_public_registry(self):
        t = verified_fixture()
        t["calibration_role"] = "HOLDOUT_CANDIDATE"
        self.assertIn("must not be stored in the public registry", joined(errors_for(t)))

    def test_holdout_overlap_by_domain_and_second_level_name(self):
        cal = verified_fixture()
        cal["calibration_role"] = "CALIBRATION_CANDIDATE"
        r = registry_of(cal)
        status = {"protocol_version": "holdout-protocol/v1", "status": "FROZEN", "frozen_at": "2026-10-09",
                  "manifest_sha256": "a" * 64, "record_count": 2, "storage_location": "private store (fixture)"}
        manifest = {"transactions": [
            {"transaction_id": "SOH-TX-900001", "domain": "example-alpha.com"},
            {"transaction_id": "H-2", "domain": "example-alpha.net"},
            {"transaction_id": "H-3", "domain": "example-beta.org"},
        ]}
        errors = []
        reg.check_holdout(status, r, errors, manifest)
        text = joined(errors)
        self.assertIn("also a calibration candidate", text)
        self.assertIn("overlaps a calibration domain", text)
        self.assertIn("shares a second-level name", text)
        self.assertNotIn("example-beta.org", text)

    def test_holdout_status_rules(self):
        errors = []
        reg.check_holdout({"protocol_version": "v1", "status": "NOT_READY", "manifest_sha256": "a" * 64}, {}, errors)
        self.assertIn("must be null while NOT_READY", joined(errors))
        errors = []
        reg.check_holdout({"protocol_version": "v1", "status": "FROZEN"}, {}, errors)
        self.assertIn("FROZEN requires", joined(errors))
        errors = []
        reg.check_holdout({"protocol_version": "v1", "status": "READY_SOON"}, {}, errors)
        self.assertIn("status must be one of", joined(errors))


class TransactionIdentity(unittest.TestCase):
    def test_duplicate_ids_rejected(self):
        a, b = verified_fixture(), verified_fixture(sale_date="2021-05-01")
        b["report_date"] = "2021-06"
        self.assertIn("duplicate transaction_id", joined(errors_for(a, b)))

    def test_repeat_sales_are_separate_transactions(self):
        a = verified_fixture()
        b = verified_fixture(tid="SOH-TX-900002", sale_date="2023-07-01")
        b["report_date"] = "2023-08"
        b["sale_price"] = 90000
        self.assertEqual(errors_for(a, b), [])

    def test_same_sale_recorded_twice_is_rejected(self):
        a = verified_fixture()
        b = verified_fixture(tid="SOH-TX-900002")
        self.assertIn("duplicates another transaction", joined(errors_for(a, b)))

    def test_repeat_sale_calibration_candidates_need_distinct_dates(self):
        a = verified_fixture()
        b = verified_fixture(tid="SOH-TX-900002")
        b["sale_price"] = 30000
        for t in (a, b):
            t["calibration_role"] = "CALIBRATION_CANDIDATE"
        self.assertIn("distinct sale dates", joined(errors_for(a, b)))


class PublishedResearchFiles(unittest.TestCase):
    def test_validator_passes_on_committed_files(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_evidence_registry.py"), "--as-of", "2026-10-09"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_seed_sale_is_investigated(self):
        seed = json.loads((ROOT / "data" / "valuation_comps_seed.json").read_text())
        inv = json.loads(reg.INVESTIGATION_PATH.read_text())
        self.assertEqual(len(inv["records"]), len(seed["sales"]))
        errors = []
        broken = copy.deepcopy(inv)
        broken["records"].pop()
        reg.check_investigation(broken, json.loads(reg.REGISTRY_PATH.read_text()), seed, errors)
        self.assertIn("exactly one record per seed sale", joined(errors))

    def test_no_calibration_or_holdout_records_yet(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        self.assertEqual(r["role_counts"]["CALIBRATION_CANDIDATE"], 0)
        self.assertEqual(r["role_counts"]["HOLDOUT_CANDIDATE"], 0)
        status = json.loads(reg.HOLDOUT_STATUS_PATH.read_text())
        self.assertEqual(status["status"], "NOT_READY")

    def test_verified_records_are_primary_and_reviewed(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        for t in r["transactions"]:
            if t["evidence_status"] == "VERIFIED":
                self.assertIn(t["source_type"], reg.PRIMARY_SOURCE_TYPES)
                self.assertEqual(t["source_access_method"], "DOCUMENT_REVIEWED")

    def test_production_does_not_read_research_files(self):
        errors = []
        reg.check_public_boundary(errors)
        self.assertEqual(errors, [])

    def test_processing_is_deterministic(self):
        for path in (reg.REGISTRY_PATH, reg.INVESTIGATION_PATH, reg.HOLDOUT_STATUS_PATH):
            payload = json.loads(path.read_text())
            self.assertEqual(reg.canonical(payload), path.read_text())
        r = json.loads(reg.REGISTRY_PATH.read_text())
        self.assertEqual(reg.content_hash(r["transactions"]), r["content_sha256"])
        inv = json.loads(reg.INVESTIGATION_PATH.read_text())
        self.assertEqual(render.render(r, inv), render.render(r, inv))
        self.assertEqual(render.render(r, inv), render.OUTPUT_PATH.read_text())

    def test_sprint0_dataset_rule_still_enforced(self):
        comps = json.loads((ROOT / "data" / "valuation_comps.json").read_text())
        self.assertEqual(comps["source_verification"]["status"], "not_verified")
        self.assertIsNone(comps["source_verification"]["last_verified"])


if __name__ == "__main__":
    unittest.main()
