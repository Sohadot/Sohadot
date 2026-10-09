# Source Reliability & Data Rights Matrix

- **Status:** Sprint 1A research reference, revised after independent review (2026-10-09).
- **Disclaimer:** rights entries are operational classifications for research
  planning, not legal advice. Before any systematic storage, commercial
  modelling or redistribution of third-party data, the owner should document
  a lawful basis or obtain permission or a licence.

## Reliability tiers

| Tier | Source class | Can support | Typical weaknesses |
| --- | --- | --- | --- |
| A | Regulatory filings (SEC EDGAR 10-K, 10-Q, 8-K, prospectuses) | `VERIFIED` when reviewed | Public-company deals only. Often a bundle or business, or rounded. |
| A | Court records | `VERIFIED` when reviewed | Docket access may involve PACER fees (not incurred without approval). |
| B | Announcements by a party to the transaction (buyer, seller, broker of record), on the party's own channel or its wire distributor | `VERIFIED` when reviewed | Self-interested. Non-cash consideration can overstate value. |
| B | Marketplace records of completed sales | `VERIFIED` when reviewed | Coverage and reuse terms vary. |
| C | Domain trade press and general press | `REPORTED` when reviewed | Relays party statements and sometimes unnamed sources. Early reports get corrected. |
| D | Compiled sales databases | Never `REPORTED` on their own | Reuse is usually restricted. Not consulted. |
| E | Encyclopaedias and lists (e.g. Wikipedia) | Leads only | Repeat figures. Conflicting years are common. |
| — | Search-engine summaries | Leads only | Can misattribute or misread. In this sprint a summary misread candy.com's consideration ("$1.7M payout"); the reviewed article showed $3M cash plus equity. |

## Four separate rights

Being able to read a page gives citation at most. It never gives the other
three rights.

| Source class | Citation | Storage | Commercial modelling | Redistribution |
| --- | --- | --- | --- | --- |
| SEC EDGAR filings | Permitted with conditions (attribution and link; basis `PUBLIC_RECORD`) | Not established (lawful basis to be documented) | Not established | Not established |
| Trade and general press | Permitted with conditions (individual facts, attribution and link; basis `PUBLIC_FACT_CITATION`) | Not established | Not established | Not established; article text and charts are never copied |
| Compiled sales databases | Not consulted | Requires a licence or permission | Requires a licence or permission | Requires a licence or permission |
| Unknown origin (the 18 unsupported seed figures) | Not established | Not established | Not established | Not established |

A documented lawful basis, such as a legal note on reusing individual
publicly disclosed facts, may establish storage or modelling rights without
a paid licence. It must be recorded as `DOCUMENTED_LAWFUL_BASIS` with a
reference before any record can become a calibration candidate.

## Sources reviewed in Sprint 1A

Every source below was fetched on 2026-10-09 and its quoted passage checked
against the raw text. The registry records 45 such passages.

| Source | Tier | Used for |
| --- | --- | --- |
| MicroStrategy 10-Q (Q3 2019), 8-K Ex. 99.1 | A, B | voice.com (VERIFIED) |
| Amazon 424B3 (2009), Zappos statements | A | clothes.com (VERIFIED) |
| eHealth 10-Q (Q1 2014) | A | medicare.com (VERIFIED) |
| QuinStreet 10-K (FY2011) | A | insurance.com (VERIFIED: website business) |
| WebMediaBrands 8-K Ex. 99.1 (2009) | A | internet.com (VERIFIED: business assets) |
| Fund.com Inc. 10-Q/A (Q1 2009), 8-K Ex. 99(a) (2008), 10-K (FY2009) | A | fund.com (VERIFIED: 24-domain and trademark bundle) |
| GetYourDomain.com release on PR Newswire (Feb. 9, 2026) | B | ai.com 2025 (VERIFIED on broker attestation only) |
| Sedo newsroom release (Feb. 22, 2011) | B | sex.com 2010 (VERIFIED on broker attestation only; domain plus trademarks) |
| DN Journal, Domain Name Wire, DomainInvesting, TheDomains | C | 16 REPORTED records and corroboration |
| The Register, TechCrunch, InformationWeek, Fortune, heise, Entrepreneur | C | REPORTED records and corroboration |

## Operational rules

1. Prefer tier A/B evidence. Tier C supports `REPORTED` only, and only when
   the source is read directly.
2. Record the review method honestly. Unchecked automated extraction is not
   review.
3. Store citations, short checked quotes and document hashes, never article
   text or third-party datasets.
4. Restricted or licensed raw data, private correspondence and holdout
   records stay out of this repository and out of the Pages artifact.
5. Any paid source needs explicit owner approval first.
6. Automated retrieval only where terms allow. EDGAR asks for a contact in the
   user agent: use an organisational role address, never a personal one.

## Basis for keeping research records in the public repository

This section is separate from the four use rights above (DEC-2026-10-09-04).

| Question | Position |
| --- | --- |
| Why public? | So that every evidence claim can be checked against its source by anyone. |
| What is kept? | Facts with attribution and a link, a document locator, a SHA-256 of the reviewed document, and at most one short verbatim quotation per source. Quotations are 300 characters or fewer, enforced by the validator. |
| What is never kept? | Full article text, images, compiled sales charts, third-party database extracts, private holdout records. |
| Is it served on sohadot.com? | No, once the filtered Pages deployment is merged. It stays readable on GitHub. |
| Does it grant use rights? | No. Keeping a record here for verification is not permission to store, model, calibrate or redistribute it commercially. Those rights remain `NOT_ESTABLISHED` per record. |
| Corrections and removal | A quotation is replaced by its locator on a source owner's request, and the record's status is re-assessed. |
| Legal status | Operational policy, not legal advice. Owner confirmation with counsel is recommended. |
