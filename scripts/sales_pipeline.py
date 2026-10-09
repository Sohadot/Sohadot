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

PRICE_TYPES = {"COMPLETED_SALE", "ASKING_PRICE", "AUCTION_BID", "AUCTION_RESULT_UNCONFIRMED", "UNDISCLOSED", "UNKNOWN"}
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
    "NOT_A_COMPLETED_SALE": "asking price, bid or unconfirmed auction result",
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
    "PRICE_TYPE_UNKNOWN": "not yet shown to be a completed sale",
    "SCOPE_UNKNOWN": "not yet shown to be a single-domain sale",
    "SALE_DATE_UNKNOWN": "sale date unknown",
    "FX_BASIS_MISSING": "non-USD amount without a recorded conversion basis",
    "RIGHTS_NOT_ESTABLISHED": "storage or commercial-modelling right not established",
    "DUPLICATE_UNRESOLVED": "possible duplicate or repeat sale needs review",
    "BUNDLE_SUSPECTED": "shares a source passage and amount with another domain",
}


# --- Pilot mapping from the Sprint 1A registry --------------------------------

def price_type_from_registry(t):
    if t["price_disclosure_status"] == "UNDISCLOSED":
        return "UNDISCLOSED"
    if t["evidence_status"] in ("VERIFIED", "REPORTED", "DISPUTED") and t["sale_price"] is not None:
        return "COMPLETED_SALE"
    return "UNKNOWN"


def pipeline_from_registry(t):
    """Wrap a registry v1 transaction in an (unassessed) pipeline block."""
    amount = t["sale_price"]
    usd = amount if (amount is not None and t["currency"] == "USD") else None
    record = dict(t)
    record["pipeline"] = {
        "state": None,
        "price_type": price_type_from_registry(t),
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


def assess(record, unresolved_dupes=frozenset(), bundle_suspects=frozenset()):
    """Return (state, blockers, rejection_reasons) computed from the record."""
    t, p = record, record["pipeline"]
    rejections, blockers = [], []

    if p["price_type"] in ("ASKING_PRICE", "AUCTION_BID", "AUCTION_RESULT_UNCONFIRMED"):
        rejections.append("NOT_A_COMPLETED_SALE")
    elif p["price_type"] == "UNDISCLOSED" or t["price_disclosure_status"] == "UNDISCLOSED":
        rejections.append("PRICE_NOT_DISCLOSED")
    elif p["price_type"] == "UNKNOWN":
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
    if t["sale_date_precision"] == "UNKNOWN":
        blockers.append("SALE_DATE_UNKNOWN")
    if p["original_amount"] is not None and p["original_currency"] != "USD" and not p["fx_basis"]:
        blockers.append("FX_BASIS_MISSING")
    if not (_granted(t["rights"], "storage") and _granted(t["rights"], "commercial_modelling")):
        if "RIGHTS_NOT_PERMITTED" not in rejections:
            blockers.append("RIGHTS_NOT_ESTABLISHED")
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
        "same_domain_relationships": dict(sorted(rel.items())),
        "unresolved_evidence": {
            "material_conflicts": sum(1 for r in records if r["evidence_status"] == "DISPUTED"),
            "duplicates_or_repeats_unresolved": sum(1 for r in records if "DUPLICATE_UNRESOLVED" in r["pipeline"]["blockers"]),
            "scope_unknown": sum(1 for r in records if "SCOPE_UNKNOWN" in r["pipeline"]["blockers"]),
            "rights_not_established": sum(1 for r in records if "RIGHTS_NOT_ESTABLISHED" in r["pipeline"]["blockers"]),
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
