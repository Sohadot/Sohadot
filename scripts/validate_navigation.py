#!/usr/bin/env python3
"""Validate Sohadot navigation and social-preview metadata.

Fails (non-zero exit) if:
  * a page that should carry the global nav is missing the markers or is out of
    sync with data/site-navigation.json;
  * any legacy navigation markup (the old 12-link bar) remains;
  * a public page declares a Twitter card but has no og:image;
  * a page references an og:image/twitter:image whose local file is missing;
  * a page has conflicting (multiple distinct) og:image URLs.

Run: python3 scripts/validate_navigation.py
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sync_navigation as nav  # noqa: E402

LEGACY = [
    '<nav class="site-nav">',
    '<div class="nav-links">',
    'class="nav-logo"',
    'class="nav-cta"',
]

# Redirect stubs / verification files are not social surfaces.
SKIP_SOCIAL = {
    "404.html", "outbakes.html", "en/blog/index.html",
    "google28b5398e4140f820.html",
}

PROD = "https://sohadot.com"


def rel_files():
    return sorted(
        f for f in glob.glob("**/*.html", recursive=True)
        if not f.startswith(".git")
    )


def local_path_for(url: str) -> Path | None:
    """Map an absolute production image URL to a local file, if it is ours."""
    if url.startswith(PROD):
        return ROOT / url[len(PROD):].lstrip("/")
    return None  # external (another asset's own domain) — not our file


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    # 1) Navigation sync + markers on every page that should carry the nav.
    nav_data = json.loads((ROOT / "data" / "site-navigation.json").read_text(encoding="utf-8"))
    block = nav.build_block(nav_data)
    for relp in nav.PAGES:
        path = ROOT / relp
        if not path.exists():
            errors.append(f"[nav] missing file: {relp}")
            continue
        text = path.read_text(encoding="utf-8")
        if nav.START not in text or nav.END not in text:
            errors.append(f"[nav] missing markers: {relp}")
            continue
        if nav.inject(text, block) != text:
            errors.append(f"[nav] out of sync (run sync_navigation.py): {relp}")

    # 2) No legacy nav markup anywhere.
    for f in rel_files():
        text = Path(f).read_text(encoding="utf-8")
        for token in LEGACY:
            if token in text:
                errors.append(f"[legacy-nav] '{token}' still present in {f}")

    # 3) Social-preview metadata audit.
    for f in rel_files():
        if f in SKIP_SOCIAL:
            continue
        text = Path(f).read_text(encoding="utf-8")
        og_imgs = re.findall(r'property="og:image"\s+content="([^"]+)"', text)
        tw_card = "twitter:card" in text
        tw_imgs = re.findall(r'name="twitter:image"\s+content="([^"]+)"', text)

        if tw_card and not og_imgs:
            errors.append(f"[social] {f}: declares twitter:card but has no og:image")
        # conflicting distinct og:image urls
        if len(set(og_imgs)) > 1:
            errors.append(f"[social] {f}: conflicting og:image URLs: {sorted(set(og_imgs))}")
        if tw_card and not tw_imgs:
            warnings.append(f"[social] {f}: twitter:card without twitter:image")
        # local files must exist
        for url in set(og_imgs) | set(tw_imgs):
            lp = local_path_for(url)
            if lp is not None and not lp.exists():
                errors.append(f"[social] {f}: image not found locally: {url}")

    for w in warnings:
        print("WARN " + w)
    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors:
            print("  " + e)
        return 1
    print(f"\nvalidate_navigation: OK ({len(nav.PAGES)} nav pages, "
          f"{len(rel_files())} HTML files audited, {len(warnings)} warnings).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
