"""업비트 KRW 전체 1시간봉의 MA120 터치 성과와 ZRO 급등 전 패턴 유사도를 기록한다."""
import json, math, statistics, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"monitor_data"/"ma120_touch_similarity.json"; KST=timezone(timedelta(hours=9))
def api(path,params=None):
 q="?"+urllib.parse.urlencode(params or {}) if params else ""; req=urllib.request.Request("https://api.upbit.com/v1"+path+q,headers={"User-Agent":"ma120-touch-research/1.0"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def mean(a):return sum(a)/len(a) if a else 0
def completed(market):
 rows=api("/candles/minutes/60",{"market":market,"count":200}); now=datetime.now(KST); out=[]
 for x in rows:
  start=datetime.fromisoformat(x["candle_date_time_kst"]+"+09:00")
  if start+timedelta(hours=1)<=now:out.append(x)
 return list(reversed(out))
def rsi(a,n=14):
 d=[a[i]-a[i-1] for i in range(1,len(a))][-n:]; g=mean([max(x,0) for x in d]); loss=mean([max(-x,0) for x in d]); return 100 if loss==0 else 100-100/(1+g/loss)
def features(b,i):
 c=[float(x["trade_price"]) for x in b]; h=[float(x["high_price"]) for x in b]; l=[float(x["low_price"]) for x in b]; v=[float(x["candle_acc_trade_volume"]) for x in b]
 ma120=mean(c[i-119:i+1]); ma20=mean(c[i-19:i+1]); sd=statistics.pstdev(c[i-19:i+1]); gap=(c[i]/ma120-1)*100; vr=v[i]/max(mean(v[i-20:i]),1e-12)
 tr=[max(h[j]-l[j],abs(h[j]-c[j-1]),abs(l[j]-c[j-1])) for j in range(i-13,i+1)]; atr=mean(tr); prior=h[max(0,i-60):i]; resistance=min((x for x in prior if x>c[i]+.5*atr),default=c[i]+3*atr)
 return {"price":c[i],"ma120":ma120,"gapPct":gap,"touched":l[i]<=ma120<=h[i] or abs(gap)<=.8,"volumeRatio":vr,"bbWidthPct":4*sd/max(ma20,1e-12)*100,"rsi":rsi(c[:i+1]),"atr":atr,"resistance":resistance}
def shape(b,i):
 c=[float(x["trade_price"]) for x in b[i-23:i+1]]; base=c[0]; return [x/base-1 for x in c]
def similarity(a,b):
 rmse=(mean([(x-y)**2 for x,y in zip(a,b)]))**.5
 try:corr=statistics.correlation(a,b)
 except Exception:corr=0
 return max(0,min(100,50+50*corr-350*rmse)),corr,rmse
markets=[x for x in api("/market/all",{"isDetails":"false"}) if x["market"].startswith("KRW-")]; names={x["market"]:x["korean_name"] for x in markets}
caps=json.loads((ROOT/"monitor_data"/"coin_market_caps.json").read_text(encoding="utf-8")); capmap={x["symbol"]:x for x in caps.get("items",[])}; zcap=capmap.get("ZRO",{}).get("marketCapKrw")
zbars=completed("KRW-ZRO"); zidx=next((i for i,x in enumerate(zbars) if x["candle_date_time_kst"]=="2026-08-25T21:00:00"),len(zbars)-2); template=shape(zbars,zidx)
success=[]; failed=[]; current=[]; errors=[]
for row in markets:
 m=row["market"]; symbol=m.split('-',1)[1]
 try:
  b=zbars if m=="KRW-ZRO" else completed(m)
  if len(b)<150:raise ValueError("120시간선 분석 봉 부족")
  last=len(b)-1; f=features(b,last); sim,corr,rmse=similarity(shape(b,last),template); cap=capmap.get(symbol,{}).get("marketCapKrw"); ratio=cap/zcap if cap and zcap else None
  atr=f["atr"]; target_low=max(f["price"]+1.5*atr,min(f["resistance"],f["price"]+3*atr)); target_high=max(target_low,f["price"]+3*atr)
  base={"symbol":symbol,"name":names[m],"time":b[last]["candle_date_time_kst"],"price":f["price"],"ma120":round(f["ma120"],8),"ma120GapPct":round(f["gapPct"],2),"volumeRatio":round(f["volumeRatio"],2),"bbWidthPct":round(f["bbWidthPct"],2),"rsi":round(f["rsi"],1),"chartSimilarity":round(sim,1),"shapeCorrelation":round(corr,3),"marketCapKrw":cap,"marketCapRatioToZro":round(ratio,2) if ratio else None,"marketCapSimilar":bool(ratio and .5<=ratio<=2),"entryZoneLow":round(f["ma120"]-.25*atr,8),"entryZoneHigh":round(f["ma120"]+.5*atr,8),"invalidationPrice":round(f["ma120"]-1.25*atr,8),"targetLow":round(target_low,8),"targetHigh":round(target_high,8),"targetLowPct":round((target_low/f["price"]-1)*100,2),"targetHighPct":round((target_high/f["price"]-1)*100,2)}
  base["recommendedBuyPrice"]=round(base["entryZoneHigh"],8); base["sellPrice1"]=round(max(base["targetLow"],base["recommendedBuyPrice"]+atr),8); base["sellPrice2"]=round(max(base["targetHigh"],base["recommendedBuyPrice"]+2*atr),8); base["netProfitPct1"]=round((base["sellPrice1"]/base["recommendedBuyPrice"]-1)*100-.2,2); base["netProfitPct2"]=round((base["sellPrice2"]/base["recommendedBuyPrice"]-1)*100-.2,2); base["lossToInvalidationPct"]=round((base["invalidationPrice"]/base["recommendedBuyPrice"]-1)*100-.2,2)
  if f["touched"] or sim>=72 or base["marketCapSimilar"]:
   base["reasons"]=(['현재 120시간선 접촉'] if f["touched"] else [])+(["ZRO 급등 전 24시간 곡선 유사"] if sim>=72 else [])+(["ZRO 시총의 0.5~2배"] if base["marketCapSimilar"] else [])+(["거래량 평균 이하"] if f["volumeRatio"]<.8 else [])
   current.append(base)
  events=[]
  for i in range(120,last-6):
   ef=features(b,i)
   if ef["touched"] and (not events or i-events[-1]>=6):events.append(i)
  for i in events[-2:]:
   entry=float(b[i]["trade_price"]); future=b[i+1:i+7]; maxret=(max(float(x["high_price"]) for x in future)/entry-1)*100; close6=(float(future[-1]["trade_price"])/entry-1)*100; ef=features(b,i); es,ec,er=similarity(shape(b,i),template)
   item={"symbol":symbol,"name":names[m],"touchTime":b[i]["candle_date_time_kst"],"touchPrice":entry,"ma120":round(ef["ma120"],8),"gapPct":round(ef["gapPct"],2),"volumeRatio":round(ef["volumeRatio"],2),"rsi":round(ef["rsi"],1),"maxReturn6hPct":round(maxret,2),"closeReturn6hPct":round(close6,2),"chartSimilarity":round(es,1),"marketCapRatioToZro":round(ratio,2) if ratio else None,"won":bool(maxret>=3 and close6>0)}
   (success if maxret>=3 and close6>0 else failed).append(item)
 except Exception as e:errors.append({"market":m,"error":str(e)[:140]})
 time.sleep(.115)
history=success+failed
base_win=mean([1 if e["won"] else 0 for e in history])
for x in current:
 matched=[e for e in history if abs(e["rsi"]-x["rsi"])<=12 and abs(e["gapPct"]-x["ma120GapPct"])<=1.5 and abs(e["chartSimilarity"]-x["chartSimilarity"])<=20 and abs(math.log(max(e["volumeRatio"],.05)/max(x["volumeRatio"],.05)))<=1.25]
 if len(matched)<8:matched=[e for e in history if abs(e["rsi"]-x["rsi"])<=15 and abs(e["gapPct"]-x["ma120GapPct"])<=2]
 wins=sum(e["won"] for e in matched); raw=wins/len(matched) if matched else base_win; adjusted=(wins+20*base_win)/(len(matched)+20); x["analogSamples"]=len(matched); x["rawWinRatePct"]=round(raw*100,1); x["historicalWinRatePct"]=round(adjusted*100,1); x["historicalAvgClose6hPct"]=round(mean([e["closeReturn6hPct"] for e in matched]),2) if matched else 0; x["confidence"]="높음" if len(matched)>=30 else "보통" if len(matched)>=15 else "낮음"
 x["priorityScore"]=round(x["historicalWinRatePct"]*.55+x["chartSimilarity"]*.2+max(0,15-abs(x["ma120GapPct"])*8)+(7 if x["volumeRatio"]<.8 else 0)+(3 if x["marketCapSimilar"] else 0),1)
 x["reading"]="120선 구간 분할 관찰" if abs(x["ma120GapPct"])<=.8 and x["volumeRatio"]<.8 else "거래량·직전 고점 돌파 대기"
current.sort(key=lambda x:(x["priorityScore"],x["historicalWinRatePct"],x["chartSimilarity"]),reverse=True); success.sort(key=lambda x:x["touchTime"],reverse=True); failed.sort(key=lambda x:x["touchTime"],reverse=True)
payload={"updatedAt":datetime.now(KST).isoformat(timespec="seconds"),"source":"Upbit completed 1h candles + CoinGecko market-cap snapshot","definition":{"touch":"봉의 저가≤MA120≤고가 또는 종가 이격도 ±0.8%","success":"터치 후 6시간 내 고가 +3% 이상이며 6시간 종가 수익 양수","chartSimilarity":"ZRO 2026-08-25 21시까지 24시간 정규화 종가곡선의 상관·RMSE 결합","marketCapSimilar":"ZRO 시총의 0.5~2배"},"zroTemplate":{"time":"2026-08-25T21:00:00","marketCapKrw":zcap},"listed":len(markets),"analyzed":len(markets)-len(errors),"currentCandidates":current[:60],"successfulTouches":success[:60],"failedTouches":failed[:60],"errors":errors,"actualOrders":0}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n"); print(json.dumps({"status":"UPDATED","analyzed":payload["analyzed"],"current":len(current),"success":len(success),"failed":len(failed),"errors":len(errors)},ensure_ascii=False))

