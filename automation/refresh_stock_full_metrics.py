import json
import math
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
TODAY = datetime.now(KST).date().isoformat().replace("-", "")
LIMIT = int(os.environ.get("STOCK_REFRESH_LIMIT", "3000"))


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def load_optional(name, fallback):
    try:
        return load(name)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        return fallback


def indicators(code):
    url = "https://fchart.stock.naver.com/sise.nhn?" + urllib.parse.urlencode({"symbol": code, "timeframe": "day", "count": 90, "requestType": 0})
    error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 full-krx-paper-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("euc-kr", errors="replace")
                raw = raw.replace('encoding="EUC-KR"', 'encoding="UTF-8"')
                root = ET.fromstring(raw)
            rows = []
            for node in root.findall(".//item"):
                parts = node.attrib["data"].split("|")
                if len(parts) >= 6 and parts[0] < TODAY:
                    rows.append([parts[0]] + [float(x or 0) for x in parts[1:6]])
            if len(rows) < 61:
                raise ValueError(f"completed daily candles={len(rows)}")
            close, high, low, volume = [x[4] for x in rows], [x[2] for x in rows], [x[3] for x in rows], [x[5] for x in rows]
            n = 14
            delta = [close[i] - close[i - 1] for i in range(1, len(close))]
            gains, losses = [max(x, 0) for x in delta], [max(-x, 0) for x in delta]
            ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
            for gain, loss in zip(gains[n:], losses[n:]):
                ag, al = (ag * 13 + gain) / 14, (al * 13 + loss) / 14
            rsi = 100 if al == 0 else 100 - 100 / (1 + ag / al)
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
                pdi, mdi = (100 * ps / atr_sum if atr_sum else 0), (100 * ms / atr_sum if atr_sum else 0)
                dx.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0)
            adx = sum(dx[:n]) / n
            for value in dx[n:]: adx = (adx * 13 + value) / 14
            recent_tr = sum(tr[-n:]); pdi = 100 * sum(plus[-n:]) / recent_tr if recent_tr else 0; mdi = 100 * sum(minus[-n:]) / recent_tr if recent_tr else 0
            obv, history = 0, [0]
            for i in range(1, len(close)):
                obv += volume[i] if close[i] > close[i - 1] else -volume[i] if close[i] < close[i - 1] else 0; history.append(obv)
            obv_slope = (history[-1] - history[-21]) / (sum(volume[-20:]) or 1)
            volume_ratio = volume[-1] / (sum(volume[-21:-1]) / 20 or 1)
            ma20, ma60 = sum(close[-20:]) / 20, sum(close[-60:]) / 60
            atr_pct = (sum(tr[-14:]) / 14) / close[-1] * 100 if close[-1] else 0
            score = sum((50 <= rsi <= 68, adx >= 20, pdi > mdi, obv_slope > 0, volume_ratio >= 1.1, close[-1] > ma20 > ma60))
            return {"rsi": round(rsi, 2), "adx": round(adx, 2), "plusDI": round(pdi, 2), "minusDI": round(mdi, 2), "obv": round(obv_slope, 3), "volumeRatio": round(volume_ratio, 2), "atrPct": round(atr_pct, 3), "ma20": round(ma20, 4), "ma60": round(ma60, 4), "score": score, "signalDate": rows[-1][0]}
        except Exception as exc:
            error = str(exc)
            time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(error)


universe = [x for x in load("stock_data/universe.json")["items"] if x["market"] in ("KOSPI", "KOSDAQ")]
caps = load("stock_data/market_caps.json")["items"]
by_name = {(x["market"], x["name"]): x for x in caps}
by_code = {(x["market"], x["code"]): x for x in caps}
target = []
for item in universe:
    derived = item["symbol"][3:9] if item["symbol"].startswith("KR7") else ""
    cap = by_name.get((item["market"], item["name"])) or by_code.get((item["market"], derived))
    code = cap["code"] if cap else derived if derived.isdigit() else None
    target.append({**item, "code": code, "price": cap.get("price") if cap else None, "change": cap.get("change") if cap else None, "amount": cap.get("tradedValue") if cap else None, "marketCap": cap.get("marketCap") if cap else None, "marketCapText": cap.get("marketCapText") if cap else "—"})

path = ROOT / "stock_data" / "full_metrics.json"
previous = load_optional("stock_data/full_metrics.json", {"items": []})
old = {x["symbol"]: x for x in previous.get("items", [])}
pending = [x for x in target if x["code"] and (x["symbol"] not in old or old[x["symbol"]].get("calculatedFor") != TODAY or old[x["symbol"]].get("error"))]
pending = pending[:LIMIT]
results, failures = {}, {}
with ThreadPoolExecutor(max_workers=16) as pool:
    jobs = {pool.submit(indicators, x["code"]): x for x in pending}
    for future in as_completed(jobs):
        item = jobs[future]
        try: results[item["symbol"]] = future.result()
        except Exception as exc: failures[item["symbol"]] = str(exc)[:160]

items = []
for item in target:
    metric = results.get(item["symbol"])
    prior = old.get(item["symbol"], {})
    merged = {**item, **({} if metric is None else metric)}
    if metric is None:
        for key in ("rsi", "adx", "plusDI", "minusDI", "obv", "volumeRatio", "atrPct", "ma20", "ma60", "score", "signalDate", "calculatedFor"):
            if key in prior: merged[key] = prior[key]
    if metric is not None: merged["calculatedFor"] = TODAY
    if item["symbol"] in failures: merged["error"] = failures[item["symbol"]]
    else: merged.pop("error", None)
    merged["status"] = "분석 완료" if merged.get("score") is not None else "신규상장·지표 계산 대기"
    items.append(merged)

complete = sum(x.get("score") is not None for x in items)
output = {"time": datetime.now(KST).isoformat(timespec="seconds"), "universe": len(items), "complete": complete, "pending": len(items) - complete, "errorsThisRun": len(failures), "items": items}
temporary = path.with_suffix(".json.tmp")
temporary.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8", newline="\n")
temporary.replace(path)
print(json.dumps({k: output[k] for k in ("universe", "complete", "pending", "errorsThisRun")}, ensure_ascii=False))


