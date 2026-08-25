import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/"monitor_data"/"multi_timeframe_swing.json").read_text(encoding="utf-8"))
assert d["mode"]=="RESEARCH_ONLY" and d["actualOrders"]==0
assert d["design"]["timeframes"]==["4시간봉","1시간봉","30분봉"]
assert d["universe"]["analyzed"]>=max(1,int(d["universe"]["listed"]*.9))
assert all(x in d for x in ("baseline","indicatorStudies","selectedIndicators","selectedBasketTest","recommendations"))
if d["universe"].get("historyMode")=="LISTING_FIRST_CANDLE":
 assert len(d["universe"].get("coverage",[]))>=int(d["universe"]["listed"]*.9)
print(json.dumps({"status":"VALID","listed":d["universe"]["listed"],"analyzed":d["universe"]["analyzed"],"approved":d["approved"],"selected":d["selectedIndicators"]},ensure_ascii=False))
