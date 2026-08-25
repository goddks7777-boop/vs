import json
from pathlib import Path
d=json.loads((Path(__file__).resolve().parents[1]/"monitor_data"/"coin_market_caps.json").read_text(encoding="utf-8"))
assert d["requested"]>=250 and d["matched"]>=150 and len(d["items"])==d["requested"]
assert all("marketCapKrw" in x and "matchMethod" in x for x in d["items"])
print(json.dumps({"status":"VALID","requested":d["requested"],"matched":d["matched"]},ensure_ascii=False))
