#!/usr/bin/env python3
"""Validate the Top 75 Meaning Lock Expansion Queue.

Cross-checks data/top-75-meaning-lock-queue.json against its sources and
against the public page that renders it, enforcing the governance rules for
Sprint 8: exactly 25 queued candidates, none already protected, none
presented as an approved canonical meaning.

Usage: python3 scripts/validate_top_75_queue.py
Exits 0 and prints PASS with 25 selected candidates if valid, otherwise
prints each violation prefixed "FAIL:" and exits 1.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPTUAL_INVENTORY_PATH = REPO_ROOT / "data" / "conceptual-inventory.json"
ASSET_MEANINGS_PATH = REPO_ROOT / "data" / "asset-meanings.json"
QUEUE_PATH = REPO_ROOT / "data" / "top-75-meaning-lock-queue.json"
QUEUE_PAGE_PATH = REPO_ROOT / "top-75-queue.html"

EXPECTED_QUEUE_SIZE = 25

REQUIRED_RECORD_FIELDS = [
    "domain",
    "queue_status",
    "priority_tier",
    "selection_rationale",
    "suspected_conceptual_direction",
    "possible_cluster_target",
    "risk_of_misreading",
    "review_required",
    "canonical_meaning_locked",
    "must_not_publish_as_definition",
]

REQUIRED_NON_EMPTY_TEXT_FIELDS = [
    "selection_rationale",
    "suspected_conceptual_direction",
    "risk_of_misreading",
]

REQUIRED_PAGE_DISCLAIMERS = [
    "Queue inclusion does not mean the canonical meaning is approved.",
    "No candidate becomes a Category Artifact until Canonical Meaning Lock is completed.",
]

# Phrases that would falsely claim a queued candidate already has an
# approved/locked/protected meaning. Allowed only inside an explicit
# negation (e.g. "No canonical meaning has been locked for this candidate").
FORBIDDEN_APPROVAL_PHRASES = [
    "canonical meaning is approved",
    "canonical meaning has been approved",
    "approved canonical meaning",
    "canonical meaning has been locked",
    "meaning has been locked for this candidate",
    "protected category artifact",
    "protected-category-artifact",
]

NEGATION_RE = re.compile(r"\b(no|not|never|without)\b", re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_negated(text, match_start):
    window_start = max(0, match_start - 60)
    context = text[window_start:match_start]
    for punct in (".", "!", "?", "\n"):
        pos = context.rfind(punct)
        if pos != -1:
            context = context[pos + 1:]
    return bool(NEGATION_RE.search(context))


def strip_scripts_and_styles(html):
    return STYLE_RE.sub("", SCRIPT_RE.sub("", html))


def check_page_claims(errors):
    if not QUEUE_PAGE_PATH.exists():
        errors.append(f"{QUEUE_PAGE_PATH.relative_to(REPO_ROOT)} not found")
        return

    html = QUEUE_PAGE_PATH.read_text(encoding="utf-8")
    text = strip_scripts_and_styles(html)

    for disclaimer in REQUIRED_PAGE_DISCLAIMERS:
        if disclaimer not in html:
            errors.append(
                f"top-75-queue.html: missing required disclaimer sentence: '{disclaimer}'"
            )

    lowered = text.lower()
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        start = 0
        while True:
            idx = lowered.find(phrase, start)
            if idx == -1:
                break
            if not is_negated(text, idx):
                snippet = text[max(0, idx - 40):idx + len(phrase) + 10].replace("\n", " ")
                errors.append(
                    f"top-75-queue.html: claims approved/protected meaning via phrase '{phrase}' "
                    f"without negation near: ...{snippet.strip()}..."
                )
            start = idx + len(phrase)


def main():
    errors = []

    for path in (CONCEPTUAL_INVENTORY_PATH, ASSET_MEANINGS_PATH, QUEUE_PATH):
        if not path.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)} not found")
    if errors:
        fail(errors)
        return

    inventory = load_json(CONCEPTUAL_INVENTORY_PATH)
    inventory_status_by_domain = {
        r["domain"].strip().lower(): r["status"] for r in inventory.get("records", [])
    }

    asset_meanings_raw = load_json(ASSET_MEANINGS_PATH)
    asset_domains = {
        a.get("domain", "").strip().lower()
        for a in asset_meanings_raw.get("assets", [])
        if isinstance(a, dict) and a.get("domain")
    }

    queue_raw = load_json(QUEUE_PATH)
    queue = queue_raw.get("queue")
    if not isinstance(queue, list):
        fail([f"{QUEUE_PATH.relative_to(REPO_ROOT)}: top-level 'queue' must be a list"])
        return

    if len(queue) != EXPECTED_QUEUE_SIZE:
        errors.append(
            f"{QUEUE_PATH.relative_to(REPO_ROOT)}: queue has {len(queue)} records, expected "
            f"exactly {EXPECTED_QUEUE_SIZE}"
        )

    seen_domains = {}
    for i, record in enumerate(queue):
        if not isinstance(record, dict):
            errors.append(f"queue record #{i}: entry is not an object")
            continue

        missing = [f for f in REQUIRED_RECORD_FIELDS if f not in record]
        if missing:
            errors.append(f"queue record #{i}: missing required field(s): {', '.join(missing)}")
            continue

        domain = record["domain"]
        key = domain.strip().lower() if isinstance(domain, str) else ""
        label = domain if isinstance(domain, str) and domain else f"record #{i}"

        if not key:
            errors.append(f"queue record #{i}: 'domain' must be a non-empty string")
        else:
            if key in seen_domains:
                errors.append(
                    f"duplicate domain '{domain}' (records #{seen_domains[key]} and #{i})"
                )
            else:
                seen_domains[key] = i

            if key in asset_domains:
                errors.append(
                    f"'{label}' is already protected in "
                    f"{ASSET_MEANINGS_PATH.relative_to(REPO_ROOT)} — must not be queued"
                )

            status = inventory_status_by_domain.get(key)
            if status is None:
                errors.append(
                    f"'{label}' not found in {CONCEPTUAL_INVENTORY_PATH.relative_to(REPO_ROOT)}"
                )
            elif status != "pending-canonical-meaning-lock":
                errors.append(
                    f"'{label}' has conceptual-inventory status '{status}', expected "
                    f"'pending-canonical-meaning-lock'"
                )

        if record.get("canonical_meaning_locked") is not False:
            errors.append(f"'{label}': canonical_meaning_locked must be exactly false")
        if record.get("review_required") is not True:
            errors.append(f"'{label}': review_required must be exactly true")
        if record.get("must_not_publish_as_definition") is not True:
            errors.append(f"'{label}': must_not_publish_as_definition must be exactly true")

        for field in REQUIRED_NON_EMPTY_TEXT_FIELDS:
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"'{label}': field '{field}' must not be empty")

        if record.get("queue_status") != "selected-for-meaning-lock-review":
            errors.append(
                f"'{label}': queue_status must be 'selected-for-meaning-lock-review', got "
                f"{record.get('queue_status')!r}"
            )
        if record.get("priority_tier") != "top-75-candidate":
            errors.append(
                f"'{label}': priority_tier must be 'top-75-candidate', got "
                f"{record.get('priority_tier')!r}"
            )

    check_page_claims(errors)

    if errors:
        fail(errors)
        return

    print(f"PASS: top 75 meaning lock expansion queue valid — {len(queue)} selected candidates")


if __name__ == "__main__":
    main()
