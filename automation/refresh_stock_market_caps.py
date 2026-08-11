import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
rows = []
for market in ("KOSPI", "KOSDAQ"):
    page = 1
    while True:
        query = urllib.parse.urlencode({"page": page, "pageSize": 100})
        request = urllib.request.Request(
            f"https://m.stock.naver.com/api/stocks/marketValue/{market}?{query}",
            headers={"User-Agent": "Mozilla/5.0 market-analysis-paper-monitor/1.0"},
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.load(response)
        batch = payload.get("stocks", [])
        for item in batch:
            rows.append({
                "market": market,
                "code": item.get("itemCode"),
                "name": item.get("stockName"),
                "marketCap": int(item.get("marketValueRaw") or 0),
                "marketCapText": item.get("marketValueHangeul") or "—",
                "price": int(item.get("closePriceRaw") or 0),
                "change": float(item.get("fluctuationsRatio") or 0),
                "volume": int(item.get("accumulatedTradingVolumeRaw") or 0),
                "tradedValue": int(item.get("accumulatedTradingValueRaw") or 0),
                "time": item.get("localTradedAt"),
            })
        if page * 100 >= int(payload.get("totalCount") or 0) or not batch:
            break
        page += 1

output = {
    "updatedAt": datetime.now(KST).isoformat(timespec="seconds"),
    "source": "Naver Finance domestic market-value list",
    "count": len(rows),
    "items": rows,
}
target = ROOT / "stock_data" / "market_caps.json"
target.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"marketCaps": len(rows), "updatedAt": output["updatedAt"]}, ensure_ascii=False))

