
(() => {
  const previousDraw = window.draw;
  const TARGET = '일목균형표(일목구름)';
  const line = (ctx, points, color, width = 3, dash = []) => {
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash);
    ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.stroke(); ctx.restore();
  };
  const text = (ctx, value, x, y, color='#c7d3df', size=12, align='left') => {
    ctx.fillStyle=color;ctx.font=`700 ${size}px Pretendard, sans-serif`;ctx.textAlign=align;ctx.fillText(value,x,y);ctx.textAlign='left';
  };
  const curve = (startX, endX, values) => values.map((y,i)=>[startX+i*(endX-startX)/(values.length-1),y]);

  function drawIchimoku(canvas) {
    const ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height,current=575,left=42,right=w-25;
    ctx.clearRect(0,0,w,h);ctx.fillStyle='#081422';ctx.fillRect(0,0,w,h);
    ctx.fillStyle='#13283d';ctx.fillRect(current,22,right-current,228);
    text(ctx,'과거 가격 구간',left,18,'#8fa3ba',11);text(ctx,'현재',current,276,'#e7eef8',12,'center');text(ctx,'26기간 앞(미래 표시 영역)',(current+right)/2,18,'#8dc9ff',11,'center');
    line(ctx,[[current,24],[current,252]],'#71869d',2,[6,6]);

    const price=curve(left,current,[208,198,187,193,177,166,154,160,143,130,119,105,91,78,64,51]);
    const tenkan=curve(left,current,[200,195,187,183,174,165,157,151,142,132,121,109,96,83,69,58]);
    const kijun=curve(left,current,[211,207,201,196,190,183,176,168,159,150,140,130,119,108,97,87]);
    line(ctx,price,'#f2f6fa',5);line(ctx,tenkan,'#438cff',3);line(ctx,kijun,'#ffbf52',3);

    // Chikou Span is today's closing-price curve plotted 26 periods to the left.
    const chikou=price.slice(4).map(([x,y])=>[x-150,y]);
    line(ctx,chikou,'#b8a2d8',2,[5,4]);
    text(ctx,'후행스팬: 종가를 26기간 과거에 표시',55,78,'#c6b7df',11);

    // Both leading spans are plotted 26 periods forward. Historical cloud remains
    // visible on the left; the portion right of CURRENT is the future cloud.
    const cloudX0=270,cloudA=[177,169,160,151,141,130,119,108,96,84,73,62,52,45],cloudB=[196,190,183,176,167,158,148,137,126,115,104,93,82,72];
    const spanA=curve(cloudX0,right,cloudA),spanB=curve(cloudX0,right,cloudB);
    ctx.fillStyle='#2ad4a72b';ctx.beginPath();spanA.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));[...spanB].reverse().forEach(([x,y])=>ctx.lineTo(x,y));ctx.closePath();ctx.fill();
    line(ctx,spanA,'#2ad4a7',3);line(ctx,spanB,'#df7d9a',3);
    ctx.save();ctx.beginPath();ctx.rect(current,22,right-current,228);ctx.clip();ctx.fillStyle='#2ad4a738';ctx.beginPath();spanA.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));[...spanB].reverse().forEach(([x,y])=>ctx.lineTo(x,y));ctx.closePath();ctx.fill();ctx.restore();

    text(ctx,'가격이 구름 위',405,42,'#f2f6fa',12);text(ctx,'전환선(9) > 기준선(26)',330,66,'#77b6ff',11);
    text(ctx,'선행스팬 A',(current+right)/2,48,'#54e0b9',11,'center');text(ctx,'선행스팬 B',(current+right)/2,145,'#f09ab2',11,'center');
    text(ctx,'미래 구름: A가 B 위 → 상승 우세 예시',(current+right)/2,235,'#a9f0d8',11,'center');
  }

  window.draw = function(name) {
    if (name !== TARGET) return previousDraw(name);
    const canvas=document.getElementById('demo')||document.getElementById('stockDemo');
    if (!canvas) return;
    drawIchimoku(canvas);
    const definition=document.getElementById('me'),good=document.getElementById('mg'),bad=document.getElementById('mb');
    if(definition) definition.textContent='전환선은 최근 9기간 고가·저가의 중간, 기준선은 26기간 중간입니다. 선행스팬 A는 전환선과 기준선의 중간, 선행스팬 B는 52기간 고가·저가의 중간이며 둘 다 26기간 앞으로 이동해 구름을 만듭니다. 후행스팬은 현재 종가를 26기간 과거에 표시합니다.';
    if(good) good.textContent='가격이 구름 위에 있고 전환선이 기준선 위이며, 미래 구름에서 선행스팬 A가 B보다 높고 거래량까지 증가하면 상승 추세가 여러 조건에서 함께 확인된 예입니다.';
    if(bad) bad.textContent='가격이 구름 안에 있거나 구름이 얇고 두 선이 자주 교차하면 방향이 불분명합니다. 구름 돌파 하나만 보고 사지 말고 종가 확정·거래량·상위 시간대 추세를 함께 확인합니다.';
    const legend=document.getElementById('visualLegend');
    if (legend) legend.innerHTML='<span>흰색: 가격</span><span>파랑: 전환선(9)</span><span>노랑: 기준선(26)</span><span>보라 점선: 후행스팬(종가를 26기간 과거로)</span><span>초록: 선행스팬 A</span><span>분홍: 선행스팬 B</span>';
  };
})();

(() => {
  const storageKey = 'upbitSelectedIndicators';
  const lessons = {
    'RSI': ['최근 가격이 얼마나 빠르게 올랐거나 내렸는지 0~100으로 보는 속도계예요.', 'RSI가 30 아래에서 다시 올라오고 가격 저점도 높아지면 매도 힘이 약해져 반등한 예가 있어요.', '30 아래라고 바로 바닥은 아니며 강한 하락에서는 과매도가 오래 이어질 수 있어요.'],
    'OBV': ['오른 날 거래량은 더하고 내린 날 거래량은 빼서 돈의 흐름을 한 줄로 보여줘요.', '가격은 비슷한 저점인데 OBV 저점이 높아지면 조용히 매수량이 쌓여 이후 가격이 오른 예가 있어요.', '한 거래소의 거래량만 보면 전체 시장 자금과 다를 수 있어요.'],
    'ADX/DMI': ['ADX는 추세의 힘, +DI와 −DI는 상승·하락 중 어느 쪽이 센지 보여줘요.', '+DI가 −DI 위로 올라가고 ADX가 20~25 이상으로 강해지면 상승 추세가 이어진 예가 있어요.', '횡보장에서는 두 선이 자주 교차해 가짜 신호가 많아요.'],
    'MACD': ['빠른 이동평균과 느린 이동평균의 간격으로 추세 전환을 살펴봐요.', 'MACD가 신호선을 상향 돌파하고 히스토그램이 커지며 거래량도 늘면 상승한 예가 있어요.', '이미 가격이 움직인 뒤 신호가 나오는 후행 지표예요.'],
    '볼린저밴드': ['20기간 평균선 주변에 가격 흔들림의 2배 폭으로 위·아래 밴드를 그려요.', '밴드가 좁아진 뒤 거래량과 함께 상단 밴드를 종가로 돌파하면 강한 움직임이 시작된 예가 있어요.', '상단 밴드에 닿았다는 이유만으로 과매수나 즉시 하락을 뜻하지 않아요.'],
    '일목균형표(일목구름)': ['전환선·기준선·선행스팬·후행스팬으로 추세와 지지·저항을 한 번에 살펴봐요.', '가격이 구름 위에 있고 전환선이 기준선 위이며 거래량까지 늘면 상승 조건이 함께 확인된 예예요.', '가격이 구름 안에 있거나 구름이 얇으면 방향이 불분명해요.'],
    'ATR': ['가격이 보통 얼마나 크게 흔들리는지 보여주는 변동성 자예요.', 'ATR에 맞춰 손절 폭과 매수 수량을 줄이면 큰 변동에도 한 번의 손실을 제한할 수 있어요.', '오를지 내릴지는 알려주지 않으므로 추세 지표와 함께 봐야 해요.']
  };
  const missingCards = [
    ['Stoch RSI','혼합 · 모멘텀','RSI 안에서 과열·침체를 더 민감하게 확인'],['MFI','혼합 · 가격·거래량','가격과 거래량을 함께 본 자금 과열 속도'],['CMF','혼합 · 자금흐름','종가 위치와 거래량으로 매수·매도 압력 확인'],['일목균형표(일목구름)','전통 · 추세·구조','구름·전환선·기준선으로 추세와 지지·저항 확인'],['시장구조 BOS/CHOCH','최근 · 시장구조','고점·저점 돌파로 추세 지속과 전환 확인'],['주문장 불균형','최근 · 주문흐름','매수·매도 호가 벽의 크기와 실제 체결 확인'],['테이커 매수/매도 비율','최근 · 주문흐름','즉시 체결된 매수와 매도의 힘 비교'],['ETF 순유입','최근 · 기관수급','현물 ETF로 들어오고 나간 기관 자금 확인'],['공포·탐욕 지수','심리 · 보조용','시장 심리를 극단적 공포부터 탐욕까지 요약'],['피보나치 되돌림','전통 · 지지저항','상승·하락 뒤 되돌림 후보 구간 확인'],['롱/숏 비율','파생 · 보조용','시장 참여자의 방향 쏠림 확인'],['비트코인 도미넌스','시장비교','전체 코인 시가총액 중 BTC 비중 확인'],['NUPL','온체인 · 장기','시장 전체 미실현 손익 구간 확인'],['Puell Multiple','온체인 · 장기','채굴자 수익의 장기 평균 대비 수준'],['거래소 보유량','온체인 · 공급','거래소에 대기 중인 잠재 매도 공급'],['고래 거래소 비율','온체인 · 고래','상위 대형 입금이 전체 입금에서 차지하는 비중']
  ];
  const readSelected = () => { try { const value=JSON.parse(localStorage.getItem(storageKey)||'[]'); return Array.isArray(value)?value:[]; } catch (_) { return []; } };
  const saveSelected = () => localStorage.setItem(storageKey, JSON.stringify([...document.querySelectorAll('[data-pick]:checked')].map(input => input.dataset.pick)));

  const repair = () => {
    const grid=[...document.querySelectorAll('.grid')].find(node=>node.querySelector('.card[data-ind]'));
    if(grid)missingCards.forEach(([name,tag,description])=>{if(!grid.querySelector(`[data-ind="${CSS.escape(name)}"]`))grid.insertAdjacentHTML('beforeend',`<div class="card modern" data-ind="${name}" tabindex="0"><span class="tag">${tag}</span><h3>${name}</h3><p>${description}</p><small class="sub">다른 종류의 지표와 함께 확인하세요.</small><label class="pick" onclick="event.stopPropagation()"><input type="checkbox" data-pick="${name}"> 시장 보고서에서 보기</label></div>`);});
    if (!document.getElementById('modal')) {
      document.body.insertAdjacentHTML('beforeend', `<div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="mt"><div class="modalbox"><button class="close" id="close" type="button">닫기 ×</button><span class="tag">코인 지표 그림 설명</span><h2 id="mt"></h2><p id="me" class="sub"></p><canvas id="demo" width="820" height="280" aria-label="선택한 지표 예시 차트"></canvas><div id="visualLegend" class="sub"></div><div class="lesson"><div class="easy good"><b>상승으로 이어진 쉬운 예시</b><p id="mg"></p></div><div class="easy bad"><b>이것만 믿으면 안 되는 이유</b><p id="mb"></p></div></div><p class="sub"><b>실전 확인:</b> 신호가 완성된 봉의 종가, 거래량, 상위 시간대 추세를 함께 확인하세요.</p></div></div>`);
    }
    const modal=document.getElementById('modal'), close=document.getElementById('close');
    const closeModal=()=>{modal.classList.remove('open');document.body.style.overflow='';};
    close.onclick=event=>{event.preventDefault();event.stopPropagation();closeModal();};
    modal.onclick=event=>{if(event.target===modal)closeModal();};
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&modal.classList.contains('open'))closeModal();});

    const selected=readSelected();
    document.querySelectorAll('.card[data-ind]').forEach(oldCard => {
      const card=oldCard.cloneNode(true); oldCard.replaceWith(card);
      const name=card.dataset.ind, input=card.querySelector('[data-pick]');
      if(input){input.checked=selected.includes(input.dataset.pick);input.addEventListener('change',saveSelected);}
      const open=()=>{
        const basic=card.querySelector('p')?.textContent.trim()||`${name}의 현재 상태를 보여주는 보조지표예요.`;
        const info=lessons[name]||[basic,`${name} 신호가 가격 방향·거래량 증가와 함께 좋아지면 상승으로 이어진 예가 있어요.`,`${name} 하나만으로 매수하지 말고 다른 종류의 지표와 함께 확인하세요.`];
        document.getElementById('mt').textContent=name;document.getElementById('me').textContent=info[0];document.getElementById('mg').textContent=info[1];document.getElementById('mb').textContent=info[2];
        modal.classList.add('open');document.body.style.overflow='hidden';requestAnimationFrame(()=>{if(typeof window.draw==='function')window.draw(name);});
      };
      card.addEventListener('click',event=>{if(!event.target.closest('.pick'))open();});
      card.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&!event.target.closest('.pick')){event.preventDefault();open();}});
    });
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',repair);else repair();
})();


