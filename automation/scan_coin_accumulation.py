"""업비트 KRW 전체 4시간봉 매집 가능성 + 1시간봉 돌파 스캐너."""
import json,math,time,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"monitor_data"/"coin_accumulation.json";KST=timezone(timedelta(hours=9))
def api(path,params=None):
 q="?"+urllib.parse.urlencode(params or {}) if params else "";r=urllib.request.Request("https://api.upbit.com/v1"+path+q,headers={"User-Agent":"accumulation-research/1.0"})
 with urllib.request.urlopen(r,timeout=25) as x:return json.load(x)
def candles(market,unit,count=140):
 rows=api(f"/candles/minutes/{unit}",{"market":market,"count":count});now=datetime.now(KST);done=[]
 for x in rows:
  start=datetime.fromisoformat(x["candle_date_time_kst"]+"+09:00")
  if start+timedelta(minutes=unit)<=now:done.append(x)
 return list(reversed(done))
def mean(x):return sum(x)/len(x) if x else 0
def snapshot(b,i=None):
 i=len(b)-1 if i is None else i;c=[float(x["trade_price"]) for x in b[:i+1]];h=[float(x["high_price"]) for x in b[:i+1]];l=[float(x["low_price"]) for x in b[:i+1]];v=[float(x["candle_acc_trade_volume"]) for x in b[:i+1]]
 if len(c)<65:raise ValueError("봉 부족")
 obv=[0.]
 for j in range(1,len(c)):obv.append(obv[-1]+(1 if c[j]>c[j-1] else -1 if c[j]<c[j-1] else 0)*v[j])
 mf=[]
 for j in range(len(c)-20,len(c)):
  mult=((c[j]-l[j])-(h[j]-c[j]))/max(h[j]-l[j],1e-12);mf.append(mult*v[j])
 cmf=sum(mf)/max(sum(v[-20:]),1e-12);ma20=mean(c[-20:]);sd=(mean([(x-ma20)**2 for x in c[-20:]]))**.5;width=4*sd/max(ma20,1e-12)*100;widths=[]
 for end in range(max(20,len(c)-60),len(c)+1):
  m=mean(c[end-20:end]);s=mean([(x-m)**2 for x in c[end-20:end]])**.5;widths.append(4*s/max(m,1e-12)*100)
 widthPct=sum(x<=width for x in widths)/len(widths)*100;mom20=(c[-1]/c[-21]-1)*100;mom6=(c[-1]/c[-7]-1)*100;volRatio=v[-1]/max(mean(v[-21:-1]),1e-12);volDry=mean(v[-5:])/max(mean(v[-20:]),1e-12);rangeLow=min(l[-20:]);rangeHigh=max(h[-20:]);rangePos=(c[-1]-rangeLow)/max(rangeHigh-rangeLow,1e-12)*100;obvSlope=(obv[-1]-obv[-11])/max(sum(v[-10:]),1e-12);breakout=c[-1]>max(h[-21:-1]);checks={"가격 20봉 박스권":abs(mom20)<=8,"OBV 10봉 상승":obvSlope>0,"CMF 20 양수":cmf>0.03,"볼린저 폭 하위 40%":widthPct<=40,"최근 거래량 수축":volDry<.9,"고점 추격 전":rangePos<75};score=sum(checks.values())
 return {"date":b[i]["candle_date_time_kst"],"price":c[-1],"score":score,"checks":checks,"cmf":cmf,"obvSlope":obvSlope,"bbWidthPct":widthPct,"volumeRatio":volRatio,"volumeDryRatio":volDry,"momentum20":mom20,"momentum6":mom6,"rangePosition":rangePos,"breakout":breakout}
markets=api("/market/all",{"isDetails":"false"});krw=[x for x in markets if x["market"].startswith("KRW-")];names={x["market"]:x["korean_name"] for x in krw};items=[];errors=[]
for n,x in enumerate(krw,1):
 m=x["market"]
 try:
  b4=candles(m,240);b1=candles(m,60);cur4=snapshot(b4);prior4=snapshot(b4,len(b4)-7);cur1=snapshot(b1);priorScore=prior4["score"];trigger=cur1["breakout"] and cur1["volumeRatio"]>=1.5
  if priorScore>=4 and trigger and cur1["momentum6"]<=12:phase="돌파 확인"
  elif priorScore>=4 and cur1["momentum6"]>2 and cur1["cmf"]>0:phase="매집 후 상승 전환"
  elif cur4["score"]>=4:phase="매집 후보"
  elif cur1["momentum6"]>12 or (cur1["breakout"] and cur1["volumeRatio"]>=2.5):phase="급등·추격 주의"
  else:phase="일반 관찰"
  evidence=[k for k,v in prior4["checks"].items() if v]+(["1시간 거래량 돌파"] if trigger else [])
  items.append({"market":m,"symbol":m.split('-',1)[1],"name":names[m],"phase":phase,"accumulationScore":priorScore,"current4hScore":cur4["score"],"breakout1h":trigger,"price":cur1["price"],"cmf4h":round(prior4["cmf"],4),"obvSlope4h":round(prior4["obvSlope"],4),"bbWidthPercentile4h":round(prior4["bbWidthPct"],1),"volumeDry4h":round(prior4["volumeDryRatio"],2),"volumeRatio1h":round(cur1["volumeRatio"],2),"momentum6h":round(cur1["momentum6"],2),"evidence":evidence,"signalTime":cur1["date"]})
 except Exception as e:errors.append({"market":m,"error":str(e)[:140]})
 time.sleep(.115)
priority={"돌파 확인":4,"매집 후 상승 전환":3,"매집 후보":2,"급등·추격 주의":1,"일반 관찰":0};items.sort(key=lambda x:(priority[x["phase"]],x["accumulationScore"],x["volumeRatio1h"]),reverse=True)
payload={"updatedAt":datetime.now(KST).isoformat(timespec="seconds"),"source":"Upbit completed 4h and 1h candles","definition":"가격 박스권·OBV·CMF·볼린저 폭·거래량 수축의 공개 OHLCV 기반 매집 가능성. 실제 주체의 매수를 확정하지 않음.","listed":len(krw),"analyzed":len(items),"items":items,"errors":errors,"actualOrders":0}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n");print(json.dumps({"status":"UPDATED","listed":len(krw),"analyzed":len(items),"signals":{p:sum(x["phase"]==p for x in items) for p in priority},"errors":len(errors)},ensure_ascii=False))

