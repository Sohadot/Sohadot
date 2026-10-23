"""Local private valuation vault. Fixtures are synthetic and are not sales."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sales_pipeline as sp  # noqa: E402
import valuation_vault as vault  # noqa: E402

PRODUCTION = (
    ROOT / "js" / "valuation-engine.js",
    ROOT / "data" / "valuation_comps.json",
    ROOT / "data" / "valuation_comps_seed.json",
    ROOT / "research" / "valuation-evidence" / "holdout" / "status.v1.json",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _envelope(record, partition="calibration"):
    return {"partition": partition, "record": record}


def _write_batch(directory: Path, name: str, records) -> Path:
    path = directory / name
    path.write_text(json.dumps({
        "synthetic": True,
        "dataset_label": "SYNTHETIC adversarial batch. Not real sales.",
        "records": records,
    }), encoding="utf-8")
    return path


def _one(tid):
    payload = vault.build_synthetic_import()
    return next(
        item["record"]
        for item in payload["records"]
        if isinstance(item, dict) and item.get("record", {}).get("transaction_id") == tid
    )


class ValuationVault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hashes = {path: _sha(path) for path in PRODUCTION}

    @classmethod
    def tearDownClass(cls):
        for path, digest in cls.production_hashes.items():
            if _sha(path) != digest:
                raise AssertionError(f"production file changed: {path}")

    def test_vault_inside_the_repository_is_refused(self):
        with self.assertRaises(SystemExit):
            vault.vault_root(str(ROOT / "valuation-vault"))

    def test_missing_root_is_refused(self):
        previous = os.environ.pop(vault.ENV_ROOT, None)
        try:
            with self.assertRaises(SystemExit):
                vault.vault_root(None)
        finally:
            if previous is not None:
                os.environ[vault.ENV_ROOT] = previous

    def test_malformed_import_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            bad = Path(tmp) / "bad.json"
            bad.write_text("{", encoding="utf-8")
            with self.assertRaises(SystemExit):
                vault.import_batch(root, bad)
            self.assertFalse((root / ".git").exists())

    def test_synthetic_demo_keeps_restricted_records_out_of_export(self):
        self.assertFalse(sp.ADMISSION_OPEN)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            (root / "licences").mkdir(parents=True)
            (root / "licences" / "confidential-licence.txt").write_text(
                "SYNTHETIC confidential licence. Not a real grant.", encoding="utf-8")
            result = vault.demo(root)
            self.assertEqual(result["approved_record_ids"], ["SYN-TX-PUBLIC"])
            self.assertFalse((root / ".git").exists())

            approved = sorted(path.name for path in (root / "export" / "approved").glob("*.json"))
            self.assertEqual(approved, ["SYN-TX-PUBLIC.json"])
            approved_text = (root / "export" / "approved" / "SYN-TX-PUBLIC.json").read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC", approved_text)
            self.assertNotIn("synthetic-holdout.example", approved_text)

            manifest = json.loads((root / "export" / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["published"])
            self.assertEqual(manifest["approved_record_ids"], ["SYN-TX-PUBLIC"])
            self.assertEqual(manifest["aggregate_record_ids"], ["SYN-TX-PUBLIC"])
            by_id = {item["transaction_id"]: item for item in manifest["decisions"]}
            self.assertEqual(by_id["SYN-TX-VALID"]["record_export"], "DENY")
            self.assertIn("REDISTRIBUTION_NOT_GRANTED", by_id["SYN-TX-VALID"]["reasons"])
            self.assertEqual(by_id["SYN-TX-HOLDOUT"]["record_export"], "DENY")
            self.assertIn("HOLDOUT_PARTITION", by_id["SYN-TX-HOLDOUT"]["reasons"])
            self.assertEqual(by_id["SYN-TX-HOLDOUT"]["aggregate_disclosure"], "DENY")
            self.assertEqual(by_id["SYN-TX-NORIGHTS"]["record_export"], "DENY")
            self.assertEqual(by_id["SYN-TX-SECONDARY"]["record_export"], "DENY")

            self.assertTrue((root / "calibration" / "SYN-TX-VALID.json").is_file())
            self.assertTrue((root / "calibration" / "SYN-TX-PUBLIC.json").is_file())
            self.assertFalse((root / "calibration" / "SYN-TX-HOLDOUT.json").exists())
            self.assertTrue((root / "holdout" / "SYN-TX-HOLDOUT.json").is_file())
            self.assertTrue((root / "evaluation" / "rejected" / "SYN-TX-UNPAID.json").is_file())
            self.assertTrue((root / "evaluation" / "rejected" / "SYN-TX-DUPLICATE.json").is_file())
            self.assertFalse((root / "calibration" / "SYN-TX-PENDING.json").exists())

            states = {
                "SYN-TX-VALID": ("calibration", "ELIGIBLE", []),
                "SYN-TX-PUBLIC": ("calibration", "ELIGIBLE", []),
                "SYN-TX-HOLDOUT": ("holdout", "ELIGIBLE", []),
                "SYN-TX-PENDING": ("verified-sales", "SOURCE_REVIEWED", ["COMPLETION_NOT_EVIDENCED"]),
                "SYN-TX-UNPAID": ("evaluation/rejected", "REJECTED", ["NOT_A_COMPLETED_SALE"]),
                "SYN-TX-DUPLICATE": ("evaluation/rejected", "REJECTED", ["DUPLICATE_REPORT"]),
                "SYN-TX-BADPRICE": ("verified-sales", "SOURCE_REVIEWED", ["PRICE_INVALID"]),
                "SYN-TX-NODATE": ("verified-sales", "SOURCE_REVIEWED", ["SALE_DATE_UNKNOWN"]),
                "SYN-TX-NORIGHTS": ("verified-sales", "SOURCE_REVIEWED", ["RIGHTS_NOT_ESTABLISHED"]),
                "SYN-TX-SECONDARY": ("verified-sales", "SOURCE_REVIEWED", ["UPSTREAM_RIGHTS_UNCONFIRMED"]),
            }
            for tid, (stage, state, codes) in states.items():
                payload = json.loads((root / stage / f"{tid}.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["pipeline"]["state"], state, tid)
                self.assertNotEqual(payload["pipeline"]["state"], "CALIBRATION_ADMITTED", tid)
                self.assertNotEqual(payload["pipeline"]["state"], "HOLDOUT_RESERVED", tid)
                for code in codes:
                    bucket = payload["pipeline"]["rejection_reasons"] if state == "REJECTED" else payload["pipeline"]["blockers"]
                    self.assertIn(code, bucket, tid)
                self.assertIn("SYNTHETIC", payload["notes"])

            report = json.loads((root / "evaluation" / "quality-report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["synthetic"])
            self.assertFalse(report["admission_open"])
            self.assertEqual(report["imported_records"], 12)
            self.assertEqual(report["stored_records"], 10)
            self.assertEqual(report["structurally_rejected"], 2)
            self.assertEqual(report["eligible_transactions"], 2)
            self.assertEqual(report["rejected_transactions"], 2)
            self.assertEqual(report["missing_completion_evidence"], 1)
            self.assertEqual(report["missing_sale_date"], 1)
            self.assertEqual(report["missing_rights"], 2)
            self.assertEqual(report["holdout_separation"]["overlap"], [])
            self.assertEqual(report["holdout_separation"]["holdout_count"], 1)
            self.assertTrue(any(item["kind"] == "DUPLICATE_REPORT" for item in report["duplicate_relationships"]))
            self.assertIn("invalid", report["price_band_distribution"])
            self.assertGreater(report["source_concentration"]["records"], 0)

            audit = (root / "audit" / "events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("4200", audit)
            self.assertNotIn("15000", audit)
            self.assertNotIn("SYNTHETIC sale marked paid", audit)
            self.assertNotIn("synthetic-holdout.example", audit)
            self.assertIn("SYN-TX-HOLDOUT", audit)

            export_tree = "\n".join(
                path.read_text(encoding="utf-8") for path in (root / "export").rglob("*") if path.is_file()
            )
            self.assertNotIn("confidential licence", export_tree.lower())
            self.assertNotIn("synthetic-holdout.example", export_tree)
            self.assertNotIn("synthetic-pending.example", export_tree)

            public_status = json.loads(PRODUCTION[-1].read_text(encoding="utf-8"))
            self.assertEqual(public_status["status"], "NOT_READY")
            self.assertIsNone(public_status["record_count"])

    def test_secret_material_is_not_exportable(self):
        payload = vault.build_synthetic_import()
        record = next(item["record"] for item in payload["records"] if isinstance(item, dict) and item["record"]["transaction_id"] == "SYN-TX-PUBLIC")
        record["notes"] = "SYNTHETIC password=not-a-real-secret"
        assessed = sp.assess_all([record])[0]
        decision = vault.export_decision(assessed, "calibration")
        self.assertEqual(decision["record_export"], "DENY")
        self.assertIn("SECRET_MATERIAL", decision["reasons"])

    def test_public_deployment_rules_exclude_private_tooling(self):
        manifest = json.loads((ROOT / "deploy" / "pages-manifest.json").read_text(encoding="utf-8"))
        for pattern in ("scripts/**", "tests/**", "docs/**", "research/**"):
            self.assertIn(pattern, manifest["exclude"])
        self.assertIn("js/valuation-engine.js", manifest["required"])
        self.assertIn("data/valuation_comps.json", manifest["required"])
        self.assertIn("/valuation-vault/", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_status_only_redistribution_is_rejected(self):
        record = _one("SYN-TX-PUBLIC")
        record["rights"]["redistribution"] = {"status": "PERMITTED"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            vault.import_batch(root, _write_batch(Path(tmp), "status.json", [_envelope(record)]))
            stored = json.loads((root / "verified-sales" / "SYN-TX-PUBLIC.json").read_text(encoding="utf-8"))
            self.assertNotEqual(stored["pipeline"]["state"], "ELIGIBLE")
            self.assertIn("RIGHTS_NOT_ESTABLISHED", stored["pipeline"]["blockers"])
            manifest = vault.export_approved(root)
            self.assertEqual(manifest["approved_record_ids"], [])
            self.assertEqual(manifest["decisions"][0]["record_export"], "DENY")
            self.assertIn("RIGHTS_INVALID", manifest["decisions"][0]["reasons"])
            self.assertFalse((root / "export" / "approved" / "SYN-TX-PUBLIC.json").exists())

    def test_missing_rights_reference_cannot_authorise_export(self):
        record = _one("SYN-TX-PUBLIC")
        record["rights"]["redistribution"] = {
            "status": "PERMITTED",
            "basis_type": "WRITTEN_PERMISSION",
            "basis": "SYNTHETIC fixture without a document reference.",
            "reference": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            vault.import_batch(root, _write_batch(Path(tmp), "ref.json", [_envelope(record)]))
            manifest = vault.export_approved(root)
            self.assertEqual(manifest["approved_record_ids"], [])
            self.assertIn("REDISTRIBUTION_NOT_GRANTED", manifest["decisions"][0]["reasons"])
            self.assertFalse(vault.REAL_IMPORT_PERMITTED)

    def test_real_import_is_disabled(self):
        record = _one("SYN-TX-VALID")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            path = Path(tmp) / "real.json"
            path.write_text(json.dumps({
                "synthetic": False,
                "dataset_label": "not synthetic",
                "records": [_envelope(record)],
            }), encoding="utf-8")
            with self.assertRaises(SystemExit):
                vault.import_batch(root, path)
            self.assertFalse(root.exists())

    def test_holdout_candidate_cannot_enter_calibration_or_export(self):
        record = _one("SYN-TX-HOLDOUT")
        self.assertEqual(record["calibration_role"], "HOLDOUT_CANDIDATE")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            summary = vault.import_batch(root, _write_batch(Path(tmp), "hold.json", [
                _envelope(record, "calibration"),
            ]))
            self.assertEqual(summary["stored"], 0)
            self.assertFalse((root / "calibration" / "SYN-TX-HOLDOUT.json").exists())
            self.assertFalse((root / "holdout" / "SYN-TX-HOLDOUT.json").exists())
            manifest = vault.export_approved(root)
            self.assertEqual(manifest["approved_record_ids"], [])
            self.assertEqual(manifest["aggregate_record_ids"], [])

    def test_same_domain_cannot_cross_from_holdout_into_calibration(self):
        holdout = _one("SYN-TX-HOLDOUT")
        other = _one("SYN-TX-VALID")
        other["domain"] = holdout["domain"]
        other["transaction_id"] = "SYN-TX-CROSS"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            vault.import_batch(root, _write_batch(Path(tmp), "h.json", [_envelope(holdout, "holdout")]))
            before = _sha(root / "holdout" / "SYN-TX-HOLDOUT.json")
            summary = vault.import_batch(root, _write_batch(Path(tmp), "c.json", [_envelope(other, "calibration")]))
            self.assertEqual(summary["stored"], 0)
            self.assertEqual(_sha(root / "holdout" / "SYN-TX-HOLDOUT.json"), before)
            self.assertFalse((root / "calibration" / "SYN-TX-CROSS.json").exists())
            self.assertEqual(vault.export_approved(root)["approved_record_ids"], [])

    def test_duplicate_across_imports_is_detected_without_overwrite(self):
        first = _one("SYN-TX-VALID")
        second = _one("SYN-TX-VALID")
        second["transaction_id"] = "SYN-TX-LATER"
        second["pipeline"]["duplicate_of"] = None
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            vault.import_batch(root, _write_batch(Path(tmp), "one.json", [_envelope(first)]))
            original = _sha(root / "calibration" / "SYN-TX-VALID.json")
            vault.import_batch(root, _write_batch(Path(tmp), "two.json", [_envelope(second)]))
            self.assertEqual(_sha(root / "calibration" / "SYN-TX-VALID.json"), original)
            later = json.loads((root / "verified-sales" / "SYN-TX-LATER.json").read_text(encoding="utf-8"))
            self.assertNotEqual(later["pipeline"]["state"], "ELIGIBLE")
            self.assertIn("DUPLICATE_UNRESOLVED", later["pipeline"]["blockers"])
            report = json.loads((root / "evaluation" / "quality-report.json").read_text(encoding="utf-8"))
            self.assertTrue(any(
                {item["left"], item["right"]} == {"SYN-TX-VALID", "SYN-TX-LATER"}
                for item in report["duplicate_relationships"]
            ))
            self.assertIn("SYN-TX-LATER", report["unresolved_relationship_ids"])
            self.assertEqual(report["stored_records"], 2)

    def test_existing_transaction_id_is_not_overwritten(self):
        record = _one("SYN-TX-VALID")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            batch = _write_batch(Path(tmp), "same.json", [_envelope(record)])
            vault.import_batch(root, batch)
            original = _sha(root / "calibration" / "SYN-TX-VALID.json")
            summary = vault.import_batch(root, batch)
            self.assertEqual(summary["stored"], 0)
            self.assertEqual(_sha(root / "calibration" / "SYN-TX-VALID.json"), original)

    def test_junction_cannot_redirect_a_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            outside = Path(tmp) / "outside"
            root.mkdir()
            outside.mkdir()
            link = root / "export"
            if os.name == "nt":
                subprocess.check_call(["cmd", "/c", "mklink", "/J", str(link), str(outside)], stdout=subprocess.DEVNULL)
            else:
                link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(SystemExit):
                vault.ensure_layout(root)
            self.assertEqual(list(outside.rglob("*")), [])

    def test_malformed_record_does_not_leave_a_partial_file(self):
        valid = _one("SYN-TX-VALID")
        poison = _one("SYN-TX-PUBLIC")
        poison["transaction_id"] = "SYN-TX-POISON"
        poison["rights"] = {"storage": "PERMITTED"}
        poison["notes"] = "password=should-not-be-written"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            summary = vault.import_batch(root, _write_batch(Path(tmp), "mix.json", [
                _envelope(valid),
                _envelope(poison),
            ]))
            self.assertEqual(summary["stored"], 1)
            self.assertTrue((root / "calibration" / "SYN-TX-VALID.json").is_file())
            self.assertFalse(list(root.rglob("*POISON*")))
            self.assertFalse(list(root.rglob("*.partial")))
            self.assertNotIn("password=should-not-be-written", (root / "audit" / "events.jsonl").read_text(encoding="utf-8"))

    def test_demo_cannot_alter_an_existing_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            (root / "calibration").mkdir(parents=True)
            sentinel = root / "calibration" / "KEEP.json"
            sentinel.write_text('{"transaction_id":"KEEP","notes":"do not replace"}\n', encoding="utf-8")
            digest = _sha(sentinel)
            previous = os.environ.get(vault.ENV_ROOT)
            os.environ[vault.ENV_ROOT] = str(root)
            try:
                with self.assertRaises(SystemExit):
                    vault.demo(root)
            finally:
                if previous is None:
                    os.environ.pop(vault.ENV_ROOT, None)
                else:
                    os.environ[vault.ENV_ROOT] = previous
            self.assertEqual(_sha(sentinel), digest)
            self.assertFalse((root / "export" / "approved").exists())

    def test_secrets_do_not_enter_the_audit_log_or_export(self):
        record = _one("SYN-TX-PUBLIC")
        record["transaction_id"] = "SYN-TX-SECRET"
        record["notes"] = "password=not-a-real-secret"
        record["checked_quote"] = "PRIVATE-EVIDENCE-SENTENCE must stay out of the log"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            vault.import_batch(root, _write_batch(Path(tmp), "secret.json", [_envelope(record)]))
            manifest = vault.export_approved(root)
            self.assertEqual(manifest["approved_record_ids"], [])
            exported = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (root / "export").rglob("*")
                if path.is_file()
            )
            audit = (root / "audit" / "events.jsonl").read_text(encoding="utf-8")
            for secret in ("password=not-a-real-secret", "PRIVATE-EVIDENCE-SENTENCE"):
                self.assertNotIn(secret, audit)
                self.assertNotIn(secret, exported)

    def test_reserved_windows_device_name_is_rejected(self):
        record = _one("SYN-TX-VALID")
        record["transaction_id"] = "CON"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            summary = vault.import_batch(root, _write_batch(Path(tmp), "con.json", [_envelope(record)]))
            self.assertEqual(summary["stored"], 0)
            self.assertFalse(list(root.rglob("CON.json")))

    def test_setup_script_rejects_a_git_root_before_creating_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 str(ROOT / "scripts" / "setup_valuation_vault.ps1"), "-VaultPath", str(repo)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertFalse((repo / "sources").exists())
            self.assertFalse((repo / "raw-sales").exists())
