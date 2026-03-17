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

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderKeywordSignals(keywordHits) {
  if (!keywordHits || !keywordHits.length) {
    return `<p>No strong direct keyword signal</p>`;
  }

  return `
    <div class="pill-row">
      ${keywordHits.map(item => `<span class="pill">${escapeHtml(item)}</span>`).join('')}
    </div>
  `;
}

function renderLexicalNotes(lexicalEntry) {
  if (!lexicalEntry) return '';

  const blocks = [];

  if (lexicalEntry.usage_note) {
    blocks.push(`<p><strong>Usage:</strong> ${escapeHtml(lexicalEntry.usage_note)}</p>`);
  }

  if (lexicalEntry.origin_note) {
    blocks.push(`<p><strong>Origin:</strong> ${escapeHtml(lexicalEntry.origin_note)}</p>`);
  }

  if (lexicalEntry.brandability_note) {
    blocks.push(`<p><strong>Brandability:</strong> ${escapeHtml(lexicalEntry.brandability_note)}</p>`);
  }

  if (lexicalEntry.commercial_note) {
    blocks.push(`<p><strong>Commercial note:</strong> ${escapeHtml(lexicalEntry.commercial_note)}</p>`);
  }

  if (lexicalEntry.seo_strength) {
    blocks.push(`<p><strong>Search visibility:</strong> ${escapeHtml(lexicalEntry.seo_strength)}</p>`);
  }

  return blocks.join('');
}

function renderComparables(comparables) {
  if (!comparables || !comparables.length) return '';

  return `
    <div class="info-block">
      <div class="block-title">Comparable Sales</div>
      <ul>
        ${comparables.map(item => `
          <li>
            <strong>${escapeHtml(item.domain)}</strong> — ${escapeHtml(item.price_display)} (${escapeHtml(item.year)})
            ${item.notes ? `<div class="muted">${escapeHtml(item.notes)}</div>` : ''}
          </li>
        `).join('')}
      </ul>
    </div>
  `;
}

function renderList(items) {
  if (!items || !items.length) {
    return `<p>No strong signals found.</p>`;
  }

  return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function renderUseCases(items) {
  if (!items || !items.length) {
    return `<p>No clear best-fit use cases detected.</p>`;
  }

  return `
    <div class="pill-row">
      ${items.map(item => `<span class="pill">${escapeHtml(item)}</span>`).join('')}
    </div>
  `;
}

function renderDomainHeader(result) {
  return `
    <div class="tier-row">
      <div>
        <div class="eyebrow-mini">Classification</div>
        <h2>${humanizeClassification(result.classification)}</h2>
        <p class="muted" style="margin-top:8px;">
          <strong>${escapeHtml(result.domain)}</strong>
        </p>
      </div>
      <div class="score-badge">${escapeHtml(result.score)}/100</div>
    </div>
  `;
}

function renderPriceGrid(result) {
  return `
    <div class="value-grid">
      <div class="value-card">
        <div class="value-label">Wholesale Midpoint</div>
        <div class="value-amount">${formatMoney(result.pricing.midpoint)}</div>
      </div>
      <div class="value-card">
        <div class="value-label">Wholesale Range</div>
        <div class="value-amount">
          ${formatMoney(result.pricing.wholesaleLow)} – ${formatMoney(result.pricing.wholesaleHigh)}
        </div>
      </div>
      <div class="value-card">
        <div class="value-label">End-User Retail</div>
        <div class="value-amount">
          ${formatMoney(result.pricing.retailLow)} – ${formatMoney(result.pricing.retailHigh)}
        </div>
      </div>
    </div>
  `;
}

function renderLexicalBlock(result) {
  return `
    <div class="info-block">
      <div class="block-title">Lexical Status</div>
      <p>${escapeHtml(result.lexicalStatus)}</p>
      ${renderLexicalNotes(result.lexicalEntry)}
    </div>
  `;
}

function renderConfidenceAndSignals(result) {
  return `
    <div class="grid-2">
      <div class="info-block">
        <div class="block-title">Confidence</div>
        <p>${confidenceLabel(result.confidence)}</p>
      </div>

      <div class="info-block">
        <div class="block-title">Keyword Signals</div>
        ${renderKeywordSignals(result.keywordHits)}
      </div>
    </div>
  `;
}

function renderStrengthsAndCautions(result) {
  return `
    <div class="grid-2">
      <div class="info-block">
        <div class="block-title">Strengths</div>
        ${renderList(result.strengths)}
      </div>

      <div class="info-block">
        <div class="block-title">Cautions</div>
        ${renderList(result.cautions)}
      </div>
    </div>
  `;
}

function renderUseCasesBlock(result) {
  return `
    <div class="info-block">
      <div class="block-title">Best-Fit Use Cases</div>
      ${renderUseCases(result.useCases)}
    </div>
  `;
}

function renderMetaBlock(result) {
  return `
    <div class="grid-2">
      <div class="info-block">
        <div class="block-title">Model Update</div>
        <p>Last updated: ${escapeHtml(result.meta.lastUpdated)}</p>
      </div>
      <div class="info-block">
        <div class="block-title">Next Refresh</div>
        <p>${escapeHtml(result.meta.nextUpdate)}</p>
      </div>
    </div>
  `;
}

function renderDisclaimer(result) {
  let specialNote = '';

  if (result.classification === 'rare_dictionary_word') {
    specialNote = `
      <div class="disclaimer-box" style="margin-bottom:12px;">
        Rare dictionary words should not be treated as nonsense strings. Their value is usually driven by rarity, originality, elite branding fit, linguistic legitimacy, and story value rather than mainstream search volume alone.
      </div>
    `;
  }

  if (result.classification === 'personal_name') {
    specialNote = `
      <div class="disclaimer-box" style="margin-bottom:12px;">
        Personal-name domains can be valuable, but market size is often narrower and strongly tied to identity relevance, cultural familiarity, and buyer specificity.
      </div>
    `;
  }

  return `
    ${specialNote}
    <div class="disclaimer-box">
      This valuation is a structured directional estimate based on lexical legitimacy, commercial keyword logic, TLD quality, naming structure, and comparable public sales context. It is not a guaranteed market outcome, not a promise of buyer interest, and not a certified appraisal.
    </div>
  `;
}

function renderValuationResult(result) {
  const box = document.getElementById('valuationResult');

  box.innerHTML = `
    ${renderDomainHeader(result)}
    ${renderPriceGrid(result)}
    ${renderLexicalBlock(result)}
    ${renderConfidenceAndSignals(result)}
    ${renderStrengthsAndCautions(result)}
    ${renderUseCasesBlock(result)}
    ${renderComparables(result.comparables)}
    ${renderMetaBlock(result)}
    ${renderDisclaimer(result)}
  `;

  box.style.display = 'block';
}

async function handleValuation() {
  const input = document.getElementById('domainInput');
  const error = document.getElementById('valuationError');
  const loading = document.getElementById('valuationLoading');
  const resultBox = document.getElementById('valuationResult');
  const button = document.getElementById('valuateBtn');

  error.style.display = 'none';
  error.textContent = '';
  resultBox.style.display = 'none';
  resultBox.innerHTML = '';
  loading.style.display = 'block';
  button.disabled = true;

  try {
    const result = await evaluateDomain(input.value);

    loading.style.display = 'none';
    button.disabled = false;

    if (!result.ok) {
      error.textContent = result.error;
      error.style.display = 'block';
      return;
    }

    renderValuationResult(result);
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    loading.style.display = 'none';
    button.disabled = false;
    error.textContent = 'Something went wrong while evaluating the domain.';
    error.style.display = 'block';
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('valuateBtn');
  const input = document.getElementById('domainInput');

  if (button) {
    button.addEventListener('click', handleValuation);
  }

  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        handleValuation();
      }
    });
  }
});
