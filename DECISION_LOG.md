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
   meaning verbatim. AITopSight.com and VRTopSight.com carry short public set
   descriptions in the Conceptual Inventory Ledger and remain pending Canonical
   Meaning Lock; the 51 Category Artifacts are not expanded.

### Rationale

The three names share one repeated structure across three adjacent interface
layers — AI understands, AR places, VR rehearses — so their value to a buyer is
as a coordinated naming system. Offering them only as one set keeps that
structure intact and gives the page a single, unambiguous acquisition path.
