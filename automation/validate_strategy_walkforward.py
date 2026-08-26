import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/'monitor_data'/'strategy_walkforward.json').read_text(encoding='utf-8'));assert d['mode']=='RESEARCH_ONLY' and d['actualOrders']==0 and set(d['rankings'])=={'scalp','swing','long'}
for x in d['rankings'].values():
 assert len(x['results'])>=5
 for r in x['results']:assert 'training' in r and 'validation' in r and r['validation']['trades']>=0
print(json.dumps({'status':'PASS','champions':{k:v['champion'] for k,v in d['rankings'].items()},'actualOrders':0},ensure_ascii=False))
