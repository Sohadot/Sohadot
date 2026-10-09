#!/usr/bin/env python3
"""Validate the Sprint 1A Transaction Evidence Registry (research only).

The registry records individual domain-sale *transactions* with their
evidence, rights and intended analytical role. It is research material:
nothing in it feeds the production valuation engine. The standard is in
docs/valuation-evidence/TRANSACTION_EVIDENCE_REGISTRY_V1.md.

Checks:
  - schema: required fields, enums, domains, prices, currencies, dates;
  - identity: unique, stable IDs; repeat sales as separate transactions;
    no duplicate (domain, date, price) records;
  - provenance: every principal source was read directly and checked
    against its raw text (locator, checked quote, document hash, review
    method). Search-index summaries are kept only as `leads`;
  - evidence: VERIFIED needs a primary source; REPORTED a reportable source
    class; DISPUTED a material conflict; UNVERIFIED no principal source.
    Valuation caveats never change the evidence status;
  - scope: bundle and business prices are never attributed to one domain;
  - rights: citation, storage, commercial modelling and redistribution are
    separate, each with an explicit basis. Public accessibility never grants
    storage or modelling rights;
  - roles: calibration candidates need domain-only, single-domain prices,
    usable evidence and established storage and modelling rights. The role
    is never derived from the evidence status;
  - dataset: header counts and content hash match, and the header never
    claims dataset-level verification (Sprint 0 rule);
  - seed investigation: one record per published seed sale;
  - holdout (fail-closed): the control map in the status file must match
    the controls this script implements. FROZEN is never accepted without
    verifying the private manifest (--holdout-manifest), which must live
    outside the repository and pass hash, count, eligibility,
    source-concentration and overlap checks against the registry, the
    published seed and comps, repeat sales and normalised name variants;
  - isolation: production code never references the research files, and no
    holdout manifest is committed anywhere in the repository;
  - determinism: files are in canonical form (--write rewrites them).

Usage:
  python3 scripts/validate_evidence_registry.py
  python3 scripts/validate_evidence_registry.py --write
  python3 scripts/validate_evidence_registry.py --holdout-manifest /private/path/manifest.json
Exits 0 and prints PASS, or prints each violation prefixed "FAIL:" and exits 1.
"""
import argparse
import hashlib
import json
import os
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
COMPS_PATH = REPO_ROOT / "data" / "valuation_comps.json"

SCHEMA_VERSION = "transaction-evidence/v1"
DATASET_STATUS = "RESEARCH_ONLY_NOT_FOR_PRODUCTION"
HOLDOUT_PROTOCOL_VERSION = "holdout-protocol/v1"
MANIFEST_KIND = "sohadot-holdout-manifest"
HOLDOUT_MIN_RECORDS = 150
HOLDOUT_MAX_SOURCE_SHARE = 0.25

ENUMS = {
    "sale_date_precision": {"DAY", "MONTH", "YEAR", "UNKNOWN"},
    "venue": {"AUCTION", "MARKETPLACE", "BROKER", "PRIVATE", "BANKRUPTCY_SALE", "CORPORATE_TRANSACTION", "UNKNOWN"},
    "transaction_type": {"DOMAIN_ONLY", "DOMAIN_PLUS_ASSETS", "MULTIPLE_DOMAINS", "WEBSITE_BUSINESS", "BUSINESS_ASSETS", "UNKNOWN"},
    "price_scope": {"SINGLE_DOMAIN", "BUNDLE_TOTAL", "BUSINESS_TOTAL", "UNKNOWN"},
    "consideration_type": {"CASH", "CASH_AND_STOCK", "CASH_AND_NOTE", "CASH_AND_OTHER", "STOCK", "CRYPTOCURRENCY", "STRUCTURED", "UNKNOWN"},
    "market_side": {"END_USER_ACQUISITION", "INVESTOR_TRADE", "UNKNOWN"},
    "source_type": {"REGULATORY_FILING", "COURT_RECORD", "PARTY_ANNOUNCEMENT", "MARKETPLACE_RECORD",
                    "TRADE_PUBLICATION", "GENERAL_NEWS", "AGGREGATOR_DATABASE", "TERTIARY_REFERENCE", "NONE"},
    "source_access_method": {"DOCUMENT_REVIEWED", "NOT_ACCESSED"},
    "review_method": {"RAW_TEXT_CHECKED", "TOOL_EXTRACT_CHECKED_AGAINST_RAW", "TOOL_EXTRACT_UNCHECKED", "NONE"},
    "price_disclosure_status": {"EXACT", "ROUNDED", "STATED_SUBJECT_TO_ADJUSTMENT", "APPROXIMATE", "LOWER_BOUND",
                                "UNDISCLOSED", "UNKNOWN"},
    "evidence_status": {"VERIFIED", "REPORTED", "DISPUTED", "UNVERIFIED"},
    "calibration_role": {"CALIBRATION_CANDIDATE", "HOLDOUT_CANDIDATE", "REFERENCE_ONLY", "EXCLUDED", "UNDETERMINED"},
}
RIGHTS_KEYS = ("citation", "storage", "commercial_modelling", "redistribution")
RIGHTS_STATUS = {"PERMITTED", "PERMITTED_WITH_CONDITIONS", "NOT_PERMITTED", "NOT_ESTABLISHED"}
RIGHTS_BASIS = {"PUBLIC_RECORD", "PUBLIC_FACT_CITATION", "LICENSE", "WRITTEN_PERMISSION", "DOCUMENTED_LAWFUL_BASIS", "NONE"}
RIGHTS_NEEDS_REFERENCE = {"LICENSE", "WRITTEN_PERMISSION", "DOCUMENTED_LAWFUL_BASIS"}
GRANTED = {"PERMITTED", "PERMITTED_WITH_CONDITIONS"}

FIELDS = [
    "transaction_id", "domain", "sale_price", "currency", "price_scope", "bundle", "sale_date",
    "sale_date_precision", "report_date", "venue", "transaction_type", "consideration_type", "market_side",
    "source_name", "source_url", "source_type", "source_access_method", "source_accessed_at", "review_method",
    "document_locator", "checked_quote", "document_sha256", "additional_sources", "leads",
    "price_disclosure_status", "price_claims", "conflicts", "valuation_caveats", "evidence_status",
    "verification_basis", "verified_at", "rights", "calibration_role", "notes",
]
SOURCE_FIELDS = ["source_name", "source_url", "source_type", "published_date", "source_access_method",
                 "source_accessed_at", "review_method", "document_locator", "checked_quote", "document_sha256"]
LEAD_FIELDS = ["source_name", "source_url", "source_type", "observed_at", "note"]

PRIMARY_SOURCE_TYPES = {"REGULATORY_FILING", "COURT_RECORD", "PARTY_ANNOUNCEMENT", "MARKETPLACE_RECORD"}
REPORTABLE_SOURCE_TYPES = PRIMARY_SOURCE_TYPES | {"TRADE_PUBLICATION", "GENERAL_NEWS"}
CHECKED_REVIEW = {"RAW_TEXT_CHECKED", "TOOL_EXTRACT_CHECKED_AGAINST_RAW"}
VERIFIABLE_PRICE = {"EXACT", "ROUNDED", "STATED_SUBJECT_TO_ADJUSTMENT"}
PRICED = VERIFIABLE_PRICE | {"APPROXIMATE", "LOWER_BOUND"}
SCOPE_BY_TYPE = {
    "DOMAIN_ONLY": {"SINGLE_DOMAIN"},
    "DOMAIN_PLUS_ASSETS": {"BUNDLE_TOTAL"},
    "MULTIPLE_DOMAINS": {"BUNDLE_TOTAL"},
    "WEBSITE_BUSINESS": {"BUSINESS_TOTAL"},
    "BUSINESS_ASSETS": {"BUSINESS_TOTAL"},
    "UNKNOWN": {"SINGLE_DOMAIN", "BUNDLE_TOTAL", "BUSINESS_TOTAL", "UNKNOWN"},
}
CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CNY", "CAD", "AUD", "CHF"}
EARLIEST_SALE = date(1985, 1, 1)

ID_RE = re.compile(r"^SOH-TX-\d{6}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
DATE_RE = {
    "DAY": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "MONTH": re.compile(r"^\d{4}-\d{2}$"),
    "YEAR": re.compile(r"^\d{4}$"),
}
PRECISION_LEN = {"YEAR": 4, "MONTH": 7, "DAY": 10}

# Holdout controls this script actually implements. The status file must
# list exactly this map so documentation cannot claim more than the code does.
HOLDOUT_CONTROLS = {
    "status_shape_and_null_fields_when_not_ready": "ENFORCED",
    "frozen_fails_closed_without_private_manifest": "ENFORCED",
    "frozen_metadata_valid_hash_count_date_storage": "ENFORCED",
    "manifest_outside_repository": "ENFORCED",
    "manifest_hash_matches_status": "ENFORCED",
    "manifest_record_count_matches_and_minimum_150": "ENFORCED",
    "manifest_record_eligibility": "ENFORCED",
    "manifest_source_concentration_max_25_percent": "ENFORCED",
    "overlap_with_registry_transactions_and_repeat_sales": "ENFORCED",
    "overlap_with_published_seed_and_comps": "ENFORCED",
    "overlap_with_normalised_name_variants": "ENFORCED",
    "no_holdout_candidates_in_public_registry": "ENFORCED",
    "no_holdout_manifest_files_in_repository": "ENFORCED",
    "stratum_minimums": "NOT_IMPLEMENTED",
    "chronological_split": "NOT_IMPLEMENTED",
    "independent_naming_class_labels": "NOT_IMPLEMENTED",
    "evaluation_budget_and_logging": "NOT_IMPLEMENTED",
    "aggregate_only_access_for_developers": "NOT_IMPLEMENTED",
    "backtest_second_level_overlap_check": "NOT_IMPLEMENTED",
    "pages_artifact_excludes_research_files": "NOT_IMPLEMENTED",
}

# Production files that must never read the research registry.
PRODUCTION_FILES = ["js/valuation-engine.js", "js/valuation-ui.js", "scripts/generate_valuation_data.py", "valuation.html"]
RESEARCH_MARKERS = ["research/valuation-evidence", "transactions.v1.json", "seed-45.v1.json"]
SKIP_DIRS = {".git", "node_modules", "__pycache__", "_site"}


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def content_hash(payload):
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_partial_date(value, precision=None):
    """Earliest calendar date a partial ISO date can denote, or None."""
    if not isinstance(value, str):
        return None
    for prec, rx in DATE_RE.items():
        if rx.match(value) and precision in (None, prec):
            parts = [int(p) for p in value.split("-")] + [1, 1]
            try:
                return date(parts[0], parts[1], parts[2])
            except ValueError:
                return None
    return None


def precision_of(value):
    for prec, rx in DATE_RE.items():
        if isinstance(value, str) and rx.match(value):
            return prec
    return None


def precedes(earlier, later):
    """True when `later` is definitely before `earlier`, compared at the
    finest precision both dates share (2020-03-01 vs 2020-03-15 is caught)."""
    p1, p2 = precision_of(earlier), precision_of(later)
    if not p1 or not p2:
        return False
    n = min(PRECISION_LEN[p1], PRECISION_LEN[p2])
    return later[:n] < earlier[:n]


def normalise_domain(value):
    d = str(value or "").strip().lower().rstrip(".")
    if d.startswith("www."):
        d = d[4:]
    try:
        d = ".".join(label.encode("idna").decode("ascii") if label else label for label in d.split("."))
    except UnicodeError:
        pass
    return d


def name_keys(domain):
    d = normalise_domain(domain)
    sld = d.split(".", 1)[0]
    return d, sld, sld.replace("-", "")


def check_source(src, where, errors, principal=False):
    """A source counts only if it was read directly and checked against raw text."""
    if src.get("source_access_method") != "DOCUMENT_REVIEWED":
        errors.append(f"{where}: source must be DOCUMENT_REVIEWED (search summaries belong in leads)")
        return
    if src.get("source_type") not in ENUMS["source_type"] or src.get("source_type") == "NONE":
        errors.append(f"{where}: invalid source_type {src.get('source_type')!r}")
    if not str(src.get("source_url") or "").startswith("https://"):
        errors.append(f"{where}: source_url must be a non-empty https URL")
    if not src.get("source_name"):
        errors.append(f"{where}: source_name required")
    accessed = parse_partial_date(src.get("source_accessed_at"), "DAY")
    if accessed is None:
        errors.append(f"{where}: source_accessed_at must be an ISO date")
    if src.get("review_method") not in CHECKED_REVIEW:
        errors.append(f"{where}: review_method {src.get('review_method')!r} is not checked against the source text")
    if len(str(src.get("document_locator") or "")) < 8:
        errors.append(f"{where}: document_locator must identify the passage (e.g. note, section, headline)")
    if len(str(src.get("checked_quote") or "")) < 20:
        errors.append(f"{where}: checked_quote required (verbatim text checked against the source)")
    if not SHA_RE.match(str(src.get("document_sha256") or "")):
        errors.append(f"{where}: document_sha256 must be the SHA-256 of the reviewed document")


def check_rights(rights, where, errors):
    if not isinstance(rights, dict) or set(rights) != set(RIGHTS_KEYS):
        errors.append(f"{where}: rights must define exactly {', '.join(RIGHTS_KEYS)}")
        return
    for key in RIGHTS_KEYS:
        r = rights[key] or {}
        status, basis_type = r.get("status"), r.get("basis_type")
        if status not in RIGHTS_STATUS:
            errors.append(f"{where}: rights.{key}.status {status!r} invalid")
        if basis_type not in RIGHTS_BASIS:
            errors.append(f"{where}: rights.{key}.basis_type {basis_type!r} invalid")
        if len(str(r.get("basis") or "")) < 20:
            errors.append(f"{where}: rights.{key}.basis must explain the conclusion")
        if status in GRANTED and basis_type == "NONE":
            errors.append(f"{where}: rights.{key} granted without a basis")
        if basis_type in RIGHTS_NEEDS_REFERENCE and not r.get("reference"):
            errors.append(f"{where}: rights.{key} basis {basis_type} needs a reference (licence, permission or legal note)")
        if key in ("storage", "commercial_modelling", "redistribution") and status in GRANTED and basis_type == "PUBLIC_FACT_CITATION":
            errors.append(f"{where}: rights.{key} cannot be granted on public accessibility or citation alone")


def check_transaction(t, errors, as_of):
    where = t.get("transaction_id") or "<missing id>"
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
        if field in t and t[field] not in allowed:
            errors.append(f"{where}: {field} {t[field]!r} not in {sorted(allowed)}")
    if not isinstance(t["domain"], str) or not DOMAIN_RE.match(t["domain"]):
        errors.append(f"{where}: invalid domain {t['domain']!r}")

    # Price.
    price, disclosure = t["sale_price"], t["price_disclosure_status"]
    if price is not None and (not isinstance(price, int) or isinstance(price, bool) or price <= 0):
        errors.append(f"{where}: sale_price must be a positive integer or null")
    if t["currency"] not in CURRENCIES:
        errors.append(f"{where}: currency {t['currency']!r} not in {sorted(CURRENCIES)}")
    if disclosure in PRICED and price is None:
        errors.append(f"{where}: price_disclosure_status {disclosure} requires sale_price")
    if disclosure in {"UNDISCLOSED", "UNKNOWN"} and price is not None:
        errors.append(f"{where}: an {disclosure.lower()} price must have sale_price null (keep claims in price_claims)")

    # Scope: bundle and business totals are never one domain's price.
    scope = t["price_scope"]
    if scope not in SCOPE_BY_TYPE.get(t["transaction_type"], set()):
        errors.append(f"{where}: price_scope {scope} inconsistent with transaction_type {t['transaction_type']}")
    if scope == "BUNDLE_TOTAL":
        b = t["bundle"]
        if not isinstance(b, dict) or "domain_count" not in b or "other_assets" not in b or b.get("allocation") != "NOT_ALLOCATED":
            errors.append(f"{where}: BUNDLE_TOTAL needs bundle {{domain_count, other_assets, allocation: NOT_ALLOCATED}}")
        elif b["domain_count"] is not None and (not isinstance(b["domain_count"], int) or b["domain_count"] < 1):
            errors.append(f"{where}: bundle.domain_count must be a positive integer or null")
    elif t["bundle"] is not None:
        errors.append(f"{where}: bundle is only used with price_scope BUNDLE_TOTAL")

    # Dates.
    precision, sale_date = t["sale_date_precision"], t["sale_date"]
    if sale_date is None:
        if precision != "UNKNOWN":
            errors.append(f"{where}: sale_date null requires sale_date_precision UNKNOWN")
    else:
        sale = parse_partial_date(sale_date, precision)
        if precision == "UNKNOWN" or sale is None:
            errors.append(f"{where}: sale_date {sale_date!r} does not match precision {precision}")
        elif sale < EARLIEST_SALE or sale > as_of:
            errors.append(f"{where}: sale_date {sale_date} outside {EARLIEST_SALE}..{as_of}")
    if t["report_date"] is not None:
        report = parse_partial_date(t["report_date"])
        if report is None or report > as_of:
            errors.append(f"{where}: invalid or future report_date {t['report_date']!r}")
        elif sale_date is not None and precedes(sale_date, t["report_date"]):
            errors.append(f"{where}: report_date {t['report_date']} precedes sale_date {sale_date}")
    for field in ("source_accessed_at", "verified_at"):
        if t[field] is not None:
            d = parse_partial_date(t[field], "DAY")
            if d is None or d > as_of:
                errors.append(f"{where}: {field} must be a past ISO date (YYYY-MM-DD)")

    # Sources: principal, additional and leads.
    status, stype = t["evidence_status"], t["source_type"]
    principal = {k: t.get(k) for k in SOURCE_FIELDS if k != "published_date"}
    if stype == "NONE":
        if any(t[k] for k in ("source_name", "source_url", "document_locator", "checked_quote", "document_sha256")):
            errors.append(f"{where}: source_type NONE must not carry source details")
        if t["source_access_method"] != "NOT_ACCESSED" or t["review_method"] != "NONE":
            errors.append(f"{where}: source_type NONE requires NOT_ACCESSED and review_method NONE")
    else:
        check_source(principal, f"{where} principal source", errors, principal=True)
    for i, src in enumerate(t["additional_sources"]):
        if set(src) - set(SOURCE_FIELDS):
            errors.append(f"{where}: additional_sources[{i}] has unknown fields")
        check_source(src, f"{where} additional_sources[{i}]", errors)
    for i, lead in enumerate(t["leads"]):
        if set(lead) != set(LEAD_FIELDS):
            errors.append(f"{where}: leads[{i}] must have exactly {', '.join(LEAD_FIELDS)}")
        elif not str(lead["source_url"] or "").startswith("https://") or lead["source_type"] not in ENUMS["source_type"]:
            errors.append(f"{where}: leads[{i}] needs an https URL and a valid source_type")

    material = [c for c in t["conflicts"] if c.get("material")]
    for c in t["conflicts"]:
        if not isinstance(c.get("material"), bool) or not c.get("description"):
            errors.append(f"{where}: each conflict needs a description and a boolean 'material'")
    if not isinstance(t["valuation_caveats"], list) or not all(isinstance(v, str) and v for v in t["valuation_caveats"]):
        errors.append(f"{where}: valuation_caveats must be a list of non-empty strings")

    # Evidence status rules.
    if status == "VERIFIED":
        reasons = []
        if stype not in PRIMARY_SOURCE_TYPES:
            reasons.append(f"source_type {stype} is not primary evidence")
        if disclosure not in VERIFIABLE_PRICE or price is None:
            reasons.append(f"price disclosure {disclosure} is not verifiable")
        if not t["verified_at"] or len(str(t["verification_basis"] or "")) < 40:
            reasons.append("verified_at and a substantive verification_basis are required")
        quote = str(t["checked_quote"] or "").lower()
        if t["domain"].split(".")[0] not in quote or not re.search(r"\d", quote):
            reasons.append("checked_quote must name the domain and state a figure")
        if material:
            reasons.append("material conflicts are unresolved")
        if reasons:
            errors.append(f"{where}: unsupported VERIFIED claim ({'; '.join(reasons)})")
    elif t["verified_at"] is not None:
        errors.append(f"{where}: verified_at set on a {status} record")
    if status in {"REPORTED", "DISPUTED"} and stype not in REPORTABLE_SOURCE_TYPES:
        errors.append(f"{where}: {status} requires a reviewed source of a reportable class, not {stype}")
    if status == "DISPUTED" and not material:
        errors.append(f"{where}: DISPUTED requires at least one material conflict")
    if status in {"REPORTED", "VERIFIED"} and material:
        errors.append(f"{where}: {status} with an unresolved material conflict must be DISPUTED")
    if status == "UNVERIFIED" and stype != "NONE":
        errors.append(f"{where}: UNVERIFIED records carry no principal source (use leads)")

    # Rights.
    check_rights(t["rights"], where, errors)

    # Roles: necessary conditions only. Status never assigns a role.
    role = t["calibration_role"]
    if role == "CALIBRATION_CANDIDATE":
        reasons = []
        if status not in {"VERIFIED", "REPORTED"}:
            reasons.append(f"evidence {status}")
        if t["transaction_type"] != "DOMAIN_ONLY" or scope != "SINGLE_DOMAIN":
            reasons.append(f"transaction_type {t['transaction_type']} / price_scope {scope}")
        if disclosure not in VERIFIABLE_PRICE:
            reasons.append(f"price {disclosure}")
        if t["consideration_type"] not in {"CASH", "UNKNOWN"}:
            reasons.append(f"consideration {t['consideration_type']}")
        rights = t["rights"] if isinstance(t["rights"], dict) else {}
        for key in ("storage", "commercial_modelling"):
            if (rights.get(key) or {}).get("status") not in GRANTED:
                reasons.append(f"{key} rights {(rights.get(key) or {}).get('status')}")
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

    by_domain = {}
    for t in txs:
        by_domain.setdefault(t.get("domain"), []).append(t)
    for domain, group in by_domain.items():
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
        statuses = {tx_ids[t]["evidence_status"] for t in r.get("transaction_ids", []) if t in tx_ids}
        if r.get("evidence_found") is False and statuses - {"UNVERIFIED"}:
            errors.append(f"investigation {d}: evidence_found false but a linked transaction has reviewed evidence")
        if r.get("evidence_found") is True and statuses <= {"UNVERIFIED"}:
            errors.append(f"investigation {d}: evidence_found true but every linked transaction is UNVERIFIED")


def holdout_eligibility(t):
    """Reasons a manifest record is not eligible under holdout-protocol/v1 §2."""
    reasons = []
    if t.get("evidence_status") not in {"VERIFIED", "REPORTED"}:
        reasons.append(f"evidence {t.get('evidence_status')}")
    if t.get("transaction_type") != "DOMAIN_ONLY" or t.get("price_scope") != "SINGLE_DOMAIN":
        reasons.append("not a single-domain sale")
    if t.get("price_disclosure_status") not in {"EXACT", "ROUNDED"} or t.get("sale_price") is None:
        reasons.append(f"price {t.get('price_disclosure_status')}")
    if t.get("consideration_type") not in {"CASH", "UNKNOWN"}:
        reasons.append(f"consideration {t.get('consideration_type')}")
    if any(c.get("material") for c in t.get("conflicts", [])):
        reasons.append("material conflict")
    rights = t.get("rights") or {}
    for key in ("storage", "commercial_modelling"):
        if (rights.get(key) or {}).get("status") not in GRANTED:
            reasons.append(f"{key} rights not established")
    if t.get("calibration_role") != "HOLDOUT_CANDIDATE":
        reasons.append("calibration_role must be HOLDOUT_CANDIDATE")
    return reasons


def calibration_name_index(registry, seed, comps):
    """Every name the calibration side has touched, keyed three ways."""
    names = []
    for t in registry.get("transactions", []):
        names.append((t.get("domain"), f"registry {t.get('transaction_id')}"))
    for s in seed.get("sales", []):
        names.append((s.get("domain"), "published seed"))
    for s in comps.get("sales", []):
        names.append((s.get("domain"), "published comps"))
    index = {"domain": {}, "sld": {}, "compact": {}}
    for domain, origin in names:
        d, sld, compact = name_keys(domain)
        index["domain"].setdefault(d, origin)
        index["sld"].setdefault(sld, origin)
        index["compact"].setdefault(compact, origin)
    return index


def check_holdout(status, registry, errors, manifest=None, manifest_path=None, seed=None, comps=None, as_of=None):
    as_of = as_of or date.today()
    state = status.get("status")
    if state not in {"NOT_READY", "FROZEN"}:
        errors.append("holdout: status must be one of ['FROZEN', 'NOT_READY']")
        return
    if status.get("protocol_version") != HOLDOUT_PROTOCOL_VERSION:
        errors.append(f"holdout: protocol_version must be {HOLDOUT_PROTOCOL_VERSION!r}")
    if status.get("controls") != HOLDOUT_CONTROLS:
        errors.append("holdout: 'controls' must match the controls implemented by this validator exactly")

    if state == "NOT_READY":
        for key in ("frozen_at", "manifest_sha256", "record_count", "storage_location"):
            if status.get(key) is not None:
                errors.append(f"holdout: {key} must be null while NOT_READY")
        if manifest is not None:
            errors.append("holdout: a manifest was supplied but the status is NOT_READY")
        return

    # FROZEN: metadata first, then fail closed unless the private manifest verifies.
    if not SHA_RE.match(str(status.get("manifest_sha256") or "")):
        errors.append("holdout: FROZEN manifest_sha256 must be 64 lowercase hex characters")
    count = status.get("record_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < HOLDOUT_MIN_RECORDS:
        errors.append(f"holdout: FROZEN record_count must be an integer >= {HOLDOUT_MIN_RECORDS}")
    frozen = parse_partial_date(status.get("frozen_at"), "DAY")
    if frozen is None or frozen > as_of:
        errors.append("holdout: FROZEN frozen_at must be a past ISO date")
    storage = str(status.get("storage_location") or "")
    if len(storage) < 10 or re.search(r"https?://|/|\\", storage):
        errors.append("holdout: storage_location must describe private storage, not a URL or path")

    if manifest is None:
        errors.append("holdout: FROZEN cannot be accepted without verifying the private manifest "
                      "(run with --holdout-manifest); refusing (fail-closed)")
        return

    if manifest_path is not None:
        try:
            Path(manifest_path).resolve().relative_to(REPO_ROOT)
            errors.append("holdout: the manifest must be stored outside the repository")
        except ValueError:
            pass
    if manifest.get("kind") != MANIFEST_KIND or manifest.get("protocol_version") != HOLDOUT_PROTOCOL_VERSION:
        errors.append(f"holdout: manifest must declare kind {MANIFEST_KIND!r} and {HOLDOUT_PROTOCOL_VERSION!r}")
    if content_hash(manifest) != status.get("manifest_sha256"):
        errors.append("holdout: manifest hash does not match manifest_sha256 in the status file")

    records = manifest.get("transactions", [])
    if len(records) != count:
        errors.append(f"holdout: manifest has {len(records)} records, status says {count}")
    if len(records) < HOLDOUT_MIN_RECORDS:
        errors.append(f"holdout: manifest has fewer than {HOLDOUT_MIN_RECORDS} records")
    schema_errors = []
    ids = set()
    for t in records:
        check_transaction(dict(t, calibration_role="EXCLUDED"), schema_errors, as_of)
        reasons = holdout_eligibility(t)
        if reasons:
            errors.append(f"holdout: {t.get('transaction_id')} ineligible ({'; '.join(reasons)})")
        if t.get("transaction_id") in ids:
            errors.append(f"holdout: duplicate transaction_id {t.get('transaction_id')}")
        ids.add(t.get("transaction_id"))
    errors.extend(f"holdout record: {e}" for e in schema_errors)

    sources = {}
    for t in records:
        sources[t.get("source_name")] = sources.get(t.get("source_name"), 0) + 1
    if records and max(sources.values()) / len(records) > HOLDOUT_MAX_SOURCE_SHARE:
        top = max(sources, key=sources.get)
        errors.append(f"holdout: source {top!r} supplies more than {int(HOLDOUT_MAX_SOURCE_SHARE * 100)}% of records")

    registry_ids = {t.get("transaction_id") for t in registry.get("transactions", [])}
    index = calibration_name_index(registry, seed or {}, comps or {})
    for t in records:
        tid = t.get("transaction_id")
        if tid in registry_ids:
            errors.append(f"holdout: {tid} also exists in the public registry")
        d, sld, compact = name_keys(t.get("domain"))
        if d in index["domain"]:
            errors.append(f"holdout: {t.get('domain')} overlaps {index['domain'][d]} (same domain or repeat sale)")
        elif sld in index["sld"]:
            errors.append(f"holdout: {t.get('domain')} shares second-level name {sld!r} with {index['sld'][sld]}")
        elif compact in index["compact"]:
            errors.append(f"holdout: {t.get('domain')} is a hyphenation variant of a name in {index['compact'][compact]}")


def check_public_boundary(errors, root=REPO_ROOT):
    holdout_dir = root / "research" / "valuation-evidence" / "holdout"
    if holdout_dir.is_dir():
        for path in holdout_dir.iterdir():
            if path.name != HOLDOUT_STATUS_PATH.name:
                errors.append(f"holdout: {path.relative_to(root)} must not be committed (holdout data stays private)")
    name_rx = re.compile(r"holdout.*manifest|manifest.*holdout", re.I)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if name_rx.search(name):
                errors.append(f"{path.relative_to(root)}: holdout manifests must never be stored in the repository")
                continue
            if name.endswith(".json") and path.stat().st_size < 2_000_000:
                if MANIFEST_KIND in path.read_text(encoding="utf-8", errors="ignore"):
                    errors.append(f"{path.relative_to(root)}: contains a holdout manifest")
    for rel in PRODUCTION_FILES:
        path = root / rel
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for marker in RESEARCH_MARKERS:
                if marker in text:
                    errors.append(f"{rel}: production code references research registry ({marker!r})")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Validate the Sprint 1A evidence registry")
    parser.add_argument("--write", action="store_true", help="recompute registry header and canonicalise files")
    parser.add_argument("--as-of", help="reference date (YYYY-MM-DD) for future-date checks")
    parser.add_argument("--holdout-manifest", help="path to the PRIVATE holdout manifest (outside the repository)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()

    registry = load(REGISTRY_PATH)
    investigation = load(INVESTIGATION_PATH)
    holdout = load(HOLDOUT_STATUS_PATH)
    seed = load(SEED_PATH)
    comps = load(COMPS_PATH)
    manifest = load(args.holdout_manifest) if args.holdout_manifest else None

    if args.write:
        header = check_registry(registry, [], as_of)
        registry.update(header)
        REGISTRY_PATH.write_text(canonical(registry), encoding="utf-8")
        INVESTIGATION_PATH.write_text(canonical(investigation), encoding="utf-8")
        HOLDOUT_STATUS_PATH.write_text(canonical(holdout), encoding="utf-8")

    errors = []
    check_registry(registry, errors, as_of)
    check_investigation(investigation, registry, seed, errors)
    check_holdout(holdout, registry, errors, manifest, args.holdout_manifest, seed, comps, as_of)
    check_public_boundary(errors)
    for path, payload in ((REGISTRY_PATH, registry), (INVESTIGATION_PATH, investigation), (HOLDOUT_STATUS_PATH, holdout)):
        if path.read_text(encoding="utf-8") != canonical(payload):
            errors.append(f"{path.relative_to(REPO_ROOT)}: not in canonical form (run with --write)")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    c = registry["status_counts"]
    not_impl = sum(1 for v in HOLDOUT_CONTROLS.values() if v == "NOT_IMPLEMENTED")
    print(f"PASS: evidence registry valid — {registry['transaction_count']} transactions "
          f"(VERIFIED {c['VERIFIED']}, REPORTED {c['REPORTED']}, DISPUTED {c['DISPUTED']}, UNVERIFIED {c['UNVERIFIED']}); "
          f"{len(investigation['records'])} seed investigations; holdout {holdout['status']} "
          f"({len(HOLDOUT_CONTROLS) - not_impl} controls enforced, {not_impl} NOT_IMPLEMENTED)")


if __name__ == "__main__":
    main()
