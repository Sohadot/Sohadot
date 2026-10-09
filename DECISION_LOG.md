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

## DEC-2026-10-09-03 — Filtered GitHub Pages Deployment

- **Status:** Proposed (draft PR; not deployed)
- **Date:** 2026-10-09

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
