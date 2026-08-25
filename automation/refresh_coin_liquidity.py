"""공개 파생시장 데이터로 코인 유동 페이지용 스냅샷을 만든다."""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "monitor_data" / "coin_liquidity.json"


def get(path, params):
    url = "https://api.bybit.com" + path + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "market-liquidity-research/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.load(response)
    if data.get("retCode") != 0:
        raise RuntimeError(data.get("retMsg", "Bybit API error"))
    return data["result"]


def upbit(path, params=None):
    query = "?" + urllib.parse.urlencode(params or {}) if params else ""
    request = urllib.request.Request("https://api.upbit.com/v1" + path + query, headers={"User-Agent": "market-liquidity-research/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def upbit_spot_snapshot():
    markets = [x for x in upbit("/market/all", {"is_details": "false"}) if x["market"].startswith("KRW-")]
    names = {x["market"]: x["korean_name"] for x in markets}
    tickers = []
    codes = list(names)
    for start in range(0, len(codes), 80):
        tickers.extend(upbit("/ticker", {"markets": ",".join(codes[start:start + 80])}))
    rows = [{"market": x["market"], "symbol": x["market"].split("-", 1)[1], "name": names[x["market"]],
             "price": number(x["trade_price"]), "turnover24h": number(x["acc_trade_price_24h"]),
             "change24hPct": number(x["signed_change_rate"]) * 100} for x in tickers]
    rows.sort(key=lambda x: x["turnover24h"], reverse=True)
    total = sum(x["turnover24h"] for x in rows)
    top5 = sum(x["turnover24h"] for x in rows[:5])
    refs = [market for market in ("KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP") if market in names]
    orderbooks = upbit("/orderbook", {"markets": ",".join(refs)}) if refs else []
    depth = []
    for book in orderbooks:
        units = book.get("orderbook_units", [])
        bid_value = sum(number(x["bid_price"]) * number(x["bid_size"]) for x in units)
        ask_value = sum(number(x["ask_price"]) * number(x["ask_size"]) for x in units)
        best_bid = number(units[0]["bid_price"]) if units else 0
        best_ask = number(units[0]["ask_price"]) if units else 0
        depth.append({"symbol": book["market"].split("-", 1)[1], "bidValue": bid_value, "askValue": ask_value,
                      "imbalancePct": (bid_value - ask_value) / (bid_value + ask_value) * 100 if bid_value + ask_value else 0,
                      "spreadPct": (best_ask / best_bid - 1) * 100 if best_bid else 0, "levels": len(units)})
    return {"count": len(rows), "turnover24h": total, "advancers": sum(x["change24hPct"] > 0 for x in rows),
            "decliners": sum(x["change24hPct"] < 0 for x in rows), "unchanged": sum(x["change24hPct"] == 0 for x in rows),
            "top5ConcentrationPct": top5 / total * 100 if total else 0, "topTurnover": rows[:15], "orderbookDepth": depth}


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def reference_zones(price):
    zones = []
    # 단순 교육용 근사치. 유지증거금·교차마진·추가증거금은 반영하지 않는다.
    for leverage in (5, 10, 20):
        move = 1 / leverage
        zones.append({
            "leverage": leverage,
            "longReference": price * (1 - move),
            "shortReference": price * (1 + move),
            "distancePct": move * 100,
        })
    return zones


result = get("/v5/market/tickers", {"category": "linear"})
spot = upbit_spot_snapshot()
rows = []
for item in result.get("list", []):
    symbol = item.get("symbol", "")
    if not symbol.endswith("USDT") or "-" in symbol:
        continue
    price = number(item.get("markPrice") or item.get("lastPrice"))
    funding = number(item.get("fundingRate")) * 100
    open_interest = number(item.get("openInterest"))
    oi_value = open_interest * price
    turnover = number(item.get("turnover24h"))
    if price <= 0 or turnover <= 0:
        continue
    rows.append({
        "symbol": symbol[:-4], "pair": symbol, "markPrice": price,
        "fundingRatePct": funding, "annualizedFundingPct": funding * 3 * 365,
        "nextFundingTime": int(number(item.get("nextFundingTime"))),
        "openInterest": open_interest, "openInterestValue": oi_value,
        "turnover24h": turnover, "priceChange24hPct": number(item.get("price24hPcnt")) * 100,
        "basisPct": (number(item.get("lastPrice")) / price - 1) * 100 if price else 0,
    })

rows.sort(key=lambda x: x["turnover24h"], reverse=True)
liquid = rows[:120]
summary_rows = liquid[:50]
positive = sorted(summary_rows, key=lambda x: x["fundingRatePct"], reverse=True)[:10]
negative = sorted(summary_rows, key=lambda x: x["fundingRatePct"])[:10]
by_symbol = {row["symbol"]: row for row in rows}
assets = []
for symbol in ("BTC", "ETH", "SOL", "XRP"):
    if symbol in by_symbol:
        row = by_symbol[symbol]
        assets.append({**row, "referenceZones": reference_zones(row["markPrice"])})

weighted_denominator = sum(x["openInterestValue"] for x in summary_rows)
weighted_funding = sum(x["fundingRatePct"] * x["openInterestValue"] for x in summary_rows) / weighted_denominator if weighted_denominator else 0
derivatives_turnover = sum(x["turnover24h"] for x in summary_rows)
open_interest_value = sum(x["openInterestValue"] for x in summary_rows)
previous = {}
if OUT.exists():
    try:
        previous = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
history = previous.get("history", [])
now_text = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
history.append({"time": now_text, "spotTurnover24h": spot["turnover24h"], "derivativesTurnover24h": derivatives_turnover,
                "openInterestValue": open_interest_value, "weightedFundingPct": weighted_funding,
                "advancers": spot["advancers"], "decliners": spot["decliners"]})
history = history[-336:]
payload = {
    "updatedAt": now_text,
    "mode": "PUBLIC_MARKET_DATA_ONLY", "actualOrders": 0,
    "source": {"name": "Bybit Public Market API", "endpoint": "/v5/market/tickers?category=linear"},
    "summary": {"contracts": len(rows), "displayed": len(summary_rows), "weightedFundingPct": weighted_funding,
                "openInterestValue": open_interest_value, "turnover24h": derivatives_turnover,
                "turnoverToOIRatio": derivatives_turnover / open_interest_value if open_interest_value else 0,
                "positiveExtremeCount": sum(x["fundingRatePct"] >= 0.03 for x in summary_rows),
                "negativeExtremeCount": sum(x["fundingRatePct"] <= -0.03 for x in summary_rows)},
    "spot": spot, "history": history,
    "positiveFunding": positive, "negativeFunding": negative, "contracts": summary_rows, "referenceAssets": assets,
    "heatmap": {"type": "EDUCATIONAL_REFERENCE_ONLY", "actualLiquidationData": False,
                "explanation": "레버리지 역수로 계산한 단순 가격 참고선이며 실제 포지션·유지증거금·교차마진을 반영하지 않음",
                "externalUrl": "https://www.coinglass.com/pro/futures/LiquidationHeatMap"},
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
print(json.dumps({"status": "UPDATED", "contracts": len(rows), "displayed": len(summary_rows), "actualOrders": 0}, ensure_ascii=False))
