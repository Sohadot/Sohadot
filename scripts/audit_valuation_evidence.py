#!/usr/bin/env python3
"""Sprint 0 — Evidence & Accuracy Audit: record-level audit of the
comparable-sales evidence behind the Sohadot valuation engine.

The valuation engine (js/valuation-engine.js) calibrates estimates against
data/valuation_comps.json, which is generated from
data/valuation_comps_seed.json by scripts/generate_valuation_data.py. This
script audits that evidence layer. It separates two kinds of findings:

  FAIL  — structural defects that make a record unusable or the generated
          file untrustworthy (missing fields, malformed domain, extension
          mismatch, duplicate, unknown classification, seed/generated drift).
          Always exit 1.
  WARN  — evidence-quality gaps: no provenance (source, venue, sale date,
          price status), keyword tags the engine can never match, semantic
          tags absent from the name, classifications the engine itself would
          never assign to that name, and stale sales. Exit 0 by default;
          exit 1 under --strict, which is the intended gate once Sprint 1
          has attached provenance to every record.

Usage:
  python3 scripts/audit_valuation_evidence.py            # report, gate on FAIL
  python3 scripts/audit_valuation_evidence.py --strict   # also gate on WARN
  python3 scripts/audit_valuation_evidence.py --json out.json

The classification cross-check needs the engine's own classifier and is
performed by scripts/valuation_backtest.mjs; this script only checks what
can be verified from the data files themselves.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

SEED_PATH = DATA_DIR / "valuation_comps_seed.json"
GENERATED_PATH = DATA_DIR / "valuation_comps.json"
CONFIG_PATH = DATA_DIR / "valuation_config.json"
KEYWORDS_PATH = DATA_DIR / "valuation_keywords.json"

REQUIRED_FIELDS = ("domain", "price", "year", "tld", "classification")

# Provenance a sale record needs before it can be cited as evidence. None of
# these exist in the current schema; Sprint 1 introduces them.
PROVENANCE_FIELDS = (
    "source_name",   # publication or venue that reported the sale
    "source_url",    # link to the report
    "sale_date",     # ISO date (or year-month) of the sale, not of the report
    "price_status",  # confirmed | reported | estimated | undisclosed
    "venue",         # auction, marketplace, broker, private, corporate
)

PRICE_STATUSES = {"confirmed", "reported", "estimated", "undisclosed"}

EARLIEST_YEAR = 1985
STALE_AFTER_YEARS = 10

DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def quantile(sorted_values, q):
    if not sorted_values:
        return None
    idx = (len(sorted_values) - 1) * q
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (idx - lo)


def audit(strict_year=None):
    seed = load_json(SEED_PATH)
    generated = load_json(GENERATED_PATH)
    config = load_json(CONFIG_PATH)
    commercial_keywords = set(load_json(KEYWORDS_PATH)["commercial_keywords"])
    known_classes = set(config["base_scores"])

    current_year = strict_year or datetime.now(timezone.utc).year
    fails, warns = [], []
    sales = seed.get("sales", [])
    seen = Counter()

    provenance_missing = Counter()
    dead_tags, semantic_tags = [], []

    for i, sale in enumerate(sales):
        label = sale.get("domain") or f"record #{i}"

        missing = [f for f in REQUIRED_FIELDS if sale.get(f) in (None, "")]
        if missing:
            fails.append(f"{label}: missing required field(s) {', '.join(missing)}")
            continue

        domain = str(sale["domain"]).strip().lower()
        seen[domain] += 1

        if not DOMAIN_RE.match(domain):
            fails.append(f"{label}: malformed domain")
            continue

        tld = "." + domain.split(".", 1)[1]
        if sale["tld"] != tld:
            fails.append(f"{label}: tld field {sale['tld']!r} does not match domain extension {tld!r}")

        if not isinstance(sale["price"], int) or sale["price"] <= 0:
            fails.append(f"{label}: price must be a positive integer")

        year = sale["year"]
        if not isinstance(year, int) or not (EARLIEST_YEAR <= year <= current_year):
            fails.append(f"{label}: year {year!r} outside {EARLIEST_YEAR}-{current_year}")
        elif current_year - year > STALE_AFTER_YEARS:
            warns.append(
                f"{label}: sale is {current_year - year} years old ({year}); "
                f"no time adjustment is applied by the engine"
            )

        if sale["classification"] not in known_classes:
            fails.append(f"{label}: unknown classification {sale['classification']!r}")

        absent = [f for f in PROVENANCE_FIELDS if not sale.get(f)]
        for f in absent:
            provenance_missing[f] += 1
        if absent:
            warns.append(f"{label}: no provenance ({', '.join(absent)})")
        status = sale.get("price_status")
        if status and status not in PRICE_STATUSES:
            fails.append(f"{label}: price_status {status!r} not in {sorted(PRICE_STATUSES)}")

        sld = domain.split(".", 1)[0]
        for kw in sale.get("keywords", []):
            if kw not in commercial_keywords:
                dead_tags.append((domain, kw))
                warns.append(
                    f"{label}: keyword tag {kw!r} is not in valuation_keywords.json, "
                    f"so it can never match a subject domain"
                )
            elif kw not in sld:
                semantic_tags.append((domain, kw))
                warns.append(
                    f"{label}: keyword tag {kw!r} does not occur in the name; it links this "
                    f"sale to every subject containing {kw!r}"
                )

    for domain, count in seen.items():
        if count > 1:
            fails.append(f"{domain}: appears {count} times in the seed")

    # The generated file must be a faithful projection of the seed.
    gen_index = {s["domain"]: s for s in generated.get("sales", [])}
    seed_index = {str(s.get("domain", "")).strip().lower(): s for s in sales}
    if set(gen_index) != set(seed_index):
        only_gen = sorted(set(gen_index) - set(seed_index))
        only_seed = sorted(set(seed_index) - set(gen_index))
        fails.append(
            f"valuation_comps.json out of sync with seed "
            f"(only in generated: {only_gen or '-'}; only in seed: {only_seed or '-'})"
        )
    for domain, s in seed_index.items():
        g = gen_index.get(domain)
        if g and (g.get("price") != s.get("price") or g.get("year") != s.get("year")):
            fails.append(f"{domain}: generated price/year differ from seed")
    if generated.get("count") != len(generated.get("sales", [])):
        fails.append("valuation_comps.json: count does not match number of sales")

    prices = sorted(s["price"] for s in sales if isinstance(s.get("price"), int))
    years = [s["year"] for s in sales if isinstance(s.get("year"), int)]
    stats = {
        "records": len(sales),
        "by_classification": dict(Counter(s.get("classification") for s in sales).most_common()),
        "by_tld": dict(Counter(s.get("tld") for s in sales).most_common()),
        "by_decade": dict(sorted(Counter(f"{y // 10 * 10}s" for y in years).items())),
        "price_min": prices[0] if prices else None,
        "price_median": quantile(prices, 0.5),
        "price_max": prices[-1] if prices else None,
        "share_at_or_above_1m": round(sum(p >= 1_000_000 for p in prices) / len(prices), 3) if prices else None,
        "share_below_10k": round(sum(p < 10_000 for p in prices) / len(prices), 3) if prices else None,
        "records_with_full_provenance": sum(
            all(s.get(f) for f in PROVENANCE_FIELDS) for s in sales
        ),
        "provenance_field_missing": dict(provenance_missing),
        "dead_keyword_tags": len(dead_tags),
        "semantic_keyword_tags": len(semantic_tags),
        "stale_records": sum(
            1 for y in years if current_year - y > STALE_AFTER_YEARS
        ),
        "generated_last_updated": generated.get("last_updated"),
    }
    return fails, warns, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--strict", action="store_true", help="treat evidence warnings as failures")
    parser.add_argument("--json", metavar="PATH", help="also write the findings as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only the summary and failures")
    parser.add_argument("--as-of-year", type=int, help="fix the reference year (reproducible reports)")
    args = parser.parse_args()

    fails, warns, stats = audit(args.as_of_year)

    for line in fails:
        print(f"FAIL: {line}")
    if not args.quiet:
        for line in warns:
            print(f"WARN: {line}")

    print()
    print("Summary")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"  fails: {len(fails)}  warnings: {len(warns)}")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"fails": fails, "warnings": warns, "stats": stats}, indent=2) + "\n",
            encoding="utf-8",
        )

    if fails or (args.strict and warns):
        sys.exit(1)
    print("PASS (structure)" + ("" if not warns else " — evidence warnings outstanding; see --strict"))


if __name__ == "__main__":
    main()
