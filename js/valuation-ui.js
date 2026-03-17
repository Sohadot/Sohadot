function humanizeClassification(value) {
  const map = {
    commercial_keyword: 'Commercial Keyword Domain',
    dictionary_word: 'Dictionary Word Domain',
    rare_dictionary_word: 'Rare Dictionary Word',
    personal_name: 'Personal Name Domain',
    brandable: 'Brandable Domain',
    random_low_quality: 'Low-Quality / Random Domain'
  };
  return map[value] || value;
}

function confidenceLabel(value) {
  const map = {
    high: 'High',
    medium_high: 'Medium-High',
    medium: 'Medium',
    low: 'Low'
  };
  return map[value] || value;
}

function renderValuationResult(result) {
  const box = document.getElementById('valuationResult');

  box.innerHTML = `
    <div class="tier-row">
      <div>
        <div class="eyebrow-mini">Classification</div>
        <h2>${humanizeClassification(result.classification)}</h2>
      </div>
      <div class="score-badge">${result.score}/100</div>
    </div>

    <div class="value-grid">
      <div class="value-card">
        <div class="value-label">Wholesale Midpoint</div>
        <div class="value-amount">${formatMoney(result.pricing.midpoint)}</div>
      </div>
      <div class="value-card">
        <div class="value-label">Wholesale Range</div>
        <div class="value-amount">${formatMoney(result.pricing.wholesaleLow)} – ${formatMoney(result.pricing.wholesaleHigh)}</div>
      </div>
      <div class="value-card">
        <div class="value-label">End-User Retail</div>
        <div class="value-amount">${formatMoney(result.pricing.retailLow)} – ${formatMoney(result.pricing.retailHigh)}</div>
      </div>
    </div>

    <div class="info-block">
      <div class="block-title">Lexical Status</div>
      <p>${result.lexicalStatus}</p>
      ${result.lexicalEntry ? `<p class="muted">${result.lexicalEntry.usage_note || ''}</p>` : ''}
    </div>

    <div class="grid-2">
      <div class="info-block">
        <div class="block-title">Strengths</div>
        <ul>${result.strengths.map(item => `<li>${item}</li>`).join('')}</ul>
      </div>

      <div class="info-block">
        <div class="block-title">Cautions</div>
        <ul>${result.cautions.map(item => `<li>${item}</li>`).join('')}</ul>
      </div>
    </div>

    <div class="info-block">
      <div class="block-title">Best-Fit Use Cases</div>
      <div class="pill-row">
        ${result.useCases.map(item => `<span class="pill">${item}</span>`).join('')}
      </div>
    </div>

    <div class="grid-2">
      <div class="info-block">
        <div class="block-title">Confidence</div>
        <p>${confidenceLabel(result.confidence)}</p>
      </div>
      <div class="info-block">
        <div class="block-title">Signals</div>
        <p>${result.keywordHits.length ? result.keywordHits.join(', ') : 'No strong direct keyword signal'}</p>
      </div>
    </div>

    <div class="disclaimer-box">
      This valuation is a structured directional estimate based on lexical legitimacy, commercial keyword logic, TLD quality, and naming structure. It is not a guaranteed market outcome or certified appraisal.
    </div>
  `;

  box.style.display = 'block';
}

async function handleValuation() {
  const input = document.getElementById('domainInput');
  const error = document.getElementById('valuationError');
  const loading = document.getElementById('valuationLoading');
  const resultBox = document.getElementById('valuationResult');

  error.style.display = 'none';
  resultBox.style.display = 'none';
  loading.style.display = 'block';

  const result = await evaluateDomain(input.value);

  loading.style.display = 'none';

  if (!result.ok) {
    error.textContent = result.error;
    error.style.display = 'block';
    return;
  }

  renderValuationResult(result);
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('valuateBtn').addEventListener('click', handleValuation);
  document.getElementById('domainInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleValuation();
  });
});
