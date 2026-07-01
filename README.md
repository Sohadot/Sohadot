# Sohadot — Domain Intelligence & Sovereign Digital Assets

**Live platform: [sohadot.com](https://sohadot.com)** — an independent domain intelligence platform combining structured valuation, a premium domain portfolio (445+ names), monthly keyword intelligence, weekly drop watchlists, a category artifact meaning layer with a strategic buyer-logic cluster layer above it, a strategic brief request channel for serious acquisition intent, a seller-approved escrow closing protocol, and direct domain brokerage.

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

### Strategic Brief Request Layer

`strategic-brief.html` is the acquisition-intent layer above both of those: a "Request Strategic
Brief" flow for buyers evaluating a single category artifact, a strategic cluster, or a broader
relationship with the portfolio — deliberately not a generic contact form, with no pricing table,
checkout, or "buy now" language anywhere on the page. The form (name, email, company/project, asset or
cluster of interest, inquiry type, message) needs no backend: it submits nowhere, storing nothing —
its native `action="mailto:agent@sohadot.com" method="GET" enctype="text/plain"` opens a plain-text
email draft even with JavaScript disabled, and `js/strategic-brief.js` progressively enhances it by
prefilling the asset/cluster field from `?asset=`, `?cluster=`, or `?type=` query parameters (used by
the "Request Brief for This Asset" links on `category-artifacts.html` and the "Request Brief for This
Cluster" links on `category-clusters.html`) and by building a cleaner structured `mailto:` link on
submit. Inquiry-type options and the asset/cluster autocomplete list are sourced from
`data/brief-request-options.json`, generated from `data/asset-meanings.json` and
`data/category-clusters.json` so the same 50 assets and 8 clusters stay the single source of truth.
Nothing typed into the form is sent, logged, or stored by Sohadot.com — only the user's own,
deliberate act of sending the resulting email transmits anything.

### Seller-Approved Escrow Closing Protocol

`escrow-closing.html` is a public trust page, not a transaction system: it explains that qualified
Sohadot asset transactions may close through **independent escrow**, and only after **written
agreement** and **seller approval** — never automatically from the website. Sohadot does not process
direct payments on-site, does not offer public checkout, and this page carries no price list, no
payment form, and no escrow API integration. The seven-step sequence (strategic brief → written terms
→ seller eligibility confirmation → seller-approved escrow initiation → buyer funding → registrar
transfer → fund release) is documented in full, alongside an explicit "what this protocol is not"
section, in `docs/ESCROW_CLOSING_PROTOCOL.md`. `strategic-brief.html` and
`data/brief-request-options.json` both carry an "Escrow closing after written agreement" inquiry type
(`?type=escrow-closing`) for buyers or sellers who have already reached written terms and want a
closing review — the Strategic Brief form remains the single inquiry path; escrow closing is never
started from a public button. `scripts/validate_escrow_closing_protocol.py` fails the build if the
public page loses any of its required boundary language, gains forbidden transaction-starting language
("Buy Now", "Checkout", "Pay Now", "Purchase Instantly", "Start Transaction Now") without an explicit
negation, or accumulates anything that looks like a hardcoded secret or API placeholder. A future
**private** operator launcher — an internal console for creating an escrow transaction after written
agreement and seller approval — is specified, but deliberately not implemented, in
`docs/OPERATOR_ESCROW_LAUNCHER_SPEC.md`: it must never place API keys, escrow credentials, or private
buyer data in this public repository, and must run as a private backend (e.g. a Cloudflare Worker or
other server-side function) with secrets held only in environment variables.

### Trust & Acquisition Readiness Audit

The full acquisition path — Home → Portfolio / Category Artifacts / Category Clusters → Strategic
Brief — is checked as one connected system, not five independent pages. `scripts/audit_acquisition_readiness.py`
verifies that every internal link and `category-artifacts.html#slug` / `category-clusters.html#cluster-id`
anchor resolves, that every `?asset=` / `?cluster=` deep link on the Strategic Brief CTAs points to a
real artifact or cluster, that no cheap-marketplace language ("buy now", "checkout", "cart", "clearance",
"bargain", and similar) appears outside an explicit negation, that `strategic-brief.html` carries no
pricing table or urgency pressure, and that `sitemap.xml` and this README stay current with the
Category Artifact, Category Cluster, and Strategic Brief layers. Findings and the pass/fail result are
recorded in `docs/TRUST_AND_ACQUISITION_READINESS_AUDIT.md`.

## Principles

- Structure over hype — assets are classified, documented, and positioned, not just listed
- Public methodology — the system that builds the assets is itself open and inspectable
- Long-horizon value — built for durability and strategic legitimacy, not short-term noise

## Contact

- ✉️ agent@sohadot.com
- 💬 [WhatsApp](https://wa.me/212668992259)
- 🌐 [sohadot.com](https://sohadot.com)
