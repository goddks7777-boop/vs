(() => {
  const won = n => Math.round(Number(n || 0)).toLocaleString('ko-KR') + '원';
  const num = (n, d = 4) => Number(n || 0).toLocaleString('ko-KR', {maximumFractionDigits:d});
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const stamp = v => String(v || '').slice(5, 16).replace('T', ' ');
  const cls = n => Number(n) >= 0 ? 'up' : 'down';

  async function load() {
    const bust = '?v=' + Date.now();
    const [state, latest, status] = await Promise.all([
      fetch('monitor_data/paper_week.json' + bust, {cache:'no-store'}).then(r => r.json()),
      fetch('monitor_data/latest.json' + bust, {cache:'no-store'}).then(r => r.json()),
      fetch('automation/status_10m.json' + bust, {cache:'no-store'}).then(r => r.json())
    ]);
    const metrics = Object.fromEntries((latest.items || []).map(x => [x.symbol, x]));
    const positions = Object.entries(state.positions || {});
    const value = Number(status.coin?.value || state.cash || 0), ret = Number(status.coin?.returnPct || 0);
    const sold = (state.trades || []).filter(x => x.side === 'SELL');
    const wins = sold.filter(x => Number(x.pnl) > 0).length;
    const posRows = positions.map(([symbol, p]) => {
      const x = metrics[symbol] || {}, current = Number(x.price || p.entry), gain = (current / Number(p.entry) - 1) * 100;
      return `<tr><td><b>${esc(symbol)}</b> ${esc(p.name)}</td><td>${num(p.entry)}</td><td>${num(current)}</td><td class="${cls(gain)}">${gain >= 0 ? '+' : ''}${gain.toFixed(2)}%</td><td>${esc(x.comboScore ?? p.score ?? '—')}/7</td><td>${num(p.atrPct, 2)}%</td></tr>`;
    }).join('') || '<tr><td colspan="6">현재 매수 조건을 충족한 종목이 없어 현금 대기 중입니다.</td></tr>';
    const tradeRows = [...(state.trades || [])].reverse().map(t => `<tr><td>${stamp(t.time)}</td><td class="${t.side === 'BUY' ? 'up' : 'down'}">${esc(t.side)}</td><td><b>${esc(t.symbol)}</b> ${esc(t.name)}</td><td>${num(t.price)}</td><td>${won(t.fee)}</td><td class="${cls(t.pnl)}">${t.pnl == null ? '—' : `${Number(t.pnl) >= 0 ? '+' : ''}${won(t.pnl)} (${Number(t.returnPct).toFixed(2)}%)`}</td><td>${esc(t.reason)}</td></tr>`).join('') || '<tr><td colspan="7">아직 체결이 없습니다.</td></tr>';
    const journals = [...(state.journal || [])].reverse().map(j => `<article class="journal"><div class="journal-time"><b>${stamp(j.time)}</b><span>${esc(j.market || j.session)}</span></div><div class="journal-notes">${(j.notes || []).map(n => typeof n === 'string' ? `<div class="thought watch"><span class="decision">WATCH</span><p>${esc(n)}</p></div>` : `<div class="thought ${esc(String(n.type || 'watch').toLowerCase())}"><span class="decision">${esc(n.type)}</span><b>${esc(n.symbol)} ${esc(n.name)}</b><p>${esc(n.comment)}</p></div>`).join('')}</div></article>`).join('');
    const main = document.querySelector('main.wrap');
    main.innerHTML = `<div class="sub">PAPER TRADING · ${esc(state.start)} ~ ${esc(state.end)}</div><h1>추천 조합 1주일 가상투자</h1><p class="sub">실제 주문은 전혀 발생하지 않습니다. 최신 완성 1시간봉 신호를 사용하고 10분마다 현재가로 가상 체결 여부를 판단합니다.</p><p class="live-status"><b>● GitHub 자동화 정상</b> · 마지막 점검 ${esc(status.time)} · 사용 신호 ${esc(status.signalTime || latest.time)} · 실제 주문 ${Number(status.actualOrders || 0)}건</p><div class="cards"><div class="card"><span>가상자산</span><b>${won(value)}</b></div><div class="card"><span>누적수익률</span><b class="${cls(ret)}">${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%</b></div><div class="card"><span>현금</span><b>${won(state.cash)}</b></div><div class="card"><span>보유종목</span><b>${positions.length}/5</b></div><div class="card"><span>승률</span><b>${sold.length ? (wins / sold.length * 100).toFixed(1) : '0.0'}%</b></div></div><section class="panel"><h2>자산 변화</h2><canvas id="chart" width="1200" height="210"></canvas></section><section class="panel"><h2>현재 가상 보유</h2><div class="box"><table><thead><tr><th>코인</th><th>매수가</th><th>현재가</th><th>수익률</th><th>현재점수</th><th>진입 ATR</th></tr></thead><tbody>${posRows}</tbody></table></div></section><section class="panel"><h2>10분별 매매 판단 일지</h2><div class="box">${journals}</div></section><section class="panel"><h2>가상 체결 기록</h2><div class="box"><table><thead><tr><th>시각</th><th>구분</th><th>코인</th><th>체결가</th><th>수수료</th><th>실현손익</th><th>이유</th></tr></thead><tbody>${tradeRows}</tbody></table></div></section><section class="panel"><h2>공개된 매매 규칙</h2><p><b>매수:</b> 6/7점 이상, RSI≤68, 거래량≥평균 1.2배, 거래대금 10억원 이상. 종목당 200만원, 최대 5종목.</p><p><b>재진입 제한:</b> 매도된 코인은 최소 1시간 동안 다시 사지 않습니다.</p><p><b>안전:</b> PAPER 모드만 사용하며 실제 거래소 주문은 0건입니다.</p></section>`;
    draw(state.curve || []);
  }
  function draw(curve) {
    const canvas = document.getElementById('chart'); if (!canvas || !curve.length) return;
    const x = canvas.getContext('2d'), values = curve.map(z => Number(z.value));
    const min = Math.min(...values) * .999, max = Math.max(...values) * 1.001, span = max - min || 1;
    x.strokeStyle = '#20344b'; for (let y=30;y<190;y+=40) { x.beginPath();x.moveTo(35,y);x.lineTo(1180,y);x.stroke(); }
    x.strokeStyle='#2ad4a7';x.lineWidth=4;x.beginPath();curve.forEach((z,i)=>{const px=35+i*1140/Math.max(curve.length-1,1),py=185-(Number(z.value)-min)/span*150;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();
  }
  const style=document.createElement('style');style.textContent='.live-status{background:#0b2d28;border:1px solid #1b806b;color:#bdf7e8;border-radius:12px;padding:12px 14px}.live-status b{color:#2ad4a7}';document.head.appendChild(style);
  load().catch(error=>{const main=document.querySelector('main.wrap');if(main)main.insertAdjacentHTML('afterbegin',`<p class="live-status"><b>데이터 표시 오류</b> · ${esc(error.message)} · 페이지를 새로고침해 주세요.</p>`)});
})();

