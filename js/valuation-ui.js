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
    return `<span style="color:var(--dim);font-size:.82rem;">No strong direct keyword signal</span>`;
  }

  return `
    <div style="display:flex;flex-wrap:wrap;gap:8px;">
      ${keywordHits.map(item => `
        <span style="padding:6px 12px;border-radius:999px;background:var(--accent3);border:1px solid rgba(99,102,241,.18);font-size:.76rem;color:var(--accent2);font-weight:600;">
          ${escapeHtml(item)}
        </span>
      `).join('')}
    </div>
  `;
}

function renderLexicalNotes(lexicalEntry) {
  if (!lexicalEntry) return '';

  const rows = [];

  if (lexicalEntry.usage_note) {
    rows.push(`<p><strong style="color:var(--text)">Usage:</strong> ${escapeHtml(lexicalEntry.usage_note)}</p>`);
  }
  if (lexicalEntry.origin_note) {
    rows.push(`<p><strong style="color:var(--text)">Origin:</strong> ${escapeHtml(lexicalEntry.origin_note)}</p>`);
  }
  if (lexicalEntry.brandability_note) {
    rows.push(`<p><strong style="color:var(--text)">Brandability:</strong> ${escapeHtml(lexicalEntry.brandability_note)}</p>`);
  }
  if (lexicalEntry.commercial_note) {
    rows.push(`<p><strong style="color:var(--text)">Commercial note:</strong> ${escapeHtml(lexicalEntry.commercial_note)}</p>`);
  }
  if (lexicalEntry.seo_strength) {
    rows.push(`<p><strong style="color:var(--text)">Search visibility:</strong> ${escapeHtml(lexicalEntry.seo_strength)}</p>`);
  }

  return rows.join('');
}

function renderComparables(comparables) {
  if (!comparables || !comparables.length) return '';

  return `
    <div class="section-label">Comparable Sales</div>
    <div class="comp-list">
      ${comparables.map(item => `
        <div class="comp-row">
          <div>
            <div class="comp-name">${escapeHtml(item.domain)}</div>
            ${item.notes ? `<div class="comp-year" style="margin-top:4px;">${escapeHtml(item.notes)}</div>` : ''}
          </div>
          <div style="text-align:right;">
            <div class="comp-price">${escapeHtml(item.price_display)}</div>
            <div class="comp-year">${escapeHtml(item.year)}</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderUseCases(items) {
  if (!items || !items.length) {
    return `<span style="color:var(--dim);font-size:.82rem;">No clear best-fit use cases detected</span>`;
  }

  return `
    <div style="display:flex;flex-wrap:wrap;gap:8px;">
      ${items.map(item => `
        <span style="padding:6px 12px;border-radius:999px;background:var(--surface2);border:1px solid var(--border);font-size:.76rem;color:var(--muted);font-weight:600;">
          ${escapeHtml(item)}
        </span>
      `).join('')}
    </div>
  `;
}

function renderBulletList(items) {
  if (!items || !items.length) {
    return `<span style="color:var(--dim);font-size:.82rem;">No strong signals found</span>`;
  }

  return `
    <ul style="padding-left:18px;color:var(--muted);line-height:1.8;font-size:.84rem;">
      ${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
    </ul>
  `;
}

function renderValuationResult(result) {
  const resultCard = document.getElementById('resultCard');

  resultCard.innerHTML = `
    <div class="result-domain">
      <div class="tld-badge-big ${result.tld === '.com' ? 'tld-com' : result.tld === '.ai' ? 'tld-ai' : result.tld === '.io' ? 'tld-io' : 'tld-other'}">
        ${escapeHtml(result.tld.replace('.', '').toUpperCase())}
      </div>
      <div>
        <div class="result-name">${escapeHtml(result.sld)}<span class="tld-part">${escapeHtml(result.tld)}</span></div>
        <div style="margin-top:8px;color:var(--muted);font-size:.86rem;">
          ${humanizeClassification(result.classification)} · Confidence: ${confidenceLabel(result.confidence)}
        </div>
      </div>
    </div>

    <div class="tier-badge tier-${result.score >= 85 ? 'ultra' : result.score >= 70 ? 'premium' : result.score >= 55 ? 'strong' : result.score >= 35 ? 'standard' : 'low'}">
      Score: ${escapeHtml(result.score)}/100
    </div>

    <div class="value-grid">
      <div class="value-box hl">
        <div class="vb-label">Wholesale Midpoint</div>
        <div class="vb-amt blue">${formatMoney(result.pricing.midpoint)}</div>
        <div class="vb-sub">Directional investor midpoint</div>
      </div>
      <div class="value-box">
        <div class="vb-label">Wholesale Range</div>
        <div class="vb-amt green">${formatMoney(result.pricing.wholesaleLow)} – ${formatMoney(result.pricing.wholesaleHigh)}</div>
        <div class="vb-sub">Investor-to-investor range</div>
      </div>
      <div class="value-box">
        <div class="vb-label">End-User Retail</div>
        <div class="vb-amt gold">${formatMoney(result.pricing.retailLow)} – ${formatMoney(result.pricing.retailHigh)}</div>
        <div class="vb-sub">Potential end-user range</div>
      </div>
    </div>

    <div class="ai-section" style="margin-bottom:18px;">
      <div class="ai-header">
        <div class="ai-icon">◆</div>
        Lexical Status
      </div>
      <div class="ai-text">
        <p>${escapeHtml(result.lexicalStatus)}</p>
        ${renderLexicalNotes(result.lexicalEntry)}
      </div>
    </div>

    <div class="section-label">Keyword Signals</div>
    <div style="margin-bottom:18px;">
      ${renderKeywordSignals(result.keywordHits)}
    </div>

    <div class="section-label">Best-Fit Use Cases</div>
    <div style="margin-bottom:18px;">
      ${renderUseCases(result.useCases)}
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px;">
      <div class="value-box">
        <div class="vb-label">Strengths</div>
        ${renderBulletList(result.strengths)}
      </div>
      <div class="value-box">
        <div class="vb-label">Cautions</div>
        ${renderBulletList(result.cautions)}
      </div>
    </div>

    ${renderComparables(result.comparables)}

    <div class="disclaimer" style="margin-top:16px;">
      <strong>Note:</strong> This is a structured directional estimate based on lexical legitimacy, commercial keyword logic, TLD quality, naming structure, and comparable public sales context. It is not a guaranteed sale price and not a certified appraisal.
    </div>
  `;

  resultCard.classList.add('show');
}

function showError(message) {
  const errorMsg = document.getElementById('errorMsg');
  errorMsg.textContent = message;
  errorMsg.style.display = 'block';
}

function clearError() {
  const errorMsg = document.getElementById('errorMsg');
  errorMsg.textContent = '';
  errorMsg.style.display = 'none';
}

function showLoading() {
  document.getElementById('loadingCard').style.display = 'block';
  document.getElementById('resultCard').classList.remove('show');
}

function hideLoading() {
  document.getElementById('loadingCard').style.display = 'none';
}

async function handleValuation() {
  const input = document.getElementById('domainInput');
  const button = document.getElementById('valBtn');
  const resultCard = document.getElementById('resultCard');

  clearError();
  resultCard.classList.remove('show');
  resultCard.innerHTML = '';

  const value = input.value.trim();
  if (!value) {
    showError('Please enter a domain name.');
    return;
  }

  button.disabled = true;
  showLoading();

  try {
    const result = await evaluateDomain(value);

    hideLoading();
    button.disabled = false;

    if (!result.ok) {
      showError(result.error || 'Unable to evaluate this domain.');
      return;
    }

    renderValuationResult(result);
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    hideLoading();
    button.disabled = false;
    console.error(err);
    showError('Something went wrong while evaluating the domain.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('valBtn');
  const input = document.getElementById('domainInput');

  if (button) {
    button.addEventListener('click', handleValuation);
  }

  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleValuation();
    });
  }
});
