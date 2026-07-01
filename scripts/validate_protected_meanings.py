#!/usr/bin/env python3
"""Protected canonical-meaning assertions for the Category Artifact Meaning Layer.

Some assets in data/asset-meanings.json carry a user-approved canonical meaning
that previously drifted toward a plausible-but-wrong surface reading (e.g.
AIDAtanaly read as "AI Data Analysis" instead of "AIDA Transition Analytics").
This validator fails the build if a forbidden phrase reappears for a protected
asset, or if a required canonical phrase goes missing, in either the canonical
dataset or the rendered HTML page.

Assertion types:
- "full"     — the phrase must NOT appear anywhere in the asset's record (any
               field, including surface_misreadings_to_avoid) or anywhere
               inside that asset's <article> block / JSON-LD entry in
               category-artifacts.html.
- "primary"  — the phrase must NOT appear in the asset's primary meaning
               fields (everything except surface_misreadings_to_avoid) or in
               the non-misreadings portion of its HTML <article> block /
               JSON-LD entry. It MAY be named inside
               surface_misreadings_to_avoid / the HTML
               <details class="misreadings"> block, since that is precisely
               where a rejected secondary reading belongs.
- "required" — a positive, must-preserve assertion. Each entry is a group of
               interchangeable phrasings (OR within a group); at least one
               phrase from every group must be present in the asset's primary
               meaning fields / primary HTML text. Used for canonical readings
               that must not be diluted or renamed away (e.g. RAGFull must
               still say "Retrieval-Augmented Generation" somewhere).

Usage: python3 scripts/validate_protected_meanings.py
Exits 0 and prints PASS if valid, otherwise prints each violation and exits 1.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "asset-meanings.json"
HTML_PATH = REPO_ROOT / "category-artifacts.html"

# domain -> {"full": [...], "primary": [...], "required": [[opt1, opt2], [opt1], ...]}
PROTECTED_ASSETS = {
    # Sprint 1A — canonical meaning drift repair
    "AIDAtanaly.com": {"full": ["AI Data Analysis", "Not a play on AIDA"]},
    "Reefier.com": {"full": ["cold-chain", "reefer echo"]},
    "DNCTA.com": {"full": ["buyer-defined", "acronym shell"]},
    "PayOTIS.com": {"full": ["One-Time Instant Settlement"]},
    "ToAVR.com": {"primary": ["Audio/Video Receiver"]},
    "Mesomere.com": {"full": ["coined", "no fixed textbook meaning"]},
    "Allenarly.com": {"full": ["Allen key"]},
    "Aliaise.com": {"primary": ["alias"]},
    # Sprint 2 — top-50 expansion, new high-risk names
    "YetFut.com": {"primary": ["yet future"]},
    "FootAerial.com": {"primary": ["football"]},
    "DriftAiry.com": {"full": ["dairy"]},
    "ARTopSight.com": {"required": [["AR + TOP + Sight"]]},
    "RAGFull.com": {"required": [["Retrieval-Augmented Generation"]]},
    "RAGLarge.com": {"required": [["Retrieval-Augmented Generation"]]},
    "OrbitSSP.com": {"required": [["Space Solar Power"]]},
    "Orthoepical.com": {"required": [["pronunciation", "orthoepy"]]},
    "Gravimeters.com": {"required": [["gravity", "gravitational"]]},
    "AccountCcy.com": {"required": [["Currency"]]},
    "EthLea.com": {"required": [["Ethereum"], ["green", "sustainable"]]},
}

NON_PRIMARY_JSON_FIELD = "surface_misreadings_to_avoid"


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def slugify(domain):
    return domain.lower().replace(".", "-")


def check_required(errors, domain, groups, text, location):
    text_lower = text.lower()
    for group in groups:
        if not any(phrase.lower() in text_lower for phrase in group):
            options = " / ".join(f"'{p}'" for p in group)
            errors.append(
                f"{location} {domain}: none of the required phrase(s) {options} were found "
                f"(canonical meaning must be preserved)"
            )


def check_json(errors):
    if not DATA_PATH.exists():
        errors.append(f"Data file not found: {DATA_PATH}")
        return

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assets_by_domain = {a.get("domain"): a for a in raw.get("assets", []) if isinstance(a, dict)}

    for domain, rules in PROTECTED_ASSETS.items():
        asset = assets_by_domain.get(domain)
        if asset is None:
            errors.append(f"Protected asset '{domain}' not found in {DATA_PATH.name}")
            continue

        full_text = json.dumps(asset).lower()
        primary_fields = {k: v for k, v in asset.items() if k != NON_PRIMARY_JSON_FIELD}
        primary_text = json.dumps(primary_fields).lower()

        for phrase in rules.get("full", []):
            if phrase.lower() in full_text:
                errors.append(
                    f"[data] {domain}: forbidden phrase '{phrase}' found anywhere in the record"
                )
        for phrase in rules.get("primary", []):
            if phrase.lower() in primary_text:
                errors.append(
                    f"[data] {domain}: forbidden phrase '{phrase}' found in primary meaning fields "
                    f"(outside {NON_PRIMARY_JSON_FIELD})"
                )
        if "required" in rules:
            check_required(errors, domain, rules["required"], json.dumps(primary_fields), "[data]")


def extract_article(html, domain):
    slug = slugify(domain)
    pattern = re.compile(
        r'<article\b[^>]*\bid="' + re.escape(slug) + r'"[^>]*>(.*?)</article>',
        re.S,
    )
    match = pattern.search(html)
    return match.group(1) if match else None


def extract_defined_term_description(html, domain):
    # JSON-LD entries are single-line objects: { "@type": "DefinedTerm", "name": "Domain.com", "description": "...", ... }
    pattern = re.compile(
        r'\{\s*"@type":\s*"DefinedTerm",\s*"name":\s*"' + re.escape(domain) + r'".*?\}',
    )
    match = pattern.search(html)
    return match.group(0) if match else None


def strip_misreadings_blocks(fragment):
    details_pattern = re.compile(
        r'<details\b[^>]*\bclass="[^"]*misreadings[^"]*"[^>]*>.*?</details>', re.S
    )
    return details_pattern.sub("", fragment)


def check_html(errors):
    if not HTML_PATH.exists():
        errors.append(f"HTML file not found: {HTML_PATH}")
        return

    html = HTML_PATH.read_text(encoding="utf-8")

    for domain, rules in PROTECTED_ASSETS.items():
        article = extract_article(html, domain)
        if article is None:
            errors.append(f"[html] {domain}: <article id=\"{slugify(domain)}\"> not found in {HTML_PATH.name}")
            article = ""

        defined_term = extract_defined_term_description(html, domain)
        if defined_term is None:
            errors.append(f"[html] {domain}: DefinedTerm JSON-LD entry not found in {HTML_PATH.name}")
            defined_term = ""

        # "full" scope covers the whole article (including misreadings) plus the JSON-LD entry.
        full_text = article + " " + defined_term
        # "primary" scope excludes the misreadings <details> block, but JSON-LD has no such
        # exemption (a DefinedTerm description is inherently a primary-meaning statement).
        primary_fragment = strip_misreadings_blocks(article) + " " + defined_term

        for phrase in rules.get("full", []):
            if phrase.lower() in full_text.lower():
                errors.append(
                    f"[html] {domain}: forbidden phrase '{phrase}' found in the artifact block "
                    f"or its JSON-LD DefinedTerm entry in {HTML_PATH.name}"
                )
        for phrase in rules.get("primary", []):
            if phrase.lower() in primary_fragment.lower():
                errors.append(
                    f"[html] {domain}: forbidden phrase '{phrase}' found outside the misreadings "
                    f"<details> block (article body or JSON-LD DefinedTerm entry) in {HTML_PATH.name}"
                )
        if "required" in rules:
            check_required(errors, domain, rules["required"], primary_fragment, "[html]")


def main():
    errors = []
    check_json(errors)
    check_html(errors)

    if errors:
        fail(errors)
        return

    print(f"PASS: {len(PROTECTED_ASSETS)} protected assets clear of forbidden-phrase drift")


if __name__ == "__main__":
    main()
