# Plan for the First 500 Qualified Transactions

- **Status:** Sprint 1B proposal, research only (2026-10-09). Nothing in this
  plan has been sent, bought, imported or deployed.
- **"Qualified"** means `ELIGIBLE` under the candidate pipeline. A
  qualified sale is:
  - reviewed;
  - a sale **shown to have completed**, by an explicit completion-evidence
    basis;
  - single-domain;
  - paid in cash;
  - at an exact or rounded price;
  - dated by a **sale date stated in the evidence**, never a report date or
    reporting window;
  - free of unresolved duplicates and conflicts;
  - covered by **storage and commercial-modelling rights from a party able
    to grant them**, including upstream rights where the data originates
    with a venue.

## 1. Targets

The holdout protocol needs at least 150 independent records **in addition
to** the calibration data. The first stage therefore needs about **650
eligible records**: 500 for calibration and development, and 150 or more
reserved privately for the holdout.

| Stratum | Target among the 500 | Why |
| --- | --- | --- |
| < $2.5k | 125 | Most real queries; the engine overestimates this band |
| $2.5k–$10k | 150 | Core ordinary market |
| $10k–$100k | 150 | Upper ordinary market; few data today |
| $100k–$1M | 50 | Context and range checks |
| ≥ $1M | 25 | Reference only; never the headline metric |
| Extensions other than .com | at least 150 (30%) | The engine borrows .com landmarks for other extensions |
| Market side | at least 30% wholesale and at least 30% retail | v2.5 cannot separate them |
| Naming class (human rules) | at least 40 per class | Comparability is class-driven |
| Sale date | at least 70% in 2021–2026 | Recency |
| Source families | at least 3 originating families (venue, party, filer or court) obtained directly, not only through one relay; no single family above 40% of calibration; holdout no more than 25% per source, with family and relay shares both reported | Independence: several venues named by one relay are one relay path, not independent families |

**Later stages:**
- 2,000 needs at least one bulk permission or licence.
- 10,000+ needs a licence at aggregator or venue scale (e.g. NameBio,
  GoDaddy).
- No combination of public records and manual citation reaches either.

## 2. Workstreams

### A. Primary public records (no third-party permission needed)

- **Sources:**
  - SEC EDGAR full-text search for domain purchases;
  - court orders in bankruptcy domain sales.
- **Prerequisites:**
  - a role contact address in the EDGAR user agent (D8);
  - counsel's confirmation that public-record facts may be stored and
    modelled (D1a);
  - PACER fees only with owner approval.
- **Expected yield:** tens of records (assumption), skewed toward $100k+
  and often bundles or stock. Valuable for verification and the upper
  bands, not for volume.

### B. Permission from the leading relay: DN Journal (discovery and cross-check)

- **What it offers:**
  - One bi-weekly report lists about 200 sales, about 170 of them under
    $10k.
  - Each row names its venue.
  - Its own notice makes written consent the route.
- **Why it cannot supply qualified sales on its own:**
  - **Sale dates:** rows carry a reporting window, not a sale date. Under
    the pipeline rules, a relay row stays `SALE_DATE_UNKNOWN` until the
    venue or a party states the date.
  - **Completion:** a row is a reported price (`REPORTED_PRICE`) unless the
    report states, for that row or in a stated rule covering every listed
    row, that the sale completed. Whether a publisher's general statement
    (for example, that lease-to-own sales are listed only once paid) is
    enough completion evidence is a reviewer decision. It is not assumed.
  - **Upstream rights:** DN Journal can grant rights in its own reports.
    Rows that originate with Sedo, Atom, Afternic and other venues stay
    `UPSTREAM_RIGHTS_UNCONFIRMED` unless DN Journal confirms it may license
    that data or the venue grants rights directly.
  - **Independence:** rows from many venues received through one relay are
    one relay path. Venue diversity in a relay is not source-family
    independence.
- **Ask for:**
  - domain, price, currency and conversion, venue and reporting window;
  - any sale dates and completion status it holds;
  - **which rights it can grant in venue-originated data**;
  - for reports from 2021 onward, for internal calibration and evaluation
    of a free valuation tool;
  - with no redistribution of rows, attribution, and deletion on request.
- **Expected yield (revised assumption):**
  - **Alone: 0 qualified sales**, for the date, completion and upstream
    reasons above.
  - **Combined with venue records (C):** relay rows become a discovery
    index and a cross-check. A row qualifies once the venue's own record
    supplies the sale date, completion and rights.
  - The earlier figure of "3–5 reports for the sub-$10k target" is
    withdrawn. It assumed reporting windows could stand in for sale dates.
- **Evidence status:** relay rows are `REPORTED` (tier C) and are
  superseded by the venue's own record when matched.

### C. Venue permissions (the primary route to qualified sales)

- **Venues:** Sedo, Atom, Flippa, park.io, GoDaddy Auctions / Afternic.
  Each venue's own terms reserve reuse to written permission.
- **Ask for:**
  - completed, non-NDA sales: domain, price, currency;
  - the **sale (completion) date**;
  - **completion status** (paid and transferred, as opposed to agreed or
    auction won);
  - market side, or the venue type as a proxy;
  - the same use limits as in B.
- **Expected yield (assumption):**
  - A venue that supplies completion dates and status for its completed
    sales would let most sub-$100k rows qualify. Suppose 70–85% survive
    the removal of duplicates, lease-to-own deals, bundles and non-USD rows
    without an FX basis.
  - **How many venues:** at least two venue permissions are needed to
    reach about 650 qualified sales with family independence for the
    holdout. Three reduce concentration risk.
  - **Timing:** depends entirely on replies. No dates are promised.
- **Why it matters:**
  - A venue's own records are tier B (`MARKETPLACE_RECORD`), which is
    stronger than a relay.
  - Venue records supply independent source families for the holdout.
- **Particular points:**
  - Sedo's terms name "competitor analysis" as a prohibited use, so the
    request should state the use plainly.
  - park.io's $99 rows are fixed backorder prices and need special
    handling.

### D. Licensed aggregator (only if the owner approves cost enquiries)

- NameBio's paid API requires written permission even for use in a free
  product, and access is aimed at "large, established businesses".
- Enquiring about terms and cost is an owner decision (D4). Nothing is
  bought without approval.

### E. Seller- and broker-consented submissions (later)

- Domain owners and brokers submit their own completed sales, with
  evidence (venue or escrow confirmation) and an explicit rights grant.
- This needs a public form and a privacy notice. That is a production
  change and needs separate authorisation (D6).

### F. Individually cited facts (only with counsel's basis)

- **What:** manually recording individual sales announced by venues or the
  press. Each is attributed, with a short checked quote, a link and a
  document hash, as in Registry v1.
- **Condition:** counsel documents a lawful basis for storage and modelling
  (D1b).
- **Expected yield:** modest (low hundreds at most) and slow. Sedo-derived
  facts carry the specific "competitor analysis" risk.

## 3. Sequence and gates

| Step | Work | Gate |
| --- | --- | --- |
| 0 | Owner decisions D1–D8 | Owner |
| 1 | Workstream A on primary records; finalise human naming-class rules | D1a, D7, D8 |
| 2 | Send permission requests B and C (drafts in §5); log replies as rights references, recording who granted them and whether upstream rights are covered | D3 |
| 3 | Set up private storage for licensed and holdout data | D2 |
| 4 | Ingest permitted data into private storage through the pipeline; second review per D5 | Permission received |
| 5 | Reserve 150+ holdout records privately, from originating source families separate from calibration (judged by family and by relay) | Holdout controls implemented |
| 6 | Research pilot: compare v2.5 (C0) with candidates C1–C6 on development data only, reported per stratum | At least 300 eligible development records |
| 7 | Holdout evaluation of at most one chosen method | Explicit approval; protocol ready |

No production change, and no change to `data/valuation_comps.json` or
engine v2.5, happens in any step without separate authorisation.

**Effort (assumption):**
- About 5 minutes of review per relayed row, so about 40 hours for 500
  records.
- Plus second review: per record, or a sampled batch audit for licensed
  feeds (D5).

## 4. Owner decisions

| ID | Decision | Why it blocks |
| --- | --- | --- |
| D1a | Counsel: may public-record facts (SEC filings, court orders) be stored and used for modelling (basis `PUBLIC_RECORD`)? | Workstream A rights |
| D1b | Counsel: is there a documented lawful basis for storing and modelling individually cited, publicly announced sale facts? | Workstream F |
| D2 | Private storage for licensed and holdout data: location, access control, retention | Licensed data cannot sit in the public repository |
| D3 | Approve sending permission requests (B, C) from a Sohadot role address | Outreach is outward-facing |
| D4 | Whether to enquire about NameBio licence terms and cost | Paid; no purchase without approval |
| D5 | Second review: every record, or a batch audit for licensed venue feeds | Review effort |
| D6 | Seller submission programme (public form, privacy notice) | Production change |
| D7 | Approve the human naming-class rules | Stratification and holdout independence |
| D8 | A role contact address for the EDGAR user agent | SEC fair-access rules |

## 5. Draft permission request (not sent)

> Subject: Request to use [source] domain sale reports for internal valuation research
>
> Sohadot (sohadot.com) offers a free domain valuation tool. We are building
> an evidence-based dataset of completed domain sales to test and improve
> our comparable-sales method, with a focus on ordinary sales under
> $100,000.
>
> We ask permission to record, from your published [reports / sales data]
> for [years], the domain, price, currency and venue, and to use them only
> for internal calibration and evaluation of our valuation method. Where you
> hold them, we would also like the date each sale completed and its
> completion status (paid and transferred, as opposed to agreed, pending or
> an unpaid auction result). We record report dates separately and never
> treat them as sale dates.
>
> Some of the sales you publish may originate with marketplaces, brokers or
> other parties. Could you tell us which of this data you are able to
> license to us, and whether any of it remains subject to the rights or
> terms of those upstream sources? If some of it does, please tell us whom
> we should ask.
>
> We would not republish your tables or rows, and would attribute you as a
> source in our methodology notes. We would delete the data on request. We
> would store it privately, separate from our public repository.
>
> Please tell us whether this is acceptable and on what conditions, or
> whether a licence is available.
>
> [Name, role, Sohadot role address]

A reply granting permission becomes the `reference` on each record's
`storage` and `commercial_modelling` rights, with basis type
`WRITTEN_PERMISSION`. It is also recorded in `pipeline.rights_provenance`:
- who granted it (`ORIGINATING_VENUE`, `TRANSACTION_PARTY` or
  `SECONDARY_PUBLISHER`);
- whether upstream rights are confirmed.

A secondary publisher's permission without upstream confirmation leaves the
record blocked (`UPSTREAM_RIGHTS_UNCONFIRMED`).
