# Independent Holdout Protocol

- **Protocol version:** `holdout-protocol/v1`
- **Status:** **NOT_READY**, recorded in `research/valuation-evidence/holdout/status.v1.json`
- **Enforcement:** §9 lists which requirements `scripts/validate_evidence_registry.py`
  enforces today and which are `NOT_IMPLEMENTED`. The status file carries the
  same map, and the validator fails if the two differ.
- **Why not ready:** no independently sourced transactions have been selected,
  obtained under usable rights, or frozen. The 45 published comps are
  calibration material and are never eligible as a holdout.

This protocol must be approved and the holdout frozen **before** any Sprint 1B
methodology change. Until then, no statement may claim that Sohadot's
valuation accuracy has been independently tested.

## 1. Purpose

The holdout measures how a valuation model performs on sales it has never
seen. It answers one question: *did a methodology change make estimates
better on independent data?* It is never used to fit, tune or choose
parameters.

## 2. Eligibility, fixed before any performance is inspected

A transaction may enter the holdout only if all of the following hold:

1. **Evidence:** `VERIFIED` or `REPORTED` under the Transaction Evidence
   Registry v1 standard, with no material conflict.
2. **Domain-only:** `transaction_type: DOMAIN_ONLY`. Business acquisitions,
   multi-domain bundles and domain-plus-assets deals are excluded.
3. **Price:** `EXACT` or `ROUNDED`. No undisclosed, approximate, lower-bound
   or structured prices. Consideration is cash or unknown, never stock,
   crypto or revenue share.
4. **Rights:** storage and commercial-modelling rights are granted, each with
   a recorded basis. Unknown or restricted rights exclude the record.
5. **Independence:** the domain does not appear in the registry, the
   published comps seed or the published comps file, in any transaction
   (repeat-sale leakage).
6. **Name independence:** names are normalised (case, `www.`, trailing dot,
   IDNA). The holdout domain must not share its second-level name, or a
   hyphen-stripped variant of it, with any of those sources on any extension
   (e.g. `example.com` vs `example.net` vs `ex-ample.io`).
7. **Source independence:** no more than 25% of holdout records come from any
   single source, and none comes from a source that supplied calibration
   records in the same batch, unless documented and approved.
8. **Chronology:** where practical, every holdout sale is dated after the
   latest calibration sale (a time-forward split). Exceptions are listed in
   the manifest.

Exclusions are recorded with a reason. Records are never removed after
results are seen.

## 3. Stratification

Report results by stratum, never only as a single average. Strata:

| Dimension | Bands |
| --- | --- |
| Price (USD equivalent at sale date) | < $2,500 · $2,500–$10k · $10k–$100k · $100k–$1M · ≥ $1M (reported separately and excluded from the headline metric) |
| Extension group | `.com` · other legacy gTLDs (`.net`, `.org`) · major ccTLD/new-gTLD brands (`.ai`, `.io`, `.co`) · other |
| Naming class | dictionary word · compound/keyword · brandable/invented · personal name · numeric/acronym (classified **independently of the engine**, by documented human rules, so the model under test cannot shape its own test labels) |
| Market side | end-user acquisition · investor trade · unknown |

**Target minimums before `FROZEN`:**

- at least 150 transactions;
- at least 25 in each of the three lowest price bands;
- at least 20 non-`.com` transactions.

If a stratum cannot reach its minimum, its results are reported as
indicative only.

## 4. Freezing

1. Assemble the candidate set from sources not used for calibration.
2. Apply §2 and record every exclusion with its reason.
3. Write the holdout manifest (transaction IDs and evidence fields) to
   **private storage outside this public repository**.
4. Compute SHA-256 over the canonical manifest JSON.
5. Update the status file to `status: FROZEN`, with `frozen_at`,
   `manifest_sha256`, `record_count` and `storage_location` (a description,
   not a link or path).
6. Commit only the status change, through a reviewed pull request. The
   manifest declares `"kind": "sohadot-holdout-manifest"` and is hashed as
   canonical JSON (sorted keys, compact separators).

**Readiness gate.** `FROZEN` is permitted only when every control in §9 is
`ENFORCED`. The status file carries a `readiness_gate` computed from those
controls (`frozen_permitted`, `blocking_controls`), and the validator
rejects any edited value. While any control is `NOT_IMPLEMENTED`, a `FROZEN`
status fails even with a valid private manifest. Today `frozen_permitted` is
`false`, with 7 blocking controls, and the status remains `NOT_READY`.

**Fail-closed verification.** A `FROZEN` status is never accepted on its own.
The validator fails unless it is run with `--holdout-manifest <private path>`
and the manifest:
- lies outside the repository;
- matches `manifest_sha256`;
- has exactly `record_count` records, at least 150;
- contains only eligible records under §2;
- draws no more than 25% of its records from any single source;
- does not overlap the registry, published seed or comps by domain, repeat
  sale or normalised name.

CI cannot see the private manifest, so a `FROZEN` status fails in CI by
design. Evaluators run the private check, and its result is recorded in the
review of the status change.

After freezing, the manifest is immutable. Corrections create a new holdout
version with its own hash. The old version's results are kept and labelled.

## 5. Protection against repeated tuning

- **Access:** model developers see only aggregate metrics per stratum, never
  record-level holdout errors.
- **Budget:** each methodology version may be evaluated against a holdout
  version at most once for its release decision. Every evaluation is logged
  (date, engine version, manifest hash, metrics) in the private store, and
  its summary metrics are published.
- **Development set:** iterative tuning uses calibration data (leave-one-out)
  or a separate development split, never the holdout.
- **Refresh:** after about 5 evaluated versions, or 12 months, a new holdout
  version is frozen from newer sales. The old one is retired and published
  as a historical result.

## 6. Isolation from production

- Holdout records never appear in `data/` or anywhere the website serves.
- The public registry rejects `HOLDOUT_CANDIDATE` records.
- The validator rejects any file in `research/valuation-evidence/holdout/`
  other than `status.v1.json`, any file anywhere in the repository whose
  name looks like a holdout manifest, and any JSON file containing the
  manifest marker.
- Keeping research files out of the GitHub Pages artifact is handled by a
  separate filtered-deployment change and is `NOT_IMPLEMENTED` here. Filtering
  Pages never makes files in this public repository private, so holdout
  records must never be committed at all.
- Evaluation runs `scripts/valuation_backtest.mjs --holdout <private file>`.
  That script refuses exact-domain overlap with the comps only. Its
  second-level-name check is `NOT_IMPLEMENTED`; run the validator's manifest
  check first.

## 7. Metrics, set before any results are seen

- Median absolute log10 error of the retail midpoint.
- Share of estimates within 2× and within 10× of the sale price.
- Share of sale prices inside the stated retail band.
- Signed median error, to show bias.

All are reported per stratum, with the stratum's n. A methodology change
ships only if holdout error does not worsen in the sub-$100k strata. Any
worsening in other strata is disclosed.

## 8. Readiness checklist

| Requirement | State |
| --- | --- |
| Protocol documented | Done (this file) |
| Status file and fail-closed validator | Done (`NOT_READY`; see §9) |
| Independent sources with usable rights identified | **Not done.** Owner decision on sources/licences needed |
| Candidate set assembled under §2 | Not done |
| Private storage arranged | **Not done.** Owner decision needed |
| Manifest frozen and hash recorded | Not done |

## 9. Implemented controls vs protocol requirements

This table is generated from `HOLDOUT_CONTROLS` in
`scripts/validate_evidence_registry.py`, and the status file must match it.
`NOT_IMPLEMENTED` rows are protocol requirements with no code yet. They must
be implemented, or checked manually and documented, before a `FROZEN` holdout
is relied on for those properties.

| Control | State |
| --- | --- |
| `status_shape_and_null_fields_when_not_ready` | ENFORCED |
| `frozen_fails_closed_without_private_manifest` | ENFORCED |
| `frozen_metadata_valid_hash_count_date_storage` | ENFORCED |
| `manifest_outside_repository` | ENFORCED |
| `manifest_hash_matches_status` | ENFORCED |
| `manifest_record_count_matches_and_minimum_150` | ENFORCED |
| `manifest_record_eligibility` | ENFORCED |
| `manifest_source_concentration_max_25_percent` | ENFORCED |
| `overlap_with_registry_transactions_and_repeat_sales` | ENFORCED |
| `overlap_with_published_seed_and_comps` | ENFORCED |
| `overlap_with_normalised_name_variants` | ENFORCED |
| `no_holdout_candidates_in_public_registry` | ENFORCED |
| `no_holdout_manifest_files_in_repository` | ENFORCED |
| `stratum_minimums` | NOT_IMPLEMENTED |
| `chronological_split` | NOT_IMPLEMENTED |
| `independent_naming_class_labels` | NOT_IMPLEMENTED |
| `evaluation_budget_and_logging` | NOT_IMPLEMENTED |
| `aggregate_only_access_for_developers` | NOT_IMPLEMENTED |
| `backtest_second_level_overlap_check` | NOT_IMPLEMENTED |
| `pages_artifact_excludes_research_files` | NOT_IMPLEMENTED |
