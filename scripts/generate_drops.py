#!/usr/bin/env python3
import csv
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "drops_candidates.csv"
JSON_PATH = DATA_DIR / "drops.json"

UTC = timezone.utc

# ----------------------------
# Configuration
# ----------------------------

QUALITY_TLDS = {
    ".com": 20,
    ".ai": 16,
    ".io": 13,
    ".co": 11,
    ".net": 6,
    ".org": 5,
}

CATEGORY_KEYWORDS = {
    "ai": [
        "ai", "agent", "agents", "agi", "asi", "neural", "rag", "model", "models",
        "prompt", "token", "genie", "llm", "vision", "synthetic", "reason", "cognitive"
    ],
    "finance": [
        "pay", "payments", "cash", "coin", "crypto", "wealth", "bank", "capital",
        "fund", "funds", "finance", "fin", "ledger", "logic", "trade", "trader", "wallet"
    ],
    "tech": [
        "stack", "scan", "cloud", "data", "pulse", "dev", "ops", "api", "core",
        "system", "token", "saas", "sync", "flow", "tech", "compute", "quantum"
    ],
    "health": [
        "health", "mind", "bio", "genomic", "genome", "crispr", "care", "med",
        "clinic", "well", "wellness", "therapy"
    ],
    "geo": [
        "austin", "detroit", "dubai", "singapore", "geneva", "london", "paris",
        "berlin", "tokyo", "map", "city", "geo", "local"
    ],
}

CATEGORY_LABELS = {
    "ai": "AI",
    "finance": "Finance / Crypto",
    "tech": "Tech / SaaS",
    "health": "Health",
    "geo": "Geo",
    "brand": "Brand",
}

CATEGORY_WEIGHTS = {
    "ai": 14,
    "finance": 12,
    "tech": 11,
    "health": 9,
    "geo": 7,
    "brand": 8,
}

SOURCE_LABELS = {
    "godaddy": "GoDaddy Auctions",
    "godaddy auctions": "GoDaddy Auctions",
    "afternic": "Afternic",
    "atom": "Atom",
    "namecheap": "Namecheap",
    "expireddomains": "ExpiredDomains.net",
    "expireddomains.net": "ExpiredDomains.net",
    "namejet": "NameJet",
}

STATUS_REGISTERED = "Still registered — near drop window"
STATUS_UNCONFIRMED = "Status unconfirmed — near drop window"
STATUS_POSSIBLE = "Possibly available soon"

# ----------------------------
# Utilities
# ----------------------------

def now_utc() -> datetime:
    return datetime.now(UTC)

def parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%b %d %Y", "%b %d, %Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None

def human_date(dt: datetime) -> str:
    return dt.strftime("%B %d, %Y %H:%M UTC")

def next_monday_8am_utc(from_dt: datetime) -> datetime:
    days_ahead = (7 - from_dt.weekday()) % 7
    if days_ahead == 0 and from_dt.hour >= 8:
        days_ahead = 7
    target = (from_dt + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0, microsecond=0)
    return target

def clean_source(source: str) -> str:
    if not source:
        return "Unknown"
    s = source.strip().lower()
    return SOURCE_LABELS.get(s, source.strip())

def split_domain(domain: str) -> Tuple[str, str]:
    domain = domain.strip().lower()
    if "." not in domain:
        return domain, ""
    parts = domain.rsplit(".", 1)
    return parts[0], "." + parts[1]

def has_hyphen_or_digit(name: str) -> bool:
    return bool(re.search(r"[-\d]", name))

def looks_pronounceable(name: str) -> bool:
    vowels = sum(1 for ch in name if ch in "aeiou")
    if len(name) <= 3:
        return True
    ratio = vowels / max(len(name), 1)
    return 0.20 <= ratio <= 0.65

def token_count(name: str) -> int:
    return len(re.findall(r"[a-z]+", name))

def sentence_case(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    return text[0].upper() + text[1:]

def clamp(n: float, low: float, high: float) -> float:
    return max(low, min(high, n))

# ----------------------------
# Classification
# ----------------------------

def classify_category(name: str) -> str:
    lowered = name.lower()

    scores = {k: 0 for k in CATEGORY_KEYWORDS.keys()}

    for category, keywords in CATEGORY_KEYWORDS.items():
      for kw in keywords:
        if kw in lowered:
          scores[category] += 2
        if lowered.startswith(kw) or lowered.endswith(kw):
          scores[category] += 1

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] <= 0:
        return "brand"
    return best_cat

def category_label(cat: str) -> str:
    return CATEGORY_LABELS.get(cat, "Brand")

# ----------------------------
# Scoring
# ----------------------------

def length_score(name: str) -> int:
    l = len(name)
    if l <= 4:
        return 20
    if l <= 6:
        return 18
    if l <= 8:
        return 15
    if l <= 10:
        return 12
    if l <= 12:
        return 9
    if l <= 14:
        return 5
    return 2

def structure_score(name: str) -> int:
    score = 0

    if not has_hyphen_or_digit(name):
        score += 10
    else:
        score -= 6

    if looks_pronounceable(name):
        score += 8

    if token_count(name) <= 2:
        score += 5

    if name.isalpha():
        score += 4

    return score

def brandability_score(name: str) -> int:
    score = 0
    l = len(name)

    if 5 <= l <= 10:
        score += 10
    elif 11 <= l <= 12:
        score += 6
    elif l <= 4:
        score += 8
    else:
        score += 2

    if looks_pronounceable(name):
        score += 8

    if not has_hyphen_or_digit(name):
        score += 4

    if re.search(r"(ly|io|ify|gen|flow|core|logic|scan|pulse|vault|mate)$", name):
        score += 3

    return score

def tld_score(tld: str) -> int:
    return QUALITY_TLDS.get(tld, 2)

def status_score(registered_now: Optional[bool], rdap_ok: bool) -> int:
    if registered_now is True:
        return 3
    if registered_now is False:
        return 7
    if not rdap_ok:
        return 1
    return 2

def compute_score(name: str, tld: str, cat: str, registered_now: Optional[bool], rdap_ok: bool) -> int:
    raw = 0
    raw += length_score(name)
    raw += structure_score(name)
    raw += brandability_score(name)
    raw += tld_score(tld)
    raw += CATEGORY_WEIGHTS.get(cat, 6)
    raw += status_score(registered_now, rdap_ok)

    # Small penalty for being too long
    if len(name) >= 13:
        raw -= 6

    # Small penalty for geo unless strong use case
    if cat == "geo" and len(name) > 10:
        raw -= 2

    return int(clamp(raw, 52, 92))

def score_class(score: int) -> str:
    if score >= 80:
        return "hi"
    if score >= 68:
        return "mid"
    return "low"

# ----------------------------
# Value estimation
# ----------------------------

def estimate_value_range(score: int, cat: str, tld: str, name: str) -> Tuple[int, int]:
    base_low = 180
    base_high = 420

    # Score multiplier
    mult = score / 70.0

    # TLD premium
    tld_mult = {
        ".com": 2.4,
        ".ai": 1.9,
        ".io": 1.55,
        ".co": 1.35,
    }.get(tld, 1.0)

    # Category premium
    cat_mult = {
        "ai": 1.45,
        "finance": 1.38,
        "tech": 1.30,
        "health": 1.22,
        "geo": 1.08,
        "brand": 1.18,
    }.get(cat, 1.0)

    # Length premium
    if len(name) <= 6:
        len_mult = 1.45
    elif len(name) <= 8:
        len_mult = 1.28
    elif len(name) <= 10:
        len_mult = 1.14
    elif len(name) <= 12:
        len_mult = 1.00
    else:
        len_mult = 0.84

    low = base_low * mult * tld_mult * cat_mult * len_mult
    high = base_high * mult * tld_mult * cat_mult * len_mult * 1.85

    low = int(round(low / 5) * 5)
    high = int(round(high / 5) * 5)

    if high <= low:
        high = low + 150

    return low, high

def fmt_money_range(low: int, high: int) -> str:
    return f"${low:,}–{high:,}"

# ----------------------------
# Status / copy
# ----------------------------

def build_status_label(registered_now: Optional[bool], rdap_ok: bool) -> str:
    if registered_now is True:
        return STATUS_REGISTERED
    if registered_now is False:
        return STATUS_POSSIBLE
    if not rdap_ok:
        return STATUS_UNCONFIRMED
    return STATUS_UNCONFIRMED

def short_category_reason(cat: str, name: str, tld: str) -> str:
    reasons = {
        "ai": "Strong AI positioning",
        "finance": "Solid finance / crypto naming logic",
        "tech": "Good B2B / SaaS naming pattern",
        "health": "Clear digital-health angle",
        "geo": "Localized utility or directory potential",
        "brand": "Brandable commercial name",
    }
    base = reasons.get(cat, "Commercially usable domain")
    if len(name) <= 8:
        base += ", compact length"
    elif len(name) <= 10:
        base += ", manageable length"
    else:
        base += ", longer but still commercially usable"

    if tld == ".com":
        base += ". .com strengthens resale liquidity"
    elif tld == ".ai":
        base += ". .ai supports AI-market relevance"
    elif tld == ".io":
        base += ". .io fits modern tech usage"
    elif tld == ".co":
        base += ". .co remains startup-friendly"

    return sentence_case(base)

def build_why(cat: str, label: str, name: str, tld: str, registered_now: Optional[bool], rdap_ok: bool) -> str:
    base = short_category_reason(cat, name, tld)
    status = build_status_label(registered_now, rdap_ok)

    if status == STATUS_REGISTERED:
        status_text = "Still registered — near drop window."
    elif status == STATUS_POSSIBLE:
        status_text = "Possibly available soon."
    else:
        status_text = "Status unconfirmed — near drop window."

    return f"{base}. Category fit: {label}. {status_text}"

# ----------------------------
# Featured picks
# ----------------------------

def choose_featured(domains: List[Dict], n: int = 3) -> List[Dict]:
    # sort by score desc, then by shorter length, then .com preference
    ranked = sorted(
        domains,
        key=lambda d: (
            d["score"],
            1 if d["tld"] == ".com" else 0,
            -len(d["name"]),
        ),
        reverse=True
    )

    chosen = []
    used_cats = set()

    # first pass: diversify categories
    for item in ranked:
        if item["category"] not in used_cats:
            chosen.append(item)
            used_cats.add(item["category"])
        if len(chosen) == n:
            break

    # second pass: fill if needed
    if len(chosen) < n:
        for item in ranked:
            if item not in chosen:
                chosen.append(item)
            if len(chosen) == n:
                break

    return chosen[:n]

# ----------------------------
# Input loading
# ----------------------------

def parse_boolish(value: str) -> Optional[bool]:
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"true", "yes", "1", "registered", "registered_now"}:
        return True
    if v in {"false", "no", "0", "available", "not_registered"}:
        return False
    return None

def parse_row(row: Dict[str, str]) -> Dict:
    domain = row.get("domain", "").strip().lower()
    source = clean_source(row.get("source", "").strip())
    drop_date = parse_date(row.get("drop_date", "").strip())
    rdap_ok = row.get("rdap_ok", "").strip().lower() in {"true", "yes", "1"}
    registered_now = parse_boolish(row.get("registered_now", ""))
    rdap_error = row.get("rdap_error", "").strip() or None

    name, tld = split_domain(domain)
    cat = classify_category(name)
    label = category_label(cat)
    score = compute_score(name, tld, cat, registered_now, rdap_ok)
    low, high = estimate_value_range(score, cat, tld, name)

    now = now_utc()
    urgency = "soon"
    if drop_date:
        days = (drop_date.date() - now.date()).days
        if days <= 3:
            urgency = "urgent"
        elif days <= 7:
            urgency = "soon"
        else:
            urgency = ""

    drop_label = drop_date.strftime("%b %-d") if drop_date else "TBD"
    # Windows fallback
    if "%-" in "%-d":
        pass
    if drop_date and drop_label == "TBD":
        drop_label = drop_date.strftime("%b %d").replace(" 0", " ")

    why = build_why(cat, label, name, tld, registered_now, rdap_ok)
    status_label = build_status_label(registered_now, rdap_ok)

    return {
        "domain": domain,
        "name": name,
        "tld": tld,
        "source": source,
        "score": score,
        "score_class": score_class(score),
        "length": len(name),
        "category": cat,
        "category_label": label,
        "drop_label": drop_label,
        "drop_sort": drop_date.strftime("%Y-%m-%d") if drop_date else "",
        "drop_date": drop_date.strftime("%Y-%m-%d") if drop_date else "",
        "urgency": urgency,
        "value_low": low,
        "value_high": high,
        "value_range": fmt_money_range(low, high),
        "value_sort": high,
        "why": why,
        "status_label": status_label,
        "rdap_ok": rdap_ok,
        "registered_now": registered_now,
        "rdap_error": rdap_error,
        "check_url": f"https://www.godaddy.com/domainsearch/find?checkAvail=1&domainToCheck={domain}",
    }

def load_candidates() -> List[Dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing CSV file: {CSV_PATH}")

    rows = []
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("domain"):
                continue
            rows.append(parse_row(row))
    return rows

# ----------------------------
# JSON build
# ----------------------------

def build_json(domains: List[Dict]) -> Dict:
    now = now_utc()
    next_update = next_monday_8am_utc(now)

    domains_sorted = sorted(
        domains,
        key=lambda d: (d["score"], d["value_high"], 1 if d["tld"] == ".com" else 0),
        reverse=True
    )

    featured = choose_featured(domains_sorted, 3)

    featured_json = []
    for item in featured:
        featured_json.append({
            "badge": "Top Pick",
            "domain": item["domain"],
            "score": item["score"],
            "tld": item["tld"],
            "length": item["length"],
            "category": item["category_label"],
            "drop_label": item["drop_label"],
            "urgency": item["urgency"],
            "why": item["why"],
            "value_range": item["value_range"],
            "status_label": item["status_label"],
            "check_url": item["check_url"],
        })

    unique_sources = []
    for d in domains_sorted:
        if d["source"] not in unique_sources:
            unique_sources.append(d["source"])

    return {
        "week_label": f"Curated Weekly Drops Watchlist — Week of {now.strftime('%b %-d, %Y').replace(' 0', ' ')}",
        "last_updated": now.isoformat(),
        "last_updated_human": human_date(now),
        "next_update_label": "Next Monday refresh",
        "next_update_iso": next_update.isoformat().replace("+00:00", "Z"),
        "curated_count": len(domains_sorted),
        "sources": unique_sources,
        "criteria": [
            "Short, brandable, commercially plausible names preferred",
            "Quality TLDs prioritized (.com / .ai / .io / .co)",
            "Category fit used as directional weighting, not absolute truth",
            "RDAP used where possible to distinguish watchlist vs likely-available names",
            "Comparable-sales style valuation shown as directional guidance only",
            "Featured picks selected for quality plus category diversity"
        ],
        "featured": featured_json,
        "domains": [
            {
                "domain": d["domain"],
                "source": d["source"],
                "score": d["score"],
                "score_class": d["score_class"],
                "length": d["length"],
                "category": d["category"],
                "category_label": d["category_label"],
                "drop_label": d["drop_label"],
                "drop_sort": d["drop_sort"],
                "drop_date": d["drop_date"],
                "urgency": d["urgency"],
                "value_range": d["value_range"],
                "value_sort": d["value_sort"],
                "why": d["why"],
                "status_label": d["status_label"],
                "rdap_ok": d["rdap_ok"],
                "registered_now": d["registered_now"],
                "rdap_error": d["rdap_error"],
                "check_url": d["check_url"],
            }
            for d in domains_sorted
        ]
    }

# ----------------------------
# Main
# ----------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    domains = load_candidates()
    payload = build_json(domains)

    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {JSON_PATH} with {len(payload['domains'])} domains.")

if __name__ == "__main__":
    main()
