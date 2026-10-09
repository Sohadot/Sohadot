# Candidate Data Architecture: Comparable-Sales Pipeline

- **Status:** Sprint 1B candidate design, research only (2026-10-09). Not
  approved for production.
- **Reference implementation:**
  - `scripts/sales_pipeline.py`
  - tests: `tests/test_sales_pipeline.py`
  - generated pilot report: `PILOT_QUALITY_REPORT.md`
- **Builds on:** Transaction Evidence Registry v1, the Source Reliability &
  Rights Matrix and the Independent Holdout Protocol (Sprint 1A).

## 1. Principles

1. **One record per transaction.** Repeat sales are separate records, and
   duplicate reports of one sale merge into a single record.
2. **States are computed, never declared.** The validator recomputes each
   record's state from its evidence, scope, price type, consideration,
   rights and duplicate checks. It fails if the stored state, blockers or
   rejection reasons say anything else.
3. **Fail closed:**
   - `CALIBRATION_ADMITTED` is refused until the owner opens admission.
   - `HOLDOUT_RESERVED` is refused in any public file.
4. **Discovery is not evidence.** Leads never move a record past
   `DISCOVERED`.
5. **Rights decide storage location** as well as use (§6).

## 2. States

```
DISCOVERED ──► SOURCE_REVIEWED ──► ELIGIBLE ──► CALIBRATION_ADMITTED
     │               │                 │
     │               │                 └──► HOLDOUT_RESERVED  (private storage only; terminal)
     └───────────────┴─────────────────┴──► REJECTED          (with reasons; can be reopened)
```

| State | Meaning | Entry condition (computed) |
| --- | --- | --- |
| `DISCOVERED` | A lead or unsourced claim | No directly reviewed source |
| `SOURCE_REVIEWED` | Evidence reviewed, but at least one blocker remains | Reviewed source (Registry v1 §3); no rejection reason |
| `ELIGIBLE` | Meets every calibration condition | Reviewed; completed sale; single domain; exact or rounded price; known date; cash or unknown consideration; USD amount or a recorded FX basis; storage and modelling rights granted; no unresolved duplicate, conflict or bundle suspicion |
| `CALIBRATION_ADMITTED` | In a named calibration batch | `ELIGIBLE`, plus a second review and an admission record (batch, approver, decision reference). **Closed** (`ADMISSION_OPEN = False`). |
| `HOLDOUT_RESERVED` | Set aside for the independent holdout | `ELIGIBLE`, selected under the holdout protocol, stored only in the private manifest. Never in this repository. |
| `REJECTED` | Not a usable comparable | At least one rejection reason |

Allowed transitions are enforced from `state_history`. A record can be
reopened (`REJECTED` → `SOURCE_REVIEWED`, for example) when new evidence
arrives. A reserved holdout record never returns to calibration.

### Rejection reasons and blockers

| Rejection (terminal unless reopened) | Trigger |
| --- | --- |
| `NOT_A_COMPLETED_SALE` | Asking price, auction bid, or auction result not confirmed as paid |
| `PRICE_NOT_DISCLOSED` | Price never disclosed |
| `IMPRECISE_PRICE` | Approximate or lower-bound price |
| `NOT_SINGLE_DOMAIN` | Bundle, domain plus assets, or business |
| `NON_CASH_CONSIDERATION` | Stock, crypto, note or structured consideration |
| `RIGHTS_NOT_PERMITTED` | Storage or modelling expressly not permitted |
| `DUPLICATE_REPORT` | Another record holds the same transaction (`duplicate_of`) |

| Blocker (keeps a record at `SOURCE_REVIEWED` or `DISCOVERED`) | Trigger |
| --- | --- |
| `NO_REVIEWED_SOURCE` | Only leads or unsourced claims |
| `MATERIAL_CONFLICT_UNRESOLVED` | `DISPUTED` evidence |
| `PRICE_TYPE_UNKNOWN` | Not shown to be a completed sale |
| `SCOPE_UNKNOWN` | Not shown to be a single-domain sale |
| `SALE_DATE_UNKNOWN` | No sale date at any precision |
| `FX_BASIS_MISSING` | Non-USD amount with no conversion basis |
| `RIGHTS_NOT_ESTABLISHED` | Storage or modelling right unknown |
| `DUPLICATE_UNRESOLVED` | Same domain as another record, relationship not yet resolved |
| `BUNDLE_SUSPECTED` | Shares a source passage and amount with a different domain |

## 3. Record fields

A pipeline record is a Registry v1 record plus a `pipeline` block. The
fields the Sprint 1B brief requires map as follows:

| Required field | Field(s) |
| --- | --- |
| Domain | `domain` (normalised: lower case, no `www.`, no trailing dot, IDNA) |
| Amount, original currency | `pipeline.original_amount`, `pipeline.original_currency`; `pipeline.amount_usd` with `pipeline.fx_basis` (rate, source, date) |
| Sale date | `sale_date`, `sale_date_precision` (DAY / MONTH / YEAR / UNKNOWN). For relayed reports without a sale date, the report window is recorded as the date at the precision it supports. |
| Reporting date | `report_date` |
| Venue | `venue` (AUCTION, MARKETPLACE, BROKER, PRIVATE, BANKRUPTCY_SALE, CORPORATE_TRANSACTION) plus the venue name in the source |
| Wholesale or retail market side | `market_side` (INVESTOR_TRADE = wholesale; END_USER_ACQUISITION = retail; UNKNOWN) |
| Transaction scope | `transaction_type`, `price_scope`, `bundle` |
| Payment type | `consideration_type` (CASH, CASH_AND_STOCK, CASH_AND_NOTE, CRYPTOCURRENCY, STRUCTURED, …); instalment or lease-to-own recorded in `valuation_caveats` |
| Price type | `pipeline.price_type` (COMPLETED_SALE, ASKING_PRICE, AUCTION_BID, AUCTION_RESULT_UNCONFIRMED, UNDISCLOSED, UNKNOWN) |
| Source, source reliability | principal and `additional_sources` (URL, locator, checked quote ≤300 characters, document SHA-256, review method); `pipeline.source_reliability_tier` (A–E) |
| Reviewed evidence | `evidence_status`, `verification_basis`, `attesting_party`, `settlement_evidence` |
| Data-use rights | `rights.{citation, storage, commercial_modelling, redistribution}`, each with status, basis type, basis and reference (licence or permission ID) |
| Naming class | `pipeline.naming_class` with `naming_class_basis`: `HUMAN_RULES_V1` or `UNASSIGNED`. Engine labels are refused, so the model under test cannot label its own test data. |
| Relationships | `pipeline.duplicate_of`, `pipeline.repeat_sale_of` |
| Review and admission | `pipeline.second_review`, `pipeline.admission`, `pipeline.state_history` |

## 4. Detection rules

| Case | Rule (same normalised domain unless stated) |
| --- | --- |
| Duplicate report | Amounts within 2% and sale dates within 60 days. One record keeps the transaction; the other becomes `DUPLICATE_REPORT`, and its source is kept as an additional source. |
| Repeat sale | Sale dates at least 180 days apart, or at least 2 calendar years apart at year precision. Linked through `repeat_sale_of`. |
| Ambiguous | Anything else, including adjacent years at year precision (a late report of one sale) and records with an unknown date. Blocks both records until a reviewer links them. |
| Bundle suspicion | Different domains citing the same source passage with the same amount |
| Asking prices, bids | Venue listings, "make offer" and "buy now" prices, and auction bids are `ASKING_PRICE` or `AUCTION_BID`. Auction results are `AUCTION_RESULT_UNCONFIRMED` until the venue or a party confirms payment. |
| Undisclosed prices | "Undisclosed" or "seven figures" are `UNDISCLOSED`, with the claim kept in `price_claims` |

Cross-source matching on a relayed report (for example a sale in both a
venue's weekly list and DN Journal) uses the same rules. The venue's own
record becomes the principal source.

## 5. Stratification and the holdout

- **Strata:** price band (< $2.5k, $2.5k–$10k, $10k–$100k, $100k–$1M,
  ≥ $1M), extension group, naming class (human rules), market side, sale
  year, and venue type.
- **Coverage targets** for the first 500 are in FIRST_500_PLAN.
- **Holdout:**
  - It is drawn from `ELIGIBLE` records, under the holdout protocol:
    - at least 150 records;
    - no more than 25% from one source;
    - no overlap with calibration data by domain, repeat sale or
      normalised name;
    - time-forward where practical.
  - Reserved records go only to the private manifest. The public pipeline
    file never contains them; the public report shows only the count.
  - Holdout evaluation does not begin without explicit approval.
- **Independence:** a holdout drawn from the same licensed feed as the
  calibration data is weakly independent at best. The plan therefore needs
  at least two independent source families.

## 6. Storage tiers decided by rights

| Tier | Contents | Where |
| --- | --- | --- |
| Public research | Records whose redistribution right is granted, or which are individually cited public facts held under DEC-2026-10-09-04 (short quote, link, hash) | This repository (`research/`) |
| Private licensed | Records licensed for storage and modelling but not redistribution (e.g. a venue licence) | Private storage outside this repository. Only aggregates, counts and code are published. |
| Private holdout | `HOLDOUT_RESERVED` records and the manifest | Private storage, under the holdout protocol |
| Never stored | Restricted or scraped data, data without a recorded basis | — |

**Owner decision needed:** private storage (location, access control,
backups) is required before any licensed data can be accepted. It is the
same decision the holdout already needs.

## 7. Quality report

`python3 scripts/sales_pipeline.py --write-report` regenerates
`PILOT_QUALITY_REPORT.md`, and CI checks it is current. It reports:
- the funnel: discovered, directly reviewed, rights-cleared,
  calibration-eligible, admitted, rejected, and the holdout count from the
  status file;
- rejection reasons and blockers;
- coverage by price band against target, market side, venue, extension,
  sale decade, naming class and source tier;
- same-domain relationships;
- unresolved evidence: conflicts, duplicates, unknown scope, rights.

**Pilot result:** run on the 49 Sprint 1A registry records, the pipeline
gives:
- 29 directly reviewed;
- 0 rights-cleared;
- 0 eligible;
- 17 rejected (bundles, non-cash, undisclosed or imprecise prices);
- 4 same-domain pairs still to resolve.

## 8. Not yet implemented

- A human-rules naming-class guide (`HUMAN_RULES_V1`) and labelling.
- An FX-rate source and its rights.
- Private storage, the batch admission workflow and the second-reviewer
  roster.
- A pipeline JSON Schema file. Structural checks currently live in the
  validator.
- Holdout sampling from `ELIGIBLE` records and the open holdout controls
  (stratum minimums, chronology, naming labels, evaluation budget).
