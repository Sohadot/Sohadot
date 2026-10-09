# Transaction Evidence Registry v1

- **Status:** Research standard (Sprint 1A). Not used by the production valuation engine.
- **Schema version:** `transaction-evidence/v1`
- **Files:**
  - `research/valuation-evidence/registry/transactions.v1.json`: the registry
  - `research/valuation-evidence/schema/transaction-evidence.v1.schema.json`: structural JSON Schema
  - `scripts/validate_evidence_registry.py`: enforces the cross-field rules below
  - `research/valuation-evidence/investigations/seed-45.v1.json`: investigation of the 45 published comps

## 1. Unit of record: the transaction

A record is a single sale of a domain, not a domain name. One domain can sell
more than once, at different prices and dates, and each sale gets its own
record and its own identifier.

- **Identifier:** `transaction_id` uses the form `SOH-TX-NNNNNN`. Once
  assigned, an identifier is never renumbered or reused. A record found to be
  wrong is corrected or retired, and its ID stays reserved.
- **Duplicates:** two records with the same domain, sale date and price are
  rejected as one sale recorded twice.
- **Repeat sales:** repeat sales of one domain are separate records. For
  example, `chat.com` has a 2023 purchase and a 2024 sale to OpenAI, and
  `fund.com` has a 2007/2008 transaction and a 2019 sale. Calibration
  candidates for the same domain need distinct sale dates.
- **Absent facts are null:** when a fact is unknown, the field is `null`
  (price, date) or `UNKNOWN` (enum). An unsourced figure appears only in
  `price_claims`, labelled `UNSOURCED_CLAIM`. It is never stored as
  `sale_price`.

## 2. Fields

| Field | Meaning | Values |
| --- | --- | --- |
| `transaction_id` | Stable ID | `SOH-TX-NNNNNN` |
| `domain` | Lower-case domain | valid hostname |
| `sale_price`, `currency` | Price in the currency of the transaction; never converted | positive integer or null; `USD`, `EUR`, `GBP`, `JPY`, `CNY`, `CAD`, `AUD`, `CHF` |
| `sale_date`, `sale_date_precision` | When the sale happened, at the precision known | `YYYY`, `YYYY-MM`, `YYYY-MM-DD` with `YEAR` / `MONTH` / `DAY`; null with `UNKNOWN` |
| `report_date` | When the sale was first publicly reported; cannot precede the sale | partial ISO date or null |
| `venue` | Where it was transacted | `AUCTION`, `MARKETPLACE`, `BROKER`, `PRIVATE`, `BANKRUPTCY_SALE`, `CORPORATE_TRANSACTION`, `UNKNOWN` |
| `transaction_type` | What was sold | `DOMAIN_ONLY`, `DOMAIN_PLUS_ASSETS`, `MULTIPLE_DOMAINS`, `WEBSITE_BUSINESS`, `BUSINESS_ASSETS`, `UNKNOWN` |
| `consideration_type` | How it was paid | `CASH`, `CASH_AND_STOCK`, `CASH_AND_NOTE`, `CASH_AND_OTHER`, `STOCK`, `CRYPTOCURRENCY`, `STRUCTURED`, `UNKNOWN` |
| `market_side` | Buyer type | `END_USER_ACQUISITION`, `INVESTOR_TRADE`, `UNKNOWN` |
| `source_name`, `source_url`, `source_type` | Principal source | see §4 |
| `source_access_method` | How the source was read | `DOCUMENT_REVIEWED`, `SEARCH_INDEX_ONLY`, `NOT_ACCESSED` |
| `source_accessed_at` | Date the source was consulted | ISO date |
| `additional_sources` | Corroborating or context sources | list with the same source fields |
| `price_disclosure_status` | How precisely the price is known | `EXACT`, `ROUNDED`, `STATED_SUBJECT_TO_ADJUSTMENT`, `APPROXIMATE`, `LOWER_BOUND`, `UNDISCLOSED`, `UNKNOWN` |
| `price_claims` | Every price figure encountered, with its source and qualifier | list |
| `conflicts` | Contradictions found, each flagged `material` true/false | list |
| `evidence_status` | §3 | `VERIFIED`, `REPORTED`, `DISPUTED`, `UNVERIFIED` |
| `verification_basis`, `verified_at` | For `VERIFIED` only: the document, locator and quoted statement, and the review date | text, ISO date |
| `rights_status`, `rights_basis`, `rights_license` | §5 | see §5 |
| `calibration_role` | §6 | `CALIBRATION_CANDIDATE`, `HOLDOUT_CANDIDATE`, `REFERENCE_ONLY`, `EXCLUDED`, `UNDETERMINED` |
| `notes` | What a reader needs to interpret the record | text |

## 3. Evidence status

Evidence status describes the strength of the evidence for one transaction as
recorded. It says nothing about whether that transaction is a good
comparable.

| Status | Requirements (all enforced by the validator) |
| --- | --- |
| **VERIFIED** | The principal source is **primary evidence** (a regulatory filing, court record, announcement by a party to the transaction, or marketplace record of a completed sale). The reviewer **read the document itself** (`DOCUMENT_REVIEWED`). The price is `EXACT`, `ROUNDED` or `STATED_SUBJECT_TO_ADJUSTMENT`. `verified_at` and a `verification_basis` quoting the statement are recorded. There is no unresolved material conflict. |
| **REPORTED** | A cited source (reputable trade or general press, or a party statement seen only second-hand) reports the transaction. There is no unresolved material conflict. |
| **DISPUTED** | At least one **material** conflict: credible sources disagree on price, date or consideration, or a primary source contradicts the headline figure. |
| **UNVERIFIED** | No attributable source was located, or only rumour or unattributed lists were found. |

**What does not count as verification:**

- A URL does not. A trade-press link, however reputable, is at most `REPORTED`.
- A search-engine summary does not. Records read only through search results
  are marked `SEARCH_INDEX_ONLY` and cannot be `VERIFIED`.
- A dataset-level date does not. No field at registry level states or implies
  that the registry as a whole is verified. The header carries counts and a
  content hash only, and `dataset_status` is fixed at
  `RESEARCH_ONLY_NOT_FOR_PRODUCTION`. This continues the Sprint 0 rule
  (DEC-2026-10-08-03).

**Verification procedure:**

1. Locate a primary document.
2. Read the passage that states the domain, the price and the date.
3. Record the document name, URL, locator (note or section) and a short quoted
   statement in `verification_basis`.
4. Set `source_access_method: DOCUMENT_REVIEWED` and `verified_at`.
5. Record what the document verifies. For example, `insurance.com` is verified
   as a *website-business* acquisition, not as a domain sale.

**Limitations:**

- Primary documents exist mainly for public-company buyers or sellers, which
  biases verified records towards large strategic deals.
- Party announcements can overstate value, especially when payment is in
  stock or crypto. The consideration type is recorded so this can be weighed.
- Verification is a point-in-time review by one reviewer. A second-reviewer
  step is recommended before any record is used for calibration (§8).

## 4. Source types

| `source_type` | Primary? | Notes |
| --- | --- | --- |
| `REGULATORY_FILING` | Yes | e.g. SEC EDGAR 10-K/10-Q/8-K notes |
| `COURT_RECORD` | Yes | e.g. bankruptcy sale orders |
| `PARTY_ANNOUNCEMENT` | Yes | Buyer, seller or broker of record, on its own channel |
| `MARKETPLACE_RECORD` | Yes | The venue's own record of a completed sale |
| `TRADE_PUBLICATION` | No | DN Journal, Domain Name Wire, TheDomains, DomainInvesting and similar |
| `GENERAL_NEWS` | No | General press |
| `AGGREGATOR_DATABASE` | No | Compiled sales databases (see the rights matrix) |
| `TERTIARY_REFERENCE` | No | Encyclopaedias and lists; context only |

## 5. Rights status

Rights status records what Sohadot may do with the *information*, separately
from whether it can be read.

| Status | Meaning |
| --- | --- |
| `PUBLIC_RECORD` | Official records (filings, court records). Facts are cited with attribution. Only valid with those source types. |
| `PUBLIC_VIEW_CITATION_ONLY` | Publicly readable. Individual facts may be cited with attribution and a link. No copying of text or compiled charts, and no bulk collection. |
| `LICENSED_REUSE` | An explicit licence permits reuse. `rights_license` must name it. |
| `PERMISSION_REQUIRED` | Reuse needs the owner's permission. |
| `RESTRICTED_OR_UNKNOWN` | Terms restrict reuse, or the origin is unknown. |

Every record carries a `rights_basis` explaining its conclusion. Being able to
read a page does not authorise collecting, redistributing or commercially
reusing a database built from it. These classifications are operational
judgements, not legal advice. Bulk reuse of any third-party data needs the
owner's review.

## 6. Analytical role

Roles describe intended analytical use. They never permit production use;
that requires a separate, explicit Sprint 1B authorisation.

| Role | Meaning |
| --- | --- |
| `CALIBRATION_CANDIDATE` | May be proposed for model calibration. |
| `HOLDOUT_CANDIDATE` | Reserved for independent testing. **Never stored in this public registry**; see the holdout protocol. |
| `REFERENCE_ONLY` | Useful context (e.g. a documented landmark sale) but unsuitable for calibrating ordinary names. |
| `EXCLUDED` | Not a usable domain comparable: business acquisitions, undisclosed prices, disputed or non-cash consideration. |
| `UNDETERMINED` | Not yet assessed, usually because the evidence is missing. |

Evidence status never assigns a role. The validator enforces only
*necessary* conditions for `CALIBRATION_CANDIDATE`:

- `VERIFIED` or `REPORTED`;
- `DOMAIN_ONLY`;
- a verifiable price;
- cash or unknown consideration;
- rights not restricted or unknown.

A verified $30M strategic sale can stay `REFERENCE_ONLY`.

## 7. Dataset rules

- The header's `transaction_count`, `status_counts`, `role_counts` and
  `content_sha256` must match the records.
- `--write` recomputes them and rewrites the files in canonical form, so
  processing is deterministic.
- Production code (`js/valuation-engine.js`, `js/valuation-ui.js`,
  `scripts/generate_valuation_data.py`, `valuation.html`) must not reference
  the research files. The validator checks this.

## 8. Change control

- Adding or changing a record goes through a pull request that runs
  `validate_evidence_registry.py` and the test suite.
- A change of `evidence_status` to `VERIFIED` must cite the reviewed document
  in the same change.
- Before any record becomes a `CALIBRATION_CANDIDATE` in Sprint 1B, a second
  reviewer should confirm its evidence and rights.
- Schema changes bump `schema_version`.
