#!/usr/bin/env python3
"""Generate data/valuation_comps.json from data/valuation_comps_seed.json.

The output is a deterministic projection of the seed. It is rewritten only
when its substantive content changes, so an unchanged seed never receives a
fresh timestamp and the weekly workflow produces no commit.

Timestamp fields are kept separate on purpose:

  content_updated      Last time the normalized sales content changed. Carried
                       forward unchanged while the content hash is unchanged.
  generated_at         Last time this file was rewritten (content or metadata
                       change). Not a data-freshness claim.
  source_verification  Status of independent source verification. Always
                       "not_verified" with last_verified null in the Sprint 0
                       schema: verification must be earned record by record,
                       and no record-level verification standard exists yet.
                       Neither the clock nor a dataset-level date can set it.
  methodology_version  Valuation framework version the data is published for.

`last_updated` / `last_updated_human` are kept for compatibility and mirror
content_updated.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

SEED_PATH = DATA_DIR / "valuation_comps_seed.json"
OUTPUT_PATH = DATA_DIR / "valuation_comps.json"

UTC = timezone.utc

METHODOLOGY_VERSION = "2.5"

UNVERIFIED_NOTE = (
    "Reported sales. Individual source provenance has not yet been "
    "independently verified for every sales record."
)


def now_utc():
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def human_date(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%B %d, %Y %H:%M UTC")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_sale(item):
    domain = item.get("domain", "").strip().lower()
    price = int(item.get("price", 0))
    year = int(item.get("year", 0))
    tld = item.get("tld", "").strip().lower()
    classification = item.get("classification", "brandable")
    keywords = item.get("keywords", [])
    notes = item.get("notes", "").strip()

    sld = domain.split(".")[0] if "." in domain else domain
    length = len(sld)

    return {
        "domain": domain,
        "price": price,
        "price_display": "${:,}".format(price),
        "year": year,
        "tld": tld,
        "classification": classification,
        "keywords": keywords,
        "notes": notes,
        "sld": sld,
        "length": length
    }


def sort_sales(sales):
    return sorted(
        sales,
        key=lambda x: (x["price"], x["year"], -x["length"]),
        reverse=True
    )


def content_hash(sales):
    canonical = json.dumps(sales, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def source_verification():
    # Deliberately independent of the seed. A dataset-level date (for example
    # a `last_source_verification` key) or the presence of source fields on
    # some records does not prove that any transaction was independently
    # verified. Verified or partially verified states need a per-record
    # verification standard, which is Sprint 1 work.
    return {
        "status": "not_verified",
        "last_verified": None,
        "note": UNVERIFIED_NOTE,
    }


def build_payload(raw, previous, now, bootstrap_content_updated=None):
    """Return the payload to publish.

    `previous` is the currently published payload (or None). When nothing
    substantive changed, `previous` is returned as-is so the file stays
    byte-identical. `bootstrap_content_updated` (ISO timestamp + basis) is only
    honoured for a legacy file that predates content tracking.
    """
    sales = sort_sales([normalize_sale(item) for item in raw.get("sales", [])])
    digest = content_hash(sales)
    previous = previous or {}

    if previous.get("content_sha256") == digest:
        content_updated = previous.get("content_updated")
        basis = previous.get("content_updated_basis")
    elif "content_sha256" not in previous and previous.get("sales") == sales:
        # Legacy file: the content is unchanged, but its last_updated was a
        # build time, not a content date, so it is never reused.
        if bootstrap_content_updated:
            content_updated, basis = bootstrap_content_updated
        else:
            content_updated, basis = None, "not recorded (predates content tracking)"
    else:
        content_updated = iso(now)
        basis = "sales content changed"

    payload = {
        "version": METHODOLOGY_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "last_updated": content_updated,
        "last_updated_human": human_date(parse_iso(content_updated)) if content_updated else "Not recorded",
        "content_updated": content_updated,
        "content_updated_basis": basis,
        "content_sha256": digest,
        "generated_at": None,
        "source_verification": source_verification(),
        "count": len(sales),
        "sales": sales
    }

    comparable_previous = dict(previous, generated_at=None)
    if comparable_previous == payload:
        return previous

    payload["generated_at"] = iso(now)
    return payload


def serialize(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate data/valuation_comps.json")
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--now", help="ISO timestamp to use instead of the clock (tests)")
    parser.add_argument(
        "--bootstrap-content-updated",
        nargs=2,
        metavar=("ISO_TIMESTAMP", "BASIS"),
        help="one-time content date for a legacy file that predates content tracking",
    )
    args = parser.parse_args()

    if not args.seed.exists():
        raise FileNotFoundError(f"Missing file: {args.seed}")

    with args.seed.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    previous_text = args.output.read_text(encoding="utf-8") if args.output.exists() else None
    previous = json.loads(previous_text) if previous_text else None

    now = parse_iso(args.now) if args.now else now_utc()
    bootstrap = tuple(args.bootstrap_content_updated) if args.bootstrap_content_updated else None
    payload = build_payload(raw, previous, now, bootstrap)

    text = serialize(payload)
    if text == previous_text:
        print(f"{args.output} unchanged ({payload['count']} comparable sales); not rewritten.")
        return

    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output} with {payload['count']} comparable sales.")


if __name__ == "__main__":
    main()
