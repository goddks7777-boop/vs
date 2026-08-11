(() => {
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const compact = n => {
    n = Number(n || 0);
    if (!n) return '—';
    if (n >= 1e12) return (n / 1e12).toLocaleString('ko-KR', {maximumFractionDigits:2}) + '조원';
    return (n / 1e8).toLocaleString('ko-KR', {maximumFractionDigits:0}) + '억원';
  };
  fetch('stock_data/full_metrics.json?v=' + Date.now(), {cache:'no-store'}).then(r => r.json()).then(payload => {
    const caps = new Map(payload.items.map(x => [`${x.market}|${x.name}`, x]));
    window.__stockCaps = caps;
    if (typeof D !== 'undefined') D.forEach(row => {
      const live = caps.get(`${row.market}|${row.name}`);
      if (!live) return;
      for (const key of ['price','change','amount','marketCap','marketCapText','score','rsi','adx','plusDI','minusDI','obv','volumeRatio','atrPct','ma20','ma60','status']) {
        if (live[key] !== undefined) row[key] = live[key];
      }
    });
    const header = document.querySelector('th[data-k="price"]');
    if (header && !document.querySelector('th[data-market-cap]')) header.insertAdjacentHTML('afterend', '<th data-market-cap>시가총액</th>');
    const decorate = () => {
      document.querySelectorAll('#tb tr').forEach(row => {
        if (row.querySelector('[data-market-cap-cell]')) return;
        const cells = row.children;
        if (cells.length < 5) return;
        const item = caps.get(`${cells[0].textContent.trim()}|${cells[2].textContent.trim()}`);
        cells[4].insertAdjacentHTML('afterend', `<td data-market-cap-cell title="${esc(item?.marketCapText || '시가총액 수집 대기')}"><b>${compact(item?.marketCap)}</b></td>`);
      });
    };
    const original = window.render;
    if (typeof original === 'function') window.render = function(){ original(); decorate(); };
    decorate();
    const summary = document.getElementById('resultSummary');
    if (summary) summary.insertAdjacentHTML('beforeend', `<span>전체 반영 <b>${Number(payload.universe).toLocaleString()}개</b></span><span>지표 완료 <b>${Number(payload.complete).toLocaleString()}개</b></span><span>신규·재시도 <b>${Number(payload.pending).toLocaleString()}개</b></span><span>갱신 <b>${esc(payload.time)}</b></span>`);
  }).catch(() => {});
})();

(() => {
  const initSearch = async () => {
    let data = typeof D !== 'undefined' && Array.isArray(D) ? D : [];
    if (!data.length) {
      try {
        const payload = await fetch('stock_data/full_metrics.json?v=' + Date.now(), {cache:'no-store'}).then(response => {
          if (!response.ok) throw new Error('전체 종목 데이터를 불러오지 못했습니다');
          return response.json();
        });
        data = Array.isArray(payload.items) ? payload.items : [];
      } catch (error) {
        const summary = document.getElementById('resultSummary');
        if (summary) summary.innerHTML = `<span class="down"><b>종목 데이터 오류</b> · ${String(error.message || error)}</span>`;
      }
    }
    const markets = ['KOSPI', 'KOSDAQ'];
    const queryInput = document.getElementById('q');
    const statusSelect = document.getElementById('status');
    const tableBody = document.getElementById('tb');
    const summary = document.getElementById('resultSummary');
    const pageInfo = document.getElementById('pageInfo');
    const prevButton = document.getElementById('prev');
    const nextButton = document.getElementById('next');
    const marketChecks = [...document.querySelectorAll('input[data-market]')];
    if (!queryInput || !statusSelect || !tableBody || !summary || !pageInfo || !prevButton || !nextButton) return;
    let sortKey = 'market', sortDirection = 1, currentPage = 1;
    const perPage = 100;
    const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const fmt = (value, currency) => value == null ? '—' : Number(value).toLocaleString('ko-KR', {maximumFractionDigits:4}) + (currency === 'USD' ? ' $' : ' 원');
    const compact = value => { const n = Number(value || 0); return !n ? '—' : n >= 1e12 ? (n / 1e12).toLocaleString('ko-KR', {maximumFractionDigits:2}) + '조원' : (n / 1e8).toLocaleString('ko-KR', {maximumFractionDigits:0}) + '억원'; };
    const renderSearch = () => {
      const enabled = marketChecks.filter(box => box.checked).map(box => box.dataset.market);
      const query = queryInput.value.trim().toLocaleLowerCase('ko-KR');
      const wantedStatus = statusSelect.value;
      const filtered = data.filter(item => enabled.includes(item.market) && (!wantedStatus || item.status === wantedStatus) && (!query || `${item.symbol} ${item.name} ${item.industry || ''}`.toLocaleLowerCase('ko-KR').includes(query)));
      const counts = Object.fromEntries(markets.map(market => [market, filtered.filter(item => item.market === market).length]));
      summary.innerHTML = `<span><b>필터 결과 ${filtered.length.toLocaleString()}개</b></span>` + markets.map(market => `<span>${market} <b>${counts[market].toLocaleString()}개</b></span>`).join('');
      filtered.sort((a, b) => { const left = a[sortKey], right = b[sortKey]; if (left == null && right == null) return 0; if (left == null) return 1; if (right == null) return -1; return (typeof left === 'number' ? left - right : String(left).localeCompare(String(right), 'ko')) * sortDirection; });
      const pages = Math.max(1, Math.ceil(filtered.length / perPage));
      currentPage = Math.min(Math.max(currentPage, 1), pages);
      const rows = filtered.slice((currentPage - 1) * perPage, currentPage * perPage);
      tableBody.innerHTML = rows.map(item => { const live = window.__stockCaps?.get(`${item.market}|${item.name}`); return `<tr><td>${esc(item.market)}</td><td><b>${esc(item.symbol)}</b></td><td>${esc(item.name)}</td><td>${esc(item.industry)}</td><td>${fmt(item.price, item.currency)}</td><td data-market-cap-cell title="${esc(live?.marketCapText || '시가총액 수집 대기')}"><b>${compact(live?.marketCap)}</b></td><td class="${item.change > 0 ? 'up' : item.change < 0 ? 'down' : ''}">${item.change == null ? '—' : Number(item.change).toLocaleString('ko-KR', {maximumFractionDigits:3}) + '%'}</td><td>${item.score == null ? '—' : esc(item.score) + '/6'}</td><td>${item.rsi ?? '—'}</td><td>${item.adx ?? '—'}</td><td>${item.obv ?? '—'}</td><td>${item.volumeRatio == null ? '—' : item.volumeRatio + '배'}</td><td><span class="status">${esc(item.status)}</span></td></tr>`; }).join('');
      pageInfo.textContent = `${currentPage} / ${pages} · 검색 결과 ${filtered.length.toLocaleString()}개`;
      prevButton.disabled = currentPage <= 1; nextButton.disabled = currentPage >= pages;
    };
    queryInput.oninput = null; statusSelect.onchange = null;
    marketChecks.forEach(box => { box.onchange = null; });
    prevButton.onclick = null; nextButton.onclick = null;
    document.querySelectorAll('th[data-k]').forEach(header => { header.onclick = null; });
    queryInput.addEventListener('input', () => { currentPage = 1; renderSearch(); });
    statusSelect.addEventListener('change', () => { currentPage = 1; renderSearch(); });
    marketChecks.forEach(box => box.addEventListener('change', () => { currentPage = 1; renderSearch(); }));
    prevButton.addEventListener('click', () => { currentPage -= 1; renderSearch(); });
    nextButton.addEventListener('click', () => { currentPage += 1; renderSearch(); });
    document.querySelectorAll('th[data-k]').forEach(header => header.addEventListener('click', () => { sortDirection = sortKey === header.dataset.k ? -sortDirection : 1; sortKey = header.dataset.k; renderSearch(); }));
    window.stockSearchRender = renderSearch;
    renderSearch();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initSearch); else initSearch();
})();


