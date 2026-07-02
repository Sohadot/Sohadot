#!/usr/bin/env python3
"""Validate the Service Boundary: Sohadot does not present itself as a
third-party domain brokerage service.

Sohadot remains a Domain Intelligence & Sovereign Digital Asset platform. It
may handle direct inquiries and acquisition processes for Sohadot-owned
assets, and may guide seller-approved escrow closing after written agreement
for Sohadot-owned assets. It must not claim to broker, represent, or
negotiate third-party domain transactions it does not own.

Scans public HTML, README.md, docs/*.md, data/*.json (excluding raw lexical
word-list datasets, which are dictionaries, not service copy), and llms.txt
for language that would present Sohadot as a brokerage. A forbidden phrase is
only a failure if it is not explicitly negated in context (e.g. "Sohadot does
not operate as a third-party domain broker" is allowed; "direct domain
brokerage" as a plain service claim is not).

Usage: python3 scripts/validate_service_boundary.py
Exits 0 and prints PASS if valid, otherwise prints each violation prefixed
"FAIL:" and exits 1.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STRATEGIC_BRIEF_PATH = REPO_ROOT / "strategic-brief.html"
ESCROW_CLOSING_PATH = REPO_ROOT / "escrow-closing.html"
README_PATH = REPO_ROOT / "README.md"

# Raw lexical/word-list datasets: dictionaries of individual words used by the
# valuation engine's classification logic, not site copy or service claims.
# "brokerage" legitimately appears here as a dictionary entry (like thousands
# of other words) and is out of scope for a service-boundary check.
EXCLUDED_DATA_FILES = {
    "english_words.json",
    "extended_words.json",
    "multilingual_words.json",
    "rare_words.json",
    "lexical_words.json",
    "names.json",
    "industry_map.json",
}

# Multi-word phrases that would present Sohadot itself as a brokerage/
# representation service. Each occurrence must be explicitly negated.
FORBIDDEN_PHRASES = [
    "domain brokerage",
    "direct domain brokerage",
    "brokerage service",
    "acquisition broker",
    "buyer representation",
    "seller representation",
    "third-party domain sale",
    "third-party seller",
    "we broker domains",
    "we negotiate third-party domain sales",
    "domain investor and broker",
    "brokerage",
]

NEGATION_RE = re.compile(r"\b(no|not|never|without|does not|doesn't|isn't|is not)\b", re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)

# Catches a self-referential claim that Sohadot itself brokers third-party
# transactions, e.g. "Sohadot brokers domains" or "we broker third-party
# sales" — flagged unless explicitly negated in the same local window.
SELF_BROKER_CLAIM_RE = re.compile(
    r"\b(sohadot|we)\b[^.!?\n]{0,60}\bbroker(?:s|ing|ed)?\b", re.IGNORECASE
)


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def strip_scripts_and_styles(html):
    return STYLE_RE.sub("", SCRIPT_RE.sub("", html))


def is_negated(text, match_start):
    window_start = max(0, match_start - 60)
    context = text[window_start:match_start]
    for punct in (".", "!", "?", "\n"):
        pos = context.rfind(punct)
        if pos != -1:
            context = context[pos + 1:]
    return bool(NEGATION_RE.search(context))


def collect_target_files():
    files = []

    for path in sorted(REPO_ROOT.glob("*.html")):
        files.append(path)
    kb_dir = REPO_ROOT / "kb"
    if kb_dir.is_dir():
        for path in sorted(kb_dir.glob("*.html")):
            files.append(path)

    if README_PATH.exists():
        files.append(README_PATH)

    docs_dir = REPO_ROOT / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.glob("*.md")):
            files.append(path)

    data_dir = REPO_ROOT / "data"
    if data_dir.is_dir():
        for path in sorted(data_dir.glob("*.json")):
            if path.name not in EXCLUDED_DATA_FILES:
                files.append(path)

    llms_path = REPO_ROOT / "llms.txt"
    if llms_path.exists():
        files.append(llms_path)

    return files


def check_file(path, errors):
    raw = path.read_text(encoding="utf-8")
    text = strip_scripts_and_styles(raw) if path.suffix == ".html" else raw
    rel = path.relative_to(REPO_ROOT)
    lowered = text.lower()

    for phrase in FORBIDDEN_PHRASES:
        start = 0
        while True:
            idx = lowered.find(phrase, start)
            if idx == -1:
                break
            if not is_negated(text, idx):
                snippet = text[max(0, idx - 40):idx + len(phrase) + 20].replace("\n", " ")
                errors.append(
                    f"{rel}: forbidden service-boundary phrase '{phrase}' used as a live claim "
                    f"(not negated) near: ...{snippet.strip()}..."
                )
            start = idx + len(phrase)

    for match in SELF_BROKER_CLAIM_RE.finditer(text):
        negated_within_span = bool(NEGATION_RE.search(match.group()))
        if not negated_within_span and not is_negated(text, match.start()):
            snippet = text[max(0, match.start() - 20):match.end() + 20].replace("\n", " ")
            errors.append(
                f"{rel}: claims Sohadot brokers/represents third-party domain transactions near: "
                f"...{snippet.strip()}..."
            )


def check_readme_boundary_statement(errors):
    if not README_PATH.exists():
        errors.append("README.md not found")
        return
    text = README_PATH.read_text(encoding="utf-8")
    equivalents = [
        "Sohadot does not operate as a third-party domain broker",
        "does not operate as a third-party domain broker",
    ]
    if not any(phrase in text for phrase in equivalents):
        errors.append(
            "README.md: missing required boundary statement equivalent to "
            "'Sohadot does not operate as a third-party domain broker'"
        )


def check_strategic_brief_exists(errors):
    if not STRATEGIC_BRIEF_PATH.exists():
        errors.append("strategic-brief.html not found — Strategic Brief must not be removed")
        return
    text = STRATEGIC_BRIEF_PATH.read_text(encoding="utf-8")
    if "strategic brief" not in text.lower():
        errors.append("strategic-brief.html: does not appear to contain the Strategic Brief request flow")


def check_escrow_closing_exists(errors):
    if not ESCROW_CLOSING_PATH.exists():
        errors.append("escrow-closing.html not found — Escrow Closing Protocol must not be removed")
        return
    text = ESCROW_CLOSING_PATH.read_text(encoding="utf-8")
    if "escrow" not in text.lower():
        errors.append("escrow-closing.html: does not appear to contain the Escrow Closing Protocol content")


def main():
    errors = []

    files = collect_target_files()
    if not files:
        fail(["no target files found to scan"])
        return

    for path in files:
        try:
            check_file(path, errors)
        except UnicodeDecodeError:
            pass

    check_readme_boundary_statement(errors)
    check_strategic_brief_exists(errors)
    check_escrow_closing_exists(errors)

    if errors:
        fail(errors)
        return

    print(f"PASS: service boundary clean across {len(files)} scanned files — no brokerage service claims found")


if __name__ == "__main__":
    main()
