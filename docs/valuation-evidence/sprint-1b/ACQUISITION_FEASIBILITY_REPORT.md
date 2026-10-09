# Sprint 1B: Comparable-Sales Acquisition Feasibility Report

- **Status:** first deliverable of Sprint 1B. Research only (2026-10-09).
- **Production unchanged:**
  - Engine v2.5, `data/valuation_comps.json`, the published sales and the
    live valuation output are untouched.
  - Nothing was merged or deployed.
  - Holdout evaluation has not begun.
- **Baseline:** `main` at `65a9681` (Sprint 1A merged).

## Contents

| Deliverable | Document |
| --- | --- |
| Acquisition feasibility (this report) | `ACQUISITION_FEASIBILITY_REPORT.md` |
| Source-rights matrix | `SOURCE_ACQUISITION_AND_RIGHTS_MAP.md` |
| Candidate data architecture | `DATA_PIPELINE_ARCHITECTURE.md`; code `scripts/sales_pipeline.py` |
| Baseline engine-bias assessment | `ENGINE_BIAS_BASELINE.md`; code `scripts/assess_comparable_selection.mjs`; data `research/valuation-evidence/sprint-1b/engine-bias-baseline.v1.json` |
| Plan for the first 500 qualified transactions | `FIRST_500_PLAN.md` |
| Reproducible quality report (pilot on the 49 registry records) | `PILOT_QUALITY_REPORT.md` (generated) |

## 1. Verdict

1. **Discovery is easy.** Trade press lists thousands of ordinary sales a
   year: DN Journal alone shows about 170 sub-$10k sales per bi-weekly
   report.
2. **Lawful bulk use is not available today.**
   - Every source with substantial sub-$100k coverage reserves reuse to
     written permission or a licence, or has terms that could not be read.
     This covers DN Journal, NameBio, Sedo, Atom, Flippa, park.io, Dynadot
     and GoDaddy/Afternic.
   - The only clearly reusable sources, SEC filings and court orders, give
     tens of mostly large or bundled deals.
3. **500 qualified transactions are feasible only through permission or a
   licence.**
   - One permission from DN Journal, or two or three venue permissions,
     could supply the first 500 with stratified coverage.
   - The holdout needs another 150 or more from independent source
     families.
   - Without permission, the realistic ceiling is tens of records.
4. **Larger stages:** 2,000 needs at least one bulk permission. 10,000+
   needs a licence at aggregator or venue scale.
5. **Today's count:** the Sprint 1A registry, run through the candidate
   pipeline, yields **0 eligible records**:
   - 49 records;
   - 29 directly reviewed;
   - 0 rights-cleared;
   - 17 rejected.

   Its sales are landmark deals, and no record has storage or modelling
   rights.

## 2. Engine bias: why expansion matters, and why it is not enough

Detailed in `ENGINE_BIAS_BASELINE.md`.

- **The comps set the estimate.**
  - 91.6% of 805 probe names use comps.
  - The median effect is about ×10.7.
  - 55.9% of names are moved up by 10× or more.
  - Median retail mid is $48,269 with comps and $4,343 without.
  - Cause: 28 of the 45 comps are $1M+ landmark sales, and dictionary or
    keyword names share a class with them.
- **The 4-result limit and the price-descending tie-breaker.**
  - The tie-breaker decides the cut for 53.8% of probes today, with a small
    effect, because the pool is uniformly expensive.
  - In synthetic expansion the effect grows with dataset size: selected
    comps sit about ×2.2 above the eligible median at 500 comps, and about
    ×9 at 10,000.
  - A neutral tie-breaker stays near zero.
- **Expansion alone does not fix it.**
  - With synthetic ordinary sales added to the 45 comps, landmarks still
    fill 8–13% of selected comps under v2.5.
  - The typical estimate also drifts upward as the pool grows.
  - The pool (evidence- and rights-checked, landmarks kept as reference
    only) and the selection rule both need testing.
- **Leave-one-out on the 45 comps:**
  - landmarks underestimated by a median of about 160×;
  - the 8 sales under $10k overestimated by a median of about 2.7×.

## 3. Rights map: summary

Detailed in `SOURCE_ACQUISITION_AND_RIGHTS_MAP.md`; ten key clauses were
re-checked against the live pages.

| Source group | Discovery | Bulk use for calibration |
| --- | --- | --- |
| DN Journal | Yes (best index; names the venue per row) | Written consent required ("No … content of any kind may be copied … without expressed written consent") |
| NameBio | Not consulted beyond the API terms | Paid licence plus written permission, even for a free product |
| Sedo, Atom, Flippa, park.io, Dynadot | Some public facts | Prohibited or permission-only. Sedo names "competitor analysis" as a prohibited use. |
| GoDaddy Auctions / Afternic | No public sold data | Terms unreadable (403); partnership needed |
| Trade press (DNW, DomainInvesting, TheDomains and others) | Yes | Discovery and manual citation only. DNW bars automated access without permission. |
| SEC EDGAR, court orders | Yes | Reusable (SEC: "may be copied or further distributed … without the SEC's permission"); low volume |
| Kaggle "open" sales datasets | — | Declared open licences, but provenance undocumented, so rights unknown |
| Wikipedia list | Leads | CC BY-SA; only $3M+ sales |

## 4. Candidate architecture: summary

Detailed in `DATA_PIPELINE_ARCHITECTURE.md`.

- **States:** `DISCOVERED → SOURCE_REVIEWED → ELIGIBLE → CALIBRATION_ADMITTED`,
  plus `REJECTED` and private-only `HOLDOUT_RESERVED`.
- **States are computed** from evidence, scope, price type, consideration,
  rights and duplicate checks. The validator rejects any record whose
  declared state overstates the evidence.
- **Fail-closed:**
  - admission is closed until the owner opens it;
  - holdout records are refused in public files;
  - engine labels cannot serve as naming classes.
- **Detection:** duplicate reports, repeat sales, ambiguous same-domain
  pairs, suspected bundles, asking prices, bids, unconfirmed auctions and
  undisclosed prices.
- **Storage follows rights.** Licensed data without a redistribution right
  must live in private storage, never in this public repository. Only code,
  aggregates and counts are published.
- **Quality report:** funnel, rejection reasons, blockers, and coverage by
  price band, market side, venue, extension, decade, naming class and
  source tier. Regenerated and checked in CI.

## 5. Plan: summary

Detailed in `FIRST_500_PLAN.md`.

- **Target:** about 650 eligible records (500 for calibration and
  development, 150+ held out privately), stratified by price band (275
  under $10k), extension (30% other than .com), market side, naming class
  and recency, from at least three source families.
- **Workstreams:**
  - A: primary public records;
  - B: DN Journal permission (first request);
  - C: venue permissions;
  - D: NameBio licence enquiry, only if approved;
  - E: seller-consented submissions, later;
  - F: individually cited facts, only on counsel's basis.
- **Pilot:** compare v2.5 with candidate methods C1–C6 on development data
  once 300 or more eligible records exist. No production algorithm is
  selected before the holdout is frozen.

## 6. Decisions needed from the owner

D1–D8 in `FIRST_500_PLAN.md` §4:
- counsel on public-record and individual-fact bases;
- private storage;
- approval to send permission requests, with a draft provided;
- NameBio enquiry;
- the second-review model;
- the seller programme;
- naming-class rules;
- an EDGAR role contact address.

## 7. What was not done

- No scraping, sign-ups, purchases, licence requests or outreach.
- No new sale was imported. The pilot uses only the 49 existing registry
  records.
- No change to the engine, the comps data, published pages or the holdout
  status. Holdout evaluation has not begun.
