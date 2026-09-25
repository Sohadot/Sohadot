#!/usr/bin/env python3
"""Validate bundle-only sale designations across every published surface.

Source of truth: data/bundle-only-assets.json. Every domain listed there is
offered exclusively as part of its complete set, so no published HTML, JSON or
JavaScript may carry an individual acquisition route for it. This validator
fails if it finds any of:

  - a strategic-brief link naming a bundle-only domain, e.g.
    asset=<domain>&type=single-asset-acquisition (raw or URL-encoded)
  - a per-domain WhatsApp, mailto or sms acquisition message (a message that
    names some, but not all, of the set's domains)
  - a per-domain purchase or inquiry CTA (an <a> whose text or href names a
    bundle-only domain and uses acquisition language, other than the full set)
  - a machine-readable strategic_brief_url for a bundle-only domain, or an
    inventory record missing its sale_mode / bundle_id / bundle_url
  - a Category Artifact block for a bundle-only domain linking anywhere but
    its complete-set page
  - a portfolio card for a bundle-only domain without a set-level CTA, or a
    renderCard() that could emit a per-domain WhatsApp/mailto/brief link for it
  - drift between the registry and the bundle page (domains, canonical URL,
    advertised price), strategic-brief.js, or the strategic-brief options

Usage:
  python3 scripts/validate_bundle_only.py              # validate the repository
  python3 scripts/validate_bundle_only.py --self-test  # prove the detectors fire
Exits 0 and prints PASS if valid, otherwise prints each violation prefixed
"FAIL:" and exits 1.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote_plus

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "data" / "bundle-only-assets.json"
INVENTORY_PATH = REPO_ROOT / "data" / "conceptual-inventory.json"
BRIEF_OPTIONS_PATH = REPO_ROOT / "data" / "brief-request-options.json"
PORTFOLIO_PATH = REPO_ROOT / "portfolio.html"
CATEGORY_ARTIFACTS_PATH = REPO_ROOT / "category-artifacts.html"
STRATEGIC_BRIEF_PATH = REPO_ROOT / "strategic-brief.html"
STRATEGIC_BRIEF_JS_PATH = REPO_ROOT / "js" / "strategic-brief.js"

# Raw lexical datasets are dictionaries, not published commercial copy.
EXCLUDED_DATA_FILES = {
    "english_words.json", "extended_words.json", "multilingual_words.json",
    "rare_words.json", "lexical_words.json", "names.json", "industry_map.json",
}

URL_RE = re.compile(
    # WhatsApp/sms message text may contain apostrophes ("I'm interested"), so
    # those URLs run until whitespace, a double quote, a tag or a backtick.
    r"""(?:https?://(?:wa\.me|api\.whatsapp\.com|web\.whatsapp\.com)/|sms:)[^\s"<>`]*"""
    r"""|(?:mailto:|[^\s"'<>`]*strategic-brief\.html)[^\s"'<>`]*""",
    re.IGNORECASE,
)
ASSET_PARAM_RE = re.compile(r"[?&](?:amp;)?(?:asset|interest)=([^&\"'\s<>`#]+)", re.IGNORECASE)
ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r"""href=["']([^"']*)["']""", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
COMMERCIAL_RE = re.compile(
    r"\b(inquire|inquiry|acquire|acquisition|buy|purchase|offer|brief|order|escrow|"
    r"make an offer|request price)\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"(?:USD|US\$|\$)\s*(?:&nbsp;|\s|<[^>]+>)*\d[\d,.]*", re.IGNORECASE)


def load_registry():
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return raw.get("bundles", [])


def domain_index(bundles):
    """lowercased domain -> bundle."""
    index = {}
    for bundle in bundles:
        for domain in bundle.get("domains", []):
            index[domain.strip().lower()] = bundle
    return index


def names_in(text, index):
    """Bundle-only domains named in text (case-insensitive, whole-token)."""
    lowered = text.lower()
    found = set()
    for domain in index:
        stem = re.escape(domain[: -len(".com")] if domain.endswith(".com") else domain)
        if re.search(r"(?<![a-z0-9])" + stem + r"(?:\.com)?(?![a-z0-9])", lowered):
            found.add(domain)
    return found


def names_whole_set(named, index):
    """True if every named domain's full bundle is named (a set-level message)."""
    for domain in named:
        members = {d.lower() for d in index[domain]["domains"]}
        if not members <= named:
            return False
    return True


# ── Detectors (pure functions over text, used by the scan and the self-test) ──

def detect_individual_routes(label, text, index):
    errors = []
    decoded_text = unquote_plus(text.replace("&amp;", "&"))

    for match in ASSET_PARAM_RE.finditer(text):
        value = unquote_plus(match.group(1))
        named = names_in(value, index)
        if named:
            window = decoded_text[max(0, match.start() - 200):match.end() + 200]
            kind = "single-asset-acquisition" if "single-asset-acquisition" in window else "strategic-brief"
            errors.append(
                f"{label}: individual {kind} route for bundle-only {sorted(named)} "
                f"('{match.group(0)[:90]}')"
            )

    for match in URL_RE.finditer(text):
        url = match.group(0)
        decoded = unquote_plus(url.replace("&amp;", "&"))
        named = names_in(decoded, index)
        if not named:
            continue
        if "strategic-brief" in decoded.lower():
            if not ASSET_PARAM_RE.search(url):  # already reported above
                errors.append(f"{label}: strategic-brief link names bundle-only {sorted(named)} ('{url[:90]}')")
        elif not names_whole_set(named, index):
            errors.append(
                f"{label}: per-domain WhatsApp/mailto/sms message for bundle-only {sorted(named)} "
                f"('{url[:90]}')"
            )
    return errors


def detect_per_domain_ctas(label, html, index):
    errors = []
    for match in ANCHOR_RE.finditer(html):
        attrs, inner = match.group(1), match.group(2)
        href_match = HREF_RE.search(attrs)
        href = href_match.group(1) if href_match else ""
        text = " ".join(TAG_RE.sub(" ", inner).split())
        named = names_in(text + " " + unquote_plus(href.replace("&amp;", "&")), index)
        if not named or names_whole_set(named, index):
            continue
        bundle_urls = {index[d]["bundle_url"] for d in named}
        if href in bundle_urls:
            continue  # a set-level CTA for the domain's own bundle
        if COMMERCIAL_RE.search(text):
            errors.append(f"{label}: per-domain acquisition CTA for bundle-only {sorted(named)}: '{text[:80]}' -> '{href[:80]}'")
    return errors


def detect_json_brief_urls(label, data, index, path="$"):
    errors = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "strategic_brief_url" and isinstance(value, str) and names_in(unquote_plus(value), index):
                errors.append(f"{label}: machine-readable strategic_brief_url for bundle-only domain at {path}.{key} ('{value}')")
            errors.extend(detect_json_brief_urls(label, value, index, f"{path}.{key}"))
        # A record describing a bundle-only domain must not carry any brief URL.
        domain = data.get("domain")
        if isinstance(domain, str) and domain.strip().lower() in index and data.get("strategic_brief_url"):
            if not names_in(unquote_plus(str(data["strategic_brief_url"])), index):
                errors.append(f"{label}: bundle-only '{domain}' at {path} carries strategic_brief_url '{data['strategic_brief_url']}'")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            errors.extend(detect_json_brief_urls(label, item, index, f"{path}[{i}]"))
    return errors


# ── Repository checks ────────────────────────────────────────────────────────

def published_files():
    files = []
    for path in sorted(REPO_ROOT.rglob("*.html")):
        if ".git" not in path.relative_to(REPO_ROOT).parts:
            files.append(path)
    for path in sorted((REPO_ROOT / "data").glob("*.json")):
        if path.name not in EXCLUDED_DATA_FILES:
            files.append(path)
    files.extend(sorted((REPO_ROOT / "js").glob("*.js")))
    for name in ("llms.txt", "sitemap.xml"):
        if (REPO_ROOT / name).exists():
            files.append(REPO_ROOT / name)
    return files


def check_registry(bundles, errors):
    portfolio = PORTFOLIO_PATH.read_text(encoding="utf-8").lower()
    seen = set()
    for bundle in bundles:
        bid = bundle.get("bundle_id", "?")
        for field in ("bundle_id", "name", "sale_mode", "bundle_url", "canonical_url", "public_price", "domains"):
            if not bundle.get(field):
                errors.append(f"bundle-only-assets.json: bundle '{bid}' missing '{field}'")
        if bundle.get("sale_mode") != "bundle-only":
            errors.append(f"bundle-only-assets.json: bundle '{bid}' sale_mode must be 'bundle-only'")
        domains = bundle.get("domains", [])
        if len(domains) < 2:
            errors.append(f"bundle-only-assets.json: bundle '{bid}' must contain at least two domains")
        for domain in domains:
            key = domain.lower()
            if key in seen:
                errors.append(f"bundle-only-assets.json: '{domain}' is listed in more than one bundle")
            seen.add(key)
            if f'{{domain:"{key}"' not in portfolio:
                errors.append(f"bundle-only-assets.json: '{domain}' is not in the portfolio.html inventory")
        for domain in bundle.get("bundle_context", {}):
            if domain not in domains:
                errors.append(f"bundle-only-assets.json: bundle_context names '{domain}', which is not in bundle '{bid}'")


def check_bundle_page(bundle, errors):
    page = REPO_ROOT / bundle["bundle_url"].strip("/") / "index.html"
    rel = page.relative_to(REPO_ROOT)
    if not page.exists():
        errors.append(f"{bundle['bundle_id']}: bundle page {rel} not found")
        return
    html = page.read_text(encoding="utf-8")
    if f'<link rel="canonical" href="{bundle["canonical_url"]}"/>' not in html:
        errors.append(f"{rel}: canonical URL is not {bundle['canonical_url']}")

    item_names = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        data = json.loads(block)
        main = data.get("mainEntity") or {}
        if main.get("@type") == "ItemList":
            item_names = [item.get("name") for item in main.get("itemListElement", [])]
    if sorted(item_names) != sorted(bundle["domains"]):
        errors.append(f"{rel}: ItemList {item_names} does not match bundle domains {bundle['domains']}")

    visible = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    expected = re.sub(r"\D", "", bundle["public_price"])
    for match in PRICE_RE.finditer(visible):
        if re.sub(r"\D", "", TAG_RE.sub("", match.group(0))) != expected:
            errors.append(f"{rel}: advertised price '{match.group(0)}' differs from {bundle['public_price']}")
    for match in PRICE_RE.finditer(unquote_plus(html)):
        if re.sub(r"\D", "", TAG_RE.sub("", match.group(0))) != expected:
            errors.append(f"{rel}: price '{match.group(0)}' in markup/links differs from {bundle['public_price']}")
    if re.search(r"strategic-brief\.html\?[^\"']*(asset|type)=", html):
        errors.append(f"{rel}: bundle page must not link to a strategic-brief acquisition route")


def check_inventory(index, errors):
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    found = set()
    for record in inventory.get("records", []):
        key = record.get("domain", "").strip().lower()
        if key not in index:
            continue
        found.add(key)
        bundle = index[key]
        for field in ("sale_mode", "bundle_id", "bundle_url"):
            if record.get(field) != bundle[field]:
                errors.append(f"conceptual-inventory.json: '{record['domain']}' {field}={record.get(field)!r}, expected {bundle[field]!r}")
        if record.get("strategic_brief_url") is not None:
            errors.append(f"conceptual-inventory.json: '{record['domain']}' must have strategic_brief_url null (bundle-only)")
        if record.get("canonical_meaning") and record.get("bundle_context") == record.get("canonical_meaning"):
            errors.append(f"conceptual-inventory.json: '{record['domain']}' bundle_context was written into canonical_meaning")
    for key in set(index) - found:
        errors.append(f"conceptual-inventory.json: bundle-only domain '{key}' has no record")


def check_category_artifacts(index, errors):
    html = CATEGORY_ARTIFACTS_PATH.read_text(encoding="utf-8")
    for domain, bundle in index.items():
        artifact_id = domain.replace(".", "-")
        match = re.search(r'<article class="artifact" id="' + re.escape(artifact_id) + r'".*?</article>', html, re.DOTALL)
        if not match:
            continue  # not a Category Artifact
        hrefs = HREF_RE.findall(match.group(0))
        outbound = [h for h in hrefs if not h.startswith("#")]
        if outbound != [bundle["bundle_url"]]:
            errors.append(
                f"category-artifacts.html: #{artifact_id} must link only to {bundle['bundle_url']} "
                f"(found {outbound})"
            )


def check_portfolio(index, errors):
    html = PORTFOLIO_PATH.read_text(encoding="utf-8")
    for domain, bundle in index.items():
        match = re.search(r'\{domain:"' + re.escape(domain) + r'"[^\n]*\}', html)
        if not match:
            errors.append(f"portfolio.html: no DOMAINS entry for bundle-only '{domain}'")
            continue
        entry = match.group(0)
        if f'bundle:"{bundle["bundle_url"]}"' not in entry:
            errors.append(f"portfolio.html: '{domain}' entry must declare bundle:\"{bundle['bundle_url']}\"")
        if re.search(r'\b(page|live):"', entry):
            errors.append(f"portfolio.html: '{domain}' entry must not declare a per-domain page/live link")

    render = re.search(r"function renderCard\(d\) \{.*?\n\}", html, re.DOTALL)
    if not render:
        errors.append("portfolio.html: renderCard(d) not found")
        return
    source = render.group(0)
    branch = re.search(r"const ctaHTML = d\.bundle\s*\?\s*(`[^`]*`)\s*:", source)
    if not branch:
        errors.append("portfolio.html: renderCard must choose a set-level CTA via 'const ctaHTML = d.bundle ? ... : ...'")
    elif re.search(r"wa\.me|whatsapp|mailto:|strategic-brief", branch.group(1), re.IGNORECASE):
        errors.append("portfolio.html: the bundle branch of renderCard emits a per-domain WhatsApp/mailto/brief link")
    before = source[: branch.start()] if branch else source
    if re.search(r"wa\.me|mailto:", before, re.IGNORECASE):
        errors.append("portfolio.html: renderCard builds a WhatsApp/mailto link before the bundle-only branch")

    # When Node is available, render the actual cards and inspect the output.
    node = shutil.which("node")
    if not node or not branch:
        return
    entries = [re.search(r'\{domain:"' + re.escape(d) + r'"[^\n]*\}', html) for d in index]
    entries = [m.group(0) for m in entries if m]
    helpers = "".join(
        m.group(0) + "\n"
        for pattern in (
            r"const getSLD = [^\n]*",
            r"const getTLD = [^\n]*",
            r"function tldClass\(.*?\n\}",
        )
        for m in [re.search(pattern, html, re.DOTALL)]
        if m
    )
    tag_class = re.search(r"const TAG_CLASS = \{.*?\};", html, re.DOTALL)
    script = (
        (tag_class.group(0) if tag_class else "const TAG_CLASS = {};") + "\n" + helpers + source + "\n"
        + "const out = [" + ",".join(entries) + "].map(renderCard);\n"
        + "process.stdout.write(JSON.stringify(out));\n"
    )
    try:
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"portfolio.html: could not render cards with node ({exc})")
        return
    if result.returncode != 0:
        errors.append(f"portfolio.html: rendering bundle-only cards failed: {result.stderr.strip()[:200]}")
        return
    for card in json.loads(result.stdout):
        label = "portfolio.html (rendered card)"
        errors.extend(detect_individual_routes(label, card, index))
        errors.extend(detect_per_domain_ctas(label, card, index))
        hrefs = HREF_RE.findall(card)
        bundle_urls = {b["bundle_url"] for b in index.values()}
        if len(hrefs) != 1 or hrefs[0] not in bundle_urls:
            errors.append(f"{label}: a bundle-only card must have exactly one link, to its set page (found {hrefs})")


def check_strategic_brief(bundles, index, errors):
    js = STRATEGIC_BRIEF_JS_PATH.read_text(encoding="utf-8")
    html = STRATEGIC_BRIEF_PATH.read_text(encoding="utf-8")
    options = json.loads(BRIEF_OPTIONS_PATH.read_text(encoding="utf-8"))
    for bundle in bundles:
        if f'bundleUrl: "{bundle["bundle_url"]}"' not in js:
            errors.append(f"js/strategic-brief.js: bundle-only guard must hand off to {bundle['bundle_url']}")
        for domain in bundle["domains"]:
            if f'"{domain}"' not in js:
                errors.append(f"js/strategic-brief.js: bundle-only guard does not list {domain}")
            if f'href="{bundle["bundle_url"]}"' not in html or domain not in html:
                errors.append(f"strategic-brief.html: static bundle-only notice must name {domain} and link {bundle['bundle_url']}")
    if "window.location.replace(BUNDLE_ONLY.bundleUrl)" not in js:
        errors.append("js/strategic-brief.js: legacy ?asset= links for bundle-only domains must redirect to the set page")
    for value in re.findall(r'<option value="([^"]*)"', html):
        if names_in(value, index):
            errors.append(f"strategic-brief.html: datalist offers bundle-only '{value}' as an individual asset option")
    for value in options.get("asset_options", []):
        if names_in(value, index):
            errors.append(f"brief-request-options.json: asset_options offers bundle-only '{value}' individually")


def validate_repository():
    errors = []
    bundles = load_registry()
    index = domain_index(bundles)
    check_registry(bundles, errors)
    for bundle in bundles:
        check_bundle_page(bundle, errors)

    scanned = 0
    for path in published_files():
        rel = str(path.relative_to(REPO_ROOT))
        text = path.read_text(encoding="utf-8")
        scanned += 1
        errors.extend(detect_individual_routes(rel, text, index))
        if path.suffix == ".html":
            errors.extend(detect_per_domain_ctas(rel, text, index))
        if path.suffix == ".json":
            errors.extend(detect_json_brief_urls(rel, json.loads(text), index))

    check_inventory(index, errors)
    check_category_artifacts(index, errors)
    check_portfolio(index, errors)
    check_strategic_brief(bundles, index, errors)
    return errors, scanned, index


def self_test():
    """Feed known-bad samples through each detector; every one must be caught."""
    index = domain_index([{
        "bundle_id": "t", "bundle_url": "/bundles/t/",
        "domains": ["AITopSight.com", "ARTopSight.com", "VRTopSight.com"],
    }])
    bad = {
        "single-asset brief link": ('<a href="/strategic-brief.html?asset=ARTopSight.com&amp;type=single-asset-acquisition">Request Brief</a>', "routes"),
        "encoded brief link": ("/strategic-brief.html?asset=aitopsight%2Ecom&type=single-asset-acquisition", "routes"),
        "lowercase brief link": ('"/strategic-brief.html?type=escrow-closing&asset=vrtopsight.com"', "routes"),
        "per-domain WhatsApp": ("https://wa.me/+212668992259?text=Hello%2C+I'm+interested+in+acquiring+vrtopsight.com", "routes"),
        "per-domain mailto": ('<a href="mailto:agent@sohadot.com?subject=Offer%20for%20AITopSight.com">Make an offer</a>', "routes"),
        "per-domain CTA": ('<a href="/contact.html">Acquire ARTopSight.com</a>', "ctas"),
        "JSON strategic_brief_url": ({"domain": "aitopsight.com", "strategic_brief_url": "/strategic-brief.html?asset=aitopsight.com&type=single-asset-acquisition"}, "json"),
    }
    good = {
        "set-level mailto": ("mailto:agent@sohadot.com?subject=Set&body=AITopSight.com%2C%20ARTopSight.com%2C%20VRTopSight.com", "routes"),
        "set-page CTA": ('<a href="/bundles/t/">View Complete Set</a>', "ctas"),
        "reference link": ('<a href="/category-artifacts.html#artopsight-com">ARTopSight.com</a>', "ctas"),
        "unrelated brief": ("/strategic-brief.html?asset=ToAVR.com&type=single-asset-acquisition", "routes"),
    }
    run = {
        "routes": lambda s: detect_individual_routes("t", s, index),
        "ctas": lambda s: detect_per_domain_ctas("t", s, index),
        "json": lambda s: detect_json_brief_urls("t", s, index),
    }
    failures = []
    for name, (sample, kind) in bad.items():
        if not run[kind](sample):
            failures.append(f"self-test: detector missed '{name}'")
    for name, (sample, kind) in good.items():
        if run[kind](sample):
            failures.append(f"self-test: false positive on '{name}': {run[kind](sample)}")
    return failures, len(bad), len(good)


def main():
    if "--self-test" in sys.argv:
        failures, n_bad, n_good = self_test()
        if failures:
            for f in failures:
                print(f"FAIL: {f}")
            sys.exit(1)
        print(f"PASS: bundle-only self-test — {n_bad} violation samples detected, {n_good} valid samples accepted")
        return

    failures, _, _ = self_test()
    errors, scanned, index = validate_repository()
    errors = failures + errors
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        sys.exit(1)
    print(
        f"PASS: bundle-only enforcement clean — {len(index)} bundle-only domains, "
        f"{scanned} published files scanned, no individual acquisition routes"
    )


if __name__ == "__main__":
    main()
