import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/"monitor_data"/"ma120_touch_similarity.json").read_text(encoding="utf-8"))
assert d["actualOrders"]==0 and d["analyzed"]>=int(d["listed"]*.9)
assert d["successfulTouches"] and d["failedTouches"] and d["currentCandidates"]
assert all(0<=x["chartSimilarity"]<=100 for group in (d["successfulTouches"],d["failedTouches"],d["currentCandidates"]) for x in group)
print(json.dumps({"status":"VALID","analyzed":d["analyzed"],"current":len(d["currentCandidates"]),"success":len(d["successfulTouches"]),"failed":len(d["failedTouches"])},ensure_ascii=False))

