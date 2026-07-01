#!/usr/bin/env python3
"""Generate data/conceptual-inventory.json — the Portfolio Coverage & Conceptual
Inventory Ledger.

This script answers, for the full public portfolio, four questions:
  1. How many domains are in the Sohadot portfolio?
  2. How many have protected conceptual definitions (Category Artifacts)?
  3. Which fields is each defined asset suitable for?
  4. Which domains are still pending Canonical Meaning Lock?

Sources (read-only):
  - portfolio.html            -> full public portfolio domain list (DOMAINS array)
  - data/asset-meanings.json  -> protected canonical meanings + possible_fields
  - data/category-clusters.json -> primary cluster membership + buyer logic

This script does not invent canonical meanings for undefined domains, does not
expand the 50 Category Artifacts, and does not change any canonical meaning.
Every domain not present in asset-meanings.json is recorded as pending Canonical
Meaning Lock with a null canonical_meaning and an empty possible_fields list.

Usage: python3 scripts/generate_conceptual_inventory.py
Writes data/conceptual-inventory.json and prints a one-line summary.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = REPO_ROOT / "portfolio.html"
ASSET_MEANINGS_PATH = REPO_ROOT / "data" / "asset-meanings.json"
CATEGORY_CLUSTERS_PATH = REPO_ROOT / "data" / "category-clusters.json"
OUTPUT_PATH = REPO_ROOT / "data" / "conceptual-inventory.json"

DOMAIN_ENTRY_RE = re.compile(r'\{domain:"([^"]+)"')


def extract_portfolio_domains():
    """Extract every domain string from portfolio.html's DOMAINS array, in order."""
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


def load_asset_meanings():
    raw = json.loads(ASSET_MEANINGS_PATH.read_text(encoding="utf-8"))
    by_lower = {}
    for asset in raw.get("assets", []):
        domain = asset.get("domain", "").strip()
        if domain:
            by_lower[domain.lower()] = asset
    return by_lower


def load_clusters():
    raw = json.loads(CATEGORY_CLUSTERS_PATH.read_text(encoding="utf-8"))
    clusters = raw.get("clusters", [])
    primary_cluster_of = {}
    buyer_logic_of = {}
    for cluster in clusters:
        name = cluster.get("name", "").strip()
        buyer_logic = cluster.get("buyer_logic", "").strip()
        for member in cluster.get("primary_members", []):
            key = member.strip().lower()
            primary_cluster_of[key] = name
            buyer_logic_of[key] = buyer_logic
    return clusters, primary_cluster_of, buyer_logic_of


def build_records(portfolio_domains, asset_meanings, primary_cluster_of, buyer_logic_of):
    records = []
    for domain in portfolio_domains:
        key = domain.lower()
        asset = asset_meanings.get(key)
        if asset:
            canonical_domain = asset.get("domain", domain)
            record = {
                "domain": canonical_domain,
                "status": "protected-category-artifact",
                "has_canonical_meaning": True,
                "canonical_meaning": asset.get("canonical_meaning"),
                "possible_fields": list(asset.get("possible_fields", [])),
                "primary_cluster": primary_cluster_of.get(key),
                "buyer_logic": buyer_logic_of.get(key),
                "strategic_brief_url": (
                    f"/strategic-brief.html?asset={canonical_domain}&type=single-asset-acquisition"
                ),
            }
        else:
            record = {
                "domain": domain,
                "status": "pending-canonical-meaning-lock",
                "has_canonical_meaning": False,
                "canonical_meaning": None,
                "possible_fields": [],
                "primary_cluster": None,
                "buyer_logic": None,
                "strategic_brief_url": (
                    f"/strategic-brief.html?asset={domain}&type=single-asset-acquisition"
                ),
            }
        records.append(record)
    return records


def main():
    portfolio_domains = extract_portfolio_domains()
    asset_meanings = load_asset_meanings()
    clusters, primary_cluster_of, buyer_logic_of = load_clusters()

    records = build_records(portfolio_domains, asset_meanings, primary_cluster_of, buyer_logic_of)

    total_domains = len(records)
    defined_assets_count = sum(1 for r in records if r["has_canonical_meaning"])
    pending_meaning_lock_count = total_domains - defined_assets_count

    payload = {
        "description": (
            "Portfolio Coverage & Conceptual Inventory Ledger — a portfolio-level "
            "coverage layer above the Category Artifact Meaning Layer "
            "(data/asset-meanings.json) and the Category Cluster & Buyer Logic Layer "
            "(data/category-clusters.json). It answers how many domains are in the "
            "Sohadot portfolio, how many carry a protected canonical meaning, which "
            "fields each defined asset is suitable for, and which domains remain "
            "pending Canonical Meaning Lock. It does not invent meanings for undefined "
            "domains and does not expand the 50 Category Artifacts. Rendered in "
            "/conceptual-inventory.html and checked by scripts/validate_conceptual_inventory.py."
        ),
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_domains": total_domains,
        "defined_assets_count": defined_assets_count,
        "pending_meaning_lock_count": pending_meaning_lock_count,
        "cluster_count": len(clusters),
        "records": records,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}: "
        f"total_domains={total_domains}, defined_assets_count={defined_assets_count}, "
        f"pending_meaning_lock_count={pending_meaning_lock_count}, "
        f"cluster_count={len(clusters)}"
    )


if __name__ == "__main__":
    main()
