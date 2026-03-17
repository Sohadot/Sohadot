#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

SEED_PATH = DATA_DIR / "valuation_comps_seed.json"
OUTPUT_PATH = DATA_DIR / "valuation_comps.json"

UTC = timezone.utc


def now_utc():
    return datetime.now(UTC)


def human_date(dt: datetime) -> str:
    return dt.strftime("%B %d, %Y %H:%M UTC")


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


def main():
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Missing file: {SEED_PATH}")

    with SEED_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    sales = [normalize_sale(item) for item in raw.get("sales", [])]
    sales = sort_sales(sales)

    now = now_utc()

    payload = {
        "version": "2.0",
        "last_updated": now.isoformat().replace("+00:00", "Z"),
        "last_updated_human": human_date(now),
        "count": len(sales),
        "sales": sales
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUTPUT_PATH} with {len(sales)} comparable sales.")


if __name__ == "__main__":
    main()
