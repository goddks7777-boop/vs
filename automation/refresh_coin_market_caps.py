"""CoinGecko 공개 시장 데이터에서 업비트 KRW 종목의 원화 시가총액을 매칭한다."""
import json,re,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"monitor_data"/"coin_market_caps.json";KST=timezone(timedelta(hours=9))
MANUAL={"BTC":"bitcoin","ETH":"ethereum","USDT":"tether","USDC":"usd-coin","XRP":"ripple","SOL":"solana","DOGE":"dogecoin","ADA":"cardano","AVAX":"avalanche-2","LINK":"chainlink","DOT":"polkadot","TRX":"tron","SHIB":"shiba-inu","SUI":"sui","BCH":"bitcoin-cash","ETC":"ethereum-classic","XLM":"stellar","NEAR":"near","ICP":"internet-computer","UNI":"uniswap","AAVE":"aave","ARB":"arbitrum","OP":"optimism","STX":"blockstack","RENDER":"render-token","TAO":"bittensor","ONDO":"ondo-finance","ENA":"ethena","PEPE":"pepe","BONK":"bonk","WLD":"worldcoin-wld","MNT":"mantle","POL":"polygon-ecosystem-token"}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"upbit-market-cap-research/1.0","Accept":"application/json"})
 for attempt in range(6):
  try:
   with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   if e.code!=429 or attempt==5:raise
   time.sleep(max(12,int(e.headers.get("Retry-After","0") or 0),12+attempt*6))
html=(ROOT/"업비트_원화마켓_시각화_보고서_2026-08-11.html").read_text(encoding="utf-8");m=re.search(r'const D=(\[.*?\]);let sortK=',html,re.S)
if not m:raise SystemExit("embedded screener data not found")
coins=json.loads(m.group(1));market=[]
for page in range(1,7):
 q=urllib.parse.urlencode({"vs_currency":"krw","order":"market_cap_desc","per_page":250,"page":page,"sparkline":"false"});batch=get("https://api.coingecko.com/api/v3/coins/markets?"+q);market+=batch
 if len(batch)<250:break
 time.sleep(7.5)
by_symbol={}
for x in market:by_symbol.setdefault(str(x.get("symbol","")).upper(),[]).append(x)
items=[]
for coin in coins:
 symbol=coin["symbol"].upper();candidates=by_symbol.get(symbol,[]);picked=None;method="unmatched"
 if symbol in MANUAL:
  picked=next((x for x in candidates if x.get("id")==MANUAL[symbol]),None);method="manual-id" if picked else method
 if not picked and len(candidates)==1:picked=candidates[0];method="unique-symbol"
 if not picked and candidates:
  en=re.sub(r'[^a-z0-9]','',coin.get("en","").lower());scored=sorted(candidates,key=lambda x:((re.sub(r'[^a-z0-9]','',str(x.get("name","")).lower())==en),x.get("market_cap") or 0),reverse=True);picked=scored[0];method="name-or-largest-cap"
 items.append({"symbol":symbol,"name":coin.get("name"),"coinGeckoId":picked.get("id") if picked else None,"marketCapKrw":picked.get("market_cap") if picked else None,"marketCapRank":picked.get("market_cap_rank") if picked else None,"circulatingSupply":picked.get("circulating_supply") if picked else None,"matchMethod":method})
payload={"updatedAt":datetime.now(KST).isoformat(timespec="seconds"),"source":{"name":"CoinGecko Public API","endpoint":"/api/v3/coins/markets","currency":"KRW","note":"업비트는 시가총액을 제공하지 않아 외부 집계값 사용"},"requested":len(coins),"matched":sum(x["marketCapKrw"] is not None for x in items),"items":items}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n");print(json.dumps({"status":"UPDATED","requested":len(coins),"matched":payload["matched"]},ensure_ascii=False))
