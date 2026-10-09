#!/usr/bin/env python3
"""Sprint 1A tests: Transaction Evidence Registry v1 (research only).

Run: python3 -m unittest discover -s tests -v

Synthetic records use reserved example domains and invented-for-test values;
they are fixtures, not market data. Holdout manifests are written only to
temporary directories outside the repository.
"""
import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
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
SHA = "a" * 64


def no_rights(what="this use"):
    return {"status": "NOT_ESTABLISHED", "basis_type": "NONE", "basis": f"Fixture: no basis recorded for {what}.", "reference": None}


def rights(storage=None, modelling=None):
    return {
        "citation": {"status": "PERMITTED_WITH_CONDITIONS", "basis_type": "PUBLIC_RECORD",
                     "basis": "Fixture: filing facts cited with attribution.", "reference": None},
        "storage": storage or no_rights("storage"),
        "commercial_modelling": modelling or no_rights("modelling"),
        "redistribution": no_rights("redistribution"),
    }


def granted(basis_type="WRITTEN_PERMISSION", reference="Fixture permission letter #1"):
    return {"status": "PERMITTED", "basis_type": basis_type, "basis": "Fixture: permission recorded for this use.", "reference": reference}


def verified_fixture(tid="SOH-TX-900001", domain="example-alpha.com", sale_date="2020-03-15"):
    return {
        "transaction_id": tid, "domain": domain, "sale_price": 25000, "currency": "USD",
        "price_scope": "SINGLE_DOMAIN", "bundle": None,
        "sale_date": sale_date, "sale_date_precision": "DAY", "report_date": "2020-04",
        "venue": "PRIVATE", "transaction_type": "DOMAIN_ONLY", "consideration_type": "CASH",
        "market_side": "END_USER_ACQUISITION", "source_name": "Example Corp Form 10-Q (fixture)",
        "source_url": "https://example.invalid/filing", "source_type": "REGULATORY_FILING",
        "source_access_method": "DOCUMENT_REVIEWED", "source_accessed_at": "2026-10-01",
        "review_method": "RAW_TEXT_CHECKED", "document_locator": "Note 7, Intangible assets",
        "checked_quote": "On March 15, 2020 we purchased example-alpha.com for $25,000 in cash.",
        "document_sha256": SHA, "additional_sources": [], "leads": [],
        "price_disclosure_status": "EXACT", "price_claims": [], "conflicts": [], "valuation_caveats": [],
        "evidence_status": "VERIFIED", "verified_at": "2026-10-01",
        "verification_basis": "Fixture: filing note, read in raw text, states the domain was purchased for $25,000 in cash.",
        "attesting_party": "BUYER", "settlement_evidence": "REGULATED_FILING_OR_COURT_RECORD",
        "rights": rights(), "calibration_role": "REFERENCE_ONLY", "notes": "Synthetic fixture.",
    }


def reported_fixture(**overrides):
    t = verified_fixture()
    t.update(source_type="TRADE_PUBLICATION", evidence_status="REPORTED", verified_at=None, verification_basis=None,
             attesting_party="NONE", settlement_evidence="NOT_ESTABLISHED")
    t["rights"]["citation"] = {"status": "PERMITTED_WITH_CONDITIONS", "basis_type": "PUBLIC_FACT_CITATION",
                               "basis": "Fixture: facts cited with attribution only.", "reference": None}
    t.update(overrides)
    return t


def unverified_fixture(**overrides):
    t = verified_fixture()
    t.update(source_name=None, source_url=None, source_type="NONE", source_access_method="NOT_ACCESSED",
             source_accessed_at=None, review_method="NONE", document_locator=None, checked_quote=None,
             document_sha256=None, evidence_status="UNVERIFIED", verified_at=None, verification_basis=None,
             attesting_party="NONE", settlement_evidence="NOT_ESTABLISHED",
             sale_price=None, price_disclosure_status="UNKNOWN", calibration_role="UNDETERMINED")
    t.update(overrides)
    return t


def calibration_ready(tid="SOH-TX-900001", domain="example-alpha.com", **overrides):
    t = verified_fixture(tid=tid, domain=domain)
    t["rights"] = rights(storage=granted(), modelling=granted())
    t["calibration_role"] = "CALIBRATION_CANDIDATE"
    t.update(overrides)
    return t


def registry_of(*txs):
    r = {"schema_version": reg.SCHEMA_VERSION, "registry_version": "test", "as_of": "2026-10-09",
         "dataset_status": reg.DATASET_STATUS, "transactions": list(txs)}
    r.update(reg.check_registry(r, [], AS_OF))
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
    def test_fixtures_are_valid(self):
        for t in (verified_fixture(), reported_fixture(), unverified_fixture(), calibration_ready()):
            self.assertEqual(errors_for(t), [], t["evidence_status"])

    def test_missing_and_malformed_ids(self):
        t = verified_fixture()
        del t["transaction_id"]
        self.assertIn("missing field", joined(errors_for(t)))
        self.assertIn("SOH-TX-NNNNNN", joined(errors_for(verified_fixture(tid="TX-1"))))

    def test_invalid_values(self):
        cases = {"domain": ("not a domain", "invalid domain"), "sale_price": (-5, "positive integer"),
                 "currency": ("XYZ", "currency"), "venue": ("SOMEWHERE", "venue"),
                 "evidence_status": ("CONFIRMED", "evidence_status")}
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

    def test_same_month_report_before_sale(self):
        t = verified_fixture()
        t["report_date"] = "2020-03-01"
        self.assertIn("precedes sale_date", joined(errors_for(t)))
        t["report_date"] = "2020-03"
        self.assertEqual(errors_for(t), [])  # month precision cannot prove an earlier day
        t["report_date"] = "2020-03-15"
        self.assertEqual(errors_for(t), [])

    def test_undisclosed_price_cannot_carry_a_number(self):
        self.assertIn("sale_price null", joined(errors_for(reported_fixture(price_disclosure_status="UNDISCLOSED"))))


class VerifiedProvenance(unittest.TestCase):
    def assert_rejected(self, message, **changes):
        t = verified_fixture()
        t.update(changes)
        self.assertIn(message, joined(errors_for(t)))

    def test_missing_source_url(self):
        self.assert_rejected("non-empty https URL", source_url=None)
        self.assert_rejected("non-empty https URL", source_url="")
        self.assert_rejected("non-empty https URL", source_url="http://example.invalid/filing")

    def test_missing_access_date(self):
        self.assert_rejected("source_accessed_at", source_accessed_at=None)

    def test_missing_locator_quote_or_hash(self):
        self.assert_rejected("document_locator", document_locator="")
        self.assert_rejected("checked_quote", checked_quote=None)
        self.assert_rejected("document_sha256", document_sha256="abc")

    def test_unchecked_tool_extraction_is_not_review(self):
        self.assert_rejected("not checked against the source text", review_method="TOOL_EXTRACT_UNCHECKED")
        self.assert_rejected("not checked against the source text", review_method="NONE")
        t = verified_fixture()
        t["review_method"] = "TOOL_EXTRACT_CHECKED_AGAINST_RAW"
        self.assertEqual(errors_for(t), [])

    def test_quote_must_name_domain_and_figure(self):
        self.assert_rejected("checked_quote must name the domain",
                             checked_quote="Trust me, the price is right and it was a good deal overall.")

    def test_party_announcement_is_attestation_not_settlement(self):
        base = dict(source_type="PARTY_ANNOUNCEMENT", attesting_party="BROKER", settlement_evidence="PARTY_ATTESTATION_ONLY",
                    verification_basis="Broker attestation, not independently confirmed settlement: release states the price.")
        t = verified_fixture()
        t.update(base)
        self.assertEqual(errors_for(t), [])
        t = verified_fixture()
        t.update(base, settlement_evidence="REGULATED_FILING_OR_COURT_RECORD")
        self.assertIn("PARTY_ATTESTATION_ONLY", joined(errors_for(t)))
        t = verified_fixture()
        t.update(base, verification_basis="Release states the price and the buyer, which we read in raw text.")
        self.assertIn("must state that the evidence is a party attestation", joined(errors_for(t)))
        t = verified_fixture()
        t.update(attesting_party="BROKER")
        self.assertIn("REGULATED_FILING_OR_COURT_RECORD", joined(errors_for(t)))
        self.assertIn("only VERIFIED records carry", joined(errors_for(reported_fixture(attesting_party="BROKER"))))

    def test_a_url_alone_never_verifies(self):
        self.assert_rejected("not primary evidence", source_type="TRADE_PUBLICATION")

    def test_search_index_access_is_not_a_source(self):
        self.assert_rejected("DOCUMENT_REVIEWED", source_access_method="SEARCH_INDEX_ONLY")

    def test_verified_needs_basis_and_verifiable_price(self):
        self.assert_rejected("verification_basis", verification_basis=None)
        self.assert_rejected("not verifiable", price_disclosure_status="APPROXIMATE")


class ReportedEvidence(unittest.TestCase):
    def test_unsupported_source_classes(self):
        for stype in ("TERTIARY_REFERENCE", "AGGREGATOR_DATABASE"):
            self.assertIn("reportable class", joined(errors_for(reported_fixture(source_type=stype))), stype)

    def test_search_leads_cannot_make_a_record_reported(self):
        t = reported_fixture(source_access_method="NOT_ACCESSED", review_method="NONE", checked_quote=None)
        self.assertIn("DOCUMENT_REVIEWED", joined(errors_for(t)))

    def test_unverified_keeps_leads_without_a_principal_source(self):
        lead = {"source_name": "Some blog", "source_url": "https://example.invalid/post", "source_type": "TRADE_PUBLICATION",
                "observed_at": "2026-10-09", "note": "Search summary only."}
        self.assertEqual(errors_for(unverified_fixture(leads=[lead])), [])
        self.assertIn("carry no principal source", joined(errors_for(unverified_fixture(source_type="TRADE_PUBLICATION",
                                                                                         source_name="x", source_url="https://example.invalid"))))
        bad = dict(lead)
        del bad["note"]
        self.assertIn("leads[0]", joined(errors_for(unverified_fixture(leads=[bad]))))

    def test_conflicts_and_caveats(self):
        conflict = [{"field": "sale_price", "description": "Two outlets disagree.", "material": True}]
        t = verified_fixture()
        t["conflicts"] = conflict
        self.assertIn("material conflicts are unresolved", joined(errors_for(t)))
        self.assertIn("must be DISPUTED", joined(errors_for(reported_fixture(conflicts=conflict))))
        self.assertIn("at least one material conflict", joined(errors_for(reported_fixture(evidence_status="DISPUTED"))))
        self.assertEqual(errors_for(reported_fixture(evidence_status="DISPUTED", conflicts=conflict)), [])
        # Valuation caveats never change the evidence status.
        t = verified_fixture()
        t["valuation_caveats"] = ["Economic value disputed by commentators."]
        self.assertEqual(errors_for(t), [])

    def test_verified_at_only_on_verified_records(self):
        self.assertIn("verified_at set", joined(errors_for(reported_fixture(verified_at="2026-10-01"))))


class BundlesAndScope(unittest.TestCase):
    def bundle_fixture(self, **changes):
        t = verified_fixture()
        t.update(transaction_type="MULTIPLE_DOMAINS", price_scope="BUNDLE_TOTAL",
                 bundle={"domain_count": 24, "other_assets": ["one trademark"], "allocation": "NOT_ALLOCATED"})
        t.update(changes)
        return t

    def test_bundle_is_valid_but_never_single_domain(self):
        self.assertEqual(errors_for(self.bundle_fixture()), [])
        self.assertIn("inconsistent with transaction_type", joined(errors_for(self.bundle_fixture(price_scope="SINGLE_DOMAIN", bundle=None))))
        self.assertIn("NOT_ALLOCATED", joined(errors_for(self.bundle_fixture(bundle={"domain_count": 24, "other_assets": [], "allocation": "ALLOCATED"}))))
        self.assertIn("BUNDLE_TOTAL needs bundle", joined(errors_for(self.bundle_fixture(bundle=None))))

    def test_bundle_cannot_be_calibration(self):
        t = self.bundle_fixture()
        t["rights"] = rights(storage=granted(), modelling=granted())
        t["calibration_role"] = "CALIBRATION_CANDIDATE"
        self.assertIn("price_scope BUNDLE_TOTAL", joined(errors_for(t)))

    def test_business_acquisitions_are_business_totals(self):
        t = verified_fixture()
        t.update(transaction_type="WEBSITE_BUSINESS")
        self.assertIn("inconsistent", joined(errors_for(t)))
        t["price_scope"] = "BUSINESS_TOTAL"
        self.assertEqual(errors_for(t), [])


class RightsSeparation(unittest.TestCase):
    def test_all_four_rights_required(self):
        t = verified_fixture()
        del t["rights"]["redistribution"]
        self.assertIn("exactly citation, storage", joined(errors_for(t)))

    def test_public_visibility_never_grants_storage_or_modelling(self):
        t = verified_fixture()
        t["rights"]["storage"] = granted(basis_type="PUBLIC_FACT_CITATION", reference=None)
        self.assertIn("cannot be granted on public accessibility", joined(errors_for(t)))

    def test_granted_rights_need_basis_and_reference(self):
        t = verified_fixture()
        t["rights"]["commercial_modelling"] = granted(basis_type="NONE", reference=None)
        self.assertIn("granted without a basis", joined(errors_for(t)))
        t = verified_fixture()
        t["rights"]["storage"] = granted(basis_type="LICENSE", reference=None)
        self.assertIn("needs a reference", joined(errors_for(t)))

    def test_documented_lawful_basis_can_qualify(self):
        t = calibration_ready()
        t["rights"]["storage"] = granted(basis_type="DOCUMENTED_LAWFUL_BASIS", reference="Fixture legal note 2026-01")
        self.assertEqual(errors_for(t), [])

    def test_unknown_rights_block_calibration(self):
        t = verified_fixture()
        t["calibration_role"] = "CALIBRATION_CANDIDATE"
        text = joined(errors_for(t))
        self.assertIn("storage rights NOT_ESTABLISHED", text)
        self.assertIn("commercial_modelling rights NOT_ESTABLISHED", text)


class RolesAndIdentity(unittest.TestCase):
    def test_status_does_not_assign_a_role(self):
        self.assertEqual(errors_for(verified_fixture()), [])

    def test_calibration_preconditions(self):
        self.assertEqual(errors_for(calibration_ready()), [])
        self.assertIn("evidence UNVERIFIED", joined(errors_for(unverified_fixture(calibration_role="CALIBRATION_CANDIDATE"))))
        self.assertIn("consideration CASH_AND_STOCK", joined(errors_for(calibration_ready(consideration_type="CASH_AND_STOCK"))))

    def test_holdout_records_never_in_public_registry(self):
        self.assertIn("must not be stored in the public registry", joined(errors_for(verified_fixture() | {"calibration_role": "HOLDOUT_CANDIDATE"})))

    def test_duplicate_ids_and_duplicate_sales(self):
        b = verified_fixture(sale_date="2021-05-01")
        b["report_date"] = "2021-06"
        self.assertIn("duplicate transaction_id", joined(errors_for(verified_fixture(), b)))
        self.assertIn("duplicates another transaction", joined(errors_for(verified_fixture(), verified_fixture(tid="SOH-TX-900002"))))

    def test_repeat_sales_are_separate_transactions(self):
        b = verified_fixture(tid="SOH-TX-900002", sale_date="2023-07-01")
        b.update(report_date="2023-08", sale_price=90000)
        self.assertEqual(errors_for(verified_fixture(), b), [])
        a, c = calibration_ready(), calibration_ready(tid="SOH-TX-900002")
        c["sale_price"] = 30000
        self.assertIn("distinct sale dates", joined(errors_for(a, c)))


class DatasetBoundary(unittest.TestCase):
    def test_header_cannot_claim_dataset_verification(self):
        self.assertIn("dataset-level verification", joined(errors_for(verified_fixture(), mutate_header=lambda r: r.update(dataset_verified=True))))
        self.assertIn("dataset_status", joined(errors_for(verified_fixture(), mutate_header=lambda r: r.update(dataset_status="VERIFIED"))))

    def test_header_counts_and_hash_must_match(self):
        self.assertIn("status_counts", joined(errors_for(verified_fixture(), mutate_header=lambda r: r["status_counts"].update(VERIFIED=99))))
        self.assertIn("content_sha256", joined(errors_for(verified_fixture(), mutate_header=lambda r: r.update(content_sha256="0" * 64))))


def holdout_record(i, domain=None, source="Holdout source {k}"):
    domain = domain or f"holdout-example-{i}.org"
    t = calibration_ready(tid=f"SOH-TX-5{i:05d}", domain=domain)
    t["checked_quote"] = f"Fixture: {domain} was purchased for $25,000 in cash."
    t["source_name"] = source.format(k=i % 10)
    t["calibration_role"] = "HOLDOUT_CANDIDATE"
    return t


def manifest_of(records):
    return {"kind": reg.MANIFEST_KIND, "protocol_version": reg.HOLDOUT_PROTOCOL_VERSION, "transactions": records}


def frozen_status(manifest, **changes):
    s = {"protocol_version": reg.HOLDOUT_PROTOCOL_VERSION, "status": "FROZEN", "frozen_at": "2026-10-01",
         "manifest_sha256": reg.content_hash(manifest), "record_count": len(manifest["transactions"]),
         "storage_location": "Private encrypted store held by the evaluator (fixture)", "controls": reg.HOLDOUT_CONTROLS,
         "readiness_gate": reg.readiness_gate()}
    s.update(changes)
    return s


class HoldoutFailClosed(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(reg.REGISTRY_PATH.read_text())
        self.seed = json.loads(reg.SEED_PATH.read_text())
        self.comps = json.loads(reg.COMPS_PATH.read_text())
        self.manifest = manifest_of([holdout_record(i) for i in range(160)])

    def run_check(self, status, manifest=None, path="/tmp/outside-repo/manifest.json"):
        errors = []
        reg.check_holdout(status, self.registry, errors, manifest, path, self.seed, self.comps, AS_OF)
        return joined(errors)

    def all_enforced(self):
        return {k: "ENFORCED" for k in reg.HOLDOUT_CONTROLS}

    def test_valid_manifest_still_blocked_by_readiness_gate(self):
        text = self.run_check(frozen_status(self.manifest), self.manifest)
        self.assertIn("FROZEN is not permitted while mandatory controls are NOT_IMPLEMENTED", text)
        for control in reg.readiness_gate()["blocking_controls"]:
            self.assertIn(control, text)

    def test_valid_private_manifest_passes_once_all_controls_exist(self):
        original = reg.HOLDOUT_CONTROLS
        reg.HOLDOUT_CONTROLS = self.all_enforced()
        try:
            status = frozen_status(self.manifest, controls=reg.HOLDOUT_CONTROLS, readiness_gate=reg.readiness_gate())
            self.assertEqual(self.run_check(status, self.manifest), "")
        finally:
            reg.HOLDOUT_CONTROLS = original

    def test_readiness_gate_cannot_be_edited_open(self):
        status = json.loads(reg.HOLDOUT_STATUS_PATH.read_text())
        self.assertFalse(status["readiness_gate"]["frozen_permitted"])
        forged = copy.deepcopy(status)
        forged["readiness_gate"] = {"frozen_permitted": True, "blocking_controls": []}
        self.assertIn("readiness_gate must be", self.run_check(forged))
        self.assertEqual(reg.readiness_gate({"a": "ENFORCED", "b": "NOT_IMPLEMENTED"}),
                         {"frozen_permitted": False, "blocking_controls": ["b"]})

    def test_frozen_without_manifest_fails_closed(self):
        self.assertIn("fail-closed", self.run_check(frozen_status(self.manifest)))

    def test_false_frozen_metadata(self):
        self.assertIn("64 lowercase hex", self.run_check(frozen_status(self.manifest, manifest_sha256="not-a-hash"), self.manifest))
        for bad in (-3, 0, 5, "160", True):
            self.assertIn("record_count must be an integer", self.run_check(frozen_status(self.manifest, record_count=bad), self.manifest), bad)
        self.assertIn("frozen_at", self.run_check(frozen_status(self.manifest, frozen_at="2099-01-01"), self.manifest))
        self.assertIn("storage_location", self.run_check(frozen_status(self.manifest, storage_location="https://example.invalid/x"), self.manifest))
        self.assertIn("does not match", self.run_check(frozen_status(self.manifest, manifest_sha256="b" * 64), self.manifest))
        self.assertIn("status says 170", self.run_check(frozen_status(self.manifest, record_count=170), self.manifest))

    def test_manifest_inside_repository_rejected(self):
        self.assertIn("outside the repository", self.run_check(frozen_status(self.manifest), self.manifest, path=str(ROOT / "tmp-manifest.json")))

    def test_too_few_records(self):
        small = manifest_of([holdout_record(i) for i in range(20)])
        self.assertIn(">= 150", self.run_check(frozen_status(small), small))

    def test_ineligible_records(self):
        records = [holdout_record(i) for i in range(160)]
        records[0]["rights"]["storage"] = no_rights()
        records[1]["consideration_type"] = "CRYPTOCURRENCY"
        m = manifest_of(records)
        text = self.run_check(frozen_status(m), m)
        self.assertIn("storage rights not established", text)
        self.assertIn("consideration CRYPTOCURRENCY", text)

    def test_source_concentration(self):
        m = manifest_of([holdout_record(i, source="One source") for i in range(160)])
        self.assertIn("more than 25%", self.run_check(frozen_status(m), m))

    def test_overlap_with_seed_registry_repeat_sales_and_variants(self):
        records = [holdout_record(i) for i in range(160)]
        records[0]["domain"] = "voice.com"         # registry + seed (repeat sale)
        records[1]["domain"] = "aluren.net"        # second-level name of a seed sale
        records[2]["domain"] = "Www.Voice.COM."    # normalised variant
        records[3]["domain"] = "stack-scan.io"     # hyphenation variant of stackscan.com
        records[4]["domain"] = "insurance.co"      # second-level name in registry
        m = manifest_of(records)
        text = self.run_check(frozen_status(m), m)
        self.assertIn("voice.com overlaps", text)
        self.assertIn("aluren.net shares second-level name", text)
        self.assertIn("Www.Voice.COM. overlaps", text)
        self.assertIn("hyphenation variant", text)
        self.assertIn("insurance.co shares second-level name", text)

    def test_controls_map_cannot_overclaim(self):
        status = json.loads(reg.HOLDOUT_STATUS_PATH.read_text())
        self.assertEqual(self.run_check(status), "")
        inflated = copy.deepcopy(status)
        inflated["controls"]["chronological_split"] = "ENFORCED"
        self.assertIn("must match the controls implemented", self.run_check(inflated))
        self.assertIn("NOT_IMPLEMENTED", set(status["controls"].values()))

    def test_protocol_document_lists_the_same_controls(self):
        doc = (ROOT / "docs" / "valuation-evidence" / "INDEPENDENT_HOLDOUT_PROTOCOL.md").read_text()
        rows = dict(re.findall(r"^\| `([a-z0-9_]+)` \| (ENFORCED|NOT_IMPLEMENTED) \|$", doc, re.M))
        self.assertEqual(rows, reg.HOLDOUT_CONTROLS)

    def test_not_ready_rules(self):
        status = json.loads(reg.HOLDOUT_STATUS_PATH.read_text())
        self.assertEqual(status["status"], "NOT_READY")
        self.assertIn("must be null while NOT_READY", self.run_check(dict(status, manifest_sha256=SHA)))
        self.assertIn("NOT_READY", self.run_check(status, self.manifest))
        self.assertIn("status must be one of", self.run_check(dict(status, status="READY_SOON")))

    def test_manifest_files_never_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research" / "valuation-evidence" / "holdout").mkdir(parents=True)
            (root / "research" / "valuation-evidence" / "holdout" / "status.v1.json").write_text("{}")
            (root / "notes").mkdir()
            (root / "notes" / "holdout-manifest-2026.json").write_text("{}")
            (root / "notes" / "data.json").write_text(json.dumps({"kind": reg.MANIFEST_KIND}))
            (root / "research" / "valuation-evidence" / "holdout" / "records.json").write_text("{}")
            errors = []
            reg.check_public_boundary(errors, root)
            text = joined(errors)
            self.assertIn("holdout-manifest-2026.json", text)
            self.assertIn("contains a holdout manifest", text)
            self.assertIn("records.json must not be committed", text)


class PublishedResearchFiles(unittest.TestCase):
    def test_validator_passes_on_committed_files(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_evidence_registry.py"), "--as-of", "2026-10-09"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_seed_sale_is_investigated(self):
        seed = json.loads(reg.SEED_PATH.read_text())
        inv = json.loads(reg.INVESTIGATION_PATH.read_text())
        self.assertEqual(len(inv["records"]), len(seed["sales"]))
        broken = copy.deepcopy(inv)
        broken["records"].pop()
        errors = []
        reg.check_investigation(broken, json.loads(reg.REGISTRY_PATH.read_text()), seed, errors)
        self.assertIn("exactly one record per seed sale", joined(errors))

    def test_every_evidence_source_was_reviewed(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        for t in r["transactions"]:
            if t["evidence_status"] != "UNVERIFIED":
                self.assertEqual(t["source_access_method"], "DOCUMENT_REVIEWED", t["transaction_id"])
                self.assertIn(t["review_method"], reg.CHECKED_REVIEW, t["transaction_id"])
            if t["evidence_status"] == "VERIFIED":
                self.assertIn(t["source_type"], reg.PRIMARY_SOURCE_TYPES)

    def test_fund_com_is_a_bundle_and_excluded(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        fund = [t for t in r["transactions"] if t["domain"] == "fund.com" and t["sale_price"] == 9999950]
        self.assertEqual(len(fund), 1)
        t = fund[0]
        self.assertEqual((t["transaction_type"], t["price_scope"], t["bundle"]["domain_count"]), ("MULTIPLE_DOMAINS", "BUNDLE_TOTAL", 24))
        self.assertEqual(t["calibration_role"], "EXCLUDED")
        self.assertIn("f10q0309a1_fund.htm", t["source_url"])

    def test_sex_com_2010_is_a_broker_attested_bundle(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        t = next(t for t in r["transactions"] if t["domain"] == "sex.com" and t["sale_price"] == 13000000)
        self.assertEqual((t["transaction_type"], t["price_scope"], t["sale_date"]), ("DOMAIN_PLUS_ASSETS", "BUNDLE_TOTAL", "2010-11-17"))
        self.assertEqual((t["attesting_party"], t["settlement_evidence"]), ("BROKER", "PARTY_ATTESTATION_ONLY"))
        self.assertIn("trademarks", " ".join(t["bundle"]["other_assets"]))
        self.assertNotEqual(t["calibration_role"], "CALIBRATION_CANDIDATE")

    def test_ai_com_is_broker_attested_and_excluded(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        t = next(t for t in r["transactions"] if t["domain"] == "ai.com" and t["evidence_status"] == "VERIFIED")
        self.assertEqual((t["attesting_party"], t["settlement_evidence"], t["calibration_role"]), ("BROKER", "PARTY_ATTESTATION_ONLY", "EXCLUDED"))
        self.assertEqual((t["sale_date"], t["sale_date_precision"], t["consideration_type"]), ("2025", "YEAR", "CRYPTOCURRENCY"))
        self.assertTrue(t["verification_basis"].startswith("Broker attestation, not independently confirmed settlement"))
        self.assertTrue(any("closing date is unknown" in c for c in t["valuation_caveats"]))

    def test_insurance_com_stays_a_business_acquisition(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        t = next(t for t in r["transactions"] if t["domain"] == "insurance.com")
        self.assertEqual((t["transaction_type"], t["price_scope"], t["consideration_type"]), ("WEBSITE_BUSINESS", "BUSINESS_TOTAL", "CASH_AND_NOTE"))

    def test_no_calibration_rights_established(self):
        r = json.loads(reg.REGISTRY_PATH.read_text())
        self.assertEqual(r["role_counts"]["CALIBRATION_CANDIDATE"], 0)
        for t in r["transactions"]:
            self.assertNotIn(t["rights"]["commercial_modelling"]["status"], reg.GRANTED, t["transaction_id"])

    def test_production_does_not_read_research_files(self):
        errors = []
        reg.check_public_boundary(errors)
        self.assertEqual(errors, [])

    def test_processing_is_deterministic(self):
        for path in (reg.REGISTRY_PATH, reg.INVESTIGATION_PATH, reg.HOLDOUT_STATUS_PATH):
            self.assertEqual(reg.canonical(json.loads(path.read_text())), path.read_text())
        r = json.loads(reg.REGISTRY_PATH.read_text())
        self.assertEqual(reg.content_hash(r["transactions"]), r["content_sha256"])
        inv = json.loads(reg.INVESTIGATION_PATH.read_text())
        self.assertEqual(render.render(r, inv), render.OUTPUT_PATH.read_text())

    def test_sprint0_dataset_rule_still_enforced(self):
        comps = json.loads(reg.COMPS_PATH.read_text())
        self.assertEqual(comps["source_verification"]["status"], "not_verified")
        self.assertIsNone(comps["source_verification"]["last_verified"])


if __name__ == "__main__":
    unittest.main()
