"""과거 4시간봉을 시간순 학습/검증해 기간별 전략과 매집 조건 조합을 선발한다."""
import json,statistics,time,urllib.parse,urllib.request
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'monitor_data'/'strategy_walkforward.json';KST=ZoneInfo('Asia/Seoul');NOW=datetime.now(KST);COST=.002
def api(path,p=None):
 q='?'+urllib.parse.urlencode(p or {}) if p else '';r=urllib.request.Request('https://api.upbit.com/v1'+path+q,headers={'User-Agent':'walk-forward-research/1.0'})
 with urllib.request.urlopen(r,timeout=25) as x:v=json.load(x)
 time.sleep(.13);return v
def mean(x):return sum(x)/len(x) if x else 0
def history(market,limit=600):
 out=[];to=None
 while len(out)<limit:
  p={'market':market,'count':min(200,limit-len(out))}
  if to:p['to']=to
  batch=api('/candles/minutes/240',p)
  if not batch:break
  out+=batch;old=datetime.fromisoformat(batch[-1]['candle_date_time_utc']+'+00:00');to=(old-timedelta(seconds=1)).isoformat().replace('+00:00','Z')
  if len(batch)<p['count']:break
 unique={x['candle_date_time_utc']:x for x in out};return [unique[k] for k in sorted(unique)]
def features(rows,i):
 c=[float(x['trade_price']) for x in rows];h=[float(x['high_price']) for x in rows];l=[float(x['low_price']) for x in rows];v=[float(x['candle_acc_trade_volume']) for x in rows];ob=[0.]
 for j in range(1,i+1):ob.append(ob[-1]+(v[j] if c[j]>c[j-1] else -v[j] if c[j]<c[j-1] else 0))
 def cmf(end):return sum(((((c[j]-l[j])-(h[j]-c[j]))/max(h[j]-l[j],1e-12))*v[j]) for j in range(end-20,end))/max(sum(v[end-20:end]),1e-12)
 ma20=mean(c[i-19:i+1]);ma60=mean(c[i-59:i+1]);ma120=mean(c[i-119:i+1]);vr=v[i]/max(mean(v[i-20:i]),1e-12);dry=mean(v[i-5:i])/max(mean(v[i-25:i-5]),1e-12);box=(max(h[i-20:i])/min(l[i-20:i])-1)*100;os=(ob[i]-ob[i-10])/max(sum(v[i-9:i+1]),1e-12);op=(ob[i-5]-ob[i-15])/max(sum(v[i-14:i-4]),1e-12);cf=cmf(i+1);cp=cmf(i-4)
 return {'price':c[i],'trend':c[i]>ma20>ma60 and ma20>mean(c[i-24:i-4]),'break20':c[i]>max(h[i-20:i]),'break10':c[i]>max(h[i-10:i]),'vol15':vr>=1.5,'vol12':vr>=1.2,'touch120':min(l[i-3:i+1])<=ma120*1.01 and c[i]>ma120,'dry':dry<.9,'box12':box<=12,'box8':box<=8,'cmf0':cf>0,'cmf03':cf>.03,'cmfImprove':cf>cp+.02,'obv':os>0,'obvImprove':os>op}
RULES={
 '추세 돌파형':lambda f:f['trend'] and f['break20'] and f['vol15'] and f['obv'],
 'MA120 반등형':lambda f:f['touch120'] and f['dry'] and f['break10'] and f['vol12'],
 '매집 기본형':lambda f:f['box12'] and f['cmf0'] and f['obv'] and f['break20'],
 '매집 개선형':lambda f:f['box12'] and f['cmfImprove'] and f['obvImprove'] and f['vol12'],
 '매집 압축형':lambda f:f['box8'] and f['dry'] and f['cmf03'] and f['obv'],
}
STYLE={'scalp':{'label':'단타','bars':6},'swing':{'label':'스윙','bars':30},'long':{'label':'장타','bars':90}}
latest=json.loads((ROOT/'monitor_data'/'latest.json').read_text(encoding='utf-8'));top=sorted(latest['items'],key=lambda x:x.get('value24',0),reverse=True)[:40];samples=[];errors=[]
for x in top:
 try:
  rows=history('KRW-'+x['symbol'])
  if len(rows)<160:raise ValueError('4시간봉 160개 미만')
  close=[float(z['trade_price']) for z in rows]
  for i in range(125,len(rows)-6):
   f=features(rows,i)
   for name,rule in RULES.items():
    if rule(f):samples.append({'symbol':x['symbol'],'i':i,'n':len(rows),'strategy':name,'entry':close[i],'future':close,'date':rows[i]['candle_date_time_kst']})
 except Exception as e:errors.append({'symbol':x['symbol'],'error':str(e)[:100]})
def metric(a,bars):
 vals=[];last={}
 for z in sorted(a,key=lambda x:(x['date'],x['symbol'])):
  if z['i']-last.get(z['symbol'],-10_000)<bars:continue
  j=z['i']+bars
  if j<z['n']:vals.append((z['future'][j]/z['entry']-1)*100-COST*100);last[z['symbol']]=z['i']
 win=[v for v in vals if v>0];loss=[v for v in vals if v<0];gp=sum(win);gl=abs(sum(loss))
 return {'trades':len(vals),'winRate':round(len(win)/len(vals)*100,2) if vals else 0,'expectancyPct':round(mean(vals),3),'profitFactor':round(gp/gl,3) if gl else None,'medianPct':round(statistics.median(vals),3) if vals else 0}
rankings={}
for sk,sc in STYLE.items():
 rows=[]
 for name in RULES:
  a=[z for z in samples if z['strategy']==name];a.sort(key=lambda z:z['date']);cut=int(len(a)*.7);tr=metric(a[:cut],sc['bars']);te=metric(a[cut:],sc['bars']);approved=tr['trades']>=30 and te['trades']>=15 and tr['expectancyPct']>0 and (tr['profitFactor'] or 0)>=1.0 and te['expectancyPct']>0 and (te['profitFactor'] or 0)>=1.1
  score=te['expectancyPct']*.35+(te['profitFactor'] or 0)*.25+te['winRate']/100*.1-max(0,-te['medianPct'])*.1
  rows.append({'strategy':name,'training':tr,'validation':te,'score':round(score,3),'approved':approved})
 rows.sort(key=lambda z:(z['approved'],z['score']),reverse=True);rankings[sk]={'label':sc['label'],'holding4hBars':sc['bars'],'champion':next((z['strategy'] for z in rows if z['approved']),None),'challengers':[z['strategy'] for z in rows if z['approved']][1:3],'results':rows}
acc=[z for z in rankings['swing']['results'] if z['strategy'].startswith('매집')];best=next((z for z in acc if z['approved']),acc[0] if acc else None);by_coin=[]
if best:
 for symbol in sorted({z['symbol'] for z in samples}):
  m=metric([z for z in samples if z['strategy']==best['strategy'] and z['symbol']==symbol],STYLE['swing']['bars'])
  if m['trades']>=3:by_coin.append({'symbol':symbol,**m})
 by_coin.sort(key=lambda z:(z['expectancyPct'],z['profitFactor'] or 0),reverse=True)
data={'updatedAt':NOW.isoformat(timespec='seconds'),'mode':'RESEARCH_ONLY','actualOrders':0,'method':{'split':'시간순 70% 학습 / 최근 30% 미사용 검증','history':'종목별 최근 600개 완성 4시간봉','costPct':COST*100,'universe':'업비트 KRW 거래대금 상위 40종목','antiOverfit':['같은 종목 보유기간 내 중복 신호 제거','최소 학습 30건','최소 검증 15건','학습·검증 기대수익 모두 > 0','학습 PF ≥ 1.0·검증 PF ≥ 1.1']},'universe':{'requested':40,'analyzed':40-len(errors)},'rankings':rankings,'bestAccumulation':best,'errors':errors}
data['bestAccumulationByCoin']=by_coin;OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n');print(json.dumps({'status':'UPDATED','samples':len(samples),'champions':{k:v['champion'] for k,v in rankings.items()},'bestAccumulation':best['strategy'] if best else None,'chartResults':len(by_coin),'errors':len(errors),'actualOrders':0},ensure_ascii=False))
