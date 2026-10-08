# Sohadot Valuation — Evidence & Accuracy Audit (Sprint 0)

- **Status:** Complete. Findings feed Sprint 1 (Comparable Sales vNext)
- **Audit date:** 2026-10-08
- **Engine audited:** `js/valuation-engine.js`, framework version 2.5
- **Evidence audited:** `data/valuation_comps_seed.json` → `data/valuation_comps.json` (45 sales)
- **Decision record:** DEC-2026-10-08-01 in `DECISION_LOG.md`

This sprint changes no public estimate, dataset value or page. It measures the
evidence and accuracy of the current valuation framework so that later sprints
build on known ground. Every figure below can be reproduced from the repository.

## How to reproduce

```bash
python3 scripts/audit_valuation_evidence.py --as-of-year 2026   # record-level evidence audit
node scripts/valuation_backtest.mjs                               # accuracy backtest + probes
```

- `audit_valuation_evidence.py` exits 1 on structural defects and reports
  evidence gaps as warnings. `--strict` also fails on warnings; it becomes the
  gate once Sprint 1 has attached provenance to every record.
- `valuation_backtest.mjs` runs the unmodified browser engine in a Node VM
  against the local data files. It does not write to the repository.
  `--holdout <file>` evaluates an independent sale set and refuses any set that
  overlaps the calibration comps.

## How the evidence layer works today

1. `data/valuation_comps_seed.json` is maintained by hand. Each record has a
   domain, price, year, extension, class, keyword tags and a free-text note.
2. Every Monday `scripts/generate_valuation_data.py` (workflow
   `update-valuation.yml`) re-sorts the seed into `data/valuation_comps.json`
   and stamps it with the current time.
3. The engine picks up to four comps per evaluation. A sale qualifies when it
   has the same class, shares a keyword tag or has the same name. The engine
   then blends the comps' median price geometrically with the model midpoint
   (30% weight, or 50% for the same name on another extension). An exact prior
   sale of the domain replaces the model entirely.

## Findings

Severity: **Critical** means public numbers can be materially wrong or
misleading. **High** means the numbers are systematically distorted. **Medium**
means a gap that blocks verification.

### F1 — No record carries provenance (Critical)

0 of 45 records have a source, a source URL, a sale date, a price status
(confirmed / reported / undisclosed) or a venue. The methodology page calls them
"documented landmark sales", but nothing in the data documents them.

Several records describe corporate acquisitions or rebrands where the price may
never have been officially disclosed and circulates only through secondary
reports, for example `ai.com`, `gpt.com`, `chat.com`, `data.ai`, `lumen.com`,
`fb.com` and `360.com`. These go first in the verification queue. This audit
does not claim any listed price is wrong. It finds that none of them can
currently be checked.

The recent low-value sales (`aluren.com`, `upfolio.com` and others) look like
marketplace records. Their source and whether we may republish them must be
confirmed before they stay in the public data.

Without a venue, the engine also cannot tell a wholesale (investor) sale from a
retail (end-user) sale, yet it scores both against the same retail band.

### F2 — The weekly "refresh" changes only the timestamp (Critical)

`generate_valuation_data.py` stamps `last_updated` with the run time whatever
the content. Between 2026-09-07 and 2026-10-05, five consecutive "Auto-update
valuation data" commits changed only `last_updated` and `last_updated_human`.
Not one sale changed. The methodology page says the datasets "are refreshed
weekly", which tells users the evidence is fresher than it is.

### F3 — The evidence is landmark-heavy and old (High)

| Measure | Value |
| --- | --- |
| Records | 45 |
| Sales of $1M or more | 62% (28) |
| Median recorded price | $4,800,000 |
| Sales under $10k | 18% (8) |
| `.com` / `.ai` / other | 42 / 3 / 0 |
| Older than 10 years | 22 (oldest: 1999) |
| Time adjustment applied | none |

Most names people actually enter are worth hundreds to low thousands of
dollars. A comps set this concentrated at the top of the market is a poor
reference for them, and a 1999 or 2001 price sits next to a 2025 price with
equal weight.

### F4 — Recorded classes disagree with the engine's own classifier (High)

For 19 of 45 sales, the class stored on the record differs from the class the
engine assigns to that name today. Comps qualify on class, so a mislabelled
sale gets matched against subjects the engine would never put in that class.
Examples:

| Sale | Recorded | Engine |
| --- | --- | --- |
| 360.com ($17M) | brandable | random_low_quality |
| fb.com ($8.5M) | brandable | random_low_quality |
| z.com ($6.8M) | brandable | random_low_quality |
| we.com ($8M) | dictionary_word | random_low_quality |
| vacationrentals.com | commercial_keyword | random_low_quality |
| porn.com | commercial_keyword | brandable |
| toys.com, clothes.com, medicare.com, slots.com | commercial_keyword | dictionary_word |

As a result, numeric, one-letter and two-letter landmark sales are labelled
"brandable" and become comps for invented four-to-seven-letter brandables (see
F6).

### F5 — Keyword tags are either dead or too broad (High)

- **15 dead tags.** These tags are not in `valuation_keywords.json`, so they can
  never match a subject. Examples: `logic`, `stack`, `scan`, `genie`, `folio`,
  `nova`, `business`, `diamond`, `beer`.
- **18 semantic tags.** These tags do not appear in the name itself. Each one
  makes a landmark sale a comp for every subject that contains the keyword:
  `vacationrentals.com`, `privatejet.com` and `hotels.com` are tagged `travel`;
  `toys.com` and `clothes.com` are tagged `shop`; `medicare.com` is tagged
  `health` and `insurance`; `sex.com` is tagged `dating`.

### F6 — The comparability rule lets landmark sales into ordinary estimates (Critical)

Sharing a class is enough on its own to qualify a comp, and the four comps
mix price scales up to 10,000×. These synthetic probe names are behaviour
checks, not valuations of real assets:

| Probe | Comps drawn | Retail estimate |
| --- | --- | --- |
| zuno.com (invented, 4 letters) | 360.com $17M, fb.com $8.5M, z.com $6.8M, aluren.com $1.5k | $40,230 – $98,747 |
| travelnook.com | privatejet.com $30.2M, vacationrentals.com $35M, hotels.com $11M, insurance.com $35.6M | $67,604 – $165,937 |
| shopvault.com | clothes.com $4.9M, toys.com $5.1M, insurance.com $35.6M, stackscan.com $2.7k | $38,802 – $95,242 |
| healthpilot.io | medicare.com $4.8M, privatejet.com $30.2M, … | $26,873 – $65,961 |

Under leave-one-out, `aluren.com` (recorded $1,524) gets a retail estimate of
$32,064 – $78,704 because `360.com` and `fb.com` enter as comps. The median and
the geometric blend soften the outliers but do not stop them: once two of four
comps are multi-million landmarks, the median is a landmark price.

### F7 — Measured accuracy (Critical)

The error unit is log10(engine retail midpoint ÷ recorded price): 0.30 is 2×,
1.0 is 10× and 2.0 is 100×.

| Pass | n | Median abs. error | Median signed | Within 2× | Within 10× | Price inside retail band |
| --- | --- | --- | --- | --- | --- | --- |
| In-sample (leakage check) | 45 | 0.05 | +0.05 | 100% | 100% | 100% |
| Leave-one-out | 45 | 1.93 | −1.93 | 8.9% | 31.1% | 2.2% |

Leave-one-out by recorded price band:

| Band | n | Median abs. error | Median signed | Inside retail band |
| --- | --- | --- | --- | --- |
| ≥ $1M | 28 | 2.21 | −2.21 | 0% |
| $100k – $1M | 5 | 0.83 | −0.83 | 0% |
| $10k – $100k | 4 | 0.44 | −0.28 | 0% |
| < $10k | 8 | 0.43 | +0.43 | 12.5% |

What this shows:

- **The in-sample score is not accuracy.** Every sale is in its own evidence,
  so the engine anchors to its own price. The comps set can never be used to
  validate the engine.
- **The model does not reach landmark prices.** Without their own sale, landmark
  domains come out about 160× under the recorded price. The model is built for
  ordinary names, so this is expected. It also means landmark sales do not
  calibrate the model; they only distort it through F6.
- **Ordinary names are overestimated.** Under $10k, the engine's typical result
  is about 2.7× above the recorded price, and only 1 of 8 falls inside the
  retail band. Some of that gap may be a wholesale-versus-retail mismatch (F1:
  no venue), which can only be resolved once the venue is recorded.
- **The sample is far too small** to support per-class conclusions (n = 1 or 2
  for some classes).

### F8 — There is no independent holdout set (Critical)

No sales are set aside from calibration, so no out-of-sample accuracy claim is
possible today. The backtest supports `--holdout`, but the data for it does
not exist yet.

### F9 — The "Confidence" label is ambiguous (Medium)

The result card shows "Confidence: High" next to the price, but the value is
the confidence of the *lexical classification* (`classifyDomain`). It is not the
confidence of the estimate. A user will reasonably read it as the latter.

## Sprint 1 inputs

### Evidence schema (per sale)

| Field | Purpose |
| --- | --- |
| `domain`, `tld`, `price`, `currency` | The transaction |
| `sale_date` | ISO date or year-month of the sale, not of the report |
| `price_status` | `confirmed` · `reported` · `estimated` · `undisclosed` |
| `venue` | auction · marketplace · broker · private · corporate |
| `market_side` | wholesale · retail · unknown (derived from venue and buyer) |
| `source_name`, `source_url`, `source_accessed` | Citation the user can open |
| `rights` | Whether the record may be republished (marketplace data licences) |
| `classification`, `keywords` | Must match what the engine computes for the name; tags must occur in the name |
| `role` | `calibration` · `holdout` · `reference_only` (landmarks shown for context, never blended) |

Records with `price_status` of `undisclosed` or `estimated` never enter pricing.

### Holdout protocol

1. Keep a separate file of sales, sourced independently of the calibration set
   and never loaded by the public engine.
2. Freeze the holdout before any calibration change is made.
3. Spread it across price bands, classes and extensions, weighted towards the
   sub-$10k and $10k–$100k ranges where most queries fall. Use a date cutoff so
   that held-out sales come after the calibration sales.
4. Report every metric from `valuation_backtest.mjs` per release. A methodology
   change ships only if holdout error does not get worse.

### Acceptance gates for Sprint 1

- `audit_valuation_evidence.py --strict` passes (full provenance, no dead or
  semantic tags, classes consistent with the engine).
- `last_updated` changes only when sale content changes. The page shows the
  evidence as-of date, not the build time.
- Landmark sales move to `reference_only` and no longer enter blending for
  ordinary names. The probes in this report no longer draw multi-million comps.
- Leave-one-out and holdout metrics are published alongside the methodology
  version, including the cases where the model is weak.

## Interim recommendations (need a decision; not applied in this sprint)

1. Change "documented landmark sales" to "reported sales" on the methodology
   page until F1 is resolved.
2. Stop the weekly job from re-stamping unchanged data (F2), or label the
   timestamp "build time".
3. Rename the result-card label to "Classification confidence" (F9).

Each is a public-surface change, so it is left for an explicit decision.

---

## Sprint 0B — Public integrity correction (implemented 2026-10-08)

Sprint 0B applies the three interim recommendations above and closes Sprint 0.
It changes what the site *says* about the valuation, and how the comps file
records time. It does not change what the engine *computes*. The Sprint 0A
findings and measurements above are kept unchanged as the historical record.

### Public claims corrected

| Surface | Before | After |
| --- | --- | --- |
| `valuation.html` methodology intro | "datasets are refreshed weekly" | Datasets are published as JSON. The comps file records when its content last changed, separately from build time, and carries the provenance disclosure |
| `valuation.html` Step 6, FAQ (HTML + JSON-LD), changelog 2.2/2.3 | "documented" sale / "documented landmark sales" | "reported" sale / "reported landmark sales" (changelog 2.3 adds: provenance not independently verified) |
| `valuation.html` Step 6, FAQ | median and geometric blend mean "one outlier sale cannot inflate the estimate" | They are *intended to limit* outlier influence. The text says these safeguards are partial (F6) |
| `valuation.html` Scope and limitations | "directional estimates" | Experimental estimates, price accuracy not independently validated, a link to this audit, reported sales, and a listed sale does not establish another domain's value |
| `valuation.html` changelog | — | October 2026 disclosure row, explicitly with no scoring change |
| `kb/how-domain-valuation-works.html`, `kb/how-to-read-comparable-sales.html` | "documented" sale; "cannot inflate" / "no single outlier can distort" | "reported" sale; "limit the influence"; the provenance disclosure is attached to the dataset link |
| `kb/keyword-strength-and-naming-terrain.html` | "as the public sales record shows" | "as reported public sales indicate" |
| `llms.txt` | "Documented public domain sales"; "own documented sale" | "Reported public domain sales" + provenance disclosure; estimates labelled experimental |
| `index.html`, `about.html`, `knowledge-base.html` stat cards | "300+ Public sales anchors / references / signals" | "45 Reported sales in the comps dataset". No source in the repository supported 300+. The published comps file holds 45 records |

General market advice in the knowledge base is unchanged. For example, the line
saying a documented prior sale is strong evidence still stands: it describes a
standard to apply, not a claim about Sohadot's data.

### Timestamp behaviour corrected

`scripts/generate_valuation_data.py` now:

- normalises the seed deterministically and hashes the normalised sales
  (`content_sha256`);
- carries `content_updated` forward unchanged while the hash is unchanged, and
  leaves the file byte-identical, so the weekly workflow makes no commit;
- advances `content_updated` only when the sales content changes;
- writes `generated_at` only when the file is actually rewritten (a content or
  metadata change). It is never presented as data freshness;
- writes `source_verification` as `not_verified` / `last_verified: null`. A
  verification date can come only from a human-recorded
  `last_source_verification` value in the seed. Running the workflow never sets
  one;
- keeps `last_updated` / `last_updated_human` for compatibility, now mirroring
  `content_updated`.

**One-time bootstrap.** The previous file had only build timestamps, so its
`last_updated` could not be reused as a content date. `content_updated` was set
once to `2026-06-12T06:24:11Z`, the date of commit `f475400`, the last commit
that modified `data/valuation_comps_seed.json` in GitHub history. The basis is
recorded in `content_updated_basis`. It is a content date, not a verification
date.

### Result card

- "Confidence: X" is now "Classification confidence: X". Below it is always-visible
  text (no hover required): *"This indicator describes confidence in the name's
  linguistic classification, not the accuracy of the estimated market price."*
- Directly above the price grid is a `role="note"` box: *"Experimental valuation
  estimate. Price accuracy has not yet been independently validated.
  Comparable-sales coverage and source verification are under review."* It also
  shows the dataset status: 45 reported sales · content last changed June 12,
  2026 · source verification: Not verified · methodology v2.5.
- The comps section is titled "Reported Comparable Sales". It states that
  provenance is not independently verified and that a listed sale does not
  establish another domain's value.
- The closing note calls the estimate experimental and refers to "reported"
  public sales.
- `valuation-ui.js` cache key moved to `?v=2.5.1`. The engine and its data cache
  key (`2.5`) are unchanged.

### Deliberately unchanged

Scoring formulas, pricing multipliers, lexical classification, comps matching,
all 45 sale prices, classes and keyword tags, use-case logic,
`js/valuation-engine.js` and `data/valuation_config.json`. The 19 class
disagreements (F4) were **not** rewritten to match the classifier, which is not
ground truth.

### Tests executed (2026-10-08)

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` (15 tests: determinism, content vs build time, legacy bootstrap, verification status, disclosure validator incl. negative case, engine baseline, audit gates) | 15 passed |
| `python3 scripts/validate_valuation_disclosures.py` (new) | PASS |
| All existing `scripts/validate_*.py` validators | PASS |
| `python3 scripts/audit_valuation_evidence.py --as-of-year 2026` | 0 FAIL, 100 WARN (unchanged from 0A) |
| `... --strict` | exit 1, as intended (0/45 records with provenance) |
| `node scripts/valuation_backtest.mjs` before vs after | JSON report identical. LOO median abs. log10 error still 1.925, within 10× still 31.1% |
| Engine snapshot (45 seed domains + 15 probes; score, class, confidence, comps, pricing) | identical to the pre-change baseline |
| Generator run twice on the published seed | second run: "unchanged … not rewritten"; file byte-identical |
| Chromium render at 1366 px and 375 px (`zuno.com`) | notice above prices, labels visible without hover, no horizontal scroll, no console errors |
| `git diff --check` | clean |

### Remaining evidence gaps (unchanged by design)

F1 (0/45 provenance), F3 (landmark skew and age), F4 (19 class disagreements),
F5 (15 dead and 18 semantic tags), F6 (landmark comps reaching ordinary names),
F7 (leave-one-out accuracy) and F8 (no holdout) all remain. The disclosures
describe these limits; they do not fix them.

### Sprint 1 readiness conditions

1. Each of the 45 records is verified against a primary or reputable secondary
   source, or removed or marked `reference_only`. No placeholder sources.
2. The Sprint 1 evidence schema is adopted, and `audit_valuation_evidence.py
   --strict` passes and becomes a mandatory gate.
3. An independent holdout set is frozen before any methodology change.
4. Any change to comps matching, classes or tags ships with a version bump, a
   new engine baseline, and before/after holdout metrics.
