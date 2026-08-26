import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"monitor_data"/"paper_style_portfolios.json";d=json.loads(p.read_text(encoding="utf-8"));assert d["mode"]=="PAPER_ONLY" and d["actualOrders"]==0
assert set(d["portfolios"])=={"scalp","swing","long"}
for k,v in d["portfolios"].items():
 assert v["initial"]==10_000_000 and v["cash"]>=0 and len(v["positions"])<=3
 assert "winRate" in v["stats"] and "expectancyPct" in v["stats"]
assert all(x["strategy"] in ("추세 돌파형","MA120 반등형","매집 전환형") for x in d["candidates"])
print(json.dumps({"status":"PASS","portfolios":3,"candidates":len(d["candidates"]),"actualOrders":0},ensure_ascii=False))
