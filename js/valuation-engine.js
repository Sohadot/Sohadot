let VALUATION_DATA = null;

async function loadValuationData() {
  if (VALUATION_DATA) return VALUATION_DATA;

  const [
    config,
    keywords,
    lexicalWords,
    rareWords,
    names,
    industryMap,
    comps
  ] = await Promise.all([
    fetch('/data/valuation_config.json').then(r => r.json()),
    fetch('/data/valuation_keywords.json').then(r => r.json()),
    fetch('/data/lexical_words.json').then(r => r.json()),
    fetch('/data/rare_words.json').then(r => r.json()),
    fetch('/data/names.json').then(r => r.json()),
    fetch('/data/industry_map.json').then(r => r.json()),
    fetch('/data/valuation_comps.json').then(r => r.json())
  ]);

  VALUATION_DATA = {
    config,
    keywords,
    lexicalWords,
    rareWords,
    names,
    industryMap,
    comps
  };

  return VALUATION_DATA;
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
    if (word.includes(kw)) hits.push(kw);
  }
  return hits;
}

function isCleanBrandable(word) {
  if (!/^[a-z]+$/.test(word)) return false;
  if (word.length < 4 || word.length > 12) return false;
  if (/(.)\1\1/.test(word)) return false;
  return true;
}

function classifyDomain(sld, datasets) {
  const { lexicalWords, rareWords, names, keywords } = datasets;

  const commercialHits = detectCommercialKeywords(sld, keywords);

  if (commercialHits.length > 0) {
    return {
      classification: 'commercial_keyword',
      confidence: 'medium_high',
      lexicalStatus: 'commercial keyword pattern',
      keywordHits: commercialHits,
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

    if (keywordHits?.length) {
      const shared = item.keywords.filter(k => keywordHits.includes(k));
      score += shared.length * 12;
    }

    if (item.sld === sld) score += 50;

    return { ...item, matchScore: score };
  });

  return matches
    .filter(item => item.matchScore >= 16)
    .sort((a, b) => b.matchScore - a.matchScore || b.price - a.price)
    .slice(0, 4);
}

function refinePricingWithComparables(basePricing, comparables) {
  if (!comparables.length) return basePricing;

  const avg = comparables.reduce((sum, item) => sum + item.price, 0) / comparables.length;
  const adjustedMid = (basePricing.midpoint * 0.7) + (avg * 0.3);

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

  const classificationData = classifyDomain(sld, datasets);

  let score = config.base_scores[classificationData.classification] || 0;
  score += config.tld_weights[tld] || config.tld_weights.other;
  score += getLengthAdjustment(config, sld.length);

  if (classificationData.keywordHits?.length) {
    score += Math.min(12, classificationData.keywordHits.length * 4);
  }

  if (classificationData.classification === 'rare_dictionary_word') {
    score += 4;
  }

  if (classificationData.classification === 'random_low_quality') {
    score -= 8;
  }

  score = Math.max(5, Math.min(100, score));

  const comparables = findComparableSales(
    sld,
    tld,
    classificationData.classification,
    classificationData.keywordHits || [],
    datasets.comps
  );

  const rawPricing = buildPricing(score, classificationData.classification, config, tld);
  const pricing = refinePricingWithComparables(rawPricing, comparables);

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
