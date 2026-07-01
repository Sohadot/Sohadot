#!/usr/bin/env python3
"""Validate data/asset-meanings.json against the Category Artifact Meaning Layer schema.

Usage: python3 scripts/validate_asset_meanings.py
Exits 0 and prints PASS if valid, otherwise prints each violation and exits 1.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "asset-meanings.json"

REQUIRED_FIELDS = [
    "domain",
    "canonical_segmentation",
    "acronym_expansion",
    "canonical_meaning",
    "arabic_meaning",
    "surface_misreadings_to_avoid",
    "conceptual_thesis",
    "category_claim",
    "possible_fields",
    "asset_type",
    "buyer_logic",
]

# acronym_expansion may legitimately be null for non-acronym domains.
FIELDS_ALLOWED_EMPTY = {"acronym_expansion"}

VALID_EXTENSIONS = (".com", ".ai", ".io", ".co", ".net", ".org")


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def main():
    if not DATA_PATH.exists():
        fail([f"Data file not found: {DATA_PATH}"])

    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"Invalid JSON in {DATA_PATH}: {exc}"])
        return

    assets = raw.get("assets")
    if not isinstance(assets, list) or not assets:
        fail([f"'assets' must be a non-empty list in {DATA_PATH}"])
        return

    errors = []
    seen_domains = {}

    for idx, asset in enumerate(assets):
        label = asset.get("domain", f"asset[{idx}]") if isinstance(asset, dict) else f"asset[{idx}]"

        if not isinstance(asset, dict):
            errors.append(f"{label}: entry is not an object")
            continue

        missing = [f for f in REQUIRED_FIELDS if f not in asset]
        if missing:
            errors.append(f"{label}: missing required field(s): {', '.join(missing)}")

        fields_with_own_message = {"possible_fields", "surface_misreadings_to_avoid"}
        for field in REQUIRED_FIELDS:
            if field in missing or field in FIELDS_ALLOWED_EMPTY or field in fields_with_own_message:
                continue
            value = asset.get(field)
            if value is None or (isinstance(value, (str, list)) and len(value) == 0):
                errors.append(f"{label}: field '{field}' must not be empty")

        possible_fields = asset.get("possible_fields")
        if "possible_fields" not in missing and isinstance(possible_fields, list) and len(possible_fields) == 0:
            errors.append(f"{label}: possible_fields must not be empty")

        misreadings = asset.get("surface_misreadings_to_avoid")
        if "surface_misreadings_to_avoid" not in missing and isinstance(misreadings, list) and len(misreadings) == 0:
            errors.append(f"{label}: surface_misreadings_to_avoid must not be empty")

        domain = asset.get("domain")
        if isinstance(domain, str) and domain.strip():
            if not domain.lower().endswith(VALID_EXTENSIONS):
                errors.append(
                    f"{label}: domain '{domain}' does not end with a valid extension "
                    f"({', '.join(VALID_EXTENSIONS)})"
                )
            key = domain.strip().lower()
            if key in seen_domains:
                errors.append(f"Duplicate domain found: '{domain}'")
            else:
                seen_domains[key] = idx
        elif "domain" in asset:
            errors.append(f"{label}: domain must be a non-empty string")

    if errors:
        fail(errors)
        return

    print(f"PASS: {len(assets)} assets validated in {DATA_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
