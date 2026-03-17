import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import urllib.request
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "drops_candidates.csv"
JSON_PATH = ROOT / "data" / "drops.json"


TLD_WEIGHTS = {
    "com": 24,
    "ai": 20,
    "io": 17,
    "co": 13,
    "org": 10,
    "net": 8,
}

CATEGORY_RULES = {
    "ai": ["ai", "agent", "agents", "neural", "rag", "llm", "gpt", "model"],
    "finance": ["pay", "cash", "coin", "crypto", "bank", "fund", "capital", "wallet"],
    "health": ["health", "med", "clinic", "bio", "well", "mind"],
    "geo": ["city", "map", "dubai", "geneva", "singapore", "miami", "detroit", "austin"],
    "tech": ["stack", "scan", "cloud", "token", "data", "labs", "logic", "sync"],
    "brand": [],
}

CATEGORY_LABELS = {
    "ai": "AI",
    "finance": "Finance / Crypto",
    "health": "Health",
    "geo": "Geo",
    "tech": "Tech / SaaS",
    "brand": "Brand",
}

CATEGORY_PRIORITY = {
    "ai": 5,
    "finance": 5,
    "tech": 4,
    "health": 4,
    "geo": 3,
    "brand": 2,
}

KEYWORD_BONUS = {
    "ai": 8,
    "agent": 10,
    "agents": 10,
    "neural": 7,
    "rag": 7,
    "cash": 7,
    "coin": 7,
    "pay": 8,
    "stack": 6,
    "scan": 6,
    "health": 7,
    "mind": 5,
    "token": 6,
    "logic": 5,
    "map": 4,
}

QUALITY_WORDS = {
    "flare", "pulse", "logic", "mate", "folio", "scan", "vault", "link",
    "genie", "factor", "stack", "mind", "health", "cash", "coin"
}

WEAK_WORDS = {
    "significant", "consistent"
}

SOURCE_WEIGHTS = {
    "GoDaddy Auctions": 6,
    "Afternic": 5,
    "Atom": 5,
    "Namecheap": 4,
    "Unknown": 2,
}


def slug_words(name: str) -> List[str]:
    return re.findall(r"[a-z]+", name.lower())


def split_domain(domain: str) -> Tuple[str, str]:
    parts = domain.lower().strip().split(".")
    if len(parts) < 2:
        return domain.lower().strip(), ""
    return parts[0], parts[-1]


def is_pure_alpha(sld: str) -> bool:
    return bool(re.fullmatch(r"[a-z]+", sld))


def has_hyphen_or_number(sld: str) -> bool:
    return bool(re.search(r"[-0-9]", sld))


def length_score(length: int) -> int:
    if length <= 4:
        return 24
    if length <= 6:
        return 22
    if length <= 8:
        return 18
    if length <= 10:
        return 14
    if length <= 12:
        return 10
    return 4


def pronounceability_score(sld: str) -> int:
    vowels = len(re.findall(r"[aeiou]", sld))
    if len(sld) == 0:
        return 0
    ratio = vowels / len(sld)
    if 0.25 <= ratio <= 0.6:
        return 10
    if 0.15 <= ratio <= 0.7:
        return 6
    return 2


def quality_word_score(words: List[str]) -> int:
    score = 0
    for word in words:
        if word in QUALITY_WORDS:
            score += 3
        if word in WEAK_WORDS:
            score -= 2
        if word in KEYWORD_BONUS:
            score += KEYWORD_BONUS[word]
    return max(score, 0)


def detect_category(sld: str) -> str:
    words = slug_words(sld)
    joined = " ".join(words)
    for category, keywords in CATEGORY_RULES.items():
        if not keywords:
            continue
        for kw in keywords:
            if kw in joined or kw in sld:
                return category
    return "brand"


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, "Brand")


def source_score(source: str) -> int:
    return SOURCE_WEIGHTS.get(source or "Unknown", 2)


def score_class(score: int) -> str:
    if score >= 85:
        return "hi"
    if score >= 70:
        return "mid"
    return "low"


def compute_status(rdap_ok: bool, registered_now: Optional[bool], drop_date: str) -> Tuple[str, str]:
    try:
        d = datetime.strptime(drop_date, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        days = (d - today).days
    except Exception:
        days = None

    if rdap_ok and registered_now is False:
        return "likely_available", "Likely available now"

    if rdap_ok and registered_now is True:
        if days is not None and days <= 2:
            return "expiring", "Still registered — near drop window"
        return "watchlist", "Still registered — watchlist candidate"

    if not rdap_ok:
        if days is not None and days <= 2:
            return "unconfirmed", "Status unconfirmed — near drop window"
        return "watchlist", "Status unconfirmed — watchlist candidate"

    return "watchlist", "Watchlist candidate"


def urgency_from_date(drop_date: str) -> str:
    try:
        d = datetime.strptime(drop_date, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        days = (d - today).days
        if days <= 2:
            return "urgent"
        if days <= 5:
            return "soon"
        return "normal"
    except Exception:
        return "normal"


def estimate_value(score: int, category: str, tld: str, length: int) -> Tuple[str, int]:
    base = 250

    if tld == "com":
        base += 250
    elif tld in {"ai", "io"}:
        base += 180
    elif tld == "co":
        base += 100

    base += score * 8

    if category in {"ai", "finance", "tech"}:
        base += 120

    if length <= 8:
        base += 140
    elif length <= 10:
        base += 60

    low = max(200, int(base * 0.7))
    high = max(low + 150, int(base * 1.5))
    return f"${low:,}–{high:,}", high


def make_why(domain: str, category: str, length: int, tld: str, status_label: str) -> str:
    parts = []
    cat_label = category_label(category)

    if category == "ai":
        parts.append("Strong AI positioning")
    elif category == "finance":
        parts.append("Commercial fintech / crypto relevance")
    elif category == "tech":
        parts.append("Good B2B / SaaS naming pattern")
    elif category == "health":
        parts.append("Clear health / wellness use case")
    elif category == "geo":
        parts.append("Localized utility or directory potential")
    else:
        parts.append("Brandable commercial name")

    if length <= 8:
        parts.append("short and memorable")
    elif length <= 10:
        parts.append("manageable length")
    else:
        parts.append("longer but still commercially usable")

    if tld == "com":
        parts.append(".com strengthens resale liquidity")
    elif tld in {"ai", "io"}:
        parts.append(f".{tld} fits modern tech usage")

    parts.append(f"Category fit: {cat_label}")
    parts.append(status_label)

    sentence = ". ".join(parts)
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def rdap_lookup(domain: str) -> Tuple[bool, Optional[bool], Optional[str]]:
    """
    Lightweight RDAP check.
    Returns:
      rdap_ok, registered_now, error
    """
    _, tld = split_domain(domain)
    if tld not in {"com", "net", "org"}:
        return False, None, "No RDAP server found for TLD"

    url = f"https://rdap.verisign.com/{tld}/v1/domain/{domain}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SohadotDropsBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                return True, True, None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, False, None
        return False, None, f"HTTP {e.code}"
    except Exception as e:
        return False, None, str(e)

    return False, None, "Unknown RDAP response"


def normalize_source(source: str) -> str:
    source = (source or "").strip()
    return source if source else "Unknown"


def parse_csv() -> List[Dict]:
    rows = []
    if not CSV_PATH.exists():
        return rows

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            domain = (raw.get("domain") or "").strip().lower()
            if not domain or "." not in domain:
                continue

            source = normalize_source(raw.get("source", "Unknown"))

            try:
                drop_date = (raw.get("drop_date") or "").strip()
                if not drop_date:
                    # default fallback
                    drop_date = (datetime.now(timezone.utc).date() + timedelta(days=3)).isoformat()
            except Exception:
                drop_date = (datetime.now(timezone.utc).date() + timedelta(days=3)).isoformat()

            rows.append({
                "domain": domain,
                "source": source,
                "drop_date": drop_date,
            })

    return rows


def score_row(domain: str, source: str, drop_date: str) -> Dict:
    sld, tld = split_domain(domain)
    words = slug_words(sld)
    category = detect_category(sld)
    cat_label = category_label(category)

    total = 0
    total += length_score(len(sld))
    total += pronounceability_score(sld)
    total += quality_word_score(words)
    total += TLD_WEIGHTS.get(tld, 6)
    total += source_score(source)
    total += CATEGORY_PRIORITY.get(category, 2) * 2

    if is_pure_alpha(sld):
        total += 8
    if has_hyphen_or_number(sld):
        total -= 10
    if len(sld) > 12:
        total -= 6

    rdap_ok, registered_now, rdap_error = rdap_lookup(domain)
    status_code, status_label = compute_status(rdap_ok, registered_now, drop_date)

    if rdap_ok and registered_now is False:
        total += 8
    elif rdap_ok and registered_now is True:
        total -= 2

    total = max(45, min(94, total))

    value_range, value_sort = estimate_value(total, category, tld, len(sld))
    urgency = urgency_from_date(drop_date)
    why = make_why(domain, category, len(sld), tld, status_label)

    return {
        "domain": domain,
        "source": source,
        "score": total,
        "score_class": score_class(total),
        "length": len(sld),
        "category": category,
        "category_label": cat_label,
        "drop_label": datetime.strptime(drop_date, "%Y-%m-%d").strftime("%b %-d") if not is_windows() else datetime.strptime(drop_date, "%Y-%m-%d").strftime("%b %d").replace(" 0", " "),
        "drop_sort": drop_date,
        "drop_date": drop_date,
        "urgency": urgency,
        "status_code": status_code,
        "status_label": status_label,
        "value_range": value_range,
        "value_sort": value_sort,
        "why": why,
        "rdap_ok": rdap_ok,
        "registered_now": registered_now,
        "rdap_error": rdap_error,
        "check_url": f"https://www.godaddy.com/domainsearch/find?checkAvail=1&domainToCheck={domain}",
    }


def is_windows() -> bool:
    import os
    return os.name == "nt"


def choose_featured(rows: List[Dict]) -> List[Dict]:
    if not rows:
        return []

    selected = []
    used_categories = set()

    sorted_rows = sorted(
        rows,
        key=lambda r: (
            r["score"],
            1 if r["status_code"] == "likely_available" else 0,
            1 if r["category"] in {"ai", "finance", "tech"} else 0,
            -r["length"],
            r["value_sort"],
        ),
        reverse=True,
    )

    for row in sorted_rows:
        if row["category"] not in used_categories:
            selected.append(row)
            used_categories.add(row["category"])
        if len(selected) == 3:
            break

    if len(selected) < 3:
        for row in sorted_rows:
            if row not in selected:
                selected.append(row)
            if len(selected) == 3:
                break

    featured = []
    for row in selected:
        featured.append({
            "badge": "Top Pick",
            "domain": row["domain"],
            "score": row["score"],
            "tld": "." + split_domain(row["domain"])[1],
            "length": row["length"],
            "category": row["category_label"],
            "drop_label": row["drop_label"],
            "urgency": row["urgency"],
            "why": row["why"],
            "value_range": row["value_range"],
            "check_url": row["check_url"],
            "status_label": row["status_label"],
        })
    return featured


def build_json(rows: List[Dict]) -> Dict:
    now = datetime.now(timezone.utc)
    next_monday = now + timedelta(days=(7 - now.weekday()) % 7 or 7)
    next_monday = next_monday.replace(hour=8, minute=0, second=0, microsecond=0)

    week_label = f"Curated Weekly Drops Watchlist — Week of {now.strftime('%b %-d, %Y')}" if not is_windows() else f"Curated Weekly Drops Watchlist — Week of {now.strftime('%b %d, %Y').replace(' 0', ' ')}"

    rows = sorted(rows, key=lambda r: (-r["score"], r["drop_sort"], r["domain"]))
    featured = choose_featured(rows)

    sources = sorted({row["source"] for row in rows})

    return {
        "week_label": week_label,
        "last_updated": now.isoformat().replace("+00:00", "Z"),
        "last_updated_human": now.strftime("%B %-d, %Y %H:%M UTC") if not is_windows() else now.strftime("%B %d, %Y %H:%M UTC").replace(" 0", " "),
        "next_update_label": "Next Monday refresh",
        "next_update_iso": next_monday.isoformat().replace("+00:00", "Z"),
        "curated_count": len(rows),
        "sources": sources,
        "page_mode": "weekly_watchlist",
        "criteria": [
            "Short, brandable, commercially plausible names preferred",
            "Quality TLDs prioritized (.com / .ai / .io / .co)",
            "Category fit used as a directional weighting, not absolute truth",
            "RDAP used where possible to distinguish watchlist vs likely-available names",
            "Comparable-sales style valuation shown as directional guidance only",
            "Featured picks selected for quality plus category diversity"
        ],
        "featured": featured,
        "domains": rows
    }


def main():
    candidates = parse_csv()
    scored = [score_row(r["domain"], r["source"], r["drop_date"]) for r in candidates]
    payload = build_json(scored)

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Updated {JSON_PATH} with {len(scored)} domains.")


if __name__ == "__main__":
    main()
