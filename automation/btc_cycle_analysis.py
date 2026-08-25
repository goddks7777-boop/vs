"""업비트 BTC/KRW 전체 일봉으로 장기 사이클과 국면별 지표 성과를 분석한다."""
import json, statistics, urllib.parse, urllib.request, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"monitor_data"/"btc_cycle_analysis.json"; KST=timezone(timedelta(hours=9))
def api(params):
    u="https://api.upbit.com/v1/candles/days?"+urllib.parse.urlencode(params);q=urllib.request.Request(u,headers={"User-Agent":"btc-cycle-research/1.0"})
    with urllib.request.urlopen(q,timeout=25) as r:return json.load(r)
def fetch():
    rows=[];to=None
    while True:
        p={"market":"KRW-BTC","count":200}
        if to:p["to"]=to
        b=api(p)
        if not b:break
        rows+=b;old=datetime.fromisoformat(b[-1]["candle_date_time_utc"]+"+00:00");to=(old-timedelta(seconds=1)).isoformat().replace("+00:00","Z")
        if len(b)<200:break
        time.sleep(.12)
    now=datetime.now(KST);u={}
    for x in rows:
        start=datetime.fromisoformat(x["candle_date_time_kst"]+"+09:00")
        if start+timedelta(days=1)<=now:u[start.date().isoformat()]=x
    return [u[k] for k in sorted(u)]
def mean(x):return sum(x)/len(x) if x else 0
def rsi(c,i,p=14):
    d=[c[j]-c[j-1] for j in range(i-p+1,i+1)];g=mean([max(x,0) for x in d]);l=mean([max(-x,0) for x in d]);return 100 if l==0 else 100-100/(1+g/l)
bars=fetch(); dates=[x["candle_date_time_kst"][:10] for x in bars]; close=[float(x["trade_price"]) for x in bars];vol=[float(x["candle_acc_trade_volume"]) for x in bars]
obv=[0.0]
for i in range(1,len(close)):obv.append(obv[-1]+(1 if close[i]>close[i-1] else -1 if close[i]<close[i-1] else 0)*vol[i])
rows=[]; regimes=[]
for i in range(200,len(close)-30):
    ma200=mean(close[i-199:i+1]);prev=mean(close[i-219:i-19]) if i>=219 else ma200
    regime="상승" if close[i]>ma200 and ma200>prev else "하락" if close[i]<ma200 and ma200<prev else "전환"
    high730=max(close[max(0,i-729):i+1]);low730=min(close[max(0,i-729):i+1]);position=(close[i]-low730)/(high730-low730)*100 if high730>low730 else 50
    rv=rsi(close,i);vr=vol[i]/max(mean(vol[i-19:i+1]),1e-12);fwd=(close[i+30]/close[i]-1)*100
    sig={"RSI 35 이하":rv<=35,"RSI 50~65":50<=rv<=65,"OBV 20일 상승":obv[i]>obv[i-20],"가격 200일선 위":close[i]>ma200,"50일선 > 200일선":mean(close[i-49:i+1])>ma200,"거래량 1.5배":vr>=1.5,"730일 고점 대비 -30%":close[i]/high730-1<=-.30,"60일 신고가":close[i]>=max(close[i-59:i+1])}
    rows.append({"date":dates[i],"price":close[i],"regime":regime,"forward30":fwd,"signals":sig,"rsi":rv,"ma200GapPct":(close[i]/ma200-1)*100,"ma200SlopePct":(ma200/prev-1)*100,"drawdownPct":(close[i]/high730-1)*100,"cyclePosition":position})
def stats(sample,signal=None):
    x=[r for r in sample if signal is None or r["signals"][signal]];v=[r["forward30"] for r in x]
    return {"count":len(v),"avgForward30Pct":mean(v),"hitRate":sum(z>0 for z in v)/len(v)*100 if v else 0,"medianForward30Pct":statistics.median(v) if v else 0}
signals=list(rows[0]["signals"]);analysis={}
for regime in ("상승","하락","전환","전체"):
    sample=rows if regime=="전체" else [r for r in rows if r["regime"]==regime];base=stats(sample);items=[]
    for signal in signals:
        m=stats(sample,signal);m.update({"indicator":signal,"edgePct":m["avgForward30Pct"]-base["avgForward30Pct"],"hitEdgePp":m["hitRate"]-base["hitRate"]})
        m["meaningful"]=m["count"]>=20 and abs(m["edgePct"])>=3 and abs(m["hitEdgePp"])>=5;items.append(m)
    items.sort(key=lambda x:(x["meaningful"],x["edgePct"]),reverse=True);analysis[regime]={"baseline":base,"indicators":items}
# 약 2.5년 고정 창 안에서 사후적으로 가장 큰 상승·하락 다리를 따로 찾는다.
# 전환점은 보고서 표시용이며 미래를 미리 알아야 하므로 AI 입력에는 넣지 않는다.
def strongest_leg(points, direction):
    anchor=points[0];best=None
    for point in points[1:]:
        change=(point["price"]/anchor["price"]-1)*100
        if best is None or (direction=="up" and change>best["changePct"]) or (direction=="down" and change<best["changePct"]):
            best={"fromDate":anchor["date"],"fromPrice":anchor["price"],"toDate":point["date"],"toPrice":point["price"],"changePct":change}
        if (direction=="up" and point["price"]<anchor["price"]) or (direction=="down" and point["price"]>anchor["price"]):anchor=point
    return best
windows=[];step=913;all_points=[{"date":dates[i],"price":close[i]} for i in range(len(close))]
for start in range(0,len(all_points),step):
    points=all_points[start:start+step]
    if len(points)<180:continue
    sample=[r for r in rows if points[0]["date"]<=r["date"]<=points[-1]["date"]]
    if not sample:continue
    best=[];base=stats(sample)
    for signal in signals:
        m=stats(sample,signal);m.update({"indicator":signal,"edgePct":m["avgForward30Pct"]-base["avgForward30Pct"]});best.append(m)
    best.sort(key=lambda x:x["edgePct"],reverse=True)
    low=min(points,key=lambda x:x["price"]);high=max(points,key=lambda x:x["price"])
    windows.append({"start":points[0]["date"],"end":points[-1]["date"],"startPrice":points[0]["price"],"endPrice":points[-1]["price"],"returnPct":(points[-1]["price"]/points[0]["price"]-1)*100,"lowPoint":low,"highPoint":high,"bullLeg":strongest_leg(points,"up"),"bearLeg":strongest_leg(points,"down"),"baseline":base,"bestIndicators":best[:3],"turningPointMethod":"윈도우 내부에서 과거 가격을 사후 확인해 최대 저점→후속 고점, 최대 고점→후속 저점을 선택"})
ci=len(close)-1;cma=mean(close[ci-199:ci+1]);cprev=mean(close[ci-219:ci-19]);chigh=max(close[max(0,ci-729):ci+1]);clow=min(close[max(0,ci-729):ci+1])
current={"date":dates[ci],"price":close[ci],"regime":"상승" if close[ci]>cma and cma>cprev else "하락" if close[ci]<cma and cma<cprev else "전환","rsi":rsi(close,ci),"ma200GapPct":(close[ci]/cma-1)*100,"ma200SlopePct":(cma/cprev-1)*100,"drawdownPct":(close[ci]/chigh-1)*100,"cyclePosition":(close[ci]-clow)/(chigh-clow)*100 if chigh>clow else 50}
payload={"updatedAt":datetime.now(KST).isoformat(timespec="seconds"),"source":"Upbit KRW-BTC completed daily candles","firstDate":dates[0],"lastDate":dates[-1],"days":len(bars),"forwardDays":30,"regimeRule":"당시 종가와 200일선 위치 + 200일선 20일 기울기","current":{"date":current["date"],"price":current["price"],"regime":current["regime"],"rsi":current["rsi"],"ma200GapPct":current["ma200GapPct"],"ma200SlopePct":current["ma200SlopePct"],"drawdownPct":current["drawdownPct"],"cyclePosition":current["cyclePosition"]},"regimeAnalysis":analysis,"multiYearWindows":windows,"series":[{"date":r["date"],"price":r["price"],"regime":r["regime"]} for r in rows[::7]],"actualOrders":0}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n");print(json.dumps({"status":"UPDATED","days":len(bars),"from":dates[0],"to":dates[-1],"regime":current["regime"]},ensure_ascii=False))
