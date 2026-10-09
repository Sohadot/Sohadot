#!/usr/bin/env python3
"""Validate the Sprint 1A Transaction Evidence Registry (research only).

The registry records individual domain-sale *transactions* with their
evidence, rights and intended analytical role. It is research material:
nothing in it feeds the production valuation engine. See
docs/valuation-evidence/TRANSACTION_EVIDENCE_REGISTRY_V1.md for the standard.

Checks:
  - schema: required fields, enums, domains, prices, currencies, dates;
  - identity: unique, stable transaction IDs; repeat sales of one domain kept
    as separate transactions; no duplicate (domain, date, price) records;
  - evidence: VERIFIED only on a reviewed primary document with an exact,
    rounded or stated price and no material conflict. A URL alone never
    verifies. DISPUTED needs a material conflict. REPORTED needs a source;
  - rights: every record states a basis; licensed reuse names the licence;
  - roles: calibration candidates must be domain-only with a usable price,
    evidence and rights. The role is never derived from the evidence status;
  - dataset: header counts and content hash match the records, and the
    header never claims dataset-level verification (Sprint 0 rule);
  - seed investigation: every seed sale has exactly one investigation record,
    and every referenced transaction exists;
  - holdout: status file is consistent; a holdout manifest never overlaps
    calibration candidates by domain or second-level name; no holdout records
    are committed to the public repository;
  - isolation: production code and data never reference the research files;
  - determinism: files are in canonical form (--write rewrites them).

Usage:
  python3 scripts/validate_evidence_registry.py           # validate
  python3 scripts/validate_evidence_registry.py --write   # recompute header, canonicalise
Exits 0 and prints PASS, or prints each violation prefixed "FAIL:" and exits 1.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = REPO_ROOT / "research" / "valuation-evidence"
REGISTRY_PATH = RESEARCH_DIR / "registry" / "transactions.v1.json"
INVESTIGATION_PATH = RESEARCH_DIR / "investigations" / "seed-45.v1.json"
HOLDOUT_STATUS_PATH = RESEARCH_DIR / "holdout" / "status.v1.json"
SEED_PATH = REPO_ROOT / "data" / "valuation_comps_seed.json"

SCHEMA_VERSION = "transaction-evidence/v1"
DATASET_STATUS = "RESEARCH_ONLY_NOT_FOR_PRODUCTION"

ENUMS = {
    "sale_date_precision": {"DAY", "MONTH", "YEAR", "UNKNOWN"},
    "venue": {"AUCTION", "MARKETPLACE", "BROKER", "PRIVATE", "BANKRUPTCY_SALE", "CORPORATE_TRANSACTION", "UNKNOWN"},
    "transaction_type": {"DOMAIN_ONLY", "DOMAIN_PLUS_ASSETS", "MULTIPLE_DOMAINS", "WEBSITE_BUSINESS", "BUSINESS_ASSETS", "UNKNOWN"},
    "consideration_type": {"CASH", "CASH_AND_STOCK", "CASH_AND_NOTE", "CASH_AND_OTHER", "STOCK", "CRYPTOCURRENCY", "STRUCTURED", "UNKNOWN"},
    "market_side": {"END_USER_ACQUISITION", "INVESTOR_TRADE", "UNKNOWN"},
    "source_type": {"REGULATORY_FILING", "COURT_RECORD", "PARTY_ANNOUNCEMENT", "MARKETPLACE_RECORD",
                    "TRADE_PUBLICATION", "GENERAL_NEWS", "AGGREGATOR_DATABASE", "TERTIARY_REFERENCE", "NONE"},
    "source_access_method": {"DOCUMENT_REVIEWED", "SEARCH_INDEX_ONLY", "NOT_ACCESSED"},
    "price_disclosure_status": {"EXACT", "ROUNDED", "STATED_SUBJECT_TO_ADJUSTMENT", "APPROXIMATE", "LOWER_BOUND",
                                "UNDISCLOSED", "UNKNOWN"},
    "evidence_status": {"VERIFIED", "REPORTED", "DISPUTED", "UNVERIFIED"},
    "rights_status": {"PUBLIC_RECORD", "PUBLIC_VIEW_CITATION_ONLY", "LICENSED_REUSE", "PERMISSION_REQUIRED",
                      "RESTRICTED_OR_UNKNOWN"},
    "calibration_role": {"CALIBRATION_CANDIDATE", "HOLDOUT_CANDIDATE", "REFERENCE_ONLY", "EXCLUDED", "UNDETERMINED"},
}

FIELDS = [
    "transaction_id", "domain", "sale_price", "currency", "sale_date", "sale_date_precision", "report_date",
    "venue", "transaction_type", "consideration_type", "market_side", "source_name", "source_url", "source_type",
    "source_access_method", "source_accessed_at", "additional_sources", "price_disclosure_status", "price_claims",
    "conflicts", "evidence_status", "verification_basis", "verified_at", "rights_status", "rights_basis",
    "rights_license", "calibration_role", "notes",
]

# Primary evidence: a statement by a party to the transaction or an official record.
PRIMARY_SOURCE_TYPES = {"REGULATORY_FILING", "COURT_RECORD", "PARTY_ANNOUNCEMENT", "MARKETPLACE_RECORD"}
VERIFIABLE_PRICE = {"EXACT", "ROUNDED", "STATED_SUBJECT_TO_ADJUSTMENT"}
PRICED = VERIFIABLE_PRICE | {"APPROXIMATE", "LOWER_BOUND"}
CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CNY", "CAD", "AUD", "CHF"}
EARLIEST_SALE = date(1985, 1, 1)

ID_RE = re.compile(r"^SOH-TX-\d{6}$")
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
DATE_RE = {
    "DAY": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "MONTH": re.compile(r"^\d{4}-\d{2}$"),
    "YEAR": re.compile(r"^\d{4}$"),
}

# Production files that must never read the research registry.
PRODUCTION_FILES = ["js/valuation-engine.js", "js/valuation-ui.js", "scripts/generate_valuation_data.py", "valuation.html"]
RESEARCH_MARKERS = ["research/valuation-evidence", "transactions.v1.json", "seed-45.v1.json"]


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def content_hash(transactions):
    blob = json.dumps(transactions, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_partial_date(value, precision=None):
    """Return the earliest date a partial ISO date can denote, or None."""
    if value is None:
        return None
    for prec, rx in DATE_RE.items():
        if rx.match(value) and (precision in (None, prec)):
            parts = [int(p) for p in value.split("-")] + [1, 1]
            try:
                return date(parts[0], parts[1], parts[2])
            except ValueError:
                return None
    return None


def second_level(domain):
    return domain.split(".", 1)[0]


def check_transaction(t, errors, as_of):
    tid = t.get("transaction_id") or "<missing id>"
    where = f"{tid}"

    missing = [f for f in FIELDS if f not in t]
    if missing:
        errors.append(f"{where}: missing field(s) {', '.join(missing)}")
        return
    extra = [f for f in t if f not in FIELDS]
    if extra:
        errors.append(f"{where}: unknown field(s) {', '.join(extra)}")

    if not isinstance(t["transaction_id"], str) or not ID_RE.match(t["transaction_id"]):
        errors.append(f"{where}: transaction_id must match SOH-TX-NNNNNN")

    for field, allowed in ENUMS.items():
        if t[field] not in allowed:
            errors.append(f"{where}: {field} {t[field]!r} not in {sorted(allowed)}")

    if not isinstance(t["domain"], str) or not DOMAIN_RE.match(t["domain"]):
        errors.append(f"{where}: invalid domain {t['domain']!r}")

    price, disclosure = t["sale_price"], t["price_disclosure_status"]
    if price is not None and (not isinstance(price, int) or isinstance(price, bool) or price <= 0):
        errors.append(f"{where}: sale_price must be a positive integer or null")
    if t["currency"] not in CURRENCIES:
        errors.append(f"{where}: currency {t['currency']!r} not in {sorted(CURRENCIES)}")
    if disclosure in PRICED and price is None:
        errors.append(f"{where}: price_disclosure_status {disclosure} requires sale_price")
    if disclosure in {"UNDISCLOSED", "UNKNOWN"} and price is not None:
        errors.append(f"{where}: an {disclosure.lower()} price must have sale_price null (keep claims in price_claims)")

    # Dates.
    precision = t["sale_date_precision"]
    if t["sale_date"] is None:
        if precision != "UNKNOWN":
            errors.append(f"{where}: sale_date null requires sale_date_precision UNKNOWN")
    else:
        sale = parse_partial_date(t["sale_date"], precision)
        if precision == "UNKNOWN" or sale is None:
            errors.append(f"{where}: sale_date {t['sale_date']!r} does not match precision {precision}")
        elif sale < EARLIEST_SALE or sale > as_of:
            errors.append(f"{where}: sale_date {t['sale_date']} outside {EARLIEST_SALE}..{as_of}")
    if t["report_date"] is not None:
        report = parse_partial_date(t["report_date"])
        if report is None or report > as_of:
            errors.append(f"{where}: invalid or future report_date {t['report_date']!r}")
        elif t["sale_date"] is not None and parse_partial_date(t["sale_date"], precision):
            # Compare at the coarser precision: a report cannot predate the sale.
            sale_year = int(t["sale_date"][:4])
            if report.year < sale_year or (
                precision in ("DAY", "MONTH") and len(t["report_date"]) >= 7
                and t["report_date"][:7] < t["sale_date"][:7]
            ):
                errors.append(f"{where}: report_date {t['report_date']} precedes sale_date {t['sale_date']}")
    for field in ("source_accessed_at", "verified_at"):
        value = t[field]
        if value is not None:
            d = parse_partial_date(value, "DAY")
            if d is None or d > as_of:
                errors.append(f"{where}: {field} must be a past ISO date (YYYY-MM-DD)")

    # Sources.
    status, stype, method = t["evidence_status"], t["source_type"], t["source_access_method"]
    has_source = bool(t["source_url"]) and stype != "NONE"
    if stype == "NONE" and (t["source_url"] or t["source_name"]):
        errors.append(f"{where}: source_type NONE must not carry a source")
    if t["source_url"] and not str(t["source_url"]).startswith("https://"):
        errors.append(f"{where}: source_url must be https")
    if has_source and (not t["source_name"] or not t["source_accessed_at"] or method == "NOT_ACCESSED"):
        errors.append(f"{where}: a cited source needs source_name, source_accessed_at and an access method")
    for extra_src in t["additional_sources"]:
        if extra_src.get("source_type") not in ENUMS["source_type"] or not str(extra_src.get("source_url", "")).startswith("https://"):
            errors.append(f"{where}: additional source needs a valid source_type and https URL")

    material = [c for c in t["conflicts"] if c.get("material")]
    for c in t["conflicts"]:
        if not isinstance(c.get("material"), bool) or not c.get("description"):
            errors.append(f"{where}: each conflict needs a description and a boolean 'material'")

    # Evidence status rules. A URL alone never verifies.
    if status == "VERIFIED":
        reasons = []
        if stype not in PRIMARY_SOURCE_TYPES:
            reasons.append(f"source_type {stype} is not primary evidence")
        if method != "DOCUMENT_REVIEWED":
            reasons.append("primary document not reviewed")
        if disclosure not in VERIFIABLE_PRICE or price is None:
            reasons.append(f"price disclosure {disclosure} is not verifiable")
        if not t["verified_at"] or not t["verification_basis"] or len(t["verification_basis"]) < 40:
            reasons.append("verified_at and a substantive verification_basis are required")
        if material:
            reasons.append("material conflicts are unresolved")
        if reasons:
            errors.append(f"{where}: unsupported VERIFIED claim ({'; '.join(reasons)})")
    else:
        if t["verified_at"] is not None:
            errors.append(f"{where}: verified_at set on a {status} record")
    if status == "DISPUTED" and not material:
        errors.append(f"{where}: DISPUTED requires at least one material conflict")
    if status in {"REPORTED", "VERIFIED"} and material:
        errors.append(f"{where}: {status} with an unresolved material conflict must be DISPUTED")
    if status == "REPORTED" and not has_source:
        errors.append(f"{where}: REPORTED requires a cited source")

    # Rights.
    if not t["rights_basis"] or len(str(t["rights_basis"])) < 20:
        errors.append(f"{where}: rights_basis must explain the rights conclusion")
    if t["rights_status"] == "LICENSED_REUSE" and not t["rights_license"]:
        errors.append(f"{where}: LICENSED_REUSE requires rights_license (licence name and URL)")
    if t["rights_status"] == "PUBLIC_RECORD" and stype not in {"REGULATORY_FILING", "COURT_RECORD"}:
        errors.append(f"{where}: PUBLIC_RECORD rights only apply to filings and court records")

    # Roles: necessary conditions only. Status never assigns a role.
    role = t["calibration_role"]
    if role == "CALIBRATION_CANDIDATE":
        reasons = []
        if status not in {"VERIFIED", "REPORTED"}:
            reasons.append(f"evidence {status}")
        if t["transaction_type"] != "DOMAIN_ONLY":
            reasons.append(f"transaction_type {t['transaction_type']}")
        if disclosure not in VERIFIABLE_PRICE:
            reasons.append(f"price {disclosure}")
        if t["consideration_type"] not in {"CASH", "UNKNOWN"}:
            reasons.append(f"consideration {t['consideration_type']}")
        if t["rights_status"] in {"PERMISSION_REQUIRED", "RESTRICTED_OR_UNKNOWN"}:
            reasons.append(f"rights {t['rights_status']}")
        if reasons:
            errors.append(f"{where}: not eligible as CALIBRATION_CANDIDATE ({'; '.join(reasons)})")
    if role == "HOLDOUT_CANDIDATE":
        errors.append(f"{where}: holdout candidates must not be stored in the public registry")


def check_registry(registry, errors, as_of=None):
    as_of = as_of or date.today()
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"registry: schema_version must be {SCHEMA_VERSION!r}")
    if registry.get("dataset_status") != DATASET_STATUS:
        errors.append(f"registry: dataset_status must be {DATASET_STATUS!r}")
    for key in registry:
        if "verif" in key.lower() and key != "status_counts":
            errors.append(f"registry: header must not carry dataset-level verification ({key!r})")

    txs = registry.get("transactions", [])
    ids, keys = set(), set()
    for t in txs:
        check_transaction(t, errors, as_of)
        tid = t.get("transaction_id")
        if tid in ids:
            errors.append(f"{tid}: duplicate transaction_id")
        ids.add(tid)
        if t.get("sale_date") is not None and t.get("sale_price") is not None:
            key = (t.get("domain"), t.get("sale_date"), t.get("sale_price"))
            if key in keys:
                errors.append(f"{tid}: duplicates another transaction of {key[0]} on {key[1]} at {key[2]}")
            keys.add(key)

    # Repeat sales: the same domain must not be both calibration and holdout,
    # and two calibration candidates of one domain need distinct dates.
    roles = {}
    for t in txs:
        roles.setdefault(t.get("domain"), []).append(t)
    for domain, group in roles.items():
        cal = [t for t in group if t.get("calibration_role") == "CALIBRATION_CANDIDATE"]
        if len({t.get("sale_date") for t in cal}) < len(cal):
            errors.append(f"{domain}: repeat-sale calibration candidates need distinct sale dates")

    counts = {s: 0 for s in sorted(ENUMS["evidence_status"])}
    role_counts = {r: 0 for r in sorted(ENUMS["calibration_role"])}
    for t in txs:
        if t.get("evidence_status") in counts:
            counts[t["evidence_status"]] += 1
        if t.get("calibration_role") in role_counts:
            role_counts[t["calibration_role"]] += 1
    header = {"transaction_count": len(txs), "status_counts": counts, "role_counts": role_counts,
              "content_sha256": content_hash(txs)}
    for key, value in header.items():
        if registry.get(key) != value:
            errors.append(f"registry: header {key} is {registry.get(key)!r}, expected {value!r}")
    return header


def check_investigation(investigation, registry, seed, errors):
    tx_ids = {t["transaction_id"]: t for t in registry.get("transactions", [])}
    records = investigation.get("records", [])
    seed_domains = [s["domain"] for s in seed["sales"]]
    seen = [r.get("seed_domain") for r in records]
    if sorted(seen) != sorted(seed_domains) or len(seen) != len(set(seen)):
        errors.append("investigation: must contain exactly one record per seed sale")
    agreements = {"CONSISTENT", "PRICE_CONFLICT", "DATE_CONFLICT", "PRICE_AND_DATE_CONFLICT",
                  "NOT_A_DOMAIN_ONLY_SALE", "PRICE_NOT_DISCLOSED", "NO_EVIDENCE_FOUND"}
    seed_index = {s["domain"]: s for s in seed["sales"]}
    for r in records:
        d = r.get("seed_domain")
        if r.get("seed_agreement") not in agreements:
            errors.append(f"investigation {d}: seed_agreement {r.get('seed_agreement')!r} invalid")
        if d in seed_index and (r.get("seed_price") != seed_index[d]["price"] or r.get("seed_year") != seed_index[d]["year"]):
            errors.append(f"investigation {d}: seed_price/seed_year do not match the published seed")
        if not r.get("transaction_ids"):
            errors.append(f"investigation {d}: no transaction referenced")
        for tid in r.get("transaction_ids", []):
            if tid not in tx_ids:
                errors.append(f"investigation {d}: unknown transaction {tid}")
            elif tx_ids[tid]["domain"] != d:
                errors.append(f"investigation {d}: {tid} belongs to {tx_ids[tid]['domain']}")
        for field in ("findings", "remaining_work", "recommended_role", "rights_uncertainty", "transaction_type_uncertainty"):
            if not r.get(field):
                errors.append(f"investigation {d}: {field} must be stated")
        if r.get("evidence_found") is False and r.get("seed_agreement") not in {"NO_EVIDENCE_FOUND", "PRICE_NOT_DISCLOSED"}:
            errors.append(f"investigation {d}: no evidence found but agreement {r.get('seed_agreement')}")


def check_holdout(status, registry, errors, manifest=None):
    allowed = {"NOT_READY", "FROZEN"}
    if status.get("status") not in allowed:
        errors.append(f"holdout: status must be one of {sorted(allowed)}")
    if status.get("status") == "NOT_READY":
        for key in ("frozen_at", "manifest_sha256", "record_count"):
            if status.get(key) is not None:
                errors.append(f"holdout: {key} must be null while NOT_READY")
    if status.get("status") == "FROZEN":
        for key in ("frozen_at", "manifest_sha256", "record_count", "storage_location"):
            if not status.get(key):
                errors.append(f"holdout: FROZEN requires {key}")
    if not status.get("protocol_version"):
        errors.append("holdout: protocol_version required")

    if manifest is not None:
        calibration = [t for t in registry.get("transactions", []) if t.get("calibration_role") == "CALIBRATION_CANDIDATE"]
        cal_domains = {t["domain"] for t in calibration}
        cal_slds = {second_level(t["domain"]) for t in calibration}
        cal_ids = {t["transaction_id"] for t in calibration}
        for h in manifest.get("transactions", []):
            if h.get("transaction_id") in cal_ids:
                errors.append(f"holdout: {h.get('transaction_id')} is also a calibration candidate")
            if h.get("domain") in cal_domains:
                errors.append(f"holdout: {h.get('domain')} overlaps a calibration domain (repeat-sale leakage)")
            elif second_level(h.get("domain", "")) in cal_slds:
                errors.append(f"holdout: {h.get('domain')} shares a second-level name with a calibration domain")


def check_public_boundary(errors):
    # Holdout records live outside the public repository; only status and protocol are committed.
    holdout_dir = RESEARCH_DIR / "holdout"
    if holdout_dir.is_dir():
        for path in holdout_dir.iterdir():
            if path.name != HOLDOUT_STATUS_PATH.name:
                errors.append(f"holdout: {path.relative_to(REPO_ROOT)} must not be committed (holdout data stays private)")
    for rel in PRODUCTION_FILES:
        path = REPO_ROOT / rel
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for marker in RESEARCH_MARKERS:
                if marker in text:
                    errors.append(f"{rel}: production code references research registry ({marker!r})")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Validate the Sprint 1A evidence registry")
    parser.add_argument("--write", action="store_true", help="recompute registry header and canonicalise files")
    parser.add_argument("--as-of", help="reference date (YYYY-MM-DD) for future-date checks")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()

    registry = load(REGISTRY_PATH)
    investigation = load(INVESTIGATION_PATH)
    holdout = load(HOLDOUT_STATUS_PATH)
    seed = load(SEED_PATH)

    if args.write:
        scratch = []
        header = check_registry(registry, scratch, as_of)
        registry.update(header)
        REGISTRY_PATH.write_text(canonical(registry), encoding="utf-8")
        INVESTIGATION_PATH.write_text(canonical(investigation), encoding="utf-8")
        HOLDOUT_STATUS_PATH.write_text(canonical(holdout), encoding="utf-8")

    errors = []
    check_registry(registry, errors, as_of)
    check_investigation(investigation, registry, seed, errors)
    check_holdout(holdout, registry, errors)
    check_public_boundary(errors)
    for path, payload in ((REGISTRY_PATH, registry), (INVESTIGATION_PATH, investigation), (HOLDOUT_STATUS_PATH, holdout)):
        if path.read_text(encoding="utf-8") != canonical(payload):
            errors.append(f"{path.relative_to(REPO_ROOT)}: not in canonical form (run with --write)")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    c = registry["status_counts"]
    print(f"PASS: evidence registry valid — {registry['transaction_count']} transactions "
          f"(VERIFIED {c['VERIFIED']}, REPORTED {c['REPORTED']}, DISPUTED {c['DISPUTED']}, UNVERIFIED {c['UNVERIFIED']}); "
          f"{len(investigation['records'])} seed investigations; holdout {holdout['status']}")


if __name__ == "__main__":
    main()
