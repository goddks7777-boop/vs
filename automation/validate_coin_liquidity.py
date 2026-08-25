import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "monitor_data" / "coin_liquidity.json").read_text(encoding="utf-8"))

def require(value, message):
    if not value:
        raise SystemExit("LIQUIDITY VALIDATION FAILED: " + message)

require(data.get("mode") == "PUBLIC_MARKET_DATA_ONLY", "invalid mode")
require(data.get("actualOrders") == 0, "actual orders must remain zero")
require(data.get("summary", {}).get("displayed", 0) >= 30, "too few contracts")
require(data.get("heatmap", {}).get("actualLiquidationData") is False, "estimated map mislabeled")
require(len(data.get("referenceAssets", [])) >= 2, "reference assets missing")
require(data.get("spot", {}).get("count", 0) >= 250, "KRW spot universe too small")
require(data.get("spot", {}).get("turnover24h", 0) > 0, "spot turnover missing")
require(len(data.get("spot", {}).get("orderbookDepth", [])) >= 2, "orderbook depth missing")
require(len(data.get("history", [])) >= 1, "liquidity history missing")
datetime.fromisoformat(data["updatedAt"])
print(json.dumps({"status": "VALID", "updatedAt": data["updatedAt"]}, ensure_ascii=False))
