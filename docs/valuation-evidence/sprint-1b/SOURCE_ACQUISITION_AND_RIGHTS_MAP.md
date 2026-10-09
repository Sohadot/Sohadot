# Source Acquisition and Rights Map for Comparable Sales

- **Status:** Sprint 1B research, first deliverable (2026-10-09).
- **Not legal advice.** Classifications are conservative readings of each
  source's published terms. Database rights, contract enforceability
  (browsewrap vs clickwrap) and use of individual facts need counsel's
  confirmation before Sohadot relies on them.
- **Method:**
  - Terms, robots.txt and API pages were read on 2026-10-09 with the
    user agent `Sohadot-Research/1.0 (+https://sohadot.com)`.
  - There were no logins, no sign-ups, no requests to venues, no paywall or
    bot-protection bypass, and no bulk download of any sales list. At most a
    page or two per source was read to understand structure.
  - Ten key clauses (marked ✔︎ below) were re-checked against the live page
    by a second, independent fetch. For Sedo the re-checked phrase is "data
    mining or scraping using robots or in some other way"; for Dynadot it is
    "incorporated into any information retrieval system". The other wording
    quoted for those two was read once.

## 0. What this map does and does not establish

| This map records | This map does **not** decide |
| --- | --- |
| What each reviewed provider's own published terms, notices, robots.txt or API documents say about copying, scraping, databases and reuse of **its site or data** | Whether an individual sale fact (domain, price, date) is itself protected, under copyright, database rights or any other law |
| Whether a provider offers a permission or licence route | Whether a fact learned from one provider can be used once it is confirmed independently, e.g. from the parties or a public record |
| Sohadot's conservative operating classification for each provider | Whether a provider's terms bind Sohadot (browsewrap vs clickwrap), or which jurisdiction's law applies |

- The classifications below describe **documented provider restrictions**.
  They are not legal conclusions about sale facts in general.
- The legal questions are open and assigned to counsel: D1a and D1b in
  FIRST_500_PLAN.
- Until counsel answers, Sohadot follows each provider's restrictions and
  treats rights it has not documented as not established.

## 1. Discovery is not ingestion

| Use | Meaning | Rights needed |
| --- | --- | --- |
| **Discovery** | Learning that a sale may have happened, to look for evidence | None beyond lawful reading. A discovery source is a lead, never evidence. |
| **Citation of an individual fact** | Recording one sale (domain, price, date, venue) with attribution and a link, after review | `citation` right (Registry v1 §5) |
| **Bulk ingestion** | Systematically copying many records from a source into Sohadot datasets | `storage`, and `commercial_modelling` for calibration. `redistribution` if the records are published, which includes committing them to this public repository. |

Rules carried over from Sprint 1A:
- Public accessibility is never permission.
- Unknown rights block calibration.
- Records whose redistribution right is not granted must not be committed
  to this public repository, even if storage and modelling are licensed
  (see DATA_PIPELINE_ARCHITECTURE §6).

## 2. Classification codes

| Code | Meaning |
| --- | --- |
| `BULK_PERMITTED` | Terms allow copying and reuse (e.g. US government records), subject to access rules |
| `CITATION_ONLY` | The provider's terms allow, or do not address, citing individual items with attribution; bulk use is restricted or not addressed |
| `DISCOVERY_ONLY` | Use as leads; record nothing beyond a pointer without a reviewed primary source |
| `NEEDS_PERMISSION` | Terms reserve reuse to written consent or a licence. Written permission is the contractually intended route. |
| `PROHIBITED` | The provider's terms forbid scraping, extraction or building a database without consent |
| `UNKNOWN` | Terms could not be read. Treated as `NEEDS_PERMISSION`. |

## 3. Marketplaces, auction venues and brokers (primary venue data)

| Source | Public sold data | Sub-$100k coverage | Terms read | Key clause | Classification | Market side and biases |
| --- | --- | --- | --- | --- | --- | --- |
| Sedo | Weekly top-sales reports, mostly relayed by press. Newsroom has only aggregate annual reports. | Yes (weekly runners-up ~$5k–$50k) | Yes, Sedo general terms, version 01 March 2023 | ✔︎ prohibited uses include "competitor analysis … data mining or scraping using robots or in some other way". §6: database information is Sedo's property. | `PROHIBITED` for bulk under Sedo's terms. The terms do not address citing an individual sale relayed by the press; that is a legal question (D1b). A written licence is needed for more. | Mixed, mostly retail. Only sales Sedo chooses to publish; NDA sales absent. Ownership may change (Ionos sale of its AdTech unit reported Nov. 2025). The "competitor analysis" wording is a specific risk for a valuation site. |
| GoDaddy Auctions / Afternic (incl. Dan.com) | No public sold-results page or sold-data API found. The Auctions API covers bidding only. | Largest pool of completed sub-$100k sales, not published | No: godaddy.com returned 403; Afternic terms render only in JavaScript. A GoDaddy-family reseller copy of the UTOS was read: "You will not collect or harvest … any User Content … without their express prior written consent." | `UNKNOWN`, leaning `NEEDS_PERMISSION` | Auctions: wholesale. Afternic: retail. Auction results can include non-paying winners. |
| GoDaddy investor filings (10-K, earnings) | Aggregate aftermarket revenue only | No per-sale data | SEC public records | — | Macro context only | n/a |
| Dynadot | No public sold page; robots.txt disallows `/market/*` auction and listing paths | Unknown | Yes, version 2026-10-02 | ✔︎ content may not be "incorporated into any information retrieval system"; API data may not be incorporated "into other applications" | `PROHIBITED` | Mixed |
| Atom (formerly Squadhelp) | No public sold page found | Unknown | Yes, last updated Nov. 4, 2025 | ✔︎ no "automated means (including bots, crawlers, or scrapers) to access or collect data from the Services without our written permission" | `NEEDS_PERMISSION` | Retail brandables. Atom sets list prices through its own review, and payment plans are reported (unverified). |
| Flippa | "Recently sold" filter; price visibility without login unverified | Yes, small deals | Yes, last updated Nov. 6, 2025 | ✔︎ "You may also not create and/or publish your own database that features substantial parts of the Flippa Services … without our express written consent." | `NEEDS_PERMISSION` (database-right wording) | Mixed, small retail |
| park.io | Home page shows recent sales with prices | Yes, mostly $99 to low thousands | Yes, last updated Mar. 13, 2017 | ✔︎ "no scraping" | `NEEDS_PERMISSION` under park.io's terms. Citing an individual sale is not addressed by its terms; legal question (D1b). | Wholesale ccTLD drop-catch. $99 is often the fixed backorder price, not a market price. |
| Porkbun | No sold data visible | — | Partly; no data clause found | — | Not a source | — |
| Escrow.com | No per-sale public data | — | Yes | — | Not a source (could carry seller-consented receipts, §6) | — |
| Grit Brokerage | "Notable sales" list, mostly without prices | Few | Terms page not found | — | `CITATION_ONLY` at most | Retail, brokered; NDAs remove most prices |
| MediaOptions | Marketing page; most sales under NDA | Mostly $100k+ | Not found | — | `UNKNOWN` | Retail, high-end |
| Namecheap, Spaceship, NameJet, SnapNames, DropCatch, Sav, Efty, Epik, Catched, Saw.com | Not verified | Some have many small sales (drop auctions) | No (403, JavaScript-only or not found) | — | `UNKNOWN` | Drop venues are wholesale and include unpaid auction wins |

## 4. Trade press, aggregators, records and datasets

| Source | What it publishes | Sub-$100k coverage | Terms read | Key clause | Classification | Reliability |
| --- | --- | --- | --- | --- | --- | --- |
| **DN Journal** (Internet Edge, Inc.) | Bi-weekly sales report: domain, price (USD; conversions stated), venue and source. Archive of year index pages 2003–2025 (2017 missing from the index list). | Strong. One current report has about 204 unique domains, about 197 under $100k and about 170 under $10k (heuristic parse of one report). | Footer only; robots.txt returned HTTP 500 | ✔︎ "No photos, text or content of any kind may be copied from this site without expressed written consent." | `DISCOVERY_ONLY`; bulk `NEEDS_PERMISSION` | Secondary relay of venue- and party-reported sales; names the venue per row. No per-sale date, only the report window. The same sale can appear in several charts. LTO deals are excluded until paid. |
| NameBio | Large compiled database: domain, price, date, venue | The deepest sub-$10k history | ToS behind Cloudflare (403); robots.txt disallows ClaudeBot, GPTBot and others; API docs read | ✔︎ API: "You MAY NOT use our Paid API for a product or service, whether free or paid, without obtaining written permission." API access is "intended for large, established businesses." The ToS reportedly bars systematic extraction (second-hand, unverified). | `NEEDS_PERMISSION` (paid licence; purchase requires owner approval) | Aggregator of venue feeds and reported sales; wholesale- and auction-heavy |
| Domain Name Wire | Weekly articles, e.g. Sedo end-user sales with buyer identification | Yes | Yes | ✔︎ users agree "To not use automated programs to access Domain Name Wire without express written permission" | `DISCOVERY_ONLY` / `CITATION_ONLY` (manual) | Relay plus editorial research |
| DomainInvesting, DomainGang, OnlineDomain, TheDomains | Articles; TheDomains relays Sedo weekly reports | Some | Disclaimers or copyright notices only | e.g. DomainInvesting: no republishing "without express written permission" | `DISCOVERY_ONLY` | Relays |
| Domaining.com | RSS headline aggregator | Relay only | No terms found | — | `DISCOVERY_ONLY` (pointer) | — |
| NamePros | User-reported sales threads | Yes | No (403) | — | `UNKNOWN`; leads only | Self-reported and mixes asking prices with claims; never evidence alone |
| DomainSherpa | Articles | Little | Yes | "…these files may not be used to construct any kind of database." | `PROHIBITED` | — |
| DomainSalesHistory.uk | 40,532 UK sales, 2003–2026 | Likely | Yes | ✔︎ "You can show a maximum of 10 results per year with all columns displayed." Beyond 10 rows, only domain and price may be stored or displayed. | `CITATION_ONLY` with caps; bulk `NEEDS_PERMISSION` | Compiled |
| **SEC EDGAR** (full-text search) | 8-K / 10-K / 10-Q passages on domain purchases | Occasional; mostly larger deals | Yes | ✔︎ sec.gov content "may be copied or further distributed by users of the web site without the SEC's permission." Fair access: no unclassified bots, at most 10 requests per second, and a declared user agent with an organisation name and contact address. | `BULK_PERMITTED` for SEC material, within fair-access rules | Tier A primary. One test query ("purchase of the domain name") returned 110 hits. Often bundles or stock consideration. |
| CourtListener / RECAP (PACER) | Dockets and orders, e.g. §363 bankruptcy domain sales | Rare (e.g. petfinders.com $25,000, Ondova bankruptcy, as summarised by others) | ToS 403; API docs read (rate limits; commercial agreements offered) | — | Court records likely public; platform terms `UNKNOWN` | Tier A primary, low volume. PACER fees need owner approval. |
| Kaggle `domainnamesales` (PDDL) and `domain-name-sales-dataset-march-2026` (CC BY 4.0) | Bulk sales files | Unknown | Metadata only | Declared open licences | `UNKNOWN`: an uploader's licence cannot clear upstream rights while provenance is undocumented | Unknown origin; possibly scraped |
| Academic datasets (arXiv 1707.00906, 1806.11222) | NameBio/venue samples and GoDaddy internal data | — | Papers only | — | Not obtainable (no release) | — |
| Wikipedia, "List of most expensive domain names" | 51 sales of $3M or more | None | Licence line read | CC BY-SA 4.0 | Permitted with attribution and share-alike | Tertiary; leads only under Registry v1 |
| Appraisal services (GoDaddy GoValue, Estibot) | Model estimates | — | GoValue help page read | — | **Not sales.** Never used as ground truth. | — |

## 5. What follows

1. **Under its own published terms, no reviewed provider with substantial
   sub-$100k coverage permits bulk ingestion for model calibration.** This
   finding is about provider restrictions, not about whether sale facts are
   legally protected (§0).
   - Every such source (DN Journal, NameBio, Sedo, Atom, Flippa, park.io,
     Dynadot, GoDaddy/Afternic) either requires written permission or a
     licence, or has terms that could not be read.
   - The only clearly reusable sources (SEC filings, court orders) are
     primary but few, and skewed to large deals.
2. **Discovery is abundant.** DN Journal alone lists roughly 170 sub-$10k
   sales per report. Trade press, NamePros and Wikipedia are leads only.
3. **Lawful routes to volume:**
   - written permission or a data licence from a publisher or venue;
   - seller- and broker-consented submissions;
   - a documented lawful basis, if counsel can confirm one, for manually
     recording individually announced facts. Whether such a basis exists, and
     how it interacts with provider terms, is open (D1b). Volume by that route is modest, and Sedo's
     "competitor analysis" clause is a specific risk.
   - All three are owner decisions (see FIRST_500_PLAN).
4. **Venue biases to model:**
   - Venue "top sales" lists are a survivorship sample.
   - Drop-catch results cluster at fixed backorder prices.
   - Auction wins may go unpaid.
   - Atom list prices are administratively set.
   - Broker lists omit prices under NDA.
   - Wholesale and retail must be recorded separately.

## 6. Could not verify

- **Terms not read:** GoDaddy's own UTOS and Auctions agreement,
  Afternic/Dan, Namecheap, Spaceship, NameJet, SnapNames, DropCatch, Sav,
  Efty, Epik, Catched, Saw.com, NamePros, CourtListener, NameBio (ToS),
  TheDomains (none found).
- **Other gaps:**
  - DN Journal's robots.txt.
  - Whether DN Journal has terms beyond its footer.
  - Exact yearly counts of DN Journal's sub-$100k listings.
  - Whether Flippa shows sold prices without login.
  - The provenance of the Kaggle datasets.
  - Whether DNPric.es still operates.
  - Where Sedo's weekly reports are published first today.
- **SEC user agent:** EDGAR asks for an organisation name and contact
  address. Sohadot needs a role address (not a personal email) before any
  systematic EDGAR querying.
