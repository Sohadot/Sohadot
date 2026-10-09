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
| `ELIGIBLE` | Meets every calibration condition | Reviewed; `COMPLETED_SALE` **with explicit completion evidence**; single domain; exact or rounded price; a sale date **stated by the evidence** (not a report date or window); cash or unknown consideration; USD amount or a recorded FX basis; storage and modelling rights granted **by a party able to grant them** (§3.3); no unresolved duplicate, conflict or bundle suspicion |
| `CALIBRATION_ADMITTED` | In a named calibration batch | `ELIGIBLE`, plus a second review and an admission record (batch, approver, decision reference). **Closed** (`ADMISSION_OPEN = False`). |
| `HOLDOUT_RESERVED` | Set aside for the independent holdout | `ELIGIBLE`, selected under the holdout protocol, stored only in the private manifest. Never in this repository. |
| `REJECTED` | Not a usable comparable | At least one rejection reason |

Allowed transitions are enforced from `state_history`. A record can be
reopened (`REJECTED` → `SOURCE_REVIEWED`, for example) when new evidence
arrives. A reserved holdout record never returns to calibration.

### Rejection reasons and blockers

| Rejection (terminal unless reopened) | Trigger |
| --- | --- |
| `NOT_A_COMPLETED_SALE` | Asking price, auction bid, or an auction result whose winner did not pay (`AUCTION_RESULT_UNPAID`) |
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
| `PRICE_TYPE_UNKNOWN` | Price not yet classified (§3.1) |
| `COMPLETION_NOT_EVIDENCED` | Announced agreement, reported price or unconfirmed auction result; or `COMPLETED_SALE` without a valid completion-evidence basis |
| `SCOPE_UNKNOWN` | Not shown to be a single-domain sale |
| `SALE_DATE_UNKNOWN` | No sale date stated by the evidence (`sale_date_basis` is not `EXPLICIT_IN_SOURCE`). A report date or reporting window never satisfies it. |
| `FX_BASIS_MISSING` | Non-USD amount with no conversion basis |
| `RIGHTS_NOT_ESTABLISHED` | Storage or modelling right unknown |
| `UPSTREAM_RIGHTS_UNCONFIRMED` | Rights granted by a secondary publisher (or with no named grantor), without confirmation that rights originating with the venue or other upstream owner are covered |
| `DUPLICATE_UNRESOLVED` | Same domain as another record, relationship not yet resolved |
| `BUNDLE_SUSPECTED` | Shares a source passage and amount with a different domain |

## 3. Record fields

A pipeline record is a Registry v1 record plus a `pipeline` block. The
fields the Sprint 1B brief requires map as follows:

| Required field | Field(s) |
| --- | --- |
| Domain | `domain` (normalised: lower case, no `www.`, no trailing dot, IDNA) |
| Amount, original currency | `pipeline.original_amount`, `pipeline.original_currency`; `pipeline.amount_usd` with `pipeline.fx_basis` (rate, source, date) |
| Sale date | `sale_date`, `sale_date_precision` (DAY / MONTH / YEAR / UNKNOWN), and `pipeline.sale_date_basis`: `EXPLICIT_IN_SOURCE` or `NOT_ESTABLISHED` (§3.2) |
| Reporting date and window | `report_date` (publication date); `pipeline.reporting_window` {start, end, source} for reports that cover a period. Both are kept apart from the sale date. |
| Venue | `venue` (AUCTION, MARKETPLACE, BROKER, PRIVATE, BANKRUPTCY_SALE, CORPORATE_TRANSACTION) plus the venue name in the source |
| Wholesale or retail market side | `market_side` (INVESTOR_TRADE = wholesale; END_USER_ACQUISITION = retail; UNKNOWN) |
| Transaction scope | `transaction_type`, `price_scope`, `bundle` |
| Payment type | `consideration_type` (CASH, CASH_AND_STOCK, CASH_AND_NOTE, CRYPTOCURRENCY, STRUCTURED, …); instalment or lease-to-own recorded in `valuation_caveats` |
| Price type and completion | `pipeline.price_type` and `pipeline.completion_evidence` {basis, locator, quote} (§3.1) |
| Source, source reliability | principal and `additional_sources` (URL, locator, checked quote ≤300 characters, document SHA-256, review method); `pipeline.source_reliability_tier` (A–E) |
| Reviewed evidence | `evidence_status`, `verification_basis`, `attesting_party`, `settlement_evidence` |
| Data-use rights | `rights.{citation, storage, commercial_modelling, redistribution}`, each with status, basis type, basis and reference (licence or permission ID); `pipeline.rights_provenance` {granted_by_role, grantor, upstream_origin, upstream_rights_confirmed} (§3.3) |
| Source family and relay | `pipeline.source_family` (the originating data owner: venue, party, filer or court) and `pipeline.relay_publisher` (the publisher that relayed it, if any) (§5) |
| Naming class | `pipeline.naming_class` with `naming_class_basis`: `HUMAN_RULES_V1` or `UNASSIGNED`. Engine labels are refused, so the model under test cannot label its own test data. |
| Relationships | `pipeline.duplicate_of`, `pipeline.repeat_sale_of` |
| Review and admission | `pipeline.second_review`, `pipeline.admission`, `pipeline.state_history` |

### 3.1 Price type and completion evidence

A stated price, even in a reviewed `VERIFIED` or `REPORTED` record, is not
evidence that the sale closed.

| `price_type` | Meaning | Effect |
| --- | --- | --- |
| `COMPLETED_SALE` | The transaction closed | Eligible only with `completion_evidence` (below); otherwise blocked, and the validator fails the record |
| `ANNOUNCED_AGREEMENT` | Agreed or pending; closing not shown | Blocked: `COMPLETION_NOT_EVIDENCED` |
| `REPORTED_PRICE` | A price is reported; completion not stated | Blocked: `COMPLETION_NOT_EVIDENCED` |
| `AUCTION_RESULT_UNCONFIRMED` | Auction closed; payment not confirmed | Blocked: `COMPLETION_NOT_EVIDENCED` |
| `AUCTION_RESULT_UNPAID` | Winner did not pay | Rejected: `NOT_A_COMPLETED_SALE` |
| `AUCTION_BID`, `ASKING_PRICE` | Bid or list price | Rejected: `NOT_A_COMPLETED_SALE` |
| `UNDISCLOSED` | Price never disclosed | Rejected: `PRICE_NOT_DISCLOSED` |
| `UNKNOWN` | Not classified | Blocked: `PRICE_TYPE_UNKNOWN` |

`completion_evidence.basis` must be one of the following, with a locator
and a checked quote:
- `SETTLEMENT_IN_FILING_OR_COURT_RECORD`
- `VENUE_RECORD_OF_COMPLETION`
- `PARTY_CONFIRMED_COMPLETION`
- `SOURCE_STATES_COMPLETED`

Registry v1 never recorded completion, so the pilot maps every priced
registry record to `REPORTED_PRICE`, not `COMPLETED_SALE`.

### 3.2 Sale-date provenance

- A sale date counts only when the evidence states it
  (`sale_date_basis: EXPLICIT_IN_SOURCE`).
- A publication date (`report_date`) or a reporting window
  (`reporting_window`) is never copied into `sale_date`. When only those
  exist, `sale_date` stays null and the record is blocked with
  `SALE_DATE_UNKNOWN`.
- A sale date equal to a window boundary needs a `sale_date_note` citing
  the explicit date; otherwise the validator fails the record.
- Registry v1 did not record where its dates came from, so the pilot treats
  every registry date as `NOT_ESTABLISHED` until re-reviewed.

### 3.3 Rights provenance

| `granted_by_role` | Can clear storage and modelling? |
| --- | --- |
| `ORIGINATING_VENUE`, `TRANSACTION_PARTY`, `PUBLIC_RECORD` | Yes, with a named grantor |
| `SECONDARY_PUBLISHER` | Only with `upstream_rights_confirmed: true` |
| `NONE` | No |

A secondary publisher, for example a trade-press relay, can grant rights in
its own compilation. That permission does not establish rights that
originate with the marketplace, broker or other upstream data owner.
Confirmation may come from the publisher's own warranty of upstream rights,
or from the upstream owner directly. Either way it is recorded as a
reference before the record can clear.

## 4. Detection rules

| Case | Rule (same normalised domain unless stated) |
| --- | --- |
| Duplicate report | Amounts within 2% and sale dates within 60 days. One record keeps the transaction; the other becomes `DUPLICATE_REPORT`, and its source is kept as an additional source. |
| Repeat sale | Sale dates at least 180 days apart, or at least 2 calendar years apart at year precision. Linked through `repeat_sale_of`. |
| Ambiguous | Anything else, including adjacent years at year precision (a late report of one sale) and records with an unknown date. Blocks both records until a reviewer links them. |
| Bundle suspicion | Different domains citing the same source passage with the same amount |
| Asking prices, bids, agreements | Venue listings, "make offer" and "buy now" prices, and auction bids are `ASKING_PRICE` or `AUCTION_BID`. Auction results are `AUCTION_RESULT_UNCONFIRMED` until the venue or a party confirms payment, and `AUCTION_RESULT_UNPAID` if the winner defaults. "Agreed to sell", "in escrow" and "pending" are `ANNOUNCED_AGREEMENT`. |
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
- **Source family vs reported venue diversity:**
  - A source family is the originating data owner: a venue, a party, a
    filer or a court.
  - A relay that names many venues (for example a trade-press sales
    report) adds venue diversity, but every row shares the relay's
    selection, transcription errors and rights position.
  - Rows from five venues received through one relay are therefore **one**
    relay path, not five independent families.
- **What the quality report shows:**
  - the largest source-family share;
  - the largest relay share;
  - the unknown-origin share.
- **Holdout design:**
  - It should use at least two families obtained directly, not only
    through the relay used for calibration.
  - Concentration should be judged on the family and on the relay.
  - The existing holdout validator's 25% limit applies per source as
    recorded. Counting by family and relay is a design rule here; it is not
    yet an enforced control.

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
- price type and sale-date basis;
- source families and relay publishers, with independence shares;
- unresolved evidence: conflicts, duplicates, unknown scope, rights,
  completion and sale dates.

**Pilot result:** run on the 49 Sprint 1A registry records, the pipeline
gives:
- 29 directly reviewed;
- 0 rights-cleared;
- 0 eligible;
- 17 rejected (bundles, non-cash, undisclosed or imprecise prices);
- 4 same-domain pairs still to resolve;
- 25 priced records with completion not evidenced (all `REPORTED_PRICE`);
- 49 records whose sale date is not established by evidence.

## 8. Not yet implemented

- A human-rules naming-class guide (`HUMAN_RULES_V1`) and labelling.
- An FX-rate source and its rights.
- Private storage, the batch admission workflow and the second-reviewer
  roster.
- A pipeline JSON Schema file. Structural checks currently live in the
  validator.
- Holdout sampling from `ELIGIBLE` records and the open holdout controls
  (stratum minimums, chronology, naming labels, evaluation budget).
