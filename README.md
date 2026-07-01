# Sohadot — Domain Intelligence & Sovereign Digital Assets

**Live platform: [sohadot.com](https://sohadot.com)** — an independent domain intelligence platform combining structured valuation, a premium domain portfolio (445+ names), monthly keyword intelligence, weekly drop watchlists, a category artifact meaning layer with a strategic buyer-logic cluster layer above it, and direct domain brokerage.

## What I build

| Layer | Where | What it is |
|---|---|---|
| 🌐 Platform | [sohadot.com](https://sohadot.com) | Domain valuation engine, premium portfolio, keyword & drop intelligence |
| 🏛️ Doctrine | [sovereign-asset-system](https://github.com/Sohadot/sovereign-asset-system) | The operating system behind the portfolio: asset taxonomy, dossier standards, valuation frameworks, long-horizon positioning rules |
| 📂 Asset surfaces | [All repositories](https://github.com/Sohadot?tab=repositories) | Individual digital assets built as inspectable, reference-grade surfaces |

## How this repository works

This repository is the source of [sohadot.com](https://sohadot.com), deployed via GitHub Pages:

- **`index.html` + pages** — the platform's static surfaces
- **`js/valuation-engine.js`** — client-side structured valuation logic (lexical legitimacy, commercial keywords, TLD fit, comparable sales)
- **`data/*.json`** — valuation datasets, keyword intelligence, drop watchlists
- **`scripts/*.py` + GitHub Actions** — automated pipelines that refresh drops weekly and keywords monthly

### Category Artifact Meaning Layer

`category-artifacts.html` is a separate, static meaning layer alongside `portfolio.html`. Where the
portfolio answers "what's for sale," this layer explains a curated set of 50 domains as **category
artifacts** — objects with a canonical segmentation, a literal meaning, misreadings to actively avoid,
a conceptual thesis, a one-line category claim, plausible commercial fields, and the buyer logic that
makes each name legible. The data lives in `data/asset-meanings.json` (canonical records) and
`data/acronym-glossary.json` (acronym expansions referenced across those records), is rendered
statically for SEO and no-JS accessibility — every field is readable with JavaScript off —
progressively enhanced by `js/asset-meanings.js` (search and acronym tooltips only — no external JS
libraries), and checked by two validators before it ships: `scripts/validate_asset_meanings.py`
(schema completeness, duplicate domains, valid TLDs) and `scripts/validate_protected_meanings.py`
(a Canonical Meaning Lock that fails the build if a name's user-approved reading drifts back toward a
plausible-but-wrong surface interpretation, or if a required canonical phrase goes missing).

### Category Cluster & Buyer Logic Layer

`category-clusters.html` sits one layer above the meaning layer, without adding a single new domain.
It groups the same 50 protected assets into 8 strategic acquisition clusters — by buyer logic and
acquisition rationale, not by product category — so the page reads as a map of strategic asset
clusters rather than a marketplace filter. Each cluster names a strategic thesis, the buyer types it's
legible to, an acquisition rationale explaining why a buyer would want several of its members at once,
and one lead asset; every domain has exactly one primary cluster, and a small number also appear as
secondary members of the Cultural, Taste & Meaning Identity cluster where a technical or commercial
asset carries a second, cultural reading. The data lives in `data/category-clusters.json`, is rendered
statically (readable with JavaScript off), progressively enhanced by `js/category-clusters.js`
(search/filter only), and checked by `scripts/validate_category_clusters.py` — which fails if a
cluster is missing required fields, references a domain absent from `data/asset-meanings.json`,
double-assigns a domain to two primary clusters, leaves any asset without a primary cluster, or points
`lead_asset` outside that cluster's own `primary_members`.

## Principles

- Structure over hype — assets are classified, documented, and positioned, not just listed
- Public methodology — the system that builds the assets is itself open and inspectable
- Long-horizon value — built for durability and strategic legitimacy, not short-term noise

## Contact

- ✉️ agent@sohadot.com
- 💬 [WhatsApp](https://wa.me/212668992259)
- 🌐 [sohadot.com](https://sohadot.com)
