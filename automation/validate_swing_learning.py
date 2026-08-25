import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "monitor_data" / "swing_learning.json").read_text(encoding="utf-8"))

def require(condition, message):
    if not condition:
        raise SystemExit("SWING VALIDATION FAILED: " + message)

require(data.get("mode") == "RESEARCH_ONLY", "mode must remain RESEARCH_ONLY")
require(data.get("actualOrders") == 0, "actualOrders must remain zero")
require(data.get("design", {}).get("holdingDays") == 14, "unexpected holding period")
require(data.get("splits", {}).get("train", 0) > 0, "training set is empty")
require(data.get("splits", {}).get("validation", 0) > 0, "validation set is empty")
require(data.get("splits", {}).get("test", 0) > 0, "test set is empty")
require(0 <= data.get("validation", {}).get("winRate", -1) <= 100, "invalid validation win rate")
require(0 <= data.get("test", {}).get("winRate", -1) <= 100, "invalid test win rate")
require(len(data.get("ranking", [])) <= 30, "ranking is unexpectedly large")
require(data.get("design", {}).get("targetMode") == "차트별 동적 목표", "dynamic target mode is missing")
require(all(x.get("targetExpectedPct", 0) > 0 and x.get("target1Price", 0) > x.get("referencePrice", 0) for x in data.get("ranking", [])), "invalid chart target")
datetime.fromisoformat(data["updatedAt"])
print(json.dumps({"status": "VALID", "approved": data.get("approved"), "updatedAt": data["updatedAt"]}, ensure_ascii=False))

