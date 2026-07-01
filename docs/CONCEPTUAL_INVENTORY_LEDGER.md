# Conceptual Inventory Ledger

**Public page:** `conceptual-inventory.html`
**Data:** `data/conceptual-inventory.json`
**Generator:** `scripts/generate_conceptual_inventory.py`
**Validator:** `scripts/validate_conceptual_inventory.py`
**Status:** A read-only coverage layer. It does not define new domains, does not expand the 50
Category Artifacts, does not change any canonical meaning, and does not add pricing, checkout,
buy-now, or marketplace language.

## Purpose

Sohadot's portfolio has grown to hundreds of domains, but only 50 of them carry a protected
canonical meaning in the Category Artifact Meaning Layer. Nothing on the site previously stated,
in one place, how much of the portfolio is actually covered by that meaning layer. The Conceptual
Inventory Ledger closes that gap by answering four questions directly:

1. How many domains are in the Sohadot portfolio?
2. How many of them have protected conceptual definitions?
3. Which commercial fields is each defined asset suitable for?
4. Which domains are still pending Canonical Meaning Lock?

This is a transparency and coverage tool, not a sales page. It reports honestly on how much of the
portfolio has been given a locked meaning and how much has not — without dressing up the gap.

## Source files

The ledger is derived, read-only, from three existing sources — it introduces no new domain data:

- **`portfolio.html`** — the `DOMAINS` array is the source of truth for the full public portfolio
  domain list (446 domains at time of writing).
- **`data/asset-meanings.json`** — the Category Artifact Meaning Layer. Source of protected
  canonical meanings and each asset's `possible_fields`.
- **`data/category-clusters.json`** — the Category Cluster & Buyer Logic Layer. Source of each
  defined asset's primary cluster membership and cluster-level buyer logic.

`scripts/generate_conceptual_inventory.py` reads all three, cross-references them by domain name,
and writes `data/conceptual-inventory.json`. `scripts/validate_conceptual_inventory.py` re-derives
the same counts independently and fails the build if the committed JSON has drifted from any of
the three sources.

## Portfolio domain vs. protected category artifact

These are two different things, and the ledger keeps them visually and structurally distinct:

- A **portfolio domain** is any domain Sohadot lists publicly for acquisition. Being in the
  portfolio means nothing more than: this domain exists, is available, and is tracked.
- A **protected category artifact** is a portfolio domain that has additionally gone through the
  meaning-lock process: a canonical segmentation, a canonical meaning, surface misreadings to
  avoid, a conceptual thesis, a category claim, possible fields, and buyer logic — reviewed and
  checked by `scripts/validate_asset_meanings.py` and `scripts/validate_protected_meanings.py`.

Every protected category artifact is a portfolio domain. Most portfolio domains are not (yet)
protected category artifacts. The ledger's `status` field makes this explicit per domain:
`protected-category-artifact` or `pending-canonical-meaning-lock`.

## Why undefined domains are not automatically given weak definitions

It would be easy to auto-generate a plausible-sounding sentence for each of the remaining domains
and call the portfolio "fully documented." This ledger deliberately does not do that, for two
reasons:

- **A canonical meaning is a published claim, not filler copy.** Each of the 50 existing entries
  in `data/asset-meanings.json` was reviewed for accuracy, checked against likely misreadings, and
  locked before being shown to a buyer. A domain that hasn't gone through that process has no
  canonical meaning to report — inventing one to fill a table cell would misrepresent it as
  reviewed when it is not.
- **Manufacturing 396 weak definitions would cheapen the 50 that were actually earned.** The value
  of the Category Artifact Meaning Layer depends on every entry in it meaning something specific
  and defensible. Diluting that set with guesses — even well-intentioned ones — undermines the
  layer this ledger is meant to make legible.

For every domain not present in `data/asset-meanings.json`, the ledger records
`canonical_meaning: null` and `possible_fields: []`, and the public page displays it plainly as
**Pending Canonical Meaning Lock** — still a real, available portfolio domain, just not yet run
through the meaning-lock process.

## How this ledger supports future expansion to Top 75 / Top 100

The Category Artifact Meaning Layer is expected to grow past its current 50 entries over future
sprints. Because the ledger is generated (not hand-maintained) directly from
`data/asset-meanings.json` and `data/category-clusters.json`, expanding either dataset and
re-running `scripts/generate_conceptual_inventory.py` automatically:

- Moves the newly defined domains from "pending" to "protected" in the next generated ledger.
- Recomputes `defined_assets_count`, `pending_meaning_lock_count`, and `cluster_count` with no
  manual bookkeeping.
- Keeps a running, auditable record of coverage progress — e.g. 50/446 today, tracked the same way
  at 75/446, 100/446, or against a larger future portfolio.

This sprint does not perform that expansion itself. It builds the measurement layer so that future
sprints expanding toward a Top 75 or Top 100 defined-asset set have an existing, validated way to
show progress.

## How it supports buyers

Buyers evaluating the portfolio can now see, at a glance and without contacting anyone:

- The total size of the portfolio and how much of it is backed by a reviewed canonical meaning.
- For every defined asset, the fields it is suitable for and the strategic cluster it belongs to,
  with a direct path to `strategic-brief.html` to request more detail on that specific asset.
- For every undefined domain, an honest "not yet defined" status rather than a misleading gap or
  an invented description — so a buyer never mistakes portfolio presence for a reviewed claim.

This makes portfolio coverage — what has been defined and what has not — a checkable fact rather
than an implicit assumption.
