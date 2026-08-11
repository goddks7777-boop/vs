import argparse
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise SystemExit("VALIDATION FAILED: " + message)


parser = argparse.ArgumentParser()
parser.add_argument("--market", choices=("coin", "stock", "all"), default="all")
args = parser.parse_args()
status = load("automation/status_10m.json")
require(status.get("mode") == "PAPER_ONLY", "mode must be PAPER_ONLY")
require(status.get("actualOrders") == 0, "actualOrders must remain zero")

if args.market in ("coin", "all"):
    latest = load("monitor_data/latest.json")
    previous = load("monitor_data/previous.json")
    state = load("monitor_data/paper_week.json")
    require(latest.get("count", 0) >= 250, "coin universe is too small")
    require(len(latest.get("items", [])) == latest.get("count"), "coin count mismatch")
    require(len(latest.get("errors", [])) <= 10, "too many coin collection errors")
    require(previous.get("items") is not None, "previous coin snapshot missing")
    require(0 <= len(state.get("positions", {})) <= 5, "invalid coin position count")
    require(state.get("cash", -1) >= 0, "negative coin cash")
    require(status.get("coinUpdatedAt"), "coin update timestamp missing")
    require(status.get("coin", {}).get("trades") == len(state.get("trades", [])), "coin trade count mismatch")
    html = (ROOT / "코인_1주일_가상투자.html").read_text(encoding="utf-8")
    require("automation/paper-live.js" in html, "coin live UI script missing")

if args.market in ("stock", "all"):
    universe = load("stock_data/universe.json")
    caps = load("stock_data/market_caps.json")
    metrics = load("stock_data/full_metrics.json")
    state = load("stock_data/paper_week_krx.json")
    require(len(universe.get("items", [])) >= 2700, "stock universe is too small")
    require(caps.get("count", 0) >= 2500, "stock market-cap list is too small")
    require(metrics.get("universe", 0) >= 2700, "stock metrics universe is too small")
    require(len(metrics.get("items", [])) == metrics.get("universe"), "stock metrics count mismatch")
    require(0 <= len(state.get("positions", {})) <= 5, "invalid stock position count")
    require(state.get("cash", -1) >= 0, "negative stock cash")
    require(status.get("stockUpdatedAt"), "stock update timestamp missing")
    require(status.get("stock", {}).get("trades") == len(state.get("trades", [])), "stock trade count mismatch")
    html = (ROOT / "주식_1주일_모의투자.html").read_text(encoding="utf-8")
    require("automation/stock-paper-live.js" in html, "stock live UI script missing")

datetime.fromisoformat(status["time"])
print(json.dumps({"status": "VALID", "market": args.market, "time": status["time"]}, ensure_ascii=False))

