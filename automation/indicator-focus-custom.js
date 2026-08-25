(() => {
  const selectedKey = 'upbitSelectedIndicators';
  const viewsKey = 'upbitIndicatorFocusViewsV1';
  const liveColumns = {'RSI': 6, 'ADX/DMI': 7, 'OBV': 8};
  const fallback = ['RSI', 'OBV', 'ADX/DMI'];
  const read = (key, fallbackValue) => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || 'null');
      return Array.isArray(value) && value.length ? value : fallbackValue;
    } catch (_) { return fallbackValue; }
  };

  window.addEventListener('DOMContentLoaded', () => {
    const target = [...document.querySelectorAll('.panel h2')]
      .find(node => node.textContent.includes('281종목'))?.parentElement;
    if (!target) return;

    document.querySelectorAll('.focus-panel').forEach(node => node.remove());
    target.querySelectorAll('tr').forEach(row => [...row.children].forEach(cell => { cell.style.display = ''; }));

    const picked = [...new Set(read(selectedKey, fallback))];
    let views = read(viewsKey, [picked[0] || 'RSI']).filter(name => picked.includes(name));
    if (!views.length) views = [picked[0] || 'RSI'];

    const panel = document.createElement('section');
    panel.id = 'indicatorFocusManager';
    panel.className = 'focus-panel focus-manager';
    panel.innerHTML = `<div class="focus-manager-head"><div><h2>내가 선택한 지표 중심 보기</h2><p class="sub">처음에는 1개만 표시됩니다. 아래 + · − 버튼으로 원하는 만큼 구성하세요.</p></div><a class="focus-link" href="업비트_지표_백과.html">지표 선택 바꾸기 →</a></div><div class="focus-view-list" aria-live="polite"></div><div class="focus-controls"><button type="button" class="focus-control focus-add" aria-label="중심 보기 추가">＋</button><button type="button" class="focus-control focus-remove" aria-label="마지막 중심 보기 삭제">−</button><span class="focus-count"></span></div>`;
    target.parentNode.insertBefore(panel, target);

    const list = panel.querySelector('.focus-view-list');
    const count = panel.querySelector('.focus-count');
    const add = panel.querySelector('.focus-add');
    const remove = panel.querySelector('.focus-remove');
    const applyColumns = () => {
      const active = new Set(views);
      Object.entries(liveColumns).forEach(([name, index]) => target.querySelectorAll('tr').forEach(row => {
        if (row.children[index]) row.children[index].style.display = active.has(name) ? '' : 'none';
      }));
    };
    const saveAndRender = () => {
      localStorage.setItem(viewsKey, JSON.stringify(views));
      list.innerHTML = views.map((name, index) => `<div class="focus-view"><span class="focus-number">${index + 1}</span><label><span class="sr-only">${index + 1}번 중심 지표</span><select data-index="${index}">${picked.map(option => `<option value="${option.replace(/"/g, '&quot;')}"${option === name ? ' selected' : ''}>${option}</option>`).join('')}</select></label><span class="focus-state ${liveColumns[name] == null ? 'offline' : ''}">${liveColumns[name] == null ? '데이터 연동 예정' : '종목표 적용 중'}</span><button type="button" class="row-remove" data-remove="${index}" aria-label="${index + 1}번 중심 보기 삭제">−</button></div>`).join('');
      count.textContent = `현재 ${views.length}개`;
      remove.disabled = views.length <= 1;
      panel.querySelectorAll('select').forEach(select => select.addEventListener('change', event => {
        views[Number(event.currentTarget.dataset.index)] = event.currentTarget.value; saveAndRender();
      }));
      panel.querySelectorAll('.row-remove').forEach(button => button.addEventListener('click', event => {
        if (views.length <= 1) return; views.splice(Number(event.currentTarget.dataset.remove), 1); saveAndRender();
      }));
      applyColumns();
    };
    add.addEventListener('click', () => { views.push(picked.find(name => !views.includes(name)) || picked[0] || 'RSI'); saveAndRender(); });
    remove.addEventListener('click', () => { if (views.length > 1) { views.pop(); saveAndRender(); } });
    saveAndRender();
  });

  const style = document.createElement('style');
  style.textContent = `.focus-manager{margin-top:18px!important}.focus-manager-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.focus-manager-head h2{margin:0 0 7px}.focus-view-list{display:grid;gap:9px;margin:16px 0 12px}.focus-view{display:grid;grid-template-columns:34px minmax(180px,1fr) auto 38px;gap:9px;align-items:center;padding:10px;background:#0a1726;border:1px solid #294562;border-radius:12px}.focus-number{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:#17314d;color:#8fc0ff;font-weight:900}.focus-view select{width:100%;padding:10px 12px;border:1px solid #315270;border-radius:9px;background:#0e2135;color:#e8f2ff;font-weight:800}.focus-state{padding:6px 9px;border-radius:99px;background:#123b35;color:#74e3c3;font-size:12px;white-space:nowrap}.focus-state.offline{background:#392b22;color:#ffcf82}.focus-controls{display:flex;align-items:center;gap:8px}.focus-control,.row-remove{border:1px solid #315270;background:#17314d;color:#e8f2ff;border-radius:9px;cursor:pointer;font-size:22px;font-weight:900;line-height:1}.focus-control{width:42px;height:38px}.row-remove{width:36px;height:34px}.focus-control:hover,.row-remove:hover{background:#245685;border-color:#72a7ff}.focus-control:disabled{opacity:.35;cursor:not-allowed}.focus-count{color:#8fa3ba;font-size:12px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:720px){.focus-manager-head{display:block}.focus-manager-head .focus-link{display:inline-block;margin-top:8px}.focus-view{grid-template-columns:30px 1fr 36px}.focus-state{grid-column:2/3;justify-self:start}.focus-view .row-remove{grid-column:3;grid-row:1/3}}`;
  document.head.appendChild(style);
})();
{const script=document.createElement('script');script.src=`automation/coin-screener-enhance.js?v=${Date.now()}`;document.body.appendChild(script)}
{const script=document.createElement('script');script.src=`automation/accumulation-live.js?v=${Date.now()}`;document.body.appendChild(script)}

