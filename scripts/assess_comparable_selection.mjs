#!/usr/bin/env node
// Sprint 1B: baseline bias assessment of comparable selection in engine v2.5.
//
// Research only. Runs the unmodified browser engine (js/valuation-engine.js) in
// a Node VM, exactly as scripts/valuation_backtest.mjs does, and measures how
// comparable selection shapes its output:
//
//   1. Probe corpus. A fixed, seeded set of names across naming classes and
//      extensions. These are probes of engine behaviour, not valuations of
//      real assets. For each probe it records whether comps are used, how many
//      comps are eligible, whether the 4-result cut falls inside a group of
//      tied match scores (so the descending-price tie-breaker decides), and
//      how far the comps move the estimate (the "comp uplift").
//   2. Tie-breaker sensitivity. The same probes with the tie-breaker reversed
//      (ascending price) and neutral (median of the tied group), run through
//      the real engine with only findComparableSales replaced inside the VM.
//   3. Expansion simulation. SYNTHETIC comps (never written anywhere, never
//      evidence) at sizes 45 to 10,000, to show how the 4-result limit and the
//      tie-breaker behave as a dataset grows. Synthetic prices come from a
//      stated, illustrative distribution, not from market data.
//
// The engine file is read, never modified. Output is deterministic.
//
// Usage:
//   node scripts/assess_comparable_selection.mjs                 # summary
//   node scripts/assess_comparable_selection.mjs --json out.json # full report
//   node scripts/assess_comparable_selection.mjs --json -        # full report to stdout

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ENGINE_SOURCE = fs.readFileSync(path.join(ROOT, 'js/valuation-engine.js'), 'utf8');
const SEED = 20261009;
const K = 4;

const jsonCache = new Map();
function readJson(rel) {
  if (!jsonCache.has(rel)) jsonCache.set(rel, JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')));
  return jsonCache.get(rel);
}

function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sample(rng, list, n) {
  const pool = [...list];
  const out = [];
  while (out.length < n && pool.length) out.push(pool.splice(Math.floor(rng() * pool.length), 1)[0]);
  return out;
}

// --- Engine harness -------------------------------------------------------

// Faithful copy of v2.5 scoring and eligibility, returning every eligible comp
// (not only the top 4). Checked against the engine's own output for each probe.
function scoreComps(sld, tld, classification, keywordHits, sales) {
  return sales.map(item => {
    let score = 0;
    if (item.tld === tld) score += 18;
    if (item.classification === classification) score += 20;
    score += Math.max(0, 16 - (Math.abs(item.length - sld.length) * 2));
    let shared = 0;
    if (keywordHits?.length) {
      shared = item.keywords.filter(k => keywordHits.includes(k)).length;
      score += shared * 12;
    }
    if (item.sld === sld) score += 50;
    const related = item.sld === sld || item.classification === classification || shared > 0;
    return { ...item, matchScore: score, related };
  }).filter(i => i.related && i.matchScore >= 30);
}

const TIE_BREAKERS = {
  // v2.5: higher score first, then higher price.
  price_desc: (a, b) => b.matchScore - a.matchScore || b.price - a.price,
  price_asc: (a, b) => b.matchScore - a.matchScore || a.price - b.price,
};

function selectWith(rule, eligible) {
  if (rule === 'tie_median') {
    // Neutral: fill the cut from the tied group in order of distance from the
    // group's median log price, so neither extreme is favoured.
    const sorted = [...eligible].sort((a, b) => b.matchScore - a.matchScore);
    if (sorted.length <= K) return sorted;
    const cutScore = sorted[K - 1].matchScore;
    const above = sorted.filter(i => i.matchScore > cutScore);
    const tied = sorted.filter(i => i.matchScore === cutScore);
    const logs = tied.map(i => Math.log(i.price)).sort((a, b) => a - b);
    const mid = logs.length % 2 ? logs[(logs.length - 1) / 2] : (logs[logs.length / 2 - 1] + logs[logs.length / 2]) / 2;
    tied.sort((a, b) => Math.abs(Math.log(a.price) - mid) - Math.abs(Math.log(b.price) - mid) || a.price - b.price);
    return [...above, ...tied].slice(0, K);
  }
  return [...eligible].sort(TIE_BREAKERS[rule]).slice(0, K);
}

function makeEngine(comps, rule = null) {
  const fetch = async (url) => {
    const rel = url.replace(/^\//, '').replace(/\?.*$/, '');
    const body = rel === 'data/valuation_comps.json' && comps ? comps : readJson(rel);
    return { json: async () => body };
  };
  const context = vm.createContext({ fetch, Math, Set, Promise, JSON, Array, Object, String, Number });
  vm.runInContext(ENGINE_SOURCE, context, { filename: 'valuation-engine.js' });
  if (rule) {
    // Replace only comparable selection; every other engine function is v2.5.
    context.__select = (sld, tld, cls, hits, data) => selectWith(rule, scoreComps(sld, tld, cls, hits, data.sales || []));
    vm.runInContext('findComparableSales = (...a) => __select(...a);', context);
  }
  return context;
}

const geoMid = p => Math.sqrt(p.retailLow * p.retailHigh);
const log10 = Math.log10;
const r3 = n => Math.round(n * 1000) / 1000;

function quantiles(values, qs = [0.1, 0.25, 0.5, 0.75, 0.9]) {
  const v = [...values].sort((a, b) => a - b);
  if (!v.length) return null;
  const at = q => v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
  return Object.fromEntries(qs.map(q => [`p${Math.round(q * 100)}`, r3(at(q))]));
}

// --- 1. Probe corpus -------------------------------------------------------

const BRANDABLE_SYLLABLES = ['ka', 'lo', 'ri', 'ven', 'zu', 'no', 'ta', 'mi', 'sol', 'ra', 'vi', 'den', 'lu', 'ko', 'ser', 'na', 'tor', 'qui', 'pa', 'lex'];
const COMPOUND_SUFFIXES = ['hub', 'lab', 'pro', 'base', 'nest', 'link', 'pilot', 'works', 'spot', 'flow'];
const TLDS = ['.com', '.com', '.com', '.net', '.org', '.io', '.ai', '.co'];

function buildProbes() {
  const rng = mulberry32(SEED);
  const words = readJson('data/english_words.json').words.filter(w => /^[a-z]{3,10}$/.test(w));
  const keywords = readJson('data/valuation_keywords.json').commercial_keywords.filter(w => /^[a-z]{2,10}$/.test(w));
  const given = readJson('data/names.json').given_names.filter(w => /^[a-z]{3,10}$/.test(w));
  const brandables = [];
  while (brandables.length < 150) {
    const n = 2 + Math.floor(rng() * 2);
    const s = Array.from({ length: n }, () => BRANDABLE_SYLLABLES[Math.floor(rng() * BRANDABLE_SYLLABLES.length)]).join('');
    if (!brandables.includes(s) && s.length <= 10) brandables.push(s);
  }
  const letters = 'abcdefghijklmnopqrstuvwxyz';
  const acronyms = Array.from({ length: 60 }, () => Array.from({ length: 3 }, () => letters[Math.floor(rng() * 26)]).join(''));
  const groups = {
    common_word: sample(rng, words, 300),
    keyword_exact: sample(rng, keywords, 80),
    keyword_compound: sample(rng, keywords, 150).map(k => k + COMPOUND_SUFFIXES[Math.floor(rng() * COMPOUND_SUFFIXES.length)]),
    given_name: sample(rng, given, 100),
    invented: brandables,
    three_letter: [...new Set(acronyms)],
  };
  const probes = [];
  for (const [group, slds] of Object.entries(groups)) {
    for (const sld of slds) probes.push({ group, domain: sld + TLDS[Math.floor(rng() * TLDS.length)] });
  }
  return probes;
}

async function runProbes(probes) {
  const comps = readJson('data/valuation_comps.json');
  const v25 = makeEngine(null);
  const none = makeEngine({ ...comps, sales: [] });
  const alt = { price_asc: makeEngine(null, 'price_asc'), tie_median: makeEngine(null, 'tie_median') };
  const rows = [];
  let mismatches = 0;
  for (const p of probes) {
    const r = await v25.evaluateDomain(p.domain);
    if (!r.ok) continue;
    const base = await none.evaluateDomain(p.domain);
    const eligible = scoreComps(r.sld, r.tld, r.classification, r.keywordHits, comps.sales);
    const replica = selectWith('price_desc', eligible).map(c => c.domain);
    if (replica.join() !== r.comparables.map(c => c.domain).join()) mismatches++;
    const sorted = [...eligible].sort(TIE_BREAKERS.price_desc);
    const cutScore = sorted.length >= K ? sorted[K - 1].matchScore : null;
    const tiedAtCut = cutScore === null ? 0 : eligible.filter(e => e.matchScore === cutScore).length;
    const aboveCut = cutScore === null ? 0 : eligible.filter(e => e.matchScore > cutScore).length;
    const row = {
      group: p.group,
      domain: p.domain,
      classification: r.classification,
      tld: r.tld,
      eligible: eligible.length,
      comps: r.comparables.map(c => c.domain),
      comp_median_price: r.comparables.length ? Math.round(r.comparables.map(c => c.price).sort((a, b) => a - b)[Math.floor((r.comparables.length - 1) / 2)]) : null,
      tie_decides_cut: eligible.length > K && tiedAtCut > K - aboveCut,
      retail_mid_v25: Math.round(geoMid(r.pricing)),
      retail_mid_no_comps: Math.round(geoMid(base.pricing)),
      comp_uplift_log10: r3(log10(geoMid(r.pricing) / geoMid(base.pricing))),
    };
    for (const [name, eng] of Object.entries(alt)) {
      const a = await eng.evaluateDomain(p.domain);
      row[`retail_mid_${name}`] = Math.round(geoMid(a.pricing));
      row[`delta_log10_${name}`] = r3(log10(geoMid(a.pricing) / geoMid(r.pricing)));
    }
    rows.push(row);
  }
  return { rows, mismatches };
}

function summarizeProbes(rows) {
  const withComps = rows.filter(r => r.comps.length);
  const usage = {};
  for (const r of withComps) for (const c of r.comps) usage[c] = (usage[c] || 0) + 1;
  const priceOf = Object.fromEntries(readJson('data/valuation_comps.json').sales.map(s => [s.domain, s.price]));
  const by = key => {
    const out = {};
    for (const r of rows) (out[r[key]] ||= []).push(r);
    return Object.fromEntries(Object.entries(out).map(([k, v]) => {
      const used = v.filter(r => r.comps.length);
      return [k, {
        n: v.length,
        share_with_comps: r3(used.length / v.length),
        median_comp_uplift_log10_when_used: used.length ? quantiles(used.map(r => r.comp_uplift_log10), [0.5]).p50 : null,
        median_retail_mid_v25: quantiles(v.map(r => r.retail_mid_v25), [0.5]).p50,
        median_retail_mid_no_comps: quantiles(v.map(r => r.retail_mid_no_comps), [0.5]).p50,
      }];
    }));
  };
  const tieRows = rows.filter(r => r.tie_decides_cut);
  return {
    probes: rows.length,
    share_with_comps: r3(withComps.length / rows.length),
    comp_uplift_log10_when_used: quantiles(withComps.map(r => r.comp_uplift_log10)),
    share_uplift_over_10x: r3(withComps.filter(r => r.comp_uplift_log10 >= 1).length / rows.length),
    median_comp_median_price: quantiles(withComps.map(r => r.comp_median_price), [0.5]).p50,
    share_where_tie_breaker_decides_cut: r3(tieRows.length / rows.length),
    tie_breaker_sensitivity_log10: {
      price_asc_vs_v25: quantiles(rows.map(r => r.delta_log10_price_asc)),
      tie_median_vs_v25: quantiles(rows.map(r => r.delta_log10_tie_median)),
      share_changed_over_2x_price_asc: r3(rows.filter(r => Math.abs(r.delta_log10_price_asc) >= log10(2)).length / rows.length),
    },
    most_used_comps: Object.entries(usage).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 10)
      .map(([d, n]) => ({ domain: d, price: priceOf[d], share_of_probes: r3(n / rows.length) })),
    by_group: by('group'),
    by_classification: by('classification'),
    by_tld: by('tld'),
  };
}

// --- 3. Expansion simulation (synthetic) -----------------------------------

// Illustrative assumption, not market data: ordinary sale prices are
// log-normal with a median of $2,500 and a log10 standard deviation of 0.6
// (so about 68% between ~$630 and ~$10,000). Classes, extensions and lengths
// are drawn from simple fixed mixes.
const SIM = {
  price_median: 2500,
  price_log10_sd: 0.6,
  classes: [['commercial_keyword', 0.35], ['dictionary_word', 0.2], ['brandable', 0.35], ['personal_name', 0.1]],
  tlds: [['.com', 0.7], ['.net', 0.08], ['.org', 0.07], ['.io', 0.07], ['.ai', 0.08]],
  sizes: [45, 200, 500, 2000, 10000],
  queries: 400,
  replicates: 5,
};

function pick(rng, mix) {
  let x = rng();
  for (const [v, w] of mix) { if ((x -= w) <= 0) return v; }
  return mix[mix.length - 1][0];
}

function gauss(rng) {
  return Math.sqrt(-2 * Math.log(rng() || 1e-12)) * Math.cos(2 * Math.PI * rng());
}

function syntheticSale(rng, i) {
  const cls = pick(rng, SIM.classes);
  const length = 3 + Math.floor(rng() * 10);
  const kw = cls === 'commercial_keyword' ? [`kw${Math.floor(rng() * 40)}`] : [];
  return {
    domain: `sim${i}`,
    sld: `sim${i}`,
    tld: pick(rng, SIM.tlds),
    classification: cls,
    length,
    keywords: kw,
    price: Math.round(SIM.price_median * 10 ** (SIM.price_log10_sd * gauss(rng))),
  };
}

function simulateExpansion() {
  const out = [];
  for (const size of SIM.sizes) {
    const acc = { size, tie_decides: 0, eligible: [], bias_desc: [], bias_asc: [], bias_median: [] };
    for (let rep = 0; rep < SIM.replicates; rep++) {
      const rng = mulberry32(SEED + size * 31 + rep);
      const sales = Array.from({ length: size }, (_, i) => syntheticSale(rng, i));
      for (let q = 0; q < SIM.queries; q++) {
        const query = syntheticSale(rng, `q${q}`);
        const eligible = scoreComps("x".repeat(query.length), query.tld, query.classification, query.keywords, sales);
        if (!eligible.length) continue;
        acc.eligible.push(eligible.length);
        const sorted = [...eligible].sort(TIE_BREAKERS.price_desc);
        if (sorted.length > K) {
          const cut = sorted[K - 1].matchScore;
          const above = eligible.filter(e => e.matchScore > cut).length;
          if (eligible.filter(e => e.matchScore === cut).length > K - above) acc.tie_decides++;
        }
        // Bias of the selected comps' median price against the median price
        // of every eligible comp, in log10 units (0 = representative).
        const med = arr => { const v = arr.map(c => c.price).sort((a, b) => a - b); const m = Math.floor(v.length / 2); return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2; };
        const ref = med(eligible);
        acc.bias_desc.push(log10(med(selectWith('price_desc', eligible)) / ref));
        acc.bias_asc.push(log10(med(selectWith('price_asc', eligible)) / ref));
        acc.bias_median.push(log10(med(selectWith('tie_median', eligible)) / ref));
      }
    }
    const n = acc.bias_desc.length;
    out.push({
      synthetic_comps: size,
      queries_with_comps: n,
      median_eligible_comps: quantiles(acc.eligible, [0.5]).p50,
      share_where_tie_breaker_decides_cut: r3(acc.tie_decides / n),
      selected_vs_eligible_median_log10: {
        v25_price_desc: quantiles(acc.bias_desc, [0.5]).p50,
        price_asc: quantiles(acc.bias_asc, [0.5]).p50,
        tie_median: quantiles(acc.bias_median, [0.5]).p50,
      },
    });
  }
  return out;
}

// --- 4. Mixed expansion (real comps + synthetic ordinary sales) ------------

// What happens if ordinary sales are added while the 45 published comps (mostly
// $1M+ landmark sales) stay in the same pool? Runs the real v2.5 engine and the
// neutral tie-breaker on the probe corpus, with SYNTHETIC ordinary sales drawn
// as in section 3, but using real commercial keywords so keyword matching
// behaves as it would on real data.
async function simulateMixed(probes) {
  const comps = readJson('data/valuation_comps.json');
  const keywords = readJson('data/valuation_keywords.json').commercial_keywords;
  const landmark = new Set(comps.sales.filter(s => s.price >= 1_000_000).map(s => s.domain));
  const out = [];
  for (const size of [0, 500, 2000, 10000]) {
    const rng = mulberry32(SEED + 7 * size + 1);
    const synthetic = Array.from({ length: size }, (_, i) => {
      const s = syntheticSale(rng, i);
      const sld = `sim${i}x`.padEnd(s.length, 'q');
      const kw = s.classification === 'commercial_keyword' ? [keywords[Math.floor(rng() * keywords.length)]] : [];
      return { ...s, domain: sld + s.tld, sld, length: sld.length, keywords: kw, year: 2025, notes: 'synthetic', price_display: '' };
    });
    const pool = { ...comps, sales: [...comps.sales, ...synthetic] };
    const engines = { v25_price_desc: makeEngine(pool), tie_median: makeEngine(pool, 'tie_median') };
    const row = { synthetic_ordinary_sales_added: size };
    for (const [name, eng] of Object.entries(engines)) {
      let selected = 0, landmarks = 0;
      const mids = [];
      for (const p of probes) {
        const r = await eng.evaluateDomain(p.domain);
        if (!r.ok) continue;
        selected += r.comparables.length;
        landmarks += r.comparables.filter(c => landmark.has(c.domain)).length;
        mids.push(log10(geoMid(r.pricing)));
      }
      row[name] = {
        share_of_selected_comps_that_are_landmarks: r3(landmarks / Math.max(1, selected)),
        median_retail_mid_usd: Math.round(10 ** quantiles(mids, [0.5]).p50),
      };
    }
    out.push(row);
  }
  return out;
}

// --- Main ------------------------------------------------------------------

async function main() {
  const argv = process.argv.slice(2);
  let jsonOut = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--json') jsonOut = argv[++i];
    else throw new Error(`Unknown argument: ${argv[i]}`);
  }
  const probes = buildProbes();
  const { rows, mismatches } = await runProbes(probes);
  if (mismatches) throw new Error(`Selection replica disagrees with engine v2.5 on ${mismatches} probes`);
  const report = {
    kind: 'sohadot-comparable-selection-assessment',
    status: 'RESEARCH_ONLY_NOT_FOR_PRODUCTION',
    engine_framework_version: /FRAMEWORK_VERSION = '([^']+)'/.exec(ENGINE_SOURCE)?.[1],
    comps_count: readJson('data/valuation_comps.json').sales.length,
    seed: SEED,
    k: K,
    units: 'log10 ratios; 1.0 = 10x, 0.301 = 2x. Retail mid = geometric mean of the retail band.',
    selection_replica_matches_engine: true,
    probe_corpus_note: 'SYNTHETIC probe names run through the real engine and the 45 published comps. Measures engine behaviour (how far comps move estimates), not accuracy; not externally validated.',
    probe_summary: summarizeProbes(rows),
    expansion_simulation: {
      warning: 'SYNTHETIC comps from an illustrative price distribution. Not evidence and not a forecast of real prices.',
      assumptions: SIM,
      results: simulateExpansion(),
    },
    mixed_expansion_simulation: {
      warning: 'The 45 published comps plus SYNTHETIC ordinary sales (section 3 distribution). Illustrative only.',
      landmark_definition: 'published comp with price >= $1,000,000',
      results: await simulateMixed(probes),
    },
    probe_rows: rows,
  };
  if (jsonOut === '-') {
    process.stdout.write(JSON.stringify(report, null, 1) + '\n');
    return;
  }
  const s = report.probe_summary;
  console.log(`Comparable-selection assessment: engine v${report.engine_framework_version}, ${report.comps_count} comps, ${s.probes} SYNTHETIC probes`);
  console.log('  Behavioural findings on a synthetic probe corpus and simulated comps; not accuracy metrics.');
  console.log(`  probes using comps: ${s.share_with_comps}`);
  console.log(`  comp uplift (log10) when used: ${JSON.stringify(s.comp_uplift_log10_when_used)}`);
  console.log(`  probes moved >=10x by comps: ${s.share_uplift_over_10x}`);
  console.log(`  tie-breaker decides the 4-result cut: ${s.share_where_tie_breaker_decides_cut}`);
  console.log(`  price_asc vs v2.5 (log10): ${JSON.stringify(s.tie_breaker_sensitivity_log10.price_asc_vs_v25)}`);
  console.log(`  most used comps: ${s.most_used_comps.slice(0, 5).map(c => `${c.domain} ${c.share_of_probes}`).join(', ')}`);
  console.log('Expansion simulation (SIMULATED comps):');
  for (const r of report.expansion_simulation.results) {
    console.log(`  N=${r.synthetic_comps}: eligible median ${r.median_eligible_comps}, tie decides ${r.share_where_tie_breaker_decides_cut}, selected-vs-eligible median log10 ${JSON.stringify(r.selected_vs_eligible_median_log10)}`);
  }
  console.log('Mixed expansion (45 real + SIMULATED ordinary sales):');
  for (const r of report.mixed_expansion_simulation.results) console.log(`  +${r.synthetic_ordinary_sales_added}: ${JSON.stringify({ v25: r.v25_price_desc, tie_median: r.tie_median })}`);
  if (jsonOut) {
    fs.writeFileSync(path.resolve(jsonOut), JSON.stringify(report, null, 1) + '\n');
    console.log(`Wrote ${jsonOut}`);
  }
}

main().catch(err => { console.error(err); process.exit(1); });
