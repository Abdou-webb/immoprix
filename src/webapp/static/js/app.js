/* ── app.js — ImmoPrix frontend logic ── */

// ═══════════════════ Navbar scroll effect ═══════════════════
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (nav) nav.classList.toggle('scrolled', window.scrollY > 10);
});

// ═══════════════════ Smooth scroll ══════════════════════════
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const el = document.querySelector(a.getAttribute('href'));
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

// ═══════════════════ Counter animation ══════════════════════
function animateCounter(el) {
  const target = parseInt(el.dataset.target, 10);
  if (isNaN(target)) return;
  const duration = 1500;
  const start = performance.now();
  const update = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(target * ease).toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

const counterObs = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting && !e.target.dataset.done) {
      e.target.dataset.done = '1';
      animateCounter(e.target);
    }
  });
}, { threshold: 0.4 });
document.querySelectorAll('[data-target]').forEach(el => {
  if (!el.classList.contains('step-btn')) counterObs.observe(el);
});

// ═══════════════════ District dropdown ══════════════════════
const citySelect = document.getElementById('citySelect');
const districtSelect = document.getElementById('districtSelect');

if (citySelect) {
  citySelect.addEventListener('change', () => {
    const city = citySelect.value;
    const districts = (typeof DISTRICTS !== 'undefined' && DISTRICTS[city]) || [];
    districtSelect.innerHTML = districts.length
      ? ['<option value="">Select district...</option>',
         ...districts.map(d => `<option value="${d}">${d}</option>`)].join('')
      : '<option value="">No districts listed</option>';
  });
}

// ═══════════════════ Stepper buttons (FIXED) ═════════════════
document.querySelectorAll('.step-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.getAttribute('data-target');
    const inp = document.getElementById(targetId);
    if (!inp) return;
    const min = parseInt(inp.min, 10) || 0;
    const max = parseInt(inp.max, 10) || 99;
    let val = parseInt(inp.value, 10);
    if (isNaN(val)) val = min;
    if (btn.classList.contains('step-plus')) {
      val = Math.min(val + 1, max);
    } else {
      val = Math.max(val - 1, min);
    }
    inp.value = val;
  });
});

// ═══════════════════ Format helper ═══════════════════════════
const fmt = n => {
  const num = Math.round(n);
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

// ═══════════════════ Prediction form ═════════════════════════
const form = document.getElementById('predictForm');
const submitBtn = document.getElementById('submitBtn');

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Show loader
    submitBtn.disabled = true;
    const textEl = submitBtn.querySelector('.submit-text');
    const loaderEl = submitBtn.querySelector('.submit-loader');
    const iconEl = submitBtn.querySelector('.submit-icon');
    if (textEl) textEl.style.display = 'none';
    if (loaderEl) loaderEl.style.display = 'inline-flex';
    if (iconEl) iconEl.style.display = 'none';
    showPlaceholder();

    const data = {
      city:              document.getElementById('citySelect').value,
      district:          document.getElementById('districtSelect').value,
      property_category: document.getElementById('propertyCategory').value,
      listing_type:      document.getElementById('listingType').value,
      surface:   parseFloat(document.getElementById('surface').value) || 80,
      rooms:     parseInt(document.getElementById('rooms').value, 10) || 3,
      bedrooms:  parseInt(document.getElementById('bedrooms').value, 10) || 2,
      bathrooms: parseInt(document.getElementById('bathrooms').value, 10) || 1,
      terrace:   document.getElementById('amen_terrace').checked,
      garage:    document.getElementById('amen_garage').checked,
      elevator:  document.getElementById('amen_elevator').checked,
      concierge: document.getElementById('amen_concierge').checked,
      pool:      document.getElementById('amen_pool').checked,
      security:  document.getElementById('amen_security').checked,
      garden:    document.getElementById('amen_garden').checked,
    };

    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await res.json();

      if (result.error) {
        showError(result.error);
      } else {
        showResult(result, data);
      }
    } catch (err) {
      showError('Network error. Please try again.');
    } finally {
      submitBtn.disabled = false;
      if (textEl) textEl.style.display = '';
      if (loaderEl) loaderEl.style.display = 'none';
      if (iconEl) iconEl.style.display = '';
    }
  });
}

// ═══════════════════ UI State ════════════════════════════════
function showPlaceholder() {
  document.getElementById('resultPlaceholder').style.display = 'block';
  document.getElementById('resultContent').style.display = 'none';
  document.getElementById('resultError').style.display = 'none';
}

function showError(msg) {
  document.getElementById('resultPlaceholder').style.display = 'none';
  document.getElementById('resultContent').style.display = 'none';
  const err = document.getElementById('resultError');
  err.style.display = 'block';
  document.getElementById('errorMessage').textContent = msg;
}

function showResult(r, data) {
  document.getElementById('resultPlaceholder').style.display = 'none';
  document.getElementById('resultError').style.display = 'none';
  document.getElementById('resultContent').style.display = 'block';

  // Animate price
  animatePrice(document.getElementById('priceAmount'), r.predicted_price);

  // Per m²
  document.getElementById('pricePerM2').textContent =
    `${fmt(r.price_per_m2)} DH/m\u00B2 \u2022 ${data.surface} m\u00B2`;

  // Range
  document.getElementById('priceMin').textContent = fmt(r.min_price) + ' DH';
  document.getElementById('priceMax').textContent = fmt(r.max_price) + ' DH';

  // Confidence
  const pct = r.confidence || 85;
  setTimeout(() => {
    document.getElementById('confidenceFill').style.width = pct + '%';
  }, 200);
  document.getElementById('confidencePct').textContent = pct + '%';

  // Summary chips
  const chips = [];
  if (data.city) chips.push(data.city);
  if (data.district) chips.push(data.district);
  chips.push(data.surface + ' m\u00B2');
  chips.push(data.rooms + ' rooms');
  ['garage','elevator','terrace','pool','security','garden','concierge'].forEach(k => {
    if (data[k]) chips.push(k.charAt(0).toUpperCase() + k.slice(1));
  });

  document.getElementById('summaryChips').innerHTML = chips.map(c =>
    `<div class="s-chip"><span class="chip-dot"></span>${c}</div>`
  ).join('');

  // Context grid
  const avgPpm2 = 14000;
  const ratio = ((r.price_per_m2 / avgPpm2 - 1) * 100).toFixed(1);
  const ratioStr = ratio > 0 ? `+${ratio}%` : `${ratio}%`;
  const ratioColor = ratio > 0 ? '#f59e0b' : '#059669';

  document.getElementById('contextGrid').innerHTML = `
    <div class="ctx-item">
      <div class="ctx-label">vs. National avg</div>
      <div class="ctx-value" style="color:${ratioColor}">${ratioStr}</div>
    </div>
    <div class="ctx-item">
      <div class="ctx-label">Price range</div>
      <div class="ctx-value">${fmt(r.max_price - r.min_price)} DH</div>
    </div>
    <div class="ctx-item">
      <div class="ctx-label">Price/m\u00B2</div>
      <div class="ctx-value">${fmt(r.price_per_m2)} DH</div>
    </div>
    <div class="ctx-item">
      <div class="ctx-label">Source</div>
      <div class="ctx-value" style="font-size:.78rem">Mubawab + Yakeey</div>
    </div>
  `;

  // Scroll to result on mobile
  if (window.innerWidth < 900) {
    setTimeout(() => document.getElementById('resultPanel').scrollIntoView({ behavior: 'smooth' }), 200);
  }
}

function animatePrice(el, target) {
  const duration = 800;
  const start = performance.now();
  const update = (now) => {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(Math.round(target * ease));
    if (p < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// ═══════════════════ Reset ════════════════════════════════════
function resetForm() {
  if (form) form.reset();
  document.getElementById('rooms').value = 3;
  document.getElementById('bedrooms').value = 2;
  document.getElementById('bathrooms').value = 1;
  if (districtSelect) districtSelect.innerHTML = '<option value="">Select city first...</option>';
  showPlaceholder();
  document.getElementById('predictor').scrollIntoView({ behavior: 'smooth' });
}

const resetBtn = document.getElementById('resetBtn');
if (resetBtn) resetBtn.addEventListener('click', resetForm);

// ═══════════════════ Share ════════════════════════════════════
const shareBtn = document.getElementById('shareBtn');
if (shareBtn) {
  shareBtn.addEventListener('click', () => {
    const price = document.getElementById('priceAmount').textContent;
    const text = `Real estate valuation: ${price} MAD — ImmoPrix AI (2026)`;
    if (navigator.share) {
      navigator.share({ title: 'ImmoPrix', text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text).then(() => {
        shareBtn.textContent = 'Copied!';
        setTimeout(() => { shareBtn.textContent = 'Share Result'; }, 2000);
      });
    }
  });
}
