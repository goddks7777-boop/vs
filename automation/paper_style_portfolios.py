"""세 가지 패턴을 선별하고 단타·스윙·장타 독립 모의계좌를 운용한다."""
import json, math, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"monitor_data"/"paper_style_portfolios.json"
KST=ZoneInfo("Asia/Seoul"); NOW=datetime.now(KST); FEE=.0005; SLIP=.0005; INITIAL=10_000_000
STABLE={"USDT","USDC","USDE","USD1","USDG","USDS"}
CFG={
 "scalp":{"label":"단타","budget":1_500_000,"max":3,"maxHours":24,"stopAtr":1.2,"targetAtr":2.0},
 "swing":{"label":"스윙","budget":2_000_000,"max":3,"maxHours":240,"stopAtr":1.6,"targetAtr":3.0},
 "long":{"label":"장타","budget":2_000_000,"max":3,"maxHours":2160,"stopAtr":2.2,"targetAtr":5.0},
}
def api(path,params=None):
 q="?"+urllib.parse.urlencode(params or {}) if params else ""; req=urllib.request.Request("https://api.upbit.com/v1"+path+q,headers={"User-Agent":"style-paper-research/1.0"})
 for attempt in range(5):
  try:
   with urllib.request.urlopen(req,timeout=25) as r:
    value=json.load(r)
   time.sleep(.13)
   return value
  except urllib.error.HTTPError as e:
   if e.code!=429 or attempt==4:raise
   time.sleep(.7*(attempt+1))
def candles(m,u,n=140):
 rows=api(f"/candles/minutes/{u}",{"market":m,"count":n}); done=[]
 for x in rows:
  start=datetime.fromisoformat(x["candle_date_time_kst"]+"+09:00")
  if start+timedelta(minutes=u)<=NOW:done.append(x)
 return list(reversed(done))
def avg(a):return sum(a)/len(a) if a else 0
def feat(b):
 c=[float(x["trade_price"]) for x in b];h=[float(x["high_price"]) for x in b];l=[float(x["low_price"]) for x in b];v=[float(x["candle_acc_trade_volume"]) for x in b]
 if len(c)<125:raise ValueError("완성봉 125개 미만")
 ob=[0.]
 for i in range(1,len(c)):ob.append(ob[-1]+(v[i] if c[i]>c[i-1] else -v[i] if c[i]<c[i-1] else 0))
 def cmf(end):
  mf=[(((c[i]-l[i])-(h[i]-c[i]))/max(h[i]-l[i],1e-12))*v[i] for i in range(end-20,end)]
  return sum(mf)/max(sum(v[end-20:end]),1e-12)
 tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]
 ma20=avg(c[-20:]);ma60=avg(c[-60:]);ma120=avg(c[-120:]); atr=avg(tr[-14:])/c[-1]*100
 return {"price":c[-1],"time":b[-1]["candle_date_time_kst"],"ma20":ma20,"ma60":ma60,"ma120":ma120,"ma120GapPct":(c[-1]/ma120-1)*100,"ma20SlopePct":(ma20/avg(c[-25:-5])-1)*100,"volumeRatio":v[-1]/max(avg(v[-21:-1]),1e-12),"volumeDry":avg(v[-6:-1])/max(avg(v[-26:-6]),1e-12),"breakout20":c[-1]>max(h[-21:-1]),"breakout10":c[-1]>max(h[-11:-1]),"touch120":min(l[-4:])<=ma120*1.008 and max(c[-4:])>=ma120,"boxPct":(max(h[-21:-1])/min(l[-21:-1])-1)*100,"cmf":cmf(len(c)),"cmfPrev":cmf(len(c)-5),"obvSlope":(ob[-1]-ob[-11])/max(sum(v[-10:]),1e-12),"obvPrev":(ob[-6]-ob[-16])/max(sum(v[-15:-5]),1e-12),"atrPct":atr}
def evidence(kind,f4,f1):
 if kind=="추세 돌파형":
  checks={"4시간 상승추세":f4["price"]>f4["ma20"]>f4["ma60"] and f4["ma20SlopePct"]>0,"1시간 고점 돌파":f1["breakout20"],"1시간 거래량 1.5배":f1["volumeRatio"]>=1.5,"OBV 상승":f1["obvSlope"]>0}
 elif kind=="MA120 반등형":
  checks={"1시간 MA120 지지":f1["touch120"] and f1["price"]>f1["ma120"],"거래량 수축 후 회복":f1["volumeDry"]<.9 and f1["volumeRatio"]>=1.15,"최근 10봉 고점 돌파":f1["breakout10"],"4시간 추세 훼손 없음":f4["price"]>f4["ma60"]}
 elif kind in ("매집 전환형","매집 기본형"):
  checks={"4시간 박스권 12% 이내":f4["boxPct"]<=12,"CMF 개선":f4["cmf"]>0 and f4["cmf"]>f4["cmfPrev"]+.02,"OBV 개선":f4["obvSlope"]>0 and f4["obvSlope"]>f4["obvPrev"],"1시간 박스 돌파+거래량":f1["breakout20"] and f1["volumeRatio"]>=1.3}
 elif kind=="매집 개선형":
  checks={"4시간 박스권 12% 이내":f4["boxPct"]<=12,"CMF 5봉 개선":f4["cmf"]>f4["cmfPrev"]+.02,"OBV 기울기 개선":f4["obvSlope"]>f4["obvPrev"] and f4["obvSlope"]>0,"1시간 거래량 회복":f1["volumeRatio"]>=1.2}
 else:
  checks={"4시간 박스권 8% 이내":f4["boxPct"]<=8,"거래량 수축":f4["volumeDry"]<.9,"CMF 0.03 이상":f4["cmf"]>.03,"OBV 상승":f4["obvSlope"]>0}
 score=sum(checks.values()); state="확인" if score==4 else "준비" if score==3 else "관찰"
 return checks,score,state
def empty():return {"initial":INITIAL,"cash":INITIAL,"positions":{},"trades":[],"curve":[],"journal":[]}
def stats(p,value):
 closed=[x for x in p["trades"] if x["side"]=="SELL"]; wins=[x for x in closed if x["pnl"]>0]; losses=[x for x in closed if x["pnl"]<0]
 gp=sum(x["pnl"] for x in wins);gl=abs(sum(x["pnl"] for x in losses)); peak=INITIAL;dd=0
 for x in p["curve"]:peak=max(peak,x["value"]);dd=max(dd,(peak-x["value"])/peak*100)
 return {"value":round(value),"returnPct":round((value/INITIAL-1)*100,3),"closedTrades":len(closed),"wins":len(wins),"winRate":round(len(wins)/len(closed)*100,2) if closed else None,"expectancyPct":round(avg([x["returnPct"] for x in closed]),3) if closed else None,"profitFactor":round(gp/gl,3) if gl else None,"maxDrawdownPct":round(dd,3)}
latest=json.loads((ROOT/"monitor_data"/"latest.json").read_text(encoding="utf-8")); names={x["symbol"]:x["name"] for x in latest["items"]}; liquid=sorted([x for x in latest["items"] if x["symbol"] not in STABLE],key=lambda x:x.get("value24",0),reverse=True)[:60]
learn_path=ROOT/"monitor_data"/"strategy_walkforward.json";learning=json.loads(learn_path.read_text(encoding="utf-8")) if learn_path.exists() else {"rankings":{}}
candidates=[];errors=[]; prices={x["symbol"]:x["price"] for x in latest["items"]}
for x in liquid:
 try:
  f4=feat(candles("KRW-"+x["symbol"],240));f1=feat(candles("KRW-"+x["symbol"],60))
  for kind in ("추세 돌파형","MA120 반등형","매집 기본형","매집 개선형","매집 압축형"):
   ch,sc,st=evidence(kind,f4,f1); candidates.append({"symbol":x["symbol"],"name":x["name"],"strategy":kind,"state":st,"score":sc,"price":f1["price"],"signalTime":f1["time"],"evidence":[k for k,v in ch.items() if v],"missing":[k for k,v in ch.items() if not v],"cmf":round(f4["cmf"],4),"cmfChange":round(f4["cmf"]-f4["cmfPrev"],4),"obvSlope":round(f4["obvSlope"],4),"volumeRatio1h":round(f1["volumeRatio"],2),"ma120GapPct":round(f1["ma120GapPct"],2),"atrPct":round(f1["atrPct"],2)})
 except Exception as e:errors.append({"symbol":x["symbol"],"error":str(e)[:120]})
candidates.sort(key=lambda x:(x["state"]=="확인",x["score"],next((z.get("value24",0) for z in liquid if z["symbol"]==x["symbol"]),0)),reverse=True)
try:state=json.loads(OUT.read_text(encoding="utf-8"))
except Exception:state={"startedAt":NOW.isoformat(timespec="seconds"),"portfolios":{}}
for key,cfg in CFG.items():
 p=state["portfolios"].setdefault(key,empty()); actions=[]
 learned=learning.get("rankings",{}).get(key,{});champion=learned.get("champion");challengers=learned.get("challengers",[]);approved=[x for x in [champion,*challengers] if x]
 for s in list(p["positions"]):
  if s not in prices:continue
  pos=p["positions"][s];ret=(prices[s]/pos["entry"]-1)*100;hours=(NOW-datetime.fromisoformat(pos["time"])).total_seconds()/3600;reason=None
  if ret<=-pos["stopPct"]:reason=f"ATR 손절 -{pos['stopPct']:.2f}%"
  elif ret>=pos["targetPct"]:reason=f"ATR·저항 예상 목표 +{pos['targetPct']:.2f}%"
  elif hours>=cfg["maxHours"]:reason=f"최대 보유 {cfg['maxHours']}시간 종료"
  if reason:
   fill=prices[s]*(1-SLIP);gross=pos["qty"]*fill;fee=gross*FEE;pnl=gross-fee-pos["cost"];p["cash"]+=gross-fee
   p["trades"].append({"time":NOW.isoformat(timespec="seconds"),"side":"SELL","symbol":s,"name":pos["name"],"entryPrice":pos["entry"],"price":fill,"amount":gross,"fee":fee,"pnl":pnl,"returnPct":pnl/pos["cost"]*100,"reason":reason});del p["positions"][s];actions.append(f"SELL {s} {reason}")
 ready=[x for x in candidates if x["strategy"] in approved and x["state"]=="확인" and x["symbol"] not in p["positions"]]
 for x in ready[:max(0,cfg["max"]-len(p["positions"]))]:
  if p["cash"]<cfg["budget"] or any(t.get("signalTime")==x["signalTime"] and t.get("symbol")==x["symbol"] and t["side"]=="BUY" for t in p["trades"]):continue
  budget=cfg["budget"];fill=prices[x["symbol"]]*(1+SLIP);fee=budget*FEE;qty=(budget-fee)/fill;stop=max(2,cfg["stopAtr"]*x["atrPct"]);target=max(stop*1.5,cfg["targetAtr"]*x["atrPct"])
  p["cash"]-=budget;p["positions"][x["symbol"]]={"name":x["name"],"entry":fill,"qty":qty,"cost":budget,"time":NOW.isoformat(timespec="seconds"),"setup":x["strategy"],"stopPct":stop,"targetPct":target,"signalTime":x["signalTime"]}
  reason=f"{x['strategy']} 4/4 확인 · {', '.join(x['evidence'])}";p["trades"].append({"time":NOW.isoformat(timespec="seconds"),"signalTime":x["signalTime"],"side":"BUY","symbol":x["symbol"],"name":x["name"],"price":fill,"amount":budget-fee,"fee":fee,"pnl":None,"returnPct":None,"targetPct":target,"stopPct":stop,"reason":reason});actions.append(f"BUY {x['symbol']} {reason}")
 value=p["cash"]+sum(z["qty"]*prices.get(s,z["entry"])*(1-FEE-SLIP) for s,z in p["positions"].items());p["curve"].append({"time":NOW.isoformat(timespec="seconds"),"value":value});p["curve"]=p["curve"][-2000:];p["journal"].append({"time":NOW.isoformat(timespec="seconds"),"actions":actions or (["검증 통과 Champion 없음 · 신규 매수 보류"] if not champion else ["새 가상체결 없음"])});p["journal"]=p["journal"][-500:];p["stats"]=stats(p,value);p["selection"]={"champion":champion,"challengers":challengers,"approvedStrategies":approved,"reviewCycle":"매일 재학습·주 1회 Champion 교체"}
state.update({"updatedAt":NOW.isoformat(timespec="seconds"),"mode":"PAPER_ONLY","actualOrders":0,"universe":{"listed":latest["count"],"requested":len(liquid),"analyzed":len({x["symbol"] for x in candidates}),"rule":"24시간 거래대금 상위 60종목"},"definitions":{"CMF 개선":"4시간 CMF가 0보다 크고 5봉 전보다 0.02 이상 상승","OBV 개선":"4시간 OBV 10봉 기울기가 양수이며 직전 기울기보다 상승"},"candidates":candidates,"errors":errors})
OUT.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n");print(json.dumps({"status":"UPDATED","analyzed":len(liquid),"candidates":len(candidates),"confirmed":sum(x["state"]=="확인" for x in candidates),"errors":len(errors),"portfolios":{k:v["stats"] for k,v in state["portfolios"].items()},"actualOrders":0},ensure_ascii=False))
