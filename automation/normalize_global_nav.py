"""모든 정적 페이지의 global-nav 항목·순서·크기를 한 규격으로 맞춘다."""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COIN={
 "업비트_원화마켓_시각화_보고서_2026-08-11.html":("₿","코인 시장"),
 "업비트_1시간_모니터링.html":("◷","코인 모니터링"),
 "코인_1주일_가상투자.html":("↗","코인 모의투자"),
 "코인_AI스윙_학습검증.html":("◆","AI 스윙"),
 "코인_싸이클_분석.html":("◉","BTC 싸이클"),
 "코인_유동.html":("≋","코인 유동"),
 "코인_매집포착.html":("⌁","매집포착"),
 "업비트_지표_백과.html":("▦","코인 지표"),
}
STOCK={
 "주식_종합분석.html":("▥","주식 시장"),
 "주식_기초지식.html":("ⓘ","주식 기초"),
 "주식_매수매도_타이밍.html":("↕","주식 타이밍"),
 "주식_1주일_모의투자.html":("◎","주식 모의투자"),
 "주식_지표_백과.html":("▦","주식 지표"),
}
STYLE="""<style id="unified-global-nav-style">
.global-nav{position:sticky!important;top:0!important;z-index:1000!important;background:rgba(9,17,28,.96)!important;border-bottom:1px solid #29405a!important;backdrop-filter:blur(14px)}
.global-nav-inner{width:100%!important;max-width:1600px!important;min-height:64px!important;margin:0 auto!important;padding:9px 180px!important;display:flex!important;align-items:center!important;justify-content:center!important;gap:7px!important;position:relative!important;overflow-x:auto!important;scrollbar-width:thin}
.global-nav a{height:44px!important;min-width:106px!important;padding:0 13px!important;border:1px solid transparent!important;border-radius:11px!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:7px!important;color:#a9bacd!important;text-decoration:none!important;font-size:14px!important;font-weight:750!important;line-height:1!important;white-space:nowrap!important;flex:0 0 auto!important}
.global-nav a:hover{color:#fff!important;background:#17283b!important;border-color:#36516d!important}.global-nav a.active{color:#fff!important;background:#173c6b!important;border-color:#3f75ad!important;box-shadow:inset 0 -3px #65a0ff!important}.global-nav .home-link{position:absolute!important;left:20px!important;min-width:118px!important;background:#152235!important;color:#fff!important}.global-nav .switch{position:absolute!important;right:20px!important;min-width:142px!important;background:#15304e!important;color:#fff!important}.global-nav .gn-icon{font-size:15px!important}.global-nav small{display:none!important}
.global-nav.home-all .global-nav-inner{padding:9px 14px!important;justify-content:flex-start!important}.global-nav.home-all .home-link{position:static!important}.global-nav.home-all a{min-width:102px!important}
@media(max-width:1150px){.global-nav-inner{justify-content:flex-start!important;padding:9px 12px!important}.global-nav .home-link,.global-nav .switch{position:static!important}.global-nav a{min-width:104px!important}}
</style>"""
def link(page,icon,label,current,extra=""):
 active=" active" if page==current else ""
 return f'<a href="{page}" data-page="{page}" class="{extra}{active}"><span class="gn-icon">{icon}</span><span>{label}</span><small>현재 위치</small></a>'
def nav_for(name):
 if name=="업비트_분석_홈.html":
  links=[link(name,"⌂","통합 홈",name,"home-link")]
  links += [link(p,*v,name) for p,v in COIN.items()]
  links += [link(p,*v,name) for p,v in STOCK.items()]
  return '<nav class="global-nav home-all" aria-label="전체 메뉴"><div class="global-nav-inner">'+''.join(links)+'</div></nav>'
 if name in COIN:
  links=[link("업비트_분석_홈.html","⌂","통합 홈",name,"home-link")]+[link(p,*v,name) for p,v in COIN.items()]+[link("주식_종합분석.html","⇄","주식으로 가기",name,"switch")]
  return '<nav class="global-nav" aria-label="코인 메뉴"><div class="global-nav-inner">'+''.join(links)+'</div></nav>'
 if name in STOCK:
  links=[link("업비트_분석_홈.html","⌂","통합 홈",name,"home-link")]+[link(p,*v,name) for p,v in STOCK.items()]+[link("업비트_원화마켓_시각화_보고서_2026-08-11.html","⇄","코인으로 가기",name,"switch")]
  return '<nav class="global-nav" aria-label="주식 메뉴"><div class="global-nav-inner">'+''.join(links)+'</div></nav>'
 return None
updated=0
for path in ROOT.glob("*.html"):
 nav=nav_for(path.name)
 if not nav:continue
 text=path.read_text(encoding="utf-8");before=text
 text=re.sub(r'<style id="unified-global-nav-style">[\s\S]*?</style>',STYLE,text,count=1)
 if 'id="unified-global-nav-style"' not in text:
  if '</head>' in text:text=text.replace('</head>',STYLE+'</head>',1)
  else:text=text.replace('<body',STYLE+'<body',1)
 text=re.sub(r'<nav class="global-nav[^>]*>[\s\S]*?</nav>',nav,text,count=1)
 if path.name=="코인_매집포착.html" and "accumulation-trade-plan-live.js" not in text:
  text=text.replace('</body>','<script src="automation/accumulation-trade-plan-live.js"></script></body>',1)
 if text!=before:path.write_text(text,encoding="utf-8",newline="\n");updated+=1
print(f"updated={updated}")

