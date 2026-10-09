# Decision Log

This log records structural decisions about Sohadot's public surfaces as they are
made. It begins with the decision below; earlier structural choices predate this
log and are intentionally not reconstructed here. Entries are public and
non-sensitive — they describe *what* was decided and *why*, not internal
operations.

---

## DEC-2026-09-16-01 — Domain Development as a Knowledge Base Series

- **Status:** Accepted
- **Date:** 2026-09-16
- **Implementation:** PR #37

### Decision

Establish **Domain Development** as a distinct educational branch inside the
existing Sohadot Knowledge Base — a cumulative series published in chapters,
rather than a set of standalone articles.

1. **Distinct branch, same library.** Domain Development is a distinct educational
   branch *inside* the existing Knowledge Base, sitting alongside the current
   market- and valuation-education material, not separate from it.
2. **Extends, does not replace.** The series extends the existing Sohadot
   framework. It does not replace or supersede the Canonical Meaning framework or
   any current reference layer; it builds on them.
3. **Governing sequence.** The governing sequence remains:
   **Domain → Canonical Meaning → Thesis → Governed Field → Development.**
4. **Development follows meaning.** Meaning is treated as a boundary condition on
   development. Development follows meaning; it does not precede or define it.
5. **Bounded ambition.** Not every domain should be built, not every asset needs
   every layer, and software is not the default destination of an asset.
6. **Sprint 1 scope.** Sprint 1 consists only of the series hub plus Chapters 1
   and 2:
   - Hub — `kb/domain-development.html`
   - Chapter 1 — `kb/the-domain-is-the-coordinate.html`
   - Chapter 2 — `kb/meaning-before-building.html`
7. **Later chapters forthcoming.** Chapters 3–6 remain intentionally forthcoming.
   They appear on the hub as titled cards carrying their driving questions and are
   not yet written.
8. **Public boundary.** No contributor recruitment, partnership solicitation,
   private economic mechanics, internal AI strategy, or confidential governance
   logic is introduced publicly through this series.
9. **Future scrutiny, discussed conceptually only.** Future independent specialist
   scrutiny of an asset's deeper layers may be discussed as a concept within the
   series, without exposing any private participation mechanics.

### Rationale

The Knowledge Base already documents how domain value, pricing, and naming quality
are evaluated. Domain Development adds a separate, cumulative line of reasoning
about domains as governed digital assets — one long argument in chapters — so that
the conceptual material reads as a coherent body of thought rather than
disconnected articles, while remaining consistent with the framework already in
place.

---

## DEC-2026-09-16-02 — Information Architecture and Gateway Consolidation

- **Status:** Accepted
- **Date:** 2026-09-16

### Decision

Reorganize the public interface around semantic gateways so the hierarchy is
visible in the navigation itself, without removing any existing public route.

1. **Gateway navigation.** Primary navigation is organized by semantic gateways —
   **Assets · Intelligence · Knowledge · About · Strategic Inquiry** — replacing the
   previous flat row of twelve peer-level links. Each former destination remains
   public; it now lives inside a gateway rather than beside every other link.
2. **Assets is a mega-menu.** Assets is grouped into Explore (Portfolio, Developed
   Assets), Portfolio Structure (Conceptual Inventory, Category Artifacts, Category
   Clusters), and a restrained set of Selected Developed Assets with a
   "View all Developed Assets" link.
3. **Artifacts stay attached to their domain.** Any framework, index, reference
   system, or public artifact created from one domain remains semantically attached
   to that domain. Agent Aptness is presented as **AptyAgent.com → Agent Aptness
   Framework**, not as an independent Sohadot framework category. Frameworks is
   removed as a primary navigation category (its content is asset-specific), while
   the `/frameworks/` URLs are preserved for compatibility.
4. **Developed Assets is the canonical index.** `developed-assets.html` is the
   canonical index of publicly developed domains; navigation shows only a
   representative subset and links out to the full index.
5. **The architecture must scale.** Navigation must remain legible at 20, 50, or
   100+ developed assets; the menu never lists them all.
6. **URLs preserved.** Canonical URLs are preserved. Information architecture and
   URL architecture are allowed to differ; breadcrumb context can differ from
   physical file paths.
7. **One static source of truth.** Navigation is generated from a single public
   data source (`data/site-navigation.json`) and injected into each page between
   explicit markers by a deterministic script (`scripts/sync_navigation.py`). The
   final HTML contains the full navigation and works without runtime JavaScript; a
   validator (`scripts/validate_navigation.py`) fails the build if any page drifts.
8. **Mobile exposes the same hierarchy.** The previous mobile pattern that hid all
   but one link is removed. Mobile uses an accessible disclosure/accordion pattern
   (a no-JS checkbox toggle plus `<details>`/`<summary>` sub-menus) exposing the
   same gateways and destinations, with visible keyboard focus states.

### Rationale

Sohadot had grown beyond the information architecture presenting it: assets,
portfolio structure, intelligence tools, reference material, and developed assets
all appeared as peer-level links, forcing visitors to understand the internal
structure before they could navigate it. Organizing the surfaces into gateways lets
the interface explain the hierarchy instead of decorating it, while preserving every
existing route and keeping artifacts legibly attached to the domains that generated
them.

---

## DEC-2026-09-16-03 — Sohadot Public Brand Mark and Social Preview Identity

- **Status:** Accepted
- **Date:** 2026-09-16

### Decision

Adopt the user-designed flat blue mark as Sohadot's primary public brand mark and
build the public identity around it.

1. **Primary public mark.** The user-designed flat blue mark is the primary public
   mark. Its canonical asset is `assets/brand/sohadot-mark.png` (a transparent,
   lossless master derived from the supplied source by background removal only).
2. **Geometry preserved.** The mark's geometry is intentionally preserved — its
   asymmetry and spontaneity are deliberate. It is not symmetrized, "cleaned up,"
   or redrawn; the only processing is a technical background conversion.
3. **Site identity.** The mark replaces the former generic "S" tile in the global
   navigation, shown beside the "Sohadot.com" wordmark, and is the Organization
   structured-data `logo`.
4. **Social previews.** The default social preview carries the mark and the
   Sohadot.com identity in the ivory/blue visual system; meaningful custom previews
   (the Drops watchlist image) keep their informational value and carry the mark in
   a restrained brand position.
5. **Favicon deferred.** The full mark is not legible at 16px, so the existing
   favicon is retained; a dedicated micro-mark derivative remains to be designed
   rather than forcing a degraded raster conversion.
6. **Public boundary.** No private brand strategy is recorded.

---

## DEC-2026-09-25-01 — AI–AR–VR Sight Domain Set (Bundle-Only Acquisition)

- **Status:** Accepted
- **Date:** 2026-09-25

### Decision

Publish one complete-set acquisition page for three Sohadot-owned compound
.com domains, offered only together.

1. **The set.** The set consists of exactly three Sohadot-owned domains:
   **AITopSight.com**, **ARTopSight.com** and **VRTopSight.com**.
2. **Bundle only.** The three domains are offered exclusively as one complete
   set. They are not publicly offered separately, and no individual public
   purchase path is created for any of them.
3. **One public price.** The only public acquisition price is **USD 5,780** for
   the complete three-domain set. No individual-domain price is published.
4. **Canonical route.** The page lives at
   `https://sohadot.com/bundles/ai-ar-vr-sight/` and is listed in `sitemap.xml`
   and alongside the existing acquisition bundles on the homepage and portfolio.
5. **Naming boundary.** Sohadot does not own `TopSight.com` and makes no claim
   to it. "The AI–AR–VR Sight Architecture" is a descriptive heading, not a
   claimed parent brand or trademark; the three compound domains are always
   named explicitly.
6. **Scope of the offer.** The offer covers the registration rights to the three
   listed domain names only. No operating company, software product, traffic or
   revenue is represented as part of it.
7. **Meaning layer unchanged.** ARTopSight.com keeps its protected canonical
   meaning verbatim. AITopSight.com and VRTopSight.com remain pending Canonical
   Meaning Lock; their set descriptions are non-canonical `bundle_context`, never
   shown as a Canonical Meaning. The 51 Category Artifacts are not expanded, and
   inventory totals stay 446 domains / 51 defined / 395 pending.
8. **Bundle only everywhere.** `data/bundle-only-assets.json` is the single
   machine-readable source of the designation (`sale_mode: "bundle-only"`,
   `bundle_id: "ai-ar-vr-sight"`, `bundle_url`). Every commercial path for the
   three domains leads to the complete-set page: the ARTopSight.com Category
   Artifact, the Conceptual Inventory records (no individual
   `strategic_brief_url`), and the portfolio cards (no per-domain WhatsApp or
   inquiry action). Strategic Brief links naming any of the three hand the
   visitor to the set page. `scripts/validate_bundle_only.py` fails the build if
   any published HTML, JSON or JavaScript regains an individual acquisition route.

### Rationale

The three names share one repeated structure across three adjacent interface
layers — AI understands, AR places, VR rehearses — so their value to a buyer is
as a coordinated naming system. Offering them only as one set keeps that
structure intact and gives the page a single, unambiguous acquisition path.

---

## DEC-2026-10-08-01 — Free Valuation Services: Evidence & Accuracy First

- **Status:** Accepted
- **Date:** 2026-10-08
- **Implementation:** Sprint 0 — `docs/VALUATION_EVIDENCE_AUDIT.md`

### Decision

Develop Sohadot's free domain-intelligence services as a standalone programme,
aimed at reliability and repeat professional use, not as a run-up to a paid
subscription. Its first step is an audit of the evidence and accuracy behind the
existing valuation, carried out before any new feature is built.

1. **Order of work.** Sprint 0 — Evidence & Accuracy Audit; Sprint 1 —
   Comparable Sales vNext; Sprint 2 — Linguistic & Category Intelligence;
   Sprint 3 — Registration (RDAP) & Trademark Research; Sprint 4 — Research
   Report & repeat-use experience.
2. **Evidence before scale.** The comparable-sales set will not be expanded in
   bulk, and no paid data API will be added, until every record has provenance
   and accuracy is measured against an independent holdout set.
3. **Bounded claims.** Results state their coverage, sources and as-of date. No
   binary "trademark free / taken" verdict. An empty registry lookup is never
   shown as "available to buy". The engine's own sales set is never presented
   as evidence of its accuracy.
4. **No unattended scraping of restricted sources.** Trademark research starts
   from user-run links to official search services. WIPO's public database
   terms do not allow automated queries.
5. **Repository discipline.** GitHub remains the source of truth. Audits and
   gates are reproducible scripts. No API keys or sensitive data go in the
   public repository, and features that need live queries or private keys get
   a security design before they are built.
6. **No mass-generated valuation pages.** Growth comes from useful tools and
   documented studies that other sites can cite, not from auto-indexed
   thin pages.

### Rationale

The Sprint 0 audit found that no comparable sale carries a source, the weekly
data refresh changes only its timestamp, and under leave-one-out testing the
engine's retail midpoint is off by a median factor of about 84×. Adding
features on top of that would multiply unverifiable output. Making the
evidence verifiable is what would set Sohadot apart from tools that already
show comps and extension status.

---

## DEC-2026-10-08-02 — Valuation Public Integrity Correction (Sprint 0B)

- **Status:** Accepted
- **Date:** 2026-10-08
- **Implementation:** Sprint 0B — see `docs/VALUATION_EVIDENCE_AUDIT.md`

### Decision

Until the comparable sales carry verified provenance and the estimates are
validated against an independent holdout set, the valuation tool states its
limits where users see its numbers, and changes nothing it computes.

1. **Reported, not documented.** Public surfaces describe the comparable sales
   as reported sales and say that individual source provenance has not yet been
   independently verified. No surface may describe them as documented,
   verified or confirmed, or overstate their number.
2. **Experimental estimates.** Every result shows an experimental-estimate
   disclosure directly above the prices. Estimates are never presented as
   validated market prices or certified appraisals.
3. **Classification confidence.** The confidence indicator is labelled and
   explained as confidence in the name's linguistic classification, not in the
   price.
4. **Honest timestamps.** The comparable-sales file separates content-change
   time, generation time, source-verification status and methodology version.
   Unchanged evidence keeps its date and produces no commit. Automation never
   records a verification date.
5. **Engine frozen.** Scores, prices, classes, tags and comps matching are
   unchanged. A test compares engine output against a recorded baseline.
6. **Gates.** Structural evidence checks and disclosure checks are mandatory.
   The provenance gate (`--strict`) stays visible but optional until Sprint 1
   meets its evidentiary requirements.

### Rationale

Sprint 0A showed that the public copy claimed more than the evidence supports.
Correcting the claims first, without touching the numbers, keeps the estimates
reproducible for research and stops the site from implying a precision it has
not earned.

---

## DEC-2026-10-08-03 — Verification Is Earned Per Record

- **Status:** Accepted
- **Date:** 2026-10-08
- **Amends:** DEC-2026-10-08-02, item 4

### Decision

A dataset-level date or the presence of source fields never makes the
comparable-sales dataset "verified". Until Sprint 1 approves a per-record
verification standard and the rules for rolling records up into a dataset
status, the published status is always `not_verified` with `last_verified`
null. The disclosure validator rejects any other value.

### Rationale

A single date cannot show which transactions were checked, or against what.
Allowing it to set the dataset status would have let one seed edit present 45
unsourced sales as verified.

---

## DEC-2026-10-09-01 — Transaction Evidence Registry and Holdout Protocol (Sprint 1A)

- **Status:** Accepted for research use; production use not authorised
- **Date:** 2026-10-09
- **Implementation:** Sprint 1A — `docs/valuation-evidence/`, `research/valuation-evidence/`
- **Findings snapshot:** registry v1.0.0 at commit `62e4e25`. The counts
  under Rationale are preserved exactly as recorded at that snapshot. They
  are historical and superseded by v1.1.0 (`884e3ba`, DEC-2026-10-09-02) and
  v1.2.0 (`af01a28`, addendum to DEC-2026-10-09-02). See the snapshot table
  in DEC-2026-10-09-04.

### Decision

1. **Transactions, not names.** Comparable-sales evidence is recorded per
   transaction with a stable `SOH-TX-` identifier. Repeat sales of a domain
   are separate records.
2. **Evidence status is earned per record.** `VERIFIED` requires a reviewed
   primary document and a recorded basis. A URL or a search summary never
   verifies. The registry asserts no dataset-level verification, which
   extends DEC-2026-10-08-03.
3. **Evidence, rights and role are independent.** Rights are recorded with
   their basis. Analytical roles are assigned by review and never derived
   from evidence status. Landmark sales are reference material, not
   calibration data.
4. **Research isolation.** The registry is research material. The
   production engine, published comps and public pages are unchanged, and
   the validator rejects any production reference to the research files.
5. **Holdout first, privately.** No methodology change before an
   independent holdout is frozen under `holdout-protocol/v1`. Holdout
   records are never committed to the public repository. Status:
   `NOT_READY`.

### Rationale

*Snapshot v1.0.0 (`62e4e25`), historical:* the investigation of the 45 published comps found 5 sales verifiable from
primary documents, 18 with no traceable evidence, 4 with price or date
conflicts, and 3 that were business acquisitions rather than domain sales.
A registry that separates what the market demonstrated from what was merely
repeated is the precondition for any credible calibration.

---

## DEC-2026-10-09-02 — Evidence Registry Remediation After Independent Review

- **Status:** Accepted for research use; production use not authorised
- **Date:** 2026-10-09
- **Amends:** DEC-2026-10-09-01

### Decision

1. **Read, then check.** A source counts as evidence only if it was read
   directly and its quoted passage was checked against the raw text. Each
   source records its locator, access date, review method and document hash.
   Search summaries are leads, never evidence.
2. **Transactions vs valuations.** Verification describes the documented
   transaction. A bundle or business price is never attributed to one
   domain. Doubts about economic value are recorded as valuation caveats and
   do not change the evidence status. Example: fund.com's 2007 purchase of
   24 domain names and one trademark.
3. **Four separate rights.** Citation, storage, commercial modelling and
   redistribution are recorded separately, each with its basis. Public
   accessibility grants citation at most. Unknown rights block calibration.
4. **Fail-closed holdout.** A FROZEN holdout is never accepted without
   verifying the private manifest outside the repository. Controls not yet
   implemented are labelled NOT_IMPLEMENTED in the status file, and the
   validator rejects any claim beyond what it enforces.
5. **Pages exposure handled separately.** Excluding research files from the
   GitHub Pages artifact is a separate change. Filtering never makes
   repository files private.

### Rationale

*Snapshot v1.1.0 (`884e3ba`), historical:* the independent review found that search-only summaries, an unenforced
holdout protocol and a single rights field could each overstate the evidence.
Direct review also corrected candy.com, which a search summary had misread.

**Addendum (second review, same day; snapshot v1.2.0, `af01a28`).**
- VERIFIED records now state who vouches for them: `attesting_party`
  and `settlement_evidence`. A party's own announcement is recorded as
  `PARTY_ATTESTATION_ONLY`, never as confirmed settlement.
- The holdout `readiness_gate` forbids FROZEN while any control is
  NOT_IMPLEMENTED.

---

## DEC-2026-10-09-03 — Filtered GitHub Pages Deployment

- **Status:** Accepted and deployed. PR #46 merged into `main` as merge
  commit `899c159`; the GitHub Pages deployment of the filtered artifact
  completed successfully and is operational on sohadot.com.
- **Date:** 2026-10-09
- **Implementation:** `deploy/pages-manifest.json`,
  `scripts/build_pages_artifact.py`, `.github/workflows/static.yml`,
  `.github/workflows/pages-artifact-check.yml`

### Decision

1. sohadot.com publishes only the exact files listed in
   `deploy/pages-manifest.json` (an approved inventory of pages, site files,
   assets, JavaScript and runtime data, with no publish globs), built into
   `_site/` by `scripts/build_pages_artifact.py`. The whole repository is no
   longer uploaded. Generator inputs that no page fetches (the four seed or
   candidate files under `data/`) are not published.
2. Every tracked file must be classified as published or excluded. The build
   fails on unclassified files, missing required files, excluded paths in the
   artifact, link regressions and broken sitemap URLs.
3. Research files, tests, scripts, internal documentation and repository-only
   files are excluded. The exception is 11 specific `docs/` and `scripts/`
   files that public pages link to on sohadot.com, kept published so those
   links do not break.
4. Filtering Pages does not make repository files private.

### Rationale

The whole-repository deployment would publish research registries and
internal tooling on sohadot.com as soon as they were merged. An explicit,
tested manifest keeps every existing route and free tool working while
publishing only what the site needs.

---

## DEC-2026-10-09-04 — Public-Repository Basis for the Research Registry

- **Status:** Accepted for research use; production and calibration use not authorised
- **Date:** 2026-10-09
- **Implementation:** `docs/valuation-evidence/SOURCE_RELIABILITY_AND_RIGHTS_MATRIX.md` (section "Basis for keeping research records in the public repository"); quotation limit enforced by `scripts/validate_evidence_registry.py`

### Decision

1. **What is kept publicly, and why.** The research registry, the seed-45
   investigation and their short source quotations are kept in this public
   GitHub repository so that anyone can check each evidence claim against
   its source. Transparency and reproducibility are the purpose.
2. **What a record may contain.**
   - Facts (domain, price, date, parties) with attribution and a link.
   - A document locator and a SHA-256 of the reviewed document.
   - At most one short verbatim quotation per source, of 300 characters or
     fewer (enforced by the validator), used only to show where a fact comes
     from.
   - Never: full article text, images, compiled sales charts or
     third-party database extracts.
3. **Separate from use rights.** Keeping a record here for verification is
   not permission to store, model, calibrate or redistribute it commercially.
   Those rights stay recorded per record (`storage`, `commercial_modelling`,
   `redistribution`) and are `NOT_ESTABLISHED` for every record until the
   owner documents a basis.
4. **Not served on sohadot.com.** The research files are excluded from the
   GitHub Pages artifact by the filtered deployment (DEC-2026-10-09-03,
   merged in `899c159` and operational). They remain readable in the public
   repository.
5. **Corrections and removal.** A source owner's request to correct, shorten
   or remove a quotation is honoured by replacing it with a locator only. The
   record is kept, downgraded if the evidence no longer meets its status.
6. **Not legal advice.** This basis is an operational policy. The owner
   should confirm it with counsel before relying on it beyond research
   verification.

### Findings by registry snapshot

| Snapshot | Commit | VERIFIED | REPORTED | DISPUTED | UNVERIFIED | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| v1.0.0 | `62e4e25` | 5 | 20 | 4 | 20 | Search summaries plus 6 SEC documents |
| v1.1.0 | `884e3ba` | 7 | 21 | 1 | 20 | Sources read directly, 40 checked passages |
| v1.2.0 | `af01a28` | 8 | 20 | 1 | 20 | Adds the sex.com bundle and broker-attestation labels; 45 checked passages |

Earlier snapshots are preserved in the Git history at the commits above and
in the entries that cite them. They are not rewritten.

---

## DEC-2026-10-09-05 — Sprint 1B Comparable-Sales Expansion: Research Foundation

- **Status:** Proposed (research only; production use not authorised)
- **Date:** 2026-10-09
- **Implementation:** `docs/valuation-evidence/sprint-1b/`, `scripts/sales_pipeline.py`,
  `scripts/assess_comparable_selection.mjs`, `research/valuation-evidence/sprint-1b/`

### Decision

1. **Discovery is not ingestion.** A source may be used to find sales only
   within its terms. Bulk storage or modelling of a source's data requires
   permission, a licence or a documented lawful basis, recorded per record.
   Unknown rights block calibration.
2. **Computed pipeline states.** Comparable sales move through DISCOVERED,
   SOURCE_REVIEWED, ELIGIBLE, CALIBRATION_ADMITTED, REJECTED and
   HOLDOUT_RESERVED. States are computed from the evidence. Admission stays
   closed until the owner opens it, and holdout records are never stored in
   the public repository.
3. **Storage follows rights.** Records licensed for storage and modelling
   but not redistribution are kept in private storage, never in this public
   repository.
4. **No algorithm is selected yet.** The baseline shows that v2.5's
   price-descending tie-breaker biases selection upward as a dataset grows.
   Candidate methods are compared on development data only. No production
   method is chosen before the independent holdout is frozen and evaluated
   under explicit approval.

### Rationale

- **Rights:** under their own published terms, no reviewed provider with
  substantial sub-$100k coverage permits bulk reuse without permission, so
  expansion depends on permissions, not collection effort. This is a finding
  about provider restrictions. Whether individual sale facts are legally
  protected is left open for counsel.
- **Engine:** on a synthetic probe corpus, the 45 published comps (mostly
  $1M+ landmarks) raise the median probe estimate about tenfold. This is a
  behavioural finding, not an externally validated accuracy metric. Simulated
  expansion shows that a larger dataset helps only if both the pool and the
  selection rule are fixed.
