#!/usr/bin/env python3
"""Generate data/top-75-meaning-lock-queue.json — the Top 75 Meaning Lock
Expansion Queue.

This script builds a governed *review queue* of 25 candidate domains, drawn
from the current Pending Canonical Meaning Lock set, that look like the
strongest candidates to eventually join the 50 protected Category Artifacts.

It does NOT:
  - invent final canonical meanings for any domain,
  - mark any candidate as "protected-category-artifact",
  - add any candidate to data/asset-meanings.json or data/category-clusters.json,
  - change any existing canonical meaning,
  - expand the 50 Category Artifacts.

Every field on a queue record is explicitly a hypothesis pending human
review: `suspected_conceptual_direction` is a directional guess, not a
locked meaning, and `canonical_meaning_locked` is always false.

Sources (read-only):
  - data/conceptual-inventory.json -> pending-canonical-meaning-lock domain
    set, and the current total/defined/pending counts.
  - data/asset-meanings.json       -> the 50 protected domains, used only to
    confirm no candidate is already protected.
  - data/category-clusters.json    -> existing cluster names, used only to
    validate that `possible_cluster_target` references a real cluster or the
    literal "new-cluster-candidate" placeholder.

Candidate selection method
---------------------------
An automated ranking over 396 pending domains cannot reliably tell a strong,
defensible category-artifact candidate from a weak generic brandable — that
judgment call (trademark risk, spelling defensibility, conceptual clarity)
needs a human-legible rationale per domain, not just a score. So this script
uses a stable, manually curated candidate list (MANUAL_CANDIDATES below),
grouped by the strategic directions requested for Sprint 8: AI/agents/AGI/
ASI, compute/chips/data/infrastructure, authentic scientific terms, commerce/
merchant/revenue control, trust/identity/evidence, sustainability/energy, and
Arabic/Amazigh/culturally rooted identity. Each entry explains, in its own
selection_rationale, why it was chosen over other pending domains in the same
bucket (e.g. real scientific/technical vocabulary over invented wordplay,
exact-match clarity over ambiguous compounds, no plausible trademark
conflict). The script still re-validates every one of these 25 domains
against data/conceptual-inventory.json and data/asset-meanings.json before
writing the queue, so a stale or incorrect manual entry fails the build
instead of silently shipping.

Usage: python3 scripts/generate_top_75_queue.py
Writes data/top-75-meaning-lock-queue.json and prints a one-line summary.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPTUAL_INVENTORY_PATH = REPO_ROOT / "data" / "conceptual-inventory.json"
ASSET_MEANINGS_PATH = REPO_ROOT / "data" / "asset-meanings.json"
CATEGORY_CLUSTERS_PATH = REPO_ROOT / "data" / "category-clusters.json"
OUTPUT_PATH = REPO_ROOT / "data" / "top-75-meaning-lock-queue.json"

QUEUE_SIZE = 25
TARGET_AFTER_APPROVAL = 75

# ---------------------------------------------------------------------------
# Manually curated candidate list.
#
# Every domain below is currently "pending-canonical-meaning-lock" in
# data/conceptual-inventory.json. Grouped by strategic direction with the
# reasoning for picking it over other pending domains in the same bucket.
# `suspected_conceptual_direction` is a hypothesis for human review, not a
# locked meaning. `possible_cluster_target` names an existing cluster from
# data/category-clusters.json, or the literal "new-cluster-candidate" where
# no existing cluster fits well (a signal for future cluster work, not a
# claim that the cluster already exists).
# ---------------------------------------------------------------------------
MANUAL_CANDIDATES = [
    # --- AI / agents / AGI / ASI / compute infrastructure -------------------
    {
        "domain": "agiconstructor.com",
        "selection_rationale": (
            "Pairs AGI with 'Constructor', extending the delegation/genesis vocabulary already "
            "protected in AGIBeget.com and ASIBeget.com into the party that builds or assembles "
            "systems on AGI's behalf. Clear two-part segmentation (AGI + Constructor) and a direct "
            "fit with the existing Agency, Liaison & Delegation Systems cluster made it a stronger "
            "pick than other 'agi*' pending domains (e.g. agioutsourcing.com, agipurify.com, "
            "agishoring.com), whose second halves read as more generic outsourcing/logistics wordplay."
        ),
        "suspected_conceptual_direction": (
            "Possibly names AGI-driven system construction or agent-assembly infrastructure — the "
            "builder role adjacent to AGI origin and delegation — not a finished product category yet."
        ),
        "possible_cluster_target": "Agency, Liaison & Delegation Systems",
        "risk_of_misreading": (
            "Could be misread as a literal construction/engineering-industry domain, with 'AGI' taken "
            "as unrelated initials rather than Artificial General Intelligence; could also be conflated "
            "with generic 'AI website builder' tooling."
        ),
    },
    {
        "domain": "rpaagi.com",
        "selection_rationale": (
            "Fuses RPA (Robotic Process Automation), an established enterprise-automation acronym, "
            "with AGI — naming the transition point where scripted automation gives way to "
            "general-intelligence-driven automation. Chosen over other RPA-adjacent pending domains "
            "(rpasi.com, wetrpa.com, tvrpa.com) for its unambiguous, high-clarity acronym pairing."
        ),
        "suspected_conceptual_direction": (
            "Possibly names the RPA-to-AGI automation transition — infrastructure or advisory "
            "positioning for enterprises moving from rules-based bots to general-intelligence agents."
        ),
        "possible_cluster_target": "Compute Sovereignty & Post-AI Infrastructure",
        "risk_of_misreading": (
            "RPA could be misread as an unrelated acronym; the compound could be mistaken for a "
            "generic 'AI automation' brandable with no specific thesis."
        ),
    },
    {
        "domain": "ineuralvault.com",
        "selection_rationale": (
            "Combines the 'I' (AI/Intelligent) prefix pattern already used across the portfolio with "
            "'Neural' and 'Vault' — naming secured custody of neural-network assets, a real and growing "
            "infrastructure need. Preferred over other neural-adjacent pending names for pairing a "
            "recognizable AI term with a concrete infrastructure noun rather than an abstract one."
        ),
        "suspected_conceptual_direction": (
            "Possibly names secure custody/versioning infrastructure for neural-network models and "
            "training data — an AI 'vault' rather than a generic storage brand."
        ),
        "possible_cluster_target": "Compute Sovereignty & Post-AI Infrastructure",
        "risk_of_misreading": (
            "The leading 'I' could be misread as a Roman numeral or personal pronoun; 'Vault' alone "
            "invites confusion with unrelated password-manager or crypto-wallet products."
        ),
    },
    {
        "domain": "synaptivault.com",
        "selection_rationale": (
            "'Synaptic' is an authentic neuroscience term, matching the portfolio's standing preference "
            "for real scientific vocabulary (cf. Ketonemia.com, Mesomere.com) over coined wordplay; "
            "paired with 'Vault' it suggests custody of neural/cognitive-model assets rather than a "
            "generic buzzword brandable."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a reference-grade or infrastructure term for storing/protecting "
            "synaptic-model (neural network) architectures or neuroscience research data."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "Could be misread as a consumer brain-health or nootropic supplement brand rather than an "
            "infrastructure or scientific-reference term."
        ),
    },
    {
        "domain": "icogniflow.com",
        "selection_rationale": (
            "'I' + 'Cogni' (cognition) + 'Flow' names the throughput of cognitive/AI reasoning "
            "processes, echoing the portfolio's existing throughput-naming logic (cf. IOPace.com) "
            "applied to AI reasoning instead of raw I/O. Chosen over other 'cogn*' or generic AI-flow "
            "pending names for this direct analogy to an already-protected naming pattern."
        ),
        "suspected_conceptual_direction": (
            "Possibly names cognitive-pipeline or reasoning-throughput infrastructure for AI systems — "
            "the cadence of AI reasoning, not just data movement."
        ),
        "possible_cluster_target": "Compute Sovereignty & Post-AI Infrastructure",
        "risk_of_misreading": (
            "Could be misread as a generic productivity/workflow SaaS brand ('flow state') unrelated "
            "to AI cognition; the 'Cogni' fragment could be mistaken for a specific named product."
        ),
    },
    {
        "domain": "photonicicon.com",
        "selection_rationale": (
            "'Photonic' is a real, high-clarity engineering term for light-based computing and chip "
            "design — an emerging real category adjacent to the portfolio's existing chip/compute "
            "cluster (AIElectronicChips.com, EmberQuantum.com, QuantumANN.com). Selected as the "
            "strongest 'next layer after electronic and quantum chips' candidate in the pending set."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a reference brand for photonic computing / optical chip technology, "
            "positioned as the layer after electronic and quantum chips — not a finished claim yet."
        ),
        "possible_cluster_target": "Compute Sovereignty & Post-AI Infrastructure",
        "risk_of_misreading": (
            "'Icon' could pull the reading toward a generic design/UI-icon product rather than a "
            "hardware or photonics-research brand — decorative branding instead of a technical claim."
        ),
    },
    {
        "domain": "streamcollider.com",
        "selection_rationale": (
            "'Collider' is a real physics term (particle collider), aligning with the portfolio's "
            "preference for authentic scientific vocabulary; paired with 'Stream' it suggests the "
            "intersection of data/event streams — a legitimate data-engineering metaphor grounded in "
            "real science rather than an invented buzzword."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a data-stream collision/correlation engine, where multiple real-time "
            "streams are merged or cross-analyzed, using 'collider' as a precise physics-derived "
            "metaphor rather than a generic term."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "Could be misread as a literal particle-physics research site rather than a data-"
            "infrastructure product; 'collider' also carries a colloquial 'crash/conflict' connotation."
        ),
    },
    {
        "domain": "unitschips.com",
        "selection_rationale": (
            "'Units' + 'Chips' names discrete allocation or accounting units of compute/semiconductor "
            "capacity — directly relevant to the existing Compute Sovereignty & Post-AI Infrastructure "
            "cluster's chip-allocation thesis (AIElectronicChips.com). Preferred over other 'units*' "
            "pending domains (unitscooler.com, unitsrefrigeration.com) that read as literal industrial "
            "equipment listings rather than a compute-infrastructure concept."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a chip-allocation, quota, or unit-accounting layer for compute/"
            "semiconductor capacity — tracking who holds how many chip 'units', not the chips themselves."
        ),
        "possible_cluster_target": "Compute Sovereignty & Post-AI Infrastructure",
        "risk_of_misreading": (
            "Could be misread as a literal snack-food ('chips') e-commerce listing or a generic "
            "hardware-parts marketplace rather than a compute-allocation concept."
        ),
    },
    {
        "domain": "depsync.com",
        "selection_rationale": (
            "'Deps' (dependencies) + 'Sync' is an established shorthand already used across software "
            "engineering for dependency/version synchronization — a high-clarity, real technical term "
            "rather than an invented brandable, fitting the operational-intelligence cluster's plumbing "
            "focus alongside IOEDI.com and Bytelco.com."
        ),
        "suspected_conceptual_direction": (
            "Possibly names dependency-synchronization or software supply-chain infrastructure — "
            "keeping dependencies, versions, or build graphs aligned across systems."
        ),
        "possible_cluster_target": "Enterprise Data, IO & Operational Intelligence",
        "risk_of_misreading": (
            "'Deps' could be misread as an abbreviation for 'departments' or 'deposits' rather than "
            "software dependencies; the domain could be mistaken for an HR or finance-sync tool."
        ),
    },
    # --- Authentic scientific / clinical terms ------------------------------
    {
        "domain": "genomicediting.com",
        "selection_rationale": (
            "'Genomic Editing' is a real, high-clarity scientific field name — authentic terminology in "
            "the spirit of the portfolio's existing scientific-reference assets, chosen deliberately "
            "over a CRISPR-branded alternative in the same pending cluster (crisprgenomic.com) to avoid "
            "invoking a heavily trademarked tool name while still naming the real field."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a reference, education, or platform brand for the genomic-editing field "
            "broadly — research, clinical, or biotech-education positioning."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "Could be misread as endorsing or being affiliated with a specific gene-editing company or "
            "patent holder rather than naming the general scientific field."
        ),
    },
    {
        "domain": "histogenous.com",
        "selection_rationale": (
            "'Histogenous' is a real, dictionary-attested medical/biological adjective (originating in "
            "tissue) — authentic reference-grade vocabulary matching the portfolio's existing rare-word "
            "scientific assets (Isotely.com, Allenarly.com), selected for its dictionary legitimacy over "
            "invented '-genous' wordplay."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a tissue-origin or histology-adjacent reference term for clinical, "
            "pathology, or biotech-education platforms."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "Could be misread as a coined pseudo-scientific brandable rather than a real dictionary "
            "word; non-specialist readers may not recognize the term without context."
        ),
    },
    {
        "domain": "zonules.com",
        "selection_rationale": (
            "'Zonules' is a real anatomical term (e.g. the ciliary zonule of the eye) — authentic "
            "clinical vocabulary consistent with the portfolio's reference-grade scientific naming "
            "pattern, and a plural exact-match term with no plausible unrelated reading."
        ),
        "suspected_conceptual_direction": (
            "Possibly names an ophthalmology, anatomy-reference, or clinical-education platform "
            "grounded in the real anatomical structure."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "Could be misread as a generic '-ules' diminutive brandable rather than the specific "
            "anatomical term; non-clinical readers may not recognize the reference at all."
        ),
    },
    {
        "domain": "polaritonmatter.com",
        "selection_rationale": (
            "'Polariton' is a real physics term (a quasiparticle from strong light-matter coupling) — "
            "precise, authentic scientific vocabulary paired plainly with 'Matter', matching the "
            "portfolio's preference for real terminology over invented wordplay."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a physics-research, photonics, or quantum-materials reference brand built "
            "on the real polariton concept."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "Could be misread as generic 'polarity' or 'polarized' branding rather than the specific "
            "quasiparticle physics term — flattened into vague 'science-sounding' marketing."
        ),
    },
    {
        "domain": "smartpitot.com",
        "selection_rationale": (
            "'Pitot' (as in Pitot tube) is a real, exact aerospace/fluid-dynamics instrument term — "
            "authentic technical vocabulary paired with 'Smart' to suggest a sensor-intelligence "
            "evolution of the classic instrument, consistent with preferring real scientific terms over "
            "invented ones."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a smart/connected airspeed- or flow-sensing instrument platform — "
            "aerospace, drone, or industrial fluid-dynamics sensor intelligence."
        ),
        "possible_cluster_target": "Scientific, Clinical & Reference-Grade Terms",
        "risk_of_misreading": (
            "'Pitot' is a specialist term many readers will not recognize and could misread as a "
            "coined brand syllable; could also be confused with generic 'smart sensor' IoT branding."
        ),
    },
    # --- Sustainability / energy ---------------------------------------------
    {
        "domain": "ecoeffectiveness.com",
        "selection_rationale": (
            "'Eco-effectiveness' is a real, named sustainability doctrine (cradle-to-cradle design "
            "thinking), distinct from the far more common 'eco-efficiency' — a high-clarity, authentic "
            "term with direct relevance to the existing Energy, Space & Sustainability Systems cluster, "
            "chosen for naming a specific doctrine rather than a generic 'green' adjective."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a sustainability-strategy or circular-design consultancy/platform grounded "
            "in the eco-effectiveness doctrine specifically, not generic 'green' branding."
        ),
        "possible_cluster_target": "Energy, Space & Sustainability Systems",
        "risk_of_misreading": (
            "Could be misread as a synonym for 'eco-efficiency' (an older concept focused on doing less "
            "harm rather than redesigning systems) — the distinction must not be collapsed."
        ),
    },
    {
        "domain": "hydrogenstandard.com",
        "selection_rationale": (
            "'Hydrogen Standard' is a high-clarity, exact category phrase relevant to the emerging "
            "hydrogen-economy standards-and-certification space — a direct, easy-to-grasp fit with the "
            "portfolio's energy/sustainability naming logic, chosen over more oblique H2-prefixed "
            "pending domains for its immediate clarity."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a certification, benchmark, or standards-setting platform for hydrogen "
            "production, purity, or supply-chain claims (e.g. green vs. blue hydrogen)."
        ),
        "possible_cluster_target": "Energy, Space & Sustainability Systems",
        "risk_of_misreading": (
            "Could be misread as implying an official government or industry-body standard (regulatory "
            "authority Sohadot does not hold) rather than a naming asset for a future standards platform."
        ),
    },
    {
        "domain": "batteryh2.com",
        "selection_rationale": (
            "Pairs 'Battery' with 'H2' (hydrogen), naming the convergence point between battery storage "
            "and hydrogen energy systems — a real, active area of energy-infrastructure debate, chosen "
            "over other H2-prefixed pending domains (avolth2.com, leawatt.com) for pairing two "
            "unambiguous, real energy terms rather than an unclear abbreviation."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a hybrid battery-hydrogen storage/infrastructure category, or a comparison/"
            "advisory platform for battery-vs-hydrogen energy strategy."
        ),
        "possible_cluster_target": "Energy, Space & Sustainability Systems",
        "risk_of_misreading": (
            "Could be misread as a literal battery retailer stocking 'H2' as a product line, or as "
            "favoring one technology over the other rather than naming their intersection."
        ),
    },
    {
        "domain": "pvgalaxy.com",
        "selection_rationale": (
            "'PV' (photovoltaic) is a high-clarity industry abbreviation; paired with 'Galaxy' it "
            "suggests a broad, constellation-style view of solar assets, fitting the Energy, Space & "
            "Sustainability Systems cluster's large-scale-energy thesis alongside Space-Based-Solar-"
            "Power.com and OrbitSSP.com."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a solar-asset portfolio/monitoring platform (a 'galaxy' of PV "
            "installations) or a large-scale photovoltaic deployment brand."
        ),
        "possible_cluster_target": "Energy, Space & Sustainability Systems",
        "risk_of_misreading": (
            "'PV' could be misread as an unrelated abbreviation; 'Galaxy' invites confusion with "
            "consumer electronics branding (e.g. smartphone product lines)."
        ),
    },
    # --- Arabic / Amazigh / culturally rooted identity -----------------------
    {
        "domain": "arganhub.com",
        "selection_rationale": (
            "'Argan' is an authentic word of Amazigh (Berber/Tashelhit) origin naming the argan tree and "
            "its oil — a real, culturally rooted commercial term with an established global commodity "
            "market, paired with the plain, high-clarity word 'Hub'. Continues the portfolio's authentic-"
            "culture direction already anchored by YetFut.com (Amazigh word for sweetness)."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a sourcing, trade, or certification hub for argan oil and related Amazigh-"
            "origin commodities — a cultural-commerce category artifact, not a generic marketplace "
            "brandable."
        ),
        "possible_cluster_target": "Cultural, Taste & Meaning Identity",
        "risk_of_misreading": (
            "Could be misread as a generic cosmetics-retail domain rather than a category-defining "
            "commodity/trade hub; the Amazigh linguistic origin could be overlooked without context."
        ),
    },
    {
        "domain": "momtaze.com",
        "selection_rationale": (
            "A transliteration of the Arabic word ممتاز (mumtaz/momtaz), "
            "meaning 'excellent' or 'premium' — authentic Arabic-rooted vocabulary consistent with the "
            "portfolio's existing cultural-identity assets (Alwakile.com, YetFut.com), selected over "
            "the less certain transliteration reading of another pending domain (nobogh.com) for a "
            "clearer, more defensible source-word match."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a quality-grading, premium-certification, or culturally rooted excellence-"
            "branding concept drawing directly on the Arabic meaning."
        ),
        "possible_cluster_target": "Cultural, Taste & Meaning Identity",
        "risk_of_misreading": (
            "Could be misread as an invented, meaningless brandable syllable-string by readers "
            "unfamiliar with the Arabic source word; the transliteration must be explicitly anchored to "
            "ممتاز during review, not left implicit."
        ),
    },
    # --- Trust / identity / evidence -----------------------------------------
    {
        "domain": "batonsecurity.com",
        "selection_rationale": (
            "'Baton' (as in a relay baton) is a real, well-understood metaphor for handoff and "
            "continuity, paired with 'Security' — naming secure transfer-of-custody moments rather than "
            "static perimeter security. No existing cluster covers this trust/handoff angle directly, "
            "which is itself useful signal for a possible future cluster."
        ),
        "suspected_conceptual_direction": (
            "Possibly names secure hand-off or custody-transfer infrastructure — identity, credentials, "
            "or control passed securely from one party or system to the next — rather than generic "
            "cybersecurity."
        ),
        "possible_cluster_target": "new-cluster-candidate",
        "risk_of_misreading": (
            "Could be misread as a literal law-enforcement or physical-security equipment brand (police "
            "batons); 'Security' alone invites conflation with generic cybersecurity-vendor naming."
        ),
    },
    {
        "domain": "lawfulbytes.com",
        "selection_rationale": (
            "'Lawful' + 'Bytes' names the intersection of legal compliance and digital data — a real, "
            "high-clarity compound relevant to legal-tech, e-discovery, and digital-evidence platforms, "
            "adjacent in spirit to the portfolio's existing forensic terms (Dactylograph.com, "
            "MobileArtifacts.com) but naming a distinct compliance angle."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a legal-compliance or lawful-data-handling platform (e.g. lawful "
            "interception, compliant data retention, e-discovery) rather than a generic legal-tech "
            "brandable."
        ),
        "possible_cluster_target": "new-cluster-candidate",
        "risk_of_misreading": (
            "'Lawful' could be misread narrowly as referring only to law-enforcement 'lawful intercept' "
            "surveillance tools rather than the broader compliant-data-handling reading; which reading "
            "is intended must be settled before any meaning is locked."
        ),
    },
    {
        "domain": "insuretrusts.com",
        "selection_rationale": (
            "'Insurance Trusts' is a real, established financial/legal instrument (a trust structure "
            "that owns a life-insurance policy) — high-clarity, exact-term commercial vocabulary in the "
            "finance/estate-planning space, adjacent to the portfolio's existing finance-infrastructure "
            "naming (AccountCcy.com)."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a platform or advisory brand for insurance-trust structuring, "
            "administration, or estate-planning-linked insurance products."
        ),
        "possible_cluster_target": "new-cluster-candidate",
        "risk_of_misreading": (
            "Could be misread as a generic 'insure + trusts (confidence)' wordplay rather than the "
            "specific legal instrument 'insurance trust'; the plural 'trusts' needs review against "
            "singular-instrument naming conventions."
        ),
    },
    {
        "domain": "homebuyerstrust.com",
        "selection_rationale": (
            "A plain, high-clarity descriptive phrase naming trust infrastructure specifically for home "
            "buyers — real-estate-adjacent, with an unambiguous literal reading and a clear commercial "
            "audience (title companies, escrow services, buyer-advocacy platforms)."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a buyer-side trust, verification, or escrow-adjacent service in residential "
            "real estate — protecting the buyer's interest specifically, not a generic real-estate "
            "portal."
        ),
        "possible_cluster_target": "new-cluster-candidate",
        "risk_of_misreading": (
            "Could be misread as a specific named nonprofit or government housing-trust program rather "
            "than an available commercial brandable; 'Trust' could also be read strictly as a legal "
            "trust rather than as confidence/assurance."
        ),
    },
    # --- Commerce / merchant / revenue control --------------------------------
    {
        "domain": "dairybenchmarks.com",
        "selection_rationale": (
            "'Benchmarks' is a real, precise commodity-market term (reference prices used for contracts "
            "and trading), paired with 'Dairy' to name a specific, legitimate commodity-index category — "
            "fitting the Merchant, Funnel & Commercial Control cluster's control-point thesis, and "
            "chosen over the portfolio's many formulaic city+commodity pending domains for naming a "
            "distinct commercial mechanism rather than a geo-exact-match listing."
        ),
        "suspected_conceptual_direction": (
            "Possibly names a dairy commodity price-benchmarking, index, or market-intelligence "
            "platform — a control point in agricultural-commodity trading, not a generic dairy-industry "
            "site."
        ),
        "possible_cluster_target": "Merchant, Funnel & Commercial Control",
        "risk_of_misreading": (
            "Could be misread as a generic dairy-industry directory or nutrition-comparison site rather "
            "than a commodity-market benchmarking concept; 'benchmarks' has a distinct financial "
            "meaning that must be preserved."
        ),
    },
]


def fail(errors):
    for err in errors:
        print(f"FAIL: {err}")
    sys.exit(1)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    errors = []

    if not CONCEPTUAL_INVENTORY_PATH.exists():
        fail([f"{CONCEPTUAL_INVENTORY_PATH.relative_to(REPO_ROOT)} not found — run "
              f"scripts/generate_conceptual_inventory.py first"])
        return

    inventory = load_json(CONCEPTUAL_INVENTORY_PATH)
    inventory_status_by_domain = {
        r["domain"].strip().lower(): r["status"] for r in inventory.get("records", [])
    }

    asset_meanings_raw = load_json(ASSET_MEANINGS_PATH)
    asset_domains = {
        a.get("domain", "").strip().lower()
        for a in asset_meanings_raw.get("assets", [])
        if isinstance(a, dict) and a.get("domain")
    }

    clusters_raw = load_json(CATEGORY_CLUSTERS_PATH)
    cluster_names = {
        c.get("name", "").strip()
        for c in clusters_raw.get("clusters", [])
        if isinstance(c, dict) and c.get("name")
    }

    if len(MANUAL_CANDIDATES) != QUEUE_SIZE:
        errors.append(
            f"MANUAL_CANDIDATES has {len(MANUAL_CANDIDATES)} entries, expected exactly {QUEUE_SIZE}"
        )

    seen = set()
    for entry in MANUAL_CANDIDATES:
        domain = entry["domain"].strip()
        key = domain.lower()

        if key in seen:
            errors.append(f"duplicate candidate domain in MANUAL_CANDIDATES: '{domain}'")
        seen.add(key)

        if key in asset_domains:
            errors.append(
                f"'{domain}' is already a protected Category Artifact in "
                f"{ASSET_MEANINGS_PATH.relative_to(REPO_ROOT)} — cannot be queued"
            )

        status = inventory_status_by_domain.get(key)
        if status is None:
            errors.append(
                f"'{domain}' not found in {CONCEPTUAL_INVENTORY_PATH.relative_to(REPO_ROOT)}"
            )
        elif status != "pending-canonical-meaning-lock":
            errors.append(
                f"'{domain}' has inventory status '{status}', expected 'pending-canonical-meaning-lock'"
            )

        cluster_target = entry["possible_cluster_target"]
        if cluster_target != "new-cluster-candidate" and cluster_target not in cluster_names:
            errors.append(
                f"'{domain}' possible_cluster_target '{cluster_target}' is neither an existing cluster "
                f"in {CATEGORY_CLUSTERS_PATH.relative_to(REPO_ROOT)} nor 'new-cluster-candidate'"
            )

        for field in ("selection_rationale", "suspected_conceptual_direction", "risk_of_misreading"):
            if not entry.get(field, "").strip():
                errors.append(f"'{domain}' field '{field}' must not be empty")

    if errors:
        fail(errors)
        return

    queue = []
    for entry in MANUAL_CANDIDATES:
        queue.append({
            "domain": entry["domain"],
            "queue_status": "selected-for-meaning-lock-review",
            "priority_tier": "top-75-candidate",
            "selection_rationale": entry["selection_rationale"],
            "suspected_conceptual_direction": entry["suspected_conceptual_direction"],
            "possible_cluster_target": entry["possible_cluster_target"],
            "risk_of_misreading": entry["risk_of_misreading"],
            "review_required": True,
            "canonical_meaning_locked": False,
            "must_not_publish_as_definition": True,
        })

    payload = {
        "description": (
            "Top 75 Meaning Lock Expansion Queue — a governed review queue of 25 candidate domains "
            "drawn from the current Pending Canonical Meaning Lock set (data/conceptual-inventory.json), "
            "selected as the strongest candidates to eventually join the 50 protected Category "
            "Artifacts. This is NOT a new meaning layer: no domain here has an approved canonical "
            "meaning, none is marked protected-category-artifact, and none has been added to "
            "data/asset-meanings.json or data/category-clusters.json. Every record is a hypothesis "
            "pending human Canonical Meaning Lock review. Rendered in /top-75-queue.html and checked "
            "by scripts/validate_top_75_queue.py."
        ),
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_portfolio_domains": inventory["total_domains"],
        "protected_definitions_count": inventory["defined_assets_count"],
        "pending_meaning_lock_count": inventory["pending_meaning_lock_count"],
        "queue_count": len(queue),
        "target_after_approval": TARGET_AFTER_APPROVAL,
        "queue": queue,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}: queue_count={len(queue)}, "
        f"protected_definitions_count={inventory['defined_assets_count']}, "
        f"pending_meaning_lock_count={inventory['pending_meaning_lock_count']}, "
        f"target_after_approval={TARGET_AFTER_APPROVAL}"
    )


if __name__ == "__main__":
    main()
