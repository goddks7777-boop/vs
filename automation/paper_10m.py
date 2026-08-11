import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
NOW = datetime.now(KST)
KRX_HOLIDAYS_2026 = {
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18",
    "2026-03-02", "2026-05-05", "2026-05-25", "2026-08-17",
    "2026-09-24", "2026-09-25", "2026-09-28", "2026-10-05",
    "2026-10-09", "2026-12-25",
}
FEE = 0.0005
SLIP = 0.0005
MAX_POSITIONS = 5
ORDER_BUDGET = 2_000_000
STABLES = {"USDT", "USDC", "USDE", "USD1", "USDG", "USDS"}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def save(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def upbit_prices(symbols):
    result = {}
    markets = [f"KRW-{s}" for s in symbols]
    for start in range(0, len(markets), 80):
        query = urllib.parse.urlencode({"markets": ",".join(markets[start:start + 80])})
        request = urllib.request.Request(
            "https://api.upbit.com/v1/ticker?" + query,
            headers={"User-Agent": "paper-trading-monitor/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            for row in json.load(response):
                result[row["market"].split("-", 1)[1]] = float(row["trade_price"])
    return result


def coin_paper():
    latest = load("monitor_data/latest.json")
    state = load("monitor_data/paper_week.json")
    metrics = {x["symbol"]: x for x in latest["items"]}
    prices = upbit_prices(metrics)
    actions = []
    sold_this_run = set()
    cooldown_since = NOW - timedelta(hours=1)
    recent_sells = {
        trade["symbol"] for trade in state.get("trades", [])
        if trade.get("side") == "SELL" and datetime.fromisoformat(trade["time"]) >= cooldown_since
    }

    def sell(symbol, reason):
        p = state["positions"][symbol]
        x = metrics[symbol]
        fill = prices[symbol] * (1 - SLIP)
        gross = p["qty"] * fill
        fee = gross * FEE
        pnl = gross - fee - p["cost"]
        state["cash"] += gross - fee
        state["trades"].append({"time": NOW.isoformat(timespec="seconds"), "side": "SELL", "symbol": symbol, "name": x["name"], "price": fill, "amount": gross, "fee": fee, "pnl": pnl, "returnPct": pnl / p["cost"] * 100, "reason": reason})
        actions.append({"type": "SELL", "symbol": symbol, "name": x["name"], "comment": reason})
        sold_this_run.add(symbol)
        del state["positions"][symbol]

    for symbol in list(state["positions"]):
        if symbol not in prices or symbol not in metrics:
            continue
        p, x = state["positions"][symbol], metrics[symbol]
        p["peak"] = max(p.get("peak", prices[symbol]), prices[symbol])
        ret = (prices[symbol] / p["entry"] - 1) * 100
        stop = max(3, 2 * p.get("atrPct", 1.5))
        reason = None
        if x.get("comboScore", 0) <= 3:
            reason = "완성 1시간봉 조합점수 3점 이하"
        elif prices[symbol] < x.get("vwap24", prices[symbol]) and x.get("minusDI", 0) > x.get("plusDI", 0):
            reason = "현재가 VWAP 하향 + -DI 우세"
        elif ret <= -stop:
            reason = f"ATR 가상손절 -{stop:.2f}%"
        elif ret >= 6:
            reason = "가상 목표수익 +6%"
        if reason:
            sell(symbol, reason)

    slots = MAX_POSITIONS - len(state["positions"])
    candidates = [x for x in metrics.values() if x["symbol"] not in state["positions"] and x["symbol"] not in STABLES and x["symbol"] not in recent_sells and x["symbol"] not in sold_this_run and x.get("comboScore", 0) >= 6 and x.get("rsi", 99) <= 68 and x.get("volumeRatio", 0) >= 1.2 and x.get("value24", 0) >= 1_000_000_000]
    candidates.sort(key=lambda x: (x["comboScore"], x["value24"]), reverse=True)
    for x in candidates[:slots]:
        budget = min(ORDER_BUDGET, state["cash"])
        if budget < 100_000 or x["symbol"] not in prices:
            break
        fill = prices[x["symbol"]] * (1 + SLIP)
        fee = budget * FEE
        qty = (budget - fee) / fill
        state["cash"] -= budget
        state["positions"][x["symbol"]] = {"name": x["name"], "entry": fill, "qty": qty, "cost": budget, "fee": fee, "time": NOW.isoformat(timespec="seconds"), "atrPct": x.get("atrPct", 1.5), "peak": prices[x["symbol"]], "score": x["comboScore"]}
        reason = f"완성 1시간봉 {x['comboScore']}/7점·RSI {x['rsi']:.1f}·거래량 {x['volumeRatio']:.2f}배"
        state["trades"].append({"time": NOW.isoformat(timespec="seconds"), "side": "BUY", "symbol": x["symbol"], "name": x["name"], "price": fill, "amount": budget - fee, "fee": fee, "pnl": None, "returnPct": None, "reason": reason})
        actions.append({"type": "BUY", "symbol": x["symbol"], "name": x["name"], "comment": reason})

    if not actions:
        actions = [{"type": "WATCH", "symbol": "MARKET", "name": "전체시장", "comment": "10분 점검 결과 새 매수·매도 조건 없음"}]
    state.setdefault("journal", []).append({"time": NOW.isoformat(timespec="seconds"), "market": f"10분 점검 · 보유 {len(state['positions'])}종목", "notes": actions})
    state["journal"] = state["journal"][-300:]
    value = state["cash"] + sum(p["qty"] * prices.get(s, p["entry"]) * (1 - FEE - SLIP) for s, p in state["positions"].items())
    state.setdefault("curve", []).append({"time": NOW.isoformat(timespec="seconds"), "value": value})
    state["curve"] = state["curve"][-1000:]
    save("monitor_data/paper_week.json", state)
    return {"value": round(value), "returnPct": round((value / state["initial"] - 1) * 100, 3), "positions": list(state["positions"]), "trades": len(state["trades"]), "actions": actions}


def stock_paper():
    state = load("stock_data/paper_week_krx.json")
    full_path = ROOT / "stock_data" / "full_metrics.json"
    latest = load("stock_data/full_metrics.json") if full_path.exists() else load("stock_data/latest.json")
    metrics = {}
    for row in latest.get("items", []):
        if row.get("market") not in ("KOSPI", "KOSDAQ"):
            continue
        symbol = row.get("code") or row.get("symbol")
        if symbol:
            metrics[symbol] = {**row, "symbol": symbol}
    weekday = NOW.weekday() < 5 and NOW.date().isoformat() not in KRX_HOLIDAYS_2026
    regular = weekday and time(9, 0) <= NOW.time() <= time(15, 30)
    label = "KRX 정규장 10분 점검" if regular else "KRX 장외시간·휴장: 가상체결 차단"
    actions = []
    prices = {s: x.get("price") for s, x in metrics.items() if x.get("price")}
    if regular:
        for symbol in list(state.get("positions", {})):
            if symbol not in prices or symbol not in metrics: continue
            p, x = state["positions"][symbol], metrics[symbol]
            ret = (prices[symbol] / p["entry"] - 1) * 100
            reason = None
            if x.get("score", 0) <= 2: reason = "기술점수 2점 이하"
            elif ret <= -max(3, 2 * p.get("atrPct", 2)): reason = "ATR 가상손절"
            elif ret >= 6: reason = "가상 목표수익 +6%"
            if reason:
                fill = prices[symbol] * (1 - SLIP); gross = p["qty"] * fill; fee = gross * 0.00015; pnl = gross - fee - p["cost"]
                state["cash"] += gross - fee
                state.setdefault("trades", []).append({"time": NOW.isoformat(timespec="seconds"), "side": "SELL", "symbol": symbol, "name": x["name"], "market": x["market"], "price": fill, "fee": fee, "pnl": pnl, "returnPct": pnl / p["cost"] * 100, "reason": reason})
                actions.append(f"{x['market']} {x['name']} 가상매도: {reason}")
                del state["positions"][symbol]

        slots = MAX_POSITIONS - len(state.get("positions", {}))
        candidates = [x for x in metrics.values() if x["symbol"] not in state.get("positions", {}) and x["symbol"] in prices and x.get("score", 0) >= 5 and 45 <= x.get("rsi", 100) <= 68 and x.get("adx", 0) >= 20 and x.get("plusDI", 0) > x.get("minusDI", 100) and x.get("volumeRatio", 0) >= 1.1]
        candidates.sort(key=lambda x: (x["score"], x.get("volumeRatio", 0)), reverse=True)
        for x in candidates[:slots]:
            budget = min(ORDER_BUDGET, state["cash"])
            if budget < 100_000: break
            fill = prices[x["symbol"]] * (1 + SLIP); fee = budget * 0.00015; qty = (budget - fee) / fill
            state["cash"] -= budget
            state.setdefault("positions", {})[x["symbol"]] = {"name": x["name"], "market": x["market"], "entry": fill, "qty": qty, "cost": budget, "atrPct": x.get("atrPct", 2), "time": NOW.isoformat(timespec="seconds"), "score": x["score"]}
            reason = f"점수 {x['score']}/6·RSI {x['rsi']:.1f}·ADX {x['adx']:.1f}·거래량 {x['volumeRatio']:.2f}배"
            state.setdefault("trades", []).append({"time": NOW.isoformat(timespec="seconds"), "side": "BUY", "symbol": x["symbol"], "name": x["name"], "market": x["market"], "price": fill, "fee": fee, "pnl": None, "returnPct": None, "reason": reason})
            actions.append(f"{x['market']} {x['name']} 가상매수: {reason}")
    if not actions:
        actions = ["정규장 안에서 조건을 점검했으나 가상체결 없음" if regular else "주식 주문은 만들지 않고 대기합니다."]
    state.setdefault("journal", []).append({"runKey": NOW.strftime("%Y-%m-%dT%H:%M")[:-1], "time": NOW.isoformat(timespec="seconds"), "session": label, "tradeEnabled": regular, "notes": actions})
    state["journal"] = state["journal"][-300:]
    save("stock_data/paper_week_krx.json", state)
    value = state["cash"] + sum(p["qty"] * prices.get(s, p["entry"]) * (1 - 0.00015 - SLIP) for s, p in state.get("positions", {}).items())
    return {"session": label, "tradeEnabled": regular, "value": round(value), "returnPct": round((value / state["initial"] - 1) * 100, 3), "positions": len(state.get("positions", {})), "trades": len(state.get("trades", [])), "analyzed": len(metrics)}


coin = coin_paper()
stock = stock_paper()
latest_signal = load("monitor_data/latest.json").get("time")
status = {"time": NOW.isoformat(timespec="seconds"), "signalTime": latest_signal, "mode": "PAPER_ONLY", "actualOrders": 0, "coin": coin, "stock": stock}
save("automation/status_10m.json", status)
print(json.dumps(status, ensure_ascii=False))


