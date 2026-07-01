#!/usr/bin/env python3
"""Trust & Acquisition Readiness Audit for the Sohadot acquisition path.

Audits the complete path Home -> Portfolio / Category Artifacts / Category
Clusters -> Strategic Brief for broken links, cheap-marketplace language,
pricing-pressure flows, CTA routing, and sitemap/README currency.

This script does not add domain assets, expand the 50 Category Artifacts, or
change canonical meanings — it only reads the existing static pages and data
files and reports on them.

Usage: python3 scripts/audit_acquisition_readiness.py
Exits 0 and prints PASS if every check passes, otherwise prints each
violation prefixed "FAIL:" with the offending file and exits 1.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent

CORE_HTML_FILES = [
    "index.html",
    "portfolio.html",
    "category-artifacts.html",
    "category-clusters.html",
    "strategic-brief.html",
]

SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
README_PATH = REPO_ROOT / "README.md"
ASSET_MEANINGS_PATH = REPO_ROOT / "data" / "asset-meanings.json"
CATEGORY_CLUSTERS_PATH = REPO_ROOT / "data" / "category-clusters.json"

REQUIRED_SITEMAP_PATHS = [
    "/category-artifacts.html",
    "/category-clusters.html",
    "/strategic-brief.html",
]

REQUIRED_README_MENTIONS = [
    "Category Artifact Meaning Layer",
    "Category Cluster & Buyer Logic Layer",
    "Strategic Brief Request Layer",
    "Trust & Acquisition Readiness Audit",
]

# Fail the audit if any of these appear as primary CTA / sales language,
# unless the occurrence is an explicit negation ("no buy-now language",
# "not a checkout flow").
FORBIDDEN_PHRASES = [
    "buy now",
    "checkout",
    "cart",
    "add to cart",
    "instant purchase",
    "lowest price",
    "discount",
    "clearance",
    "cheap domain",
    "bargain",
    "fire sale",
]

NEGATION_RE = re.compile(r"\b(no|not|never|without)\b", re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
ID_RE = re.compile(r'\bid="([^"]+)"')
HREF_RE = re.compile(r'href="([^"]+)"')
VIEWPORT_RE = re.compile(r'<meta[^>]+name=["\']viewport["\']', re.IGNORECASE)


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def strip_scripts(html):
    return SCRIPT_RE.sub("", html)


def strip_scripts_and_styles(html):
    return STYLE_RE.sub("", SCRIPT_RE.sub("", html))


def load_html(name):
    path = REPO_ROOT / name
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def extract_ids(html):
    return set(ID_RE.findall(html))


def extract_hrefs(html):
    """hrefs from <a>/<link> tags, excluding <script> contents (JSON-LD)."""
    return HREF_RE.findall(strip_scripts(html))


def is_negated(text, match_start):
    window_start = max(0, match_start - 40)
    context = text[window_start:match_start]
    for punct in (".", "!", "?", "\n"):
        pos = context.rfind(punct)
        if pos != -1:
            context = context[pos + 1:]
    return bool(NEGATION_RE.search(context))


def check_forbidden_language(name, html, errors):
    lowered = html.lower()
    for phrase in FORBIDDEN_PHRASES:
        start = 0
        while True:
            idx = lowered.find(phrase, start)
            if idx == -1:
                break
            if not is_negated(html, idx):
                snippet = html[max(0, idx - 30):idx + len(phrase) + 10].replace("\n", " ")
                errors.append(
                    f"{name}: forbidden cheap-marketplace phrase '{phrase}' used "
                    f"without negation near: ...{snippet.strip()}..."
                )
            start = idx + len(phrase)


def load_asset_domains():
    if not ASSET_MEANINGS_PATH.exists():
        return set()
    try:
        raw = json.loads(ASSET_MEANINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {
        a.get("domain", "").strip().lower()
        for a in raw.get("assets", [])
        if isinstance(a, dict) and a.get("domain")
    }


def load_cluster_names():
    if not CATEGORY_CLUSTERS_PATH.exists():
        return set()
    try:
        raw = json.loads(CATEGORY_CLUSTERS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {
        c.get("name", "").strip()
        for c in raw.get("clusters", [])
        if isinstance(c, dict) and c.get("name")
    }


def check_links_and_anchors(name, html, page_ids_cache, asset_domains, cluster_names, errors):
    hrefs = extract_hrefs(html)

    for href in hrefs:
        scheme = urlsplit(href).scheme

        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        if scheme == "http":
            errors.append(f"{name}: external link uses http instead of https: '{href}'")
            continue

        if scheme == "https" or href.startswith("//"):
            continue  # external https link — exempt from local resolution

        # Same-page anchor
        if href.startswith("#"):
            fragment = href[1:]
            if fragment and fragment not in page_ids_cache.get(name, set()):
                errors.append(f"{name}: same-page anchor '{href}' has no matching id=\"{fragment}\"")
            continue

        parsed = urlsplit(href)
        path = parsed.path

        if path in ("", "/"):
            target_ids = set()
            target_name = None
        else:
            local_rel = path.lstrip("/")
            local_path = REPO_ROOT / local_rel
            if not local_path.exists():
                errors.append(f"{name}: broken local link '{href}' -> file not found: {local_rel}")
                continue
            target_name = local_rel
            target_ids = page_ids_cache.get(target_name)
            if target_ids is None and local_path.suffix == ".html":
                target_html = local_path.read_text(encoding="utf-8")
                target_ids = extract_ids(target_html)
                page_ids_cache[target_name] = target_ids

        if parsed.fragment:
            if target_ids is not None and parsed.fragment not in target_ids:
                errors.append(
                    f"{name}: link '{href}' anchors to #{parsed.fragment} which does not exist "
                    f"in {target_name or path}"
                )

        if parsed.query and (path.endswith("strategic-brief.html")):
            params = parse_qs(parsed.query)
            if "asset" in params:
                asset_value = unquote(params["asset"][0]).strip().lower()
                if asset_domains and asset_value not in asset_domains:
                    errors.append(
                        f"{name}: link '{href}' references asset '{asset_value}' not found in "
                        f"{ASSET_MEANINGS_PATH.relative_to(REPO_ROOT)}"
                    )
            if "cluster" in params:
                cluster_value = unquote(params["cluster"][0]).strip()
                if cluster_names and cluster_value not in cluster_names:
                    errors.append(
                        f"{name}: link '{href}' references cluster '{cluster_value}' not found in "
                        f"{CATEGORY_CLUSTERS_PATH.relative_to(REPO_ROOT)}"
                    )


ARTICLE_RE = re.compile(
    r'<article class="artifact" id="([a-z0-9-]+)".*?</article>', re.DOTALL
)
CLUSTER_ARTICLE_RE = re.compile(
    r'<article class="cluster" id="([a-z0-9-]+)".*?</article>', re.DOTALL
)


def check_artifact_ctas(html, errors):
    articles = ARTICLE_RE.findall(html)
    if len(articles) != 50:
        errors.append(
            f"category-artifacts.html: expected 50 artifact articles, found {len(articles)} "
            f"(this sprint must not expand or shrink the 50 Category Artifacts)"
        )

    for match in ARTICLE_RE.finditer(html):
        artifact_id = match.group(1)
        block = match.group(0)
        cta_matches = re.findall(
            r'href="/strategic-brief\.html\?asset=([^&"]+)&type=[^"]+"', block
        )
        if len(cta_matches) != 1:
            errors.append(
                f"category-artifacts.html: artifact #{artifact_id} must have exactly one "
                f"'Request Brief for This Asset' CTA to strategic-brief.html, found {len(cta_matches)}"
            )
            continue
        asset_slug = unquote(cta_matches[0]).strip().lower().replace(".", "-")
        if asset_slug != artifact_id:
            errors.append(
                f"category-artifacts.html: artifact #{artifact_id} CTA asset param "
                f"'{cta_matches[0]}' does not match its own article id"
            )


def check_cluster_ctas(html, errors):
    clusters = CLUSTER_ARTICLE_RE.findall(html)
    if len(clusters) != 8:
        errors.append(
            f"category-clusters.html: expected 8 cluster articles, found {len(clusters)}"
        )

    for match in CLUSTER_ARTICLE_RE.finditer(html):
        cluster_id = match.group(1)
        block = match.group(0)
        cta_matches = re.findall(
            r'href="/strategic-brief\.html\?cluster=[^&"]+&type=[^"]+"', block
        )
        if len(cta_matches) != 1:
            errors.append(
                f"category-clusters.html: cluster #{cluster_id} must have exactly one "
                f"'Request Brief for This Cluster' CTA to strategic-brief.html, found {len(cta_matches)}"
            )


def check_cta_paths(pages, errors):
    index_hrefs = extract_hrefs(pages["index.html"])
    for required in ("portfolio.html", "category-artifacts.html", "category-clusters.html", "strategic-brief.html"):
        if not any(urlsplit(h).path.lstrip("/") == required for h in index_hrefs):
            errors.append(f"index.html: missing a link to /{required} (Home must expose the acquisition path)")

    portfolio_hrefs = extract_hrefs(pages["portfolio.html"])
    if not any(urlsplit(h).path.endswith("strategic-brief.html") for h in portfolio_hrefs):
        errors.append("portfolio.html: missing a Strategic Brief CTA")

    check_artifact_ctas(pages["category-artifacts.html"], errors)
    check_cluster_ctas(pages["category-clusters.html"], errors)


def check_pricing_pressure(pages, errors):
    brief_html = pages["strategic-brief.html"]
    if re.search(r"<table\b", brief_html, re.IGNORECASE):
        errors.append("strategic-brief.html: contains a <table> element — no pricing table is allowed here")

    portfolio_html = pages["portfolio.html"]
    urgency_terms = ["limited time", "act now", "ends soon", "hurry", "only .* left", "selling fast"]
    for term in urgency_terms:
        if re.search(term, portfolio_html, re.IGNORECASE):
            errors.append(f"portfolio.html: contains pricing-urgency language matching '{term}'")


def check_strategic_distinction(pages, errors):
    markers = {
        "index.html": ["domain intelligence", "platform"],
        "portfolio.html": ["category-artifacts.html", "category-clusters.html"],
        "category-artifacts.html": ["canonical meaning", "buyer logic", "conceptual thesis"],
        "category-clusters.html": ["strategic thesis", "acquisition rationale", "buyer logic"],
        "strategic-brief.html": ["not a generic contact form", "acquisition-intent", "acquisition intent"],
    }
    for name, needles in markers.items():
        html_lower = pages[name].lower()
        if not any(needle in html_lower for needle in needles):
            errors.append(
                f"{name}: does not clearly distinguish Sohadot from a generic domain listing "
                f"(expected one of {needles})"
            )


def check_mobile_readability(pages, errors):
    for name, html in pages.items():
        if not VIEWPORT_RE.search(html):
            errors.append(f"{name}: missing responsive <meta name=\"viewport\"> tag")
        if "@media" not in html:
            errors.append(f"{name}: no @media rules found — page may not adapt to mobile widths")
        if "box-sizing:border-box" not in html.replace(" ", ""):
            errors.append(f"{name}: missing 'box-sizing:border-box' reset, which can cause mobile overflow")
        if re.search(r"(?<!max-)(?<!min-)\bwidth:\s*\d{4,}px", html):
            errors.append(f"{name}: fixed pixel width of 1000px+ found — check for horizontal overflow on mobile")


def check_sitemap(errors):
    if not SITEMAP_PATH.exists():
        errors.append(f"sitemap.xml not found at {SITEMAP_PATH}")
        return
    sitemap_text = SITEMAP_PATH.read_text(encoding="utf-8")
    for required_path in REQUIRED_SITEMAP_PATHS:
        if required_path not in sitemap_text:
            errors.append(f"sitemap.xml: missing required entry '{required_path}'")


def check_readme(errors):
    if not README_PATH.exists():
        errors.append(f"README.md not found at {README_PATH}")
        return
    readme_text = README_PATH.read_text(encoding="utf-8")
    for mention in REQUIRED_README_MENTIONS:
        if mention not in readme_text:
            errors.append(f"README.md: missing required mention '{mention}'")


def main():
    errors = []
    pages = {}
    for name in CORE_HTML_FILES:
        html = load_html(name)
        if html is None:
            errors.append(f"{name}: file not found")
            continue
        pages[name] = html

    if len(pages) != len(CORE_HTML_FILES):
        fail(errors)
        return

    page_ids_cache = {name: extract_ids(html) for name, html in pages.items()}
    asset_domains = load_asset_domains()
    cluster_names = load_cluster_names()

    for name, html in pages.items():
        check_links_and_anchors(name, html, page_ids_cache, asset_domains, cluster_names, errors)
        check_forbidden_language(name, strip_scripts_and_styles(html), errors)

    check_cta_paths(pages, errors)
    check_pricing_pressure(pages, errors)
    check_strategic_distinction(pages, errors)
    check_mobile_readability(pages, errors)
    check_sitemap(errors)
    check_readme(errors)

    if errors:
        fail(errors)
        return

    print(
        f"PASS: trust & acquisition readiness audit clean across {len(CORE_HTML_FILES)} core pages, "
        f"sitemap.xml, and README.md"
    )


if __name__ == "__main__":
    main()
