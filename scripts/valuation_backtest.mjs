#!/usr/bin/env node
// Sprint 0 — Evidence & Accuracy Audit: accuracy backtest for the Sohadot
// valuation engine.
//
// Runs the unmodified browser engine (js/valuation-engine.js) in a Node VM,
// with fetch() served from the local data/ directory, and measures how well
// its estimates match recorded sale prices.
//
// Three passes:
//   1. In-sample      — every sale evaluated with the full comps dataset.
//                       The sale itself is in the evidence, so the engine
//                       anchors to its own price: this pass measures leakage,
//                       not accuracy.
//   2. Leave-one-out  — every sale evaluated with itself removed from the
//                       comps. This is the honest accuracy figure available
//                       from the current data.
//   3. Holdout        — optional (--holdout path.json, same shape as the
//                       seed): sales never used for calibration, evaluated
//                       against the full comps dataset.
//
// Also reports where the engine's own classifier disagrees with the class
// recorded on a sale (comps match on class, so a mislabelled sale is matched
// to subjects the engine would never put in that class), and evaluates a few
// synthetic probe names to expose which comps they draw.
//
// Usage:
//   node scripts/valuation_backtest.mjs
//   node scripts/valuation_backtest.mjs --holdout data/valuation_holdout.json
//   node scripts/valuation_backtest.mjs --json report.json
//
// Read-only: never writes to the repository unless --json points there.

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// Synthetic, unregistered-looking names chosen to exercise each comps route.
// They are probes of engine behaviour, not claims about any real domain.
const PROBES = [
  'zuno.com',          // 4-letter invented brandable
  'kavorin.com',       // 7-letter invented brandable
  'travelnook.com',    // compound containing "travel"
  'shopvault.com',     // compound containing "shop"
  'healthpilot.io',    // compound containing "health", non-.com
  'aibrief.ai',        // compound containing "ai" on .ai
];

function parseArgs(argv) {
  const args = { holdout: null, json: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--holdout') args.holdout = argv[++i];
    else if (argv[i] === '--json') args.json = argv[++i];
    else throw new Error(`Unknown argument: ${argv[i]}`);
  }
  return args;
}

const jsonCache = new Map();
function readJson(rel) {
  if (!jsonCache.has(rel)) {
    jsonCache.set(rel, JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')));
  }
  return jsonCache.get(rel);
}

const ENGINE_SOURCE = fs.readFileSync(path.join(ROOT, 'js/valuation-engine.js'), 'utf8');

// A fresh engine per comps dataset: the engine caches its data in a
// module-level variable, so each evidence set needs its own context.
function makeEngine(compsOverride) {
  const fetch = async (url) => {
    const rel = url.replace(/^\//, '').replace(/\?.*$/, '');
    const body = rel === 'data/valuation_comps.json' && compsOverride
      ? compsOverride
      : readJson(rel);
    return { json: async () => body };
  };
  const context = vm.createContext({ fetch, Math, Set, Promise, JSON, Array, Object, String, Number });
  vm.runInContext(ENGINE_SOURCE, context, { filename: 'valuation-engine.js' });
  return context;
}

function normalizeSale(item) {
  const domain = item.domain.trim().toLowerCase();
  const sld = domain.split('.')[0];
  return {
    domain,
    price: item.price,
    price_display: '$' + item.price.toLocaleString('en-US'),
    year: item.year,
    tld: item.tld,
    classification: item.classification,
    keywords: item.keywords || [],
    notes: item.notes || '',
    sld,
    length: sld.length,
  };
}

const log10 = Math.log10;
const geoMid = (lo, hi) => Math.sqrt(lo * hi);

function scoreEstimate(sale, result) {
  const p = result.pricing;
  const retailMid = geoMid(p.retailLow, p.retailHigh);
  return {
    domain: sale.domain,
    price: sale.price,
    year: sale.year,
    classification: sale.classification,
    engine_classification: result.classification,
    comps_used: result.comparables.map(c => c.domain),
    anchored_to_own_sale: Boolean(p.anchoredToOwnSale),
    wholesale_mid: Math.round(p.midpoint),
    retail_low: Math.round(p.retailLow),
    retail_high: Math.round(p.retailHigh),
    // Positive: engine above the recorded price. One unit = 10x.
    log10_error_retail_mid: +(log10(retailMid) - log10(sale.price)).toFixed(3),
    in_retail_band: sale.price >= p.retailLow && sale.price <= p.retailHigh,
    in_full_span: sale.price >= p.wholesaleLow && sale.price <= p.retailHigh,
  };
}

function median(values) {
  const v = [...values].sort((a, b) => a - b);
  if (!v.length) return null;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

function summarize(rows) {
  const errs = rows.map(r => r.log10_error_retail_mid);
  const abs = errs.map(Math.abs);
  return {
    n: rows.length,
    median_abs_log10_error: median(abs) === null ? null : +median(abs).toFixed(3),
    median_signed_log10_error: median(errs) === null ? null : +median(errs).toFixed(3),
    within_2x: rows.length ? +(abs.filter(e => e <= log10(2)).length / rows.length).toFixed(3) : null,
    within_10x: rows.length ? +(abs.filter(e => e <= 1).length / rows.length).toFixed(3) : null,
    in_retail_band: rows.length ? +(rows.filter(r => r.in_retail_band).length / rows.length).toFixed(3) : null,
    in_full_span: rows.length ? +(rows.filter(r => r.in_full_span).length / rows.length).toFixed(3) : null,
    anchored_to_own_sale: rows.filter(r => r.anchored_to_own_sale).length,
  };
}

function groupBy(rows, keyFn) {
  const out = {};
  for (const r of rows) (out[keyFn(r)] ||= []).push(r);
  return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, summarize(v)]));
}

function priceBand(price) {
  if (price < 10_000) return '<$10k';
  if (price < 100_000) return '$10k-$100k';
  if (price < 1_000_000) return '$100k-$1M';
  return '>=$1M';
}

async function evaluateAll(sales, compsFor) {
  const rows = [];
  for (const sale of sales) {
    const engine = makeEngine(compsFor(sale));
    const result = await engine.evaluateDomain(sale.domain);
    if (!result.ok) throw new Error(`${sale.domain}: ${result.error}`);
    rows.push(scoreEstimate(sale, result));
  }
  return rows;
}

function fmtMoney(n) {
  return '$' + Math.round(n).toLocaleString('en-US');
}

function printSummary(title, s) {
  console.log(`\n${title}`);
  for (const [k, v] of Object.entries(s)) console.log(`  ${k}: ${v}`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const generated = readJson('data/valuation_comps.json');
  const sales = readJson('data/valuation_comps_seed.json').sales.map(normalizeSale);

  // 1. In-sample (leakage).
  const inSample = await evaluateAll(sales, () => null);

  // 2. Leave-one-out.
  const loo = await evaluateAll(sales, held => ({
    ...generated,
    sales: generated.sales.filter(s => s.domain !== held.domain),
  }));

  // 3. Optional independent holdout.
  let holdout = null;
  if (args.holdout) {
    const raw = JSON.parse(fs.readFileSync(path.resolve(args.holdout), 'utf8'));
    const held = (raw.sales || []).map(normalizeSale);
    const overlap = held.filter(h => generated.sales.some(s => s.domain === h.domain));
    if (overlap.length) {
      throw new Error(`Holdout overlaps the calibration comps: ${overlap.map(o => o.domain).join(', ')}`);
    }
    holdout = await evaluateAll(held, () => null);
  }

  // Classifier agreement: class recorded on the sale vs the engine's own.
  const mismatches = loo
    .filter(r => r.classification !== r.engine_classification)
    .map(r => ({ domain: r.domain, recorded: r.classification, engine: r.engine_classification }));

  // Probes.
  const probeEngine = makeEngine(null);
  const probes = [];
  for (const domain of PROBES) {
    const r = await probeEngine.evaluateDomain(domain);
    probes.push({
      domain,
      classification: r.classification,
      score: r.score,
      comps: r.comparables.map(c => `${c.domain} (${c.price_display}, ${c.year})`),
      wholesale_mid: Math.round(r.pricing.midpoint),
      retail_range: `${fmtMoney(r.pricing.retailLow)} - ${fmtMoney(r.pricing.retailHigh)}`,
    });
  }

  const report = {
    engine_framework_version: /FRAMEWORK_VERSION = '([^']+)'/.exec(ENGINE_SOURCE)?.[1],
    comps_count: generated.sales.length,
    in_sample: summarize(inSample),
    leave_one_out: summarize(loo),
    leave_one_out_by_classification: groupBy(loo, r => r.classification),
    leave_one_out_by_price_band: groupBy(loo, r => priceBand(r.price)),
    holdout: holdout ? summarize(holdout) : null,
    classification_mismatches: mismatches,
    probes,
    leave_one_out_rows: loo,
  };

  console.log(`Sohadot valuation backtest — engine v${report.engine_framework_version}, ${report.comps_count} comps`);
  console.log('Error unit: log10 of (engine retail midpoint / recorded price); 1.0 = off by 10x.');
  printSummary('In-sample (sale present in its own evidence — leakage check)', report.in_sample);
  printSummary('Leave-one-out (sale removed from evidence)', report.leave_one_out);
  console.log('\nLeave-one-out by recorded price band');
  for (const [band, s] of Object.entries(report.leave_one_out_by_price_band)) {
    console.log(`  ${band}: n=${s.n}, median |err|=${s.median_abs_log10_error}, median signed=${s.median_signed_log10_error}, in retail band=${s.in_retail_band}`);
  }
  console.log('\nLeave-one-out by recorded classification');
  for (const [cls, s] of Object.entries(report.leave_one_out_by_classification)) {
    console.log(`  ${cls}: n=${s.n}, median |err|=${s.median_abs_log10_error}, median signed=${s.median_signed_log10_error}, in retail band=${s.in_retail_band}`);
  }
  if (holdout) printSummary('Independent holdout', report.holdout);
  else console.log('\nIndependent holdout: none supplied (--holdout). No out-of-sample accuracy claim is possible yet.');

  console.log(`\nClassification mismatches (recorded vs engine): ${mismatches.length}`);
  for (const m of mismatches) console.log(`  ${m.domain}: recorded ${m.recorded}, engine ${m.engine}`);

  console.log('\nLeave-one-out rows (worst 12 by |error|)');
  for (const r of [...loo].sort((a, b) => Math.abs(b.log10_error_retail_mid) - Math.abs(a.log10_error_retail_mid)).slice(0, 12)) {
    console.log(`  ${r.domain}: recorded ${fmtMoney(r.price)}, engine retail ${fmtMoney(r.retail_low)}-${fmtMoney(r.retail_high)}, err ${r.log10_error_retail_mid}`);
  }

  console.log('\nSynthetic probes (behaviour checks, not valuations of real assets)');
  for (const p of probes) {
    console.log(`  ${p.domain} [${p.classification}, score ${p.score}] retail ${p.retail_range}`);
    for (const c of p.comps) console.log(`      comp: ${c}`);
  }

  if (args.json) {
    fs.writeFileSync(path.resolve(args.json), JSON.stringify(report, null, 2) + '\n');
    console.log(`\nWrote ${args.json}`);
  }
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
