#!/usr/bin/env python3
"""Validate the public integrity disclosures of the valuation tool (Sprint 0B).

Until the comparable sales carry verified provenance and the estimates are
validated against an independent holdout set, the public surfaces must:

  1. Describe the comparable sales as reported, never as documented or
     verified, and never inflate their number.
  2. Label the lexical confidence indicator as classification confidence and
     explain that it says nothing about price accuracy.
  3. Show an experimental-estimate disclosure where the price is shown.
  4. Publish a comparable-sales file whose content timestamp, content hash and
     source-verification status are consistent with its data. No record-level
     verification standard exists yet, so any status other than
     "not_verified" (or any last_verified date) is rejected, whatever a
     dataset-level date in the seed says.

Usage: python3 scripts/validate_valuation_disclosures.py
Exits 0 and prints PASS if valid, otherwise prints each violation prefixed
"FAIL:" and exits 1.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

UI_PATH = REPO_ROOT / "js" / "valuation-ui.js"
VALUATION_PAGE = REPO_ROOT / "valuation.html"
COMPS_PATH = REPO_ROOT / "data" / "valuation_comps.json"

PROVENANCE_DISCLOSURE = (
    "Individual source provenance has not yet been independently verified "
    "for every sales record"
)
ESTIMATE_DISCLOSURE = (
    "Experimental valuation estimate.</strong> Price accuracy has not yet been "
    "independently validated. Comparable-sales coverage and source verification "
    "are under review."
)
CONFIDENCE_EXPLANATION = (
    "This indicator describes confidence in the name's linguistic classification, "
    "not the accuracy of the estimated market price."
)

# Claims that present the unsourced comps as documented, verified, or larger
# than they are. Matched case-insensitively against public surfaces.
FORBIDDEN_CLAIMS = [
    "documented landmark sales",
    "documented public domain sales",
    "own documented sale",
    "documented prior sale of the exact domain",
    "verified comparable sales",
    "comparable-sales datasets are refreshed weekly",
    "public sales anchors",
    "public sales references",
    "public sales signals behind the system",
    "one outlier sale cannot inflate",
    "no single outlier can distort",
]


def public_surfaces():
    files = sorted(REPO_ROOT.glob("*.html"))
    files += sorted(REPO_ROOT.glob("*/*.html"))
    files += sorted(REPO_ROOT.glob("*/*/*.html"))
    files += [REPO_ROOT / "llms.txt", UI_PATH]
    return [f for f in files if f.exists()]


def content_hash(sales):
    canonical = json.dumps(sales, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_claims(errors):
    for path in public_surfaces():
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).lower()
        for phrase in FORBIDDEN_CLAIMS:
            if phrase in text:
                errors.append(f"{path.relative_to(REPO_ROOT)}: contains {phrase!r}")


def check_result_card(errors):
    ui = re.sub(r"\s+", " ", UI_PATH.read_text(encoding="utf-8"))
    if "Classification confidence:" not in ui:
        errors.append("valuation-ui.js: result card must label the indicator 'Classification confidence'")
    if re.search(r"·\s*Confidence:", ui):
        errors.append("valuation-ui.js: bare 'Confidence:' label still present")
    if CONFIDENCE_EXPLANATION not in ui:
        errors.append("valuation-ui.js: classification-confidence explanation missing")
    if ESTIMATE_DISCLOSURE not in ui:
        errors.append("valuation-ui.js: experimental-estimate disclosure missing")
    if PROVENANCE_DISCLOSURE not in ui:
        errors.append("valuation-ui.js: provenance disclosure missing from comparable sales")

    # The disclosure must sit with the prices, ahead of the value grid.
    template = ui[ui.find("function renderValuationResult"):]
    notice, grid = template.find("renderEstimateNotice("), template.find('class="value-grid"')
    if notice == -1 or grid == -1 or notice > grid:
        errors.append("valuation-ui.js: estimate disclosure must render immediately before the price grid")


def check_page(errors):
    page = re.sub(r"\s+", " ", VALUATION_PAGE.read_text(encoding="utf-8"))
    if PROVENANCE_DISCLOSURE not in page:
        errors.append("valuation.html: provenance disclosure missing")
    if "Price accuracy has not yet been independently validated" not in page:
        errors.append("valuation.html: price-accuracy limitation missing from Scope and limitations")


def check_comps(errors, comps=None):
    if comps is None:
        comps = json.loads(COMPS_PATH.read_text(encoding="utf-8"))

    for field in ("content_updated", "content_sha256", "generated_at", "source_verification", "methodology_version"):
        if field not in comps:
            errors.append(f"valuation_comps.json: missing {field!r}")
    if errors:
        return

    if comps["content_sha256"] != content_hash(comps["sales"]):
        errors.append("valuation_comps.json: content_sha256 does not match its sales")
    if comps["last_updated"] != comps["content_updated"]:
        errors.append("valuation_comps.json: last_updated must mirror content_updated, not the build time")

    # Sprint 0 invariant: verification is earned per record, and no
    # record-level verification standard has been approved yet.
    verification = comps["source_verification"] or {}
    if verification.get("status") != "not_verified":
        errors.append(
            "valuation_comps.json: source_verification.status must be 'not_verified' "
            "until a record-level verification standard exists"
        )
    if verification.get("last_verified") is not None:
        errors.append("valuation_comps.json: last_verified must be null until records are individually verified")
    if PROVENANCE_DISCLOSURE not in (verification.get("note") or ""):
        errors.append("valuation_comps.json: source_verification.note must carry the provenance disclosure")


def main():
    errors = []
    check_claims(errors)
    check_result_card(errors)
    check_page(errors)
    check_comps(errors)

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: valuation disclosures intact — reported-sales language, classification-confidence label, "
          "experimental-estimate notice, and content-based comps timestamp")


if __name__ == "__main__":
    main()
