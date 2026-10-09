# Source Reliability & Data Rights Matrix

- **Status:** Sprint 1A research reference, as of 2026-10-09.
- **Scope:** sources met while investigating the 45 published comparable sales,
  and the source classes Sohadot is likely to need when it scales up.
- **Disclaimer:** rights entries are operational judgements for research
  planning, not legal advice. Before any bulk collection or commercial reuse
  of third-party data, the owner should review the source's current terms and
  obtain permission or a licence where needed.

## Reliability tiers

| Tier | Source class | Can support | Typical weaknesses |
| --- | --- | --- | --- |
| A | Regulatory filings (e.g. SEC EDGAR 10-K/10-Q/8-K, prospectuses) | `VERIFIED` once the document is reviewed | Only public-company deals. Often bundles the domain with a business, or rounds figures. |
| A | Court records (e.g. bankruptcy sale orders) | `VERIFIED` once reviewed | Docket access can require PACER fees (not incurred without approval). |
| B | Announcements by a party to the sale: buyer, seller or broker of record | `VERIFIED` if reviewed on the party's own channel | Self-interested. Stock or crypto consideration can overstate value. |
| B | Marketplace records of completed sales | `VERIFIED` if the venue publishes the record itself | Coverage and reuse terms vary by venue. |
| C | Domain trade press (DN Journal, Domain Name Wire, TheDomains, DomainInvesting, NamePros blog) | `REPORTED` | Often relays party statements. Some figures come from unnamed sources. Early reports get corrected later. |
| C | General press (TechCrunch, The Register, Fortune, heise, InformationWeek, VentureBeat, Entrepreneur) | `REPORTED` | Often second-hand from trade press. |
| D | Compiled sales databases and aggregators | `REPORTED` at most; per-record provenance often thin | Reuse is usually restricted by terms. Not consulted in Sprint 1A. |
| E | Encyclopaedias and "most expensive domains" lists (e.g. Wikipedia) | Context only (`TERTIARY_REFERENCE`) | Repeat figures without independent checking. Conflicting years are common. |
| — | Search-engine summaries | Leads only (`SEARCH_INDEX_ONLY`) | Never evidence on their own; can misattribute. |

## Rights by source class

| Source class | Rights status used | Basis |
| --- | --- | --- |
| SEC EDGAR filings | `PUBLIC_RECORD` | U.S. government public records. Facts are cited with attribution and a link. Automated retrieval must follow SEC EDGAR fair-access rules (declared user agent, rate limits). |
| Trade and general press | `PUBLIC_VIEW_CITATION_ONLY` | Articles are copyrighted. Individual facts (price, date, parties) are cited with attribution and a link. Text and compiled sales charts are not copied. Systematic extraction of a publisher's archive would need permission. |
| Compiled sales databases (e.g. NameBio-style services) | `PERMISSION_REQUIRED` until their terms are reviewed | Not consulted. Their terms commonly restrict scraping and redistribution. A licence is a Sprint 1B decision requiring owner approval and must not be bought without it. |
| Marketplace sale records | Case by case | Terms differ per venue. Record the basis per transaction. |
| Unknown origin (the 18 seed records with no evidence) | `RESTRICTED_OR_UNKNOWN` | The original source of the figure was never recorded, so its terms cannot be assessed. |
| Wikipedia | Context only | CC BY-SA text. Used only to find primary or secondary sources, never as the evidence itself. |

## Sources used in Sprint 1A

| Source | Tier | Access | Used for |
| --- | --- | --- | --- |
| MicroStrategy 10-Q (Q3 2019) and 8-K Ex. 99.1 | A/B | Document reviewed | voice.com (VERIFIED) |
| Amazon 424B3 (2009), Zappos financial statements | A | Document reviewed | clothes.com (VERIFIED) |
| eHealth 10-Q (Q1 2014) | A | Document reviewed | medicare.com (VERIFIED) |
| QuinStreet 10-K (FY2011) | A | Document reviewed | insurance.com (VERIFIED as a website business) |
| WebMediaBrands 8-K Ex. 99.1 (2009) | A | Document reviewed | internet.com (VERIFIED as business assets) |
| Fund.com Inc. 8-K Ex. 99(a) (2008) | A | Document reviewed | fund.com (DISPUTED: domain plus IP, contested) |
| DN Journal, Domain Name Wire, TheDomains, DomainInvesting | C | Search index only | Most REPORTED records |
| TechCrunch, The Register, Fortune, heise, InformationWeek, VentureBeat, Entrepreneur, TechRadar | C | Search index only | REPORTED records and context |
| Syndicated copy of a broker press release (GetYourDomain.com) | B (copy) | Search index only | ai.com 2025 sale (REPORTED) |
| Wikipedia | E | Search index only | Context only |

## Operational rules

1. Prefer tier A/B evidence. Tier C supports `REPORTED` only.
2. Record the access method honestly. A record read only through search
   summaries is never `VERIFIED`.
3. Store citations, not copies. The repository holds facts, links and short
   quoted locators, never article text or third-party datasets.
4. Restricted or licensed raw data, private correspondence and holdout records
   stay out of this public repository.
5. Any paid source (database licence, API, court-record fees) needs explicit
   owner approval first.
6. Automated retrieval only where terms allow it. EDGAR asks automated
   clients to declare a contact in the user agent. Use an organisational role
   address (for example a mailbox on sohadot.com), never a personal one.
