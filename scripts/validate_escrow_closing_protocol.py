#!/usr/bin/env python3
"""Validate the Seller-Approved Escrow Closing Protocol layer.

Checks that the public escrow-closing.html page, its two docs, the sitemap,
and the README stay consistent with a hard boundary: escrow is documented as
a seller-approved closing path that begins only after written agreement, and
the page contains no public purchase mechanism, pricing table, or payment
form, and no hardcoded secrets or API placeholders.

Usage: python3 scripts/validate_escrow_closing_protocol.py
Exits 0 and prints PASS if valid, otherwise prints each violation prefixed
"FAIL:" and exits 1.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ESCROW_PAGE_PATH = REPO_ROOT / "escrow-closing.html"
PROTOCOL_DOC_PATH = REPO_ROOT / "docs" / "ESCROW_CLOSING_PROTOCOL.md"
LAUNCHER_SPEC_PATH = REPO_ROOT / "docs" / "OPERATOR_ESCROW_LAUNCHER_SPEC.md"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
README_PATH = REPO_ROOT / "README.md"
STRATEGIC_BRIEF_PATH = REPO_ROOT / "strategic-brief.html"
BRIEF_OPTIONS_PATH = REPO_ROOT / "data" / "brief-request-options.json"

REQUIRED_ESCROW_PAGE_PHRASES = [
    "seller approval",
    "written agreement",
    "independent escrow",
    "does not process direct payments on-site",
    "not a marketplace",
    "not a checkout",
    "not a buy-now flow",
]

# Public transaction-starting language that must never appear as live CTA
# wording — only allowed as an explicit negation ("not a checkout").
FORBIDDEN_TRANSACTION_PHRASES = [
    "buy now",
    "checkout",
    "pay now",
    "purchase instantly",
    "start transaction now",
]

SECRET_PLACEHOLDER_PATTERNS = [
    "api_key",
    "escrow_password",
    "secret",
    "bearer token",
    "client_secret",
]

REQUIRED_README_MENTION = "Seller-Approved Escrow Closing Protocol"
REQUIRED_SITEMAP_ENTRY = "/escrow-closing.html"
REQUIRED_INQUIRY_TYPE_LABEL = "Escrow closing after written agreement"

NEGATION_RE = re.compile(r"\b(no|not|never|without)\b", re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def is_negated(text, match_start):
    window_start = max(0, match_start - 40)
    context = text[window_start:match_start]
    for punct in (".", "!", "?", "\n"):
        pos = context.rfind(punct)
        if pos != -1:
            context = context[pos + 1:]
    return bool(NEGATION_RE.search(context))


def check_existence(errors):
    for path, label in (
        (ESCROW_PAGE_PATH, "escrow-closing.html"),
        (PROTOCOL_DOC_PATH, "docs/ESCROW_CLOSING_PROTOCOL.md"),
        (LAUNCHER_SPEC_PATH, "docs/OPERATOR_ESCROW_LAUNCHER_SPEC.md"),
    ):
        if not path.exists():
            errors.append(f"{label}: file not found at {path}")


def check_sitemap(errors):
    if not SITEMAP_PATH.exists():
        errors.append(f"sitemap.xml not found at {SITEMAP_PATH}")
        return
    text = SITEMAP_PATH.read_text(encoding="utf-8")
    if REQUIRED_SITEMAP_ENTRY not in text:
        errors.append(f"sitemap.xml: missing required entry '{REQUIRED_SITEMAP_ENTRY}'")


def check_readme(errors):
    if not README_PATH.exists():
        errors.append(f"README.md not found at {README_PATH}")
        return
    text = README_PATH.read_text(encoding="utf-8")
    if REQUIRED_README_MENTION not in text:
        errors.append(f"README.md: missing required mention '{REQUIRED_README_MENTION}'")


def check_escrow_page_required_phrases(html, errors):
    lowered = html.lower()
    for phrase in REQUIRED_ESCROW_PAGE_PHRASES:
        if phrase not in lowered:
            errors.append(f"escrow-closing.html: missing required phrase '{phrase}'")


def check_escrow_page_forbidden_phrases(html, errors):
    lowered = html.lower()
    for phrase in FORBIDDEN_TRANSACTION_PHRASES:
        start = 0
        while True:
            idx = lowered.find(phrase, start)
            if idx == -1:
                break
            if not is_negated(html, idx):
                snippet = html[max(0, idx - 30):idx + len(phrase) + 10].replace("\n", " ")
                errors.append(
                    f"escrow-closing.html: forbidden transaction-starting phrase '{phrase}' used "
                    f"without negation near: ...{snippet.strip()}..."
                )
            start = idx + len(phrase)


def check_escrow_page_secrets(html, errors):
    lowered = html.lower()
    for pattern in SECRET_PLACEHOLDER_PATTERNS:
        if pattern in lowered:
            errors.append(
                f"escrow-closing.html: contains possible secret/API placeholder '{pattern}' — "
                f"this public page must never carry credentials or integration secrets"
            )


def check_inquiry_type_present(errors):
    found = False
    for path in (STRATEGIC_BRIEF_PATH, BRIEF_OPTIONS_PATH):
        if path.exists() and REQUIRED_INQUIRY_TYPE_LABEL in path.read_text(encoding="utf-8"):
            found = True
            break
    if not found:
        errors.append(
            f"strategic-brief.html and data/brief-request-options.json: neither contains the "
            f"required inquiry type '{REQUIRED_INQUIRY_TYPE_LABEL}'"
        )


def main():
    errors = []
    check_existence(errors)
    check_sitemap(errors)
    check_readme(errors)
    check_inquiry_type_present(errors)

    if ESCROW_PAGE_PATH.exists():
        html = ESCROW_PAGE_PATH.read_text(encoding="utf-8")
        check_escrow_page_required_phrases(html, errors)
        stripped = STYLE_RE.sub("", SCRIPT_RE.sub("", html))
        check_escrow_page_forbidden_phrases(stripped, errors)
        check_escrow_page_secrets(stripped, errors)

    if errors:
        fail(errors)
        return

    print("PASS: seller-approved escrow closing protocol clean — public boundary intact")


if __name__ == "__main__":
    main()
