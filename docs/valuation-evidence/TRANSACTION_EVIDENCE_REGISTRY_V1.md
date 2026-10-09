# Transaction Evidence Registry v1

- **Status:** Research standard (Sprint 1A, revised after independent review). Not used by the production valuation engine.
- **Schema version:** `transaction-evidence/v1` (registry data version 1.2.0)
- **Files:**
  - `research/valuation-evidence/registry/transactions.v1.json`: the registry
  - `research/valuation-evidence/schema/transaction-evidence.v1.schema.json`: structural JSON Schema
  - `scripts/validate_evidence_registry.py`: enforces every cross-field rule below
  - `research/valuation-evidence/investigations/seed-45.v1.json`: investigation of the 45 published comps

## 1. Unit of record: the transaction

A record is one sale of a domain, not a domain name. Each sale gets its own
`SOH-TX-NNNNNN` identifier, which is never renumbered or reused.

- **Repeat sales** of one domain are separate records. Examples: `chat.com`
  in 2023 and 2024, `fund.com` in 2007 and 2019, `sex.com` in 2005/2006 and
  2010.
- **Duplicates:** two records with the same domain, date and price are
  rejected.
- **Unknown facts are null.** An unsourced figure appears only in
  `price_claims`, labelled `UNSOURCED_CLAIM`.

## 2. Price scope

`price_scope` states what the price paid for. A bundle or business price is
never one domain's price.

| `transaction_type` | Required `price_scope` |
| --- | --- |
| `DOMAIN_ONLY` | `SINGLE_DOMAIN` |
| `MULTIPLE_DOMAINS`, `DOMAIN_PLUS_ASSETS` | `BUNDLE_TOTAL`, with `bundle: {domain_count, other_assets, allocation: NOT_ALLOCATED}` |
| `WEBSITE_BUSINESS`, `BUSINESS_ASSETS` | `BUSINESS_TOTAL` |
| `UNKNOWN` | any |

Example: `fund.com`'s documented 2007 transaction bought 24 domain names and
one trademark for $9,999,950 in total. It is recorded as a verified bundle,
with no amount attributed to fund.com.

## 3. Provenance: what counts as a source

The **principal source** and every entry in `additional_sources` must have
been read directly. The validator requires:

| Field | Requirement |
| --- | --- |
| `source_access_method` | `DOCUMENT_REVIEWED` |
| `review_method` | `RAW_TEXT_CHECKED`, or `TOOL_EXTRACT_CHECKED_AGAINST_RAW`. Automated extraction alone (`TOOL_EXTRACT_UNCHECKED`) is insufficient. |
| `source_url` | Non-empty `https://` URL |
| `source_accessed_at` | ISO date |
| `document_locator` | Note, section, headline or paragraph that holds the statement |
| `checked_quote` | Verbatim text, checked against the retrieved document |
| `document_sha256` | SHA-256 of the bytes retrieved at review time. Web pages change, so the hash identifies what was reviewed; it does not guarantee a later fetch matches. |

**Leads.** Search-index summaries and unread pointers are stored only in
`leads`, with name, URL, type, date observed and a note. Leads are never
evidence. When a record is downgraded, its earlier sources are kept as leads,
so no provenance is lost.

**Absence of access.** Not finding or not reaching a source never shows that
a transaction did not happen. Such records stay `UNVERIFIED`.

**Report date.** `report_date` is the publication date of the principal
reviewed source. Earlier reports are listed in `additional_sources` with
their own `published_date`. A report cannot predate the sale; dates are
compared at the finest precision both share, so 2020-03-01 vs 2020-03-15 is
rejected.

## 4. Evidence status

Evidence status describes the evidence for the *transaction as recorded*. It
says nothing about whether the price is a good comparable.

| Status | Requirements |
| --- | --- |
| **VERIFIED** | Principal source is primary: `REGULATORY_FILING`, `COURT_RECORD`, `PARTY_ANNOUNCEMENT` (buyer, seller or broker of record) or `MARKETPLACE_RECORD`. It is reviewed as in §3. The price is `EXACT`, `ROUNDED` or `STATED_SUBJECT_TO_ADJUSTMENT`. The checked quote names the domain and states a figure. `verified_at` and a `verification_basis` are recorded. No material conflict. |
| **REPORTED** | Reviewed principal source of a reportable class: primary, `TRADE_PUBLICATION` or `GENERAL_NEWS`. Never `TERTIARY_REFERENCE`, `AGGREGATOR_DATABASE` or a search summary. No material conflict. |
| **DISPUTED** | Reviewed source, plus at least one **material** conflict about the transaction itself (price, date or consideration). |
| **UNVERIFIED** | No reviewed principal source. Leads may be listed. |

**Who vouches for a VERIFIED record.** Every `VERIFIED` record states
`attesting_party` and `settlement_evidence`:

| Principal source | `settlement_evidence` | `attesting_party` |
| --- | --- | --- |
| Regulatory filing or court record | `REGULATED_FILING_OR_COURT_RECORD` | `BUYER`, `SELLER` or `COURT` |
| Party announcement or marketplace record | `PARTY_ATTESTATION_ONLY` | `BUYER`, `SELLER`, `BROKER` or `VENUE` |

- A party's own announcement is an **attestation, not independently confirmed
  settlement**. Its `verification_basis` must say so.
- Non-`VERIFIED` records carry `NONE` / `NOT_ESTABLISHED`.
- Examples: ai.com (2025) and sex.com (2010) are `VERIFIED` on broker
  attestation only.

**Conflicts vs valuation caveats.**
- `conflicts` are contradictions about the transaction itself.
- `valuation_caveats` are limits on what the price says about value: bundles,
  non-cash consideration, commissions, disputed arm's-length pricing.
- Caveats never change the evidence status. A transaction can be `VERIFIED`
  while its economic valuation is disputed, as with fund.com.

**Limitations.**
- Primary documents exist mostly for public-company deals, which biases
  `VERIFIED` towards large strategic sales.
- Party announcements are self-interested. The consideration type and
  caveats are recorded so readers can weigh them.
- Verification is a point-in-time review by one reviewer. A second reviewer
  is required before any record becomes a calibration candidate (§7).

## 5. Rights

Four independent rights. Each has its own `status`, `basis_type`, `basis`
and, where needed, `reference`.

| Right | Covers |
| --- | --- |
| `citation` | Citing individual facts with attribution and a link |
| `storage` | Systematic storage of the record in Sohadot datasets |
| `commercial_modelling` | Using the record to build, calibrate or evaluate commercial models |
| `redistribution` | Publishing or sharing the data onwards |

| `status` | `basis_type` |
| --- | --- |
| `PERMITTED`, `PERMITTED_WITH_CONDITIONS`, `NOT_PERMITTED`, `NOT_ESTABLISHED` | `PUBLIC_RECORD`, `PUBLIC_FACT_CITATION`, `LICENSE`, `WRITTEN_PERMISSION`, `DOCUMENTED_LAWFUL_BASIS`, `NONE` |

Rules enforced:
- A granted right needs a basis other than `NONE`.
- `LICENSE`, `WRITTEN_PERMISSION` and `DOCUMENTED_LAWFUL_BASIS` need a
  `reference`. A documented lawful basis can qualify; a paid licence is not
  required for individual publicly disclosed facts.
- Storage, modelling and redistribution can never be granted on
  `PUBLIC_FACT_CITATION`. Public accessibility is not permission.
- Unknown (`NOT_ESTABLISHED`) or restricted storage or modelling rights block
  calibration.

**Current state:**
- Every record has storage, modelling and redistribution rights
  `NOT_ESTABLISHED`.
- Citation is permitted with conditions for reviewed filings and press
  articles.
- These are operational classifications, not legal advice.

## 6. Analytical role

| Role | Meaning |
| --- | --- |
| `CALIBRATION_CANDIDATE` | May be proposed for calibration. Necessary conditions:<ul><li>`VERIFIED` or `REPORTED`</li><li>`DOMAIN_ONLY` with `SINGLE_DOMAIN` scope</li><li>a verifiable price</li><li>cash or unknown consideration</li><li>storage and modelling rights granted</li></ul> |
| `HOLDOUT_CANDIDATE` | Never stored in this public registry (see the holdout protocol). |
| `REFERENCE_ONLY` | Context, e.g. a documented landmark sale. Not for calibrating ordinary names. |
| `EXCLUDED` | Not a usable domain comparable. |
| `UNDETERMINED` | Not yet assessed. |

Evidence status never assigns a role. Roles never permit production use; that
requires a separate Sprint 1B authorisation.

## 7. Dataset rules and change control

- Header counts and `content_sha256` must match the records. `--write`
  recomputes them and canonicalises the files.
- The header carries no dataset-level verification claim, and
  `dataset_status` is fixed at `RESEARCH_ONLY_NOT_FOR_PRODUCTION`
  (DEC-2026-10-08-03).
- Production code must not reference the research files.
- Every change goes through a pull request running the validator and tests.
- Changing a record to `VERIFIED` must cite the reviewed document in the same
  change.
- Before any record becomes a calibration candidate, a second reviewer
  confirms its evidence and rights.
