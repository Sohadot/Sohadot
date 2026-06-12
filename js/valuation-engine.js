let VALUATION_DATA = null;

// Bump with each framework release so browsers never serve stale
// scoring data after a methodology update.
const FRAMEWORK_VERSION = '2.4';

async function loadValuationData() {
  if (VALUATION_DATA) return VALUATION_DATA;

  const v = '?v=' + FRAMEWORK_VERSION;
  const [
    config,
    keywords,
    lexicalWords,
    rareWords,
    names,
    industryMap,
    comps,
    englishWords
  ] = await Promise.all([
    fetch('/data/valuation_config.json' + v).then(r => r.json()),
    fetch('/data/valuation_keywords.json' + v).then(r => r.json()),
    fetch('/data/lexical_words.json' + v).then(r => r.json()),
    fetch('/data/rare_words.json' + v).then(r => r.json()),
    fetch('/data/names.json' + v).then(r => r.json()),
    fetch('/data/industry_map.json' + v).then(r => r.json()),
    fetch('/data/valuation_comps.json' + v).then(r => r.json()),
    fetch('/data/english_words.json' + v).then(r => r.json())
  ]);

  VALUATION_DATA = {
    config,
    keywords,
    lexicalWords,
    rareWords,
    names,
    industryMap,
    comps,
    dictionarySet: new Set(englishWords.words || [])
  };

  return VALUATION_DATA;
}

// The extended attested wordlist (~319k entries) is heavy, so it is
// fetched lazily — only when a name is not resolved by the common
// dictionary, curated entries, names, or keyword checks.
let EXTENDED_WORDS = null;

async function loadExtendedWords() {
  if (EXTENDED_WORDS) return EXTENDED_WORDS;
  const data = await fetch('/data/extended_words.json?v=' + FRAMEWORK_VERSION)
    .then(r => r.json())
    .catch(() => ({ words: [] }));
  EXTENDED_WORDS = new Set(data.words || []);
  return EXTENDED_WORDS;
}

function normalizeDomain(input) {
  return input
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/.*$/, '');
}

function splitDomain(domain) {
  const parts = domain.split('.');
  if (parts.length < 2) return null;

  const tld = '.' + parts.slice(1).join('.');
  const sld = parts[0];

  return { sld, tld };
}

function isValidDomainLike(input) {
  return /^[a-z0-9-]+\.[a-z.]{2,}$/i.test(input);
}

function getLengthAdjustment(config, len) {
  if (len >= 11) return config.length_adjustments["11_plus"] || 0;
  return config.length_adjustments[String(len)] || 0;
}

function detectCommercialKeywords(word, keywordsData) {
  const hits = [];
  for (const kw of keywordsData.commercial_keywords) {
    // Keywords shorter than 3 characters only match as the whole word
    // or at a word boundary, so "ai" fires on "aitools" but not "rain".
    const matched = kw.length >= 3
      ? word.includes(kw)
      : word === kw || word.startsWith(kw) || word.endsWith(kw);
    if (matched) hits.push(kw);
  }
  return hits;
}

function isCleanBrandable(word) {
  if (!/^[a-z]+$/.test(word)) return false;
  if (word.length < 4 || word.length > 12) return false;
  if (/(.)\1\1/.test(word)) return false;
  if (!/[aeiouy]/.test(word)) return false;
  // A doubled consonant ending reads as a typo unless it is one of the
  // natural English endings (ll, ss, ff, zz).
  if (/(.)\1$/.test(word) && !/(ll|ss|ff|zz|ee|oo)$/.test(word)) return false;
  return true;
}

function classifyDomain(sld, datasets) {
  const { lexicalWords, rareWords, names, keywords, dictionarySet } = datasets;

  const commercialHits = detectCommercialKeywords(sld, keywords);
  const isExactKeyword = keywords.commercial_keywords.includes(sld);

  // The name being itself a commercial term (exact-match domain)
  // outranks everything else.
  if (isExactKeyword) {
    return {
      classification: 'commercial_keyword',
      confidence: 'high',
      lexicalStatus: 'exact-match commercial keyword',
      keywordHits: commercialHits.length ? commercialHits : [sld],
      lexicalEntry: null
    };
  }

  if (lexicalWords[sld]) {
    return {
      classification: lexicalWords[sld].type,
      confidence: 'high',
      lexicalStatus: 'dictionary-attested word',
      keywordHits: [],
      lexicalEntry: lexicalWords[sld]
    };
  }

  if (rareWords[sld]) {
    return {
      classification: rareWords[sld].type,
      confidence: 'high',
      lexicalStatus: 'rare dictionary-attested word',
      keywordHits: [],
      lexicalEntry: rareWords[sld]
    };
  }

  if (names.given_names.includes(sld) || names.surnames.includes(sld)) {
    return {
      classification: 'personal_name',
      confidence: 'high',
      lexicalStatus: 'recognized personal name',
      keywordHits: [],
      lexicalEntry: null
    };
  }

  // Attested dictionary words rank by their lexical class even when a
  // commercial substring happens to appear inside them ("brain" is a
  // dictionary word, not an "ai" keyword domain).
  if (dictionarySet && dictionarySet.has(sld)) {
    return {
      classification: 'dictionary_word',
      confidence: 'high',
      lexicalStatus: 'dictionary-attested word',
      keywordHits: [],
      lexicalEntry: null
    };
  }

  // Compound names containing a commercial term ("aitools", "payify").
  if (commercialHits.length > 0) {
    return {
      classification: 'commercial_keyword',
      confidence: 'medium_high',
      lexicalStatus: 'commercial keyword pattern',
      keywordHits: commercialHits,
      lexicalEntry: null
    };
  }

  if (isCleanBrandable(sld)) {
    return {
      classification: 'brandable',
      confidence: 'medium',
      lexicalStatus: 'clean invented or brandable structure',
      keywordHits: [],
      lexicalEntry: null
    };
  }

  return {
    classification: 'random_low_quality',
    confidence: 'low',
    lexicalStatus: 'weak lexical legitimacy',
    keywordHits: [],
    lexicalEntry: null
  };
}

function estimateUseCases(result, industryMap) {
  const hits = new Set();
  const keywordHits = result.keywordHits || [];

  if (
    keywordHits.includes('ai') ||
    keywordHits.includes('agent') ||
    keywordHits.includes('agents') ||
    keywordHits.includes('gpt') ||
    keywordHits.includes('llm') ||
    keywordHits.includes('neural') ||
    keywordHits.includes('vision') ||
    keywordHits.includes('model')
  ) {
    industryMap.ai.forEach(v => hits.add(v));
  }

  if (
    keywordHits.includes('finance') ||
    keywordHits.includes('fintech') ||
    keywordHits.includes('pay') ||
    keywordHits.includes('payments') ||
    keywordHits.includes('wealth') ||
    keywordHits.includes('wallet') ||
    keywordHits.includes('bank') ||
    keywordHits.includes('cash') ||
    keywordHits.includes('credit') ||
    keywordHits.includes('loan') ||
    keywordHits.includes('loans') ||
    keywordHits.includes('mortgage') ||
    keywordHits.includes('trading') ||
    keywordHits.includes('forex')
  ) {
    industryMap.finance.forEach(v => hits.add(v));
  }

  if (
    keywordHits.includes('health') ||
    keywordHits.includes('therapy') ||
    keywordHits.includes('medical') ||
    keywordHits.includes('pharma') ||
    keywordHits.includes('clinic') ||
    keywordHits.includes('bio') ||
    keywordHits.includes('genomics')
  ) {
    industryMap.health.forEach(v => hits.add(v));
  }

  if (
    keywordHits.includes('legal') ||
    keywordHits.includes('law') ||
    keywordHits.includes('attorney')
  ) {
    industryMap.legal.forEach(v => hits.add(v));
  }

  if (
    keywordHits.includes('data') ||
    keywordHits.includes('cloud') ||
    keywordHits.includes('security') ||
    keywordHits.includes('cyber')
  ) {
    industryMap.tech.forEach(v => hits.add(v));
  }

  if (
    keywordHits.includes('solar') ||
    keywordHits.includes('energy') ||
    keywordHits.includes('battery') ||
    keywordHits.includes('hydrogen')
  ) {
    industryMap.energy.forEach(v => hits.add(v));
  }

  if (
    keywordHits.includes('travel') ||
    keywordHits.includes('hotel') ||
    keywordHits.includes('hotels')
  ) {
    industryMap.travel.forEach(v => hits.add(v));
  }

  if (result.classification === 'rare_dictionary_word') {
    industryMap.culture.forEach(v => hits.add(v));
    industryMap.creative.forEach(v => hits.add(v));
  }

  if (result.classification === 'dictionary_word') {
    industryMap.creative.forEach(v => hits.add(v));
    industryMap.tech.forEach(v => hits.add(v));
  }

  if (result.classification === 'brandable') {
    industryMap.creative.forEach(v => hits.add(v));
    industryMap.tech.forEach(v => hits.add(v));
  }

  if (result.classification === 'personal_name') {
    hits.add('personal brand');
    hits.add('portfolio site');
    hits.add('professional identity');
  }

  return Array.from(hits).slice(0, 6);
}

function formatMoney(num) {
  if (num >= 1000000) {
    return '$' + (num / 1000000).toFixed(2).replace(/\.00$/, '') + 'M';
  }
  return '$' + Math.round(num).toLocaleString();
}

function buildPricing(score, classification, config, tld) {
  const multipliers = config.pricing_multipliers[classification];
  const tldBoost = config.tld_weights[tld] || config.tld_weights.other;

  const midpoint = Math.max(75, score * 16 + tldBoost * 14);
  const wholesaleLow = midpoint * multipliers.low;
  const wholesaleHigh = midpoint * multipliers.high;
  const retailLow = midpoint * multipliers.retail_low;
  const retailHigh = midpoint * multipliers.retail_high;

  return {
    midpoint,
    wholesaleLow,
    wholesaleHigh,
    retailLow,
    retailHigh
  };
}

function findComparableSales(sld, tld, classification, keywordHits, compsData) {
  const sales = compsData.sales || [];

  const matches = sales.map(item => {
    let score = 0;

    if (item.tld === tld) score += 18;
    if (item.classification === classification) score += 20;

    const lengthDiff = Math.abs(item.length - sld.length);
    score += Math.max(0, 16 - (lengthDiff * 2));

    let sharedKeywords = 0;
    if (keywordHits?.length) {
      sharedKeywords = item.keywords.filter(k => keywordHits.includes(k)).length;
      score += sharedKeywords * 12;
    }

    if (item.sld === sld) score += 50;

    // A comp is only relevant if it shares real pricing drivers:
    // same lexical classification, a shared commercial keyword, or
    // the exact name. Extension + length alone is not comparability.
    const related =
      item.sld === sld ||
      item.classification === classification ||
      sharedKeywords > 0;

    return { ...item, matchScore: score, related };
  });

  return matches
    .filter(item => item.related && item.matchScore >= 30)
    .sort((a, b) => b.matchScore - a.matchScore || b.price - a.price)
    .slice(0, 4);
}

function medianPrice(comparables) {
  const prices = comparables.map(item => item.price).sort((a, b) => a - b);
  const mid = Math.floor(prices.length / 2);
  return prices.length % 2 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2;
}

function refinePricingWithComparables(basePricing, comparables, sld, tld) {
  if (!comparables.length) return basePricing;

  // Evidence hierarchy: a documented public sale of the asset itself
  // outranks any model output, so pricing anchors to the market record
  // and the model only sets the resale spread around it.
  const ownSale = comparables.find(item => item.sld === sld && item.tld === tld);
  if (ownSale) {
    return {
      midpoint: ownSale.price * 0.5,
      wholesaleLow: ownSale.price * 0.35,
      wholesaleHigh: ownSale.price * 0.65,
      retailLow: ownSale.price * 0.9,
      retailHigh: ownSale.price * 1.4,
      anchoredToOwnSale: true
    };
  }

  // A sale of the same name on another extension is strong evidence
  // (50% weight); otherwise blend 30% against the median comparable.
  const sameName = comparables.find(item => item.sld === sld);
  const anchor = sameName ? sameName.price : medianPrice(comparables);
  const weight = sameName ? 0.5 : 0.3;

  // Geometric blending so a single outlier sale cannot inflate the
  // estimate by orders of magnitude.
  const adjustedMid = Math.exp(
    (Math.log(basePricing.midpoint) * (1 - weight)) + (Math.log(anchor) * weight)
  );

  return {
    midpoint: adjustedMid,
    wholesaleLow: adjustedMid * 0.68,
    wholesaleHigh: adjustedMid * 1.34,
    retailLow: adjustedMid * 2.2,
    retailHigh: adjustedMid * 5.4
  };
}

function buildStrengths(result) {
  const strengths = [];

  if (result.classification === 'commercial_keyword') strengths.push('clear commercial intent');
  if (result.classification === 'dictionary_word') strengths.push('strong lexical legitimacy');
  if (result.classification === 'rare_dictionary_word') strengths.push('rare but authentic lexical legitimacy');
  if (result.classification === 'personal_name') strengths.push('identity-based use potential');
  if (result.classification === 'brandable') strengths.push('clean naming structure');

  if (result.tld === '.com') strengths.push('strongest global resale extension');
  if (result.tld === '.ai') strengths.push('strong alignment with modern AI naming demand');
  if (result.tld === '.io') strengths.push('strong fit for software and developer-oriented branding');
  if (result.sld.length <= 6) strengths.push('short length advantage');
  if (result.sld.length <= 10) strengths.push('manageable brand length');

  return strengths.slice(0, 5);
}

function buildCautions(result) {
  const cautions = [];

  if (result.classification === 'rare_dictionary_word') {
    cautions.push('low mainstream search demand');
    cautions.push('buyer pool is narrower than generic commercial keywords');
  }

  if (result.classification === 'dictionary_word') {
    cautions.push('value depends on buyer fit, not lexical legitimacy alone');
  }

  if (result.classification === 'brandable') {
    cautions.push('value depends heavily on buyer taste and branding fit');
  }

  if (result.classification === 'personal_name') {
    cautions.push('value is usually identity-specific rather than broad-market');
  }

  if (result.classification === 'random_low_quality') {
    cautions.push('weak lexical and commercial foundation');
  }

  if (
    result.tld !== '.com' &&
    result.tld !== '.ai' &&
    result.tld !== '.io' &&
    result.tld !== '.co'
  ) {
    cautions.push('extension may limit resale liquidity');
  }

  return cautions.slice(0, 4);
}

async function evaluateDomain(domainInput) {
  const datasets = await loadValuationData();
  const domain = normalizeDomain(domainInput);

  if (!isValidDomainLike(domain)) {
    return {
      ok: false,
      error: 'Enter a valid domain like example.com'
    };
  }

  const parts = splitDomain(domain);
  if (!parts) {
    return {
      ok: false,
      error: 'Invalid domain structure'
    };
  }

  const { sld, tld } = parts;
  const config = datasets.config;

  let classificationData = classifyDomain(sld, datasets);

  // Deep lexical check: before accepting a name as invented or random,
  // verify it against the extended attested wordlist. Uncommon but real
  // words ("dactylograph") classify as rare dictionary words, with
  // medium-high confidence and no curated brandability bonus.
  if (
    classificationData.classification === 'brandable' ||
    classificationData.classification === 'random_low_quality'
  ) {
    const extendedWords = await loadExtendedWords();
    if (extendedWords.has(sld)) {
      classificationData = {
        classification: 'rare_dictionary_word',
        confidence: 'medium_high',
        lexicalStatus: 'attested but uncommon dictionary word',
        keywordHits: [],
        lexicalEntry: null
      };
    }
  }

  let score = config.base_scores[classificationData.classification] || 0;
  score += config.tld_weights[tld] || config.tld_weights.other;
  score += getLengthAdjustment(config, sld.length);

  if (classificationData.keywordHits?.length) {
    score += Math.min(12, classificationData.keywordHits.length * 4);
  }

  if (classificationData.classification === 'rare_dictionary_word') {
    score += 4;
  }

  // Curated per-word brandability rating from the public lexical
  // datasets — recorded in the data, never assigned at evaluation time.
  const brandability = classificationData.lexicalEntry?.brandability;
  if (brandability === 'strong') {
    score += 8;
  } else if (brandability === 'moderate') {
    score += 4;
  }

  if (classificationData.classification === 'random_low_quality') {
    score -= 8;
  }

  // Normalize against the theoretical maximum (88 base + 12 keyword
  // bonus + 24 TLD + 30 length = 154) instead of clamping at 100, so
  // the top of the scale stays reserved for category-defining assets.
  const MAX_RAW_SCORE = 154;
  score = Math.max(5, Math.min(100, Math.round((score / MAX_RAW_SCORE) * 100)));

  const comparables = findComparableSales(
    sld,
    tld,
    classificationData.classification,
    classificationData.keywordHits || [],
    datasets.comps
  );

  const rawPricing = buildPricing(score, classificationData.classification, config, tld);
  const pricing = refinePricingWithComparables(rawPricing, comparables, sld, tld);

  const useCases = estimateUseCases({
    sld,
    tld,
    classification: classificationData.classification,
    keywordHits: classificationData.keywordHits || []
  }, datasets.industryMap);

  return {
    ok: true,
    domain,
    sld,
    tld,
    score,
    classification: classificationData.classification,
    confidence: classificationData.confidence,
    lexicalStatus: classificationData.lexicalStatus,
    keywordHits: classificationData.keywordHits || [],
    lexicalEntry: classificationData.lexicalEntry || null,
    pricing,
    comparables,
    useCases,
    strengths: buildStrengths({
      sld,
      tld,
      classification: classificationData.classification
    }),
    cautions: buildCautions({
      tld,
      classification: classificationData.classification
    }),
    meta: {
      lastUpdated: config.last_updated_human,
      nextUpdate: config.next_update_label
    }
  };
}
