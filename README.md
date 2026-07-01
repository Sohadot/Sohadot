# Sohadot — Domain Intelligence & Sovereign Digital Assets

**Live platform: [sohadot.com](https://sohadot.com)** — an independent domain intelligence platform combining structured valuation, a premium domain portfolio (445+ names), monthly keyword intelligence, weekly drop watchlists, a category artifact meaning layer, and direct domain brokerage.

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

## Principles

- Structure over hype — assets are classified, documented, and positioned, not just listed
- Public methodology — the system that builds the assets is itself open and inspectable
- Long-horizon value — built for durability and strategic legitimacy, not short-term noise

## Contact

- ✉️ agent@sohadot.com
- 💬 [WhatsApp](https://wa.me/212668992259)
- 🌐 [sohadot.com](https://sohadot.com)
