# Plan for the First 500 Qualified Transactions

- **Status:** Sprint 1B proposal, research only (2026-10-09). Nothing in this
  plan has been sent, bought, imported or deployed.
- **"Qualified"** means `ELIGIBLE` under the candidate pipeline: reviewed,
  completed, single-domain, cash, exact or rounded price, known date, no
  unresolved duplicate or conflict, and **storage and commercial-modelling
  rights on record**.

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
| Source families | at least 3; no single family above 40% of calibration; holdout no more than 25% per source | Independence |

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

### B. Permission from the leading relay: DN Journal (first request)

- **Why first:**
  - One bi-weekly report lists about 200 sales, about 170 of them under
    $10k.
  - Each row names its venue, so venue diversity can satisfy the
    source-concentration rules.
  - Its own notice makes written consent the route.
- **Ask for:**
  - domain, price, currency and conversion, venue, report window;
  - for reports from 2021 onward;
  - for internal calibration and evaluation of a free valuation tool;
  - with no redistribution of rows, attribution, and deletion on request.
- **Expected yield if granted (assumption):**
  - Suppose 70–85% of rows survive the removal of duplicates, lease-to-own
    deals, bundles, non-completed sales and non-USD rows without an FX
    basis.
  - Then about 3–5 reports would cover the 275 sub-$10k target.
  - The $10k–$100k band (about 25 rows per report) would need about 8–10
    reports.
  - Spreading the reports across 2021–2026 serves the recency and
    diversity targets.
- **Evidence status:** rows are relays of venue reports, so `REPORTED`
  (tier C) unless matched to the venue's own record.

### C. Venue permissions (in parallel with B)

- **Venues:** Sedo, Atom, Flippa, park.io, GoDaddy Auctions / Afternic.
  Each venue's own terms reserve reuse to written permission.
- **Ask for:**
  - completed, non-NDA sales: domain, price, currency, date;
  - market side, or the venue type as a proxy;
  - the same use limits as in B.
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
| 2 | Send permission requests B and C (drafts in §5); log replies as rights references | D3 |
| 3 | Set up private storage for licensed and holdout data | D2 |
| 4 | Ingest permitted data into private storage through the pipeline; second review per D5 | Permission received |
| 5 | Reserve 150+ holdout records privately, from source families separate from calibration | Holdout controls implemented |
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
> for [years], the domain, price, currency, sale or report date and venue,
> and to use them only for internal calibration and evaluation of our
> valuation method.
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
`WRITTEN_PERMISSION`.
