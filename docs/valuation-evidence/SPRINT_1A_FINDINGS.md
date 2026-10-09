# Sprint 1A Findings and Unresolved Questions

- **Sprint:** 1A, Comparable Sales Evidence Registry & Independent Holdout Foundation
- **Baseline:** `main` at `262b875` (PR #44 merged)
- **Date:** 2026-10-09 (revised the same day after the independent review)
- **Production impact:** none. The engine, published comps, public pages and
  engine baseline are unchanged.

## 1. What was built

| Deliverable | Location |
| --- | --- |
| Transaction Evidence Registry v1 (standard) | `docs/valuation-evidence/TRANSACTION_EVIDENCE_REGISTRY_V1.md` |
| Registry data (49 transactions, version 1.1.0) | `research/valuation-evidence/registry/transactions.v1.json` |
| Structural JSON Schema | `research/valuation-evidence/schema/transaction-evidence.v1.schema.json` |
| Seed-45 investigation (data and generated matrix) | `research/valuation-evidence/investigations/seed-45.v1.json`, `docs/valuation-evidence/SEED_45_INVESTIGATION.md` |
| Source Reliability & Data Rights Matrix | `docs/valuation-evidence/SOURCE_RELIABILITY_AND_RIGHTS_MATRIX.md` |
| Independent Holdout Protocol and status (`NOT_READY`) | `docs/valuation-evidence/INDEPENDENT_HOLDOUT_PROTOCOL.md`, `research/valuation-evidence/holdout/status.v1.json` |
| Validator and matrix renderer | `scripts/validate_evidence_registry.py`, `scripts/render_seed_investigation.py` |
| Tests | `tests/test_evidence_registry.py` |

## 2. Investigation results

**Method.**
1. A web search per seed sale located candidate sources.
2. Every source used as evidence was then fetched and its quoted passage
   checked against the raw document text. The registry records 40 such
   passages, each with a locator and a SHA-256 of the retrieved bytes.
3. Search summaries are kept only as leads (13 recorded).

No paid sources, APIs or scraping of restricted services were used.

**Registry transactions (49):**

| Evidence status | Count | Role | Count |
| --- | --- | --- | --- |
| VERIFIED | 7 | CALIBRATION_CANDIDATE | 0 |
| REPORTED | 21 | HOLDOUT_CANDIDATE | 0 |
| DISPUTED | 1 | REFERENCE_ONLY | 18 |
| UNVERIFIED | 20 | EXCLUDED | 11 |
| | | UNDETERMINED | 20 |

**The 45 seed records against the reviewed evidence:**

| Result | Records |
| --- | --- |
| Consistent | 16 |
| No evidence found | 18 |
| Not a domain-only sale | 6 |
| Price or date conflict | 3 |
| Price never disclosed | 2 |

- **Not domain-only:**
  - insurance.com (website business)
  - internet.com (business assets)
  - vacationrentals.com (business)
  - fund.com (24 domains and a trademark)
  - fb.com ("a couple of domain names")
  - diamond.com (domain plus associated IP)
- **Price or date conflicts:**
  - ai.com: no reviewed support for $11M/2023; the documented sale is $70M,
    closed in 2025.
  - agents.ai: $125,000, not $400,000.
  - slots.com: sold May 2010, not 2013.
- **Price never disclosed:** gpt.com, crypto.com.

**Verified from primary documents read in raw text:**

| Domain | What is verified | Source |
| --- | --- | --- |
| voice.com | $30.0M cash, 2019-05-30 | MicroStrategy 10-Q, 8-K |
| clothes.com | $4,864,000, 2008-05 | Zappos statements in Amazon 424B3 |
| medicare.com | $4.8M ($4.5M cash + $0.3M receivables), 2014-03-31 | eHealth 10-Q |
| insurance.com | Website business, $33.0M cash + $2.6M note, 2010-07 | QuinStreet 10-K |
| internet.com | Business assets, $18M subject to adjustment, 2009-11-30 | WebMediaBrands 8-K |
| fund.com | Bundle of 24 domains and one trademark, $9,999,950 in total, 2007. No amount attributed to fund.com, and its economic value stays disputed. | Fund.com Inc. 10-Q/A |
| ai.com | $70M, 2025. Caveats: the broker's own statement, the USD value of crypto consideration, closing date undisclosed. | Broker of record's release (PR Newswire, 2026-02-09) |

**Disputed:** sex.com's earlier purchase. The Register gives $12M–$14M in
2006; DN Journal gives about $12M in cash and stock in January 2005.

## 3. What this means for the published comps

1. **No published comp is fit for calibrating ordinary names today.**
   - Every sale under $25,000 is unsupported.
   - The records with evidence are strategic landmark sales, bundles or
     business acquisitions.
   - No record has established storage or modelling rights.
2. **Known errors in the public data:**
   - slots.com's year;
   - agents.ai's price;
   - ai.com, which matches no reviewed transaction;
   - six non-domain-only transactions shown as single-domain sales;
   - two undisclosed prices shown as facts.

   None was changed in Sprint 1A. Correcting or retiring them is a Sprint 1B
   decision.
3. **No accuracy claim** is made. The Sprint 0 leave-one-out results remain
   the only accuracy measurement.

## 4. Source and rights limitations

- **Rights:** storage, commercial modelling and redistribution rights are
  `NOT_ESTABLISHED` for all 49 transactions. This blocks any calibration use
  until the owner documents a lawful basis or obtains permission.
- **Document hashes:** they identify what was reviewed. Web pages change, so
  a later fetch may hash differently.
- **Not consulted:** compiled sales databases and court records (PACER).
- **One-reviewer verification:** a second reviewer is required before any
  calibration use.

## 5. Holdout readiness: NOT_READY

- **Enforced (13 controls):** fail-closed FROZEN validation (no FROZEN status
  is accepted without the private manifest), hash, record count of at least
  150, eligibility, source concentration, and overlap with the registry,
  published seed and comps, repeat sales and normalised name variants.
- **NOT_IMPLEMENTED (7 controls), marked in the status file and the protocol
  §9:** stratum minimums, chronological split, independent naming-class
  labels, evaluation budget, aggregate-only access, the backtest's
  second-level-name check, and Pages-artifact exclusion (separate draft PR).
- **No independent data exists yet.**

## 6. Remediation after independent review (R1–R6)

| Item | Change |
| --- | --- |
| R1 Provenance | Every evidence source must be read directly, with an https URL, access date, locator, quote checked against raw text, review method and document hash. Unchecked automated extraction is rejected. |
| R2 fund.com | Re-examined using the 10-Q/A (filed 2009-11-30): 24 domains and one trademark, $9,999,950, 2007. Recorded as a VERIFIED bundle with `price_scope: BUNDLE_TOTAL`, unallocated and EXCLUDED. The disputed economic value moved to `valuation_caveats`. insurance.com stays a website-business acquisition (cash plus note). |
| R3 Reported evidence | All 23 previously search-only REPORTED/DISPUTED records were re-reviewed from original sources, so none had to be downgraded. Search summaries remain as leads. Precise dates added: agents.ai 2023-07-13; slots.com 2010-05-13; ai.com release 2026-02-09, first reports 2026-02-06, and closing year 2025 with April unconfirmed. |
| R4 Rights | Four separate rights, each with its own basis. Public accessibility cannot grant storage, modelling or redistribution rights. Unknown rights block calibration. |
| R5 Holdout | Fail-closed FROZEN validation. Private manifest checks (outside the repository, hash, count, eligibility, source share, overlap with seed, comps, registry and name variants). Repository-wide manifest detection. A controls map that cannot claim more than the code enforces. |
| R6 Tests | Adversarial cases for every confirmed weakness (see the PR). |

**Corrections caused by direct review:**
- **candy.com:** previously DISPUTED from a search summary ("$1.7M payout vs
  $3M"). The reviewed 2023 article shows $3M cash plus equity, with $1.7M
  coming from a later share sale. Now REPORTED, cash and stock, EXCLUDED for
  its non-cash component.
- **crypto.com:** previously DISPUTED. The reviewed source reports the
  transaction with an unconfirmed price. Now REPORTED with the price
  undisclosed.
- **sex.com 2006:** previously DISPUTED on a Sedo $11.5M figure seen only in
  search results. Now DISPUTED on reviewed sources: price $12M–$14M, and the
  date 2005 vs 2006.
- **Bundles:** fb.com and diamond.com are now recorded as bundles, matching
  their sources' wording.
- **ai.com 2025:** now VERIFIED from the broker of record's release, with
  caveats.
- **hotels.com:** the "2001 vs 2002" date conflict came only from search
  results. It was dropped because the reviewed source says 2001.

## 7. Decisions needed from the owner

1. **Correcting the published comps (Sprint 1B):** correct or retire the
   records in §3.2, or keep them visible with labels.
2. **Rights:** document a lawful basis, or obtain permission or licences,
   for storage and modelling. Alternatively, keep the dataset citation-only.
3. **Private holdout storage and evaluator access.**
4. **Second reviewer:** who confirms evidence and rights before calibration.
5. **ai.com 2025:** the standard treats a broker of record's own release as
   primary evidence. Confirm this is acceptable, or require independent
   corroboration of the price.
6. **Website and business acquisitions:** whether they are ever shown
   publicly, even as context.

## 8. Unresolved questions

- Where did the 18 unsupported seed figures come from, and under what terms?
- Did the bankruptcy court approve the 2010 sex.com sale? The order has not
  been reviewed.
- What was the true date and price of Escom's earlier sex.com purchase?
- Did the privatejet.com cash-and-stock deal close, and at what value?
- Do Qihoo 360's (360.com) or Odimo's (diamond.com) filings disclose the
  purchase?
- In what year did HomeAway acquire VacationRentals.com? The reviewed source
  does not say.

## 9. Recommended Sprint 1B scope

1. Owner decisions in §7.
2. A public-data correction PR, with each change backed by the registry.
3. Build a candidate pool of domain-only sales under $100,000 with
   established rights. Split it into calibration data and a frozen private
   holdout, and implement the `NOT_IMPLEMENTED` controls first.
4. Only then, any methodology change, evaluated once against the frozen
   holdout.
