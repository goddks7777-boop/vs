import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/"monitor_data"/"coin_accumulation.json").read_text(encoding="utf-8"))
assert d["actualOrders"]==0 and d["analyzed"]>=int(d["listed"]*.9)
assert all(0<=x["accumulationScore"]<=6 and x["phase"] in {"돌파 확인","매집 후 상승 전환","매집 후보","급등·추격 주의","일반 관찰"} for x in d["items"])
print(json.dumps({"status":"VALID","listed":d["listed"],"analyzed":d["analyzed"]},ensure_ascii=False))

