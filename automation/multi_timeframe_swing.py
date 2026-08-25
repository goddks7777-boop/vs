"""업비트 KRW 전 종목 4h·1h·30m 스윙 연구. 실제 주문은 수행하지 않는다."""
import argparse,json,math,time,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"monitor_data"/"multi_timeframe_swing.json";KST=timezone(timedelta(hours=9));TARGET,STOP,HORIZON,COST=6.,4.,42,.2
def api(path,params=None):
 q="?"+urllib.parse.urlencode(params or {}) if params else "";r=urllib.request.Request("https://api.upbit.com/v1"+path+q,headers={"User-Agent":"mtf-swing-research/1.0"})
 with urllib.request.urlopen(r,timeout=25) as x:return json.load(x)
def fetch(market,unit,count):
 rows=[];to=None
 while len(rows)<count:
  p={"market":market,"count":min(200,count-len(rows))}
  if to:p["to"]=to
  b=api(f"/candles/minutes/{unit}",p)
  if not b:break
  rows+=b;old=datetime.fromisoformat(b[-1]["candle_date_time_utc"]+"+00:00");to=(old-timedelta(seconds=1)).isoformat().replace("+00:00","Z");time.sleep(.11)
 now=datetime.now(KST);done=[]
 for x in rows:
  start=datetime.fromisoformat(x["candle_date_time_kst"]+"+09:00")
  if start+timedelta(minutes=unit)<=now:done.append(x)
 return sorted({x["candle_date_time_kst"]:x for x in done}.values(),key=lambda x:x["candle_date_time_kst"])
def mean(x):return sum(x)/len(x) if x else 0
def rsi(c,p=14):
 d=[c[i]-c[i-1] for i in range(len(c)-p,len(c))];g=mean([max(v,0) for v in d]);l=mean([max(-v,0) for v in d]);return 100 if l==0 else 100-100/(1+g/l)
def features(b,i=None):
 i=len(b)-1 if i is None else i;c=[float(x["trade_price"]) for x in b];h=[float(x["high_price"]) for x in b];l=[float(x["low_price"]) for x in b];v=[float(x["candle_acc_trade_volume"]) for x in b];pc=c[i-60:i+1];ph=h[i-60:i+1];pl=l[i-60:i+1];pv=v[i-60:i+1];obv=[0.];plus=[];minus=[];trs=[]
 for j in range(1,len(pc)):
  obv.append(obv[-1]+(1 if pc[j]>pc[j-1] else -1 if pc[j]<pc[j-1] else 0)*pv[j]);up=ph[j]-ph[j-1];dn=pl[j-1]-pl[j];plus.append(up if up>dn and up>0 else 0);minus.append(dn if dn>up and dn>0 else 0);trs.append(max(ph[j]-pl[j],abs(ph[j]-pc[j-1]),abs(pl[j]-pc[j-1])))
 tr=max(mean(trs[-14:]),1e-12);pdi=100*mean(plus[-14:])/tr;mdi=100*mean(minus[-14:])/tr;dx=[]
 for k in range(14,len(trs)+1):
  t=max(mean(trs[k-14:k]),1e-12);aa=100*mean(plus[k-14:k])/t;zz=100*mean(minus[k-14:k])/t;dx.append(100*abs(aa-zz)/max(aa+zz,1e-12))
 return {"rsi":rsi(pc),"obvSlope":(obv[-1]-obv[-11])/max(sum(pv[-10:]),1e-12),"adx":mean(dx[-14:]),"plusDI":pdi,"minusDI":mdi,"maGap":(mean(pc[-20:])/mean(pc[-60:])-1)*100,"volumeRatio":pv[-1]/max(mean(pv[-20:]),1e-12),"breakout":pc[-1]>=max(pc[-20:]),"momentum":(pc[-1]/pc[-13]-1)*100,"atrPct":tr/pc[-1]*100,"price":pc[-1],"date":b[i]["candle_date_time_kst"]}
RULES={"RSI 45~65":lambda f:45<=f["rsi"]<=65,"OBV 10봉 상승":lambda f:f["obvSlope"]>0,"ADX 20 이상·+DI 우위":lambda f:f["adx"]>=20 and f["plusDI"]>f["minusDI"],"20선 > 60선":lambda f:f["maGap"]>0,"거래량 20봉 평균 1.2배":lambda f:f["volumeRatio"]>=1.2,"20봉 신고가":lambda f:f["breakout"],"12봉 모멘텀 0~15%":lambda f:0<f["momentum"]<=15,"과매도 RSI≤35 + OBV 상승":lambda f:f["rsi"]<=35 and f["obvSlope"]>0,"조정 RSI 35~50 + OBV 상승":lambda f:35<=f["rsi"]<50 and f["obvSlope"]>0,"추세 20>60 + ADX·+DI":lambda f:f["maGap"]>0 and f["adx"]>=20 and f["plusDI"]>f["minusDI"],"추세 20>60 + RSI 45~60":lambda f:f["maGap"]>0 and 45<=f["rsi"]<=60,"추세+OBV+과열 제한":lambda f:f["maGap"]>0 and f["obvSlope"]>0 and 45<=f["rsi"]<=65 and f["momentum"]<=15}
def make_rows(symbol,b):
 out=[]
 for i in range(60,len(b)-HORIZON):
  f=features(b,i);entry=f["price"];ret=None
  for x in b[i+1:i+HORIZON+1]:
   if float(x["low_price"])<=entry*(1-STOP/100):ret=-STOP-COST;break
   if float(x["high_price"])>=entry*(1+TARGET/100):ret=TARGET-COST;break
  if ret is None:ret=(float(b[i+HORIZON]["trade_price"])/entry-1)*100-COST
  out.append({"symbol":symbol,"date":f["date"],"ret":ret,"rules":{n:fn(f) for n,fn in RULES.items()}})
 return out
def metric(rs,rule=None,rules=None):
 x=rs
 if rule:x=[r for r in x if r["rules"][rule]]
 if rules:x=[r for r in x if sum(r["rules"][n] for n in rules)>=max(1,math.ceil(len(rules)*.6))]
 v=[r["ret"] for r in x];w=[z for z in v if z>0];loss=[z for z in v if z<=0]
 return {"trades":len(v),"winRate":len(w)/len(v)*100 if v else 0,"expectancyPct":mean(v),"profitFactor":sum(w)/abs(sum(loss)) if loss and sum(loss) else (99 if w else 0),"avgWinPct":mean(w),"avgLossPct":mean(loss)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--training-markets",type=int,default=50);p.add_argument("--bars",type=int,default=800);a=p.parse_args();markets=api("/market/all",{"isDetails":"false"});krw=[x for x in markets if x["market"].startswith("KRW-")];names={x["market"]:x["korean_name"] for x in krw};tick=[]
 for i in range(0,len(krw),100):tick+=api("/ticker",{"markets":",".join(x["market"] for x in krw[i:i+100])});time.sleep(.11)
 liquid=sorted(tick,key=lambda x:float(x.get("acc_trade_price_24h",0)),reverse=True);training=[x["market"] for x in liquid[:a.training_markets]];history=[];errors=[];latest4={}
 for m in training:
  try:b=fetch(m,240,a.bars);history+=make_rows(m,b);latest4[m]=features(b)
  except Exception as e:errors.append({"market":m,"timeframe":"4h","error":str(e)[:150]})
 dates=sorted({r["date"] for r in history});cut=dates[int(len(dates)*.7)];train=[r for r in history if r["date"]<cut];test=[r for r in history if r["date"]>=cut];base_train=metric(train);base_test=metric(test);studies=[];selected=[]
 for n in RULES:
  tr=metric(train,rule=n);te=metric(test,rule=n);improved=tr["trades"]>=50 and te["trades"]>=30 and tr["expectancyPct"]>base_train["expectancyPct"] and te["expectancyPct"]>base_test["expectancyPct"] and te["profitFactor"]>1;studies.append({"indicator":n,"training":tr,"test":te,"expectancyLiftPct":te["expectancyPct"]-base_test["expectancyPct"],"winRateLiftPp":te["winRate"]-base_test["winRate"],"improved":improved})
  if improved:selected.append(n)
 selected.sort(key=lambda n:next(x["expectancyLiftPct"] for x in studies if x["indicator"]==n),reverse=True);basket=metric(test,rules=selected) if selected else base_test;approved=bool(selected) and basket["trades"]>=30 and basket["expectancyPct"]>0 and basket["profitFactor"]>=1.2;ranking=[]
 for t in liquid:
  m=t["market"]
  try:
   f4=latest4.get(m) or features(fetch(m,240,80));f1=features(fetch(m,60,80));f30=features(fetch(m,30,80));frames={"4시간봉":f4,"1시간봉":f1,"30분봉":f30};used=[];score=0
   for n in selected:
    passed=[RULES[n](f) for f in (f4,f1,f30)];score+=sum(passed);used.append({"indicator":n,"fourHour":passed[0],"oneHour":passed[1],"thirtyMinute":passed[2],"passedFrames":sum(passed)})
   required=max(1,math.ceil(len(selected)*3*.55));signal=approved and score>=required and f4["maGap"]>0;ranking.append({"market":m,"symbol":m.split("-",1)[1],"name":names.get(m,m),"price":float(t["trade_price"]),"value24":float(t.get("acc_trade_price_24h",0)),"score":score,"maxScore":len(selected)*3,"signal":signal,"usedIndicators":used,"frames":{k:{x:round(y,4) if isinstance(y,float) else y for x,y in f.items()} for k,f in frames.items()},"reason":f"개선 지표 {len(selected)}개 · 시간대 합산 {score}/{len(selected)*3} 통과"})
  except Exception as e:errors.append({"market":m,"timeframe":"live","error":str(e)[:150]})
 ranking.sort(key=lambda x:(x["signal"],x["score"],x["value24"]),reverse=True);data={"updatedAt":datetime.now(KST).isoformat(timespec="seconds"),"mode":"RESEARCH_ONLY","actualOrders":0,"approved":approved,"universe":{"market":"UPBIT_KRW_ALL","listed":len(krw),"analyzed":len(ranking),"trainingMarkets":len(training)},"design":{"timeframes":["4시간봉","1시간봉","30분봉"],"roles":{"4시간봉":"스윙 방향","1시간봉":"진입 확인","30분봉":"세부 타이밍"},"targetPct":TARGET,"stopPct":STOP,"holding4hBars":HORIZON,"costPct":COST},"baseline":{"training":base_train,"test":base_test},"indicatorStudies":sorted(studies,key=lambda x:x["expectancyLiftPct"],reverse=True),"selectedIndicators":selected,"selectedBasketTest":basket,"recommendations":ranking[:50],"errors":errors}
 OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n");print(json.dumps({"status":"UPDATED","listed":len(krw),"analyzed":len(ranking),"selected":selected,"approved":approved,"test":basket,"errors":len(errors)},ensure_ascii=False))
if __name__=="__main__":main()
