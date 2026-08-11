
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
