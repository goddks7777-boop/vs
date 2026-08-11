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

