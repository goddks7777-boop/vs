
(() => {
  const won=n=>Math.round(Number(n||0)).toLocaleString('ko-KR')+'원';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const badge=(type)=>type==='BUY'?'매수':type==='SELL'?'매도':type==='RESET'?'초기화':'관망';
  Promise.all([
    fetch('monitor_data/paper_week.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),
    fetch('automation/status_10m.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json())
  ]).then(([state,status])=>{
    let panel=[...document.querySelectorAll('.panel')].find(x=>x.textContent.includes('1-WEEK PAPER TRADING'));
    if(!panel){panel=document.createElement('section');panel.className='panel';document.querySelector('main.wrap')?.prepend(panel)}
    const ret=Number(status.coin?.returnPct||0),positions=Object.entries(state.positions||{}),last=(status.coin?.actions||[])[0];
    panel.id='livePaperSummary';
    panel.innerHTML=`<div class="sub">LIVE PAPER TRADING · JSON 동기화</div><h2>현재 시점 기준 코인 모의투자</h2><div class="paper-sync-grid"><div><small>새 시작</small><b>${esc(state.start)}</b></div><div><small>가상자산</small><b>${won(status.coin?.value)}</b></div><div><small>수익률</small><b class="${ret>=0?'up':'down'}">${ret>=0?'+':''}${ret.toFixed(2)}%</b></div><div><small>현금</small><b>${won(state.cash)}</b></div><div><small>보유</small><b>${positions.length}종목</b></div><div><small>신규 거래</small><b>${Number(status.coin?.trades||0)}건</b></div></div><p class="paper-positions"><b>현재 보유:</b> ${positions.length?positions.map(([s,p])=>`<span>${esc(s)} ${esc(p.name)}</span>`).join(' '):'현금 대기'}</p><p class="paper-action"><b>최근 판단:</b> ${last?`<span class="decision ${esc(String(last.type).toLowerCase())}">${badge(last.type)}</span> ${esc(last.symbol)} ${esc(last.name)} · ${esc(last.comment)}`:'기록 없음'}</p><p class="sub">마지막 점검 ${esc(status.time)} · 사용 신호 ${esc(status.signalTime)} · 실제 주문 ${Number(status.actualOrders||0)}건</p><p><a style="color:#72a7ff" href="코인_1주일_가상투자.html">매수·매도 기록 전체 보기 →</a></p>`;
  }).catch(error=>console.error('paper summary sync failed',error));
  const style=document.createElement('style');style.textContent='.paper-sync-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:14px 0}.paper-sync-grid>div{background:#091728;border:1px solid #20344b;border-radius:11px;padding:11px}.paper-sync-grid small,.paper-sync-grid b{display:block}.paper-sync-grid small{color:#8fa3ba;margin-bottom:5px}.paper-positions span{display:inline-block;background:#18304b;border-radius:99px;padding:5px 9px;margin:3px}.paper-action{background:#091728;border-radius:11px;padding:11px}.decision{display:inline-block;padding:3px 7px;border-radius:99px;background:#384b61}.decision.buy{background:#0c493b;color:#6ff0c8}.decision.sell{background:#542331;color:#ff9caf}@media(max-width:900px){.paper-sync-grid{grid-template-columns:repeat(2,1fr)}}';document.head.appendChild(style);
})();

