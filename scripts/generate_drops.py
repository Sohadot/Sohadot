import csv
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_CSV = DATA_DIR / "drops_candidates.csv"
OUTPUT_JSON = DATA_DIR / "drops.json"
IANA_RDAP_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"

QUALITY_TLDS = {
    "com": 30,
    "ai": 26,
    "io": 22,
    "co": 18,
    "org": 14,
    "net": 12,
    "app": 14,
    "dev": 12,
}

CATEGORY_KEYWORDS = {
    "ai": ["ai", "agent", "agents", "neural", "model", "gpt", "vision", "prompt"],
    "finance": ["cash", "pay", "bank", "fund", "capital", "coin", "wallet", "wealth", "credit"],
    "health": ["health", "mind", "care", "therapy", "med", "clinic"],
    "geo": ["city", "map", "dubai", "london", "miami", "paris", "tokyo", "austin", "detroit"],
    "tech": ["stack", "scan", "cloud", "data", "token", "api", "dev", "secure"],
    "brand": [],
}

FEATURED_COUNT = 3


def fetch_json(url: str):
    req = Request(
        url,
        headers={
            "User-Agent": "SohadotDropsBot/1.0 (+https://sohadot.com)"
        }
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_iana_bootstrap():
    return fetch_json(IANA_RDAP_BOOTSTRAP)


def get_tld(domain: str) -> str:
    return domain.lower().split(".")[-1]


def get_sld(domain: str) -> str:
    parts = domain.lower().split(".")
    return parts[0] if parts else domain.lower()


def find_rdap_base(bootstrap: dict, domain: str) -> str | None:
    tld = get_tld(domain)
    for service in bootstrap.get("services", []):
        tlds, urls = service
        if tld in tlds and urls:
            return urls[0].rstrip("/")
    return None


def rdap_lookup(bootstrap: dict, domain: str) -> dict:
    """
    Returns:
      {
        "rdap_ok": bool,
        "registered": bool | None,
        "status": list[str],
        "events": list[dict],
        "error": str | None
      }
    """
    rdap_base = find_rdap_base(bootstrap, domain)
    if not rdap_base:
        return {
            "rdap_ok": False,
            "registered": None,
            "status": [],
            "events": [],
            "error": "No RDAP server found for TLD",
        }

    url = f"{rdap_base}/domain/{domain}"
    req = Request(
        url,
        headers={"User-Agent": "SohadotDropsBot/1.0 (+https://sohadot.com)"}
    )

    try:
        with urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return {
                "rdap_ok": True,
                "registered": True,
                "status": payload.get("status", []),
                "events": payload.get("events", []),
                "error": None,
            }
    except HTTPError as e:
        # 404 often means not found / not registered, but behavior varies by registry
        if e.code == 404:
            return {
                "rdap_ok": True,
                "registered": False,
                "status": [],
                "events": [],
                "error": None,
            }
        return {
            "rdap_ok": False,
            "registered": None,
            "status": [],
            "events": [],
            "error": f"HTTP {e.code}",
        }
    except URLError as e:
        return {
            "rdap_ok": False,
            "registered": None,
            "status": [],
            "events": [],
            "error": str(e),
        }
    except Exception as e:
        return {
            "rdap_ok": False,
            "registered": None,
            "status": [],
            "events": [],
            "error": str(e),
        }


def infer_category(domain: str, category_hint: str = "") -> tuple[str, str]:
    hint = (category_hint or "").strip().lower()
    if hint in CATEGORY_KEYWORDS:
        return hint, category_label(hint)

    sld = get_sld(domain)
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in sld:
                return cat, category_label(cat)

    return "brand", category_label("brand")


def category_label(cat: str) -> str:
    return {
        "ai": "AI",
        "finance": "Finance / Crypto",
        "health": "Health",
        "geo": "Geo",
        "tech": "Tech / SaaS",
        "brand": "Brand",
    }.get(cat, "Brand")


def score_domain(domain: str, category_hint: str = "") -> tuple[int, dict]:
    sld = get_sld(domain)
    tld = get_tld(domain)

    score = 0
    reasons = []

    # TLD
    tld_score = QUALITY_TLDS.get(tld, 8)
    score += tld_score
    reasons.append(f"TLD quality: +{tld_score}")

    # Length
    length = len(sld.replace("-", ""))
    if length <= 4:
        score += 28
        reasons.append("Ultra-short structure: +28")
    elif length <= 6:
        score += 24
        reasons.append("Short structure: +24")
    elif length <= 8:
        score += 20
        reasons.append("Compact structure: +20")
    elif length <= 12:
        score += 14
        reasons.append("Usable length: +14")
    else:
        score += 6
        reasons.append("Longer length: +6")

    # Character quality
    if re.fullmatch(r"[a-z]+", sld):
        score += 14
        reasons.append("Pure alpha: +14")
    elif "-" not in sld and not re.search(r"\d", sld):
        score += 10
        reasons.append("Clean structure: +10")
    else:
        score -= 8
        reasons.append("Hyphen/number penalty: -8")

    # Category relevance
    cat, _ = infer_category(domain, category_hint)
    if cat == "ai":
        score += 14
        reasons.append("AI relevance: +14")
    elif cat == "finance":
        score += 12
        reasons.append("Finance relevance: +12")
    elif cat == "tech":
        score += 11
        reasons.append("Tech relevance: +11")
    elif cat == "health":
        score += 10
        reasons.append("Health relevance: +10")
    elif cat == "geo":
        score += 8
        reasons.append("Geo relevance: +8")
    else:
        score += 6
        reasons.append("Brandable relevance: +6")

    # Word quality bonus
    if re.search(r"(logic|scan|pulse|genie|folio|factor|health|flare|stack|mind|token)", sld):
        score += 6
        reasons.append("Strong lexical signal: +6")

    # Penalty for awkward length
    if length > 14:
        score -= 10
        reasons.append("Long name penalty: -10")

    score = max(35, min(95, score))
    return score, {"length": length, "reasons": reasons}


def score_to_class(score: int) -> str:
    if score >= 85:
        return "high"
    if score >= 70:
        return "mid"
    return "low"


def estimate_value(score: int, tld: str, category: str) -> tuple[str, int]:
    base = 200

    if tld == "com":
        base += 350
    elif tld == "ai":
        base += 300
    elif tld == "io":
        base += 220
    elif tld == "co":
        base += 140

    if category == "ai":
        base += 220
    elif category == "finance":
        base += 180
    elif category == "tech":
        base += 160
    elif category == "health":
        base += 120
    elif category == "geo":
        base += 80
    else:
        base += 100

    midpoint = int(base * (score / 70))
    low = int(midpoint * 0.65)
    high = int(midpoint * 1.45)

    # round for cleaner display
    def round_n(x):
        if x >= 1000:
            return int(round(x / 100.0) * 100)
        return int(round(x / 50.0) * 50)

    low = round_n(low)
    high = round_n(high)
    return f"${low:,}–{high:,}", high


def drop_label(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    return dt.strftime("%b %-d") if hasattr(dt, "strftime") else dt.isoformat()


def week_label_from_dates(rows: list[dict]) -> str:
    dates = sorted(datetime.strptime(r["drop_date"], "%Y-%m-%d").date() for r in rows)
    first = dates[0]
    return f"Curated Weekly Picks — Week of {first.strftime('%b')} {first.day}, {first.year}"


def next_monday_8utc(from_dt=None) -> datetime:
    now = from_dt or datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    target = (now + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0, microsecond=0)
    return target


def build_featured(domains: list[dict]) -> list[dict]:
    top = sorted(domains, key=lambda x: (x["score"], x["value_sort"]), reverse=True)[:FEATURED_COUNT]
    featured = []
    for item in top:
        featured.append({
            "badge": "Top Pick",
            "domain": item["domain"],
            "score": item["score"],
            "tld": f".{get_tld(item['domain'])}",
            "length": item["length"],
            "category": item["category_label"],
            "drop_label": item["drop_label"],
            "urgency": item["urgency"],
            "why": item["why"],
            "value_range": item["value_range"],
            "check_url": item["check_url"],
        })
    return featured


def make_check_url(domain: str) -> str:
    return f"https://www.godaddy.com/domainsearch/find?checkAvail=1&domainToCheck={domain}"


def build_why(domain: str, category_label: str, notes: str, rdap_data: dict) -> str:
    pieces = []

    if notes:
        pieces.append(notes.strip().rstrip("."))

    pieces.append(f"Category fit: {category_label}.")

    if rdap_data["rdap_ok"] and rdap_data["registered"] is False:
        pieces.append("RDAP lookup did not find an active registration at generation time.")
    elif rdap_data["rdap_ok"] and rdap_data["registered"] is True:
        pieces.append("RDAP confirms the name is still currently registered or in registry state.")
    elif rdap_data["error"]:
        pieces.append("RDAP status could not be fully confirmed during this run.")

    return " ".join(pieces)


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_CSV}")

    bootstrap = load_iana_bootstrap()

    rows = []
    with INPUT_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row["domain"].strip().lower()
            if not domain or "." not in domain:
                continue

            category, category_lbl = infer_category(domain, row.get("category_hint", ""))
            score, score_meta = score_domain(domain, row.get("category_hint", ""))
            value_range, value_sort = estimate_value(score, get_tld(domain), category)
            rdap_data = rdap_lookup(bootstrap, domain)

            drop_date_iso = row["drop_date"].strip()
            dt = datetime.strptime(drop_date_iso, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            days_left = (dt - today).days

            if days_left <= 2:
                urgency = "urgent"
            elif days_left <= 5:
                urgency = "soon"
            else:
                urgency = "normal"

            why = build_why(
                domain=domain,
                category_label=category_lbl,
                notes=row.get("notes", ""),
                rdap_data=rdap_data,
            )

            rows.append({
                "domain": domain,
                "source": row.get("source", "").strip(),
                "score": score,
                "score_class": score_to_class(score),
                "length": score_meta["length"],
                "category": category,
                "category_label": category_lbl,
                "drop_label": dt.strftime("%b ") + str(dt.day),
                "drop_sort": drop_date_iso,
                "drop_date": drop_date_iso,
                "urgency": urgency,
                "value_range": value_range,
                "value_sort": value_sort,
                "why": why,
                "rdap_ok": rdap_data["rdap_ok"],
                "registered_now": rdap_data["registered"],
                "rdap_error": rdap_data["error"],
                "check_url": make_check_url(domain),
            })

    rows.sort(key=lambda x: (x["score"], x["value_sort"]), reverse=True)

    next_update = next_monday_8utc()
    output = {
        "week_label": week_label_from_dates(rows) if rows else "Curated Weekly Picks",
        "last_updated": datetime.now(timezone.utc).strftime("%B %-d, %Y"),
        "next_update_label": "Next Monday refresh",
        "next_update_iso": next_update.isoformat().replace("+00:00", "Z"),
        "curated_count": len(rows),
        "sources": sorted(list({r["source"] for r in rows if r["source"]})),
        "criteria": [
            "Length generally kept concise",
            "Pure alpha preferred over hyphens and numbers",
            "Quality TLDs prioritized (.com / .ai / .io / .co)",
            "Brandability and memorability considered",
            "Obvious trademark issues avoided where possible",
            "Comparable public sales used as directional reference",
            "RDAP checked when available for current registration state",
            "Only names with plausible resale rationale included"
        ],
        "featured": build_featured(rows),
        "domains": rows
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_JSON} with {len(rows)} domains.")


if __name__ == "__main__":
    main()
