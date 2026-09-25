#!/usr/bin/env python3
"""Validate data/conceptual-inventory.json against its source files.

Cross-checks the generated Portfolio Coverage & Conceptual Inventory Ledger
against the three sources it is derived from:
  - portfolio.html            -> full public portfolio domain list
  - data/asset-meanings.json  -> protected canonical meanings
  - data/category-clusters.json -> cluster membership

Usage: python3 scripts/validate_conceptual_inventory.py
Exits 0 and prints PASS with total/defined/pending counts if valid, otherwise
prints each violation prefixed "FAIL:" and exits 1.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = REPO_ROOT / "portfolio.html"
ASSET_MEANINGS_PATH = REPO_ROOT / "data" / "asset-meanings.json"
CATEGORY_CLUSTERS_PATH = REPO_ROOT / "data" / "category-clusters.json"
INVENTORY_PATH = REPO_ROOT / "data" / "conceptual-inventory.json"
BUNDLE_ONLY_PATH = REPO_ROOT / "data" / "bundle-only-assets.json"

DOMAIN_ENTRY_RE = re.compile(r'\{domain:"([^"]+)"')

REQUIRED_RECORD_FIELDS = [
    "domain",
    "status",
    "has_canonical_meaning",
    "canonical_meaning",
    "possible_fields",
    "primary_cluster",
    "buyer_logic",
    "strategic_brief_url",
]


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def extract_portfolio_domains():
    html = PORTFOLIO_PATH.read_text(encoding="utf-8")
    domains = DOMAIN_ENTRY_RE.findall(html)
    seen = set()
    ordered = []
    for domain in domains:
        key = domain.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(domain.strip())
    return ordered


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    errors = []

    if not INVENTORY_PATH.exists():
        fail([f"{INVENTORY_PATH.relative_to(REPO_ROOT)} not found — run scripts/generate_conceptual_inventory.py"])
        return

    portfolio_domains = extract_portfolio_domains()
    portfolio_domain_set = {d.lower() for d in portfolio_domains}

    asset_meanings_raw = load_json(ASSET_MEANINGS_PATH)
    asset_domains = {
        a.get("domain", "").strip().lower()
        for a in asset_meanings_raw.get("assets", [])
        if isinstance(a, dict) and a.get("domain")
    }

    clusters_raw = load_json(CATEGORY_CLUSTERS_PATH)
    cluster_names = {
        c.get("name", "").strip()
        for c in clusters_raw.get("clusters", [])
        if isinstance(c, dict) and c.get("name")
    }

    inventory = load_json(INVENTORY_PATH)

    bundle_only = {}
    if BUNDLE_ONLY_PATH.exists():
        for bundle in load_json(BUNDLE_ONLY_PATH).get("bundles", []):
            for member in bundle.get("domains", []):
                bundle_only[member.strip().lower()] = bundle

    for field in (
        "total_domains",
        "defined_assets_count",
        "pending_meaning_lock_count",
        "cluster_count",
        "generated_at",
        "records",
    ):
        if field not in inventory:
            errors.append(f"conceptual-inventory.json: missing required top-level field '{field}'")

    if errors:
        fail(errors)
        return

    records = inventory["records"]

    if inventory["total_domains"] != len(portfolio_domains):
        errors.append(
            f"conceptual-inventory.json: total_domains={inventory['total_domains']} does not match "
            f"extracted portfolio.html domain count={len(portfolio_domains)}"
        )

    if inventory["defined_assets_count"] != len(asset_domains):
        errors.append(
            f"conceptual-inventory.json: defined_assets_count={inventory['defined_assets_count']} does not "
            f"match data/asset-meanings.json asset count={len(asset_domains)}"
        )

    expected_pending = inventory["total_domains"] - inventory["defined_assets_count"]
    if inventory["pending_meaning_lock_count"] != expected_pending:
        errors.append(
            f"conceptual-inventory.json: pending_meaning_lock_count="
            f"{inventory['pending_meaning_lock_count']} != total_domains - defined_assets_count "
            f"({expected_pending})"
        )

    seen_domains = {}
    inventory_domain_set = set()
    for i, record in enumerate(records):
        missing_fields = [f for f in REQUIRED_RECORD_FIELDS if f not in record]
        if missing_fields:
            errors.append(f"conceptual-inventory.json: record #{i} missing fields {missing_fields}")
            continue

        domain = record["domain"]
        key = domain.strip().lower()
        inventory_domain_set.add(key)

        if key in seen_domains:
            errors.append(f"conceptual-inventory.json: duplicate domain '{domain}' (records #{seen_domains[key]} and #{i})")
        else:
            seen_domains[key] = i

        is_defined = key in asset_domains

        if is_defined:
            if record["status"] != "protected-category-artifact":
                errors.append(f"conceptual-inventory.json: '{domain}' is a defined asset but status is '{record['status']}'")
            if record["has_canonical_meaning"] is not True:
                errors.append(f"conceptual-inventory.json: '{domain}' is a defined asset but has_canonical_meaning is not true")
            if not record["canonical_meaning"]:
                errors.append(f"conceptual-inventory.json: '{domain}' is a defined asset but canonical_meaning is empty/null")
        else:
            if record["status"] != "pending-canonical-meaning-lock":
                errors.append(f"conceptual-inventory.json: '{domain}' is undefined but status is '{record['status']}'")
            if record["has_canonical_meaning"] is not False:
                errors.append(f"conceptual-inventory.json: '{domain}' is undefined but has_canonical_meaning is not false")
            if record["canonical_meaning"] is not None:
                errors.append(f"conceptual-inventory.json: undefined asset '{domain}' has a non-null canonical_meaning")
            if record["possible_fields"]:
                errors.append(f"conceptual-inventory.json: undefined asset '{domain}' has non-empty possible_fields")
            if record["primary_cluster"] is not None:
                errors.append(f"conceptual-inventory.json: undefined asset '{domain}' has a non-null primary_cluster")
            if record["buyer_logic"] is not None:
                errors.append(f"conceptual-inventory.json: undefined asset '{domain}' has a non-null buyer_logic")

        if record["primary_cluster"] is not None and record["primary_cluster"] not in cluster_names:
            errors.append(f"conceptual-inventory.json: '{domain}' primary_cluster '{record['primary_cluster']}' not found in data/category-clusters.json")

        url = record["strategic_brief_url"]
        bundle = bundle_only.get(key)
        if bundle:
            for field in ("sale_mode", "bundle_id", "bundle_url"):
                if record.get(field) != bundle[field]:
                    errors.append(
                        f"conceptual-inventory.json: bundle-only '{domain}' has {field}="
                        f"{record.get(field)!r}, expected {bundle[field]!r}"
                    )
            if url is not None:
                errors.append(
                    f"conceptual-inventory.json: bundle-only '{domain}' must not advertise an "
                    f"individual strategic_brief_url (found '{url}')"
                )
            bundle_page = REPO_ROOT / bundle["bundle_url"].strip("/") / "index.html"
            if not bundle_page.exists():
                errors.append(f"conceptual-inventory.json: '{domain}' bundle_url '{bundle['bundle_url']}' does not resolve to a page")
            if record.get("bundle_context") is not None and is_defined:
                errors.append(f"conceptual-inventory.json: protected asset '{domain}' must not carry a bundle_context")
        else:
            for field in ("sale_mode", "bundle_id", "bundle_url", "bundle_context"):
                if field in record:
                    errors.append(f"conceptual-inventory.json: '{domain}' carries '{field}' but is not listed in data/bundle-only-assets.json")
            path = urlsplit(url or "").path
            if not path.endswith("strategic-brief.html"):
                errors.append(f"conceptual-inventory.json: '{domain}' strategic_brief_url '{url}' does not point to strategic-brief.html")

    missing_defined = asset_domains - inventory_domain_set
    if missing_defined:
        errors.append(
            f"conceptual-inventory.json: {len(missing_defined)} defined asset(s) missing from inventory: "
            f"{sorted(missing_defined)}"
        )

    missing_portfolio = portfolio_domain_set - inventory_domain_set
    if missing_portfolio:
        errors.append(
            f"conceptual-inventory.json: {len(missing_portfolio)} portfolio domain(s) missing from inventory: "
            f"{sorted(missing_portfolio)[:10]}"
        )

    if errors:
        fail(errors)
        return

    print(
        f"PASS: conceptual inventory ledger valid — total={inventory['total_domains']}, "
        f"defined={inventory['defined_assets_count']}, pending={inventory['pending_meaning_lock_count']}"
    )


if __name__ == "__main__":
    main()
