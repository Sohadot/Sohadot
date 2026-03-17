#!/usr/bin/env python3
import json
from datetime import datetime, timezone

ROOT_SEED = "data/keywords_seed.json"
OUTPUT_JSON = "data/keywords.json"

UTC = timezone.utc

CATEGORY_ORDER = {
    "AI": 1,
    "Finance": 2,
    "Finance / Crypto": 2,
    "Tech": 3,
    "Tech / AI": 3,
    "Health": 4,
    "Geo": 5,
    "Brand": 6
}


def now_utc():
    return datetime.now(UTC)


def first_day_next_month_8utc(dt):
    year = dt.year
    month = dt.month
    if month == 12:
        return datetime(year + 1, 1, 1, 8, 0, 0, tzinfo=UTC)
    return datetime(year, month + 1, 1, 8, 0, 0, tzinfo=UTC)


def month_label(dt):
    return f"Monthly Domain Intelligence — {dt.strftime('%B %Y')}"


def human_date(dt):
    return dt.strftime("%B %d, %Y %H:%M UTC")


def normalize_keyword_entry(item, rank):
    return {
        "rank": rank,
        "keyword": item.get("keyword", "Unnamed Keyword"),
        "category": item.get("category", "Brand"),
        "activity_level": item.get("activity_level", "Moderate"),
        "search_volume": item.get("search_volume", "Unknown"),
        "cpc_range": item.get("cpc_range", "Unknown"),
        "domain_logic": item.get("domain_logic", ""),
        "example_domains": item.get("example_domains", []),
        "investor_note": item.get("investor_note", ""),
        "developer_note": item.get("developer_note", ""),
        "score": int(item.get("score", 70)),
        "trend": item.get("trend", "Stable"),
        "priority_tlds": item.get("priority_tlds", [".com"])
    }


def normalize_sale_entry(item):
    return {
        "domain": item.get("domain", "Unknown.com"),
        "price": item.get("price", "N/A"),
        "category": item.get("category", "General"),
        "sale_month": item.get("sale_month", "Reference Sale"),
        "source": item.get("source", "Publicly reported"),
        "why_it_sold": item.get("why_it_sold", ""),
        "market_signal": item.get("market_signal", "")
    }


def sort_keywords(items):
    def sort_key(x):
        return (
            int(x.get("score", 0)),
            -CATEGORY_ORDER.get(x.get("category", "Brand"), 99),
            x.get("keyword", "")
        )
    return sorted(items, key=sort_key, reverse=True)


def build_market_insight(seed):
    return seed.get(
        "market_insight",
        "This month favors commercially usable themes with clear business logic over vague hype. The strongest naming signals come from categories where buyer intent, category relevance, and naming usability converge."
    )


def main():
    with open(ROOT_SEED, "r", encoding="utf-8") as f:
        seed = json.load(f)

    now = now_utc()
    next_update = first_day_next_month_8utc(now)

    raw_keywords = seed.get("keywords", [])
    raw_sales = seed.get("top_sales", [])

    sorted_keywords = sort_keywords(raw_keywords)
    keywords = [normalize_keyword_entry(item, idx + 1) for idx, item in enumerate(sorted_keywords[:10])]
    sales = [normalize_sale_entry(item) for item in raw_sales[:10]]

    payload = {
        "month_label": month_label(now),
        "last_updated": now.isoformat().replace("+00:00", "Z"),
        "last_updated_human": human_date(now),
        "next_update_label": "Next monthly refresh",
        "next_update_iso": next_update.isoformat().replace("+00:00", "Z"),
        "sources": seed.get("sources", []),
        "market_insight_title": seed.get("market_insight_title", "What the Market Is Signaling This Month"),
        "market_insight": build_market_insight(seed),
        "insight_bullets": seed.get("insight_bullets", []),
        "methodology": seed.get("methodology", []),
        "keywords": keywords,
        "top_sales": sales
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUTPUT_JSON} with {len(keywords)} keywords and {len(sales)} sales.")


if __name__ == "__main__":
    main()
