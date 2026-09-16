#!/usr/bin/env python3
"""Synchronize Sohadot primary navigation across static HTML pages.

Single source of truth: ``data/site-navigation.json``.
This script renders one self-contained navigation block (scoped CSS + markup)
and injects it between explicit markers in every public HTML page:

    <!-- SOHADOT:NAV:START -->  ... generated ...  <!-- SOHADOT:NAV:END -->

Design constraints (see the gateway sprint brief):
  * No framework, no CMS, no CDN, no runtime dependency.
  * The rendered HTML contains the full navigation; it works with JavaScript
    disabled (menus use native <details>/<summary>).
  * A tiny progressive-enhancement script only improves behaviour (close on
    Escape / outside click, hover-open on pointer devices).

Usage:
  python3 scripts/sync_navigation.py            # sync pages that have markers
  python3 scripts/sync_navigation.py --install  # also insert markers where missing
  python3 scripts/sync_navigation.py --check    # verify every page is in sync (CI)
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAV_JSON = ROOT / "data" / "site-navigation.json"

START = "<!-- SOHADOT:NAV:START -->"
END = "<!-- SOHADOT:NAV:END -->"

# Pages that carry the global navigation. Paths are relative to repo root.
PAGES = [
    "index.html", "about.html", "portfolio.html", "developed-assets.html",
    "conceptual-inventory.html", "category-artifacts.html", "category-clusters.html",
    "valuation.html", "keywords.html", "dropping.html", "knowledge-base.html",
    "how-to-buy.html", "strategic-brief.html", "top-75-queue.html",
    "escrow-closing.html", "allenarly.html", "frameworks/index.html",
    "frameworks/agent-aptness/index.html", "outbakes/index.html",
    "hygieneroll/index.html", "altissports/index.html",
    "san-jose-bundle/index.html", "automation-bundle/index.html",
    "privacy.html", "terms.html",
    "kb/domain-development.html", "kb/the-domain-is-the-coordinate.html",
    "kb/meaning-before-building.html", "kb/how-domain-valuation-works.html",
    "kb/how-to-read-comparable-sales.html", "kb/what-makes-a-domain-premium.html",
    "kb/keyword-strength-and-naming-terrain.html",
    "kb/domain-buyer-psychology-and-negotiation.html",
    "kb/wholesale-vs-retail-domain-pricing.html",
]


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_css() -> str:
    return """
<style id="sdn-style">
/* Sohadot global navigation — self-contained, scoped with .sdn- prefix. */
.sdn{--sdn-ivory:#f6f2e9;--sdn-blue:#0f2658;--sdn-blue-2:#2454d3;--sdn-ink:#1f2a44;
  --sdn-muted:#5b6478;--sdn-border:rgba(15,38,88,.14);--sdn-panel:#fffdf8;
  position:sticky;top:0;z-index:200;background:rgba(246,242,233,.92);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--sdn-border);font-family:'DM Sans','Segoe UI',system-ui,sans-serif;}
.sdn *{box-sizing:border-box;}
/* Defensive resets so host-page element selectors (e.g. generic nav{}) cannot leak in. */
.sdn-nav{position:static;background:none;border:0;box-shadow:none;backdrop-filter:none;
  -webkit-backdrop-filter:none;max-width:1200px;margin:0 auto;padding:12px 24px;
  display:flex;align-items:center;gap:24px;}
.sdn a{text-decoration:none;}
.sdn ul{list-style:none;}
.sdn-brand{display:flex;align-items:center;gap:12px;text-decoration:none;flex-shrink:0;}
.sdn-brand-mark{width:38px;height:38px;border-radius:12px;
  background:linear-gradient(135deg,#0f2658 0%,#2454d3 100%);
  box-shadow:0 8px 20px rgba(36,84,211,.18);display:flex;align-items:center;justify-content:center;
  color:#fff;font-weight:700;font-size:.95rem;letter-spacing:.04em;}
.sdn-brand-name{font-family:'Cormorant Garamond','Playfair Display',serif;font-size:1.7rem;
  line-height:1;font-weight:700;color:var(--sdn-blue);letter-spacing:.01em;}
.sdn-menu{list-style:none;margin:0;padding:0;display:flex;align-items:center;gap:6px;
  margin-left:auto;flex-wrap:wrap;}
.sdn-item{position:relative;}
.sdn-link,.sdn-summary{display:inline-flex;align-items:center;gap:6px;font-size:.82rem;
  font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sdn-muted);
  text-decoration:none;padding:10px 12px;border-radius:10px;cursor:pointer;
  background:none;border:0;transition:color .16s ease,background .16s ease;}
.sdn-link:hover,.sdn-summary:hover,.sdn-link:focus-visible,.sdn-summary:focus-visible{color:var(--sdn-blue);}
.sdn-details[open] > .sdn-summary{color:var(--sdn-blue);background:rgba(15,38,88,.06);}
.sdn-summary{list-style:none;}
.sdn-summary::-webkit-details-marker{display:none;}
.sdn-caret{width:9px;height:9px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;
  transform:rotate(45deg);margin-top:-3px;transition:transform .18s ease;opacity:.75;}
.sdn-details[open] > .sdn-summary .sdn-caret{transform:rotate(-135deg);margin-top:3px;}
.sdn-cta{display:inline-flex;align-items:center;font-size:.8rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.08em;text-decoration:none;color:#fff;
  padding:11px 18px;border-radius:12px;background:linear-gradient(135deg,var(--sdn-blue),var(--sdn-blue-2));
  box-shadow:0 8px 20px rgba(36,84,211,.2);transition:transform .15s ease,box-shadow .15s ease;}
.sdn-cta:hover{transform:translateY(-1px);box-shadow:0 12px 26px rgba(36,84,211,.3);}
.sdn-panel{background:var(--sdn-panel);border:1px solid var(--sdn-border);border-radius:16px;
  box-shadow:0 24px 60px rgba(15,38,88,.16);padding:22px;}
/* Desktop dropdown positioning */
@media (min-width:961px){
  .sdn-cb{display:none;}
  .sdn-has-mega{position:static;}
  .sdn-panel{position:absolute;top:calc(100% + 10px);right:0;left:auto;min-width:280px;}
  .sdn-mega{width:min(760px,92vw);left:50%;right:auto;transform:translateX(-50%);}
}
.sdn-groups{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));}
.sdn-group-title{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
  color:var(--sdn-blue-2);margin:0 0 12px;}
.sdn-group ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px;}
.sdn-entry{display:block;text-decoration:none;color:var(--sdn-ink);border-radius:10px;
  padding:8px 10px;transition:background .15s ease;}
.sdn-entry:hover,.sdn-entry:focus-visible{background:rgba(15,38,88,.05);}
.sdn-entry-label{display:block;font-weight:700;font-size:.92rem;color:var(--sdn-blue);}
.sdn-entry-desc{display:block;font-size:.8rem;color:var(--sdn-muted);line-height:1.5;margin-top:2px;}
.sdn-asset .sdn-entry-domain{display:block;font-weight:700;font-size:.95rem;color:var(--sdn-blue);}
.sdn-asset .sdn-entry-artifact{display:block;font-size:.78rem;color:var(--sdn-muted);margin-top:1px;}
.sdn-ext{font-size:.62rem;letter-spacing:.06em;color:var(--sdn-muted);vertical-align:super;}
.sdn-viewall{display:inline-flex;align-items:center;gap:6px;margin-top:14px;font-weight:700;
  font-size:.82rem;color:var(--sdn-blue-2);text-decoration:none;}
.sdn-viewall:hover{text-decoration:underline;}
/* Mobile toggle — no-JS checkbox pattern + accordion */
.sdn-cb{position:absolute;width:1px;height:1px;opacity:0;overflow:hidden;clip:rect(0 0 0 0);margin:0;}
.sdn-toggle{display:none;margin-left:auto;align-items:center;justify-content:center;
  width:44px;height:44px;border:1px solid var(--sdn-border);border-radius:12px;background:var(--sdn-panel);
  cursor:pointer;color:var(--sdn-blue);}
.sdn-toggle span,.sdn-toggle span::before,.sdn-toggle span::after{content:'';display:block;width:20px;
  height:2px;background:currentColor;border-radius:2px;position:relative;}
.sdn-toggle span::before{position:absolute;top:-6px;}
.sdn-toggle span::after{position:absolute;top:6px;}
.sdn-cb:focus-visible + .sdn-toggle{outline:2px solid var(--sdn-blue-2);outline-offset:2px;}
@media (max-width:960px){
  .sdn-nav{flex-wrap:wrap;padding:12px 18px;}
  .sdn-toggle{display:inline-flex;}
  .sdn-menu{display:none;flex-direction:column;align-items:stretch;flex-basis:100%;width:100%;gap:2px;margin:10px 0 4px;}
  .sdn-cb:checked ~ .sdn-menu{display:flex;}
  .sdn-item{width:100%;}
  .sdn-link,.sdn-summary{width:100%;justify-content:space-between;padding:14px 8px;font-size:.9rem;
    border-bottom:1px solid var(--sdn-border);}
  .sdn-cta{width:100%;justify-content:center;margin-top:10px;}
  .sdn-panel{position:static;box-shadow:none;border:0;border-radius:0;padding:6px 8px 14px;
    background:rgba(15,38,88,.03);}
  .sdn-mega{width:100%;}
  .sdn-groups{grid-template-columns:1fr;gap:16px;}
}
</style>""".strip()


def render_entry(item: dict) -> str:
    desc = ""
    if item.get("desc"):
        desc = f'<span class="sdn-entry-desc">{esc(item["desc"])}</span>'
    return (
        f'<li><a class="sdn-entry" href="{esc(item["href"])}">'
        f'<span class="sdn-entry-label">{esc(item["label"])}</span>{desc}</a></li>'
    )


def render_asset(a: dict) -> str:
    ext = ' <span class="sdn-ext">↗</span>' if a.get("external") else ""
    return (
        f'<li><a class="sdn-entry sdn-asset" href="{esc(a["href"])}">'
        f'<span class="sdn-entry-domain">{esc(a["domain"])}{ext}</span>'
        f'<span class="sdn-entry-artifact">{esc(a["artifact"])}</span></a></li>'
    )


def render_group(group: dict) -> str:
    rows = []
    for item in group.get("items", []):
        rows.append(render_entry(item))
    for a in group.get("assets", []):
        rows.append(render_asset(a))
    inner = "".join(rows)
    footer = ""
    if group.get("footerLink"):
        fl = group["footerLink"]
        footer = (
            f'<a class="sdn-viewall" href="{esc(fl["href"])}">{esc(fl["label"])} '
            f'<span aria-hidden="true">→</span></a>'
        )
    return (
        f'<div class="sdn-group"><p class="sdn-group-title">{esc(group["title"])}</p>'
        f'<ul>{inner}</ul>{footer}</div>'
    )


def render_top(entry: dict) -> str:
    if entry.get("cta"):
        return (
            f'<li class="sdn-item"><a class="sdn-cta" href="{esc(entry["href"])}">'
            f'{esc(entry["label"])}</a></li>'
        )
    if not entry.get("groups"):
        return (
            f'<li class="sdn-item"><a class="sdn-link" href="{esc(entry["href"])}">'
            f'{esc(entry["label"])}</a></li>'
        )
    groups = "".join(render_group(g) for g in entry["groups"])
    is_mega = len(entry["groups"]) > 1
    mega = " sdn-mega" if is_mega else ""
    item_cls = "sdn-item sdn-has-mega" if is_mega else "sdn-item"
    return (
        f'<li class="{item_cls}"><details class="sdn-details">'
        f'<summary class="sdn-summary">{esc(entry["label"])}'
        '<span class="sdn-caret" aria-hidden="true"></span></summary>'
        f'<div class="sdn-panel{mega}"><div class="sdn-groups">{groups}</div></div>'
        "</details></li>"
    )


def render_script() -> str:
    return """
<script>
/* Progressive enhancement only — navigation is fully usable without this. */
(function(){
  var header=document.getElementById('sdn-header');
  if(!header)return;
  var cb=document.getElementById('sdn-menu-toggle');
  var details=Array.prototype.slice.call(header.querySelectorAll('.sdn-details'));
  function isDesktop(){return window.matchMedia('(min-width:961px)').matches;}
  details.forEach(function(d){
    d.addEventListener('toggle',function(){
      if(d.open&&isDesktop()){details.forEach(function(o){if(o!==d)o.open=false;});}
    });
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'){details.forEach(function(d){d.open=false;});if(cb)cb.checked=false;}
  });
  document.addEventListener('click',function(e){
    if(!header.contains(e.target)&&isDesktop()){details.forEach(function(d){d.open=false;});}
  });
})();
</script>""".strip()


def render_nav(nav: dict) -> str:
    brand = nav["brand"]
    tops = "".join(render_top(e) for e in nav["primary"])
    body = (
        f'<header class="sdn" id="sdn-header" role="banner">'
        f'<nav class="sdn-nav" aria-label="Primary">'
        f'<a class="sdn-brand" href="{esc(brand["href"])}" aria-label="{esc(brand["ariaLabel"])}">'
        f'<span class="sdn-brand-mark" aria-hidden="true">S</span>'
        f'<span class="sdn-brand-name">{esc(brand["name"])}</span></a>'
        f'<input type="checkbox" id="sdn-menu-toggle" class="sdn-cb">'
        f'<label class="sdn-toggle" for="sdn-menu-toggle" '
        f'aria-label="Toggle navigation menu" title="Menu"><span></span></label>'
        f'<ul class="sdn-menu">{tops}</ul>'
        f"</nav></header>"
    )
    return render_css() + "\n" + body + "\n" + render_script()


def build_block(nav: dict) -> str:
    return f"{START}\n{render_nav(nav)}\n{END}"


def inject(text: str, block: str) -> str:
    if START in text and END in text:
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
        return pattern.sub(lambda _m: block, text, count=1)
    return text


def install_markers(text: str, block: str) -> str:
    """Insert markers on a page that has none, removing the legacy site-nav."""
    site_nav = re.compile(r"<nav class=\"site-nav\">.*?</nav>", re.DOTALL)
    if site_nav.search(text):
        return site_nav.sub(lambda _m: block, text, count=1)
    # No legacy site-nav: insert immediately after the opening <body ...> tag.
    body = re.compile(r"(<body[^>]*>)", re.IGNORECASE)
    if body.search(text):
        return body.sub(lambda m: m.group(1) + "\n" + block, text, count=1)
    return text


def main() -> int:
    args = set(sys.argv[1:])
    install = "--install" in args
    check = "--check" in args
    nav = json.loads(NAV_JSON.read_text(encoding="utf-8"))
    block = build_block(nav)

    changed, synced, missing, drift = [], 0, [], []
    for rel in PAGES:
        path = ROOT / rel
        if not path.exists():
            print(f"  ! missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        has_markers = START in text and END in text
        if not has_markers:
            if install:
                new = install_markers(text, block)
                if new != text:
                    path.write_text(new, encoding="utf-8")
                    changed.append(rel + " (installed)")
                    continue
            missing.append(rel)
            continue
        new = inject(text, block)
        if new != text:
            if check:
                drift.append(rel)
            else:
                path.write_text(new, encoding="utf-8")
                changed.append(rel)
        else:
            synced += 1

    for c in changed:
        print(f"  updated: {c}")
    print(f"\n{len(changed)} updated, {synced} already in sync.")
    if missing:
        print(f"{len(missing)} without markers (run --install): " + ", ".join(missing))
    if check and (drift or missing):
        print("\nCHECK FAILED — navigation out of sync:")
        for d in drift:
            print(f"  drift: {d}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
