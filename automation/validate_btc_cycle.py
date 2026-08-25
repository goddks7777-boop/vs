import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/"monitor_data"/"btc_cycle_analysis.json").read_text(encoding="utf-8"))
assert d["days"]>=2500 and d["actualOrders"]==0
assert set(d["regimeAnalysis"])=={"상승","하락","전환","전체"}
assert len(d["multiYearWindows"])>=3 and len(d["series"])>=300
for w in d["multiYearWindows"]:
 assert all(k in w for k in ("startPrice","endPrice","lowPoint","highPoint","bullLeg","bearLeg"))
 assert w["bullLeg"]["changePct"]>=0 and w["bearLeg"]["changePct"]<=0
print(json.dumps({"status":"VALID","days":d["days"],"current":d["current"]},ensure_ascii=False))
