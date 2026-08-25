import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/"monitor_data"/"ma120_touch_similarity.json").read_text(encoding="utf-8"))
assert d["actualOrders"]==0 and d["analyzed"]>=int(d["listed"]*.9)
assert d["successfulTouches"] and d["failedTouches"] and d["currentCandidates"]
assert all(0<=x["chartSimilarity"]<=100 for group in (d["successfulTouches"],d["failedTouches"],d["currentCandidates"]) for x in group)
assert all(0<=x["historicalWinRatePct"]<=100 and x["analogSamples"]>=0 and x["targetHigh"]>=x["targetLow"]>x["price"] for x in d["currentCandidates"])
assert all(x["sellPrice2"]>=x["sellPrice1"]>x["recommendedBuyPrice"]>x["invalidationPrice"] and x["netProfitPct2"]>=x["netProfitPct1"] for x in d["currentCandidates"])
print(json.dumps({"status":"VALID","analyzed":d["analyzed"],"current":len(d["currentCandidates"]),"success":len(d["successfulTouches"]),"failed":len(d["failedTouches"])},ensure_ascii=False))

