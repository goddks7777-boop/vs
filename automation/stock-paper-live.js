(() => {
  const won = n => Math.round(Number(n || 0)).toLocaleString('ko-KR') + '원';
  const num = (n, d = 2) => Number(n || 0).toLocaleString('ko-KR', {maximumFractionDigits:d});
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const stamp = v => String(v || '').slice(5, 16).replace('T', ' ');
  const cls = n => Number(n) >= 0 ? 'up' : 'down';

  async function load() {
    const bust = '?v=' + Date.now();
    const [state, metrics, status] = await Promise.all([
      fetch('stock_data/paper_week_krx.json' + bust, {cache:'no-store'}).then(r => {if(!r.ok) throw Error('주식 투자 기록을 불러오지 못했습니다'); return r.json()}),
      fetch('stock_data/full_metrics.json' + bust, {cache:'no-store'}).then(r => {if(!r.ok) throw Error('주식 지표를 불러오지 못했습니다'); return r.json()}),
      fetch('automation/status_10m.json' + bust, {cache:'no-store'}).then(r => {if(!r.ok) throw Error('자동화 상태를 불러오지 못했습니다'); return r.json()})
    ]);
    const byCode = Object.fromEntries((metrics.items || []).map(x => [x.code || x.symbol, x]));
    const positions = Object.entries(state.positions || {});
    const checkedAt = status.stockUpdatedAt || status.time;
    const age = Date.now() - Date.parse(checkedAt || 0);
    const healthy = Number.isFinite(age) && age <= 30 * 60 * 1000;
    const value = Number(status.stock?.value || state.cash || 0);
    const ret = Number(status.stock?.returnPct || 0);
    const sold = (state.trades || []).filter(x => x.side === 'SELL');
    const wins = sold.filter(x => Number(x.pnl) > 0).length;
    const posRows = positions.map(([symbol, p]) => {
      const x = byCode[symbol] || {}, current = Number(x.price || p.entry), gain = (current / Number(p.entry) - 1) * 100;
      return `<tr><td>${esc(p.market)}</td><td><b>${esc(symbol)}</b> ${esc(p.name)}</td><td>${won(p.entry)}</td><td>${won(current)}</td><td class="${cls(gain)}">${gain >= 0 ? '+' : ''}${gain.toFixed(2)}%</td><td>${esc(x.score ?? p.score ?? '—')}/6</td></tr>`;
    }).join('') || '<tr><td colspan="6">현재 보유 종목이 없어 현금 대기 중입니다.</td></tr>';
    const tradeRows = [...(state.trades || [])].reverse().map(t => `<tr><td>${stamp(t.time)}</td><td class="${t.side === 'BUY' ? 'up' : 'down'}">${esc(t.side)}</td><td>${esc(t.market)}</td><td><b>${esc(t.symbol)}</b> ${esc(t.name)}</td><td>${won(t.price)}</td><td>${t.pnl == null ? '—' : won(t.pnl)}</td><td>${esc(t.reason)}</td></tr>`).join('') || '<tr><td colspan="7">아직 체결이 없습니다.</td></tr>';
    const journals = [...(state.journal || [])].reverse().map(j => `<article class="journal"><div class="journal-time"><b>${stamp(j.time)}</b><span>${esc(j.session)}</span></div><div class="journal-notes">${(j.notes || []).map(n => `<div class="thought"><p>${esc(typeof n === 'string' ? n : n.comment)}</p></div>`).join('')}</div></article>`).join('');
    const main = document.querySelector('main.wrap') || document.querySelector('main');
    if (!main) throw Error('화면 본문을 찾지 못했습니다');
    main.innerHTML = `<div class="sub">KOSPI · KOSDAQ PAPER TRADING</div><h1>주식 1주일 모의투자</h1><p class="sub">한국 정규장 거래시간에만 가상 체결하며 실제 주문은 전혀 발생하지 않습니다.</p><p class="live-status ${healthy ? 'ok' : 'warn'}"><b>● ${healthy ? 'GitHub 자동화 정상' : '자동화 갱신 지연 · Actions 확인 필요'}</b> · 마지막 주식 점검 ${esc(checkedAt)} · ${esc(status.stock?.session)} · 실제 주문 ${Number(status.actualOrders || 0)}건</p><div class="cards"><div class="card"><span>가상자산</span><b>${won(value)}</b></div><div class="card"><span>수익률</span><b class="${cls(ret)}">${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%</b></div><div class="card"><span>현금</span><b>${won(state.cash)}</b></div><div class="card"><span>보유종목</span><b>${positions.length}/5</b></div><div class="card"><span>승률</span><b>${sold.length ? (wins / sold.length * 100).toFixed(1) : '0.0'}%</b></div></div><section class="panel"><h2>현재 가상 보유</h2><div class="box"><table><thead><tr><th>시장</th><th>종목</th><th>매수가</th><th>현재가</th><th>수익률</th><th>점수</th></tr></thead><tbody>${posRows}</tbody></table></div></section><section class="panel"><h2>시간별 판단 기록</h2><div class="box">${journals}</div></section><section class="panel"><h2>가상 체결 기록</h2><div class="box"><table><thead><tr><th>시각</th><th>구분</th><th>시장</th><th>종목</th><th>체결가</th><th>실현손익</th><th>이유</th></tr></thead><tbody>${tradeRows}</tbody></table></div></section><section class="panel"><h2>거래 안전 규칙</h2><p>매수·매도는 KOSPI·KOSDAQ 정규장에만 가상으로 처리합니다. 장외시간·주말·휴장일에는 주문을 만들지 않습니다.</p><p><b>안전:</b> PAPER 모드만 사용하며 실제 주문은 항상 0건입니다.</p></section>`;
  }
  const style = document.createElement('style');
  style.textContent = '.live-status{border-radius:12px;padding:12px 14px}.live-status.ok{background:#29312f;border:1px solid #61706a;color:#e3ece8}.live-status.warn{background:#3a2b0b;border:1px solid #b17b16;color:#ffe4a3}.journal{padding:12px 0;border-bottom:1px solid #444}.journal-time{display:flex;gap:12px;margin-bottom:6px}.journal-time span{color:#aaa}';
  document.head.appendChild(style);
  load().catch(error => {const main=document.querySelector('main.wrap') || document.querySelector('main'); if(main) main.insertAdjacentHTML('afterbegin', `<p class="live-status warn"><b>데이터 표시 오류</b> · ${esc(error.message)}</p>`)});
})();

