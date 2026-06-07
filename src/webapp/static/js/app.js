/* app.js — ImmoPrix frontend logic */

// ═══════════════════ Navbar Scroll Effect ═══════════════════
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (nav) nav.classList.toggle('scrolled', window.scrollY > 10);
});

// ═══════════════════ Smooth Scrolling ════════════════════════
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const targetId = a.getAttribute('href');
    const el = document.querySelector(targetId);
    if (el) {
      const offset = 72; // navbar height
      const bodyRect = document.body.getBoundingClientRect().top;
      const elRect = el.getBoundingClientRect().top;
      const elPosition = elRect - bodyRect;
      const offsetPosition = elPosition - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  });
});

// ═══════════════════ Counter Animation ══════════════════════
function animateCounter(el) {
  const target = parseInt(el.textContent.replace(/,/g, ''), 10) || parseInt(el.dataset.target, 10);
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

// ═══════════════════ District Dropdown Population ════════════
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

// ═══════════════════ Stepper Numeric Controls ════════════════
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

// ═══════════════════ Formatting Helper ═══════════════════════
const fmt = n => {
  const num = Math.round(n);
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

// ═══════════════════ Prediction Form Controller ══════════════
const form = document.getElementById('predictForm');
const submitBtn = document.getElementById('submitBtn');

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Check validity
    if (!document.getElementById('citySelect').value) {
      showError('Please select a city.');
      return;
    }
    if (!document.getElementById('surface').value) {
      showError('Please specify the property surface area.');
      return;
    }

    // Show loading state in button
    submitBtn.disabled = true;
    const textEl = submitBtn.querySelector('.submit-text');
    const loaderEl = submitBtn.querySelector('.submit-loader');
    const iconEl = submitBtn.querySelector('.submit-icon');
    if (textEl) textEl.style.display = 'none';
    if (loaderEl) loaderEl.style.display = 'inline-flex';
    if (iconEl) iconEl.style.display = 'none';

    showPlaceholder();

    try {
      const surfaceVal = parseFloat(document.getElementById('surface').value) || 80;
      if (surfaceVal > 900) {
        showError('La superficie maximale autorisée est de 900 m².');
        return;
      }

      const data = {
        city: document.getElementById('citySelect').value,
        district: document.getElementById('districtSelect').value,
        property_category: document.getElementById('propertyCategory').value,
        listing_type: document.getElementById('listingType').value,
        surface: surfaceVal,
        rooms: parseInt(document.getElementById('rooms').value, 10) || 3,
        bedrooms: parseInt(document.getElementById('bedrooms').value, 10) || 2,
        bathrooms: parseInt(document.getElementById('bathrooms').value, 10) || 1,
        terrace: document.getElementById('amen_terrace').checked,
        garage: document.getElementById('amen_garage').checked,
        elevator: document.getElementById('amen_elevator').checked,
        concierge: document.getElementById('amen_concierge').checked,
        pool: document.getElementById('amen_pool').checked,
        security: document.getElementById('amen_security').checked,
        garden: document.getElementById('amen_garden').checked,
      };

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
      showError('Network error connecting to valuation engine. Please try again.');
    } finally {
      submitBtn.disabled = false;
      if (textEl) textEl.style.display = '';
      if (loaderEl) loaderEl.style.display = 'none';
      if (iconEl) iconEl.style.display = '';
    }
  });
}

// ═══════════════════ UI States ════════════════════════════════
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

  // Animate pricing text
  animatePrice(document.getElementById('priceAmount'), r.predicted_price);

  // Unit and surface details
  const displayUnit = r.unit === '/mo' ? ' MAD/month' : ' MAD';
  document.getElementById('pricePerM2').textContent =
    `${fmt(r.price_per_m2)} DH/m² \u2022 ${data.surface} m²`;

  // Range values
  document.getElementById('priceMin').textContent = fmt(r.min_price) + displayUnit;
  document.getElementById('priceMax').textContent = fmt(r.max_price) + displayUnit;

  // Position indicator slider dot (exactly centered at 50% for standard bounds)
  setTimeout(() => {
    document.getElementById('rangeDot').style.left = '50%';
  }, 100);

  // Confidence progress bar
  const pct = r.confidence || 92;
  setTimeout(() => {
    document.getElementById('confidenceFill').style.width = pct + '%';
  }, 200);
  document.getElementById('confidencePct').textContent = pct + '%';

  // ── Yakeey local benchmark calibration logic
  const calCard = document.getElementById('yakeeyCalibration');
  const benchValEl = document.getElementById('yakeeyBenchVal');
  const deviationValEl = document.getElementById('yakeeyDeviationVal');

  let refPriceM2 = null;
  if (typeof YAKEEY_REF !== 'undefined' && YAKEEY_REF[data.city] && YAKEEY_REF[data.city][data.district]) {
    const refData = YAKEEY_REF[data.city][data.district];
    const isVilla = ['villa', 'riad'].includes(data.property_category.toLowerCase());
    refPriceM2 = isVilla ? refData.villa_price_m2 : refData.apartment_price_m2;
  }

  if (refPriceM2) {
    calCard.style.display = 'block';
    benchValEl.textContent = `${fmt(refPriceM2)} DH/m²`;

    const deviation = ((r.price_per_m2 - refPriceM2) / refPriceM2 * 100).toFixed(1);
    const deviationStr = deviation > 0 ? `+${deviation}%` : `${deviation}%`;
    deviationValEl.textContent = deviationStr;

    // Style deviation dynamically
    if (Math.abs(deviation) <= 10) {
      deviationValEl.style.color = 'var(--emerald)';
    } else if (deviation > 0) {
      deviationValEl.style.color = 'var(--gold)';
    } else {
      deviationValEl.style.color = '#3b82f6';
    }
  } else {
    // If benchmark is missing, hide or show placeholder
    calCard.style.display = 'block';
    benchValEl.textContent = 'Unavailable';
    deviationValEl.textContent = '—';
    deviationValEl.style.color = 'var(--text-light)';
  }

  // Summary tags creation
  const chips = [];
  if (data.city) chips.push(data.city);
  if (data.district) chips.push(data.district);
  chips.push(data.property_category);
  chips.push(data.listing_type.replace('_', ' '));
  chips.push(data.surface + ' m²');
  chips.push(data.rooms + ' rooms');
  ['garage', 'elevator', 'terrace', 'pool', 'security', 'garden', 'concierge'].forEach(k => {
    if (data[k]) chips.push(k.charAt(0).toUpperCase() + k.slice(1));
  });

  document.getElementById('summaryChips').innerHTML = chips.map(c =>
    `<div class="s-chip"><span class="chip-dot"></span>${c}</div>`
  ).join('');

  // Context comparison grid
  const nationalAvg = 14000;
  const ratio = ((r.price_per_m2 / nationalAvg - 1) * 100).toFixed(1);
  const ratioStr = ratio > 0 ? `+${ratio}%` : `${ratio}%`;
  const ratioColor = ratio > 0 ? 'var(--gold)' : 'var(--emerald)';

  document.getElementById('contextGrid').innerHTML = `
    <div class="ctx-item">
      <div class="ctx-label">vs. National Average</div>
      <div class="ctx-value" style="color:${ratioColor}">${ratioStr}</div>
    </div>
    <div class="ctx-item">
      <div class="ctx-label">Price Margin (&plusmn;10%)</div>
      <div class="ctx-value">${fmt(r.max_price - r.min_price)} MAD</div>
    </div>
    <div class="ctx-item">
      <div class="ctx-label">Price per m²</div>
      <div class="ctx-value">${fmt(r.price_per_m2)} DH/m²</div>
    </div>
    <div class="ctx-item">
      <div class="ctx-label">Registry References</div>
      <div class="ctx-value" style="font-size:0.75rem; color:var(--text-muted);">Mubawab + Yakeey</div>
    </div>
  `;

  // Dynamic scroll on mobile viewports
  if (window.innerWidth < 1024) {
    setTimeout(() => {
      const headerOffset = 80;
      const element = document.getElementById('resultPanel');
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }, 200);
  }
}

function animatePrice(el, target) {
  const duration = 1000;
  const start = performance.now();
  const update = (now) => {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 4); // Cubic quartic ease-out
    el.textContent = fmt(Math.round(target * ease));
    if (p < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// ═══════════════════ Form Reset ═══════════════════════════════
function resetForm() {
  if (form) form.reset();
  document.getElementById('rooms').value = 3;
  document.getElementById('bedrooms').value = 2;
  document.getElementById('bathrooms').value = 1;
  if (districtSelect) districtSelect.innerHTML = '<option value="">Select city first...</option>';
  showPlaceholder();

  const predictorEl = document.getElementById('predictor');
  if (predictorEl) {
    const offset = 72;
    const bodyRect = document.body.getBoundingClientRect().top;
    const elRect = predictorEl.getBoundingClientRect().top;
    const elPosition = elRect - bodyRect;
    const offsetPosition = elPosition - offset;
    window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
  }
}

const resetBtn = document.getElementById('resetBtn');
if (resetBtn) resetBtn.addEventListener('click', resetForm);

// ═══════════════════ Result Sharing ══════════════════════════
const shareBtn = document.getElementById('shareBtn');
if (shareBtn) {
  shareBtn.addEventListener('click', () => {
    const price = document.getElementById('priceAmount').textContent;
    const city = document.getElementById('citySelect').value;
    const text = `Real estate valuation: ${price} MAD in ${city} — ImmoPrix AI Prediction (2026)`;
    if (navigator.share) {
      navigator.share({ title: 'ImmoPrix Estimate', text }).catch(() => { });
    } else {
      navigator.clipboard.writeText(text).then(() => {
        const prevText = shareBtn.textContent;
        shareBtn.textContent = 'Copied Link!';
        setTimeout(() => { shareBtn.textContent = prevText; }, 2000);
      });
    }
  });
}

// ═══════════════════ City Market Tabs Controller ══════════════
const tabsContainer = document.getElementById('marketTabs');
if (tabsContainer) {
  tabsContainer.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const city = btn.dataset.city;

      // Update buttons active class
      tabsContainer.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Update chart panels active class
      document.querySelectorAll('.city-chart-panel').forEach(p => {
        p.classList.remove('active');
      });

      const activePanel = document.getElementById(`chart-${city}`);
      if (activePanel) {
        activePanel.classList.add('active');
        triggerBarAnimations(activePanel);
      }
    });
  });

  function triggerBarAnimations(panel) {
    panel.querySelectorAll('.bar-fill').forEach(fill => {
      const w = fill.style.width;
      fill.style.width = '0%';
      setTimeout(() => {
        fill.style.width = w;
      }, 50);
    });
  }

  // Trigger initial animation for Casablanca on page load
  const initialActive = document.querySelector('.city-chart-panel.active');
  if (initialActive) {
    setTimeout(() => {
      triggerBarAnimations(initialActive);
    }, 500);
  }
}
