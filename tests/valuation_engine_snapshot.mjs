#!/usr/bin/env node
// Prints a deterministic snapshot of the valuation engine's numerical output
// (score, class, confidence, comps, pricing) for every seed sale and a fixed
// list of probe names. tests/test_valuation_integrity.py compares it with
// tests/fixtures/valuation_engine_baseline.json to prove that disclosure and
// data-freshness changes leave valuation behaviour untouched.
//
// Usage: node tests/valuation_engine_snapshot.mjs > snapshot.json

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const PROBES = [
  'zuno.com', 'kavorin.com', 'travelnook.com', 'shopvault.com', 'healthpilot.io',
  'aibrief.ai', 'river.com', 'vacances.fr', 'dactylograph.com', 'emma.net',
  'xqz.com', 'bestcheapaitools.net', 'payify.co', 'brain.io', 'example.org',
];

const cache = new Map();
const fetch = async (url) => {
  const rel = url.replace(/^\//, '').replace(/\?.*$/, '');
  if (!cache.has(rel)) cache.set(rel, JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')));
  return { json: async () => cache.get(rel) };
};

const context = vm.createContext({ fetch, Math, Set, Promise, JSON, Array, Object, String, Number });
vm.runInContext(fs.readFileSync(path.join(ROOT, 'js/valuation-engine.js'), 'utf8'), context);

const seed = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/valuation_comps_seed.json'), 'utf8'));
const domains = [...seed.sales.map(s => s.domain.toLowerCase()), ...PROBES];

const round = n => Math.round(n * 100) / 100;
const out = {};
for (const domain of domains) {
  const r = await context.evaluateDomain(domain);
  out[domain] = {
    score: r.score,
    classification: r.classification,
    confidence: r.confidence,
    keywordHits: r.keywordHits,
    comparables: r.comparables.map(c => c.domain),
    pricing: Object.fromEntries(Object.entries(r.pricing).map(([k, v]) => [k, typeof v === 'number' ? round(v) : v])),
    useCases: r.useCases,
  };
}
process.stdout.write(JSON.stringify(out, null, 2) + '\n');
