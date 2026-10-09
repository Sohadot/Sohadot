# Sprint 1A Findings and Unresolved Questions

- **Sprint:** 1A, Comparable Sales Evidence Registry & Independent Holdout Foundation
- **Baseline:** `main` at `262b875` (PR #44 merged)
- **Date:** 2026-10-09
- **Production impact:** none. The engine, the published comps, the public
  pages and the engine baseline are unchanged.

## 1. What was built

| Deliverable | Location |
| --- | --- |
| Transaction Evidence Registry v1 (standard) | `docs/valuation-evidence/TRANSACTION_EVIDENCE_REGISTRY_V1.md` |
| Registry data (49 transactions) | `research/valuation-evidence/registry/transactions.v1.json` |
| Structural JSON Schema | `research/valuation-evidence/schema/transaction-evidence.v1.schema.json` |
| Seed-45 investigation (data and generated matrix) | `research/valuation-evidence/investigations/seed-45.v1.json`, `docs/valuation-evidence/SEED_45_INVESTIGATION.md` |
| Source Reliability & Data Rights Matrix | `docs/valuation-evidence/SOURCE_RELIABILITY_AND_RIGHTS_MATRIX.md` |
| Independent Holdout Protocol and status (`NOT_READY`) | `docs/valuation-evidence/INDEPENDENT_HOLDOUT_PROTOCOL.md`, `research/valuation-evidence/holdout/status.v1.json` |
| Validator and matrix renderer | `scripts/validate_evidence_registry.py`, `scripts/render_seed_investigation.py` |
| Tests (33 new) | `tests/test_evidence_registry.py` |

## 2. Investigation results

Every one of the 45 published sales was investigated: a web search per
record, then direct review of primary documents (SEC EDGAR) where they
existed. No paid sources, APIs or scraping of restricted services were used.

**Registry transactions (49).** Repeat sales and a later ai.com sale are
recorded separately, which is why there are more transactions than seed
records.

| Evidence status | Count | Role | Count |
| --- | --- | --- | --- |
| VERIFIED | 5 | CALIBRATION_CANDIDATE | 0 |
| REPORTED | 20 | HOLDOUT_CANDIDATE | 0 |
| DISPUTED | 4 | REFERENCE_ONLY | 18 |
| UNVERIFIED | 20 | EXCLUDED | 11 |
| | | UNDETERMINED | 20 |

**The 45 seed records against the evidence:**
- **18 consistent:** price and year match the evidence, within the precision
  the evidence supports.
- **18 with no evidence found:** these include every sale under $25,000 and
  several six- and seven-figure claims (wallet.com, trading.com, echo.com,
  nova.com, lumen.com, data.ai, veritas.com). For emma.com there is also a
  contrary indicator: MicroStrategy ownership and a $3M asking price around
  2018–2019.
- **3 not domain-only sales:** insurance.com (website business),
  internet.com (business assets) and vacationrentals.com (business).
- **4 price or date conflicts:**
  - ai.com: no 2023 sale at $11M found; a 2025 sale was reported at $70M.
  - agents.ai: reported $125,000, not $400,000.
  - fund.com: the filing gives $9,999,950 for the domain plus other IP; the
    figure is disputed.
  - slots.com: sold in 2010, not 2013.
- **2 with prices never disclosed:** gpt.com and crypto.com.

**Verified (primary documents reviewed):**

| Domain | What is verified |
| --- | --- |
| voice.com | $30.0M cash, 30 May 2019 (MicroStrategy 10-Q and 8-K) |
| clothes.com | $4,864,000, May 2008 (Zappos statements in Amazon 424B3) |
| medicare.com | $4.8M ($4.5M cash plus $0.3M receivables), 31 March 2014 (eHealth 10-Q) |
| insurance.com | $33.0M cash plus a $2.6M note, July 2010 (QuinStreet 10-K): a website-business acquisition, not a domain sale |
| internet.com | $18M subject to adjustment, 30 November 2009 (WebMediaBrands 8-K): business assets, not a domain sale |

**Disputed:**
- crypto.com: the price was never disclosed; estimates run from $5M to $12M.
- fund.com (2007/08): the price covers the domain plus other IP, and its
  legitimacy is contested.
- candy.com: announced at $3M plus a revenue share; the seller later reported
  a $1.7M payout plus equity.
- sex.com (2006): Escom's purchase is variously reported between $11.5M and
  $14M.

## 3. What this means for the published comps

1. **No published comp is fit for calibrating ordinary names today.** The
   records with evidence are mostly multi-million strategic sales
   (`REFERENCE_ONLY`) or not domain-only (`EXCLUDED`). Every sale under
   $25,000 is unsupported.
2. **The public data contains known errors:**
   - slots.com's year;
   - agents.ai's price;
   - ai.com, which matches no documented transaction;
   - three business acquisitions listed as domain sales;
   - gpt.com and crypto.com, which list prices nobody disclosed.

   They were **not changed** in Sprint 1A, as the sprint required. Correcting
   or retiring them is a Sprint 1B decision.
3. The Sprint 0 leave-one-out results (median error about 84×) remain the
   only accuracy measurement. No accuracy claim is made or implied here.

## 4. Source and rights limitations

- Most `REPORTED` records were read through search-result summaries
  (`SEARCH_INDEX_ONLY`), not by opening the article. Reviewing the articles
  directly could upgrade a few to `VERIFIED` (e.g. party announcements), and
  would also catch misattribution.
- Trade-press sources are `PUBLIC_VIEW_CITATION_ONLY`: facts can be cited
  with a link, but archives and charts cannot be bulk-copied.
- The origin of the 18 unsupported seed figures is unknown, so their rights
  are `RESTRICTED_OR_UNKNOWN`. If they came from a sales database, its terms
  may not allow republishing them on sohadot.com.
- Compiled sales databases and court-record systems (PACER) were not used:
  both may involve fees or licences that need owner approval.

## 5. Holdout readiness: NOT_READY

The protocol is complete and enforced by the validator. No independent
transactions exist yet. Freezing a holdout needs:

- independent sources with usable rights;
- private storage outside this public repository;
- at least 150 domain-only transactions spread across price bands.

## 6. Decisions needed from the owner

1. **Correcting the published comps (Sprint 1B).** Approve correcting or
   retiring the records found unsupported or wrong: the 18 with no evidence,
   the 4 conflicts, the 3 business acquisitions and the 2 undisclosed prices.
   Alternatively, keep them visible but labelled.
2. **Data sources and licences.** Decide whether to seek a licence or
   permission from a compiled sales-data provider, or to limit the dataset to
   citable public sources. No purchase was made.
3. **Private holdout storage.** Choose where holdout records will live:
   outside GitHub Pages, with access limited to evaluators.
4. **Second reviewer.** Name who confirms evidence and rights before any
   record becomes a calibration candidate.
5. **Business acquisitions.** Decide whether website or business
   acquisitions (insurance.com, internet.com, vacationrentals.com) are ever
   shown publicly, even as context.

## 7. Unresolved questions

- Did the 18 unsupported seed figures come from a specific database or
  marketplace? If so, which one, and under what terms?
- Was the sex.com 2010 sale formally approved by the bankruptcy court? The
  court record has not been reviewed.
- Was fb.com's $8.5M for fb.com alone, or for "a couple of domain names"?
- Did the privatejet.com stock-and-cash deal ever close, and at what
  realised value?
- Do Qihoo 360's filings (360.com) or Odimo's filings (diamond.com) disclose
  those purchases?

## 8. Recommended Sprint 1B scope

1. Owner decisions in §6, then a public-data correction PR covering the seed
   records in §3.2. Each change must be backed by the registry.
2. Direct review of the `REPORTED` sources and the primary-document leads in
   §7.
3. Build a candidate pool of domain-only sales under $100,000 from citable or
   licensed sources. Split it into calibration and a frozen private holdout
   under the protocol.
4. Only then, any methodology change, evaluated once against the frozen
   holdout. The landmark sales stay `REFERENCE_ONLY`.
