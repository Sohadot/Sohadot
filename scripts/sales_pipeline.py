#!/usr/bin/env python3
"""Sprint 1B candidate comparable-sales pipeline (research only).

Every sale moves through explicit states:

    DISCOVERED -> SOURCE_REVIEWED -> ELIGIBLE -> CALIBRATION_ADMITTED
                                         \\-> HOLDOUT_RESERVED   (private storage only)
    any state  -> REJECTED

A pipeline record is a Transaction Evidence Registry v1 record (see
docs/valuation-evidence/TRANSACTION_EVIDENCE_REGISTRY_V1.md) plus a
``pipeline`` block. The state is never chosen by hand: ``assess_all`` computes
it from the evidence, scope, price type, consideration, rights and duplicate
checks, and ``validate`` fails if a record declares anything else.

Fail-closed rules:
- CALIBRATION_ADMITTED is refused while ADMISSION_OPEN is False. Opening it
  needs a separate owner decision (Sprint 1B does not select a production
  algorithm before the independent holdout is ready).
- HOLDOUT_RESERVED records are refused in any file in this public repository.
  Reserved records live only in private storage; the public report shows a
  count taken from the holdout status file.

Usage:
    python3 scripts/sales_pipeline.py --report            # print pilot quality report
    python3 scripts/sales_pipeline.py --write-report      # regenerate the committed report
    python3 scripts/sales_pipeline.py --check             # fail if the committed report is stale
    python3 scripts/sales_pipeline.py --validate FILE     # validate a pipeline JSON file
"""

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_evidence_registry as reg  # noqa: E402

REPO_ROOT = reg.REPO_ROOT
REPORT_PATH = REPO_ROOT / "docs" / "valuation-evidence" / "sprint-1b" / "PILOT_QUALITY_REPORT.md"
PIPELINE_VERSION = "sales-pipeline/v1-candidate"

STATES = ("DISCOVERED", "SOURCE_REVIEWED", "ELIGIBLE", "CALIBRATION_ADMITTED", "REJECTED", "HOLDOUT_RESERVED")
TRANSITIONS = {
    "DISCOVERED": {"SOURCE_REVIEWED", "REJECTED"},
    "SOURCE_REVIEWED": {"ELIGIBLE", "REJECTED", "DISCOVERED"},
    "ELIGIBLE": {"CALIBRATION_ADMITTED", "HOLDOUT_RESERVED", "REJECTED", "SOURCE_REVIEWED"},
    "CALIBRATION_ADMITTED": {"REJECTED", "SOURCE_REVIEWED"},
    "HOLDOUT_RESERVED": set(),
    "REJECTED": {"DISCOVERED", "SOURCE_REVIEWED"},
}
ADMISSION_OPEN = False

# What a stated price is evidence of. Only COMPLETED_SALE can become ELIGIBLE,
# and only with an explicit completion-evidence basis.
PRICE_TYPES = {
    "COMPLETED_SALE",               # the transaction closed (needs completion_evidence)
    "ANNOUNCED_AGREEMENT",          # agreed or pending; closing not shown
    "REPORTED_PRICE",               # a price is reported; completion not stated
    "AUCTION_RESULT_UNCONFIRMED",   # auction closed; payment not confirmed
    "AUCTION_RESULT_UNPAID",        # auction winner did not pay
    "AUCTION_BID",
    "ASKING_PRICE",
    "UNDISCLOSED",
    "UNKNOWN",
}
REJECTED_PRICE_TYPES = {"ASKING_PRICE", "AUCTION_BID", "AUCTION_RESULT_UNPAID"}
UNPROVEN_COMPLETION = {"ANNOUNCED_AGREEMENT", "REPORTED_PRICE", "AUCTION_RESULT_UNCONFIRMED"}
# Who or what shows that the sale closed. A price alone never does.
COMPLETION_BASES = {
    "SETTLEMENT_IN_FILING_OR_COURT_RECORD",  # filing or court record describes the completed transfer
    "VENUE_RECORD_OF_COMPLETION",            # marketplace or escrow record of a completed, paid sale
    "PARTY_CONFIRMED_COMPLETION",            # buyer, seller or broker of record states it closed
    "SOURCE_STATES_COMPLETED",               # reviewed source explicitly says the sale was completed
}
# Where a sale date comes from. Report publication dates and reporting
# windows are never sale dates: they are kept in reporting_window.
SALE_DATE_BASES = {"EXPLICIT_IN_SOURCE", "NOT_ESTABLISHED"}
# Who granted storage/modelling rights. A secondary publisher's permission
# covers its own compilation; it does not establish rights that originate
# with the venue or another upstream data owner.
RIGHTS_GRANTOR_ROLES = {"ORIGINATING_VENUE", "TRANSACTION_PARTY", "PUBLIC_RECORD", "SECONDARY_PUBLISHER", "NONE"}
NAMING_CLASSES = {"DICTIONARY_WORD", "COMPOUND_OR_KEYWORD", "BRANDABLE_INVENTED", "PERSONAL_NAME",
                  "NUMERIC_OR_ACRONYM", "UNASSIGNED"}
NAMING_BASIS = {"HUMAN_RULES_V1", "UNASSIGNED"}
TIER_BY_SOURCE = {
    "REGULATORY_FILING": "A", "COURT_RECORD": "A",
    "PARTY_ANNOUNCEMENT": "B", "MARKETPLACE_RECORD": "B",
    "TRADE_PUBLICATION": "C", "GENERAL_NEWS": "C",
    "AGGREGATOR_DATABASE": "D", "TERTIARY_REFERENCE": "E",
}
CASH_LIKE = {"CASH", "UNKNOWN"}
PRICE_BANDS = (("<$2.5k", 2_500), ("$2.5k-$10k", 10_000), ("$10k-$100k", 100_000),
               ("$100k-$1M", 1_000_000), (">=$1M", float("inf")))
MARKET_SIDE = {"END_USER_ACQUISITION": "RETAIL_END_USER", "INVESTOR_TRADE": "WHOLESALE_INVESTOR", "UNKNOWN": "UNKNOWN"}

# Duplicate detection thresholds (same normalised domain).
DUP_AMOUNT_TOLERANCE = 0.02   # 2% (rounding in reports)
DUP_MAX_DAYS = 60             # reports of one sale cluster within weeks
REPEAT_MIN_DAYS = 180         # further apart: a separate (repeat) sale

# Targets for the first 500 qualified transactions (see FIRST_500_PLAN).
TARGET_TOTAL = 500
TARGET_BY_BAND = {"<$2.5k": 125, "$2.5k-$10k": 150, "$10k-$100k": 150, "$100k-$1M": 50, ">=$1M": 25}

REJECTION_REASONS = {
    "NOT_A_COMPLETED_SALE": "asking price, auction bid or unpaid auction result",
    "PRICE_NOT_DISCLOSED": "price never disclosed",
    "IMPRECISE_PRICE": "approximate or lower-bound price",
    "NOT_SINGLE_DOMAIN": "bundle, domain plus assets, or business acquisition",
    "NON_CASH_CONSIDERATION": "stock, crypto, note or structured consideration",
    "RIGHTS_NOT_PERMITTED": "storage or modelling expressly not permitted",
    "DUPLICATE_REPORT": "another record already holds this transaction",
}
BLOCKERS = {
    "NO_REVIEWED_SOURCE": "no directly reviewed source (leads or unsourced claims only)",
    "MATERIAL_CONFLICT_UNRESOLVED": "material conflict about the transaction itself",
    "PRICE_TYPE_UNKNOWN": "not yet classified (completed, agreed, reported, bid or asking)",
    "COMPLETION_NOT_EVIDENCED": "no explicit evidence that the sale closed (agreed, reported or unconfirmed)",
    "SCOPE_UNKNOWN": "not yet shown to be a single-domain sale",
    "SALE_DATE_UNKNOWN": "no sale date stated by evidence (report dates and windows do not count)",
    "FX_BASIS_MISSING": "non-USD amount without a recorded conversion basis",
    "RIGHTS_NOT_ESTABLISHED": "storage or commercial-modelling right not established",
    "UPSTREAM_RIGHTS_UNCONFIRMED": "rights granted by a secondary publisher; upstream venue or owner rights not confirmed",
    "DUPLICATE_UNRESOLVED": "possible duplicate or repeat sale needs review",
    "BUNDLE_SUSPECTED": "shares a source passage and amount with another domain",
}


# --- Pilot mapping from the Sprint 1A registry --------------------------------

def price_type_from_registry(t):
    """Registry v1 does not classify completion, so a stated price maps to
    REPORTED_PRICE, never COMPLETED_SALE. A reviewer must record the
    completion evidence before a record can become eligible."""
    if t["price_disclosure_status"] == "UNDISCLOSED":
        return "UNDISCLOSED"
    if t["evidence_status"] in ("VERIFIED", "REPORTED", "DISPUTED") and t["sale_price"] is not None:
        return "REPORTED_PRICE"
    return "UNKNOWN"


def source_family_from_registry(t):
    """(source_family, relay_publisher). A family is the originating data
    owner (venue, party, filer or court). Press relays an origin it may not
    name, so a press source gives a relay, not a family."""
    if t["source_type"] in ("REGULATORY_FILING", "COURT_RECORD", "PARTY_ANNOUNCEMENT", "MARKETPLACE_RECORD"):
        return t["source_name"], None
    if t["source_type"] in ("TRADE_PUBLICATION", "GENERAL_NEWS"):
        return "UNKNOWN_ORIGIN", t["source_name"]
    return None, None


def pipeline_from_registry(t):
    """Wrap a registry v1 transaction in an (unassessed) pipeline block."""
    amount = t["sale_price"]
    usd = amount if (amount is not None and t["currency"] == "USD") else None
    record = dict(t)
    record["pipeline"] = {
        "state": None,
        "price_type": price_type_from_registry(t),
        "completion_evidence": None,
        # Registry v1 does not record where its sale dates come from, so none
        # is treated as explicit until re-reviewed.
        "sale_date_basis": "NOT_ESTABLISHED",
        "reporting_window": None,
        "source_family": source_family_from_registry(t)[0],
        "relay_publisher": source_family_from_registry(t)[1],
        "rights_provenance": {"granted_by_role": "NONE", "grantor": None,
                              "upstream_origin": None, "upstream_rights_confirmed": False},
        "original_amount": amount,
        "original_currency": t["currency"] if amount is not None else None,
        "amount_usd": usd,
        "fx_basis": None,
        "source_reliability_tier": TIER_BY_SOURCE.get(t["source_type"]),
        "naming_class": "UNASSIGNED",
        "naming_class_basis": "UNASSIGNED",
        "duplicate_of": None,
        "repeat_sale_of": [],
        "blockers": [],
        "rejection_reasons": [],
        "second_review": None,
        "admission": None,
        "state_history": [{"state": "DISCOVERED", "at": t.get("verified_at") or "2026-10-09",
                           "note": "Imported from Transaction Evidence Registry v1 (Sprint 1A)."}],
    }
    return record


def pilot_records():
    registry = reg.load(reg.REGISTRY_PATH)
    records = [pipeline_from_registry(t) for t in registry["transactions"]]
    # The registry already records repeat sales as separate reviewed
    # transactions, so pairs the detector classes as REPEAT_SALE are linked.
    # Anything else stays unresolved for a reviewer.
    by_id = {r["transaction_id"]: r for r in records}
    for a, b, kind in find_relationships(records):
        if kind == "REPEAT_SALE":
            by_id[b]["pipeline"]["repeat_sale_of"].append(a)
    return assess_all(records)


# --- Duplicate, repeat-sale and bundle detection ------------------------------

def _days_apart(a, b):
    da, db = reg.parse_partial_date(a), reg.parse_partial_date(b)
    if da is None or db is None:
        return None
    # Compare at the coarser precision so "2019" vs "2019-05-30" is not 150 days.
    pa, pb = reg.precision_of(a), reg.precision_of(b)
    if "YEAR" in (pa, pb):
        # Adjacent years at year precision can be one sale reported late.
        gap = abs(da.year - db.year)
        return 0 if gap == 0 else (None if gap == 1 else gap * 365)
    if "MONTH" in (pa, pb):
        return abs((da.year - db.year) * 12 + da.month - db.month) * 30
    return abs((da - db).days)


def classify_pair(a, b):
    """Relationship between two records of the same normalised domain."""
    pa, pb = a["pipeline"], b["pipeline"]
    amt_a, amt_b = pa["amount_usd"], pb["amount_usd"]
    days = _days_apart(a["sale_date"], b["sale_date"])
    same_amount = (amt_a is not None and amt_b is not None
                   and abs(amt_a - amt_b) <= DUP_AMOUNT_TOLERANCE * max(amt_a, amt_b))
    if days is not None and days >= REPEAT_MIN_DAYS:
        return "REPEAT_SALE"
    if same_amount and days is not None and days <= DUP_MAX_DAYS:
        return "DUPLICATE_REPORT"
    return "AMBIGUOUS"


def find_relationships(records):
    by_domain = {}
    for r in records:
        by_domain.setdefault(reg.normalise_domain(r["domain"]), []).append(r)
    pairs = []
    for group in by_domain.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                pairs.append((a["transaction_id"], b["transaction_id"], classify_pair(a, b)))
    return pairs


def find_bundle_suspects(records):
    """Different domains citing the same passage with the same amount."""
    seen = {}
    for r in records:
        if r["source_url"] and r["document_locator"] and r["pipeline"]["amount_usd"] is not None:
            key = (r["source_url"], r["document_locator"], round(r["pipeline"]["amount_usd"]))
            seen.setdefault(key, []).append(r)
    suspects = set()
    for group in seen.values():
        if len({reg.normalise_domain(r["domain"]) for r in group}) > 1:
            suspects.update(r["transaction_id"] for r in group if r["price_scope"] == "SINGLE_DOMAIN")
    return suspects


# --- State assessment ---------------------------------------------------------

def _granted(rights, key):
    return rights[key]["status"] in reg.GRANTED


def completion_evidence_ok(ev):
    """An explicit basis, tied to a located passage, that the sale closed."""
    return (isinstance(ev, dict) and ev.get("basis") in COMPLETION_BASES
            and len(str(ev.get("locator") or "")) >= 8 and len(str(ev.get("quote") or "")) >= 10)


def sale_date_evidenced(t):
    """A sale date counts only when the evidence states it. A reporting
    window or publication date never stands in for it."""
    p = t["pipeline"]
    return (t["sale_date"] is not None and t["sale_date_precision"] != "UNKNOWN"
            and p.get("sale_date_basis") == "EXPLICIT_IN_SOURCE")


def upstream_rights_ok(prov):
    """Rights granted by a secondary publisher do not cover data that
    originates with a venue or other owner unless that is confirmed."""
    if not isinstance(prov, dict):
        return False
    role = prov.get("granted_by_role")
    if role in ("ORIGINATING_VENUE", "TRANSACTION_PARTY", "PUBLIC_RECORD"):
        return bool(prov.get("grantor"))
    if role == "SECONDARY_PUBLISHER":
        return bool(prov.get("grantor")) and prov.get("upstream_rights_confirmed") is True
    return False


def assess(record, unresolved_dupes=frozenset(), bundle_suspects=frozenset()):
    """Return (state, blockers, rejection_reasons) computed from the record."""
    t, p = record, record["pipeline"]
    rejections, blockers = [], []

    if p["price_type"] in REJECTED_PRICE_TYPES:
        rejections.append("NOT_A_COMPLETED_SALE")
    elif p["price_type"] == "UNDISCLOSED" or t["price_disclosure_status"] == "UNDISCLOSED":
        rejections.append("PRICE_NOT_DISCLOSED")
    elif p["price_type"] in UNPROVEN_COMPLETION:
        blockers.append("COMPLETION_NOT_EVIDENCED")
    elif p["price_type"] == "COMPLETED_SALE":
        if not completion_evidence_ok(p.get("completion_evidence")):
            blockers.append("COMPLETION_NOT_EVIDENCED")
    else:
        blockers.append("PRICE_TYPE_UNKNOWN")
    if t["price_disclosure_status"] in ("APPROXIMATE", "LOWER_BOUND"):
        rejections.append("IMPRECISE_PRICE")
    if t["transaction_type"] not in ("DOMAIN_ONLY", "UNKNOWN") or t["price_scope"] in ("BUNDLE_TOTAL", "BUSINESS_TOTAL"):
        rejections.append("NOT_SINGLE_DOMAIN")
    elif t["transaction_type"] == "UNKNOWN" or t["price_scope"] == "UNKNOWN":
        blockers.append("SCOPE_UNKNOWN")
    if t["consideration_type"] not in CASH_LIKE:
        rejections.append("NON_CASH_CONSIDERATION")
    if any(t["rights"][k]["status"] == "NOT_PERMITTED" for k in ("storage", "commercial_modelling")):
        rejections.append("RIGHTS_NOT_PERMITTED")
    if p["duplicate_of"]:
        rejections.append("DUPLICATE_REPORT")

    reviewed = t["evidence_status"] in ("VERIFIED", "REPORTED", "DISPUTED")
    if not reviewed:
        blockers.append("NO_REVIEWED_SOURCE")
    if t["evidence_status"] == "DISPUTED":
        blockers.append("MATERIAL_CONFLICT_UNRESOLVED")
    if not sale_date_evidenced(t):
        blockers.append("SALE_DATE_UNKNOWN")
    if p["original_amount"] is not None and p["original_currency"] != "USD" and not p["fx_basis"]:
        blockers.append("FX_BASIS_MISSING")
    if not (_granted(t["rights"], "storage") and _granted(t["rights"], "commercial_modelling")):
        if "RIGHTS_NOT_PERMITTED" not in rejections:
            blockers.append("RIGHTS_NOT_ESTABLISHED")
    elif not upstream_rights_ok(p.get("rights_provenance")):
        blockers.append("UPSTREAM_RIGHTS_UNCONFIRMED")
    if t["transaction_id"] in unresolved_dupes:
        blockers.append("DUPLICATE_UNRESOLVED")
    if t["transaction_id"] in bundle_suspects:
        blockers.append("BUNDLE_SUSPECTED")

    if rejections:
        state = "REJECTED"
    elif not reviewed:
        state = "DISCOVERED"
    elif blockers:
        state = "SOURCE_REVIEWED"
    else:
        state = "ELIGIBLE"
    return state, sorted(blockers), sorted(rejections)


def unresolved_duplicates(records):
    ids = {r["transaction_id"]: r for r in records}
    unresolved = set()
    for a, b, rel in find_relationships(records):
        ra, rb = ids[a]["pipeline"], ids[b]["pipeline"]
        if rel == "REPEAT_SALE":
            if a not in rb["repeat_sale_of"] and b not in ra["repeat_sale_of"]:
                unresolved.update((a, b))
        elif rel == "DUPLICATE_REPORT":
            if ra["duplicate_of"] != b and rb["duplicate_of"] != a:
                unresolved.update((a, b))
        else:
            if not (ra["duplicate_of"] in (b,) or rb["duplicate_of"] in (a,)
                    or a in rb["repeat_sale_of"] or b in ra["repeat_sale_of"]):
                unresolved.update((a, b))
    return unresolved


def assess_all(records):
    dupes = unresolved_duplicates(records)
    bundles = find_bundle_suspects(records)
    out = []
    for r in records:
        r = dict(r)
        p = dict(r["pipeline"])
        state, blockers, rejections = assess({**r, "pipeline": p}, dupes, bundles)
        p.update(state=state, blockers=blockers, rejection_reasons=rejections)
        r["pipeline"] = p
        out.append(r)
    return out


# --- Validation ---------------------------------------------------------------

def validate(records, errors):
    """Check declared pipeline states against the computed ones."""
    ids = [r.get("transaction_id") for r in records]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"{dup}: duplicate transaction_id")
    known = set(ids)
    dupes = unresolved_duplicates(records)
    bundles = find_bundle_suspects(records)
    for r in records:
        where = r.get("transaction_id")
        p = r.get("pipeline")
        if not isinstance(p, dict):
            errors.append(f"{where}: missing pipeline block")
            continue
        reg.check_rights(r.get("rights"), where, errors)
        declared = p.get("state")
        if declared not in STATES:
            errors.append(f"{where}: invalid state {declared!r}")
            continue
        if p.get("price_type") not in PRICE_TYPES:
            errors.append(f"{where}: invalid price_type {p.get('price_type')!r}")
        if p.get("price_type") == "COMPLETED_SALE" and not completion_evidence_ok(p.get("completion_evidence")):
            errors.append(f"{where}: COMPLETED_SALE needs completion_evidence (basis, locator, quote); a price alone is not evidence of completion")
        if p.get("sale_date_basis") not in SALE_DATE_BASES:
            errors.append(f"{where}: sale_date_basis must be one of {sorted(SALE_DATE_BASES)} (report dates are not sale dates)")
        win = p.get("reporting_window")
        if win is not None and (not isinstance(win, dict) or not win.get("start") or not win.get("end")):
            errors.append(f"{where}: reporting_window needs start and end")
        if (win and r.get("sale_date") and p.get("sale_date_basis") == "EXPLICIT_IN_SOURCE"
                and r["sale_date"] in (win.get("start"), win.get("end")) and not p.get("sale_date_note")):
            errors.append(f"{where}: sale_date equals a reporting-window boundary; record sale_date_note citing the explicit date")
        prov = p.get("rights_provenance")
        if not isinstance(prov, dict) or prov.get("granted_by_role") not in RIGHTS_GRANTOR_ROLES:
            errors.append(f"{where}: rights_provenance.granted_by_role must be one of {sorted(RIGHTS_GRANTOR_ROLES)}")
        if p.get("naming_class") not in NAMING_CLASSES or p.get("naming_class_basis") not in NAMING_BASIS:
            errors.append(f"{where}: naming_class must be assigned by documented human rules or UNASSIGNED")
        elif (p["naming_class"] == "UNASSIGNED") != (p["naming_class_basis"] == "UNASSIGNED"):
            errors.append(f"{where}: naming_class and naming_class_basis disagree")
        if p.get("duplicate_of") and p["duplicate_of"] not in known:
            errors.append(f"{where}: duplicate_of points to unknown record {p['duplicate_of']}")
        for other in p.get("repeat_sale_of") or []:
            if other not in known:
                errors.append(f"{where}: repeat_sale_of points to unknown record {other}")
        if declared == "HOLDOUT_RESERVED":
            errors.append(f"{where}: HOLDOUT_RESERVED records must never be stored in the public repository")
            continue
        state, blockers, rejections = assess(r, dupes, bundles)
        if declared == "CALIBRATION_ADMITTED":
            if not ADMISSION_OPEN:
                errors.append(f"{where}: CALIBRATION_ADMITTED refused; admission is closed until the owner authorises it")
            if state != "ELIGIBLE":
                errors.append(f"{where}: CALIBRATION_ADMITTED but computed state is {state}")
            if not p.get("second_review") or not p.get("admission"):
                errors.append(f"{where}: admission needs a second review and an approved admission record")
        elif declared != state:
            errors.append(f"{where}: declared state {declared} but evidence supports {state}")
        if sorted(p.get("blockers") or []) != blockers:
            errors.append(f"{where}: blockers {p.get('blockers')} do not match computed {blockers}")
        if sorted(p.get("rejection_reasons") or []) != rejections:
            errors.append(f"{where}: rejection_reasons {p.get('rejection_reasons')} do not match computed {rejections}")
        history = p.get("state_history") or []
        if not history or history[0].get("state") != "DISCOVERED":
            errors.append(f"{where}: state_history must start at DISCOVERED")
        for prev, nxt in zip(history, history[1:]):
            if nxt.get("state") not in TRANSITIONS.get(prev.get("state"), set()):
                errors.append(f"{where}: illegal transition {prev.get('state')} -> {nxt.get('state')}")
    return errors


# --- Quality report -----------------------------------------------------------

def price_band(usd):
    if usd is None:
        return "unknown"
    for name, upper in PRICE_BANDS:
        if usd < upper:
            return name
    return PRICE_BANDS[-1][0]


def independence_summary(records):
    """Source-family and relay concentration among priced, reviewed records.

    Venue diversity reported by one relay is not family independence: rows
    from several venues that all reach Sohadot through one publisher share
    that publisher's selection, errors and rights. Both shares are reported.
    """
    pool = [r for r in records if r["evidence_status"] in ("VERIFIED", "REPORTED") and r["pipeline"]["amount_usd"] is not None]
    if not pool:
        return {"records": 0, "max_family_share": None, "max_relay_share": None, "unknown_origin_share": None}
    fam = Counter(r["pipeline"]["source_family"] or "none" for r in pool)
    relay = Counter(r["pipeline"]["relay_publisher"] for r in pool if r["pipeline"]["relay_publisher"])
    share = lambda c: round(max(c.values()) / len(pool), 3) if c else 0.0
    known = Counter({k: v for k, v in fam.items() if k not in ("UNKNOWN_ORIGIN", "none")})
    return {
        "records": len(pool),
        "max_family_share": share(known),
        "max_relay_share": share(relay),
        "unknown_origin_share": round(fam.get("UNKNOWN_ORIGIN", 0) / len(pool), 3),
    }


def quality_report(records, holdout_status):
    states = Counter(r["pipeline"]["state"] for r in records)
    reviewed = [r for r in records if r["evidence_status"] in ("VERIFIED", "REPORTED", "DISPUTED")]
    rights_cleared = [r for r in records if _granted(r["rights"], "storage") and _granted(r["rights"], "commercial_modelling")]
    eligible = [r for r in records if r["pipeline"]["state"] in ("ELIGIBLE", "CALIBRATION_ADMITTED")]
    rel = Counter(kind for _, _, kind in find_relationships(records))

    def coverage(key_fn, subset):
        return dict(sorted(Counter(key_fn(r) for r in subset).items()))

    band = lambda r: price_band(r["pipeline"]["amount_usd"])
    return {
        "pipeline_version": PIPELINE_VERSION,
        "dataset_status": reg.DATASET_STATUS,
        "records": len(records),
        "funnel": {
            "discovered_total": len(records),
            "directly_reviewed": len(reviewed),
            "rights_cleared": len(rights_cleared),
            "calibration_eligible": len(eligible),
            "calibration_admitted": states.get("CALIBRATION_ADMITTED", 0),
            "rejected": states.get("REJECTED", 0),
            "holdout_reserved_private": holdout_status.get("record_count") or 0,
        },
        "states": {s: states.get(s, 0) for s in STATES if s != "HOLDOUT_RESERVED"},
        "rejection_reasons": dict(sorted(Counter(x for r in records for x in r["pipeline"]["rejection_reasons"]).items())),
        "blockers": dict(sorted(Counter(x for r in records for x in r["pipeline"]["blockers"]).items())),
        "price_band_all_priced": coverage(band, [r for r in records if r["pipeline"]["amount_usd"] is not None]),
        "price_band_eligible": {b: sum(1 for r in eligible if band(r) == b) for b, _ in PRICE_BANDS},
        "price_band_target": TARGET_BY_BAND,
        "market_side_all": coverage(lambda r: MARKET_SIDE[r["market_side"]], records),
        "venue_all": coverage(lambda r: r["venue"], records),
        "extension_all": coverage(lambda r: "." + reg.normalise_domain(r["domain"]).split(".", 1)[1], records),
        "sale_decade_all": coverage(lambda r: (r["sale_date"][:3] + "0s") if r["sale_date"] else "unknown", records),
        "naming_class_all": coverage(lambda r: r["pipeline"]["naming_class"], records),
        "source_tier_all": coverage(lambda r: r["pipeline"]["source_reliability_tier"] or "none", records),
        "price_type_all": coverage(lambda r: r["pipeline"]["price_type"], records),
        "sale_date_basis_all": coverage(lambda r: r["pipeline"]["sale_date_basis"], records),
        "source_family_all": coverage(lambda r: r["pipeline"]["source_family"] or "none", records),
        "relay_publisher_all": coverage(lambda r: r["pipeline"]["relay_publisher"] or "none (direct)", records),
        "independence": independence_summary(records),
        "same_domain_relationships": dict(sorted(rel.items())),
        "unresolved_evidence": {
            "material_conflicts": sum(1 for r in records if r["evidence_status"] == "DISPUTED"),
            "duplicates_or_repeats_unresolved": sum(1 for r in records if "DUPLICATE_UNRESOLVED" in r["pipeline"]["blockers"]),
            "scope_unknown": sum(1 for r in records if "SCOPE_UNKNOWN" in r["pipeline"]["blockers"]),
            "rights_not_established": sum(1 for r in records if "RIGHTS_NOT_ESTABLISHED" in r["pipeline"]["blockers"]),
            "completion_not_evidenced": sum(1 for r in records if "COMPLETION_NOT_EVIDENCED" in r["pipeline"]["blockers"]),
            "sale_date_not_evidenced": sum(1 for r in records if "SALE_DATE_UNKNOWN" in r["pipeline"]["blockers"]),
        },
        "target_first_stage": TARGET_TOTAL,
    }


def _table(mapping, head=("Value", "Records")):
    lines = [f"| {head[0]} | {head[1]} |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in mapping.items()] or ["| (none) | 0 |"]
    return "\n".join(lines)


def render_markdown(q):
    f = q["funnel"]
    band_rows = ["| Price band | Eligible | Target (first 500) | All priced records |", "| --- | --- | --- | --- |"]
    for b, _ in PRICE_BANDS:
        band_rows.append(f"| {b} | {q['price_band_eligible'][b]} | {q['price_band_target'][b]} | {q['price_band_all_priced'].get(b, 0)} |")
    reasons = {f"{k} ({REJECTION_REASONS[k]})": v for k, v in q["rejection_reasons"].items()}
    blockers = {f"{k} ({BLOCKERS[k]})": v for k, v in q["blockers"].items()}
    return f"""# Pilot Quality Report: Comparable-Sales Pipeline

<!-- Generated by scripts/sales_pipeline.py --write-report. Do not edit by hand. -->

- **Pipeline:** `{q['pipeline_version']}` (candidate architecture, research only)
- **Dataset status:** `{q['dataset_status']}`
- **Input:** the {q['records']} transactions of the Sprint 1A Transaction Evidence
  Registry v1, run through the candidate pipeline rules. No new sales were
  imported.
- **Reading this report:** a sale counts as calibration-eligible only when it
  is reviewed, a completed single-domain cash sale with a verifiable price
  and date, and has storage and commercial-modelling rights on record.

## Funnel

| Stage | Records |
| --- | --- |
| Discovered (all records) | {f['discovered_total']} |
| Directly reviewed source | {f['directly_reviewed']} |
| Rights cleared (storage and modelling) | {f['rights_cleared']} |
| Calibration-eligible | {f['calibration_eligible']} |
| Calibration-admitted | {f['calibration_admitted']} |
| Rejected | {f['rejected']} |
| Holdout reserved (private; count from holdout status) | {f['holdout_reserved_private']} |

## Pipeline states

{_table(q['states'], ('State', 'Records'))}

## Rejection reasons (a record can have several)

{_table(reasons, ('Reason', 'Records'))}

## Blockers on non-rejected and rejected records

{_table(blockers, ('Blocker', 'Records'))}

## Price-band coverage

{chr(10).join(band_rows)}

## Market side

{_table(q['market_side_all'], ('Market side', 'Records'))}

## Venue

{_table(q['venue_all'], ('Venue', 'Records'))}

## Extension

{_table(q['extension_all'], ('Extension', 'Records'))}

## Sale decade

{_table(q['sale_decade_all'], ('Decade', 'Records'))}

## Naming class (human rules; engine labels are never used)

{_table(q['naming_class_all'], ('Naming class', 'Records'))}

## Source reliability tier (principal source)

{_table(q['source_tier_all'], ('Tier', 'Records'))}

## Price type (what the stated price is evidence of)

{_table(q['price_type_all'], ('Price type', 'Records'))}

## Sale-date basis (report dates and windows never count)

{_table(q['sale_date_basis_all'], ('Basis', 'Records'))}

## Source family (originating data owner) and relay publisher

{_table(q['source_family_all'], ('Source family', 'Records'))}

{_table(q['relay_publisher_all'], ('Relay publisher', 'Records'))}

Independence among reviewed, priced records: {q['independence']['records']} records;
largest known source family {q['independence']['max_family_share']}; largest relay
{q['independence']['max_relay_share']}; unknown origin {q['independence']['unknown_origin_share']}.
Venues named by one relay are not independent source families.

## Same-domain relationships

{_table(q['same_domain_relationships'], ('Relationship', 'Pairs'))}

## Unresolved evidence

{_table(q['unresolved_evidence'], ('Issue', 'Records'))}

## Reading

- {f['calibration_eligible']} of the first-stage target of {q['target_first_stage']} qualified
  transactions exist today. The registry was built to check the published
  comps, which are mostly landmark sales, so it cannot supply the
  ordinary-sales evidence the target needs.
- Rights are the binding constraint: no record has storage and modelling
  rights on record, so none can become eligible whatever its evidence.
- Registry v1 records neither completion evidence nor where its sale dates
  come from, so every priced record is `REPORTED_PRICE` and every date basis
  is `NOT_ESTABLISHED` until re-reviewed.
"""


def main():
    parser = argparse.ArgumentParser(description="Sprint 1B candidate comparable-sales pipeline")
    parser.add_argument("--report", action="store_true", help="print the pilot quality report as JSON")
    parser.add_argument("--write-report", action="store_true", help="regenerate the committed pilot report")
    parser.add_argument("--check", action="store_true", help="fail if the committed pilot report is stale")
    parser.add_argument("--validate", metavar="FILE", help="validate a pipeline JSON file ({'records': [...]})")
    args = parser.parse_args()

    if args.validate:
        records = reg.load(args.validate).get("records", [])
        errors = validate(records, [])
        for e in errors:
            print(f"FAIL: {e}")
        if errors:
            sys.exit(1)
        print(f"PASS: {len(records)} pipeline records valid")
        return

    records = pilot_records()
    errors = validate(records, [])
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    q = quality_report(records, reg.load(reg.HOLDOUT_STATUS_PATH))
    text = render_markdown(q)
    if args.write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(text, encoding="utf-8")
        print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    elif args.check:
        if not REPORT_PATH.exists() or REPORT_PATH.read_text(encoding="utf-8") != text:
            print(f"FAIL: {REPORT_PATH.relative_to(REPO_ROOT)} is stale (run --write-report)")
            sys.exit(1)
        print("PASS: pilot quality report is up to date")
    else:
        print(json.dumps(q, indent=1))


if __name__ == "__main__":
    main()
