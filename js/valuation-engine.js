let VALUATION_DATA = null;

async function loadValuationData() {
  if (VALUATION_DATA) return VALUATION_DATA;

  const [
    config,
    keywords,
    lexicalWords,
    rareWords,
    names,
    industryMap
  ] = await Promise.all([
    fetch('/data/valuation_config.json').then(r => r.json()),
    fetch('/data/keywords.json').then(r => r.json()),
    fetch('/data/lexical_words.json').then(r => r.json()),
    fetch('/data/rare_words.json').then(r => r.json()),
    fetch('/data/names.json').then(r => r.json()),
    fetch('/data/industry_map.json').then(r => r.json())
  ]);

  VALUATION_DATA = {
    config,
    keywords,
    lexicalWords,
    rareWords,
    names,
    industryMap
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
      keywordHits: commercialHits
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
      keywordHits: []
    };
  }

  if (isCleanBrandable(sld)) {
    return {
      classification: 'brandable',
      confidence: 'medium',
      lexicalStatus: 'clean invented or brandable structure',
      keywordHits: []
    };
  }

  return {
    classification: 'random_low_quality',
    confidence: 'low',
    lexicalStatus: 'weak lexical legitimacy',
    keywordHits: []
  };
}

function estimateUseCases(result, industryMap) {
  const sld = result.sld;
  const hits = new Set();

  if (result.keywordHits?.includes('ai') || result.keywordHits?.includes('agent') || result.keywordHits?.includes('agents') || result.keywordHits?.includes('gpt') || result.keywordHits?.includes('llm')) {
    industryMap.ai.forEach(v => hits.add(v));
  }

  if (result.keywordHits?.includes('finance') || result.keywordHits?.includes('pay') || result.keywordHits?.includes('payments') || result.keywordHits?.includes('wealth') || result.keywordHits?.includes('bank') || result.keywordHits?.includes('cash')) {
    industryMap.finance.forEach(v => hits.add(v));
  }

  if (result.keywordHits?.includes('health') || result.keywordHits?.includes('therapy') || result.keywordHits?.includes('medical') || result.keywordHits?.includes('pharma')) {
    industryMap.health.forEach(v => hits.add(v));
  }

  if (result.keywordHits?.includes('legal') || result.keywordHits?.includes('law') || result.keywordHits?.includes('attorney')) {
    industryMap.legal.forEach(v => hits.add(v));
  }

  if (result.keywordHits?.includes('data') || result.keywordHits?.includes('cloud') || result.keywordHits?.includes('security')) {
    industryMap.tech.forEach(v => hits.add(v));
  }

  if (result.classification === 'rare_dictionary_word') {
    industryMap.culture.forEach(v => hits.add(v));
    industryMap.creative.forEach(v => hits.add(v));
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

function buildStrengths(result) {
  const strengths = [];

  if (result.classification === 'commercial_keyword') strengths.push('clear commercial intent');
  if (result.classification === 'dictionary_word') strengths.push('strong lexical legitimacy');
  if (result.classification === 'rare_dictionary_word') strengths.push('rare but authentic lexical legitimacy');
  if (result.classification === 'personal_name') strengths.push('identity-based use potential');
  if (result.classification === 'brandable') strengths.push('clean naming structure');

  if (result.tld === '.com') strengths.push('strongest global resale extension');
  if (result.tld === '.ai') strengths.push('strong alignment with modern AI naming demand');
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

  if (result.classification === 'brandable') {
    cautions.push('value depends heavily on buyer taste and branding fit');
  }

  if (result.classification === 'personal_name') {
    cautions.push('value is usually identity-specific rather than broad-market');
  }

  if (result.classification === 'random_low_quality') {
    cautions.push('weak lexical and commercial foundation');
  }

  if (result.tld !== '.com' && result.tld !== '.ai' && result.tld !== '.io' && result.tld !== '.co') {
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

  const pricing = buildPricing(score, classificationData.classification, config, tld);
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
    useCases,
    strengths: buildStrengths({ sld, tld, classification: classificationData.classification }),
    cautions: buildCautions({ tld, classification: classificationData.classification }),
    meta: {
      lastUpdated: config.last_updated_human,
      nextUpdate: config.next_update_label
    }
  };
}
