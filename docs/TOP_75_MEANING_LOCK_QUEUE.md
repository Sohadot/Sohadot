# Top 75 Meaning Lock Expansion Queue

**Public page:** `top-75-queue.html`
**Data:** `data/top-75-meaning-lock-queue.json`
**Generator:** `scripts/generate_top_75_queue.py`
**Validator:** `scripts/validate_top_75_queue.py`
**Status:** A governed review queue. It does not define new domains, does not add anything to the
50 protected Category Artifacts, does not change any canonical meaning, and does not add pricing,
checkout, buy-now, or marketplace language.

## Purpose

The Category Artifact Meaning Layer protects 50 domains today. Sprint 8 does not grow that number
to 75 — inventing 25 new canonical meanings in one pass would repeat the same shortcut the
[Conceptual Inventory Ledger](CONCEPTUAL_INVENTORY_LEDGER.md) was built to refuse: manufacturing
plausible-sounding definitions to make a count look bigger, instead of earning each one through
review. Sprint 8 instead builds the queue: a public, transparent shortlist of 25 domains, drawn from
the current Pending Canonical Meaning Lock set, selected as the strongest candidates to review next
on the path from 50 to 75.

## Why the queue exists

Without a queue, "which domain gets reviewed next" is an invisible, ad hoc decision. The queue makes
that decision visible and checkable:

- It states, for each of 25 domains, *why* it was selected over the other 371 pending domains in the
  same pool — not just that it was picked.
- It separates the *selection* step (which domains are worth reviewing) from the *approval* step
  (locking an actual canonical meaning), so a buyer or reviewer can see exactly where each candidate
  stands.
- It gives the next expansion sprint a fixed, pre-validated starting set instead of a fresh,
  unaccountable search through 396 pending domains.

## Why meanings are not published yet

Every field in a queue record is explicitly a hypothesis, not a finished claim:

- `suspected_conceptual_direction` is a directional guess a human reviewer must confirm, refine, or
  reject — the same way a first read of a domain is only the starting point for the segmentation,
  misreadings, conceptual thesis, and buyer logic that a real Category Artifact record requires.
- `canonical_meaning_locked` is `false` on every record, and `must_not_publish_as_definition` is
  `true` on every record — both enforced by `scripts/validate_top_75_queue.py`, which fails the build
  if either drifts.
- No candidate is added to `data/asset-meanings.json` or `data/category-clusters.json`, and no
  candidate's `status` in `data/conceptual-inventory.json` changes from
  `pending-canonical-meaning-lock`. Queue membership is a prioritization signal layered on top of that
  status, not a replacement for it.

Locking a canonical meaning without review — for 25 domains at once, to hit a round number — would
cheapen the 50 that were actually earned, exactly as described in the Conceptual Inventory Ledger's
rationale for not auto-generating definitions. The queue exists so that expansion can be *measured*
without being *rushed*.

## Selection criteria

`scripts/generate_top_75_queue.py` selects candidates from the pending set using a manually curated,
commented list rather than a scoring formula — a defensible category-artifact candidate depends on
judgment calls (spelling defensibility, trademark risk, conceptual clarity) that a script cannot
reliably automate. Each of the 25 entries states, in its own `selection_rationale`, why it was chosen
over other pending domains in the same strategic direction. The directions favored, per the sprint
brief, are:

1. Strategic category potential — does the domain plausibly name a real category, not just describe
   a product?
2. Exact-match or high-clarity term value — is the segmentation obvious, or does it require a
   speculative leap?
3. Fit with Sohadot's existing eight clusters (or a clear signal that a new cluster may be needed).
4. Relevance to AI/agents/AGI/ASI, compute/chips/data/infrastructure, authentic scientific terms,
   commerce/merchant/revenue control, trust/identity/evidence, sustainability/energy, and
   Arabic/Amazigh/culturally rooted identity.
5. Low risk of turning out to be a generic weak brandable once reviewed.
6. Realistic potential to become a Category Artifact after human review — not a name that would
   require an implausible or trademark-risky reading to justify a meaning.

Domains with indefensible spelling, domains that would require speculative claims to justify, and
domains carrying plausible trademark conflicts (for example a CRISPR-branded alternative was
deliberately passed over in favor of the generic scientific term "genomic editing") were excluded
even where they might otherwise have fit a strategic direction.

## Relationship to the Conceptual Inventory Ledger

The queue is layered strictly on top of the ledger, not a fork of it:

- Every queued domain must currently have `status: "pending-canonical-meaning-lock"` in
  `data/conceptual-inventory.json` — `scripts/validate_top_75_queue.py` fails the build otherwise.
- No queued domain may already appear in `data/asset-meanings.json` — the validator checks this
  independently of the ledger, directly against the source file.
- Queue selection does not change a domain's ledger status. A queued domain still counts toward the
  396 pending domains reported on `conceptual-inventory.html` until it is actually reviewed and
  locked; the queue is a subset callout, not a new bucket.

## Relationship to future Top 75 expansion

The queue is the input to — not a substitute for — the sprint that will actually expand the meaning
layer. When a queued domain is reviewed and a canonical meaning is locked, the intended sequence is:

1. Add the reviewed record to `data/asset-meanings.json` (canonical segmentation, meaning, surface
   misreadings, conceptual thesis, category claim, possible fields, buyer logic).
2. Assign it to a primary cluster in `data/category-clusters.json` — using its
   `possible_cluster_target` as a starting point, not a final answer; `new-cluster-candidate` entries
   may justify an entirely new ninth cluster instead of forcing a fit into an existing one.
3. Re-run `scripts/generate_conceptual_inventory.py`, which will automatically move that domain from
   "pending" to "protected" in the ledger with no manual bookkeeping.
4. Remove the domain from `data/top-75-meaning-lock-queue.json` (or mark it reviewed in a later
   revision of the queue schema) so the queue always reflects domains still awaiting review.

Doing this for all 25 queued domains — plus whatever additional review is needed if a candidate does
not survive human scrutiny — is future work, not part of this sprint.

## Human review requirement

Nothing in this queue authorizes publishing a canonical meaning automatically. Every record carries
`review_required: true`, and the public page states plainly, twice, in a highlighted box: queue
inclusion does not mean the canonical meaning is approved, and no candidate becomes a Category
Artifact until Canonical Meaning Lock is completed. A human reviewer must still perform the same work
that produced each of the existing 50 records: confirm or correct the segmentation, write the actual
misreadings to avoid, and decide whether the domain earns a place in the meaning layer at all — some
queued candidates may ultimately be rejected rather than locked.

## Strategic conclusion

The Top 75 queue creates a controlled expansion path from 50 protected assets to 75 without weakening
the meaning-lock standard. It separates candidate selection from canonical meaning approval,
preserving trust while making the next expansion measurable.
