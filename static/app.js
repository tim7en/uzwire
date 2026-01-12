(function () {
  const STORAGE_KEY = 'uzwire_theme';

  function applyTheme(theme, emitEvent = true) {
    const html = document.documentElement;
    html.classList.remove('theme-dark', 'theme-light');
    html.classList.add(theme === 'light' ? 'theme-light' : 'theme-dark');
    html.dataset.theme = theme;
    if (emitEvent) {
      try {
        window.dispatchEvent(new CustomEvent('uzwire:theme', { detail: { theme } }));
      } catch (e) {}
    }
  }

  function getPreferredTheme() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function toggleTheme() {
    const current = document.documentElement.dataset.theme || getPreferredTheme();
    const next = current === 'light' ? 'dark' : 'light';
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next, true);
  }

  // Theme
  applyTheme(getPreferredTheme(), false);
  window.uzwireToggleTheme = toggleTheme;

  // Scroll-reactive background rotation
  const html = document.documentElement;
  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(() => {
      const y = window.scrollY || 0;
      const deg = (y % 2000) / 2000 * 360;
      html.style.setProperty('--uz-spin', deg.toFixed(2) + 'deg');
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Market ticker
  function formatNumber(n, digits) {
    try {
      const locale = document.documentElement.lang || undefined;
      return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(n);
    } catch (e) {
      return String(n);
    }
  }

  function formatPrice(item) {
    if (item == null || item.price == null) return '';
    const v = Number(item.price);
    if (Number.isNaN(v)) return '';

    // FX UZS rates can be large; keep 0 decimals.
    if ((item.category === 'FX') || (String(item.symbol || '').includes('/UZS'))) {
      return formatNumber(v, 0);
    }

    // Index/commodity/crypto can be shown with 2 decimals.
    return formatNumber(v, 2);
  }

  function formatChange(item) {
    if (item == null || item.change_pct == null) return '';
    const v = Number(item.change_pct);
    if (Number.isNaN(v)) return '';
    const sign = v > 0 ? '+' : '';
    return `${sign}${formatNumber(v, 2)}%`;
  }

  function escapeHtml(s) {
    return String(s || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function getBadgeText(symbol, name) {
    const sym = String(symbol || '').toUpperCase();
    if (sym === 'BTC') return '₿';
    if (sym === 'ETH') return 'Ξ';
    if (sym === 'XAU') return 'Au';
    if (sym === 'XAG') return 'Ag';
    if (sym === 'SPX') return 'S&P';
    if (sym === 'NDX') return 'NDX';
    if (sym === 'USDUZS') return 'USD';
    if (sym === 'EURUZS') return 'EUR';
    if (sym === 'RUBUZS') return 'RUB';
    return (name || sym || 'MKT').slice(0, 3).toUpperCase();
  }

  function buildTickerRowHtml(items) {
    const parts = (items || [])
      .filter(Boolean)
      .map((it) => {
        const name = it.name || it.symbol || '';
        const badge = getBadgeText(it.symbol, name);
        const price = formatPrice(it);
        const chg = formatChange(it);
        const chgPart = chg ? ` <span class="uz-ticker-chg">(${escapeHtml(chg)})</span>` : '';
        return `<span class="uz-ticker-item"><span class="uz-ticker-badge">${escapeHtml(badge)}</span><span class="uz-ticker-name">${escapeHtml(name)}:</span> <span class="uz-ticker-price">${escapeHtml(price)}</span>${chgPart}</span>`;
      })
      .filter(Boolean);

    return parts.join('<span class="uz-ticker-sep">•</span>');
  }

  async function refreshTicker() {
    const el = document.getElementById('uzTicker');
    const track = document.getElementById('uzTickerTrack');
    if (!el || !track) return;

    const loading = el.getAttribute('data-loading') || 'Loading…';
    try {
      track.textContent = loading;
      const resp = await fetch('/api/markets/ticker/', { headers: { 'Accept': 'application/json' } });
      if (!resp.ok) throw new Error('bad status');
      const data = await resp.json();
      const row = buildTickerRowHtml(data.items);
      if (!row) {
        el.style.display = 'none';
        return;
      }

      // Two identical sequences => seamless marquee with no visible “gap”.
      track.innerHTML = `<div class="uz-ticker-seq">${row}</div><div class="uz-ticker-seq" aria-hidden="true">${row}</div>`;
      el.style.display = '';

      // Slower speed.
      const seconds = 90;
      el.style.setProperty('--uz-ticker-duration', `${seconds}s`);
    } catch (e) {
      // Keep a non-blocking fallback.
      track.textContent = loading;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', refreshTicker);
  } else {
    refreshTicker();
  }
  window.setInterval(refreshTicker, 5 * 60 * 1000);
})();
