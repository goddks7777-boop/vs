import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "monitor_data"
DATA.mkdir(parents=True, exist_ok=True)
BASE = "https://api.upbit.com/v1"
KST = ZoneInfo("Asia/Seoul")


def get(path, params=None):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": "paper-trading-monitor/2.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def rsi(close, n=14):
    delta = [close[i] - close[i - 1] for i in range(1, len(close))]
    gain, loss = [max(x, 0) for x in delta], [max(-x, 0) for x in delta]
    ag, al = sum(gain[:n]) / n, sum(loss[:n]) / n
    for x, y in zip(gain[n:], loss[n:]):
        ag, al = (ag * (n - 1) + x) / n, (al * (n - 1) + y) / n
    return 100 if al == 0 else 100 - 100 / (1 + ag / al)


def dmi_adx(high, low, close, n=14):
    tr, plus, minus = [], [], []
    for i in range(1, len(close)):
        tr.append(max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])))
        up, down = high[i] - high[i - 1], low[i - 1] - low[i]
        plus.append(up if up > down and up > 0 else 0)
        minus.append(down if down > up and down > 0 else 0)
    atr_sum, ps, ms, dx = sum(tr[:n]), sum(plus[:n]), sum(minus[:n]), []
    for i in range(n - 1, len(tr)):
        if i >= n:
            atr_sum = atr_sum - atr_sum / n + tr[i]
            ps, ms = ps - ps / n + plus[i], ms - ms / n + minus[i]
        pdi = 100 * ps / atr_sum if atr_sum else 0
        mdi = 100 * ms / atr_sum if atr_sum else 0
        dx.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0)
    adx_value = sum(dx[:n]) / n
    for value in dx[n:]:
        adx_value = (adx_value * (n - 1) + value) / n
    recent_tr = sum(tr[-n:])
    return adx_value, (100 * sum(plus[-n:]) / recent_tr if recent_tr else 0), (100 * sum(minus[-n:]) / recent_tr if recent_tr else 0), sum(tr[-n:]) / n


def obv_slope(close, volume):
    total, history = 0, [0]
    for i in range(1, len(close)):
        total += volume[i] if close[i] > close[i - 1] else -volume[i] if close[i] < close[i - 1] else 0
        history.append(total)
    return (history[-1] - history[-21]) / (sum(volume[-20:]) or 1)


now = datetime.now(KST)
completed_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
latest_path = DATA / "latest.json"
if latest_path.exists():
    previous_time = datetime.fromisoformat(json.loads(latest_path.read_text(encoding="utf-8"))["time"])
    if previous_time.replace(minute=0, second=0, microsecond=0) >= completed_hour:
        print(json.dumps({"status": "SKIPPED", "reason": "completed hour already collected", "signalHour": completed_hour.isoformat()}, ensure_ascii=False))
        raise SystemExit(0)

markets = [row for row in get("/market/all") if row["market"].startswith("KRW-")]
tickers = {}
for start in range(0, len(markets), 100):
    for row in get("/ticker", {"markets": ",".join(x["market"] for x in markets[start:start + 100])}):
        tickers[row["market"]] = row

items, errors = [], []
for market in markets:
    try:
        candles = get("/candles/minutes/60", {"market": market["market"], "count": 200})[::-1]
        candles = [x for x in candles if datetime.fromisoformat(x["candle_date_time_kst"] + "+09:00") <= completed_hour]
        close = [x["trade_price"] for x in candles]
        high = [x["high_price"] for x in candles]
        low = [x["low_price"] for x in candles]
        volume = [x["candle_acc_trade_volume"] for x in candles]
        if len(close) < 60:
            raise ValueError("insufficient completed candles")
        rv, ov = rsi(close), obv_slope(close, volume)
        av, pdi, mdi, atr_value = dmi_adx(high, low, close)
        typical = [(high[i] + low[i] + close[i]) / 3 for i in range(len(close))]
        volume24 = sum(volume[-24:])
        vwap = sum(typical[i] * volume[i] for i in range(len(close) - 24, len(close))) / volume24 if volume24 else None
        ratio = volume[-1] / (sum(volume[-21:-1]) / 20 or 1)
        ma20, ma60 = sum(close[-20:]) / 20, sum(close[-60:]) / 60
        score = sum((close[-1] > vwap, 50 <= rv <= 68, av >= 25, pdi > mdi, ov > 0, ratio >= 1.2, close[-1] > ma20 > ma60))
        ticker = tickers[market["market"]]
        items.append({"symbol": market["market"][4:], "name": market["korean_name"], "price": ticker["trade_price"], "change24": round(ticker["signed_change_rate"] * 100, 3), "value24": ticker["acc_trade_price_24h"], "rsi": round(rv, 2), "obv": round(ov, 3), "adx": round(av, 2), "plusDI": round(pdi, 2), "minusDI": round(mdi, 2), "atrPct": round(atr_value / close[-1] * 100, 3), "vwap24": round(vwap, 8), "volumeRatio": round(ratio, 2), "ma20": ma20, "ma60": ma60, "comboScore": score})
    except Exception as exc:
        errors.append({"market": market["market"], "error": str(exc)[:160]})
    time.sleep(0.12)

snapshot = {"time": completed_hour.isoformat(), "collectedAt": now.isoformat(timespec="seconds"), "count": len(items), "errors": errors, "items": items}
if latest_path.exists():
    (DATA / "previous.json").write_text(latest_path.read_text(encoding="utf-8"), encoding="utf-8")
latest_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
history_path = DATA / "history.json"
history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
history.append({"time": completed_hour.isoformat(), "up": sum(x["change24"] > 0 for x in items), "down": sum(x["change24"] < 0 for x in items), "overbought": sum(x["rsi"] >= 70 for x in items), "oversold": sum(x["rsi"] <= 30 for x in items), "value": sum(x["value24"] for x in items)})
history_path.write_text(json.dumps(history[-720:], ensure_ascii=False), encoding="utf-8")
print(json.dumps({"status": "UPDATED", "signalHour": completed_hour.isoformat(), "coins": len(items), "errors": len(errors)}, ensure_ascii=False))

