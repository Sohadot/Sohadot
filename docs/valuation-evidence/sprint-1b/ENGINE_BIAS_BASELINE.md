# Engine v2.5: Comparable-Selection Bias Baseline

- **Status:** Sprint 1B research, first deliverable (2026-10-09). No production change.
- **Engine:** `js/valuation-engine.js` v2.5, read and never modified. Comps:
  `data/valuation_comps.json` (45 sales).
- **Reproduce:**
  - `node scripts/assess_comparable_selection.mjs` prints the summary. The full
    output is `research/valuation-evidence/sprint-1b/engine-bias-baseline.v1.json`,
    and a test checks it still matches the engine.
  - `node scripts/valuation_backtest.mjs` gives the leave-one-out figures.
- **Units:** errors and effects are log10 ratios. 1.0 means 10×, 0.301 means 2×.
  "Retail mid" is the geometric mean of the engine's retail band.

> **READ FIRST: synthetic probes and simulated data. Not accuracy metrics.**
>
> | Section | Data | What it can show |
> | --- | --- | --- |
> | §2 F1, F2 | **Synthetic probe corpus**: 805 generated names run through the real engine and the real 45 comps | How much the comps move the engine's output. Not whether any estimate is right. |
> | §2 F3 | Real sales: leave-one-out on the 45 published comps | Internal error on those 45 sales only; not externally validated |
> | §4, §5 | **Simulated comps** from an assumed price distribution | Direction and rough size of the tie-breaker effect as a dataset grows. Not real prices. |
>
> The "about 10×" comp effect is a probe-corpus finding about engine
> behaviour. It is not an externally validated accuracy metric, and it does
> not say how far v2.5 is from real market prices. The probes are generated
> names, not valuations of real assets or real query traffic.

## 1. How v2.5 selects and uses comparables

`findComparableSales` (lines 340–375):

| Step | Rule |
| --- | --- |
| Match score | +18 same extension; +20 same engine class; +16 − 2×(length difference), floored at 0; +12 per shared commercial keyword; +50 same second-level name |
| Eligibility | Score ≥ 30, and the comp shares the class, a keyword or the exact name |
| Ordering | Score, descending; **ties broken by price, descending** |
| Limit | **First 4** only |

`refinePricingWithComparables` (lines 383–420):

| Case | Effect on the estimate |
| --- | --- |
| Same name and extension already sold | Midpoint = 0.5 × that price; retail band 0.9–1.4 × that price. No adjustment for time or currency. |
| Same name on another extension | Geometric blend, 50% weight on that sale's price |
| Otherwise | Geometric blend, 30% weight on the **median of the 4 selected comps** |

The score has coarse steps. Two comps with the same class and extension
differ only by length, in steps of 2 points. Ties are therefore common, and
the price tie-breaker often decides which comps are used.

## 2. Findings on the current 45 comps

### F1. The comps dominate the output, and they are mostly landmark sales (synthetic probe corpus)

- 28 of the 45 comps are sales of $1M or more.
- 805 probe names were spread across common words, commercial keywords,
  keyword compounds, given names, invented names and three-letter strings,
  on .com, .net, .org, .io, .ai and .co.

| Measure | Value |
| --- | --- |
| Probes that use comps | 91.6% |
| Median comp effect when used | +1.029 (×10.7) |
| Probes moved up by 10× or more | 55.9% |
| Median retail mid, all probes: v2.5 / same engine with no comps | $48,269 / $4,343 |
| Median of the selected comps' median price | $1,500,000 |
| Most-used comps (share of probes) | voice.com $30M (29.2%), diamond.com $7.5M (21.6%), whisky.com $3.1M (19.8%), aluren.com $1,524 (16.8%), veritas.com $95k (15.9%) |

By probe group (median retail mid, with comps / without):

| Group | With comps | Without comps | Median comp effect |
| --- | --- | --- | --- |
| Common words | $52,642 | $4,910 | +1.036 |
| Exact commercial keywords | $72,652 | $6,147 | +1.063 |
| Keyword compounds | $72,652 | $5,706 | +1.119 |
| Given names | $10,632 | $3,555 | +0.480 |
| Invented names | $4,894 | $3,273 | +0.160 |
| Three-letter strings | $1,072 | $1,072 | none (3% use comps) |

- **Why:** any dictionary or commercial-keyword name shares a class with
  landmark sales such as voice.com, diamond.com and whisky.com. A 30% weight
  on a median comp price in the millions multiplies a base estimate of a few
  thousand dollars about tenfold.
- **Extensions:** the extension adds only 18 points, so .net, .org, .io and
  .co queries draw the same .com landmarks (median effect +0.97 to +1.06).

### F2. The 4-result limit and the descending-price tie-breaker (synthetic probe corpus)

- **Frequency:** in 53.8% of probes the 4th place falls inside a group of
  comps with the same score, so the tie-breaker decides which comps are used.
- **Effect today is small,** because the eligible comps are uniformly
  expensive:

  | Tie-breaker | Median change vs v2.5 | 10th percentile | Probes moved 2× or more |
  | --- | --- | --- | --- |
  | Ascending price | −0.032 | −0.178 | 3.4% |
  | Neutral (median of the tied group) | 0.000 | −0.094 | |

- **The rule is biased upward by construction.** When ties exceed the free
  places, it always takes the most expensive tied comps. Sections 4 and 5
  show that this bias grows as the dataset grows.

### F3. Leave-one-out accuracy on the 45 comps (real sales; internal, not externally validated)

| Recorded price band | n | Median signed error | Median absolute error |
| --- | --- | --- | --- |
| ≥ $1M | 28 | −2.209 (about 160× too low) | 2.209 |
| $100k–$1M | 5 | −0.826 | 0.826 |
| $10k–$100k | 4 | −0.281 | 0.443 |
| < $10k | 8 | +0.425 (about 2.7× too high) | 0.425 |

- **Overall:** median absolute error 1.925; 31.1% of estimates within 10×;
  2.2% inside the retail band.
- **Pattern:** the engine compresses prices. Landmarks are badly
  underestimated, and the few ordinary sales are overestimated.
- **Too few cases:** with only 8 sales under $10k, the sub-$10k result is
  not a reliable estimate.

### F4. Other structural limits that affect expansion

1. **Coarse comparability:** class, extension and length only. Comps are
   never weighted by date, market side, venue or evidence status.
2. **No evidence or rights filter:** `valuation_comps.json` has no
   evidence-status, market-side or rights fields. An unsourced figure anchors
   an estimate exactly like a verified one. In the Sprint 1A investigation,
   18 of the 45 published comps had no evidence found.
3. **Own-sale anchoring:**
   - The own-sale rule anchors to any earlier sale of the same name, however
     old, without time adjustment.
   - With more repeat sales in a larger dataset, stale prices would take
     over more estimates.
4. **One currency, one market:** there is no FX or market-side handling.
   Wholesale (investor) and retail (end-user) prices differ systematically,
   and v2.5 cannot tell them apart.

## 3. What the 4-result limit means

Four comps are few, but a small k is not the main issue. The issues are which
four are chosen and what pool they come from:

- With 45 comps, 4 slots are mostly filled by landmarks (F1).
- As the pool grows, ties grow, and price-descending selection fills the 4
  slots from the top of the price distribution (Sections 4 and 5).
- The median of 4 values is sensitive to one or two outliers.

## 4. SIMULATED DATA: tie-breaker bias grows with the dataset

- **Synthetic sales:** log-normal prices with a median of $2,500 and a log10
  standard deviation of 0.6. Classes, extensions and lengths are drawn from
  fixed mixes. The price assumption is illustrative only.
- **Setup:** 400 synthetic queries × 5 replicates per size.
- **Metric:** "Selected vs eligible" is the median price of the 4 selected
  comps, against the median price of all eligible comps (log10).

| Synthetic comps | Median eligible per query | Tie-breaker decides the cut | v2.5 (price ↓) | Price ↑ | Neutral |
| --- | --- | --- | --- | --- | --- |
| 45 | 12 | 44.1% | +0.124 | 0.000 | 0.000 |
| 200 | 55 | 73.6% | +0.200 | −0.171 | +0.006 |
| 500 | 137 | 78.1% | +0.349 (×2.2) | −0.284 | +0.019 |
| 2,000 | 531 | 83.8% | +0.595 (×3.9) | −0.499 | +0.006 |
| 10,000 | 2,576 | 92.4% | +0.962 (×9.2) | −0.925 | −0.001 |

**Reading:**
- Under the v2.5 rule, adding ordinary sales would push the selected comps
  further toward the expensive end, by about ×2 at 500 sales and ×9 at
  10,000.
- A neutral tie-breaker keeps the selection representative at every size.
- Reversing the tie-breaker only flips the bias.

## 5. SIMULATED DATA: real comps plus simulated ordinary sales

- **Setup:** the 45 published comps stay in the pool and **simulated**
  ordinary sales are added (as in Section 4, using real commercial keywords).
  The dollar figures in this table come from simulated prices.
- **Engines:** the v2.5 engine and the same engine with a neutral
  tie-breaker, on the 805 probes.

| Synthetic sales added | v2.5: landmark share of selected comps | v2.5: median retail mid | Neutral: landmark share | Neutral: median retail mid |
| --- | --- | --- | --- | --- |
| 0 | 59.1% | $48,306 | 55.0% | $40,926 |
| 500 | 13.1% | $6,918 | 7.1% | $5,105 |
| 2,000 | 11.0% | $7,145 | 6.7% | $5,546 |
| 10,000 | 7.8% | $7,962 | 5.0% | $5,284 |

**Reading:**
1. Ordinary sales would largely displace landmark comps and cut the typical
   estimate about sevenfold.
2. Under v2.5, landmarks keep winning ties: they are still 8–13% of selected
   comps even at 10,000 added sales. The typical estimate also drifts upward
   as the pool grows.
3. The pilot must therefore test two things separately: the pool (landmark
   and reference-only sales kept out of calibration) and the selection rule.

## 6. Candidate methods for the research pilot (not selected)

The Sprint 1B pilot compares these methods against v2.5 on development data.
No method becomes production before the independent holdout is frozen and
evaluated.

| ID | Change | Tests |
| --- | --- | --- |
| C0 | v2.5 unchanged | Baseline |
| C1 | Neutral tie-breaker (median of the tied group) | Section 4 bias |
| C2 | Calibration pool only: evidence-checked, rights-cleared, single-domain cash sales; landmarks reference-only | F1, F4.2 |
| C3 | Similarity-weighted geometric mean over the top k (k tested 4–15), with a minimum-similarity floor | 4-result limit, outliers |
| C4 | Extension-aware matching (same extension or an explicit extension factor) | F1 cross-extension borrowing |
| C5 | Time adjustment and recency weighting; own-sale anchor only within a set age | F4.3 |
| C6 | Separate wholesale and retail estimates by market side | F4.4 |

Comparisons will be reported per stratum (price band, extension, naming
class, market side), never only as one average.

## 7. Limits of this assessment

- The probes are synthetic and do not represent real query traffic.
- The synthetic price distribution is an assumption. Its numbers show
  direction and rough size, not real-market magnitudes.
- Leave-one-out on 45 mostly landmark sales says little about ordinary
  names.
- No accuracy claim follows from this document.
