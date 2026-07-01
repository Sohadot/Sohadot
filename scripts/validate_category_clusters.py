#!/usr/bin/env python3
"""Validate data/category-clusters.json against the Category Cluster & Buyer Logic Layer schema.

This layer sits above the Category Artifact Meaning Layer (data/asset-meanings.json).
It groups existing, already-validated assets into strategic clusters — it must never
introduce a domain that doesn't already exist in the asset-meanings dataset, and every
asset must land in exactly one primary cluster.

Usage: python3 scripts/validate_category_clusters.py
Exits 0 and prints PASS if valid, otherwise prints each violation and exits 1.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_PATH = REPO_ROOT / "data" / "asset-meanings.json"
CLUSTERS_PATH = REPO_ROOT / "data" / "category-clusters.json"

REQUIRED_CLUSTER_FIELDS = [
    "id",
    "name",
    "short_claim",
    "strategic_thesis",
    "buyer_logic",
    "acquisition_rationale",
    "primary_buyer_types",
    "primary_members",
    "secondary_members",
    "lead_asset",
]

NON_EMPTY_STRING_FIELDS = [
    "id",
    "name",
    "short_claim",
    "strategic_thesis",
    "buyer_logic",
    "acquisition_rationale",
    "lead_asset",
]

NON_EMPTY_LIST_FIELDS = [
    "primary_buyer_types",
    "primary_members",
]


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def main():
    if not ASSETS_PATH.exists():
        fail([f"Asset data file not found: {ASSETS_PATH}"])
        return
    if not CLUSTERS_PATH.exists():
        fail([f"Cluster data file not found: {CLUSTERS_PATH}"])
        return

    try:
        assets_raw = json.loads(ASSETS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"Invalid JSON in {ASSETS_PATH}: {exc}"])
        return

    try:
        clusters_raw = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"Invalid JSON in {CLUSTERS_PATH}: {exc}"])
        return

    all_domains = {
        a.get("domain") for a in assets_raw.get("assets", []) if isinstance(a, dict) and a.get("domain")
    }
    if not all_domains:
        fail([f"No assets found in {ASSETS_PATH}"])
        return

    clusters = clusters_raw.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        fail([f"'clusters' must be a non-empty list in {CLUSTERS_PATH}"])
        return

    errors = []
    seen_cluster_ids = {}
    primary_owner = {}  # domain -> cluster id/name that already claims it primarily

    for idx, cluster in enumerate(clusters):
        label = cluster.get("name", cluster.get("id", f"cluster[{idx}]")) if isinstance(cluster, dict) else f"cluster[{idx}]"

        if not isinstance(cluster, dict):
            errors.append(f"{label}: cluster entry is not an object")
            continue

        missing = [f for f in REQUIRED_CLUSTER_FIELDS if f not in cluster]
        if missing:
            errors.append(f"{label}: missing required field(s): {', '.join(missing)}")

        for field in NON_EMPTY_STRING_FIELDS:
            if field in missing:
                continue
            value = cluster.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: field '{field}' must be a non-empty string")

        for field in NON_EMPTY_LIST_FIELDS:
            if field in missing:
                continue
            value = cluster.get(field)
            if not isinstance(value, list) or len(value) == 0:
                errors.append(f"{label}: field '{field}' must be a non-empty list")

        cluster_id = cluster.get("id")
        if isinstance(cluster_id, str) and cluster_id.strip():
            if cluster_id in seen_cluster_ids:
                errors.append(f"Duplicate cluster id found: '{cluster_id}'")
            else:
                seen_cluster_ids[cluster_id] = idx

        primary_members = cluster.get("primary_members") if isinstance(cluster.get("primary_members"), list) else []
        secondary_members = cluster.get("secondary_members") if isinstance(cluster.get("secondary_members"), list) else []

        for domain in primary_members:
            if domain not in all_domains:
                errors.append(
                    f"{label}: primary_member '{domain}' does not exist in {ASSETS_PATH.name}"
                )
            if domain in primary_owner:
                errors.append(
                    f"{label}: domain '{domain}' already appears as a primary member of "
                    f"'{primary_owner[domain]}' — a domain may have only one primary cluster"
                )
            else:
                primary_owner[domain] = label

        for domain in secondary_members:
            if domain not in all_domains:
                errors.append(
                    f"{label}: secondary_member '{domain}' does not exist in {ASSETS_PATH.name}"
                )

        lead_asset = cluster.get("lead_asset")
        if isinstance(lead_asset, str) and lead_asset.strip():
            if lead_asset not in primary_members:
                errors.append(
                    f"{label}: lead_asset '{lead_asset}' is not inside this cluster's primary_members"
                )

    uncovered = all_domains - set(primary_owner.keys())
    if uncovered:
        errors.append(
            f"{len(uncovered)} asset(s) have no primary cluster: {', '.join(sorted(uncovered))}"
        )

    if errors:
        fail(errors)
        return

    print(
        f"PASS: {len(clusters)} clusters validated, covering {len(primary_owner)} of "
        f"{len(all_domains)} assets in {ASSETS_PATH.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
